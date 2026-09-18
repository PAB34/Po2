"""Un local est un quadrilatère (docs/thermique/parois-et-motifs-decisions.md §0.6, règle des 98 %)."""
from __future__ import annotations

import math

import pytest

from thermique_moteur import quadrilatere

M = 1000 / 50 / (25.4 / 72)  # points PDF pour 1 m à 1/50


def _plat(points):
    return [c * M for point in points for c in point]


def _points(contour):
    return [(contour[k] / M, contour[k + 1] / M) for k in range(0, len(contour) - 1, 2)]


def test_un_rectangle_reste_lui_meme():
    contour = _plat([(0, 0), (6, 0), (6, 4), (0, 4)])
    coins = sorted(_points(quadrilatere.simplifier(contour, M)))
    assert coins == pytest.approx([(0, 0), (0, 4), (6, 0), (6, 4)], abs=0.01)


def test_les_petits_decrochements_disparaissent():
    """Tableaux de portes et redans : le contour relevé a douze sommets, le local en a quatre."""
    contour = _plat(
        [
            (0, 0), (2.4, 0), (2.4, 0.12), (3.3, 0.12), (3.3, 0), (6, 0),
            (6, 2.1), (5.88, 2.1), (5.88, 2.9), (6, 2.9), (6, 4), (0, 4),
        ]
    )
    simplifie = quadrilatere.simplifier(contour, M)
    assert len(simplifie) == 8
    coins = sorted(_points(simplifie))
    assert coins == pytest.approx([(0, 0), (0, 4), (6, 0), (6, 4)], abs=0.02)
    assert quadrilatere.aire(_points(simplifie)) == pytest.approx(24.0, abs=0.1)


def test_un_local_en_biais_garde_son_angle():
    angle = math.radians(17)
    c, s = math.cos(angle), math.sin(angle)
    coins = [(0, 0), (7, 0), (7, 5), (0, 5)]
    tournes = [(x * c - y * s, x * s + y * c) for x, y in coins]
    simplifie = quadrilatere.simplifier(_plat(tournes), M)
    assert quadrilatere.aire(_points(simplifie)) == pytest.approx(35.0, abs=0.2)


def test_un_local_en_L_est_garde_tel_quel():
    """La règle ne vaut que pour les 98 % : un local en L ne se ramène pas à quatre côtés."""
    contour = _plat([(0, 0), (8, 0), (8, 3), (4, 3), (4, 7), (0, 7)])
    with pytest.raises(quadrilatere.QuadrilatereError):
        quadrilatere.simplifier(contour, M)


def test_un_contour_qui_fuit_par_une_baie_est_rattrape():
    """Le tracé s'échappe sur 1,5 m par une baie non désignée : les quatre grandes droites le ramènent."""
    contour = _plat(
        [
            (0, 0), (6, 0), (6, 4), (4.5, 4), (4.5, 5.2), (3.0, 5.2), (3.0, 4), (0, 4),
        ]
    )
    simplifie = quadrilatere.simplifier(contour, M)
    assert len(simplifie) == 8
    assert quadrilatere.aire(_points(simplifie)) == pytest.approx(24.0, abs=0.5)


def test_un_triangle_n_a_pas_quatre_cotes():
    with pytest.raises(quadrilatere.QuadrilatereError, match="quatre directions"):
        quadrilatere.simplifier(_plat([(0, 0), (6, 0), (3, 5)]), M)


def test_un_grand_espace_perd_ses_zigzags_sans_perdre_sa_forme_en_l():
    contour = _plat(
        [
            (0, 0), (2, 0.06), (4, -0.04), (6, 0.05), (8, -0.03), (10, 0.04), (12, 0),
            (12.04, 2), (11.96, 4), (10, 4.05), (8, 4), (8.04, 6), (8, 8),
            (6, 8.05), (4, 7.95), (2, 8.04), (0, 8), (-0.04, 6), (0.03, 4), (-0.02, 2),
        ]
    )
    simplifie = quadrilatere.simplifier_adaptatif(contour, M)
    points = _points(simplifie)
    assert 5 <= len(points) <= 8
    assert quadrilatere.aire(points) == pytest.approx(80.0, abs=1.0)
    assert any(math.dist(point, (8, 8)) < 0.1 for point in points)


def test_un_contour_croise_n_est_jamais_corrige_automatiquement():
    with pytest.raises(quadrilatere.QuadrilatereError, match="invalide"):
        quadrilatere.simplifier_adaptatif(_plat([(0, 0), (6, 4), (0, 4), (6, 0)]), M)


def test_un_contour_tres_bruite_reste_corrigeable_a_la_main():
    forme = [(0, 0), (12, 0), (12, 4), (8, 4), (8, 8), (0, 8)]
    points = []
    for a, b in zip(forme, forme[1:] + forme[:1]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        longueur = math.hypot(dx, dy)
        nx, ny = -dy / longueur, dx / longueur
        for rang in range(8):
            t = rang / 8
            bruit = 0 if rang == 0 else (0.08 if rang % 2 else -0.08)
            points.append((a[0] + t * dx + bruit * nx, a[1] + t * dy + bruit * ny))
    simplifie = _points(quadrilatere.simplifier_adaptatif(_plat(points), M))
    assert len(simplifie) <= quadrilatere.SOMMETS_BRUITES
    assert quadrilatere.aire(simplifie) == pytest.approx(80.0, abs=1.0)
