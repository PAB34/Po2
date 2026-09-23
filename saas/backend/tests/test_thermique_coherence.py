"""Contrôle de cohérence de fin de chaîne (D77).

Chaque test prend le défaut que le contrôle doit attraper et vérifie qu'il ne passe plus en silence.
Le premier est celui qui a motivé la décision : un contour qui mord dans une paroi mesurée.
"""
from __future__ import annotations

import pytest

from app.services import thermique_coherence as coherence

# Même repère que les autres tests du lot : page de 1000 x 1000 px, 10 px par mètre, bâtiment de 100 m.
MANIFESTE = {
    "page_px": [1000, 1000],
    "px_par_m": 10,
    "batiment_px": [[0, 0], [1000, 0], [1000, 1000], [0, 1000]],
    "trous_px": [],
    "troncons": [
        {
            "id": "T01",
            "debut_m": 0.0,
            "local_debut_m": 0.0,
            "origine_px": [0, 0],
            "direction": [1.0, 0.0],
            "normale_ext": [0.0, -1.0],
        }
    ],
}

RELEVE = {
    "elements": [
        {
            "troncon": "T01",
            "debut_m": 0.0,
            "fin_m": 100.0,
            "type": "paroi",
            "composant": "P1",
            "nu_exterieur_cm": 0,
            "nu_interieur_cm": -50,
            "confiance": 0.9,
            "a_verifier": False,
            "indice": "mur",
        }
    ],
    "catalogue": [],
    "observations": [],
}


def _piece(identifiant: str, points: list[list[float]], nom: str) -> dict:
    return {
        "id": identifiant,
        "category": "piece",
        "subtype": nom,
        "geometry_type": "polygon",
        "local": "chauffe",
        "points": points,
    }


def _local(identifiant: str, nom: str, contour: list[list[float]], cotes=None, facade_m: float | None = None) -> dict:
    return {
        "id": identifiant,
        "nom": nom,
        "nature": "chauffe",
        "contour": contour,
        "fiche": {"piece": nom, "cotes": cotes or [], "alertes": []},
        "synthese": {"piece": nom, "facade_m": facade_m} if facade_m is not None else {},
    }


def _contenu(objets: list[dict], locaux: list[dict], couverture: dict | None = None, releve=RELEVE) -> dict:
    return {
        "niveau": "R1",
        "analyse": {"objects": objets},
        "enveloppe": {"manifeste": MANIFESTE, "releve_brut": releve},
        "locaux": locaux,
        "couverture": couverture or {"surface_non_affectee_m2": 0.0, "zones_non_affectees": [],
                                     "chevauchements": [], "chevauchement_m2": 0.0, "taux_couverture_pct": 100.0},
    }


def _anomalies(rapport: dict, code: str) -> list[dict]:
    return next(controle["anomalies"] for controle in rapport["controles"] if controle["code"] == code)


def test_un_contour_qui_mord_dans_une_paroi_mesuree_est_signale():
    # Le local monte jusqu'au nu extérieur : il avale les 50 cm de mur relevés sur tout le bord nord.
    contour = [[0, 0], [1000, 0], [1000, 500], [0, 500]]
    rapport = coherence.controler_niveau(
        _contenu([_piece("piece-001", contour, "Bureau")], [_local("piece-001", "Bureau", contour)])
    )
    morsures = _anomalies(rapport, "morsure_paroi")
    assert len(morsures) == 1
    assert morsures[0]["local"] == "piece-001"
    assert morsures[0]["deplacement_m"] == pytest.approx(0.5, abs=0.05)
    assert rapport["statut"] == "attention"


def test_un_contour_deja_cale_ne_declenche_plus_rien():
    # Même local, posé au nu intérieur : le contrôle rejoué sur un fichier calé doit se taire.
    contour = [[0, 6], [1000, 6], [1000, 500], [0, 500]]
    rapport = coherence.controler_niveau(
        _contenu([_piece("piece-001", contour, "Bureau")], [_local("piece-001", "Bureau", contour)])
    )
    assert _anomalies(rapport, "morsure_paroi") == []


