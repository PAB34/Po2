"""Contrôle du relevé de l'enveloppe par l'image (alvéoles d'isolant, béton)."""
from PIL import Image, ImageDraw

from app.services import thermique_controle_image as controle
from app.services import thermique_parcours_enveloppe as enveloppe
from tests.test_thermique_parcours_enveloppe import PX_PAR_M, _analyse


def _page_avec_mur_isole(x_fin_isolant):
    """Mur nord sous la limite des pièces (y = 200) : 44 cm de gris, rangée d'alvéoles blanches à 15-25 cm."""
    page = Image.new("L", (2000, 1000), 255)
    dessin = ImageDraw.Draw(page)
    dessin.rectangle((150, 200, 1500, 200 + round(0.44 * PX_PAR_M)), fill=152)
    y0, y1 = 200 + round(0.16 * PX_PAR_M), 200 + round(0.24 * PX_PAR_M)
    for x in range(160, x_fin_isolant, 12):
        dessin.rectangle((x, y0, x + 8, y1), fill=255)  # alvéoles séparées par des traits gris
    return page


def _releve(troncons, isole_jusqu_a_m):
    couches = [{"nature": "mur", "epaisseur_cm": 12, "indice": ""}, {"nature": "isolant", "epaisseur_cm": 12, "indice": ""},
               {"nature": "mur", "epaisseur_cm": 20, "indice": ""}]
    elements = []
    for t in troncons[:3]:  # façade nord
        elements.append({"troncon": t["id"], "debut_m": t["debut_m"], "fin_m": t["fin_m"], "type": "paroi",
                         "composant": "P1", "nu_exterieur_cm": 0, "nu_interieur_cm": -44, "couches": []})
    catalogue = [{"id": "P1", "genre": "paroi", "decision": "integre", "couches": couches}]
    return {"catalogue": catalogue, "elements": elements, "observations": []}


def _manifeste():
    analyse = _analyse()
    guide = enveloppe.contour_guide(analyse, 2000, 1000, PX_PAR_M)
    troncons = enveloppe.troncons(guide, analyse, 2000, 1000, PX_PAR_M)
    return {"px_par_m": PX_PAR_M, "page_px": [2000, 1000], "troncons": troncons}


def test_les_alveoles_sont_trouvees_et_confirment_l_isolant_compte():
    manifeste = _manifeste()
    page = _page_avec_mur_isole(1400)
    brut = _releve(manifeste["troncons"], 10)

    bilan = controle.controler(page, manifeste, brut)

    p1 = next(ligne for ligne in bilan["composants"] if ligne["composant"] == "P1")
    assert p1["beton_pct"] > 90 and p1["confirme_pct"] > 90
    assert p1["isolant_pct"] > 85
    assert bilan["isolant"]["taux_compte_pct"] > 90


def test_isolant_compte_mais_absent_de_l_image_est_signale():
    manifeste = _manifeste()
    page = _page_avec_mur_isole(160 + round(4 * PX_PAR_M))  # alvéoles sur les 4 premiers mètres seulement
    brut = _releve(manifeste["troncons"], 10)

    bilan = controle.controler(page, manifeste, brut)

    non_vus = bilan["isolant"]["non_vus"]
    assert non_vus and sum(s["fin_m"] - s["debut_m"] for s in non_vus) > 4
    assert controle.troncons_a_montrer(bilan)[0] in {t["id"] for t in manifeste["troncons"][1:3]}


def test_une_lettre_cernee_de_noir_n_est_pas_une_alveole():
    bande = Image.new("L", (400, 300), 255)
    dessin = ImageDraw.Draw(bande)
    for x in range(20, 380, 30):
        dessin.rectangle((x, 100, x + 20, 120), outline=0, width=3)  # cases cernées de noir (texte, mobilier)
    import numpy as np

    assert controle.cellules_isolant(np.asarray(bande), PX_PAR_M * enveloppe.AGRANDISSEMENT) == []
