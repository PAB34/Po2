"""Tests du moteur de diff entre versions d'import DALKIA."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe_dalkia import (
    CpeDalkiaRefCible,
    CpeDalkiaRefImport,
    CpeDalkiaRefP2P3,
    CpeDalkiaRefSite,
)
from app.models.cpe_dpgf_p1 import CpeDpgfP1Import, CpeDpgfP1Line
from app.services.cpe_dalkia_diff import build_dpgf_summary, build_master_diff


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


def _master(db, *, lot, filename, active, sites, p2, p3, cible_gaz_nb):
    imp = CpeDalkiaRefImport(city_id=1, lot=lot, filename=filename, is_active=active, nb_sites=len(sites))
    db.add(imp)
    db.flush()
    for code in sites:
        db.add(CpeDalkiaRefSite(import_id=imp.id, city_id=1, lot=lot, code_site=code, nom_batiment=code))
    db.add(CpeDalkiaRefP2P3(import_id=imp.id, city_id=1, code_site=sites[0], period_idx=2,
                            period_label="2026", period_year=2026, p2_total_ht=p2, p3_total_ht=p3))
    db.add(CpeDalkiaRefCible(import_id=imp.id, city_id=1, code_site=sites[0], fluid="GAZ", period_idx=2,
                            period_label="2026", period_year=2026, nb_mwhpci=cible_gaz_nb))
    db.flush()
    return imp


def test_master_diff_sites_postes_cibles(db_session, user):
    base = _master(db_session, lot=1, filename="base.xlsx", active=False,
                   sites=["A", "B", "C"], p2=274000.0, p3=689000.0, cible_gaz_nb=100.0)
    aven = _master(db_session, lot=1, filename="avenant.xlsx", active=True,
                   sites=["A", "B", "D"], p2=280000.0, p3=689000.0, cible_gaz_nb=90.0)
    db_session.commit()

    d = build_master_diff(db_session, user, aven.id)  # from_id None -> base (la plus ancienne)
    assert d["ok"] is True
    assert d["from_import"]["id"] == base.id and d["to_import"]["id"] == aven.id
    assert d["sites_entres"] == ["D"] and d["sites_sortis"] == ["C"]
    p2 = next(p for p in d["postes"] if p["poste"] == "P2")
    assert p2["from_ht"] == 274000.0 and p2["to_ht"] == 280000.0 and p2["delta_ht"] == 6000.0
    assert d["cibles_gaz_modifiees"] == 1
    assert "+1 site" in d["chips"] and "−1 site" in d["chips"]
    assert any("P2" in c for c in d["chips"])


def test_master_diff_no_baseline(db_session, user):
    only = _master(db_session, lot=1, filename="base.xlsx", active=True,
                   sites=["A"], p2=1.0, p3=1.0, cible_gaz_nb=10.0)
    db_session.commit()
    d = build_master_diff(db_session, user, only.id)
    assert d["ok"] is False and d["reason"] == "no_baseline"


def test_master_diff_explicit_from(db_session, user):
    base = _master(db_session, lot=1, filename="base.xlsx", active=False,
                   sites=["A"], p2=100.0, p3=0.0, cible_gaz_nb=100.0)
    aven = _master(db_session, lot=1, filename="aven.xlsx", active=True,
                   sites=["A"], p2=150.0, p3=0.0, cible_gaz_nb=100.0)
    db_session.commit()
    d = build_master_diff(db_session, user, aven.id, from_id=base.id)
    assert d["ok"] is True
    p2 = next(p for p in d["postes"] if p["poste"] == "P2")
    assert p2["delta_ht"] == 50.0
    assert d["cibles_gaz_modifiees"] == 0


def test_dpgf_summary_levels_and_delta(db_session, user):
    imp = CpeDpgfP1Import(city_id=1, lot=1, filename="DPGF.xlsx", is_active=True, nb_lines=3)
    db_session.add(imp)
    db_session.flush()
    for level, val in [("contrat", 317775.0), ("rev_temp", 352073.0), ("rev_temp_prix", 312197.0)]:
        db_session.add(CpeDpgfP1Line(import_id=imp.id, city_id=1, lot=1, level=level, code_site="S",
                                     period_idx=2, period_label="2026", period_year=2026, p10_total_ht=val))
    db_session.commit()

    s = build_dpgf_summary(db_session, user, imp.id)
    assert s["ok"] is True
    y = next(r for r in s["by_year"] if r["year"] == 2026)
    assert y["contrat"] == 317775.0 and y["rev_temp"] == 352073.0
    assert y["delta_rev_temp"] == round(352073.0 - 317775.0, 2)
    assert any("Rév Temp" in c for c in s["chips"])
