"""Parcours de l'enveloppe : guide, tronçons, bandes redressées et reprojection."""
import math

from PIL import Image, ImageDraw
from shapely.geometry import Point

from app.services import thermique_parcours_enveloppe as enveloppe

PX_PAR_M = 118.11  # 300 dpi au 1/100


def _analyse():
    # deux pièces accolées de 10 m x 5 m sur une page de 2000 x 1000 px
    def norm(x, y):
        return [x * 1000 / 2000, y * 1000 / 1000]

    a = [norm(x, y) for x, y in ((200, 200), (200 + 5 * PX_PAR_M, 200), (200 + 5 * PX_PAR_M, 200 + 5 * PX_PAR_M), (200, 200 + 5 * PX_PAR_M))]
    b = [norm(x + 5 * PX_PAR_M + 12, y) for x, y in ((200, 200), (200 + 5 * PX_PAR_M, 200), (200 + 5 * PX_PAR_M, 200 + 5 * PX_PAR_M), (200, 200 + 5 * PX_PAR_M))]
    return {"objects": [
        {"id": "piece-001", "category": "piece", "subtype": "Bureau A", "geometry_type": "polygon", "points": a},
        {"id": "piece-002", "category": "piece", "subtype": "Bureau B", "geometry_type": "polygon", "points": b},
    ], "manifest": {"page_width_px": 2000, "page_height_px": 1000, "crop_box_px": [0, 0, 2000, 1000],
                    "width_px": 2000, "height_px": 1000}}


def test_guide_ferme_la_cloison_et_part_du_nord_ouest_en_sens_horaire():
    guide = enveloppe.contour_guide(_analyse(), 2000, 1000, PX_PAR_M)

    assert len(guide["anneau"]) == 4
    depart, suivant = guide["anneau"][0], guide["anneau"][1]
    assert depart == min(guide["anneau"], key=lambda p: p[0] + p[1])
    assert suivant[0] > depart[0] and abs(suivant[1] - depart[1]) < 1  # vers l'est : sens horaire à l'écran


def test_troncons_de_5_m_au_plus_normale_vers_l_exterieur_et_piece_interieure():
    analyse = _analyse()
    guide = enveloppe.contour_guide(analyse, 2000, 1000, PX_PAR_M)
    liste = enveloppe.troncons(guide, analyse, 2000, 1000, PX_PAR_M)

    assert all(t["fin_m"] - t["debut_m"] <= 5.0 + 1e-6 for t in liste)
    assert math.isclose(liste[-1]["fin_m"], 2 * (10.1 + 5), rel_tol=0.02)
    nord = liste[0]
    assert nord["normale_ext"][1] < 0  # la façade nord regarde vers le haut de l'image
    assert nord["piece"] == "Bureau A"


def test_bande_redressee_montre_l_exterieur_en_haut():
    analyse = _analyse()
    page = Image.new("L", (2000, 1000), 255)
    # mur nord réel : bande noire de 20 cm au-dessus du nu intérieur (y = 200)
    ImageDraw.Draw(page).rectangle((150, 200 - round(0.2 * PX_PAR_M), 1500, 199), fill=0)
    guide = enveloppe.contour_guide(analyse, 2000, 1000, PX_PAR_M)
    troncon = enveloppe.troncons(guide, analyse, 2000, 1000, PX_PAR_M)[0]

    bande = enveloppe._bande(page, troncon, PX_PAR_M)

    k = PX_PAR_M * enveloppe.AGRANDISSEMENT
    y_mur = round((enveloppe.BANDE_EXTERIEURE_M - 0.10) * k)  # 10 cm côté extérieur
    y_interieur = round((enveloppe.BANDE_EXTERIEURE_M + 0.10) * k)  # 10 cm côté intérieur
    x = bande.width // 2
    assert bande.getpixel((x, y_mur)) < 60
    assert bande.getpixel((x, y_interieur)) > 200


