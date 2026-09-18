"""Ce qui borde un local (docs/thermique/parois-et-motifs-decisions.md §0.6, étape 3)."""
from __future__ import annotations

import pytest

from thermique_moteur import calques, composants

M = 1000 / 50 / (25.4 / 72)  # points PDF pour 1 m à 1/50
MUR = "trait|1.56|#000000|"
VITRAGE = "trait|0.24|#000000|"
MOBILIER = "trait|0.36|#808080|"


def _s(x1, y1, x2, y2):
    return [x1 * M, y1 * M, x2 * M, y2 * M]


def _contour(x0, y0, x1, y1):
    return [x0 * M, y0 * M, x1 * M, y0 * M, x1 * M, y1 * M, x0 * M, y1 * M]


def _plan(traits):
    return calques.assembler([(calques.TRAIT, s, f, c) for s, f, c in traits], 50)


def test_les_familles_collees_au_contour_sont_relevees_avec_leur_longueur():
    """Un local de 8 × 5 m : trois murs, une façade vitrée, et du mobilier au milieu."""
    plan = _plan(
        [
            (MUR, "droit", _s(0, 0, 8, 0)),
            (MUR, "droit", _s(0, 0, 0, 5)),
            (MUR, "droit", _s(8, 0, 8, 5)),
            (VITRAGE, "droit", _s(0, 5, 8, 5)),
            (MOBILIER, "droit", _s(3, 2, 5, 2)),  # loin du contour
        ]
    )
    familles = composants.bordant(plan, _contour(0, 0, 8, 5))
    par_signature = {f["signature"]: f for f in familles}

    assert set(par_signature) == {MUR, VITRAGE}  # le mobilier du milieu n'est pas une paroi
    assert par_signature[MUR]["nombre"] == 3
    assert par_signature[MUR]["longueur_m"] == pytest.approx(18.0, abs=0.1)
    assert par_signature[VITRAGE]["longueur_m"] == pytest.approx(8.0, abs=0.1)
    # la façade vitrée ne touche qu'un côté ; les murs en touchent trois
    assert len(par_signature[VITRAGE]["cotes"]) == 1
    assert len(par_signature[MUR]["cotes"]) == 3
    # les plus longues d'abord
    assert familles[0]["signature"] == MUR


def test_un_element_qui_effleure_le_contour_est_ecarte():
    """Une cloison perpendiculaire touche le contour en un point : ce n'est pas une paroi du local."""
    plan = _plan(
        [
            (MUR, "droit", _s(0, 0, 8, 0)),
            (MUR, "droit", _s(4, 0, 4, 4)),  # part du contour vers l'intérieur
        ]
    )
    familles = composants.bordant(plan, _contour(0, 0, 8, 5))
    assert len(familles) == 1
    assert familles[0]["nombre"] == 1  # seul le mur du bas est retenu
    assert familles[0]["longueur_m"] == pytest.approx(8.0, abs=0.1)


def test_les_natures_deja_connues_sont_rendues_telles_quelles():
    plan = _plan([(MUR, "droit", _s(0, 0, 8, 0)), (VITRAGE, "droit", _s(0, 5, 8, 5))])
    familles = composants.bordant(plan, _contour(0, 0, 8, 5), natures={0: "mur"})
    par_signature = {f["signature"]: f for f in familles}
    assert par_signature[MUR]["nature"] == "mur"
    assert par_signature[VITRAGE]["nature"] is None  # à identifier


def test_les_longueurs_des_cotes_donnent_le_metre_du_local():
    plan = _plan([(MUR, "droit", _s(0, 0, 8, 0))])
    assert composants.longueurs_des_cotes(plan, _contour(0, 0, 8, 5)) == [8.0, 5.0, 8.0, 5.0]


def test_un_local_sans_rien_autour_ne_rend_rien():
    plan = _plan([(MOBILIER, "droit", _s(30, 30, 32, 30))])
    assert composants.bordant(plan, _contour(0, 0, 8, 5)) == []
