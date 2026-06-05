"""Tests du suivi de performance électrique CPE (cible vs réel, hors intéressement)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe import CpeConsoReleve, CpeSite
from app.models.cpe_dalkia import CpeDalkiaRefCible, CpeDalkiaRefImport
from app.schemas.cpe import CpeElecPerfOut
from app.services.cpe import build_elec_performance


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


def _site(db, code="VDS-ENS 01", cible_elec=0.0):
    s = CpeSite(
        city_id=1, code_site=code, nom_site="Maternelle X", categorie="ENS",
        nb_mwh_pci=0.0, ecs_ref_m3_an=0.0, dju_reference=1426.0,
        cible_elec_mwh=cible_elec, actif=True,
    )
    db.add(s)
    db.flush()
    return s


def _dalkia_cible_elec(db, code, annee, nb):
    imp = db.scalars(
        select(CpeDalkiaRefImport).where(CpeDalkiaRefImport.lot == 1)
    ).first()
    if imp is None:
        imp = CpeDalkiaRefImport(city_id=1, lot=1, filename="L1.xlsx", is_active=True)
        db.add(imp)
        db.flush()
    db.add(CpeDalkiaRefCible(
        import_id=imp.id, city_id=1, code_site=code, fluid="ELEC",
        period_idx=2, period_label="2026", period_year=annee, nb_mwhpci=nb,
    ))
    db.flush()


def _conso_elec(db, site, annee, months, mwh_per_month):
    for m in months:
        db.add(CpeConsoReleve(
            city_id=1, cpe_site_id=site.id, code_site=site.code_site, fluide="ELEC",
            annee=annee, mois=m, energie_mwh=mwh_per_month,
        ))
    db.flush()


def test_cible_dalkia_vs_conso_reelle(db_session):
    site = _site(db_session, cible_elec=99.0)  # le fallback site ne doit PAS primer
    _dalkia_cible_elec(db_session, site.code_site, 2026, nb=15.8)
    _conso_elec(db_session, site, 2026, months=range(1, 7), mwh_per_month=3.0)  # 6 mois × 3 = 18
    db_session.commit()

    res = build_elec_performance(db_session, 2026, city_id=1)
    assert res["has_data"] is True
    it = res["items"][0]
    assert it["cible_mwh"] == 15.8 and it["cible_source"] == "dalkia"  # cible DALKIA prioritaire
    assert it["conso_reelle_mwh"] == 18.0 and it["nb_mois"] == 6
    # écart calculé vs cible AU PRORATA (6/12) = 7.9, pas vs cible annuelle 15.8
    assert it["cible_periode_mwh"] == round(15.8 * 6 / 12, 2)
    assert it["ecart_mwh"] == round(18.0 - 7.9, 2)  # surconsommation reelle (cumul > prorata)
    assert it["ecart_pct"] == round((18.0 - 7.9) / 7.9, 4)
    assert it["statut"] == "suivi"
    # schéma Pydantic : le champ items traverse bien
    out = CpeElecPerfOut.model_validate(res)
    assert out.items[0].cible_source == "dalkia"


def test_fallback_site_cible_when_no_dalkia(db_session):
    site = _site(db_session, cible_elec=20.0)
    _conso_elec(db_session, site, 2026, months=range(1, 13), mwh_per_month=1.5)  # 18
    db_session.commit()
    res = build_elec_performance(db_session, 2026, city_id=1)
    it = res["items"][0]
    assert it["cible_source"] == "site" and it["cible_mwh"] == 20.0
    assert it["nb_mois"] == 12


def test_statuts_sans_cible_et_sans_conso(db_session):
    s1 = _site(db_session, code="VDS-ENS 01", cible_elec=0.0)  # pas de cible -> sans_cible
    s2 = _site(db_session, code="VDS-ENS 02", cible_elec=10.0)  # cible mais pas de conso
    _ = s1, s2
    db_session.commit()
    res = build_elec_performance(db_session, 2026, city_id=1)
    by_code = {i["code_site"]: i for i in res["items"]}
    assert by_code["VDS-ENS 01"]["statut"] == "sans_cible"
    assert by_code["VDS-ENS 02"]["statut"] == "sans_conso"
    assert res["has_data"] is False  # aucun site en suivi complet


def test_totaux(db_session):
    s1 = _site(db_session, code="VDS-ENS 01", cible_elec=10.0)
    s2 = _site(db_session, code="VDS-ENS 02", cible_elec=20.0)
    _conso_elec(db_session, s1, 2026, months=range(1, 13), mwh_per_month=1.0)  # 12
    _conso_elec(db_session, s2, 2026, months=range(1, 13), mwh_per_month=1.0)  # 12
    db_session.commit()
    res = build_elec_performance(db_session, 2026, city_id=1)
    assert res["total_cible_mwh"] == 30.0
    assert res["total_conso_mwh"] == 24.0
    assert res["total_ecart_mwh"] == -6.0  # sous la cible globale
    assert res["nb_suivis"] == 2
