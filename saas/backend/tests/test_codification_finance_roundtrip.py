"""Aller-retour du gabarit finance COMBINE de codification (DALKIA + ENGIE/EDF).

export (build_finance_codification_workbook) -> import
(import_finance_codification_workbook) doit restituer les 4 jeux à l'identique
(Actif / Opération / Notes / fournisseur EDF compris) et l'export DALKIA est scopé
au marché Ville en cours.
"""
from __future__ import annotations

import io

import openpyxl
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe import CpeAccountingNatureRule, CpeAccountingSiteMapping, CpeContractReference
from app.models.invoice import EnergyAccountingNatureRule, EnergyAccountingSiteMapping
from app.services.cpe_accounting import list_accounting_nature_rules, list_accounting_site_mappings
from app.services.codification_finance import (
    build_finance_codification_workbook,
    import_finance_codification_workbook,
    SHEET_DALKIA_POSTES,
)
from app.services import energie_accounting


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


def _seed_scope(db: Session) -> None:
    for code, lot in (("C00190116O", "1"), ("C00190155J", "2")):
        db.add(
            CpeContractReference(
                city_id=1, contract_code=code, reference_kind="cpe_contract_scope",
                year=2026, market="SCOPE", billed_item=f"CPE_VILLE_LOT_{lot}", active=True,
            )
        )
    db.commit()


def _seed_all(db: Session) -> None:
    _seed_scope(db)
    db.add(CpeAccountingSiteMapping(
        city_id=1, code_site="VDS-BAM 08", site_name="CTM", service_code="MABA",
        function_code="020", antenna_code="CTM", active=True, notes="site test",
    ))
    db.add(CpeAccountingNatureRule(
        city_id=1, contract_code="C00190116O", market="P3", billed_item="P3.4",
        accounting_nature="21351", active=True, notes="invest",
    ))
    db.add(CpeAccountingNatureRule(  # HORS périmètre -> ne doit pas ressortir à l'export
        city_id=1, contract_code="C00025811F", market="P2", billed_item="P2-11",
        accounting_nature="6156", active=True,
    ))
    db.add(EnergyAccountingSiteMapping(
        city_id=1, prm_id="14500001", site_name="Ecole", service_code="ENS",
        function_code="211", antenna_code="A VARDA", active=False, notes="prm test",
    ))
    db.add(EnergyAccountingNatureRule(
        city_id=1, supplier="EDF", market="C5", billed_item="ABONNEMENT",
        accounting_nature="60612", active=True, notes="edf",
    ))
    db.commit()


def test_combined_export_then_import_roundtrip(db_session: Session) -> None:
    _seed_all(db_session)
    content = build_finance_codification_workbook(db_session, city_id=1)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as fresh:
        fresh.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        fresh.commit()
        res = import_finance_codification_workbook(fresh, content, filename="gabarit", city_id=1)
        assert res.errors == []
        assert res.dalkia_sites_created == 1
        assert res.dalkia_rules_created == 1  # seul le poste en périmètre est exporté
        assert res.energy_points_created == 1
        assert res.energy_rules_created == 1

        site = list_accounting_site_mappings(fresh, 1)[0]
        assert site.code_site == "VDS-BAM 08"
        assert site.service_code == "MABA"
        assert site.notes == "site test"

        point = energie_accounting.list_site_mappings(fresh, 1)[0]
        assert point.prm_id == "14500001"
        assert point.active is False  # l'état inactif survit
        assert point.antenna_code == "A VARDA"

        erule = energie_accounting.list_nature_rules(fresh, 1)[0]
        assert erule.supplier == "EDF"  # fournisseur préservé
        assert erule.accounting_nature == "60612"


def test_export_dalkia_sheet_scoped_to_current_market(db_session: Session) -> None:
    _seed_all(db_session)
    content = build_finance_codification_workbook(db_session, city_id=1)
    wb = openpyxl.load_workbook(io.BytesIO(content))
    contrats = {row[0] for row in wb[SHEET_DALKIA_POSTES].iter_rows(min_row=2, values_only=True) if row[0]}
    assert contrats == {"C00190116O"}  # C00025811F exclu


def test_reimport_combined_is_upsert(db_session: Session) -> None:
    _seed_all(db_session)
    content = build_finance_codification_workbook(db_session, city_id=1)
    res = import_finance_codification_workbook(db_session, content, filename="g", city_id=1)
    assert res.dalkia_sites_created == 0 and res.dalkia_sites_updated == 1
    assert res.energy_points_created == 0 and res.energy_points_updated == 1


def test_scope_helper_filters_display(db_session: Session) -> None:
    _seed_all(db_session)
    assert len(list_accounting_nature_rules(db_session, 1)) == 2
    scoped = list_accounting_nature_rules(db_session, 1, only_current_scope=True)
    assert {r.contract_code for r in scoped} == {"C00190116O"}
