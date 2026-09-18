"""Locaux délimités par les traits réels (docs/thermique/parois-et-motifs-decisions.md §0.6, étape 1)."""
from __future__ import annotations

import math

import pytest

from thermique_moteur import calques, locaux

M = 1000 / 50 / (25.4 / 72)  # points PDF pour 1 m à 1/50
MUR = "trait|1.56|#000000|"


def _t(x, y):
    return (x * M, y * M)


def _segment(x1, y1, x2, y2):
    return [x1 * M, y1 * M, x2 * M, y2 * M]


def _plan(traits):
    return calques.assembler([(calques.TRAIT, MUR, "droit", t) for t in traits], 50)


def _preparer(traits):
    plan = _plan(traits)
    return locaux.decouper_le_plan(plan, list(range(len(plan["elements"]))))


def test_un_local_rectangulaire_a_quatre_sommets_exacts():
    """Les traits débordent aux angles, comme sur un vrai plan : les coins sont les intersections."""
    graphe = _preparer(
        [
            _segment(-0.5, 0, 8.5, 0),
            _segment(-0.5, 5, 8.5, 5),
            _segment(0, -0.5, 0, 5.5),
            _segment(8, -0.5, 8, 5.5),
        ]
    )
    local = locaux.local_au_point(graphe, _t(4, 2.5))
    assert local["sommets"] == 4
    assert local["surface_m2"] == pytest.approx(40.0, abs=0.1)
    assert local["perimetre_m"] == pytest.approx(26.0, abs=0.1)
    assert local["compacite"] == pytest.approx(4 * math.pi * 40 / 26**2, abs=0.01)


def test_deux_locaux_separes_par_un_refend():
    graphe = _preparer(
        [
            _segment(0, 0, 10, 0),
            _segment(0, 4, 10, 4),
            _segment(0, 0, 0, 4),
            _segment(10, 0, 10, 4),
            _segment(6, 0, 6, 4),
        ]
    )
    gauche = locaux.local_au_point(graphe, _t(3, 2))
    droite = locaux.local_au_point(graphe, _t(8, 2))
    assert gauche["surface_m2"] == pytest.approx(24.0, abs=0.1)
    assert droite["surface_m2"] == pytest.approx(16.0, abs=0.1)
    assert gauche["sommets"] == 4 and droite["sommets"] == 4


def test_une_porte_est_refermee_et_le_local_ne_fuit_pas():
    """Sans le raccord, le contour s'échapperait par l'ouverture : c'est le défaut des 544 m² ratés."""
    graphe = _preparer(
        [
            _segment(0, 0, 10, 0),
            _segment(0, 4, 10, 4),
            _segment(0, 0, 0, 4),
            _segment(10, 0, 10, 4),
            # refend percé d'une porte de 0,9 m
            _segment(6, 0, 6, 1.5),
            _segment(6, 2.4, 6, 4),
        ]
    )
    gauche = locaux.local_au_point(graphe, _t(3, 2))
    droite = locaux.local_au_point(graphe, _t(8, 2))
    assert gauche["surface_m2"] == pytest.approx(24.0, abs=0.2)
    assert droite["surface_m2"] == pytest.approx(16.0, abs=0.2)
    # le local reste net : pas de contour en étoile
    assert gauche["compacite"] > 0.5 and droite["compacite"] > 0.5


def test_un_passage_trop_large_n_est_pas_referme():
    """Au-delà de PASSAGE_MAX_M, ce n'est plus une porte : les deux espaces n'en font qu'un."""
    graphe = _preparer(
        [
            _segment(0, 0, 10, 0),
            _segment(0, 4, 10, 4),
            _segment(0, 0, 0, 4),
            _segment(10, 0, 10, 4),
            _segment(6, 0, 6, 0.6),
            _segment(6, 3.4, 6, 4),
        ]
    )
    local = locaux.local_au_point(graphe, _t(3, 2))
    assert local["surface_m2"] == pytest.approx(40.0, abs=0.5)


def test_le_plus_petit_local_l_emporte():
    """Un local dans un plateau : le clic rend le local, pas le plateau qui le contient."""
    graphe = _preparer(
        [
            _segment(0, 0, 20, 0),
            _segment(0, 12, 20, 12),
            _segment(0, 0, 0, 12),
            _segment(20, 0, 20, 12),
            _segment(2, 2, 6, 2),
            _segment(2, 6, 6, 6),
            _segment(2, 2, 2, 6),
            _segment(6, 2, 6, 6),
        ]
    )
    petit = locaux.local_au_point(graphe, _t(4, 4))
    assert petit["surface_m2"] == pytest.approx(16.0, abs=0.1)
    grand = locaux.local_au_point(graphe, _t(15, 8))
    assert grand["surface_m2"] > 200


def test_un_point_hors_de_tout_local_est_dit_tel_quel():
    graphe = _preparer(
        [
            _segment(0, 0, 6, 0),
            _segment(0, 4, 6, 4),
            _segment(0, 0, 0, 4),
            _segment(6, 0, 6, 4),
        ]
    )
    with pytest.raises(locaux.LocauxError, match="aucun local"):
        locaux.local_au_point(graphe, _t(20, 20))


def test_un_plan_sans_limite_le_dit():
    plan = calques.assembler([], 50)
    with pytest.raises(locaux.LocauxError, match="Aucun trait"):
        locaux.decouper_le_plan(plan, [])


def test_un_local_en_biais_garde_ses_sommets_exacts():
    """Bâtiment dessiné en biais : aucun redressement, les coins sont les vraies intersections."""
    angle = math.radians(23)
    c, s = math.cos(angle), math.sin(angle)
    coins = [(0, 0), (7, 0), (7, 5), (0, 5)]
    tournes = [(x * c - y * s, x * s + y * c) for x, y in coins]
    traits = []
    for a, b in zip(tournes, tournes[1:] + tournes[:1]):
        traits.append(_segment(a[0], a[1], b[0], b[1]))
    graphe = _preparer(traits)
    milieu = tuple(sum(p[k] for p in tournes) / 4 * M for k in (0, 1))
    local = locaux.local_au_point(graphe, milieu)
    assert local["sommets"] == 4
    assert local["surface_m2"] == pytest.approx(35.0, abs=0.1)
