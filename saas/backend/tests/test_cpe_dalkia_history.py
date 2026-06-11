"""Tests historique des imports (toutes versions) + synthèse de l'état en vigueur."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe_dalkia import CpeDalkiaRefImport, CpeDalkiaRefP1Elec, CpeDalkiaRefP1Gaz, CpeDalkiaRefP2P3
from app.services.cpe_dalkia_db import build_active_market_summary, get_all_imports


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


@pytest.fixture()
def user():
    return SimpleNamespace(city_id=1)


def test_get_all_imports_includes_inactive(db_session, user):
    v1 = CpeDalkiaRefImport(city_id=1, lot=1, filename="v1.xlsx", is_active=False, nb_sites=70)
    v2 = CpeDalkiaRefImport(city_id=1, lot=1, filename="v2.xlsx", is_active=True, nb_sites=72)
    db_session.add_all([v1, v2])
    db_session.commit()

    allimp = get_all_imports(db_session, user, lot=1)
    assert len(allimp) == 2  # active + remplacé conservé
    assert {i.is_active for i in allimp} == {True, False}


def test_active_market_summary(db_session, user):
    imp = CpeDalkiaRefImport(city_id=1, lot=1, filename="L1.xlsx", is_active=True, nb_sites=72, nb_ape_rows=31)
    db_session.add(imp)
    db_session.flush()
    # 2026 + 2027 P1 gaz ; P2/P3 2026 (period_idx distinct -> contrainte unique)
    for idx, (y, p1) in enumerate([(2026, 317775.0), (2027, 200000.0)], start=1):
        db_session.add(CpeDalkiaRefP1Gaz(import_id=imp.id, city_id=1, code_site="S", period_idx=idx,
                                         period_label=str(y), period_year=y, p10_total_ht=p1))
    db_session.add(CpeDalkiaRefP2P3(import_id=imp.id, city_id=1, code_site="S", period_idx=1,
                                    period_label="2026", period_year=2026, p2_total_ht=274000.0, p3_total_ht=689000.0))
    db_session.commit()

    s = build_active_market_summary(db_session, user, lot=1, ref_year=2026)
    assert s["has_data"] is True
    assert s["nb_sites"] == 72 and s["nb_ape"] == 31
    assert s["p1_gaz_ref_year_ht"] == 317775.0
    assert s["p2_ref_year_ht"] == 274000.0 and s["p3_ref_year_ht"] == 689000.0
    # marché global = P1(2026+2027) + P2 + P3 toutes années
    assert s["marche_total_ht"] == round(317775.0 + 200000.0 + 274000.0 + 689000.0, 2)


def test_active_summary_includes_p1_elec(db_session, user):
    imp = CpeDalkiaRefImport(city_id=1, lot=2, filename="L2.xlsx", is_active=True, nb_sites=3)
    db_session.add(imp)
    db_session.flush()
    db_session.add(CpeDalkiaRefP1Elec(import_id=imp.id, city_id=1, code_site="VDS-PSC-01", period_idx=2,
                                      period_label="2026", period_year=2026, p10_total_ht=94936.4))
    db_session.commit()
    s = build_active_market_summary(db_session, user, lot=2, ref_year=2026)
    assert s["p1_elec_ref_year_ht"] == 94936.4
    assert s["marche_total_ht"] == 94936.4


def test_active_summary_no_data(db_session, user):
    s = build_active_market_summary(db_session, user, lot=1, ref_year=2026)
    assert s["has_data"] is False
