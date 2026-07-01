import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.accounting_matrix import (
    AccountingMatrixContract,
    AccountingMatrixRule,
    AccountingMatrixVersion,
)
from app.models.city import City
from app.schemas.accounting_matrix import AccountingMatrixRuleCreateIn, AccountingMatrixRuleUpdateIn
from app.services import accounting_matrix as svc


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


def _make_version(db_session, status: str) -> AccountingMatrixVersion:
    contract = AccountingMatrixContract(city_id=1, domain="cpe", supplier="DALKIA", contract_code="C1", status="active")
    db_session.add(contract)
    db_session.flush()
    version = AccountingMatrixVersion(matrix_contract_id=contract.id, version_label="V0", status=status, source="manuel")
    db_session.add(version)
    db_session.flush()
    rule = AccountingMatrixRule(
        matrix_version_id=version.id, stable_rule_key="k1", scope="billed_item",
        billed_item_pattern="P1", accounting_nature="60621", allocation_percent=100.0,
    )
    db_session.add(rule)
    db_session.commit()
    return version


def test_edit_active_version_rule_is_allowed(db_session):
    version = _make_version(db_session, "active")
    rule = version.rules[0]
    updated = svc.update_rule(
        db_session, 1, rule.id,
        AccountingMatrixRuleUpdateIn(accounting_service="4021", accounting_antenna="NORD", operation_number="OP-1"),
    )
    assert updated.accounting_service == "4021"
    assert updated.accounting_antenna == "NORD"
    assert updated.operation_number == "OP-1"


def test_create_and_delete_rule_on_active_version(db_session):
    version = _make_version(db_session, "active")
    created = svc.create_rule(
        db_session, 1, version.id,
        AccountingMatrixRuleCreateIn(stable_rule_key="k2", billed_item_pattern="P2", accounting_nature="6156"),
    )
    assert created.id is not None
    svc.delete_rule(db_session, 1, created.id)
    remaining = [r.stable_rule_key for r in svc.list_version_rules(db_session, 1, version.id)]
    assert remaining == ["k1"]


def test_archived_version_stays_frozen(db_session):
    version = _make_version(db_session, "archived")
    rule = version.rules[0]
    with pytest.raises(ValueError):
        svc.update_rule(db_session, 1, rule.id, AccountingMatrixRuleUpdateIn(accounting_service="X"))
    with pytest.raises(ValueError):
        svc.create_rule(db_session, 1, version.id, AccountingMatrixRuleCreateIn(stable_rule_key="k9", accounting_nature="60621"))
    with pytest.raises(ValueError):
        svc.delete_rule(db_session, 1, rule.id)
