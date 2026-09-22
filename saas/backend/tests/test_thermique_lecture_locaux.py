"""Essai de lecture de l'enveloppe par local (D42 à D45)."""
from shapely.geometry import Polygon

from app.services import thermique_lecture_locaux as lecture
from app.services import thermique_parcours_enveloppe as enveloppe

PX = 100.0  # px par m


def _analyse() -> dict:
    # deux locaux chauffés côte à côte (repère feuille 0..1000 sur une page de 1000 px) : 4 m × 3 m chacun
    return {
        "objects": [
            {"category": "piece", "subtype": "A", "points": [[100, 100], [500, 100], [500, 400], [100, 400]]},
            {"category": "piece", "subtype": "B", "points": [[520, 100], [920, 100], [920, 400], [520, 400]]},
        ]
    }


def test_bande_par_defaut_et_par_local():
    assert enveloppe.bande_m({}) == (enveloppe.BANDE_INTERIEURE_M, enveloppe.BANDE_EXTERIEURE_M)
    assert enveloppe.bande_m({"bande_m": {"interieure": 0.4, "exterieure": 0.9}}) == (0.4, 0.9)


def test_lots_des_cotes_sur_local_non_chauffe_a_part():
    planches = [{"chemin": f"p{k}", "troncons": [], "complement": k >= 4} for k in range(6)]
    lots = enveloppe.lots({"planches": planches})
    assert [[p["chemin"] for p in lot] for lot in lots] == [["p0", "p1", "p2"], ["p3"], ["p4", "p5"]]


def test_un_troncon_par_cote_deperditif_sans_le_mitoyen():
    batiment = Polygon([(80, 80), (940, 80), (940, 420), (80, 420)])
    troncons = lecture.troncons_par_local(_analyse(), 1000, 1000, PX, batiment)
    par_local = {}
    for t in troncons:
        par_local.setdefault(t["piece"], 0.0)
        par_local[t["piece"]] += t["local_fin_m"] - t["local_debut_m"]
        # la normale pointe hors du local, la ligne 0 est la face intérieure
        assert t["ligne"] == "face_interieure"
        assert t["local_fin_m"] - t["local_debut_m"] <= enveloppe.TRONCON_MAX_M + 1e-6
    # A : 4 + 3 + 4 m sur l'extérieur ; le côté mitoyen avec B (chauffé) n'est pas lu
    assert abs(par_local["A"] - 11.0) < 0.15
    assert abs(par_local["B"] - 11.0) < 0.15
