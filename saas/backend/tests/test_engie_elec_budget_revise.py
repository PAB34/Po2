"""Tests du budget révisé ENGIE élec (reconstitution fixe/variable par PRM)."""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.building import Building
from app.models.building_meter import BuildingMeterLink
from app.models.city import City
from app.models.invoice import (
    EnergyInvoice,
    EnergyInvoiceLine,
    EnergyInvoicePeriod,
    EnergyInvoiceSite,
)
from app.services import energie
from app.services import engie_elec_budget_revise as mod
from app.services import turpe
from app.services.engie_elec_budget_revise import (
    build_edf_elec_budget_revise,
    build_engie_elec_budget_revise,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


_COUNTER = {"n": 0}


def _seed_invoice(
    db: Session,
    *,
    prm: str,
    year: int,
    month: int,
    lines: list[tuple[str, str | None, float | None, float | None]],
    supplier: str = "ENGIE",
    segment: str | None = None,
    site_name: str | None = None,
    regroupement: str | None = None,
    total_ht: float | None = None,
) -> None:
    """Crée une facture élec (invoice→site→period→lines). lines = (code, poste, qty, amount)."""
    _COUNTER["n"] += 1
    inv = EnergyInvoice(
        city_id=1, import_id=_COUNTER["n"], supplier=supplier, energy_type="electricity",
    )
    db.add(inv)
    db.flush()
    site = EnergyInvoiceSite(
        invoice_id=inv.id, prm_id=prm, site_name=site_name, segment=segment, regroupement=regroupement
    )
    db.add(site)
    db.flush()
    period = EnergyInvoicePeriod(
        invoice_site_id=site.id,
        period_start=date(year, month, 1),
        period_end=date(year, month, 28),
        total_ht=total_ht,
    )
    db.add(period)
    db.flush()
    for code, poste, qty, amount in lines:
        db.add(
            EnergyInvoiceLine(
                invoice_period_id=period.id,
                normalized_code=code,
                poste=poste,
                quantity=qty,
                amount_ht=amount,
            )
        )
    db.commit()


def _dju_index(per_month: dict[tuple[int, int], float]) -> dict[str, dict[str, float]]:
    return {f"{y}-{m:02d}": {"dju_chauffe": v, "dju_froid": 0.0} for (y, m), v in per_month.items()}


def _patch_prices(monkeypatch, *, events=None):
    """BPU vide (ratio 1,0) + TURPE contrôlé (events=[] → ratio 1,0)."""
    monkeypatch.setattr(mod, "load_historical_bpu_prices", lambda db, s: [])
    monkeypatch.setattr(turpe, "list_turpe_evolution_events", lambda: events or [])


# Historique ENEDIS/DJU linéaire : kWh = 1000 + 2×DJU, DJU[m]=10×m sur 2024+2025.
def _linear_history():
    dju = {(y, m): 10.0 * m for y in (2024, 2025) for m in range(1, 13)}
    conso = {f"{y}-{m:02d}": 1000.0 + 2.0 * (10.0 * m) for y in (2024, 2025) for m in range(1, 13)}
    return dju, conso


def test_prevision_thermo_regression(db_session, monkeypatch):
    # N-1 (2025) : fourniture 100000 kWh / 4000€ (0,04) ; network_variable 1000€ (0,01/kWh) ;
    # cspe 500€ (0,005/kWh) ; fixe réseau 700 (gestion) ; cta 100.
    _seed_invoice(
        db_session, prm="PRM1", year=2025, month=6, site_name="Ecole A",
        lines=[
            ("supply", "base", 100000, 4000),
            ("network_variable", "base", 100000, 1000),
            ("cspe", None, None, 500),
            ("network_management", None, None, 700),
            ("cta", None, None, 100),
        ],
    )
    dju, conso = _linear_history()
    monkeypatch.setattr(energie, "_dju_monthly_index", lambda: _dju_index(dju))
    monkeypatch.setattr(energie, "_consumption_by_month", lambda: {"PRM1": conso})
    _patch_prices(monkeypatch)

    res = build_engie_elec_budget_revise(db_session, 1, year=2026, today=date(2026, 6, 30))
    assert res["prm_count"] == 1
    assert res["turpe_available"] is False
    p = res["points"][0]
    # slope=2, intercept=1000 ; DJU_normal[m]=10m (Σ=780) ; conso = 12000 + 2×780 = 13560
    assert p["conso_method"] == "thermo"
    assert p["conso_attendue_kwh"] == 13560
    # pu_variable = 0,04 + 0,01 + 0,005 = 0,055 (ratios BPU/TURPE = 1,0)
    assert p["pu_variable_eur_kwh"] == 0.055
    assert p["variable_prevision"] == round(13560 * 0.055, 2)  # 745,8
    assert p["fixe_prevision"] == 800.0  # 700 réseau + 100 cta
    assert p["prevision_reference"] == round(745.8 + 800.0, 2)
    # aucun réalisé 2026 → atterrissage = prévision
    assert p["realise"] == 0.0
    assert p["landing_method"] == "prevision"
    assert p["atterrissage"] == p["prevision_reference"]


def test_atterrissage_partial_monthly_projection(db_session, monkeypatch):
    _seed_invoice(
        db_session, prm="PRM1", year=2025, month=6,
        lines=[
            ("supply", "base", 100000, 4000),
            ("network_variable", "base", 100000, 1000),
            ("cspe", None, None, 500),
            ("network_management", None, None, 700),
        ],
    )
    # 6 factures 2026 (janv→juin) : fourniture 1000 kWh / 60€ + réseau 15€ + gestion 58,33€.
    for m in range(1, 7):
        _seed_invoice(
            db_session, prm="PRM1", year=2026, month=m,
            lines=[
                ("supply", "base", 1000, 60),
                ("network_variable", "base", 1000, 15),
                ("network_management", None, None, 58.33),
            ],
        )
    dju, conso = _linear_history()
    monkeypatch.setattr(energie, "_dju_monthly_index", lambda: _dju_index(dju))
    monkeypatch.setattr(energie, "_consumption_by_month", lambda: {"PRM1": conso})
    _patch_prices(monkeypatch)

    res = build_engie_elec_budget_revise(db_session, 1, year=2026, today=date(2026, 6, 30))
    p = res["points"][0]
    assert p["months_covered"] == 6
    # réalisé = 6 × (60+15+58,33) = 6 × 133,33 = 799,98
    assert p["realise"] == round(6 * 133.33, 2)
    # reste = conso mensuelle attendue mois 7..12 = Σ (1000 + 20m) pour m=7..12
    reste = sum(1000 + 20 * m for m in range(7, 13))  # 6000 + 20×57 = 7140
    pu = 0.055  # 0,04 fourniture + 0,01 réseau + 0 autres (pas de cspe en N-1 ? il y en a 500 → 0,005)
    # N-1 a cspe 500 → pu_autres_var = 0,005 → pu_variable = 0,055
    fixe_par_mois = round(6 * 58.33, 2) / 6
    attendu = round(6 * 133.33 + reste * pu + fixe_par_mois * 6, 2)
    assert p["landing_method"] == "mensuel"
    assert p["atterrissage"] == attendu


def test_no_enedis_fallback(db_session, monkeypatch):
    _seed_invoice(
        db_session, prm="PRM1", year=2025, month=6,
        lines=[("supply", "base", 50000, 2500), ("network_management", None, None, 300)],
    )
    monkeypatch.setattr(energie, "_dju_monthly_index", lambda: {})
    monkeypatch.setattr(energie, "_consumption_by_month", lambda: {})  # pas d'ENEDIS
    _patch_prices(monkeypatch)

    res = build_engie_elec_budget_revise(db_session, 1, year=2026, today=date(2026, 6, 30))
    p = res["points"][0]
    assert p["enedis_available"] is False
    assert p["conso_method"] == "no_enedis"
    assert p["conso_attendue_kwh"] == 50000  # kWh facturés N-1
    assert p["fixe_prevision"] == 300.0


def test_supplier_filter_and_totals_ignored(db_session, monkeypatch):
    # Facture EDF (autre fournisseur) : ignorée.
    _seed_invoice(
        db_session, prm="PRM_EDF", year=2025, month=6, supplier="EDF",
        lines=[("supply", "base", 10000, 500)],
    )
    # Facture ENGIE avec un vrai total (supply_total_ht) qui ne doit pas gonfler le variable.
    _seed_invoice(
        db_session, prm="PRM1", year=2025, month=6,
        lines=[
            ("supply", "base", 10000, 500),
            ("supply_total_ht", None, None, 500),  # total → ignoré
        ],
    )
    monkeypatch.setattr(energie, "_dju_monthly_index", lambda: {})
    monkeypatch.setattr(energie, "_consumption_by_month", lambda: {})
    _patch_prices(monkeypatch)

    res = build_engie_elec_budget_revise(db_session, 1, year=2026, today=date(2026, 6, 30))
    assert res["prm_count"] == 1  # seul PRM1 (ENGIE), l'EDF est filtré
    p = res["points"][0]
    assert p["prm"] == "PRM1"
    # supply_total_ht ignoré → fourniture = 500 (pu 0,05), pas 1000 → variable prévision = 10000×0,05.
    assert p["variable_prevision"] == 500.0


def test_turpe_ratio_applies_to_network(db_session, monkeypatch):
    _seed_invoice(
        db_session, prm="PRM1", year=2025, month=6,
        lines=[
            ("supply", "base", 100000, 4000),  # 0,04 (hors TURPE)
            ("network_variable", "base", 100000, 1000),  # 0,01 (TURPE)
            ("network_management", None, None, 1000),  # fixe réseau (TURPE)
        ],
    )
    monkeypatch.setattr(energie, "_dju_monthly_index", lambda: {})
    monkeypatch.setattr(energie, "_consumption_by_month", lambda: {})
    # +10% en 2026 (effectif 2026-01) → ratio = index(2026-07)/index(2025-07) = 1,10.
    _patch_prices(monkeypatch, events=[{"effective_date": date(2026, 1, 1), "evolution_percent": 10}])

    res = build_engie_elec_budget_revise(db_session, 1, year=2026, today=date(2026, 6, 30))
    p = res["points"][0]
    assert res["turpe_available"] is True
    assert p["turpe_ratio"] == 1.1
    # pu_variable = 0,04 + 0,01×1,1 = 0,051 ; fixe = 1000×1,1 = 1100
    assert p["pu_variable_eur_kwh"] == 0.051
    assert p["fixe_prevision"] == 1100.0


def test_building_aggregation(db_session, monkeypatch):
    db_session.add(Building(id=10, city_id=1, nom_batiment="Mairie", nom_commune="Sete"))
    db_session.add(
        BuildingMeterLink(building_id=10, fluid="ELECTRICITE", meter_identifier="PRM1")
    )
    db_session.commit()
    for prm in ("PRM1", "PRM2"):
        _seed_invoice(
            db_session, prm=prm, year=2025, month=6,
            lines=[("supply", "base", 10000, 500)],
        )
    monkeypatch.setattr(energie, "_dju_monthly_index", lambda: {})
    monkeypatch.setattr(energie, "_consumption_by_month", lambda: {})
    _patch_prices(monkeypatch)

    res = build_engie_elec_budget_revise(db_session, 1, year=2026, today=date(2026, 6, 30))
    by_prm = {p["prm"]: p for p in res["points"]}
    assert by_prm["PRM1"]["building_id"] == 10
    assert by_prm["PRM1"]["building_name"] == "Mairie"
    assert by_prm["PRM2"]["building_id"] is None
    labels = {b["label"] for b in res["buildings"]}
    assert "Mairie" in labels
    assert "Non affecté" in labels


def test_regroupement_aggregation(db_session, monkeypatch):
    _seed_invoice(
        db_session, prm="PRM1", year=2025, month=6, regroupement="ECOLES",
        lines=[("supply", "base", 10000, 500)],
    )
    _seed_invoice(
        db_session, prm="PRM2", year=2025, month=6, regroupement="ECOLES",
        lines=[("supply", "base", 20000, 900)],
    )
    _seed_invoice(
        db_session, prm="PRM3", year=2025, month=6, regroupement=None,
        lines=[("supply", "base", 5000, 300)],
    )
    monkeypatch.setattr(energie, "_dju_monthly_index", lambda: {})
    monkeypatch.setattr(energie, "_consumption_by_month", lambda: {})
    _patch_prices(monkeypatch)

    res = build_engie_elec_budget_revise(db_session, 1, year=2026, today=date(2026, 6, 30))
    by_label = {r["label"]: r for r in res["regroupements"]}
    assert by_label["ECOLES"]["prm_count"] == 2
    assert by_label["Non regroupé"]["prm_count"] == 1


def test_anomaly_soutirage_variable_corrected(db_session, monkeypatch):
    # Bug d'import : le montant (230,43) est mis dans le prix unitaire → montant stocké = 4761×230,43.
    _seed_invoice(
        db_session, prm="PRM1", year=2026, month=5,
        lines=[
            ("supply", "base", 4761, 358.46),
            # quantity=4761, unit_price=230.43 (aberrant), amount=1097077 (=4761×230.43).
            ("network_variable", "base", 4761, 1097077.23),
        ],
    )
    monkeypatch.setattr(energie, "_dju_monthly_index", lambda: {})
    monkeypatch.setattr(energie, "_consumption_by_month", lambda: {})
    _patch_prices(monkeypatch)
    # On force le prix unitaire aberrant sur la ligne network_variable.
    from app.models.invoice import EnergyInvoiceLine
    line = db_session.query(EnergyInvoiceLine).filter(EnergyInvoiceLine.normalized_code == "network_variable").one()
    line.unit_price_ht = 230.43
    db_session.commit()

    res = build_engie_elec_budget_revise(db_session, 1, year=2026, today=date(2026, 6, 30))
    p = res["points"][0]
    assert p["has_anomaly"] is True
    assert res["anomaly_prm_count"] == 1
    # montant réseau variable corrigé = 230,43 (et non 1 097 077) → réalisé = 358,46 + 230,43.
    assert p["realise"] == round(358.46 + 230.43, 2)


def test_edf_photoperiod_consumption(db_session, monkeypatch):
    # EDF éclairage public : N-1 (2025) reconduit, réparti par photopériode (plus l'hiver).
    _seed_invoice(
        db_session, prm="EP1", year=2025, month=6, supplier="EDF",
        lines=[("supply", "base", 120000, 12000), ("network_fixed_total", None, None, 600)],
    )
    monkeypatch.setattr(energie, "_dju_monthly_index", lambda: {})
    monkeypatch.setattr(energie, "_consumption_by_month", lambda: {})  # pas d'ENEDIS
    _patch_prices(monkeypatch)

    res = build_edf_elec_budget_revise(db_session, 1, year=2026, today=date(2026, 6, 30))
    assert res["prm_count"] == 1
    p = res["points"][0]
    assert p["conso_method"] == "photoperiod_n1"
    assert p["conso_attendue_kwh"] == 120000  # N-1 reconduit
    # network_fixed_total compté comme fixe réseau (EDF n'a pas les composantes).
    assert p["fixe_prevision"] == 600.0
    # Vérifie la répartition mensuelle : janvier (nuit longue) > juillet (nuit courte).
    from app.services.engie_elec_budget_revise import _photoperiod_monthly
    w = _photoperiod_monthly()
    assert w[1] > w[7]
    assert abs(sum(w.values()) - 1.0) < 1e-9


def test_network_fixed_total_ignored_when_components_present(db_session, monkeypatch):
    # ENGIE : composantes + total → le total est ignoré (pas de double comptage).
    _seed_invoice(
        db_session, prm="PRM1", year=2025, month=6,
        lines=[
            ("supply", "base", 10000, 500),
            ("network_management", None, None, 700),
            ("network_fixed_total", None, None, 700),  # double les composantes → ignoré
        ],
    )
    monkeypatch.setattr(energie, "_dju_monthly_index", lambda: {})
    monkeypatch.setattr(energie, "_consumption_by_month", lambda: {})
    _patch_prices(monkeypatch)

    res = build_engie_elec_budget_revise(db_session, 1, year=2026, today=date(2026, 6, 30))
    p = res["points"][0]
    assert p["fixe_prevision"] == 700.0  # 700, pas 1400
