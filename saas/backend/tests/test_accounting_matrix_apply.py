import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.accounting_matrix import (
    AccountingMatrixContract,
    AccountingMatrixRule,
    AccountingMatrixVersion,
)
from app.services import accounting_matrix_apply as apply_svc
from app.services.accounting_matrix_apply import InvoiceLine


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
        city_id=1, domain="fluides", supplier="ENGIE",
        contract_code="LOT1", contract_label="ENGIE", status="active",
    )
    db_session.add(c)
    db_session.flush()
    v = AccountingMatrixVersion(matrix_contract_id=c.id, version_label="V1", status="active", source="manuel")
    db_session.add(v)
    db_session.flush()
    db_session.add_all([
        AccountingMatrixRule(
            matrix_version_id=v.id, stable_rule_key="k-abo", scope="billed_item",
            billed_item_pattern="Abonnement", accounting_nature="6061",
            accounting_service="EAU", allocation_percent=100.0, priority=0,
        ),
        AccountingMatrixRule(
            matrix_version_id=v.id, stable_rule_key="k-conso", scope="billed_item",
            billed_item_pattern="Consommation", accounting_nature="60612",
            allocation_percent=100.0, priority=0,
        ),
    ])
    db_session.commit()
    return c


# ---- moteur pur -----------------------------------------------------------
def test_engine_matches_and_flags_unmatched(contract, db_session):
    version = contract.versions[0]
    rules = list(version.rules)
    lines = [
        InvoiceLine(billed_item="Abonnement mensuel", amount=120.0),
        InvoiceLine(billed_item="Taxe inconnue", amount=10.0),
    ]
    result = apply_svc.apply_matrix(rules, lines)
    assert result["matched_lines"] == 1
    assert result["lines"][0]["imputations"][0]["nature"] == "6061"
    assert result["lines"][0]["imputations"][0]["amount_allocated"] == 120.0
    assert len(result["exceptions"]) == 1
    assert result["exceptions"][0]["line_index"] == 1


# ---- cycle de vie ---------------------------------------------------------
def test_apply_creates_proposed_snapshot(contract, db_session):
    snap = apply_svc.apply_to_invoice(
        db_session, 1, source="energy_import", invoice_id="F-1",
        contract_id=contract.id, lines=[InvoiceLine(billed_item="Abonnement", amount=50.0)],
    )
    assert snap.status == "proposed"
    assert snap.matrix_version_id == contract.versions[0].id


def test_validate_blocked_by_exceptions(contract, db_session):
    apply_svc.apply_to_invoice(
        db_session, 1, source="energy_import", invoice_id="F-2",
        contract_id=contract.id, lines=[InvoiceLine(billed_item="Inconnu", amount=5.0)],
    )
    with pytest.raises(ValueError):
        apply_svc.validate_snapshot(db_session, 1, source="energy_import", invoice_id="F-2", user_id=1)


def test_validate_then_apply_is_refused(contract, db_session):
    apply_svc.apply_to_invoice(
        db_session, 1, source="energy_import", invoice_id="F-3",
        contract_id=contract.id, lines=[InvoiceLine(billed_item="Abonnement", amount=50.0)],
    )
    snap = apply_svc.validate_snapshot(db_session, 1, source="energy_import", invoice_id="F-3", user_id=1)
    assert snap.status == "validated"
    # Réimport / ré-application d'une facture figée : refusé (doc 35 critère 2).
    with pytest.raises(ValueError):
        apply_svc.apply_to_invoice(
            db_session, 1, source="energy_import", invoice_id="F-3",
            contract_id=contract.id, lines=[InvoiceLine(billed_item="Abonnement", amount=999.0)],
        )


def test_snapshot_keeps_old_version_after_new_version(contract, db_session):
    apply_svc.apply_to_invoice(
        db_session, 1, source="energy_import", invoice_id="F-4",
        contract_id=contract.id, lines=[InvoiceLine(billed_item="Abonnement", amount=50.0)],
    )
    snap = apply_svc.validate_snapshot(db_session, 1, source="energy_import", invoice_id="F-4", user_id=1)
    pinned = snap.matrix_version_id

    # Une nouvelle version est créée et activée ensuite.
    v2 = AccountingMatrixVersion(matrix_contract_id=contract.id, version_label="V2", status="active", source="manuel")
    db_session.add(v2)
    db_session.commit()

    db_session.refresh(snap)
    assert snap.matrix_version_id == pinned  # immutabilité (doc 35 critère 5)


def test_export_finance_flow(contract, db_session):
    apply_svc.apply_to_invoice(
        db_session, 1, source="energy_import", invoice_id="F-5",
        contract_id=contract.id, lines=[InvoiceLine(billed_item="Abonnement", amount=50.0)],
    )
    apply_svc.validate_snapshot(db_session, 1, source="energy_import", invoice_id="F-5", user_id=1)
    snap = apply_svc.export_finance(db_session, 1, source="energy_import", invoice_id="F-5")
    assert snap.status == "exported"
    assert snap.exported_at is not None
    # snapshot_json bien sérialisé
    assert json.loads(snap.snapshot_json)["matched_lines"] == 1
