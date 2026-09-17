"""« Tout détecter » : reconnaissance des objets d'un plan vierge, fermeture automatique et enveloppe déduite des
pièces chauffées (docs/thermique/refondation-parcours-decisions.md §18)."""
from __future__ import annotations

import math

import pytest

from thermique_moteur import bande, calques, reconnaissance

M = 1000 / 50 / (25.4 / 72)  # points PDF pour 1 m à 1/50
MUR = "trait|1.56|#000000|"
CADRE = "trait|0.36|#000000|"
VITRE = "trait|0.24|#000000|"
ISOLANT = "trait|0.24|#808080|"


def _rect(x0, y0, x1, y1):
    return [x0 * M, y0 * M, x1 * M, y0 * M, x1 * M, y1 * M, x0 * M, y1 * M, x0 * M, y0 * M]


def _plan():
    """Bâtiment de 10 × 6 m (murs de 30 cm), une baie vitrée, une porte à battement en pointillés, l'isolant des
    façades et, dehors, une terrasse à lames parallèles."""
    elements = [
        (calques.TRAIT, MUR, "grand_ferme", _rect(0, 0, 10, 6)),
        (calques.TRAIT, MUR, "grand_ferme", _rect(0.3, 0.3, 9.7, 5.7)),
    ]
    # baie : trois traits fins et deux traits de cadre, tous de 1 m
    for y, signature in ((0.10, VITRE), (0.15, VITRE), (0.20, VITRE), (0.05, CADRE), (0.25, CADRE)):
        elements.append((calques.TRAIT, signature, "droit", [2 * M, y * M, 3 * M, y * M]))
    # porte : arc de 0,9 m en points tous les 1,5 pt, et son vantail
    centre, rayon = (4 * M, 0.3 * M), 0.9 * M
    pas = 1.5 / rayon
    angle = 0.0
    while angle <= math.pi / 2:
        x, y = centre[0] + rayon * math.cos(angle), centre[1] + rayon * math.sin(angle)
        elements.append((calques.TRAIT, CADRE, "court", [x, y, x + 0.15, y]))
        angle += pas
    elements.append((calques.TRAIT, CADRE, "droit", [centre[0], centre[1], centre[0] + rayon, centre[1]]))
    # isolant : 60 petits traits gris dans l'épaisseur du mur bas
    for k in range(60):
        x = (0.5 + k * 0.15) * M
        elements.append((calques.TRAIT, ISOLANT, "court", [x, 0.12 * M, x + 0.08 * M, 0.18 * M]))
    # terrasse : 30 lames parallèles dehors
    for k in range(30):
        y = (-0.2 - k * 0.1) * M
        elements.append((calques.TRAIT, CADRE, "droit", [1 * M, y, 9 * M, y]))
    return calques.assembler(elements, 50)


def test_objets_reconnus_sans_calque():
    plan = _plan()
    assert reconnaissance.signature_murs(plan) == MUR

    trouvees = reconnaissance.portes(plan)
    assert len(trouvees) == 1
    porte = trouvees[0]
    assert porte["rayon"] == pytest.approx(0.9 * M, rel=0.05)
    assert len(porte["elements"]) >= 30  # les points de l'arc et le vantail
    assert math.dist(porte["centre"], (4 * M, 0.3 * M)) < 0.05 * M

    exclus = set(porte["elements"])
    groupes = reconnaissance.menuiseries(plan, exclus=exclus)
    assert len(groupes) == 1
    signatures = {plan["signatures"][plan["elements"][i][1]] for i in groupes[0]}
    # le vitrage et son cadre, sans les lames de la terrasse
    assert signatures == {VITRE, CADRE} and len(groupes[0]) == 5

    murs = calques.famille(plan, MUR, calques.TOUTES_FORMES)
    assert reconnaissance.familles_isolant(plan, murs) == [ISOLANT]
    assert reconnaissance.familles_isolant(plan, []) == []


def test_fermeture_auto_et_enveloppe_depuis_les_pieces():
    plan = _plan()
    murs = calques.famille(plan, MUR, calques.TOUTES_FORMES)
    assert bande.fermeture_auto(plan, murs) == 0.5
    with pytest.raises(Exception, match="Aucun calque"):
        bande.fermeture_auto(plan, [])

    # la pièce chauffée est l'intérieur du bâtiment : le nu extérieur passe par la face extérieure des murs
    piece = [v for k, v in enumerate(_rect(0.3, 0.3, 9.7, 5.7)) if k < 8]
    (batiment,) = bande.depuis_pieces(plan, murs, [piece])
    assert batiment["aire_interieur_m2"] == pytest.approx(9.4 * 5.4, abs=1.0)
    assert batiment["aire_exterieur_m2"] == pytest.approx(60, abs=1.5)
    with pytest.raises(Exception, match="Aucune pièce chauffée"):
        bande.depuis_pieces(plan, murs, [])

    # la terrasse, dehors, ne doit pas être gagnée par le nu extérieur
    assert min(p[1] for p in batiment["nu_exterieur"]) > -0.2 * M
