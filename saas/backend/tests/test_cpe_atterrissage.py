"""Tests de l'atterrissage trimestriel CPE (projection pro-rata DJU)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe import CpeGazReleve, CpePrixGaz, CpeSite
from app.services.cpe_atterrissage import build_atterrissage


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


def _seed_site(db: Session, *, nb: float = 100.0, tarif: str = "T2") -> CpeSite:
    site = CpeSite(
        city_id=1, code_site="VDS-ENS 01", nom_site="Maternelle X", categorie="ENS",
        nb_mwh_pci=nb, ecs_ref_m3_an=0.0, q_ecs_mwh_pci_per_m3=None,
        dju_reference=1426.0, tarif=tarif, actif=True,
    )
    db.add(site)
    db.add(CpePrixGaz(annee=2026, tarif=tarif, pu_eur_mwh_pci=82.13))
    db.flush()
    return site


def _seed_releves(db: Session, site_id: int, *, qt_per_month: float, months: range) -> None:
    for m in months:
        db.add(CpeGazReleve(cpe_site_id=site_id, annee=2026, mois=m, qt_mwh_pci=qt_per_month))
    db.commit()


def _dju_history(real_2026: dict[int, float], normal_month_7_12: float) -> list[dict]:
    """Construit un historique DJU : 2024 + 2025 (profil normal) + 2026 (réel partiel)."""
    rows: list[dict] = []
    for y in (2024, 2025):
        for m in range(1, 13):
            val = normal_month_7_12 if m >= 7 else 100.0
            rows.append({"month": f"{y}-{m:02d}", "dju_chauffe": val, "dju_froid": 0.0})
    for m, val in real_2026.items():
        rows.append({"month": f"2026-{m:02d}", "dju_chauffe": val, "dju_froid": 0.0})
    return rows


def test_projection_prorata_dju(db_session, monkeypatch):
    import app.services.energie as energie_mod
    # Réel 2026 : 6 mois × 200 = 1200 ; normal mois 7-12 : 50 chacun = 300 → projeté annuel 1500
    monkeypatch.setattr(
        energie_mod, "get_dju_monthly",
        lambda: _dju_history({m: 200.0 for m in range(1, 7)}, normal_month_7_12=50.0),
    )
    site = _seed_site(db_session, nb=100.0)
    _seed_releves(db_session, site.id, qt_per_month=10.0, months=range(1, 7))  # NC réalisé = 60

    res = build_atterrissage(db_session, 2026, 2, city_id=1)
    assert res["mois_ecoules"] == 6
    assert res["dju_reel_ecoule"] == 1200.0
    assert res["dju_normal_restant"] == 300.0
    assert res["dju_projete_annuel"] == 1500.0
    assert res["dju_method"] == "profil_normal"
    assert res["has_data"] is True

    item = res["items"][0]
    assert item["nc_realise"] == 60.0
    # facteur = 1500/1200 = 1.25 → NC projeté = 75
    assert item["nc_projete"] == 75.0
    # N'B projeté = 100 × 1500/1426
    assert item["n_prime_b_projete"] == round(100 * 1500 / 1426, 2)
    # N'B (~105.2) > NC (75) → intéressement
    assert item["type_resultat"] == "interessement"
    assert item["montant_ht_projete"] > 0
    assert item["statut"] == "projete"
    # total = somme des montants intéressement projetés
    assert res["total_interessement_projete"] == item["montant_ht_projete"]
    assert res["net_projete"] == round(res["total_interessement_projete"] - res["total_penalite_projete"], 2)


def test_penalite_when_overconsumption(db_session, monkeypatch):
    import app.services.energie as energie_mod
    monkeypatch.setattr(
        energie_mod, "get_dju_monthly",
        lambda: _dju_history({m: 200.0 for m in range(1, 7)}, normal_month_7_12=50.0),
    )
    site = _seed_site(db_session, nb=100.0)
    # Surconsommation : NC réalisé = 120 (6×20) → projeté 150 >> N'B ~105 → pénalité
    _seed_releves(db_session, site.id, qt_per_month=20.0, months=range(1, 7))
    res = build_atterrissage(db_session, 2026, 2, city_id=1)
    item = res["items"][0]
    assert item["type_resultat"] == "penalite"
    assert res["total_penalite_projete"] > 0
    assert res["net_projete"] < 0


def test_sans_donnee_when_no_releve(db_session, monkeypatch):
    import app.services.energie as energie_mod
    monkeypatch.setattr(
        energie_mod, "get_dju_monthly",
        lambda: _dju_history({m: 200.0 for m in range(1, 7)}, normal_month_7_12=50.0),
    )
    _seed_site(db_session, nb=100.0)  # aucun relevé
    res = build_atterrissage(db_session, 2026, 2, city_id=1)
    assert res["has_data"] is False
    assert res["items"][0]["statut"] == "sans_donnee"
    assert res["nb_sites_projetes"] == 0


def test_fallback_reference_without_history(db_session, monkeypatch):
    import app.services.energie as energie_mod
    # Pas d'historique : seulement 2026 → mois restants via fallback reference/12
    monkeypatch.setattr(
        energie_mod, "get_dju_monthly",
        lambda: [{"month": f"2026-{m:02d}", "dju_chauffe": 200.0, "dju_froid": 0.0} for m in range(1, 7)],
    )
    site = _seed_site(db_session, nb=100.0)
    _seed_releves(db_session, site.id, qt_per_month=10.0, months=range(1, 7))
    res = build_atterrissage(db_session, 2026, 2, city_id=1)
    assert res["dju_method"] == "fallback_reference"
    # restant = 6 mois × (1426/12)
    assert res["dju_normal_restant"] == round(6 * (1426.0 / 12.0), 1)


def test_invalid_trimestre(db_session):
    with pytest.raises(ValueError):
        build_atterrissage(db_session, 2026, 5, city_id=1)
