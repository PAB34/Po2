from decimal import Decimal
from pathlib import Path

import pytest

from app.services.invoice_parsers.engie_xlsx import (
    _coerce_decimal,
    parse_engie_xlsx,
    resolve_soutirage_variable,
)


def test_soutirage_variable_price_column_holding_amount():
    # Cas normal (feuille C3/C4) : colonne = vrai prix €/kWh.
    unit_price, amount = resolve_soutirage_variable(14546.0, 0.0101)
    assert unit_price == 0.0101
    assert round(amount, 2) == round(14546.0 * 0.0101, 2)

    # Cas C5 : la colonne « prix (€) » contient le MONTANT (230,43) → ne pas remultiplier.
    unit_price, amount = resolve_soutirage_variable(4761.0, 230.43)
    assert amount == 230.43
    assert round(unit_price, 4) == round(230.43 / 4761.0, 4)

    # Avoir/régularisation (quantité et montant négatifs) → prix unitaire recalculé positif.
    unit_price, amount = resolve_soutirage_variable(-6598.0, -319.34)
    assert amount == -319.34
    assert round(unit_price, 4) == round(-319.34 / -6598.0, 4)


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
