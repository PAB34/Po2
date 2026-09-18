"""Parois mesurées par paires de faces (docs/thermique/parois-et-motifs-decisions.md, D4 et D5)."""
from __future__ import annotations

import math

import pytest

from thermique_moteur import calques, parois

M = 1000 / 50 / (25.4 / 72)  # points PDF pour 1 m à 1/50
MUR = "trait|1.56|#000000|"
TRAME = "trait|0.36|#000000|"


def _segment(x1, y1, x2, y2):
    return [x1 * M, y1 * M, x2 * M, y2 * M]


def _plan(elements):
    return calques.assembler(elements, 50)


def _mur_droit(y_bas, y_haut, x0=0.0, x1=6.0, signature=MUR):
    """Les deux faces d'un mur horizontal."""
    return [
        (calques.TRAIT, signature, "droit", _segment(x0, y_bas, x1, y_bas)),
        (calques.TRAIT, signature, "droit", _segment(x0, y_haut, x1, y_haut)),
    ]


def test_une_paroi_porte_son_epaisseur_et_sa_longueur():
    plan = _plan(_mur_droit(0.0, 0.24))
    indices = list(range(len(plan["elements"])))
    mesure = parois.mesurer(plan, indices)

    assert len(mesure["parois"]) == 1
    paroi = mesure["parois"][0]
    assert paroi["epaisseur"] / M == pytest.approx(0.24, abs=0.005)
    assert paroi["longueur"] / M == pytest.approx(6.0, abs=0.01)
    assert mesure["longueur_m"] == pytest.approx(6.0, abs=0.01)
    # l'axe passe au milieu des deux faces
    x1, y1, x2, y2 = paroi["axe"]
    assert y1 / M == pytest.approx(0.12, abs=0.005) and y2 / M == pytest.approx(0.12, abs=0.005)
    assert (x1 / M, x2 / M) == pytest.approx((0.0, 6.0), abs=0.01)
    assert mesure["faces_appariees"] == 2


def test_les_faces_trop_courtes_ou_sans_vis_a_vis_sont_ecartees():
    # un trait isolé, et deux faces qui ne se recouvrent pas
    plan = _plan(
        [
            (calques.TRAIT, MUR, "droit", _segment(0, 0, 3, 0)),
            (calques.TRAIT, MUR, "droit", _segment(8, 0.2, 11, 0.2)),
            (calques.TRAIT, MUR, "court", _segment(0, 5, 0.2, 5)),
        ]
    )
    with pytest.raises(parois.ParoisError, match="vis-à-vis"):
        parois.mesurer(plan, list(range(len(plan["elements"]))))

    plan = _plan([(calques.TRAIT, MUR, "court", _segment(0, 0, 0.2, 0))])
    with pytest.raises(parois.ParoisError, match="assez longue"):
        parois.mesurer(plan, [0])


def test_les_faces_obliques_ou_trop_ecartees_ne_font_pas_paroi():
    # 5° d'écart : ce ne sont pas deux faces d'une même paroi
    plan = _plan(
        [
            (calques.TRAIT, MUR, "droit", _segment(0, 0, 6, 0)),
            (calques.TRAIT, MUR, "droit", _segment(0, 0.24, 6, 0.24 + 6 * math.tan(math.radians(5)))),
        ]
    )
    with pytest.raises(parois.ParoisError):
        parois.mesurer(plan, [0, 1])

    # 1,20 m d'écart : c'est un couloir, pas une paroi
    plan = _plan(_mur_droit(0.0, 1.20))
    with pytest.raises(parois.ParoisError):
        parois.mesurer(plan, [0, 1])


def test_un_mur_en_biais_est_mesure_comme_un_autre():
    angle = math.radians(37)
    ex, ey = math.cos(angle), math.sin(angle)
    nx, ny = -ey * 0.30, ex * 0.30
    plan = _plan(
        [
            (calques.TRAIT, MUR, "droit", _segment(0, 0, 5 * ex, 5 * ey)),
            (calques.TRAIT, MUR, "droit", _segment(nx, ny, 5 * ex + nx, 5 * ey + ny)),
        ]
    )
    mesure = parois.mesurer(plan, [0, 1])
    assert len(mesure["parois"]) == 1
    assert mesure["parois"][0]["epaisseur"] / M == pytest.approx(0.30, abs=0.005)
    assert mesure["parois"][0]["longueur"] / M == pytest.approx(5.0, abs=0.02)


