"""Tests du rapprochement compteur energie -> batiment (matching)."""
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.building import Building
from app.models.building_meter import BuildingMeterLink
from app.models.gas import GasPce
from app.schemas.building import MeterMapping
from app.services import meter_matching as svc


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _user():
    return SimpleNamespace(city_id=1)


def _seed_buildings(db):
    mairie = Building(city_id=1, nom_batiment="Mairie", nom_commune="Sete")
    ecole = Building(city_id=1, nom_batiment="Ecole Jean Jaures", nom_commune="Sete")
    db.add_all([mairie, ecole])
    db.commit()
    db.refresh(mairie)
    db.refresh(ecole)
    return mairie, ecole


def test_list_meter_matches_gas_pce_suggests_building(db):
    mairie, _ = _seed_buildings(db)
    db.add(GasPce(city_id=1, id_pce="GI000123", nom_site="Mairie"))
    db.commit()

    matches = svc.list_meter_matches(db, _user())
    gas = [m for m in matches if m.fluid == "GAZ" and m.meter_identifier == "GI000123"]
    assert len(gas) == 1
    match = gas[0]
    assert match.current_building_id is None
    # La similarite "Mairie" doit ressortir le batiment Mairie en suggestion.
    assert match.auto_building_id == mairie.id
    assert any(s.building_id == mairie.id for s in match.suggestions)


def test_apply_gas_mapping_syncs_pce_and_creates_link(db):
    mairie, _ = _seed_buildings(db)
    db.add(GasPce(city_id=1, id_pce="GI000123", nom_site="Mairie"))
    db.commit()

    result = svc.apply_meter_mappings(
        db, _user(), [MeterMapping(fluid="GAZ", meter_identifier="GI000123", building_id=mairie.id)]
    )
    assert result.applied == 1

    pce = db.scalar(select(GasPce).where(GasPce.id_pce == "GI000123"))
    assert pce.building_id == mairie.id
    link = db.scalar(
        select(BuildingMeterLink).where(
            BuildingMeterLink.fluid == "GAZ", BuildingMeterLink.meter_identifier == "GI000123"
        )
    )
    assert link is not None
    assert link.building_id == mairie.id
    assert link.source == "MATCHING"
    assert link.validation_status == "VALIDE"


def test_apply_elec_mapping_then_move_canonical(db):
    mairie, ecole = _seed_buildings(db)

    svc.apply_meter_mappings(
        db, _user(), [MeterMapping(fluid="ELECTRICITE", meter_identifier="PRM999", building_id=mairie.id)]
    )
    links = list(
        db.scalars(select(BuildingMeterLink).where(BuildingMeterLink.meter_identifier == "PRM999"))
    )
    assert len(links) == 1
    assert links[0].building_id == mairie.id

    # Re-rattacher le meme PRM a un autre batiment : un seul lien canonique subsiste.
    result = svc.apply_meter_mappings(
        db, _user(), [MeterMapping(fluid="ELECTRICITE", meter_identifier="PRM999", building_id=ecole.id)]
    )
    assert result.updated >= 1
    links = list(
        db.scalars(select(BuildingMeterLink).where(BuildingMeterLink.meter_identifier == "PRM999"))
    )
    assert len(links) == 1
    assert links[0].building_id == ecole.id
