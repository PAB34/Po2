"""Lot G1 : nu extérieur et nu intérieur déduits des murs vectoriels.
Voir docs/thermique/detection-guidee-decisions.md §6."""
from __future__ import annotations

import pytest

from thermique_moteur import lignes

M = 1000 / 100 / (25.4 / 72)  # points PDF pour 1 m à 1/100


def _horizontal(x0, y0, x1, y1):
    # faces sur les arêtes 0-1 et 2-3, comme les murs de murs.detecter_murs
    return {"points": [(x0 * M, y0 * M), (x1 * M, y0 * M), (x1 * M, y1 * M), (x0 * M, y1 * M)], "epaisseur_m": round(y1 - y0, 3)}


def _vertical(x0, y0, x1, y1):
    return {"points": [(x0 * M, y0 * M), (x0 * M, y1 * M), (x1 * M, y1 * M), (x1 * M, y0 * M)], "epaisseur_m": round(x1 - x0, 3)}


def test_deux_lignes_d_un_batiment_avec_porte_refend_et_doublage():
    # Bâtiment de 10 × 8 m hors tout, murs de 30 cm, porte de 1 m en bas, doublage de 10 cm à gauche,
    # refend de 20 cm à l'intérieur.
    murs = [
        _horizontal(0, 0, 4.5, 0.3),
        _horizontal(5.5, 0, 10, 0.3),
        _horizontal(0, 7.7, 10, 8),
        _vertical(0, 0.3, 0.3, 7.7),
        _vertical(9.7, 0.3, 10, 7.7),
        _vertical(0.3, 0.3, 0.4, 7.7),
        _vertical(7, 0.3, 7.2, 7.7),
    ]
    resultat = lignes.detecter_deux_lignes(murs, 100)
    assert resultat is not None
    assert resultat["nu_exterieur"]["aire_m2"] == pytest.approx(80.0, abs=0.05)
    assert len(resultat["nu_exterieur"]["points"]) == 4
    # intérieur : 0,4 m à gauche (mur + doublage), 0,3 m ailleurs, la porte ne crée pas d'encoche
    assert resultat["nu_interieur"]["aire_m2"] == pytest.approx(9.3 * 7.4, abs=0.05)
    assert len(resultat["nu_interieur"]["points"]) == 4
    xs = sorted(round(p[0] / M, 2) for p in resultat["nu_interieur"]["points"])
    assert xs[0] == pytest.approx(0.4, abs=0.005) and xs[-1] == pytest.approx(9.7, abs=0.005)


def test_nu_interieur_suit_un_changement_d_epaisseur():
    # Façade basse : 30 cm sur la moitié gauche, 50 cm sur la moitié droite.
    murs = [
        _horizontal(0, 0, 5, 0.3),
        _horizontal(5, 0, 10, 0.5),
        _horizontal(0, 7.7, 10, 8),
        _vertical(0, 0.3, 0.3, 7.7),
        _vertical(9.7, 0.5, 10, 7.7),
    ]
    resultat = lignes.detecter_deux_lignes(murs, 100)
    assert resultat is not None
    assert resultat["nu_interieur"]["aire_m2"] == pytest.approx(9.4 * 7.4 - 4.7 * 0.2, abs=0.05)
    assert len(resultat["nu_interieur"]["points"]) == 6
