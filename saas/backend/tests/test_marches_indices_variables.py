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


def test_build_indices_variables_swaps_inverted_years(db_session):
    report = build_indices_variables(db_session, city_id=1, year_from=2026, year_to=2025)

    assert report["year_from"] == 2025
    assert report["year_to"] == 2026