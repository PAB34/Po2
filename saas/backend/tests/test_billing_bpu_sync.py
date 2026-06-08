"""Tests de la sync BPU (xlsx) → BillingBpuLine.

Vérité terrain : `bpu_templates.BPU_TEMPLATES_BY_LOT` (saisie manuelle validée). La sync
construite depuis le xlsx audité doit le reproduire, à l'exception documentée des lignes
MUDT noircies du Lot 2 (le xlsx laisse cee/go vides ; l'ancien template les avait re-remplis).
"""
from pathlib import Path

import pytest

from app.services.billing_bpu_sync import (
    build_lines_for_lot,
    tariff_codes_for_row,
    _to_eur_per_mwh,
    _parse_last_year,
)
from app.services.bpu_templates import BPU_TEMPLATES_BY_LOT

XLSX = (
    Path(__file__).resolve().parents[2]
    / "energie"
    / "HERAULT ENERGIE"
    / "HISTORIQUE BPU"
    / "extraction_tarifs_electricite_BPU.xlsx"
)

pytestmark = pytest.mark.skipif(not XLSX.exists(), reason="xlsx de référence absent")


def _key4(line):
    """(tariff, poste, fourniture, capacite) — le cœur du prix, arrondi."""
    r = lambda v: round(v, 3) if v is not None else None
    return (line["tariff_code"], line["poste"], r(line["pu_fourniture"]), r(line["pu_capacite"]))


def _key6(line):
    r = lambda v: round(v, 3) if v is not None else None
    return (*_key4(line), r(line["pu_cee"]), r(line["pu_go"]))


def test_lot1_identical_to_template():
    res = build_lines_for_lot(1, xlsx_path=XLSX)
    assert res.warnings == []
    assert res.source_supplier == "ENGIE"
    assert res.source_year == 2026
    got = sorted(_key6(l) for l in res.lines)
    exp = sorted(_key6(l) for l in BPU_TEMPLATES_BY_LOT["lot1"])
    assert got == exp


def test_lot2_matches_template_except_blacked_out_mudt():
    res = build_lines_for_lot(2, xlsx_path=XLSX)
    assert res.warnings == []
    assert res.source_supplier == "EDF"
    # fourniture + capacite + tarif + poste : identiques sur les 22 lignes
    got4 = sorted(_key4(l) for l in res.lines)
    exp4 = sorted(_key4(l) for l in BPU_TEMPLATES_BY_LOT["lot2"])
    assert got4 == exp4
    # seule différence attendue : MUDT (lignes noircies) → cee/go None côté xlsx
    diffs = {(l["tariff_code"], l["poste"]) for l in res.lines if _key6(l) not in {_key6(t) for t in BPU_TEMPLATES_BY_LOT["lot2"]}}
    assert diffs == {("MUDT", "hp"), ("MUDT", "hc")}
    for line in res.lines:
        if line["tariff_code"] == "MUDT":
            assert line["pu_cee"] is None and line["pu_go"] is None


def test_lot2_eclairage_public_distinct_from_cu():
    """La ligne SDT CU (75,80) doit être CU, pas EP, malgré le TURPE 'Assimilé Eclairage Public'."""
    res = build_lines_for_lot(2, xlsx_path=XLSX)
    by_code = {(l["tariff_code"], l["poste"]): l for l in res.lines}
    assert ("CU", "base") in by_code
    assert ("EP", "base") in by_code
    assert round(by_code[("CU", "base")]["pu_fourniture"], 2) == 75.80
    assert round(by_code[("EP", "base")]["pu_fourniture"], 2) == 84.84


def test_tariff_mapper_cases():
    assert tariff_codes_for_row("BT ≤ 36 kVA SDT CU4 / MU4", "Bâtiment", "Bâtiment") == ["CU4", "MU4"]
    assert tariff_codes_for_row("BT ≤ 36 kVA SDT CU", "Bâtiment", "Bâtiment") == ["CU"]
    assert tariff_codes_for_row("BT ≤ 36 kVA SDT LU", "Bâtiment", "Bâtiment") == ["LU"]
    assert tariff_codes_for_row("BT ≤ 36 kVA MUDT", "Bâtiment", "Bâtiment") == ["MUDT"]
    assert tariff_codes_for_row("HTA", "C2", "Bâtiment") == ["C2"]
    assert tariff_codes_for_row("BT", "C4", "Bâtiment") == ["C4"]
    assert tariff_codes_for_row("BT>36 kVA - C4", "Assimilé Eclairage Public", "Eclairage Public") == ["C4"]
    # plain BT ≤ 36 kVA sans token tarifaire + eclairage → EP
    assert tariff_codes_for_row("BT ≤ 36 kVA", "Assimilé Eclairage Public", "Eclairage Public") == ["EP"]
    assert tariff_codes_for_row("inconnu", None, None) == []


def test_unit_normalization_and_year_parsing():
    assert _to_eur_per_mwh(4.68, "c€/kWh HTT") == 46.8  # c€/kWh → ×10
    assert _to_eur_per_mwh(75.8, "€/MWh HTT") == 75.8
    assert _to_eur_per_mwh(None, "€/MWh") is None
    assert _parse_last_year("2026") == 2026
    assert _parse_last_year("2021-2022") == 2022
    assert _parse_last_year("2022 / signé 2023") == 2023