def test_reprojection_et_bibliotheque():
    analyse = _analyse()
    guide = enveloppe.contour_guide(analyse, 2000, 1000, PX_PAR_M)
    liste = enveloppe.troncons(guide, analyse, 2000, 1000, PX_PAR_M)
    manifeste = {"px_par_m": PX_PAR_M, "page_px": [2000, 1000], "troncons": liste}
    t = liste[0]
    couches = [{"nature": "mur", "epaisseur_cm": 16, "indice": ""}, {"nature": "isolant", "epaisseur_cm": 12, "indice": ""},
               {"nature": "mur", "epaisseur_cm": 20, "indice": ""}]
    brut = {"elements": [
        {"troncon": t["id"], "debut_m": t["debut_m"], "fin_m": t["debut_m"] + 2, "type": "paroi", "nu_exterieur_cm": 48,
         "nu_interieur_cm": 0, "couches": couches, "menuiserie_type": "", "cadre_cm": 0, "confiance": 0.9, "indice": "", "a_verifier": False},
        {"troncon": t["id"], "debut_m": t["debut_m"] + 2, "fin_m": t["debut_m"] + 3.2, "type": "menuiserie", "nu_exterieur_cm": 48,
         "nu_interieur_cm": 0, "couches": [], "menuiserie_type": "fenêtre", "cadre_cm": 10, "confiance": 0.8, "indice": "", "a_verifier": False},
        {"troncon": t["id"], "debut_m": t["debut_m"] + 3.2, "fin_m": t["debut_m"] + 3.3, "type": "angle_sortant", "nu_exterieur_cm": 48,
         "nu_interieur_cm": 0, "couches": [], "menuiserie_type": "", "cadre_cm": 0, "confiance": 0.6, "indice": "angle", "a_verifier": False},
    ], "observations": []}

    releve = enveloppe.reprojeter(brut, manifeste, analyse)

    # une couche = un objet : voile extérieur, isolant, voile intérieur, doublage BA13 présumé
    categories = [o["category"] for o in releve["objets"]]
    assert categories == ["mur_exterieur", "isolation", "mur_exterieur", "doublage", "menuiserie_exterieure"]
    sous_types = [o["subtype"] for o in releve["objets"][:4]]
    assert sous_types == ["voile extérieur 16 cm", "isolant 12 cm", "voile intérieur 20 cm", "doublage BA13 présumé 1.3 cm"]
    assert releve["objets"][3]["review_required"] and not releve["objets"][0]["review_required"]
    paroi = releve["bibliotheque"]["parois"][0]
    assert paroi["composition"] == "mur 16 + isolant 12 + mur 20 + doublage 1.3 présumé"
    assert math.isclose(paroi["lineaire_m"], 2.0) and paroi["epaisseur_cm"] == 48
    assert releve["bibliotheque"]["menuiseries"][0]["largeurs_cm"] == [120]
    assert releve["bibliotheque"]["liaisons"][0]["type"] == "angle_sortant"
    # l'isolant est entre 32 et 20 cm à l'extérieur du nu intérieur (nord : y plus petit que 200 px)
    ys = [y * 1000 / 1000 for _, y in releve["objets"][1]["points"]]
    assert all(200 - 0.33 * PX_PAR_M <= y <= 200 - 0.19 * PX_PAR_M for y in ys)
    # le doublage présumé est côté pièce, sous le nu intérieur dessiné (y > 200 px au nord)
    ys = [y * 1000 / 1000 for _, y in releve["objets"][3]["points"]]
    assert all(200 - 0.5 <= y <= 200 + 0.02 * PX_PAR_M for y in ys)


def test_doublage_presume_seulement_sur_un_voile_nu_et_hors_elements_exclus():
    voile = {"nature": "mur", "epaisseur_cm": 20, "indice": ""}
    isolant = {"nature": "isolant", "epaisseur_cm": 10, "indice": ""}
    assert enveloppe.avec_doublage_presume([voile, isolant]) == [voile, isolant]  # ITE nue côté pièce : rien
    assert enveloppe.avec_doublage_presume([isolant, voile])[-1]["presume"]
    lu = {"nature": "doublage", "epaisseur_cm": 1.3, "indice": ""}
    assert enveloppe.avec_doublage_presume([voile, lu]) == [voile, lu]  # doublage lu : il prime
    brut = {"catalogue": [{"id": "X1", "genre": "element_exterieur", "decision": "exclu", "couches": [voile]},
                          {"id": "P3", "genre": "paroi", "decision": "a_confirmer", "couches": [voile]}],
            "elements": [{"type": "paroi", "composant": "P3", "couches": []}]}
    resolu = enveloppe.resoudre(brut)
    assert resolu["elements"][0]["couches"][-1]["presume"]
    assert resolu["catalogue"][0]["couches"] == [voile]
    assert enveloppe.role_couche([voile, isolant, voile], 2) == "voile intérieur"
    assert enveloppe.role_couche([voile], 0) == "voile"


