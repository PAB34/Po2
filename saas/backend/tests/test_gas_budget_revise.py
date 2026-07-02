"""Tests du budget révisé gaz (reconstitution fixe/variable par PCE)."""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.gas_invoice import GasInvoice
from app.services import energie, gas_budget_revise
from app.services.gas_budget_revise import build_gas_budget_revise


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


_COUNTER = {"n": 0}


def _seed(
    db: Session,
    *,
    pce: str,
    year: int,
    month: int = 6,
    kwh: int = 0,
    fourniture: float = 0.0,
    ticgn: float = 0.0,
    atrd_var: float = 0.0,
    indexation: float = 0.0,
    fixe: float = 0.0,
    total_ht: float = 0.0,
    nom_site: str | None = None,
) -> None:
    _COUNTER["n"] += 1
    db.add(
        GasInvoice(
            city_id=1,
            num_facture=f"F{_COUNTER['n']}",
            pce=pce,
            nom_site=nom_site,
            debut_conso=date(year, month, 1),
            fin_conso=date(year, month, 28),
            total_conso_kwh=kwh,
            montant_conso_gaz=fourniture,
            montant_ticgn=ticgn,
            atrd_terme_variable=atrd_var,
            montant_indexation=indexation,
            # parts fixes réparties (somme = fixe)
            abonnement_fournisseur=fixe,
            atrt_terme_fixe=0.0,
            atrd_terme_fixe=0.0,
            montant_cta=0.0,
            total_hors_tva=total_ht,
        )
    )
    db.commit()


def _dju_rows(per_year: dict[int, float]) -> list[dict]:
    """DJU constant par mois pour chaque année fournie."""
    rows: list[dict] = []
    for y, val in per_year.items():
        for m in range(1, 13):
            rows.append({"month": f"{y}-{m:02d}", "dju_chauffe": val, "dju_froid": 0.0})
    return rows


def _patch_peg(monkeypatch, mapping):
    monkeypatch.setattr(gas_budget_revise, "load_revisable_prices", lambda db, cid: mapping)


def test_budget_revise_variable_dju_peg(db_session, monkeypatch):
    # N-1 (2025) : 100 000 kWh, fourniture 4000 (0,04/kWh), autres var 1000 (0,01/kWh), fixe 700.
    _seed(db_session, pce="GI1", year=2025, kwh=100000, fourniture=4000,
          ticgn=800, atrd_var=200, fixe=700, nom_site="Ecole A")
    # DJU : 2024=10/mois (120/an), 2025=20/mois (240/an) → normal=15/mois (180/an) → climat=180/240=0,75
    monkeypatch.setattr(energie, "get_dju_monthly", lambda: _dju_rows({2024: 10.0, 2025: 20.0}))
    # PEG : 2025 moyenne 20, 2026 moyenne 25 → ratio 1,25
    _patch_peg(monkeypatch, {(2025, 1): 20.0, (2026, 1): 25.0})

    res = build_gas_budget_revise(db_session, 1, year=2026, today=date(2026, 6, 30))
    assert res["pce_count"] == 1
    assert res["peg_available"] is True
    p = res["points"][0]
    assert p["peg_ratio"] == 1.25
    assert p["climate_ratio"] == 0.75
    assert p["conso_attendue_kwh"] == 75000
    # pu_variable = 0,04×1,25 + 0,01 = 0,06 ; variable = 75000×0,06 = 4500 ; fixe = 700
    assert p["pu_variable_eur_kwh"] == 0.06
    assert p["variable_budget"] == 4500.0
    assert p["fixe_budget"] == 700.0
    assert p["budget_revise"] == 5200.0
    # aucun réalisé 2026 → atterrissage = budget révisé
    assert p["realise"] == 0.0
    assert p["atterrissage"] == 5200.0
    assert p["landing_method"] == "budget_revise"


