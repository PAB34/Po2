"""Le contrôle d'acompte P1 gaz est un agrégat de lot : il ne doit être émis qu'une
seule fois par (lot, contrat, période), pas dupliqué sur chaque facture P1 du trimestre."""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe import (
    CpeContractReference,
    CpeFinanceControl,
    CpeFinanceImportBatch,
    CpeFinanceInvoice,
    CpeFinanceLine,
)
from app.services.cpe_accounting import recompute_finance_invoice_controls


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
                billed_item="CPE",
                active=True,
            )
        )
        session.add(
            CpeContractReference(
                city_id=1,
                contract_code="C00190116O",
                contract_label="LOT 1",
                reference_kind="p1_gaz_acompte",
                year=2026,
                market="P1",
                billed_item="P1",
                annual_amount_ht=317774.96,  # /4 = 79443.74
                installment_count=4,
                expected_period_months="3,6,9",
                tolerance_pct=0.01,
                tolerance_eur=100.0,
                active=True,
            )
        )
        session.commit()
        yield session


def _make_p1_invoice(db: Session, batch_id: int, number: str, amount: float) -> CpeFinanceInvoice:
    invoice = CpeFinanceInvoice(
        batch_id=batch_id,
        city_id=1,
        invoice_number=number,
        contract_code="C00190116O",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        invoice_date=date(2026, 4, 5),
        due_date=date(2026, 5, 5),
        total_ht=amount,
    )
    db.add(invoice)
    db.flush()
    db.add(
        CpeFinanceLine(
            batch_id=batch_id,
            invoice_id=invoice.id,
            city_id=1,
            row_number=1,
            contract_code="C00190116O",
            market="P1",
            billed_item="P1",
            amount_ht=amount,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
        )
    )
    db.flush()
    return invoice


def test_p1_acompte_control_emitted_once_per_lot_period(db_session):
    batch = CpeFinanceImportBatch(city_id=1, filename="lot.xlsx")
    db_session.add(batch)
    db_session.flush()
    # 3 factures P1 du même trimestre, total lot = 90000 (acompte provisionnel < annuel révisé)
    invoices = [
        _make_p1_invoice(db_session, batch.id, "INV-A", 30000.0),
        _make_p1_invoice(db_session, batch.id, "INV-B", 30000.0),
        _make_p1_invoice(db_session, batch.id, "INV-C", 30000.0),
    ]
    db_session.commit()

    for invoice in invoices:
        recompute_finance_invoice_controls(db_session, invoice)

    p1_controls = list(
        db_session.scalars(
            select(CpeFinanceControl).where(CpeFinanceControl.control_type == "p1_gaz_acompte_dpgf")
        )
    )
    # Un seul contrôle P1 acompte pour tout le lot/trimestre (pas 3).
    assert len(p1_controls) == 1
    control = p1_controls[0]
    # Porté par la facture de plus petit id (INV-A).
    assert control.invoice_id == invoices[0].id
    # Le montant agrégé est bien la somme du lot, pas celui d'une facture isolée.
    assert control.actual_revised_price == 90000.0
    assert control.expected_revised_price == 79443.74
    # Acompte provisionnel : informatif (pas d'erreur sur l'écart au quart théorique).
    assert control.status == "ok"
    assert control.severity == "info"
    assert "3 factures P1" in control.message


def test_p1_acompte_error_when_quarter_exceeds_annual(db_session):
    """Garde-fou zéro tolérance : un acompte trimestriel > P1 annuel révisé est impossible."""
    batch = CpeFinanceImportBatch(city_id=1, filename="lot.xlsx")
    db_session.add(batch)
    db_session.flush()
    # Lot trimestriel = 320000 > annuel révisé 317774.96 -> erreur.
    invoice = _make_p1_invoice(db_session, batch.id, "INV-XL", 320000.0)
    db_session.commit()

    recompute_finance_invoice_controls(db_session, invoice)

    control = db_session.scalars(
        select(CpeFinanceControl).where(CpeFinanceControl.control_type == "p1_gaz_acompte_dpgf")
    ).one()
    assert control.status == "error"
    assert control.expected_revised_price == 317774.96
    assert control.actual_revised_price == 320000.0
