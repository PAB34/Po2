"""Lignes redressées sur les faces vectorielles (docs/thermique/refondation-parcours-decisions.md §17)."""
from __future__ import annotations

import math

import numpy as np
import pytest

from thermique_moteur.redressement import redresser

M = 1000 / 50 / (25.4 / 72)  # points PDF pour 1 m à 1/50
M_PAR_PT = 1 / M


def _tremble(x0, y0, x1, y1, pas=0.05, ampl=0.03):
    """Contour d'un rectangle qui oscille de ± 3 cm autour des faces, un sommet tous les 5 cm."""
    points = []
    for (ax, ay), (bx, by) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        n = int(math.hypot(bx - ax, by - ay) / pas)
        nx, ny = -(by - ay), bx - ax
        norme = math.hypot(nx, ny)
        for k in range(n):
            t = k / n
            decalage = ampl * (1 if k % 4 < 2 else -1)
            points.append(((ax + (bx - ax) * t + nx / norme * decalage) * M, (ay + (by - ay) * t + ny / norme * decalage) * M))
    return points


FACES = np.array(
    [
        [0, 0, 6 * M, 0],
        [6 * M, 0, 6 * M, 4 * M],
        [6 * M, 4 * M, 3 * M, 4 * M],  # face coupée en deux morceaux alignés
        [3 * M, 4 * M, 0, 4 * M],
        [0, 4 * M, 0, 0],
        [0, 0.3 * M, 6 * M, 0.3 * M],  # face voisine, à 30 cm : ne doit pas attirer
    ]
)


def test_contour_tremble_redresse_sur_les_faces():
    sommets = redresser(_tremble(0, 0, 6, 4), FACES, M_PAR_PT)
    assert len(sommets) == 4
    attendus = [(0, 0), (6 * M, 0), (6 * M, 4 * M), (0, 4 * M)]
    for point in attendus:
        assert min(math.dist(point, s) for s in sommets) < 0.01 * M


def test_sans_face_proche_le_contour_reste_simplifie():
    loin = FACES + 1.0 * M
    sommets = redresser(_tremble(0, 0, 6, 4), loin, M_PAR_PT)
    aire = abs(sum(sommets[k - 1][0] * sommets[k][1] - sommets[k][0] * sommets[k - 1][1] for k in range(len(sommets)))) / 2
    assert aire / (M * M) == pytest.approx(24, abs=1.0)
    assert redresser(_tremble(0, 0, 6, 4), np.zeros((0, 4)), M_PAR_PT)
