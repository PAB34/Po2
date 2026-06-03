"""Tests de l'import du vrai format DALKIA 'consommation détaillée' (multi-fluides)."""
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe import CpeConsoReleve, CpeContractReference, CpeGazReleve, CpeSite
from app.services.cpe import PCS_PCI_RATIO, get_conso_synthese
from app.services.cpe_import import _extract_code_site, import_releves_csv


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.add(CpeSite(city_id=1, code_site="VDS-SPORT 05", nom_site="Gymnase", categorie="SPORT"))
        session.add(CpeContractReference(
            city_id=1,
            contract_code="C00190116O",
            contract_label="SETE (34) - BATIMENTS COMMUNAUX LOT 1",
            reference_kind="cpe_contract_scope",
            year=2026,
            market="SCOPE",
            billed_item="CPE_VILLE_LOT_1",
            active=True,
        ))
        session.commit()
        yield session


def test_extract_code_site():
    assert _extract_code_site("SETE GYMNASE VINCENT FERRARI VDS-SPORT 05") == "VDS-SPORT 05"
    assert _extract_code_site("SETE STRUCTURE MULTI ACCUEIL CHATEAU VERT CCAS 05") == "CCAS 05"
    assert _extract_code_site("SETE GS LANGEVIN VDS-ENS 17.05") == "VDS-ENS 17.05"
    assert _extract_code_site("SETE SANS CODE") is None


