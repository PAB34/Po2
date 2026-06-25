from io import BytesIO

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.accounting_matrix import (
    AccountingMatrixContract,
    AccountingMatrixRule,
    AccountingMatrixVersion,
)
from app.services import accounting_matrix_xlsx as xlsx_svc


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


@pytest.fixture()
def contract_with_active_version(db_session):
    contract = AccountingMatrixContract(
        city_id=1, domain="fluides", supplier="ENGIE",
        contract_code="LOT1", contract_label="Fourniture ENGIE", status="active",
    )
    db_session.add(contract)
    db_session.flush()
    version = AccountingMatrixVersion(
        matrix_contract_id=contract.id, version_label="V1", status="active", source="manuel",
    )
    db_session.add(version)
    db_session.flush()
    db_session.add_all([
        AccountingMatrixRule(
            matrix_version_id=version.id, stable_rule_key="r-abonnement", scope="billed_item",
            billed_item_pattern="Abonnement", accounting_nature="6061", allocation_percent=100.0,
        ),
        AccountingMatrixRule(
            matrix_version_id=version.id, stable_rule_key="r-conso", scope="billed_item",
            billed_item_pattern="Consommation", accounting_nature="60612", allocation_percent=100.0,
        ),
    ])
    db_session.commit()
    return contract, version


def _make_xlsx(rows: list[dict]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Matrice"
    ws.append(xlsx_svc.COLUMNS)
    for row in rows:
        ws.append([row.get(col) for col in xlsx_svc.COLUMNS])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_export_roundtrip_is_unchanged(db_session, contract_with_active_version):
    contract, version = contract_with_active_version
    content, filename = xlsx_svc.export_version_xlsx(db_session, 1, version.id)
    assert filename.endswith(".xlsx")

    preview = xlsx_svc.preview_import(db_session, 1, contract.id, content)
    assert preview["structural_errors"] == []
    assert preview["summary"]["inchange"] == 2
    assert preview["summary"]["ajout"] == 0
    assert preview["summary"]["modifie"] == 0
    assert preview["can_commit"] is True


def test_preview_detects_add_modify_and_missing(db_session, contract_with_active_version):
    contract, _ = contract_with_active_version
    raw = _make_xlsx([
        # clé existante, nature modifiée -> modifie
        {"stable_rule_key": "r-abonnement", "scope": "billed_item",
         "billed_item_pattern": "Abonnement", "accounting_nature": "9999", "allocation_percent": 100},
        # clé neuve -> ajout
        {"stable_rule_key": "r-cee", "scope": "billed_item",
         "billed_item_pattern": "CEE", "accounting_nature": "6061", "allocation_percent": 100},
    ])
    preview = xlsx_svc.preview_import(db_session, 1, contract.id, raw)
    assert preview["summary"]["modifie"] == 1
    assert preview["summary"]["ajout"] == 1
    # r-conso est dans la version de référence mais absent du fichier -> signalé, pas supprimé.
    assert "r-conso" in preview["absentes_du_fichier"]


def test_preview_flags_errors(db_session, contract_with_active_version):
    contract, _ = contract_with_active_version
    raw = _make_xlsx([
        {"stable_rule_key": None, "scope": "billed_item", "accounting_nature": "6061", "allocation_percent": 100},
        {"stable_rule_key": "r-bad", "scope": "billed_item", "accounting_nature": "6061", "allocation_percent": 150},
    ])
    preview = xlsx_svc.preview_import(db_session, 1, contract.id, raw)
    assert preview["summary"]["erreurs"] == 2
    assert preview["can_commit"] is False


def test_commit_creates_draft_without_touching_active(db_session, contract_with_active_version):
    contract, active = contract_with_active_version
    raw = _make_xlsx([
        {"stable_rule_key": "r-abonnement", "scope": "billed_item",
         "billed_item_pattern": "Abonnement", "accounting_nature": "6061", "allocation_percent": 100},
    ])
    result = xlsx_svc.commit_import(
        db_session, 1, contract.id, raw, version_label="V2 import", user_id=1,
    )
    assert result["status"] == "draft"
    assert result["source"] == "import_xlsx"
    assert result["id"] != active.id

    db_session.refresh(active)
    assert active.status == "active"
    assert len(active.rules) == 2  # version active jamais mutée


def test_commit_rejects_invalid_file(db_session, contract_with_active_version):
    contract, _ = contract_with_active_version
    raw = _make_xlsx([
        {"stable_rule_key": "r-x", "scope": "billed_item", "accounting_nature": None, "allocation_percent": 100},
    ])
    with pytest.raises(ValueError):
        xlsx_svc.commit_import(db_session, 1, contract.id, raw, version_label="V2", user_id=1)
