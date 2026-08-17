"""Propagation des rattachements CVC vers les équipements.

Couvre la règle tranchée le 2026-08-17 : un libellé source couvrant plusieurs
bâtiments (ex. « Élémentaire LA RENAISSANCE + restaurant scolaire ») rattache ses
équipements au **bâtiment principal** (le premier déclaré) au lieu de les laisser
orphelins, le périmètre complet restant tracé dans `building_ids_json`.
"""
from __future__ import annotations

import io

import openpyxl
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.building import Building
from app.models.city import City
from app.models.cvc import CvcInventoryItem, CvcSourceBuildingMapping
from app.models.equipment import EquipmentReference  # noqa: F401 (enregistre la table)
from app.models.local import Local  # noqa: F401
from app.models.site import Site
from app.schemas.cvc import CvcSourceBuildingMappingUpdate
from app.services.cvc import (
    import_cvc_from_excel,
    reapply_source_building_mappings,
    update_cvc_source_building_mapping,
)

DALKIA_HEADER = [
    "SITE",
    "BATIMENT",
    "NIVEAU",
    "LOCAL",
    "DESIGNATION",
    "FAMILLE",
    "MARQUE",
    "MODELE",
    "STATUT",
    "ETAT SANTE",
    "QTE RELEVEE",
    "DATE MES",
]

SOURCE_LABEL = "VDS-ENS 13 Elementaire LA RENAISSANCE + restaurant scolaire"


def _workbook_bytes(header: list[str], rows: list[list]) -> bytes:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


def _seed_two_buildings(db: Session) -> tuple[Building, Building]:
    site = Site(city_id=1, nom_site="Groupe scolaire LA RENAISSANCE")
    db.add(site)
    db.flush()
    ecole = Building(city_id=1, site_id=site.id, nom_batiment="Elementaire LA RENAISSANCE", nom_commune="Sete")
    restaurant = Building(city_id=1, site_id=site.id, nom_batiment="Restaurant scolaire LA RENAISSANCE", nom_commune="Sete")
    db.add_all([ecole, restaurant])
    db.commit()
    return ecole, restaurant


def _import_one_item(db: Session) -> CvcInventoryItem:
    raw = _workbook_bytes(
        DALKIA_HEADER,
        [[SOURCE_LABEL, None, None, None, "Chaudiere gaz", "Chaudiere", None, None, None, "bon", 1, 2015]],
    )
    import_cvc_from_excel(db, raw, [], city_id=1)
    item = db.scalars(select(CvcInventoryItem)).one()
    return item


def _mapping_for_label(db: Session) -> CvcSourceBuildingMapping:
    return db.scalars(
        select(CvcSourceBuildingMapping).where(CvcSourceBuildingMapping.source_site_raw == SOURCE_LABEL)
    ).one()


def test_multi_building_mapping_attaches_to_primary(db_session):
    ecole, restaurant = _seed_two_buildings(db_session)
    _import_one_item(db_session)
    mapping = _mapping_for_label(db_session)

    update_cvc_source_building_mapping(
        db_session,
        mapping.id,
        CvcSourceBuildingMappingUpdate(building_ids=[ecole.id, restaurant.id], status="matched"),
        city_id=1,
    )

    item = db_session.scalars(select(CvcInventoryItem)).one()
    # Rattaché au bâtiment principal, plus orphelin.
    assert item.building_id == ecole.id
    # Le local n'a pas de sens quand le périmètre couvre plusieurs bâtiments.
    assert item.local_id is None
    # Le périmètre complet reste tracé côté mapping.
    db_session.refresh(mapping)
    assert mapping.building_ids_json is not None
    assert str(restaurant.id) in mapping.building_ids_json


def test_single_building_mapping_still_attaches(db_session):
    ecole, _ = _seed_two_buildings(db_session)
    _import_one_item(db_session)
    mapping = _mapping_for_label(db_session)

    update_cvc_source_building_mapping(
        db_session,
        mapping.id,
        CvcSourceBuildingMappingUpdate(building_ids=[ecole.id], status="matched"),
        city_id=1,
    )

    item = db_session.scalars(select(CvcInventoryItem)).one()
    assert item.building_id == ecole.id


def test_reapply_propagates_existing_mappings(db_session):
    ecole, restaurant = _seed_two_buildings(db_session)
    _import_one_item(db_session)
    mapping = _mapping_for_label(db_session)

    # Simule l'état laissé par l'ancienne règle : cible multi-bâtiments enregistrée,
    # mais équipement resté orphelin.
    mapping.building_ids_json = f"[{ecole.id}, {restaurant.id}]"
    mapping.building_id = None
    mapping.status = "matched"
    item = db_session.scalars(select(CvcInventoryItem)).one()
    item.building_id = None
    db_session.commit()

    result = reapply_source_building_mappings(db_session, city_id=1)

    assert result["mappings_applied"] >= 1
    assert result["rows_updated"] >= 1
    item = db_session.scalars(select(CvcInventoryItem)).one()
    assert item.building_id == ecole.id


def test_reapply_skips_unresolved_mappings(db_session):
    _seed_two_buildings(db_session)
    _import_one_item(db_session)
    mapping = _mapping_for_label(db_session)
    mapping.building_ids_json = None
    mapping.building_id = None
    mapping.site_id = None
    db_session.commit()

    result = reapply_source_building_mappings(db_session, city_id=1)

    assert result["mappings_applied"] == 0
    item = db_session.scalars(select(CvcInventoryItem)).one()
    assert item.building_id is None
