from decimal import Decimal
from pathlib import Path

import pytest

from app.services.invoice_parsers.engie_xlsx import _coerce_decimal, parse_engie_xlsx


def test_engie_xlsx_bordereau_total_matches_fic_sum():
    workbook = (
        Path(__file__).resolve().parents[2]
        / "energie"
        / "ENGIE"
        / "FACTURES"
        / "MesFactures_20260609132103.xlsx"
    )
    if not workbook.exists():
        pytest.skip("ENGIE sample workbook unavailable")

    parsed = parse_engie_xlsx(workbook)

    assert parsed
    for entry in parsed:
        total = _coerce_decimal(entry["invoice"].get("total_ttc"))
        fic_sum = sum(
            (_coerce_decimal(site.get("total_ttc")) or Decimal("0"))
            for site in entry.get("sites", [])
        )
        assert total is not None
        assert abs(total - fic_sum) <= Decimal("0.02")


def test_engie_xlsx_extracts_subscribed_power_from_segment_headers():
    workbook = (
        Path(__file__).resolve().parents[2]
        / "energie"
        / "ENGIE"
        / "FACTURES"
        / "MesFactures_20260609132103.xlsx"
    )
    if not workbook.exists():
        pytest.skip("ENGIE sample workbook unavailable")

    parsed = parse_engie_xlsx(workbook)
    sites = [site for entry in parsed for site in entry.get("sites", [])]
    missing = [site for site in sites if site.get("subscribed_power_kva") is None]

    assert sites
    assert len(missing) <= 1
