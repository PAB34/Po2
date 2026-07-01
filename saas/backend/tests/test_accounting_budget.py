import json
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.accounting_budget import AccountingBudgetLine
from app.models.accounting_matrix import AccountingMatrixContract, InvoiceAccountingSnapshot
from app.models.city import City
from app.models.cpe import CpeFinanceImportBatch, CpeFinanceInvoice
from app.schemas.accounting_budget import AccountingBudgetLineCreateIn, AccountingBudgetLineUpdateIn
from app.services import accounting_budget as svc


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


@pytest.fixture()
def contract(db_session):
    c = AccountingMatrixContract(
        city_id=1, domain="cpe", supplier="DALKIA",
        contract_code="C00190116O", contract_label="CPE Lot 1", status="active",
    )
    db_session.add(c)
    db_session.commit()
    return c


def _snapshot_json(*imputations: dict) -> str:
    return json.dumps({"lines": [{"imputations": list(imputations)}], "exceptions": []}, ensure_ascii=False)


def _add_cpe_invoice_snapshot(
    db_session, contract, *, invoice_date: date, amount: float, operation: str | None, status: str = "validated"
):
    batch = CpeFinanceImportBatch(city_id=1, filename="export.csv")
    db_session.add(batch)
    db_session.flush()
    invoice = CpeFinanceInvoice(
        batch_id=batch.id, city_id=1, invoice_number=f"F-{invoice_date.isoformat()}-{operation}",
        invoice_date=invoice_date, total_ht=amount,
    )
    db_session.add(invoice)
    db_session.flush()
    snapshot = InvoiceAccountingSnapshot(
        city_id=1, invoice_source="cpe_dalkia", invoice_id=str(invoice.id),
        matrix_contract_id=contract.id, status=status,
        snapshot_json=_snapshot_json({"operation": operation, "amount_allocated": amount}),
    )
    db_session.add(snapshot)
    db_session.commit()
    return snapshot


# ---------------------------------------------------------------------------
# CRUD lignes de budget
# ---------------------------------------------------------------------------
def test_create_then_list_budget_lines(db_session, contract):
    line = svc.create_budget_line(
        db_session, 1,
        AccountingBudgetLineCreateIn(matrix_contract_id=contract.id, year=2026, operation_number="OP-1", amount_budget=10000.0),
    )
    assert line.id is not None

    lines = svc.list_budget_lines(db_session, 1, contract.id, 2026)
    assert len(lines) == 1
    assert lines[0].operation_number == "OP-1"


def test_create_duplicate_operation_same_year_rejected(db_session, contract):
    svc.create_budget_line(
        db_session, 1,
        AccountingBudgetLineCreateIn(matrix_contract_id=contract.id, year=2026, operation_number="OP-1", amount_budget=1000.0),
    )
    with pytest.raises(ValueError):
        svc.create_budget_line(
            db_session, 1,
            AccountingBudgetLineCreateIn(matrix_contract_id=contract.id, year=2026, operation_number="OP-1", amount_budget=2000.0),
        )


def test_update_and_delete_budget_line(db_session, contract):
    line = svc.create_budget_line(
        db_session, 1,
        AccountingBudgetLineCreateIn(matrix_contract_id=contract.id, year=2026, operation_number="OP-1", amount_budget=1000.0),
    )
    updated = svc.update_budget_line(db_session, 1, line.id, AccountingBudgetLineUpdateIn(amount_budget=1500.0))
    assert updated.amount_budget == 1500.0

    svc.delete_budget_line(db_session, 1, line.id)
    assert svc.list_budget_lines(db_session, 1, contract.id, 2026) == []


def test_budget_lines_are_city_scoped(db_session, contract):
    svc.create_budget_line(
        db_session, 1,
        AccountingBudgetLineCreateIn(matrix_contract_id=contract.id, year=2026, operation_number="OP-1", amount_budget=1000.0),
    )
    with pytest.raises(ValueError):
        svc.list_budget_lines(db_session, 2, contract.id, 2026)


