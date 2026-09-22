"""Découpage de l'enveloppe pièce par pièce (D18 à D20)."""
import math

from app.services import thermique_enveloppe_pieces as pieces
from app.services import thermique_parcours_enveloppe as enveloppe
from tests.test_thermique_parcours_enveloppe import PX_PAR_M, _analyse


def _manifeste(analyse):
    guide = enveloppe.contour_guide(analyse, 2000, 1000, PX_PAR_M)
    return {"px_par_m": PX_PAR_M, "page_px": [2000, 1000], "troncons": enveloppe.troncons(guide, analyse, 2000, 1000, PX_PAR_M)}


def _element(troncon, debut, fin, genre="paroi", **autres):
    return {"troncon": troncon["id"], "debut_m": debut, "fin_m": fin, "type": genre, "nu_exterieur_cm": 44,
            "nu_interieur_cm": 0, "couches": [{"nature": "mur", "epaisseur_cm": 20, "indice": ""},
                                              {"nature": "isolant", "epaisseur_cm": 12, "indice": ""},
                                              {"nature": "mur", "epaisseur_cm": 12, "indice": ""}] if genre == "paroi" else [],
            "menuiserie_type": "fenêtre" if genre == "menuiserie" else "", "cadre_cm": 20, "confiance": 0.9, "indice": "",
            "a_verifier": False, **autres}


def test_paroi_coupee_au_droit_du_refend_et_ponts_partages():
    analyse = _analyse()
    manifeste = _manifeste(analyse)
    # façade nord : 3 tronçons de 3,37 m ; la cloison entre les deux bureaux tombe vers 5,05 m, dans le 2e
    t = manifeste["troncons"][1]
    limite = 5 + 0.05
    brut = {"catalogue": [], "observations": [], "elements": [
        _element(t, t["debut_m"], limite - 0.03),
        _element(t, limite - 0.03, limite + 0.03, "about_refend"),
        _element(t, limite + 0.03, t["fin_m"] - 1.2),
        _element(t, t["fin_m"] - 1.2, t["fin_m"], "menuiserie"),
    ]}

    decoupe = pieces.decouper_par_piece(brut, manifeste, analyse)

    parois = [e for e in decoupe["elements"] if e["type"] == "paroi"]
    assert [e["piece"] for e in parois] == ["Bureau A", "Bureau B"]
    about = next(e for e in decoupe["elements"] if e["type"] == "about_refend")
    assert about["pieces"] == [["Bureau A", 0.5], ["Bureau B", 0.5]]
    assert parois[0]["couches"][-1]["presume"]  # doublage BA13 présumé repris

    synthese = {f["piece"]: f for f in pieces.synthese_pieces(decoupe, manifeste)}
    a, b = synthese["Bureau A"], synthese["Bureau B"]
    assert math.isclose(a["parois"][0]["lineaire_m"], limite - 0.03 - t["debut_m"], abs_tol=0.01)
    assert a["ponts"]["about_refend"] == 0.5 and b["ponts"]["about_refend"] == 0.5
    assert b["menuiseries"][0]["largeurs_cm"] == [120]
    assert math.isclose(b["facade_m"], b["liaison_plancher_m"]) and b["facade_m"] > 1.2


def test_une_baie_a_cheval_sur_deux_pieces_est_coupee_et_recalee_sur_la_cloison():
    analyse = _analyse()
    manifeste = _manifeste(analyse)
    t = manifeste["troncons"][1]
    cloison = 5.05
    brut = {"catalogue": [], "observations": [], "elements": [
        _element(t, t["debut_m"], 4.0),
        _element(t, 4.0, 6.0, "menuiserie"),
        _element(t, 6.0, t["fin_m"]),
        # about de cloison relevé à 5,15 m : la coupe s'y recale (le sondage la place vers 5,05 m)
        _element(t, 5.13, 5.17, "about_refend"),
    ]}

    decoupe = pieces.decouper_par_piece(brut, manifeste, analyse)

    baies = [e for e in decoupe["elements"] if e["type"] == "menuiserie"]
    assert [e["piece"] for e in baies] == ["Bureau A", "Bureau B"]
    assert math.isclose(baies[0]["fin_m"], 5.15) and math.isclose(baies[1]["debut_m"], 5.15)
    assert abs(cloison - baies[0]["fin_m"]) <= pieces.RECALAGE_M


def test_angle_a_la_piece_qui_le_contient_et_elements_exclus_ignores():
    analyse = _analyse()
    manifeste = _manifeste(analyse)
    nord = manifeste["troncons"][0]
    brut = {"catalogue": [{"id": "X1", "genre": "element_exterieur", "decision": "exclu", "couches": []}],
            "observations": [], "elements": [
                _element(nord, nord["debut_m"], nord["debut_m"] + 0.4, "angle_sortant"),
                _element(nord, nord["debut_m"] + 0.4, nord["debut_m"] + 2, "indetermine", composant="X1"),
            ]}

    synthese = pieces.synthese_pieces(pieces.decouper_par_piece(brut, manifeste, analyse), manifeste)

    assert synthese == [{"piece": "Bureau A", "parois": [], "menuiseries": [], "poteaux": 0,
                         "ponts": {"angle_sortant": 1.0, "angle_rentrant": 0.0, "about_refend": 0.0},
                         "facade_m": 0.0, "liaison_plancher_m": 0.0}]


