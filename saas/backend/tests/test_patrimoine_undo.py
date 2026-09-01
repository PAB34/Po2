"""Retour arrière sur le rapprochement ASTECH (décision Q46).

Ce module réécrit des lignes en base : il n'a pas le droit d'être approximatif. Les cas
vérifiés sont ceux où une annulation naïve se trompe —

- **une création** s'annule en supprimant, pas en vidant les champs ;
- **une suppression** s'annule en réinsérant la ligne AVEC son identifiant d'origine,
  sinon les biens ASTECH qui la désignaient pointent dans le vide ;
- **une suppression en cascade** doit revenir entière : bâtiment, locaux et
  rattachements, dans l'ordre des clés étrangères ;
- **un geste de masse** n'est pas annulable, et doit alors BLOQUER la pile au lieu de
  laisser « Annuler » défaire silencieusement l'action d'avant.
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
from app.models.patrimoine_undo import PatrimoineUndoEntry
from app.models.site import Site  # noqa: F401 (enregistre la table)
from app.models.user import User  # noqa: F401 (enregistre la table)
from app.services import patrimoine_undo as undo
from app.services.buildings import delete_building, delete_local


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


def _asset(**kwargs) -> PatrimoineLegacyAsset:
    base = dict(
        city_id=1,
        code_bien="BATI00001",
        designation="RESTAURANT SCOLAIRE",
        nomcourt="RESTAURANT SCOLAIRE",
        target_type="building",
        status="a_traiter",
        source_payload_json="{}",
    )
    base.update(kwargs)
    return PatrimoineLegacyAsset(**base)


def _record(db: Session, label: str):
    return undo.record(db, city_id=1, user_id=1, label=label)


# --- Créations ---------------------------------------------------------------

def test_annuler_une_creation_supprime_la_ligne(db_session: Session):
    with _record(db_session, "Création d'un bâtiment Po2"):
        db_session.add(Building(city_id=1, nom_batiment="GYMNASE", nom_commune="Sete"))
        db_session.commit()
    assert db_session.scalar(select(Building).where(Building.nom_batiment == "GYMNASE"))

    resultat = undo.undo_last(db_session, 1)

    assert resultat["annule"] is True
    assert db_session.scalar(select(Building).where(Building.nom_batiment == "GYMNASE")) is None


# --- Modifications -----------------------------------------------------------

def test_annuler_un_renommage_rend_l_ancien_nom(db_session: Session):
    building = Building(id=42, city_id=1, nom_batiment="ECOLE LOUISE MICHEL", nom_commune="Sete")
    db_session.add(building)
    db_session.commit()

    with _record(db_session, "Renommage"):
        building.nom_batiment = "ECOLE MATERNELLE LOUISE MICHEL"
        db_session.commit()

    undo.undo_last(db_session, 1)

    db_session.expire_all()
    assert db_session.get(Building, 42).nom_batiment == "ECOLE LOUISE MICHEL"


def test_annuler_un_rattachement_rend_le_quadruplet_d_avant(db_session: Session):
    """Le cas le plus courant : ce n'est pas qu'un champ qui change, c'est un état."""
    db_session.add(Building(id=42, city_id=1, nom_batiment="ECOLE", nom_commune="Sete"))
    asset = _asset()
    db_session.add(asset)
    db_session.commit()

    with _record(db_session, "Rattachement"):
        asset.building_id = 42
        asset.status = "lie"
        asset.link_origin = "manual"
        asset.designation = "ECOLE"
        asset.nomcourt = "ECOLE"
        db_session.commit()

    undo.undo_last(db_session, 1)

    db_session.expire_all()
    restored = db_session.get(PatrimoineLegacyAsset, asset.id)
    assert restored.building_id is None
    assert restored.status == "a_traiter"
    assert restored.link_origin is None
    assert restored.nomcourt == "RESTAURANT SCOLAIRE"


# --- Suppressions ------------------------------------------------------------

def test_annuler_la_suppression_d_un_local_rend_son_identifiant(db_session: Session):
    """L'identifiant doit revenir à l'identique : un bien ASTECH le désigne."""
    db_session.add(Building(id=42, city_id=1, nom_batiment="ECOLE", nom_commune="Sete"))
    db_session.add(Local(id=7, building_id=42, nom_local="SALLE POLYVALENTE", type_local="IMPORT"))
    db_session.add(_asset(building_id=42, local_id=7, target_type="local", status="lie"))
    db_session.commit()

    local = db_session.get(Local, 7)
    with _record(db_session, "Suppression d'un local Po2"):
        delete_local(db_session, local)
    assert db_session.get(Local, 7) is None

    undo.undo_last(db_session, 1)

    db_session.expire_all()
    revenu = db_session.get(Local, 7)
    assert revenu is not None
    assert revenu.nom_local == "SALLE POLYVALENTE"
    asset = db_session.scalar(select(PatrimoineLegacyAsset))
    assert asset.local_id == 7
    assert asset.target_type == "local"


