"""Tests de l'indicateur P2.4 (objectif global gaz+élec atteint -> 100% / 50%)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe import CpeConsoReleve, CpeGazReleve, CpePrixGaz, CpeSite
from app.models.cpe_dalkia import CpeDalkiaRefCible, CpeDalkiaRefImport, CpeDalkiaRefP2P3
from app.schemas.cpe import CpeP24Objective
from app.services.cpe import build_p24_objective


@pytest.fixture()
def db_session(monkeypatch):
    # DJU réel = 1426 (= référence) -> N'B = NB (pas de correction), calcul simple
    import app.services.cpe as cpe_mod
    monkeypatch.setattr(cpe_mod, "get_dju_annuel", lambda annee: cpe_mod.CpeDjuAnnuel(
        annee=annee, dju_total=1426.0, nb_jours=365, source="test"))
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


def _site(db, code="VDS-ENS 01", nb_gaz=100.0, tarif="T2"):
    s = CpeSite(
        city_id=1, code_site=code, nom_site="X", categorie="ENS",
        nb_mwh_pci=nb_gaz, ecs_ref_m3_an=0.0, q_ecs_mwh_pci_per_m3=None,
        dju_reference=1426.0, tarif=tarif, cible_elec_mwh=0.0, actif=True,
    )
    db.add(s)
    db.add(CpePrixGaz(annee=2026, tarif=tarif, pu_eur_mwh_pci=82.13))
    db.flush()
    return s


def _gaz_releves(db, site, qt_total, mois=12):
    per = qt_total / mois
    for m in range(1, mois + 1):
        db.add(CpeGazReleve(cpe_site_id=site.id, annee=2026, mois=m, qt_mwh_pci=per))
    db.flush()


def _p24(db, code, montant, lot=1):
    imp = db.scalars(select(CpeDalkiaRefImport).where(CpeDalkiaRefImport.lot == lot)).first()
    if imp is None:
        imp = CpeDalkiaRefImport(city_id=1, lot=lot, filename="L.xlsx", is_active=True)
        db.add(imp)
        db.flush()
    db.add(CpeDalkiaRefP2P3(
        import_id=imp.id, city_id=1, code_site=code, period_idx=2, period_label="2026",
        period_year=2026, p2_4_ht=montant,
    ))
    db.flush()


def test_objectif_atteint_p24_100pct(db_session):
    site = _site(db_session, nb_gaz=100.0)
    _gaz_releves(db_session, site, qt_total=90.0)  # NC 90 < N'B 100 -> economie
    _p24(db_session, site.code_site, montant=1474.0)
    db_session.commit()

    res = build_p24_objective(db_session, 2026, city_id=1)
    assert res["has_data"] is True
    assert res["global_cible_mwh"] == 100.0 and res["global_reel_mwh"] == 90.0
    assert res["economie_mwh"] == 10.0
    assert res["objectif_atteint"] is True
    assert res["p24_taux"] == 1.0
    assert res["p24_montant_ht"] == 1474.0
    assert res["p24_facturable_ht"] == 1474.0
    assert res["p24_a_risque_ht"] == 737.0
    CpeP24Objective.model_validate(res)  # schéma OK


def test_objectif_non_atteint_p24_50pct(db_session):
    site = _site(db_session, nb_gaz=100.0)
    _gaz_releves(db_session, site, qt_total=115.0)  # surconsommation -> objectif manqué
    _p24(db_session, site.code_site, montant=1000.0)
    db_session.commit()

    res = build_p24_objective(db_session, 2026, city_id=1)
    assert res["economie_mwh"] == -15.0
    assert res["objectif_atteint"] is False
    assert res["p24_taux"] == 0.5
    assert res["p24_facturable_ht"] == 500.0


def test_global_gaz_plus_elec(db_session):
    site = _site(db_session, nb_gaz=100.0)
    _gaz_releves(db_session, site, qt_total=98.0)  # gaz : -2 (juste sous cible)
    # cible élec DALKIA 20, conso réelle 25 -> +5 (surconso élec)
    imp = db_session.query(CpeDalkiaRefImport).first()
    if imp is None:
        imp = CpeDalkiaRefImport(city_id=1, lot=1, filename="L.xlsx", is_active=True)
        db_session.add(imp)
        db_session.flush()
    db_session.add(CpeDalkiaRefCible(
        import_id=imp.id, city_id=1, code_site=site.code_site, fluid="ELEC",
        period_idx=2, period_label="2026", period_year=2026, nb_mwhpci=20.0,
    ))
    for m in range(1, 13):
        db_session.add(CpeConsoReleve(
            city_id=1, cpe_site_id=site.id, code_site=site.code_site, fluide="ELEC",
            annee=2026, mois=m, energie_mwh=25.0 / 12,
        ))
    _p24(db_session, site.code_site, montant=500.0)
    db_session.commit()

    res = build_p24_objective(db_session, 2026, city_id=1)
    # global cible = 100 (gaz) + 20 (élec) = 120 ; global réel = 98 + 25 = 123 -> manqué
    assert res["global_cible_mwh"] == 120.0
    assert res["global_reel_mwh"] == 123.0
    assert res["objectif_atteint"] is False  # le dépassement élec fait basculer le global
    assert res["p24_taux"] == 0.5


def test_sans_donnee(db_session):
    _site(db_session, nb_gaz=100.0)  # aucun relevé
    db_session.commit()
    res = build_p24_objective(db_session, 2026, city_id=1)
    assert res["has_data"] is False
    assert res["objectif_atteint"] is False
