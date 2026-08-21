"""`update_building` est une mise à jour PARTIELLE, pas une remise à plat.

La fonction écrasait par `None` tout champ absent du payload. Un appel qui n'envoyait
que `nom_batiment` — renommer un bâtiment depuis l'écran de rapprochement ASTECH —
effaçait donc sa position, son adresse, son code postal et son cadastre.

Constaté en prod le 2026-08-21 : le bâtiment 1316 « STADE FRANCOIS MAILLOL », créé
avec ses coordonnées à 07:57, les avait perdues à 08:00 après un simple renommage. Il
disparaissait de la carte, et le bien ASTECH qui le visait semblait partir avec lui.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.building import Building
from app.models.city import City
from app.models.local import Local  # noqa: F401 (enregistre la table)
from app.models.site import Site
from app.schemas.building import BuildingUpdate
from app.services.buildings import update_building


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
def building(db_session: Session) -> Building:
    item = Building(
        city_id=1,
        site_id=1,
        nom_batiment="STADE FRANCOIS MAILLOL",
        nom_commune="Sete",
        code_postal="34200",
        adresse_reconstituee="12 RUE DES CAPECHADES",
        section="AK",
        numero_plan="0149",
        dgfip_reference_norm="34301000AK0149",
        latitude=43.4122,
        longitude=3.6735,
        source_creation="ASTECH",
        statut_geocodage="A_VERIFIER",
    )
    db_session.add(item)
    db_session.commit()
    return item


def test_renommer_ne_detruit_pas_la_position(db_session: Session, building: Building):
    """Le cas exact remonté : seul le nom est envoyé, tout le reste doit survivre."""
    update_building(db_session, building, BuildingUpdate(nom_batiment="STADE F. MAILLOL"))

    db_session.refresh(building)
    assert building.nom_batiment == "STADE F. MAILLOL"
    assert building.latitude == 43.4122
    assert building.longitude == 3.6735
    assert building.adresse_reconstituee == "12 RUE DES CAPECHADES"
    assert building.code_postal == "34200"
    assert building.section == "AK"
    assert building.numero_plan == "0149"
    # Le site de rattachement survivait deja, il ne doit pas regresser.
    assert building.site_id == 1


def test_un_champ_explicitement_vide_est_bien_efface(db_session: Session, building: Building):
    """La mise à jour partielle ne doit pas empêcher d'effacer volontairement un champ.

    La distinction porte sur la PRÉSENCE de la clé dans le payload, pas sur sa valeur.
    """
    update_building(db_session, building, BuildingUpdate(code_postal=None))

    db_session.refresh(building)
    assert building.code_postal is None
    # Les autres champs, eux, n'etaient pas dans le payload.
    assert building.latitude == 43.4122
    assert building.nom_batiment == "STADE FRANCOIS MAILLOL"


def test_le_formulaire_complet_ecrase_toujours(db_session: Session, building: Building):
    """Les écrans qui envoient tout le formulaire ne changent pas de comportement."""
    update_building(
        db_session,
        building,
        BuildingUpdate(
            nom_batiment="AUTRE NOM",
            code_postal="34300",
            adresse_reconstituee="1 RUE NEUVE",
            latitude=44.0,
            longitude=4.0,
        ),
    )

    db_session.refresh(building)
    assert building.nom_batiment == "AUTRE NOM"
    assert building.code_postal == "34300"
    assert building.adresse_reconstituee == "1 RUE NEUVE"
    assert building.latitude == 44.0
