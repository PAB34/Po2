"""Tests du parsing de l'en-tête Annexe 6 : composants de prix gaz + coefficients de révision Pu.

Sémantique validée sur le fichier réel (L1) : a+b+c+d+e = 1 par tarif, Pu T2 = 92,46.
"""
from pathlib import Path

import pytest

from app.services.cpe_dalkia_import import _parse_p1_gaz_tarifs, parse_dalkia_file

L1_FILE = Path(__file__).resolve().parents[2] / "energie" / "DALKIA" / "01_24BT039_L1_AE_ANNEXES_OFFRE_FINALE.xlsx"


def _row(pairs: dict[int, object], width: int = 40) -> tuple:
    """Construit une ligne (tuple) avec valeurs aux colonnes 1-indexées indiquées."""
    cells: list[object] = [None] * width
    for col, val in pairs.items():
        cells[col - 1] = val
    return tuple(cells)


def _synthetic_rows() -> list[tuple]:
    rows: list[tuple] = []
    rows.append(_row({1: "ANNEXE 6"}))                       # 0
    rows.append(_row({}))                                     # 1
    rows.append(_row({8: "P0 FOURNISSEUR (EHT/MWHPCS)"}))     # 2  header prix
    # cols : 7=tarif, 8=p0, 9=peg, 10=tvd, 11=cee, 12=ticgn, 13=marge, 14=pu
    rows.append(_row({7: "T1", 8: 3.75, 9: 44.74, 10: 42.37, 11: 6.51, 12: 17.16, 13: 0.1032, 14: 126.35}))  # 3
    rows.append(_row({7: "T2", 8: 4.01, 9: 44.74, 10: 11.39, 11: 6.51, 12: 17.16, 13: 0.1032, 14: 92.46}))   # 4
    rows.append(_row({7: "T3", 8: 4.13, 9: 44.74, 10: 8.19, 11: 6.51, 12: 17.16, 13: 0.1032, 14: 89.06}))    # 5
    rows.append(_row({7: "T4", 8: 6.078, 9: 44.74, 10: 1.11, 11: 6.51, 12: 17.16, 13: 0.1032, 14: 83.4}))    # 6
    rows.append(_row({1: "Formule : Pu GAZ = Pu 0 x ..."}))  # 7
    # bloc coefficients : seule la ligne 'a' porte les libellés tarif (cols 1,5,9,13)
    rows.append(_row({1: "T1", 2: "a", 3: 0.03272, 5: "T2", 6: "a", 7: 0.04782,
                      9: "T3", 10: "a", 11: 0.05112, 13: "T4", 14: "a", 15: 0.08037}))  # 8
    rows.append(_row({2: "b", 3: 0.39065, 6: "b", 7: 0.53384, 10: "b", 11: 0.55422, 14: "b", 15: 0.59183}))  # 9
    rows.append(_row({2: "c", 3: 0.36996, 6: "c", 7: 0.13591, 10: "c", 11: 0.10145, 14: "c", 15: 0.01468}))  # 10
    rows.append(_row({2: "d", 3: 0.05684, 6: "d", 7: 0.07768, 10: "d", 11: 0.08064, 14: "d", 15: 0.08612}))  # 11
    rows.append(_row({2: "e", 3: 0.14983, 6: "e", 7: 0.20475, 10: "e", 11: 0.21257, 14: "e", 15: 0.227}))    # 12
    return rows


def test_parse_synthetic_tarifs_and_coefficients():
    tarifs, warnings = _parse_p1_gaz_tarifs(_synthetic_rows())
    assert warnings == []
    by = {t.type_tarif: t for t in tarifs}
    assert set(by) == {"T1", "T2", "T3", "T4"}

    t2 = by["T2"]
    assert t2.prix_unitaire_ht == pytest.approx(92.46)
    assert t2.ref_peg == pytest.approx(44.74)
    assert t2.terme_acheminement == pytest.approx(11.39)
    assert t2.ticgn == pytest.approx(17.16)
    # coefficients T2
    assert (t2.coef_a, t2.coef_b, t2.coef_c, t2.coef_d, t2.coef_e) == pytest.approx(
        (0.04782, 0.53384, 0.13591, 0.07768, 0.20475)
    )


def test_coefficients_sum_to_one_per_tarif():
    """Invariant fort : la formule est normalisée (a+b+c+d+e = 1)."""
    tarifs, _ = _parse_p1_gaz_tarifs(_synthetic_rows())
    for t in tarifs:
        total = t.coef_a + t.coef_b + t.coef_c + t.coef_d + t.coef_e
        assert total == pytest.approx(1.0, abs=1e-4), f"{t.type_tarif} somme={total}"


def test_no_price_header_returns_warning():
    tarifs, warnings = _parse_p1_gaz_tarifs([_row({1: "rien"}), _row({1: "autre"})])
    assert tarifs == []
    assert any("P0 FOURNISSEUR" in w for w in warnings)


@pytest.mark.skipif(not L1_FILE.exists(), reason="fichier DALKIA L1 absent")
def test_parse_real_l1_file():
    res = parse_dalkia_file(L1_FILE.read_bytes(), L1_FILE.name, 1)
    by = {t.type_tarif: t for t in res.p1_tarifs}
    assert {"T1", "T2", "T3", "T4"} <= set(by)
    assert by["T2"].prix_unitaire_ht == pytest.approx(92.46)
    assert by["T1"].coef_a == pytest.approx(0.03272, abs=1e-5)
    for t in res.p1_tarifs:
        total = t.coef_a + t.coef_b + t.coef_c + t.coef_d + t.coef_e
        assert total == pytest.approx(1.0, abs=1e-4)
