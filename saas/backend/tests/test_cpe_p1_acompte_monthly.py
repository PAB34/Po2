"""Le controle d'acompte P1 gaz ne doit se declencher que pour des periodes REELLEMENT
trimestrielles. Une facture mensuelle finissant un dernier jour de mois de fin de trimestre
(ex. 01/03 -> 31/03) ne doit plus produire d'ecart (le scope_query n'agregeait alors qu'un
seul mois et le comparait au trimestre complet)."""
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


def _make_p1_invoice(
    db: Session,
    batch_id: int,
    number: str,
    amount: float,
    *,
    period_start: date,
    period_end: date,
) -> CpeFinanceInvoice:
    invoice = CpeFinanceInvoice(
        batch_id=batch_id,
        city_id=1,
        invoice_number=number,
        contract_code="C00190116O",
        period_start=period_start,
        period_end=period_end,
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
            period_start=period_start,
            period_end=period_end,
        )
    )
    db.flush()
    return invoice


def _p1_controls(db: Session) -> list[CpeFinanceControl]:
    return list(
        db.scalars(
            select(CpeFinanceControl).where(
                CpeFinanceControl.control_type == "p1_gaz_acompte_dpgf"
            )
        )
    )


def test_monthly_invoice_ending_quarter_not_applied(db_session):
    """Facture MENSUELLE 01/03 -> 31/03 : controle non applique, pas d'ecart (statut ok)."""
    batch = CpeFinanceImportBatch(city_id=1, filename="lot.xlsx")
    db_session.add(batch)
    db_session.flush()
    invoice = _make_p1_invoice(
        db_session,
        batch.id,
        "CFF4",
        37539.0,
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
    )
    db_session.commit()

    recompute_finance_invoice_controls(db_session, invoice)

    controls = _p1_controls(db_session)
    assert len(controls) == 1
    control = controls[0]
    assert control.status == "ok"
    assert control.delta_abs is None  # aucun ecart calcule : controle non applique
    assert "non applique" in control.message


def test_real_quarter_invoice_is_controlled(db_session):
    """Vraie facture TRIMESTRIELLE 01/01 -> 31/03 : controle applique, INFORMATIF (acompte
    provisionnel, pas d'erreur sur l'ecart au quart theorique)."""
    batch = CpeFinanceImportBatch(city_id=1, filename="lot.xlsx")
    db_session.add(batch)
    db_session.flush()
    invoice = _make_p1_invoice(
        db_session,
        batch.id,
        "TRIM-Q1",
        83001.0,  # ecart au quart theorique 79443.74 -> informatif, pas une erreur
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
    )
    db_session.commit()

    recompute_finance_invoice_controls(db_session, invoice)

    controls = _p1_controls(db_session)
    assert len(controls) == 1
    control = controls[0]
    assert control.status == "ok"
    assert control.severity == "info"
    assert control.expected_revised_price == 79443.74
    assert control.actual_revised_price == 83001.0


def test_monthly_and_quarter_coexist_no_double_count(db_session):
    """Lot mixte : la facture mensuelle de mars n'est pas agregee dans le trimestre Q1.

    Reproduit le cas reel : une vraie facture trimestrielle (01/01 -> 31/03) coexiste avec une
    facture mensuelle (01/03 -> 31/03). Seule la trimestrielle est controlee (sur sa propre
    fenetre), la mensuelle reste 'non applique' -> pas de double comptage ni d'ecart parasite.
    """
    batch = CpeFinanceImportBatch(city_id=1, filename="lot.xlsx")
    db_session.add(batch)
    db_session.flush()
    quarter_invoice = _make_p1_invoice(
        db_session,
        batch.id,
        "TRIM-Q1",
        79443.74,  # pile l'attendu -> ok
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
    )
    monthly_invoice = _make_p1_invoice(
        db_session,
        batch.id,
        "CFF4",
        37539.0,
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
    )
    db_session.commit()

    recompute_finance_invoice_controls(db_session, quarter_invoice)
    recompute_finance_invoice_controls(db_session, monthly_invoice)

    controls = {c.invoice_id: c for c in _p1_controls(db_session)}
    # Le controle trimestriel n'agrege que la fenetre Q1 (79443.74), pas le mois de mars.
    assert controls[quarter_invoice.id].status == "ok"
    assert controls[quarter_invoice.id].actual_revised_price == 79443.74
    # La facture mensuelle reste non appliquee (pas d'ecart parasite).
    assert controls[monthly_invoice.id].status == "ok"
    assert controls[monthly_invoice.id].delta_abs is None