def test_la_couverture_et_les_recouvrements_remontent_dans_le_rapport():
    contour = [[0, 6], [500, 6], [500, 500], [0, 500]]
    couverture = {
        "surface_non_affectee_m2": 31.0,
        "zones_non_affectees": [[[0, 0], [1, 0], [1, 1]]] * 10,
        "chevauchements": [{"locaux": ["piece-001", "piece-002"], "surface_m2": 10.85}],
        "chevauchement_m2": 10.85,
        "taux_couverture_pct": 92.5,
    }
    rapport = coherence.controler_niveau(
        _contenu(
            [_piece("piece-001", contour, "Bureau")],
            [_local("piece-001", "Bureau", contour), _local("piece-002", "Atrium", contour)],
            couverture,
        )
    )
    manques = _anomalies(rapport, "couverture")
    assert len(manques) == 1 and manques[0]["surface_m2"] == 31.0 and manques[0]["zones"] == 10
    recouvrements = _anomalies(rapport, "chevauchement")
    assert len(recouvrements) == 1
    # Le message nomme les locaux : c'est ce que le thermicien lit, pas leur identifiant technique.
    assert "Bureau" in recouvrements[0]["message"] and "Atrium" in recouvrements[0]["message"]


def test_un_local_pose_hors_du_batiment_est_signale():
    # Le bâtiment ne couvre que la moitié gauche de la feuille : ce local est posé à côté.
    contenu = _contenu([], [])
    contenu["enveloppe"]["manifeste"] = {**MANIFESTE, "batiment_px": [[0, 0], [500, 0], [500, 1000], [0, 1000]]}
    contour = [[600, 100], [800, 100], [800, 300], [600, 300]]
    contenu["analyse"]["objects"] = [_piece("piece-001", contour, "Terrasse")]
    contenu["locaux"] = [_local("piece-001", "Terrasse", contour)]
    rapport = coherence.controler_niveau(contenu)
    debords = _anomalies(rapport, "debord_emprise")
    assert len(debords) == 1 and debords[0]["surface_m2"] > 0.5


def test_les_deux_lectures_d_une_meme_facade_sont_confrontees():
    # 20 m de côtés extérieurs au contour contre 12 m de façade relevée : l'une des deux lectures se trompe.
    contour = [[0, 6], [1000, 6], [1000, 500], [0, 500]]
    cotes = [{"adjacence": "exterieur", "longueur_m": 20.0, "enveloppe": [{"composant": "P1", "lineaire_m": 20.0}]}]
    rapport = coherence.controler_niveau(
        _contenu(
            [_piece("piece-001", contour, "Bureau")],
            [_local("piece-001", "Bureau", contour, cotes, facade_m=12.0)],
        )
    )
    ecarts = _anomalies(rapport, "ecart_facade")
    assert len(ecarts) == 1 and ecarts[0]["ecart_m"] == pytest.approx(8.0, abs=0.01)


def test_un_cote_exterieur_sans_enveloppe_et_une_enveloppe_sans_local_sont_vus():
    # Le local est au milieu de la page : le mur nord relevé n'a aucun local en regard, et son côté
    # extérieur déclaré n'a aucun élément d'enveloppe rattaché.
    contour = [[300, 300], [700, 300], [700, 700], [300, 700]]
    cotes = [{"adjacence": "exterieur", "longueur_m": 4.0, "enveloppe": []}]
    rapport = coherence.controler_niveau(
        _contenu(
            [_piece("piece-001", contour, "Bureau")],
            [_local("piece-001", "Bureau", contour, cotes)],
        )
    )
    orphelins = _anomalies(rapport, "enveloppe_orpheline")
    sens = {anomalie["sens"] for anomalie in orphelins}
    assert sens == {"cote_sans_element", "element_sans_cote"}


def test_un_niveau_sans_defaut_se_dit_conforme():
    contour = [[0, 6], [1000, 6], [1000, 500], [0, 500]]
    cotes = [{"adjacence": "exterieur", "longueur_m": 100.0, "enveloppe": [{"composant": "P1", "lineaire_m": 100.0}]}]
    rapport = coherence.controler_niveau(
        _contenu(
            [_piece("piece-001", contour, "Bureau")],
            [_local("piece-001", "Bureau", contour, cotes, facade_m=100.0)],
        )
    )
    assert rapport["statut"] == "ok" and rapport["anomalies"] == 0
    assert "rien à signaler" in "\n".join(coherence.rapport_markdown(rapport))


def test_sans_releve_le_controle_des_parois_se_declare_impossible():
    contour = [[0, 6], [1000, 6], [1000, 500], [0, 500]]
    rapport = coherence.controler_niveau(
        _contenu(
            [_piece("piece-001", contour, "Bureau")],
            [_local("piece-001", "Bureau", contour)],
            releve={"elements": [], "catalogue": [], "observations": []},
        )
    )
    controle = next(c for c in rapport["controles"] if c["code"] == "morsure_paroi")
    assert controle["anomalies"] == [] and "impossible" in controle["resume"]