def test_annuler_la_suppression_d_un_batiment_rend_TOUTE_la_cascade(db_session: Session):
    """Bâtiment, locaux et rattachements : une restauration partielle serait fausse."""
    db_session.add(Building(id=42, city_id=1, nom_batiment="ECOLE", nom_commune="Sete"))
    db_session.add(Local(id=7, building_id=42, nom_local="SALLE", type_local="IMPORT"))
    db_session.add(_asset(building_id=42, local_id=7, target_type="local", status="lie"))
    db_session.commit()

    with _record(db_session, "Suppression d'un bâtiment Po2"):
        delete_building(db_session, db_session.get(Building, 42))
    assert db_session.get(Building, 42) is None
    assert db_session.get(Local, 7) is None

    undo.undo_last(db_session, 1)

    db_session.expire_all()
    assert db_session.get(Building, 42) is not None
    assert db_session.get(Local, 7) is not None
    asset = db_session.scalar(select(PatrimoineLegacyAsset))
    assert asset.building_id == 42
    assert asset.local_id == 7
    assert asset.status == "lie"


def test_supprimer_un_batiment_ne_laisse_pas_un_bien_lie_sans_batiment(db_session: Session):
    """Les cascades de la base laissaient un état que l'écran ne sait pas représenter."""
    db_session.add(Building(id=42, city_id=1, nom_batiment="ECOLE", nom_commune="Sete"))
    db_session.add(_asset(building_id=42, status="lie", link_origin="manual"))
    db_session.commit()

    delete_building(db_session, db_session.get(Building, 42))

    asset = db_session.scalar(select(PatrimoineLegacyAsset))
    assert asset.building_id is None
    assert asset.status == "a_traiter"
    assert asset.link_origin is None


# --- Pile et bornes ----------------------------------------------------------

def test_les_annulations_remontent_la_pile_une_a_une(db_session: Session):
    building = Building(id=42, city_id=1, nom_batiment="UN", nom_commune="Sete")
    db_session.add(building)
    db_session.commit()

    with _record(db_session, "Renommage 1"):
        building.nom_batiment = "DEUX"
        db_session.commit()
    with _record(db_session, "Renommage 2"):
        building.nom_batiment = "TROIS"
        db_session.commit()

    undo.undo_last(db_session, 1)
    db_session.expire_all()
    assert db_session.get(Building, 42).nom_batiment == "DEUX"

    undo.undo_last(db_session, 1)
    db_session.expire_all()
    assert db_session.get(Building, 42).nom_batiment == "UN"

    assert undo.undo_last(db_session, 1)["annule"] is False


def test_un_geste_de_masse_bloque_la_pile_au_lieu_de_defaire_autre_chose(db_session: Session):
    """Sans cette borne, « Annuler » après un import défait l'action d'AVANT l'import."""
    building = Building(id=42, city_id=1, nom_batiment="AVANT", nom_commune="Sete")
    db_session.add(building)
    db_session.commit()
    with _record(db_session, "Renommage"):
        building.nom_batiment = "APRES"
        db_session.commit()

    with _record(db_session, "Import ASTECH"):
        for index in range(undo.MAX_ROWS + 1):
            db_session.add(_asset(code_bien=f"BATI{index:05d}"))
        db_session.commit()

    resultat = undo.undo_last(db_session, 1)

    assert resultat["annule"] is False
    assert resultat["motif"] == "trop_vaste"
    # Le renommage est toujours là : la borne n'a pas été franchie.
    db_session.expire_all()
    assert db_session.get(Building, 42).nom_batiment == "APRES"


def test_une_action_qui_echoue_n_est_pas_journalisee(db_session: Session):
    db_session.add(Building(id=42, city_id=1, nom_batiment="ECOLE", nom_commune="Sete"))
    db_session.commit()

    with pytest.raises(RuntimeError):
        with _record(db_session, "Action qui échoue"):
            db_session.get(Building, 42).nom_batiment = "JAMAIS"
            raise RuntimeError("boom")

    assert db_session.scalars(select(PatrimoineUndoEntry)).all() == []


def test_une_lecture_ne_cree_aucune_entree(db_session: Session):
    db_session.add(Building(id=42, city_id=1, nom_batiment="ECOLE", nom_commune="Sete"))
    db_session.commit()

    with _record(db_session, "Consultation"):
        db_session.get(Building, 42)

    assert undo.describe(undo.last_entry(db_session, 1))["disponible"] is False
