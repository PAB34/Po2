from datetime import date
from decimal import Decimal

from app.models.bpu import BpuDocument, BpuPriceComponent, BpuSegment, BpuTimePeriod
from app.services.invoice_bpu import (
    HistoricalBpuPrice,
    historical_bpu_prices_from_rows,
    historical_segment_code_for_site,
    normalize_bpu_supplier,
    resolve_historical_bpu_price,
)


def test_historical_bpu_rows_become_invoice_references() -> None:
    references = historical_bpu_prices_from_rows(
        [
            (
                BpuDocument(
                    id=4,
                    supplier="EDF",
                    valid_year=2024,
                    lot_number=1,
                    pdf_filename="BPU 2024 LOT 1 Elec.pdf",
                ),
                BpuSegment(id=8, segment_code="C4"),
                BpuTimePeriod(id=12, period_code="HPH"),
                BpuPriceComponent(component_type="fourniture", price_value_eur_per_mwh=Decimal("88.17")),
            )
        ]
    )

    assert references == [
        HistoricalBpuPrice(
            document_id=4,
            supplier="EDF",
            valid_year=2024,
            lot_number=1,
            segment_code="C4",
            period_code="HPH",
            component_type="fourniture",
            price_eur_per_mwh=Decimal("88.17"),
            pdf_filename="BPU 2024 LOT 1 Elec.pdf",
        )
    ]


def test_resolve_historical_bpu_price_requires_exact_period_context() -> None:
    reference = HistoricalBpuPrice(
        document_id=4,
        supplier="EDF",
        valid_year=2024,
        lot_number=1,
        segment_code="C4",
        period_code="HPH",
        component_type="fourniture",
        price_eur_per_mwh=Decimal("88.17"),
        pdf_filename="BPU 2024 LOT 1 Elec.pdf",
    )
    site = {"segment": "C4", "period_start": date(2024, 2, 1)}

    assert resolve_historical_bpu_price(
        [reference],
        site,
        {"normalized_component": "supply", "poste": "hph"},
    ) == reference
    assert resolve_historical_bpu_price(
        [reference],
        site,
        {"normalized_component": "supply", "poste": "hpe"},
    ) is None
    assert resolve_historical_bpu_price(
        [reference],
        {"segment": "C4", "period_start": date(2025, 2, 1)},
        {"normalized_component": "supply", "poste": "hph"},
    ) is None


def test_resolve_historical_bpu_price_keeps_ambiguous_market_docs_out() -> None:
    site = {"segment": "C2", "period_start": date(2022, 4, 1)}
    line = {"normalized_component": "capacity", "poste": "pointe"}
    references = [
        HistoricalBpuPrice(
            document_id=1,
            supplier="EDF",
            valid_year=2022,
            lot_number=1,
            segment_code="C2",
            period_code="POINTE",
            component_type="capacite",
            price_eur_per_mwh=Decimal("1.00"),
            pdf_filename="first.pdf",
        ),
        HistoricalBpuPrice(
            document_id=2,
            supplier="EDF",
            valid_year=2022,
            lot_number=1,
            segment_code="C2",
            period_code="POINTE",
            component_type="capacite",
            price_eur_per_mwh=Decimal("2.00"),
            pdf_filename="second.pdf",
        ),
    ]

    assert resolve_historical_bpu_price(references, site, line) is None


def test_bpu_supplier_and_segment_normalization_stays_conservative() -> None:
    assert normalize_bpu_supplier("Electricite de France") == "EDF"
    assert normalize_bpu_supplier("ENGIE Entreprises") == "ENGIE"
    assert historical_segment_code_for_site({"segment": "C5", "site_name": "Eclairage public centre"}) == "C5_EP"
    assert historical_segment_code_for_site({"segment": "C5", "site_name": "Gymnase"}) is None


def test_normalize_bpu_supplier_recognizes_totalenergies() -> None:
    assert normalize_bpu_supplier("TotalEnergies") == "TOTALENERGIES"
    assert normalize_bpu_supplier("TOTALENERGIES") == "TOTALENERGIES"
    assert normalize_bpu_supplier("Total Energies Gaz") == "TOTALENERGIES"
    assert normalize_bpu_supplier(None) is None
    assert normalize_bpu_supplier("inconnu") is None


def test_historical_segment_code_recognizes_gas_profiles() -> None:
    assert historical_segment_code_for_site({"segment": "T1"}) == "T1"
    assert historical_segment_code_for_site({"segment": "T2"}) == "T2"
    assert historical_segment_code_for_site({"segment": "T3"}) == "T3"
    assert historical_segment_code_for_site({"segment": "T4"}) == "T4"
    assert historical_segment_code_for_site({"segment": "t2"}) == "T2"
    assert historical_segment_code_for_site({"segment": "T5"}) is None


def test_resolve_historical_bpu_price_gas_lot7() -> None:
    reference = HistoricalBpuPrice(
        document_id=10,
        supplier="TOTALENERGIES",
        valid_year=2026,
        lot_number=7,
        segment_code="T2",
        period_code="BASE",
        component_type="cee_precarite",
        price_eur_per_mwh=Decimal("3.06"),
        pdf_filename="BPU_2026_Lots_1_2_et_7.xlsx",
    )
    site = {"segment": "T2", "period_start": date(2026, 3, 1)}

    resolved = resolve_historical_bpu_price(
        [reference],
        site,
        {"normalized_component": "cee_precarite", "poste": "base"},
    )
    assert resolved == reference

    # Un autre profil ne doit pas matcher
    assert resolve_historical_bpu_price(
        [reference],
        {"segment": "T1", "period_start": date(2026, 3, 1)},
        {"normalized_component": "cee_precarite", "poste": "base"},
    ) is None

    # Une année hors validité ne doit pas matcher
    assert resolve_historical_bpu_price(
        [reference],
        {"segment": "T2", "period_start": date(2025, 3, 1)},
        {"normalized_component": "cee_precarite", "poste": "base"},
    ) is None