def test_guide_raster_suit_une_dent_de_scie_fermee_par_une_rive():
    analyse = _analyse()
    page = Image.new("L", (2000, 1000), 255)
    dessin = ImageDraw.Draw(page)
    x0, y0 = 200, 200
    x1, y1 = 200 + 10 * PX_PAR_M + 12, 200 + 5 * PX_PAR_M
    epaisseur = round(0.3 * PX_PAR_M)
    # murs épais pleins autour des deux pièces
    dessin.rectangle((x0 - epaisseur, y0 - epaisseur, x1 + epaisseur, y0), fill=0)
    dessin.rectangle((x0 - epaisseur, y1, x1 + epaisseur, y1 + epaisseur), fill=0)
    dessin.rectangle((x1, y0, x1 + epaisseur, y1), fill=0)
    # façade ouest : deux voiles séparés par une poche d'1 m de profondeur, fermée dehors par une rive fine
    dessin.rectangle((x0 - epaisseur, y0, x0, y0 + 1.5 * PX_PAR_M), fill=0)
    dessin.rectangle((x0 - epaisseur, y0 + 3.5 * PX_PAR_M, x0, y1), fill=0)
    dessin.line((x0, y0 + 1.5 * PX_PAR_M, x0, y0 + 3.5 * PX_PAR_M), fill=0, width=3)  # vitrage au nu intérieur
    rive = x0 - round(1.0 * PX_PAR_M)
    dessin.line((rive, y0 - epaisseur, rive, y1 + epaisseur), fill=0, width=1)
    dessin.line((rive, y0 - epaisseur, x0 - epaisseur, y0 - epaisseur), fill=0, width=1)
    dessin.line((rive, y1 + epaisseur, x0 - epaisseur, y1 + epaisseur), fill=0, width=1)

    guide = enveloppe.contour_guide(analyse, 2000, 1000, PX_PAR_M, page)

    assert guide["methode"] == "remplissage_exterieur"
    milieu_poche = (x0 - 0.5 * PX_PAR_M, y0 + 2.5 * PX_PAR_M)
    assert not guide["polygone"].contains(Point(milieu_poche))  # la poche est extérieure
    assert guide["polygone"].contains(Point(x0 - 0.15 * PX_PAR_M, y0 + 0.5 * PX_PAR_M))  # le voile est dans le volume


def test_epaisseurs_ramenees_a_la_gamme_commerciale():
    assert enveloppe.epaisseur_commerciale("isolant", 13) == 12
    assert enveloppe.epaisseur_commerciale("isolant", 17) == 16
    assert enveloppe.epaisseur_commerciale("mur", 19) == 18
    assert enveloppe.epaisseur_commerciale("lame_air", 3) == 3  # pas de gamme : lu tel quel


def test_catalogue_fusionne_et_couches_reprises_de_la_fiche():
    p1 = {"id": "P1", "nom": "double mur", "genre": "paroi", "decision": "integre", "regle": "alvéoles",
          "couches": [{"nature": "mur", "epaisseur_cm": 12, "indice": ""}, {"nature": "isolant", "epaisseur_cm": 13, "indice": ""}],
          "premiere_vue": {"troncon": "T01", "debut_m": 0, "fin_m": 1}}
    catalogue = enveloppe.fusionner_catalogue([p1], [{**p1, "nom": "double mur isolé"}, {**p1, "id": "X1", "genre": "element_exterieur"}])
    assert [f["id"] for f in catalogue] == ["P1", "X1"] and catalogue[0]["nom"] == "double mur isolé"

    brut = {"catalogue": catalogue, "elements": [{"troncon": "T01", "debut_m": 0, "fin_m": 2, "type": "paroi", "composant": "P1",
                                                   "couches": [], "nu_exterieur_cm": 0, "nu_interieur_cm": -25}]}
    assert enveloppe.resoudre(brut)["elements"][0]["couches"] == p1["couches"]
    synthese = enveloppe.synthese_catalogue(brut)
    assert synthese[0]["lineaire_m"] == 2 and synthese[0]["composition_retenue"] == "mur 12 + isolant 12"


def test_massif_d_epaisseur_variable_cale_ses_couches_sur_le_nu_interieur():
    element = {"nu_exterieur_cm": 0, "nu_interieur_cm": -10, "nu_exterieur_fin_cm": 0, "nu_interieur_fin_cm": -70,
               "couches": [{"nature": "mur", "epaisseur_cm": 30}, {"nature": "isolant", "epaisseur_cm": 12},
                           {"nature": "mur", "epaisseur_cm": 12}]}
    couches = enveloppe.couches_positionnees(element)
    isolant = couches[1]
    assert isolant[1:] == (0, -5, -46, -58)  # longe la face intérieure en biais, comprimé au départ
    assert couches[0][1] == 0 and couches[0][3] == 0  # le massif absorbe la variation


def test_paroi_droite_en_biais_garde_ses_couches_depuis_le_nu_exterieur():
    element = {"nu_exterieur_cm": 0, "nu_interieur_cm": -44, "nu_exterieur_fin_cm": -20, "nu_interieur_fin_cm": -64,
               "couches": [{"nature": "mur", "epaisseur_cm": 12}, {"nature": "isolant", "epaisseur_cm": 12},
                           {"nature": "mur", "epaisseur_cm": 20}]}
    assert enveloppe.couches_positionnees(element)[1][1:] == (-12, -24, -32, -44)


def test_massif_trop_mince_comprime_ses_couches_sans_deborder():
    element = {"nu_exterieur_cm": 0, "nu_interieur_cm": -8, "nu_exterieur_fin_cm": 0, "nu_interieur_fin_cm": -70,
               "couches": [{"nature": "mur", "epaisseur_cm": 30}, {"nature": "isolant", "epaisseur_cm": 12},
                           {"nature": "mur", "epaisseur_cm": 12}]}
    for _couche, haut, bas, haut_fin, bas_fin in enveloppe.couches_positionnees(element):
        assert -8 <= bas <= haut <= 0 and -70 <= bas_fin <= haut_fin <= 0
