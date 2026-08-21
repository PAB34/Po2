"""Reclassement local ↔ bâtiment — ce que l'entité doit emporter avec elle.

Un reclassement **supprime** l'entité et en recrée une avec un nouvel identifiant.
Deux choses en découlaient silencieusement, avant ces tests :

1. l'adresse, la position et le cadastre n'étaient pas transportés — promouvoir un
   local le dépouillait de tout ce qui permettait de le situer ;
2. les biens ASTECH qui visaient l'entité devenaient orphelins (`ON DELETE SET NULL`),
   sans qu'aucun garde-fou ne le signale : celui qui existe vérifie les compteurs et le
   CVC, mais ignorait le référentiel historique.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.building import Building
from app.models.city import City
from app.models.local import Local
from app.models.patrimoine_legacy import PatrimoineLegacyAsset
from app.models.site import Site
from app.models.user import User
from app.schemas.building import PatrimonyReclassifyPayload
from app.services.buildings import reclassify_building, reclassify_local


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.add(Site(id=1, city_id=1, nom_site="GROUPE SCOLAIRE"))
        session.commit()
        yield session


@pytest.fixture()
def user():
    return User(id=1, email="a@b.c", password_hash="x", nom="T", prenom="T", city_id=1)


def _building(db: Session, **kwargs) -> Building:
    defaults = dict(
        city_id=1,
        site_id=1,
        nom_batiment="ECOLE JEAN MOULIN",
        nom_commune="Sete",
        adresse_reconstituee="12 RUE DES CAPECHADES",
        code_postal="34200",
        latitude=43.404512,
        longitude=3.693845,
        dgfip_reference_norm="34301000AK0149",
        source_creation="IMPORT",
        statut_geocodage="IGN_VALIDE",
    )
    defaults.update(kwargs)
    building = Building(**defaults)
    db.add(building)
    db.commit()
    return building


def test_promouvoir_un_local_lui_fait_emporter_son_adresse(db_session: Session, user: User):
    """Un local promu en bâtiment garde adresse, position et cadastre.

    À défaut des siens, il prend ceux de son bâtiment porteur : il était dedans.
    """
    parent = _building(db_session)
    local = Local(
        building_id=parent.id,
        nom_local="LOGEMENT DE FONCTION",
        type_local="PRINCIPAL",
        adresse_reconstituee="14 RUE DES CAPECHADES",
        latitude=43.40,
        longitude=3.69,
    )
    db_session.add(local)
    db_session.commit()

    result = reclassify_local(
        db_session, local, PatrimonyReclassifyPayload(target_type="building"), user
    )

    created = db_session.get(Building, result.entity_id)
    assert created.nom_batiment == "LOGEMENT DE FONCTION"
    assert created.adresse_reconstituee == "14 RUE DES CAPECHADES"  # la sienne
    assert created.latitude == 43.40
    # Le cadastre n'etait pas renseigne sur le local : il vient du batiment porteur.
    assert created.dgfip_reference_norm == "34301000AK0149"
    # Il reste dans le meme site que son ancien parent.
    assert created.site_id == 1


def test_promouvoir_un_local_emporte_ses_biens_astech(db_session: Session, user: User):
    """Le rattachement suit l'entité : c'est la même réalité qui change de niveau."""
    parent = _building(db_session)
    local = Local(building_id=parent.id, nom_local="SALLE DES FETES", type_local="PRINCIPAL")
    db_session.add(local)
    db_session.commit()
    asset = PatrimoineLegacyAsset(
        city_id=1, code_bien="BATI00140", designation="SALLE DES FETES",
        building_id=parent.id, local_id=local.id, target_type="local", status="lie",
    )
    db_session.add(asset)
    db_session.commit()

    result = reclassify_local(
        db_session, local, PatrimonyReclassifyPayload(target_type="building"), user
    )

    db_session.refresh(asset)
    assert asset.building_id == result.entity_id
    assert asset.local_id is None
    assert asset.target_type == "building"
    # Le rattachement n'a pas ete rompu en silence.
    assert asset.status == "lie"


def test_retrograder_un_batiment_emporte_tout_aussi(db_session: Session, user: User):
    """Sens inverse : le bâtiment devient un local du bâtiment cible, sans rien perdre."""
    cible = _building(db_session, nom_batiment="ECOLE PRINCIPALE")
    building = _building(
        db_session,
        nom_batiment="PREAU",
        adresse_reconstituee="16 RUE DES CAPECHADES",
        latitude=43.41,
        longitude=3.70,
    )
    asset = PatrimoineLegacyAsset(
        city_id=1, code_bien="BATI00272", designation="PREAU",
        building_id=building.id, target_type="building", status="lie",
    )
    db_session.add(asset)
    db_session.commit()

    result = reclassify_building(
        db_session,
        building,
        PatrimonyReclassifyPayload(target_type="local", target_building_id=cible.id),
        user,
    )

    created = db_session.get(Local, result.entity_id)
    assert created.building_id == cible.id
    assert created.nom_local == "PREAU"
    assert created.adresse_reconstituee == "16 RUE DES CAPECHADES"
    assert created.latitude == 43.41
    assert created.dgfip_reference_norm == "34301000AK0149"

    db_session.refresh(asset)
    assert asset.local_id == created.id
    assert asset.building_id == cible.id
    assert asset.target_type == "local"


def test_aucun_bien_astech_ne_reste_orphelin(db_session: Session, user: User):
    """Aucun bien ne doit se retrouver sans cible après un reclassement."""
    parent = _building(db_session)
    local = Local(building_id=parent.id, nom_local="ATELIER", type_local="PRINCIPAL")
    db_session.add(local)
    db_session.commit()
    db_session.add(
        PatrimoineLegacyAsset(
            city_id=1, code_bien="BATI00001", designation="ATELIER",
            building_id=parent.id, local_id=local.id, target_type="local", status="propose",
        )
    )
    db_session.commit()

    reclassify_local(db_session, local, PatrimonyReclassifyPayload(target_type="building"), user)

    orphelins = db_session.scalars(
        select(PatrimoineLegacyAsset).where(PatrimoineLegacyAsset.building_id.is_(None))
    ).all()
    assert orphelins == []
