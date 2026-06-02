"""Tests du parsing du BPU travaux P3 (Annexe 7) — catalogue de prix unitaires.

Validé sur le fichier réel L1 : 132 prestations, 7 taux horaires, 4 coefficients ;
ENT-001-1 = 334 €HT/m.l, Chauffagiste jour = 50, CF-001 = 1,18.
"""
from collections import Counter
from pathlib import Path

import pytest

from app.services.cpe_dalkia_import import _parse_bpu, parse_dalkia_file

L1_FILE = Path(__file__).resolve().parents[2] / "energie" / "DALKIA" / "01_24BT039_L1_AE_ANNEXES_OFFRE_FINALE.xlsx"


def _row(pairs: dict[int, object], width: int = 12) -> tuple:
    cells: list[object] = [None] * width
    for col, val in pairs.items():
        cells[col - 1] = val
    return tuple(cells)


def _synthetic_rows() -> list[tuple]:
    return [
        _row({1: "OPERATIONS STANDARDS"}),
        _row({1: "Travaux de terrassement (pour reseaux enterres) :"}),
        # header : Code | Profondeur | Seuil | Cout (€HT / m.l) | _ | Qte | Cout
        _row({2: "Code", 3: "Profondeur", 4: "Seuil de longueur", 5: "Cout (€ HT / m.l)", 7: "Quantite", 8: "Cout (€ HT)"}),
        _row({1: "Tranchee sur espace vert", 2: "ENT-001-1", 3: "80 cm", 4: "L < 5", 5: 334, 7: 5, 8: 1670}),
        _row({2: "ENT-001-2", 4: "5 < L < 10", 5: 303, 7: 5, 8: 1515}),
        _row({1: "Travaux de maconnerie :"}),
        _row({2: "Code", 3: "Epaisseur", 4: "Cout (€ HT / m2)", 7: "Quantite", 8: "Cout (€ HT)"}),
        _row({1: "Cassage de mur", 2: "ENR-001", 3: "10 cm", 4: 130, 7: 2, 8: 260}),
        _row({1: "AUTRES INTERVENTIONS (TAUX HORAIRES)"}),
        _row({1: "Designation", 2: "Jour : 7h - 21h", 3: "Nuit : 21h - 7h", 4: "Samedi", 5: "Dimanche", 7: "Quantite", 8: "Cout"}),
        _row({1: "Chauffagiste monteur soudeur", 2: 50, 3: 75, 4: 75, 5: 75, 7: 20, 8: 1100}),
        _row({1: "Plombier", 2: 50, 3: 75, 4: 75, 5: 75, 7: 5, 8: 275}),
        _row({1: "Coefficients d'entreprise affectes aux fournitures"}),
        _row({2: "Code", 3: "Coefficient", 4: "Coefficient MAXIMAL", 7: "Quantite", 8: "Cout"}),
        _row({1: "Pour des fournitures < 1500", 2: "CF-001", 3: 1.18, 4: 1.2, 7: 4000, 8: 4720}),
    ]


def test_parse_synthetic_bpu():
    rows, warnings = _parse_bpu(_synthetic_rows())
    cats = Counter(r.categorie for r in rows)
    assert cats["prestation"] == 3
    assert cats["taux_horaire"] == 2
    assert cats["coefficient"] == 1

    by_code = {r.code: r for r in rows if r.code}
    assert by_code["ENT-001-1"].cout_unitaire == pytest.approx(334)
    assert "m.l" in (by_code["ENT-001-1"].unite or "")
    assert by_code["ENT-001-1"].specificite == "80 cm | L < 5"
    assert by_code["ENR-001"].cout_unitaire == pytest.approx(130)
    assert "m2" in (by_code["ENR-001"].unite or "")
    assert by_code["CF-001"].coefficient == pytest.approx(1.18)
    assert by_code["CF-001"].coefficient_max == pytest.approx(1.2)

    chauf = next(r for r in rows if r.categorie == "taux_horaire" and "Chauffagiste" in (r.libelle or ""))
    assert (chauf.cout_unitaire, chauf.cout_nuit, chauf.cout_samedi, chauf.cout_dimanche) == pytest.approx((50, 75, 75, 75))


def test_prestation_inherits_libelle_within_group():
    rows, _ = _parse_bpu(_synthetic_rows())
    ent2 = next(r for r in rows if r.code == "ENT-001-2")
    assert ent2.libelle == "Tranchee sur espace vert"  # hérité de la 1re ligne du groupe


@pytest.mark.skipif(not L1_FILE.exists(), reason="fichier DALKIA L1 absent")
def test_parse_real_l1_bpu():
    res = parse_dalkia_file(L1_FILE.read_bytes(), L1_FILE.name, 1)
    cats = Counter(r.categorie for r in res.bpu_rows)
    assert cats["prestation"] >= 120
    assert cats["taux_horaire"] == 7
    assert cats["coefficient"] >= 3
    by_code = {r.code: r for r in res.bpu_rows if r.code}
    assert by_code["ENT-001-1"].cout_unitaire == pytest.approx(334)
    assert by_code["CF-001"].coefficient == pytest.approx(1.18)