# ---------------------------------------------------------------------------
# Réalisé par opération
# ---------------------------------------------------------------------------
def test_realized_sums_amount_allocated_by_operation_for_matching_year(db_session, contract):
    _add_cpe_invoice_snapshot(db_session, contract, invoice_date=date(2026, 3, 1), amount=500.0, operation="OP-1")
    _add_cpe_invoice_snapshot(db_session, contract, invoice_date=date(2026, 6, 1), amount=300.0, operation="OP-1")
    _add_cpe_invoice_snapshot(db_session, contract, invoice_date=date(2026, 2, 1), amount=200.0, operation="OP-2")
    # Année différente : ne doit pas polluer 2026.
    _add_cpe_invoice_snapshot(db_session, contract, invoice_date=date(2025, 12, 1), amount=999.0, operation="OP-1")
    # Snapshot non figé : ignoré.
    _add_cpe_invoice_snapshot(db_session, contract, invoice_date=date(2026, 4, 1), amount=50.0, operation="OP-1", status="proposed")

    realized = svc.compute_realized_by_operation(db_session, 1, contract.id, 2026)
    assert realized["by_operation"] == {"OP-1": 800.0, "OP-2": 200.0}
    assert realized["snapshots_included"] == 3
    assert realized["snapshots_excluded_other_year"] == 1
    assert realized["snapshots_excluded_unknown_year"] == 0


def test_realized_excludes_snapshots_with_unresolved_year(db_session, contract):
    snapshot = InvoiceAccountingSnapshot(
        city_id=1, invoice_source="unbranched_source", invoice_id="42",
        matrix_contract_id=contract.id, status="validated",
        snapshot_json=_snapshot_json({"operation": "OP-1", "amount_allocated": 100.0}),
    )
    db_session.add(snapshot)
    db_session.commit()

    realized = svc.compute_realized_by_operation(db_session, 1, contract.id, 2026)
    assert realized["by_operation"] == {}
    assert realized["snapshots_excluded_unknown_year"] == 1


def test_realized_tracks_unassigned_amount_without_operation(db_session, contract):
    _add_cpe_invoice_snapshot(db_session, contract, invoice_date=date(2026, 1, 15), amount=75.0, operation=None)
    realized = svc.compute_realized_by_operation(db_session, 1, contract.id, 2026)
    assert realized["by_operation"] == {}
    assert realized["unassigned_amount"] == 75.0


# ---------------------------------------------------------------------------
# Suivi (budget vs réalisé vs atterrissage pro-rata)
# ---------------------------------------------------------------------------
def test_suivi_combines_budget_and_realized_with_prorata_landing(db_session, contract):
    svc.create_budget_line(
        db_session, 1,
        AccountingBudgetLineCreateIn(matrix_contract_id=contract.id, year=2026, operation_number="OP-1", amount_budget=2000.0),
    )
    _add_cpe_invoice_snapshot(db_session, contract, invoice_date=date(2026, 1, 1), amount=500.0, operation="OP-1")

    # Milieu d'année exact -> pro-rata x2.
    suivi = svc.compute_suivi(db_session, 1, contract.id, 2026, today=date(2026, 7, 2))
    row = next(r for r in suivi["rows"] if r["operation_number"] == "OP-1")
    assert row["amount_budget"] == 2000.0
    assert row["amount_realized"] == 500.0
    assert row["amount_landing"] == pytest.approx(1000.0, rel=0.02)
    assert suivi["snapshots_total"] == 1


def test_suivi_reports_data_completeness_note_when_years_unresolved(db_session, contract):
    snapshot = InvoiceAccountingSnapshot(
        city_id=1, invoice_source="unbranched_source", invoice_id="1",
        matrix_contract_id=contract.id, status="validated",
        snapshot_json=_snapshot_json({"operation": "OP-1", "amount_allocated": 100.0}),
    )
    db_session.add(snapshot)
    db_session.commit()

    suivi = svc.compute_suivi(db_session, 1, contract.id, 2026, today=date(2026, 7, 2))
    assert suivi["snapshots_excluded_unknown_year"] == 1
    assert "n'ont pas pu être rattachées" in suivi["data_completeness_note"]


def test_suivi_unknown_contract_raises(db_session):
    with pytest.raises(ValueError):
        svc.compute_suivi(db_session, 1, 999, 2026)
