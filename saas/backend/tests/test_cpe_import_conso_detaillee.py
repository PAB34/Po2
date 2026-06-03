"""Tests de l'import du vrai format DALKIA 'consommation détaillée' (multi-fluides)."""
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe import CpeGazReleve, CpeSite
from app.services.cpe import PCS_PCI_RATIO
from app.services.cpe_import import _extract_code_site, import_releves_csv


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.add(CpeSite(city_id=1, code_site="VDS-SPORT 05", nom_site="Gymnase", categorie="SPORT"))
        session.commit()
        yield session


def test_extract_code_site():
    assert _extract_code_site("SETE GYMNASE VINCENT FERRARI VDS-SPORT 05") == "VDS-SPORT 05"
    assert _extract_code_site("SETE STRUCTURE MULTI ACCUEIL CHATEAU VERT CCAS 05") == "CCAS 05"
    assert _extract_code_site("SETE GS LANGEVIN VDS-ENS 17.05") == "VDS-ENS 17.05"
    assert _extract_code_site("SETE SANS CODE") is None


CSV = (
    "CODE CONTRAT;SITE;TYPE DE COMPTEUR;DATE DU RELEVE;CONSOMMATION;UNITE;MWH PCS\n"
    "C1;SETE GYMNASE VDS-SPORT 05;GAZ;2026-01-15;1000;m3;11.068\n"
    "C1;SETE GYMNASE VDS-SPORT 05;GAZ;2026-01-28;1000;m3;11.068\n"
    "C1;SETE GYMNASE VDS-SPORT 05;ECS;2026-01-20;5;m3;0\n"
    "C1;SETE GYMNASE VDS-SPORT 05;ELECTRICITE;2026-01-20;300;k Wh;0\n"
    "C1;SETE INCONNU VDS-ENS 99;GAZ;2026-01-15;500;m3;5.534\n"
)


def test_import_detailed_aggregates_gas_and_ecs(db_session: Session):
    res = import_releves_csv(db_session, CSV)
    # 1 site connu importé, 1 site inconnu signalé
    assert res.nb_inseres == 1
    assert "VDS-ENS 99" in res.sites_inconnus

    rel = db_session.scalar(
        select(CpeGazReleve).where(CpeGazReleve.annee == 2026, CpeGazReleve.mois == 1)
    )
    assert rel is not None
    # 2 lignes gaz de 11.068 MWh PCS -> somme 22.136 PCS -> PCI = 22.136/1.1068 = 20.0
    assert rel.qt_mwh_pci == pytest.approx(22.136 / PCS_PCI_RATIO, abs=0.01)
    assert rel.qt_mwh_pci == pytest.approx(20.0, abs=0.05)
    # ECS agrégé en m3
    assert rel.volume_ecs_m3 == pytest.approx(5.0)


def test_simple_format_still_works(db_session: Session):
    """Le format simple historique (code_site, qt_mwh_pci) reste pris en charge."""
    simple = "code_site;date_releve;qt_mwh_pci;volume_ecs_m3\nVDS-SPORT 05;2026-02-15;42;3\n"
    res = import_releves_csv(db_session, simple)
    assert res.nb_inseres == 1
    rel = db_session.scalar(select(CpeGazReleve).where(CpeGazReleve.mois == 2))
    assert rel.qt_mwh_pci == pytest.approx(42)
