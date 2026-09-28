"""Remarque E (D160) : l'angle réel d'un angle sortant ou rentrant, et la minoration qu'il vaut à ψ."""
from __future__ import annotations

import math

import pytest

from app.services import thermique_angles as angles
from app.services import thermique_elements as elements_releve
from app.services.thermique import ThermiqueError


def _troncon(identifiant: str, debut: float, fin: float, cap_deg: float, **reste) -> dict:
    cap = math.radians(cap_deg)
    return {"id": identifiant, "debut_m": debut, "fin_m": fin, "direction": [math.cos(cap), math.sin(cap)], **reste}


def _manifeste(*troncons: dict, perimetre: float = 0.0) -> dict:
    return {"troncons": list(troncons), "perimetre_m": perimetre}


def _angle(troncon: str, debut: float, fin: float, **reste) -> dict:
    return {"type": "angle_sortant", "troncon": troncon, "debut_m": debut, "fin_m": fin, **reste}


# Un carré de 10 m : quatre angles droits, la façade se referme sur elle-même.
CARRE = _manifeste(
    _troncon("T01", 0, 10, 0), _troncon("T02", 10, 20, 90), _troncon("T03", 20, 30, 180), _troncon("T04", 30, 40, 270),
    perimetre=40.0,
)


def test_un_angle_droit_vaut_90_et_garde_son_psi():
    element = _angle("T01", 9.75, 10.0)
    assert angles.angle_mesure(element, CARRE) == 90.0
    assert angles.coefficient(angles.angle_retenu(element, CARRE)) == 1.0


def test_la_facade_se_referme_le_premier_angle_se_lit_avec_le_dernier_troncon():
    assert angles.angle_mesure(_angle("T01", 0.0, 0.25), CARRE) == 90.0


def test_un_pan_coupe_a_45_degres_perd_la_moitie_de_son_psi():
    manifeste = _manifeste(_troncon("T01", 0, 10, 0), _troncon("T02", 10, 20, 45), perimetre=0.0)
    element = _angle("T01", 9.8, 10.0)
    assert angles.angle_mesure(element, manifeste) == 45.0
    assert angles.coefficient(45.0) == 0.5


def test_un_angle_loin_de_toute_jonction_ne_se_devine_pas():
    assert angles.angle_mesure(_angle("T01", 4.0, 4.2), CARRE) is None


def test_un_troncon_interieur_isole_n_a_pas_de_voisin():
    manifeste = _manifeste(
        _troncon("U01", 100, 103, 0, ligne="face_interieure"), _troncon("U02", 110, 112, 90, ligne="face_interieure")
    )
    assert angles.angle_mesure(_angle("U01", 102.8, 103.0), manifeste) is None


def test_un_pont_pose_a_la_main_ne_se_mesure_pas_il_se_saisit():
    pose = _angle("T01", 9.9, 9.9, point_feuille=[10.0, 10.0])
    assert angles.angle_mesure(pose, CARRE) is None
    assert angles.angle_retenu({**pose, "angle_deg": 60.0}, CARRE) == 60.0
    # Sans angle connu, on garde l'angle droit du catalogue plutôt que d'annuler le pont.
    assert angles.coefficient(None) == 1.0


def test_l_angle_saisi_l_emporte_sur_la_mesure():
    assert angles.angle_retenu(_angle("T01", 9.75, 10.0, angle_deg=30.0), CARRE) == 30.0


def test_l_angle_se_corrige_entre_0_et_180_et_seulement_sur_un_angle():
    contenu = {"enveloppe": {"releve_brut": {"elements": [
        _angle("T01", 9.75, 10.0, nu_exterieur_cm=0, nu_interieur_cm=-30),
        {"type": "paroi", "troncon": "T01", "debut_m": 0.0, "fin_m": 9.75, "nu_exterieur_cm": 0, "nu_interieur_cm": -30},
    ]}}}
    ref = {"troncon": "T01", "debut_m": 9.75, "fin_m": 10.0}
    corrige = elements_releve.corriger(contenu, ref, {"angle_deg": 45})
    assert corrige[0]["angle_deg"] == 45.0
    with pytest.raises(ThermiqueError, match="entre 0 et 180"):
        elements_releve.corriger(contenu, ref, {"angle_deg": 200})
    with pytest.raises(ThermiqueError, match="Seul un angle"):
        elements_releve.corriger(contenu, {"troncon": "T01", "debut_m": 0.0, "fin_m": 9.75}, {"angle_deg": 45})
