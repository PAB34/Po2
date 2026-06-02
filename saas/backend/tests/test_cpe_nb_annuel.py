"""Tests de la résolution du NB contractuel par année (Phase A — sync cibles DALKIA).

`resolve_nb_for_year` doit préférer la cible GAZ « NB » de l'import DALKIA actif pour
l'année demandée, et retomber sur le scalaire `CpeSite.nb_mwh_pci` en l'absence de cible.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe import CpeSite
from app.models.cpe_dalkia import CpeDalkiaRefCible, CpeDalkiaRefImport
from app.services.cpe import resolve_nb_for_year


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.add(City(id=2, nom_commune="Autre", code_commune="00000"))
        session.commit()
        yield session


def _make_site(db: Session, *, city_id: int = 1, code: str = "VDS-ENS 08", nb: float = 56.1) -> CpeSite:
    site = CpeSite(
        city_id=city_id,
        code_site=code,
        nom_site="Ecole test",
        categorie="ENS",
        nb_mwh_pci=nb,
        dju_reference=1426.0,
    )
    db.add(site)
    db.flush()
    return site


def _add_cible(
    db: Session,
    *,
    import_id: int,
    code: str,
    annee: int,
    nb: float | None,
    city_id: int = 1,
    fluid: str = "GAZ",
) -> None:
    db.add(CpeDalkiaRefCible(
        import_id=import_id,
        city_id=city_id,
        code_site=code,
        fluid=fluid,
        period_idx=annee - 2024,
        period_label=str(annee),
        period_year=annee,
        nb_mwhpci=nb,
    ))
    db.flush()


def _add_import(db: Session, *, city_id: int = 1, lot: int = 1, active: bool = True) -> CpeDalkiaRefImport:
    imp = CpeDalkiaRefImport(city_id=city_id, lot=lot, filename="L1.xlsx", is_active=active)
    db.add(imp)
    db.flush()
    return imp


def test_returns_dalkia_cible_when_present(db_session: Session):
    """La cible DALKIA de l'année prime sur le scalaire du site (NB réduit après APE)."""
    site = _make_site(db_session, nb=56.1)
    imp = _add_import(db_session)
    _add_cible(db_session, import_id=imp.id, code=site.code_site, annee=2026, nb=56.1)
    _add_cible(db_session, import_id=imp.id, code=site.code_site, annee=2028, nb=18.0)
    db_session.commit()

    assert resolve_nb_for_year(db_session, site, 2026) == pytest.approx(56.1)
    assert resolve_nb_for_year(db_session, site, 2028) == pytest.approx(18.0)


def test_falls_back_to_scalar_when_no_cible_for_year(db_session: Session):
    """Sans cible DALKIA pour l'année, on garde le comportement historique (scalaire site)."""
    site = _make_site(db_session, nb=56.1)
    imp = _add_import(db_session)
    _add_cible(db_session, import_id=imp.id, code=site.code_site, annee=2026, nb=56.1)
    db_session.commit()

    assert resolve_nb_for_year(db_session, site, 2099) == pytest.approx(56.1)


def test_falls_back_when_no_active_import(db_session: Session):
    """Une cible appartenant à un import inactif est ignorée."""
    site = _make_site(db_session, nb=56.1)
    imp = _add_import(db_session, active=False)
    _add_cible(db_session, import_id=imp.id, code=site.code_site, annee=2028, nb=18.0)
    db_session.commit()

    assert resolve_nb_for_year(db_session, site, 2028) == pytest.approx(56.1)


def test_falls_back_when_no_dalkia_data_at_all(db_session: Session):
    """Site hors périmètre DALKIA : aucune cible, fallback pur."""
    site = _make_site(db_session, nb=42.0)
    db_session.commit()

    assert resolve_nb_for_year(db_session, site, 2028) == pytest.approx(42.0)


def test_city_scoping_excludes_other_city(db_session: Session):
    """La cible d'une autre commune n'est jamais retenue."""
    site = _make_site(db_session, city_id=1, nb=56.1)
    imp_other = _add_import(db_session, city_id=2)
    _add_cible(db_session, import_id=imp_other.id, code=site.code_site, annee=2028, nb=18.0, city_id=2)
    db_session.commit()

    assert resolve_nb_for_year(db_session, site, 2028) == pytest.approx(56.1)


def test_zero_or_null_cible_falls_back(db_session: Session):
    """Une cible NB nulle ou à 0 ne masque pas le scalaire (évite un faux 'insuffisant')."""
    site = _make_site(db_session, nb=56.1)
    imp = _add_import(db_session)
    _add_cible(db_session, import_id=imp.id, code=site.code_site, annee=2028, nb=None)
    _add_cible(db_session, import_id=imp.id, code=site.code_site, annee=2029, nb=0.0)
    db_session.commit()

    assert resolve_nb_for_year(db_session, site, 2028) == pytest.approx(56.1)
    assert resolve_nb_for_year(db_session, site, 2029) == pytest.approx(56.1)
