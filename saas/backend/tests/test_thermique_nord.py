"""Nord de la planche (D85) : le repère est le seul endroit où l'on peut se tromper."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.services import thermique_nord as nord

# Même matrice que les autres tests d'étude : px = 2x, py = -2y + 1000 (l'axe y du PDF monte).
TRANSFORM = [2, 0, 0, -2, 0, 1000]


def _fleche(dx: float, dy: float) -> dict:
    return nord.poser([100.0, 100.0], [100.0 + dx, 100.0 + dy])


@pytest.mark.parametrize(
    ("dx", "dy", "azimut", "lecture"),
    [
        (0, 50, 0, "vers le haut de la planche"),
        (50, 0, 90, "vers la droite de la planche"),
        (0, -50, 180, "vers le bas de la planche"),
        (-50, 0, 270, "vers la gauche de la planche"),
        (50, 50, 45, "vers le haut à droite"),
    ],
)
def test_la_fleche_se_lit_dans_le_repere_affiche(dx, dy, azimut, lecture):
    """Le thermicien trace la pointe du côté du nord ; l'angle se mesure depuis le haut de l'image."""
    mesure = nord.azimut_dans_l_image(_fleche(dx, dy), TRANSFORM)
    assert mesure == pytest.approx(azimut, abs=0.01)
    assert nord.lecture_en_clair(mesure) == lecture


def test_une_fleche_trop_courte_est_refusee():
    with pytest.raises(ValueError, match="trop courte"):
        nord.poser([100.0, 100.0], [102.0, 100.0])


@pytest.mark.parametrize(
    ("p1", "p2", "message"),
    [
        ([float("nan"), 10], [50, 50], "invalides"),
        ([-1, 10], [50, 50], "rester dans"),
        ([10, 10], [201, 50], "rester dans"),
    ],
)
def test_une_fleche_invalide_ou_hors_planche_est_refusee(p1, p2, message):
    with pytest.raises(ValueError, match=message):
        nord.poser(p1, p2, 200, 100)


def test_sans_nord_pose_il_n_y_a_pas_d_azimut():
    assert nord.azimut_dans_l_image(None, TRANSFORM) is None


def test_une_planche_tournee_ne_fausse_pas_le_nord():
    """La flèche est stockée en points PDF : tourner l'affichage tourne l'angle, pas la donnée.

    Rendu tourné d'un quart de tour : px = 2y, py = 2x. Une flèche qui pointait vers le haut de la
    feuille pointe alors vers la droite, et c'est bien ce que le calcul renvoie.
    """
    tournee = [0, 2, 2, 0, 0, 0]
    fleche = _fleche(0, 50)
    assert nord.azimut_dans_l_image(fleche, TRANSFORM) == pytest.approx(0, abs=0.01)
    assert nord.azimut_dans_l_image(fleche, tournee) == pytest.approx(90, abs=0.01)
    assert nord.lecture_en_clair(nord.azimut_dans_l_image(fleche, tournee)) == "vers la droite de la planche"


def test_la_direction_est_reancree_quand_le_format_de_page_change():
    source = nord.poser([900, 700], [980, 780], 1000, 800)
    cible = nord.adapter_a_planche(source, 1000, 800, 400, 1000)

    dx_source, dy_source = nord.vecteur_du_nord(source)
    dx_cible, dy_cible = nord.vecteur_du_nord(cible)
    assert dx_cible / dy_cible == pytest.approx(dx_source / dy_source)
    assert all(0 <= x <= 400 and 0 <= y <= 1000 for x, y in (cible["p1"], cible["p2"]))


def test_la_propagation_conserve_l_azimut_dans_un_meme_repere():
    source = nord.poser([100, 100], [160, 180], 1000, 800)
    cible = nord.adapter_a_planche(source, 1000, 800, 500, 500)
    assert nord.azimut_dans_l_image(source, TRANSFORM) == pytest.approx(
        nord.azimut_dans_l_image(cible, TRANSFORM), abs=0.01
    )


def test_une_valeur_corrompue_en_base_n_est_pas_exposee():
    sheet = SimpleNamespace(north_json='{"p1":[-10,0],"p2":[20,20]}', page_width_pt=100, page_height_pt=100)
    assert nord.charger(sheet) is None

    sheet.north_json = json.dumps(nord.poser([10, 10], [20, 50], 100, 100))
    assert nord.charger(sheet)["p2"] == [20.0, 50.0]
