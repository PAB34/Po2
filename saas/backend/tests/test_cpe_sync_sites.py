"""Tests de la création de cpe_sites depuis le référentiel DALKIA (volet performance)."""
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe import CpeSite
from app.models.cpe_dalkia import (
    CpeDalkiaRefCible,
    CpeDalkiaRefImport,
    CpeDalkiaRefP1Gaz,
    CpeDalkiaRefSite,
)
from app.services.cpe_dalkia_db import sync_cpe_sites_from_dalkia


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        imp = CpeDalkiaRefImport(city_id=1, lot=1, filename="L1.xlsx", is_active=True)
        session.add(imp)
        session.flush()
        # 2 sites : 1 avec gaz (CCAS 04 T3), 1 sans gaz (CCAS 02)
        session.add_all([
            CpeDalkiaRefSite(import_id=imp.id, city_id=1, lot=1, code_site="CCAS 04", nom_batiment="Residence LE THONNAIRE"),
            CpeDalkiaRefSite(import_id=imp.id, city_id=1, lot=1, code_site="VDS-ENS 01", nom_batiment="Maternelle DOLTO"),
            CpeDalkiaRefSite(import_id=imp.id, city_id=1, lot=1, code_site="CCAS 02", nom_batiment="Ludotheque"),
        ])
        session.add_all([
            CpeDalkiaRefCible(import_id=imp.id, city_id=1, code_site="CCAS 04", fluid="GAZ",
                              period_idx=2, period_label="2026", period_year=2026,
                              nb_mwhpci=170.7, dju_reference=1426, q_ecs=84),
            CpeDalkiaRefCible(import_id=imp.id, city_id=1, code_site="VDS-ENS 01", fluid="GAZ",
                              period_idx=2, period_label="2026", period_year=2026, nb_mwhpci=56.1),
            CpeDalkiaRefCible(import_id=imp.id, city_id=1, code_site="VDS-ENS 01", fluid="ELEC",
                              period_idx=2, period_label="2026", period_year=2026, nb_mwhpci=33.5),
        ])
        session.add(CpeDalkiaRefP1Gaz(import_id=imp.id, city_id=1, code_site="CCAS 04", type_tarif="T3",
                                      pce="GI091902", period_idx=2, period_label="2026", period_year=2026))
        session.commit()
        yield session


def test_creates_sites_with_nb_tarif_categorie(db_session: Session):
    res = sync_cpe_sites_from_dalkia(db_session, city_id=1)
    assert res["created"] == 3 and res["total"] == 3

    by = {s.code_site: s for s in db_session.scalars(select(CpeSite))}
    assert set(by) == {"CCAS 04", "VDS-ENS 01", "CCAS 02"}

    ccas04 = by["CCAS 04"]
    assert ccas04.nom_site == "Residence LE THONNAIRE"
    assert ccas04.categorie == "CCAS"
    assert ccas04.nb_mwh_pci == pytest.approx(170.7)
    assert ccas04.tarif == "T3"
    assert ccas04.pce == "GI091902"
    assert ccas04.dju_reference == pytest.approx(1426)
    assert ccas04.q_ecs_mwh_pci_per_m3 == pytest.approx(84)

    ens = by["VDS-ENS 01"]
    assert ens.categorie == "ENS"
    assert ens.nb_mwh_pci == pytest.approx(56.1)
    assert ens.cible_elec_mwh == pytest.approx(33.5)
    assert ens.tarif is None  # pas de ligne P1 gaz

    # site sans gaz : NB 0, pas de tarif
    assert by["CCAS 02"].nb_mwh_pci == pytest.approx(0.0)
    assert by["CCAS 02"].tarif is None


def test_idempotent_upsert(db_session: Session):
    sync_cpe_sites_from_dalkia(db_session, city_id=1)
    res2 = sync_cpe_sites_from_dalkia(db_session, city_id=1)
    assert res2["created"] == 0 and res2["updated"] == 3
    assert db_session.scalar(select(CpeSite).where(CpeSite.code_site == "CCAS 04")) is not None
    assert len(list(db_session.scalars(select(CpeSite)))) == 3  # pas de doublon


def test_nb_aligned_after_sync(db_session: Session):
    """Après sync, resolve_nb_for_year trouve bien le NB DALKIA (badge DLK garanti)."""
    from app.services.cpe import resolve_nb_for_year_detailed
    sync_cpe_sites_from_dalkia(db_session, city_id=1)
    site = db_session.scalar(select(CpeSite).where(CpeSite.code_site == "CCAS 04"))
    nb, source = resolve_nb_for_year_detailed(db_session, site, 2026)
    assert nb == pytest.approx(170.7)
    assert source == "dalkia"