CPE = "C00190116O"  # contrat CPE Ville DALKIA Lot 1
CSV = (
    "CODE CONTRAT;SITE;TYPE DE COMPTEUR;DATE DU RELEVE;CONSOMMATION;UNITE;MWH PCS\n"
    f"{CPE};SETE GYMNASE VDS-SPORT 05;GAZ;2026-01-15;1000;m3;11.068\n"
    f"{CPE};SETE GYMNASE VDS-SPORT 05;GAZ;2026-01-28;1000;m3;11.068\n"
    f"{CPE};SETE GYMNASE VDS-SPORT 05;ECS;2026-01-20;5;m3;0\n"
    f"{CPE};SETE GYMNASE VDS-SPORT 05;ELECTRICITE;2026-01-20;300;k Wh;0\n"
    f"{CPE};SETE INCONNU VDS-ENS 99;GAZ;2026-01-15;500;m3;5.534\n"
    # autre marché (CREM PISCINE FONQUERNE) -> doit être ignoré, même si le code matchait
    "C00032657J;SETE GYMNASE VDS-SPORT 05;GAZ;2026-01-15;9999;m3;999\n"
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
    # La ligne du contrat C00032657J (999 PCS) NE doit PAS être comptée (autre marché).
    assert rel.qt_mwh_pci == pytest.approx(22.136 / PCS_PCI_RATIO, abs=0.01)
    assert rel.qt_mwh_pci == pytest.approx(20.0, abs=0.05)
    # ECS agrégé en m3
    assert rel.volume_ecs_m3 == pytest.approx(5.0)
    # note d'info sur les lignes hors marché CPE
    assert any("hors march" in e for e in res.erreurs)


def test_multifluide_conso_releves(db_session: Session):
    """Le stockage multi-fluides capte GAZ/ELEC/ECS (et site non rattaché en cpe_site_id=None)."""
    import_releves_csv(db_session, CSV)
    by_fluide = {
        (c.code_site, c.fluide): c
        for c in db_session.scalars(select(CpeConsoReleve).where(CpeConsoReleve.annee == 2026, CpeConsoReleve.mois == 1))
    }
    # le site connu a 3 fluides
    assert ("VDS-SPORT 05", "GAZ") in by_fluide
    assert ("VDS-SPORT 05", "ELEC") in by_fluide
    assert ("VDS-SPORT 05", "ECS") in by_fluide
    elec = by_fluide[("VDS-SPORT 05", "ELEC")]
    assert elec.consommation == pytest.approx(300)        # kWh
    assert elec.energie_mwh == pytest.approx(0.3)          # 300 kWh -> 0.3 MWh
    gaz = by_fluide[("VDS-SPORT 05", "GAZ")]
    assert gaz.energie_mwh == pytest.approx(22.136)        # MWh PCS
    assert gaz.cpe_site_id is not None                     # site rattaché
    # le site inconnu est tout de même capté (cpe_site_id None), pas perdu
    assert ("VDS-ENS 99", "GAZ") in by_fluide
    assert by_fluide[("VDS-ENS 99", "GAZ")].cpe_site_id is None
    # le contrat exclu (C00032657J) n'a rien créé
    assert all(c.contract_code != "C00032657J" for c in by_fluide.values())


def test_conso_synthese_exposes_unknown_sites_and_fluids(db_session: Session):
    import_releves_csv(db_session, CSV)

    synthese = get_conso_synthese(db_session, 2026, city_id=1)

    assert synthese.nb_sites_actifs == 1
    assert synthese.nb_sites_couverts == 1
    assert synthese.nb_sites_inconnus == 1
    assert [s.code_site for s in synthese.sites_inconnus] == ["VDS-ENS 99"]

    by_fluide = {f.fluide: f for f in synthese.fluides}
    assert by_fluide["GAZ"].total == pytest.approx(27.67, abs=0.01)
    assert by_fluide["GAZ"].nb_sites == 1
    assert by_fluide["ELEC"].total == pytest.approx(0.3)
    assert by_fluide["ECS"].total == pytest.approx(5.0)


def test_filtre_contrat_exclut_autre_marche(db_session: Session):
    """Une ligne d'un autre contrat (même si le code site matche) n'est jamais importée."""
    autre = (
        "CODE CONTRAT;SITE;TYPE DE COMPTEUR;DATE DU RELEVE;CONSOMMATION;UNITE;MWH PCS\n"
        "C00032657J;SETE GYMNASE VDS-SPORT 05;GAZ;2026-03-15;1000;m3;50\n"
    )
    res = import_releves_csv(db_session, autre)
    assert res.nb_inseres == 0
    assert db_session.scalar(select(CpeGazReleve).where(CpeGazReleve.mois == 3)) is None


def test_filtre_contrat_lit_le_referentiel_editable(db_session: Session):
    """Le perimetre CPE vient de cpe_contract_references, pas d'une constante de codes."""
    db_session.add(CpeContractReference(
        city_id=1,
        contract_code="C00999999Z",
        contract_label="Contrat editable de test",
        reference_kind="cpe_contract_scope",
        year=2026,
        market="SCOPE",
        billed_item="CPE_TEST",
        active=True,
    ))
    db_session.commit()
    csv = (
        "CODE CONTRAT;SITE;TYPE DE COMPTEUR;DATE DU RELEVE;CONSOMMATION;UNITE;MWH PCS\n"
        "C00999999Z;SETE GYMNASE VDS-SPORT 05;GAZ;2026-04-15;1000;m3;10\n"
    )
    res = import_releves_csv(db_session, csv, city_id=1)

    assert res.nb_inseres == 1
    releve = db_session.scalar(select(CpeGazReleve).where(CpeGazReleve.mois == 4))
    assert releve is not None
    assert releve.qt_mwh_pci == pytest.approx(10 / PCS_PCI_RATIO, abs=0.0001)


def test_simple_format_still_works(db_session: Session):
    """Le format simple historique (code_site, qt_mwh_pci) reste pris en charge."""
    simple = "code_site;date_releve;qt_mwh_pci;volume_ecs_m3\nVDS-SPORT 05;2026-02-15;42;3\n"
    res = import_releves_csv(db_session, simple)
    assert res.nb_inseres == 1
    rel = db_session.scalar(select(CpeGazReleve).where(CpeGazReleve.mois == 2))
    assert rel.qt_mwh_pci == pytest.approx(42)
