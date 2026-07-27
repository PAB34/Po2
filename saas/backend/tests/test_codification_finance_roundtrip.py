"""Aller-retour du gabarit finance de codification DALKIA.

export (build_codification_finance_workbook) -> import (import_codification_workbook)
doit restituer sites + postes à l'identique, colonnes Actif / Opération / Notes comprises.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe import CpeAccountingNatureRule, CpeAccountingSiteMapping
from app.services.cpe_accounting import (
    build_codification_finance_workbook,
    import_codification_workbook,
    list_accounting_nature_rules,
    list_accounting_site_mappings,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


def _seed(db: Session) -> None:
    db.add(
        CpeAccountingSiteMapping(
            city_id=1, code_site="VDS-BAM 08", site_name="Centre Technique Municipal",
            service_code="MABA", service_label="Maintenance batiment", function_code="020",
            antenna_code="CTM", operation_code=None, active=True, notes="site test",
        )
    )
    db.add(
        CpeAccountingSiteMapping(
            city_id=1, code_site="VDS-ENS 01", site_name="Maternelle AGNES VARDA",
            service_code="ENS", function_code="211", antenna_code="A VARDA", active=False,
        )
    )
    db.add(
        CpeAccountingNatureRule(
            city_id=1, contract_code="C00190116O", market="P3", billed_item="P3.4",
            accounting_nature="21351", accounting_label="Installations generales",
            active=True, notes="invest",
        )
    )
    db.add(
        CpeAccountingNatureRule(
            city_id=1, contract_code="C00190116O", market="P2", billed_item="P2",
            accounting_nature="6156", accounting_label="Maintenance", active=False,
        )
    )
    db.commit()


def test_export_then_import_roundtrip(db_session: Session) -> None:
    _seed(db_session)
    content = build_codification_finance_workbook(db_session, city_id=1)

    # Import dans une base neuve : on doit retrouver exactement les memes lignes.
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as fresh:
        fresh.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        fresh.commit()
        res = import_codification_workbook(fresh, content, filename="gabarit", city_id=1)
        assert res.errors == []
        assert res.site_mappings_created == 2
        assert res.nature_rules_created == 2

        sites = {s.code_site: s for s in list_accounting_site_mappings(fresh, 1)}
        assert sites["VDS-BAM 08"].service_code == "MABA"
        assert sites["VDS-BAM 08"].antenna_code == "CTM"
        assert sites["VDS-BAM 08"].operation_code is None
        assert sites["VDS-BAM 08"].active is True
        assert sites["VDS-BAM 08"].notes == "site test"
        # L'état inactif doit survivre à l'aller-retour.
        assert sites["VDS-ENS 01"].active is False

        rules = {(r.contract_code, r.billed_item): r for r in list_accounting_nature_rules(fresh, 1)}
        assert rules[("C00190116O", "P3.4")].accounting_nature == "21351"
        assert rules[("C00190116O", "P3.4")].market == "P3"
        assert rules[("C00190116O", "P2")].active is False


def test_reimport_is_upsert_not_duplicate(db_session: Session) -> None:
    _seed(db_session)
    content = build_codification_finance_workbook(db_session, city_id=1)
    # Réimport dans la MÊME base : mise à jour, aucun doublon.
    res = import_codification_workbook(db_session, content, filename="gabarit", city_id=1)
    assert res.errors == []
    assert res.site_mappings_created == 0
    assert res.site_mappings_updated == 2
    assert res.nature_rules_created == 0
    assert res.nature_rules_updated == 2
    assert len(list_accounting_site_mappings(db_session, 1)) == 2
    assert len(list_accounting_nature_rules(db_session, 1)) == 2
