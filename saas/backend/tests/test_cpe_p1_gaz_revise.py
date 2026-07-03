"""Tests reconstitution budget P1 gaz DALKIA (conso attendue DJU × prix OS3)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe import CpeGazReleve, CpePrixGaz, CpeSite
from app.models.cpe_dpgf_p1 import CpeDpgfP1Import, CpeDpgfP1Line
from app.services import cpe_p1_gaz_revise as svc
from app.services.accounting_contract_budget import _p1_budget_override, _poste_landing


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


def _seed_site(db: Session, *, code: str = "VDS-ENS 01", tarif: str = "T2", nb: float = 100.0) -> CpeSite:
    site = CpeSite(
        city_id=1, code_site=code, nom_site="Site " + code, categorie="ENS",
        nb_mwh_pci=nb, ecs_ref_m3_an=0.0, q_ecs_mwh_pci_per_m3=None,
        dju_reference=1426.0, tarif=tarif, actif=True,
    )
    db.add(site)
    db.flush()
    return site


def _seed_releves(db: Session, site_id: int, annee: int, qt_per_month: float) -> None:
    for m in range(1, 13):
        db.add(CpeGazReleve(cpe_site_id=site_id, annee=annee, mois=m, qt_mwh_pci=qt_per_month))
    db.commit()


def _dju(monkeypatch, per_year_heating: dict[int, float]) -> None:
    # DJU des mois de chauffe DALKIA (1-5,10-12) uniquement.
    rows = []
    for y, val in per_year_heating.items():
        for m in range(1, 13):
            if m in {1, 2, 3, 4, 5, 10, 11, 12}:
                rows.append({"month": f"{y}-{m:02d}", "dju_chauffe": val, "dju_froid": 0.0})
    monkeypatch.setattr(svc, "aggregate_dju_monthly", lambda profile: rows)


def test_budget_conso_dju_x_os3(db_session, monkeypatch):
    site = _seed_site(db_session, tarif="T2", nb=100.0)
    _seed_releves(db_session, site.id, 2025, qt_per_month=10.0)  # conso N-1 = 120 MWh
    db_session.add(CpePrixGaz(annee=2026, tarif="T2", pu_eur_mwh_pci=80.0))
    db_session.commit()
    # DJU chauffe : 2024=10/mois (8 mois=80), 2025=20/mois (160) → normal=120 ; climat=120/160=0,75
    _dju(monkeypatch, {2024: 10.0, 2025: 20.0})

    res = svc.compute_p1_gaz_budget(db_session, 1, year=2026)
    assert res["climate_ratio"] == 0.75
    row = res["by_site"][0]
    assert row["conso_source"] == "releves_n1_dju"
    assert row["conso_attendue_mwh"] == 90.0  # 120 × 0,75
    assert row["budget"] == 7200.0  # 90 × 80
    assert res["total"] == 7200.0


def test_fallback_nb_when_no_releves(db_session, monkeypatch):
    _seed_site(db_session, tarif="T2", nb=100.0)  # aucun relevé N-1
    db_session.add(CpePrixGaz(annee=2026, tarif="T2", pu_eur_mwh_pci=80.0))
    db_session.commit()
    _dju(monkeypatch, {2024: 10.0, 2025: 20.0})

    res = svc.compute_p1_gaz_budget(db_session, 1, year=2026)
    row = res["by_site"][0]
    assert row["conso_source"] == "nb_contractuel"
    assert row["conso_attendue_mwh"] == 100.0  # NB = site.nb_mwh_pci
    assert row["budget"] == 8000.0


def test_incomplet_when_no_os3_price(db_session, monkeypatch):
    site = _seed_site(db_session, tarif="T2", nb=100.0)
    _seed_releves(db_session, site.id, 2025, qt_per_month=10.0)
    # aucun CpePrixGaz seedé → pu None
    _dju(monkeypatch, {2024: 10.0, 2025: 20.0})

    res = svc.compute_p1_gaz_budget(db_session, 1, year=2026)
    assert res["incomplete_sites"] == 1
    assert res["by_site"][0]["status"] == "incomplet"
    assert res["total"] == 0.0


def _seed_dpgf_revise(db: Session, *, year: int, total: float, level: str = "rev_temp_prix") -> None:
    imp = CpeDpgfP1Import(city_id=1, lot=1, filename="P1-DPGF.xlsx", nb_lines=1, is_active=True)
    db.add(imp)
    db.flush()
    db.add(CpeDpgfP1Line(
        import_id=imp.id, city_id=1, lot=1, level=level, code_site="VDS-ENS 01",
        period_idx=0, period_label=str(year), period_year=year, p10_total_ht=total,
    ))
    db.commit()


def test_p1_override_prefers_dpgf_revise(db_session, monkeypatch):
    # Reconstitution donnerait 7200, mais un DPGF Rév T° & prix officiel (9000) doit primer.
    site = _seed_site(db_session, tarif="T2", nb=100.0)
    _seed_releves(db_session, site.id, 2025, qt_per_month=10.0)
    db_session.add(CpePrixGaz(annee=2026, tarif="T2", pu_eur_mwh_pci=80.0))
    db_session.commit()
    _seed_dpgf_revise(db_session, year=2026, total=9000.0)
    _dju(monkeypatch, {2024: 10.0, 2025: 20.0})

    budget, detail = _p1_budget_override(db_session, 1, 2026, None)
    assert budget == 9000.0
    assert "révisé DALKIA" in detail


def test_p1_override_fallback_reconstitution(db_session, monkeypatch):
    # Aucun DPGF révisé → repli sur la reconstitution conso×OS3 (7200).
    site = _seed_site(db_session, tarif="T2", nb=100.0)
    _seed_releves(db_session, site.id, 2025, qt_per_month=10.0)
    db_session.add(CpePrixGaz(annee=2026, tarif="T2", pu_eur_mwh_pci=80.0))
    db_session.commit()
    _dju(monkeypatch, {2024: 10.0, 2025: 20.0})

    budget, detail = _p1_budget_override(db_session, 1, 2026, None)
    assert budget == 7200.0
    assert "reconstitué" in detail


def test_p1_override_none_when_no_source(db_session, monkeypatch):
    _seed_site(db_session, tarif="T2", nb=0.0)  # pas de conso, pas de prix, pas de DPGF
    _dju(monkeypatch, {2024: 10.0, 2025: 20.0})
    budget, detail = _p1_budget_override(db_session, 1, 2026, None)
    assert budget is None and detail is None


def test_poste_landing_override_p1_reconstitue():
    poste = _poste_landing(
        "P1", "P1 - Fourniture gaz", prevu=1000.0, recu=200.0, progress=50.0, coef_by_market={},
        override_budget=7200.0, override_detail="reconstitué",
    )
    assert poste["budget_contractuel"] == 7200.0
    assert poste["coefficient_revision"] == 7.2  # 7200 / 1000
    assert poste["revision_detail"] == "reconstitué"
    assert poste["landing_method"] == "reconstitue_os3"
    assert poste["atterrissage"] == 7200.0