def test_une_polyligne_donne_une_face_par_pan():
    """Un mur dessiné d'un seul trait brisé porte bien une paroi par pan."""
    plan = _plan(
        [
            (calques.TRAIT, MUR, "polyligne", _segment(0, 0, 6, 0) + [6 * M, 4 * M]),
            (calques.TRAIT, MUR, "polyligne", _segment(0, 0.2, 5.8, 0.2) + [5.8 * M, 4 * M]),
        ]
    )
    mesure = parois.mesurer(plan, [0, 1])
    assert len(mesure["parois"]) == 2
    assert all(p["epaisseur"] / M == pytest.approx(0.20, abs=0.005) for p in mesure["parois"])


def test_une_facade_coupee_par_ses_baies_reste_une_paroi():
    """Les morceaux d'une façade, séparés par les fenêtres, sont recousus ; les trous sont les baies."""
    elements = []
    # face extérieure et face intérieure d'une façade de 12 m, percée de deux baies de 1,5 m
    for y in (0.0, 0.30):
        for x0, x1 in ((0.0, 3.0), (4.5, 7.5), (9.0, 12.0)):
            elements.append((calques.TRAIT, MUR, "droit", _segment(x0, y, x1, y)))
    plan = _plan(elements)
    mesure = parois.mesurer(plan, list(range(len(plan["elements"]))))

    assert len(mesure["parois"]) == 1
    paroi = mesure["parois"][0]
    assert paroi["longueur"] / M == pytest.approx(12.0, abs=0.02)
    assert paroi["epaisseur"] / M == pytest.approx(0.30, abs=0.005)
    # deux baies de 1,50 m percent la paroi de part en part, et 9 m restent pleins
    assert len(paroi["baies"]) == 2
    assert all(b / M == pytest.approx(1.5, abs=0.02) for b in paroi["baies"])
    assert mesure["baies_m"] == pytest.approx(3.0, abs=0.05)
    assert mesure["pleine_m"] == pytest.approx(9.0, abs=0.05)


def test_deux_murs_alignes_mais_lointains_restent_deux_parois():
    """Au-delà de BAIE_MAX_M, le trou n'est plus une baie : ce sont deux murs distincts."""
    elements = []
    for y in (0.0, 0.20):
        for x0, x1 in ((0.0, 4.0), (14.0, 18.0)):
            elements.append((calques.TRAIT, MUR, "droit", _segment(x0, y, x1, y)))
    plan = _plan(elements)
    mesure = parois.mesurer(plan, list(range(len(plan["elements"]))))
    assert len(mesure["parois"]) == 2
    assert all(not p["baies"] for p in mesure["parois"])
    assert mesure["longueur_m"] == pytest.approx(8.0, abs=0.05)


def test_une_trame_reguliere_est_refusee():
    """Garde-fou D5 : dans un quadrillage, chaque trait a une dizaine de vis-à-vis possibles."""
    elements = []
    for k in range(30):
        elements.append((calques.TRAIT, TRAME, "droit", _segment(0, k * 0.1, 8, k * 0.1)))
    plan = _plan(elements)
    indices = list(range(len(plan["elements"])))

    with pytest.raises(parois.ParoisError, match="trame"):
        parois.mesurer(plan, indices)

    # sans le garde-fou, les paires existent bel et bien : c'est leur nombre qui les trahit
    sans_controle = parois.mesurer(plan, indices, controler=False)
    assert len(sans_controle["parois"]) >= 20
    assert sans_controle["vis_a_vis_par_face"] > parois.VIS_A_VIS_MAX


def test_des_parois_franches_passent_le_garde_fou():
    """Les mêmes traits, mais posés par paires d'épaisseurs franches : c'est un bâtiment."""
    elements = []
    for k in range(12):
        bas = k * 3.0
        elements += _mur_droit(bas, bas + (0.24 if k % 3 else 0.12))
    plan = _plan(elements)
    mesure = parois.mesurer(plan, list(range(len(plan["elements"]))))
    assert len(mesure["parois"]) == 12
    assert mesure["vis_a_vis_par_face"] <= 1.0
    assert [round(e, 2) for e, _ in mesure["epaisseurs"]] == [0.24, 0.12]
    assert dict(mesure["epaisseurs"])[0.24] == 8
