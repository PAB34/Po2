"""Attribution IGN : un toponyme de ZONE ne doit pas renommer le bâtiment.

Cas réel constaté en prod le 2026-08-19 sur le groupe scolaire Anatole France.
Quand le bâtiment IGN n'a pas de nom propre, `_resolve_building_name` retombe sur le
toponyme de la zone qui l'englobe (`zone_d_activite_ou_d_interet`). Ce nom désigne le
groupe scolaire entier, pas un bâtiment : « Attribuer IGN » renommait donc à l'identique
tous les bâtiments de la cour.

Conséquences mesurées en base : 3 bâtiments Po2 nommés « École Élémentaire Anatole
France », dont 2 accrochés au même bâtiment IGN. Le rapprochement ASTECH ne pouvait plus
les départager (garde-fou « plusieurs bâtiments proches ») et la référente n'avait plus
aucun critère à l'écran pour choisir.

Règle verrouillée ici : on n'écrase un nom existant que si l'utilisateur l'a validé, ou
si le nom vient du bâtiment IGN lui-même (`resolved_name_source == "batiment"`).
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.building import Building
from app.models.city import City
from app.models.local import Local  # noqa: F401
from app.schemas.building import BuildingIgnAttachmentPayload
from app.services.buildings import attach_building_ign


def _feature(resolved_name: str, source: str) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [3.659, 43.412]},
        "properties": {
            # Le bâtiment IGN lui-même est anonyme : c'est tout le sujet.
            "name": "" if source != "batiment" else resolved_name,
            "resolved_name": resolved_name,
            "resolved_name_source": source,
            "ign_id": "batiment.1193443",
            "attributes": {},
        },
    }


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


def _building(db: Session, nom: str | None) -> Building:
    building = Building(city_id=1, nom_batiment=nom, nom_commune="Sete")
    db.add(building)
    db.commit()
    db.refresh(building)
    return building


def test_un_toponyme_de_zone_ne_renomme_pas_un_batiment_deja_nomme(db_session: Session):
    building = _building(db_session, "ECOLE MATERNELLE SUZANNE LACORE")
    updated = attach_building_ign(
        db_session,
        building,
        BuildingIgnAttachmentPayload(
            selected_features=[
                _feature("École Élémentaire Anatole France", "zone_d_activite_ou_d_interet")
            ]
        ),
    )
    # Le nom d'origine survit : sans ça, tous les bâtiments de la cour deviennent homonymes.
    assert updated.nom_batiment == "ECOLE MATERNELLE SUZANNE LACORE"
    # La proposition reste disponible : l'écran peut l'offrir, il ne l'impose plus.
    assert updated.ign_name_proposed == "École Élémentaire Anatole France"
    # Le reste de l'attachement (cadastre, statut) n'est pas affecté par le garde-fou.
    assert updated.statut_geocodage == "IGN_VALIDE"


def test_le_nom_du_batiment_ign_lui_meme_est_bien_repris(db_session: Session):
    building = _building(db_session, "ANCIEN NOM")
    updated = attach_building_ign(
        db_session,
        building,
        BuildingIgnAttachmentPayload(
            selected_features=[_feature("HALLES CENTRALES", "batiment")]
        ),
    )
    assert updated.nom_batiment == "HALLES CENTRALES"


def test_un_nom_valide_par_l_utilisateur_gagne_toujours(db_session: Session):
    building = _building(db_session, "ECOLE MATERNELLE SUZANNE LACORE")
    updated = attach_building_ign(
        db_session,
        building,
        BuildingIgnAttachmentPayload(
            validated_name="ECOLE MATERNELLE SUZANNE LACORE - ANNEXE",
            selected_features=[
                _feature("École Élémentaire Anatole France", "zone_d_activite_ou_d_interet")
            ],
        ),
    )
    assert updated.nom_batiment == "ECOLE MATERNELLE SUZANNE LACORE - ANNEXE"


def test_un_batiment_sans_nom_accepte_le_toponyme_de_zone(db_session: Session):
    # Mieux vaut un nom approximatif que pas de nom du tout : rien n'est écrasé ici.
    building = _building(db_session, None)
    updated = attach_building_ign(
        db_session,
        building,
        BuildingIgnAttachmentPayload(
            selected_features=[
                _feature("École Élémentaire Anatole France", "zone_d_activite_ou_d_interet")
            ]
        ),
    )
    assert updated.nom_batiment == "École Élémentaire Anatole France"


def test_l_attribution_ign_descend_jusqu_au_bien_astech(db_session: Session):
    """Le cadastre obtenu par l'IGN doit atteindre le fichier de retour ASTECH.

    Les attributs IGN sont écrits sur le **bâtiment Po2** — c'est le référentiel de
    vérité, et c'est voulu. Mais le bien ASTECH ne les récupérait jamais : il gardait
    les valeurs héritées AVANT l'attribution. « Attribuer IGN » enrichissait donc Po2
    sans que rien n'atteigne l'export.
    """
    from app.models.patrimoine_legacy import PatrimoineLegacyAsset

    building = _building(db_session, "STADE FRANCOIS MAILLOL")
    building.adresse_reconstituee = "12 RUE DES CAPECHADES"
    building.dgfip_reference_norm = "34301000AK0149"
    db_session.add(building)
    asset = PatrimoineLegacyAsset(
        city_id=1,
        code_bien="BATI00450",
        designation="STADE FRANCOIS MAILLOL",
        building_id=building.id,
        target_type="building",
        status="lie",
        # Valeurs héritées d'AVANT : elles doivent être remplacées.
        resolved_street="ANCIENNE VOIE",
        resolved_refcad="ZZ001",
        resolved_source="building",
    )
    db_session.add(asset)
    db_session.commit()

    attach_building_ign(
        db_session,
        building,
        BuildingIgnAttachmentPayload(
            selected_features=[_feature("STADE FRANCOIS MAILLOL", "batiment")]
        ),
    )

    db_session.refresh(asset)
    # Le bien a bien recupere ce que le batiment porte desormais.
    assert asset.resolved_refcad == "AK149"
    assert asset.resolved_street == "RUE DES CAPECHADES"
    assert asset.resolved_housenumber == "12"
    # Les attributs IGN eux-memes restent sur le batiment Po2, pas sur le bien.
    assert building.statut_geocodage == "IGN_VALIDE"
