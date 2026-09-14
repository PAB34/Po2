"""Jalon J1 de la détection exacte des murs : fusion des morceaux de lignes, union des facettes
d'aplat, dictionnaire des plumes. Voir docs/thermique/detection-murs-strategie.md."""
from __future__ import annotations

import pytest

from thermique_moteur import vecteurs

M = 1000 / 100 / (25.4 / 72)  # points PDF pour 1 m à 1/100


def test_fusion_des_morceaux_colineaires():
    morceaux = [
        (0.0, 10.0, 30.0, 10.0, 1.56, 0),
        (30.05, 10.0, 60.0, 10.0, 1.56, 0),  # jointure de 0,05 pt : recollé
        (90.0, 10.02, 60.0, 10.02, 1.56, 0),  # sens inverse, décalé de 0,02 pt : recollé
        (91.0, 10.0, 120.0, 10.0, 1.56, 0),  # trou de 1 pt : nouvelle ligne
        (0.0, 10.3, 50.0, 10.3, 1.56, 0),  # droite voisine à 0,3 pt : distincte
        (0.0, 10.0, 50.0, 10.0, 0.48, 0),  # autre plume : distincte
        (5.0, 5.0, 5.0, 5.0, 1.56, 0),  # point : ignoré
    ]
    lignes = vecteurs.fusionner_lignes(morceaux)
    epaisses = sorted((round(l["x1"], 2), round(l["x2"], 2), round(l["y1"], 2), l["morceaux"]) for l in lignes if l["largeur"] == 1.56)
    # Les morceaux d'une même droite (écart ≤ 0,05 pt) partagent sa position moyenne pondérée.
    assert epaisses == [(0.0, 50.0, 10.3, 1), (0.0, 90.0, 10.01, 3), (91.0, 120.0, 10.01, 1)]
    assert sum(1 for l in lignes if l["largeur"] == 0.48) == 1


def test_fusion_d_une_ligne_oblique_hachee():
    # Mur oblique à 10° découpé en 20 morceaux jointifs.
    import math

    ux, uy = math.cos(math.radians(10)), math.sin(math.radians(10))
    morceaux = [(k * 5 * ux, k * 5 * uy, (k + 1) * 5 * ux, (k + 1) * 5 * uy, 0.96, 0) for k in range(20)]
    lignes = vecteurs.fusionner_lignes(morceaux)
    assert len(lignes) == 1
    assert lignes[0]["longueur"] == pytest.approx(100.0, abs=1e-6)
    assert lignes[0]["morceaux"] == 20


def test_union_exacte_des_facettes():
    # Mur rectangulaire 30 × 5 pt imprimé en 4 triangles (maillage conforme), plus un triangle isolé.
    a, b, c, d, e = (0, 0), (15, 0), (30, 0), (30, 5), (0, 5)
    milieu = (15, 5)
    triangles = [([a, b, milieu], 153), ([a, milieu, e], 153), ([b, c, d], 153), ([b, d, milieu], 153), ([(50, 0), (60, 0), (55, 8)], 153)]
    anneaux = vecteurs.unir_aplats(triangles)
    assert len(anneaux) == 2
    aires = sorted(abs(anneau["aire_pt2"]) for anneau in anneaux)
    assert aires == pytest.approx([40.0, 150.0])
    rectangle = max(anneaux, key=lambda anneau: abs(anneau["aire_pt2"]))
    assert set(rectangle["points"]) == {(0.0, 0.0), (15.0, 0.0), (30.0, 0.0), (30.0, 5.0), (15.0, 5.0), (0.0, 5.0)}
    assert rectangle["facettes"] == 5


def test_dictionnaire_des_plumes():
    lignes = vecteurs.fusionner_lignes(
        [
            # deux faces de mur de 30 cm sur 6 m
            (0, 0, 6 * M, 0, 1.56, 0),
            (0, 0.30 * M, 6 * M, 0.30 * M, 1.56, 0),
            # cadre de la feuille : long, sans partenaire
            (0, -20 * M, 50 * M, -20 * M, 0.96, 0),
            # motif d'isolant : petits traits gris
            *[(k * 0.1 * M, 0.1 * M, k * 0.1 * M + 0.05 * M, 0.15 * M, 0.48, 152) for k in range(40)],
        ]
    )
    plumes = {(p["largeur"], p["luminance"]): p for p in vecteurs.dictionnaire_plumes(lignes, 100)}
    assert plumes[(1.56, 0)]["role"] == "faces de murs" and plumes[(1.56, 0)]["part_appariee"] == 1.0
    assert plumes[(0.96, 0)]["role"].startswith("autres")
    assert plumes[(0.48, 152)]["role"] == "hachures et motifs"