def test_pieces_homonymes_restent_distinctes():
    analyse = _analyse()
    for objet in analyse["objects"]:
        objet["subtype"] = "B.asst"
    noms = [nom for nom, _ in pieces.pieces_du_plan(analyse, 2000, 1000)]
    assert noms == ["B.asst (1)", "B.asst (2)"]


def _angle_rentrant(genre_apres="paroi", interieur_apres=-20):
    # parcours horaire : vers l'est puis vers le nord ; le bâtiment est au sud du 1er côté et à l'est du 2e
    t1 = {"id": "T01", "origine_px": [0, 0], "direction": [1, 0], "normale_ext": [0, -1], "debut_m": 0, "fin_m": 3,
          "local_debut_m": 0}
    t2 = {"id": "T02", "origine_px": [3 * PX_PAR_M, 0], "direction": [0, -1], "normale_ext": [-1, 0], "debut_m": 3,
          "fin_m": 6, "local_debut_m": 0}
    manifeste = {"px_par_m": PX_PAR_M, "page_px": [2000, 1000], "troncons": [t1, t2], "perimetre_m": 6}
    paroi = {"type": "paroi", "nu_exterieur_cm": 0, "nu_interieur_cm": -20, "couches": []}
    brut = {"catalogue": [], "elements": [
        {**paroi, "troncon": "T01", "debut_m": 0, "fin_m": 3},
        {**paroi, "type": genre_apres, "troncon": "T02", "debut_m": 3, "fin_m": 6, "nu_interieur_cm": interieur_apres,
         "nu_interieur_fin_cm": -20},
    ]}
    return brut, manifeste


def test_angle_rentrant_prolonge_les_faces_interieures_de_l_epaisseur_du_mur():
    brut, manifeste = _angle_rentrant()

    raccords = pieces.raccorder_faces(brut, manifeste)

    assert [r["nature"] for r in raccords] == ["rentrant"]
    assert math.isclose(raccords[0]["allongement_m"], 0.4, abs_tol=0.005)  # 20 cm de chaque côté
    avant, apres = brut["elements"]
    coin = (3.2 * PX_PAR_M, 0.2 * PX_PAR_M)
    assert math.dist(avant["face_px"][1], coin) < 0.5 and math.dist(apres["face_px"][0], coin) < 0.5
    assert math.isclose(pieces.longueur_interieure(avant, manifeste["troncons"][0], PX_PAR_M), 3.2, abs_tol=0.01)


def test_un_mur_contre_une_baie_n_est_pas_raccorde_et_un_releve_incoherent_est_refuse():
    brut, manifeste = _angle_rentrant(genre_apres="menuiserie")
    assert pieces.raccorder_faces(brut, manifeste) == []  # le mur s'arrête au tableau

    brut, manifeste = _angle_rentrant(interieur_apres=-60)  # 60 cm d'un côté, 20 de l'autre : relevé à revoir
    raccords = pieces.raccorder_faces(brut, manifeste)
    assert [r["nature"] for r in raccords] == ["refusé"]
    assert math.isclose(pieces.longueur_interieure(brut["elements"][0], manifeste["troncons"][0], PX_PAR_M), 3.0)


def test_demande_de_decoupage_pour_un_espace_qui_regroupe_plusieurs_locaux():
    synthese = [{"piece": "4.2 Pôle (inclut 4.3 Musique)", "facade_m": 12.0},
                {"piece": "Bureau", "facade_m": 3.0}, {"piece": "Hall", "facade_m": 45.0}]
    demandes = pieces.demandes_etude(synthese)
    assert [d["piece"] for d in demandes] == ["4.2 Pôle (inclut 4.3 Musique)", "Hall"]
    assert all(d["objet"] == "Découpage précis des zones" for d in demandes)


def test_longueur_interieure_d_une_paroi_en_biais():
    troncon = {"id": "T01", "origine_px": [0, 0], "direction": [1, 0], "normale_ext": [0, -1],
               "debut_m": 0, "fin_m": 3, "local_debut_m": 0}
    element = {"debut_m": 0, "fin_m": 3, "nu_exterieur_cm": 40, "nu_interieur_cm": 0,
               "nu_exterieur_fin_cm": 0, "nu_interieur_fin_cm": -40}
    assert math.isclose(pieces.longueur_interieure(element, troncon, PX_PAR_M), math.hypot(3, 0.4), rel_tol=1e-6)