def test_atterrissage_partial_realized_dju(db_session, monkeypatch):
    _seed(db_session, pce="GI1", year=2025, kwh=100000, fourniture=4000, ticgn=800, atrd_var=200, fixe=700)
    # 6 factures 2026 (mois 1..6) : 10 000 kWh chacune (60 000), 500 HT chacune (3000)
    for m in range(1, 7):
        _seed(db_session, pce="GI1", year=2026, month=m, kwh=10000, total_ht=500)
    # DJU normal 2024/2025 = 15/mois ; réel 2026 mois 1..6 = 30
    rows = _dju_rows({2024: 10.0, 2025: 20.0})
    rows += [{"month": f"2026-{m:02d}", "dju_chauffe": 30.0, "dju_froid": 0.0} for m in range(1, 7)]
    monkeypatch.setattr(energie, "get_dju_monthly", lambda: rows)
    _patch_peg(monkeypatch, {(2025, 1): 20.0, (2026, 1): 25.0})

    res = build_gas_budget_revise(db_session, 1, year=2026, today=date(2026, 6, 30))
    p = res["points"][0]
    # DJU écoulé = 6×30 = 180 ; restant = 6×15 = 90 ; projeté = 60000×270/180 = 90000
    # reste conso = 30000 ; variable reste = 30000×0,06 = 1800 ; fixe reste = 700/12×6 = 350
    # atterrissage = 3000 + 1800 + 350 = 5150
    assert p["realise"] == 3000.0
    assert p["kwh_realise"] == 60000
    assert p["atterrissage"] == 5150.0
    assert p["landing_method"] == "dju"
    assert p["ecart_atterrissage_vs_budget"] == round(5150.0 - p["budget_revise"], 2)


def test_fixe_pur_sans_conso(db_session, monkeypatch):
    _seed(db_session, pce="GF", year=2025, kwh=0, fixe=700)
    monkeypatch.setattr(energie, "get_dju_monthly", lambda: _dju_rows({2024: 10.0, 2025: 20.0}))
    _patch_peg(monkeypatch, {})

    res = build_gas_budget_revise(db_session, 1, year=2026, today=date(2026, 6, 30))
    p = res["points"][0]
    assert p["variable_budget"] == 0.0
    assert p["budget_revise"] == 700.0
    assert p["has_history"] is False  # kWh N-1 nul
    assert p["atterrissage"] == 700.0


def test_pce_sans_historique_n1(db_session, monkeypatch):
    # PCE avec seulement des factures de l'année Y (aucun N-1) → budget 0, atterrissage = réalisé.
    _seed(db_session, pce="NEW", year=2026, month=3, kwh=5000, total_ht=400)
    monkeypatch.setattr(energie, "get_dju_monthly", lambda: [])
    _patch_peg(monkeypatch, {})

    res = build_gas_budget_revise(db_session, 1, year=2026, today=date(2027, 1, 1))
    p = res["points"][0]
    assert p["budget_revise"] == 0.0
    assert p["has_history"] is False
    assert p["realise"] == 400.0
    assert p["atterrissage"] == 400.0
    assert p["landing_method"] == "realise_complet"


def test_peg_unavailable_holds_price(db_session, monkeypatch):
    _seed(db_session, pce="GI1", year=2025, kwh=100000, fourniture=4000, ticgn=800, atrd_var=200, fixe=700)
    monkeypatch.setattr(energie, "get_dju_monthly", lambda: _dju_rows({2024: 10.0, 2025: 20.0}))
    _patch_peg(monkeypatch, {})  # aucun PEG → ratio tenu à 1,0

    res = build_gas_budget_revise(db_session, 1, year=2026, today=date(2026, 6, 30))
    assert res["peg_available"] is False
    p = res["points"][0]
    assert p["peg_ratio"] == 1.0
    # pu_variable = 0,04×1,0 + 0,01 = 0,05 ; variable = 75000×0,05 = 3750
    assert p["pu_variable_eur_kwh"] == 0.05
    assert p["variable_budget"] == 3750.0
    assert p["budget_revise"] == 4450.0
