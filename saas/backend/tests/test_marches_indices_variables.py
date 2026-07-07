from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe import (
    CpeContractReference,
    CpeFinanceImportBatch,
    CpeFinanceInvoice,
    CpeFinanceLine,
    CpeRevisionIndex,
)
from app.models.gas_revisable import GasSupplyRevisablePrice
from app.services.marches_indices_variables import build_indices_variables


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.add(
            CpeContractReference(
                city_id=1,
                contract_code="C00190116O",
                contract_label="LOT 1",
                reference_kind="cpe_contract_scope",
                year=2026,
                market="SCOPE",
                billed_item="CPE_VILLE_LOT_1",
                active=True,
            )
        )
        session.commit()
        yield session


def _series(report: dict, code: str) -> dict:
    return next(item for item in report["series"] if item["code"] == code)


def test_build_indices_variables_normalizes_existing_sources(db_session):
    db_session.add_all(
        [
            CpeRevisionIndex(city_id=1, index_code="ICHT_IME", year=2026, quarter=1, value=131.2, source="DALKIA"),
            CpeRevisionIndex(city_id=1, index_code="FSD2", year=2026, quarter=1, value=118.4, source="DALKIA"),
            GasSupplyRevisablePrice(city_id=1, annee=2026, mois=2, fourniture_eur_mwh=41.5, source="PEG mensuel"),
        ]
    )
    batch = CpeFinanceImportBatch(city_id=1, filename="fin.xlsx")
    db_session.add(batch)
    db_session.flush()
    invoice = CpeFinanceInvoice(
        batch_id=batch.id,
        city_id=1,
        invoice_number="INV-REV-1",
        contract_code="C00190116O",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        total_ht=0.0,
    )
    db_session.add(invoice)
    db_session.flush()
    db_session.add(
        CpeFinanceLine(
            batch_id=batch.id,
            invoice_id=invoice.id,
            city_id=1,
            row_number=1,
            contract_code="C00190116O",
            invoice_number="INV-REV-1",
            market="P2",
            billed_item="P2",
            amount_ht=100.0,
            base_price=1000.0,
            revised_price=1100.0,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
        )
    )
    db_session.commit()

    report = build_indices_variables(db_session, city_id=1, year_from=2025, year_to=2026)

    assert report["year_from"] == 2025
    assert report["year_to"] == 2026
    assert _series(report, "ICHT_IME")["points"] == [
        {"period": "2026-T1", "value": 131.2, "label": "ICHT-IME", "source": "DALKIA"}
    ]
    assert _series(report, "PEG_GAZ")["points"] == [
        {"period": "2026-02", "value": 41.5, "label": "PEG gaz", "source": "PEG mensuel"}
    ]
    observed = _series(report, "DALKIA_COEF_OBSERVE_P2")
    assert observed["points"][0]["period"] == "2026-T1"
    assert observed["points"][0]["value"] == 1.1
    assert _series(report, "TURPE_EVOLUTION_HTA_BT")["points"]
    assert _series(report, "TURPE_INDEX_CUMULE_HTA_BT")["points"]




def test_build_indices_variables_aggregates_observed_factor_by_market_period(db_session):
    db_session.add(CpeRevisionIndex(city_id=1, index_code="ICHT_IME", year=2026, quarter=1, value=131.2))
    batch = CpeFinanceImportBatch(city_id=1, filename="fin.xlsx")
    db_session.add(batch)
    db_session.flush()
    invoice = CpeFinanceInvoice(
        batch_id=batch.id,
        city_id=1,
        invoice_number="INV-REV-AGG",
        contract_code="C00190116O",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        total_ht=0.0,
    )
    db_session.add(invoice)
    db_session.flush()
    for row_number, base_price, revised_price in [(1, 1000.0, 1100.0), (2, 1000.0, 1200.0)]:
        db_session.add(
            CpeFinanceLine(
                batch_id=batch.id,
                invoice_id=invoice.id,
                city_id=1,
                row_number=row_number,
                contract_code="C00190116O",
                invoice_number="INV-REV-AGG",
                market="P2",
                billed_item="P2",
                amount_ht=100.0,
                base_price=base_price,
                revised_price=revised_price,
                period_start=date(2026, 1, 1),
                period_end=date(2026, 3, 31),
            )
        )
    db_session.commit()

    report = build_indices_variables(db_session, city_id=1, year_from=2026, year_to=2026)

    observed_points = _series(report, "DALKIA_COEF_OBSERVE_P2")["points"]
    assert observed_points == [
        {"period": "2026-T1", "value": 1.15, "label": "2 ligne(s) facture", "source": "INV-REV-AGG"}
    ]
def test_build_indices_variables_swaps_inverted_years(db_session):
    report = build_indices_variables(db_session, city_id=1, year_from=2026, year_to=2025)

    assert report["year_from"] == 2025
    assert report["year_to"] == 2026

def test_bpu_fourniture_series_by_typologie(db_session, monkeypatch):
    from decimal import Decimal
    from app.services import marches_indices_variables as mod
    from app.services.invoice_bpu import HistoricalBpuPrice

    def _p(supplier, year, seg, price):
        return HistoricalBpuPrice(
            document_id=1, supplier=supplier, valid_year=year, lot_number=1,
            segment_code=seg, period_code="HPH", component_type="fourniture",
            price_eur_per_mwh=Decimal(str(price)), pdf_filename="x.pdf",
        )

    fake = {
        "ENGIE": [_p("ENGIE", 2026, "BATIMENT_HTA", 110.0), _p("ENGIE", 2026, "BATIMENT_BT36", 76.0)],
        "EDF": [_p("EDF", 2025, "C2", 84.0), _p("EDF", 2025, "C5_EP", 46.0), _p("EDF", 2026, "ECLAIRAGE_PUBLIC", 75.0)],
    }
    monkeypatch.setattr(mod, "load_historical_bpu_prices", lambda db, s: fake.get(s, []))

    report = build_indices_variables(db_session, city_id=1, year_from=2025, year_to=2026)
    bpu = [s for s in report["series"] if s["family"] == "elec_bpu"]
    codes = {s["code"] for s in bpu}
    assert "BPU_FOURNITURE_HTA" in codes and "BPU_FOURNITURE_EP" in codes
    hta = _series(report, "BPU_FOURNITURE_HTA")
    assert hta["unit"] == "EUR/MWh" and hta["family"] == "elec_bpu"
    # HTA : 2025 = C2 (84), 2026 = BATIMENT_HTA (110)
    vals = {p["period"]: p["value"] for p in hta["points"]}
    assert vals.get("2025") == 84.0 and vals.get("2026") == 110.0
    # EP : 2025 = C5_EP (46), 2026 = ECLAIRAGE_PUBLIC (75)
    ep = {p["period"]: p["value"] for p in _series(report, "BPU_FOURNITURE_EP")["points"]}
    assert ep.get("2025") == 46.0 and ep.get("2026") == 75.0
