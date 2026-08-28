"""Invariants du rapprochement ASTECH ↔ Po2 — le filet qui manquait.

Ce fichier n'ajoute pas de fonctionnalité : il vérifie que **tous** les chemins qui
rattachent un bien respectent les mêmes règles. Ils avaient dérivé un à un, et chaque
écart n'a été découvert qu'à l'usage, en prod :

- `confirm_proposed` n'adoptait pas le nom Po2 → 49 biens « liés » portaient encore leur
  libellé ASTECH, et c'est ce libellé qui repartait dans le fichier de la collectivité ;
- `convert_asset_to_local` nommait le local depuis le libellé COURANT, déjà remplacé par
  celui du bâtiment → le local naissait homonyme de son parent ;
- `update_asset(local_id=…)` n'adoptait rien du tout.

Les invariants vérifiés, pour chaque chemin :

**I1 — un bien rattaché porte le nom de sa cible Po2** (décision Q11), qu'il ait été
rattaché à la main, proposé puis confirmé, converti en local ou reclassé. C'est
`nomcourt`/`designation` que le réexport écrit, pas `resolved_name`.

**I2 — détacher rend le libellé ASTECH d'origine** (Q26), relu depuis la ligne source.

**I3 — le quadruplet (statut, bâtiment, local, niveau) reste cohérent** : pas de cible
« local » sans local, pas de « lié » sans bâtiment.
"""
from __future__ import annotations

import io
import json

import openpyxl
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.building import Building
from app.models.city import City
from app.models.local import Local
from app.models.patrimoine_legacy import PatrimoineLegacyAsset
from app.models.site import Site  # noqa: F401 (enregistre la table)
from app.models.user import User
from app.schemas.building import PatrimonyReclassifyPayload
from app.services.buildings import reclassify_local
from app.services.patrimoine_legacy import (
    confirm_proposed,
    convert_asset_to_local,
    import_astech_file,
    update_asset,
)

NOM_ASTECH = "RESTAURATION SCOLAIRE LOUISE MICHEL"
NOM_BATIMENT = "ECOLE MATERNELLE LOUISE MICHEL"


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


@pytest.fixture()
def user():
    return User(id=1, email="operatrice@sete.fr", city_id=1)


def _workbook() -> bytes:
    """Un export ASTECH minimal, à la deuxième génération d'en-têtes."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Worksheet"
    sheet.append(["Code", "Désignation", "Nom court", "Genre", "Adresse", "Ville", "Commune"])
    sheet.append(
        ["BATI00242", NOM_ASTECH, "RESTAURATION LOUISE MICHEL", "BATI / BATIMENT",
         "AV MERMOZ", "SETE", "34301 / 34301 SETE"]
    )
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


@pytest.fixture()
def contexte(db_session: Session):
    """Un bâtiment Po2 et un bien ASTECH au nom volontairement différent."""
    db_session.add(Building(id=42, city_id=1, nom_batiment=NOM_BATIMENT, nom_commune="Sete"))
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_workbook())
    asset = db_session.scalar(
        select(PatrimoineLegacyAsset).where(PatrimoineLegacyAsset.code_bien == "BATI00242")
    )
    assert asset.designation == NOM_ASTECH
    return asset


def _assert_coherent(asset: PatrimoineLegacyAsset) -> None:
    """I3 — le quadruplet ne doit jamais se contredire."""
    if asset.target_type == "local":
        assert asset.local_id is not None, "cible « local » sans local_id"
        assert asset.building_id is not None, "un local a toujours un bâtiment porteur"
    else:
        assert asset.local_id is None, "local_id conservé alors que la cible est le bâtiment"
    if asset.status == "lie":
        assert asset.building_id is not None, "« lié » sans bâtiment"


# --- I1 : le nom de la cible, par tous les chemins ---------------------------

def test_rattachement_manuel_a_un_batiment(db_session: Session, contexte):
    update_asset(db_session, contexte, building_id=42)
    assert contexte.nomcourt == NOM_BATIMENT
    _assert_coherent(contexte)


def test_confirmation_en_bloc(db_session: Session, contexte):
    contexte.building_id = 42
    contexte.status = "propose"
    db_session.commit()

    confirm_proposed(db_session, 1)

    db_session.refresh(contexte)
    assert contexte.nomcourt == NOM_BATIMENT
    _assert_coherent(contexte)


def test_rattachement_a_un_local_existant(db_session: Session, contexte):
    """Ce chemin n'adoptait rien : viser un local laissait le bien sous son ancien nom."""
    local = Local(id=7, building_id=42, nom_local="SALLE POLYVALENTE", type_local="IMPORT")
    db_session.add(local)
    db_session.commit()

    update_asset(db_session, contexte, local_id=7)

    assert contexte.nomcourt == "SALLE POLYVALENTE"
    _assert_coherent(contexte)


def test_conversion_en_local_apres_rattachement(db_session: Session, contexte):
    """Le local doit naître avec le nom ASTECH, pas celui du bâtiment déjà adopté."""
    update_asset(db_session, contexte, building_id=42)
    convert_asset_to_local(db_session, contexte)

    local = db_session.get(Local, contexte.local_id)
    assert local.nom_local == NOM_ASTECH
    assert contexte.nomcourt == NOM_ASTECH
    _assert_coherent(contexte)


def test_reclassement_d_un_local_en_batiment(db_session: Session, contexte, user: User):
    """Le bien suit sa cible, et prend le nom qu'elle porte à l'arrivée."""
    local = Local(id=7, building_id=42, nom_local="SALLE POLYVALENTE", type_local="IMPORT")
    db_session.add(local)
    db_session.commit()
    update_asset(db_session, contexte, local_id=7)

    reclassify_local(
        db_session, local, PatrimonyReclassifyPayload(target_type="building", name="GYMNASE"), user
    )

    db_session.refresh(contexte)
    assert contexte.target_type == "building"
    assert contexte.local_id is None
    assert contexte.nomcourt == "GYMNASE"
    _assert_coherent(contexte)


# --- I2 : détacher rend le libellé d'origine ---------------------------------

@pytest.mark.parametrize("via_local", [False, True])
def test_detacher_rend_le_nom_astech(db_session: Session, contexte, via_local: bool):
    if via_local:
        db_session.add(Local(id=7, building_id=42, nom_local="SALLE", type_local="IMPORT"))
        db_session.commit()
        update_asset(db_session, contexte, local_id=7)
    else:
        update_asset(db_session, contexte, building_id=42)
    assert contexte.nomcourt != NOM_ASTECH

    update_asset(db_session, contexte, clear_building=True, status="a_traiter")

    assert contexte.designation == NOM_ASTECH
    assert contexte.building_id is None
    _assert_coherent(contexte)


def test_le_payload_source_est_conserve_intact(db_session: Session, contexte):
    """C'est lui qui permet la restitution : aucun chemin ne doit l'écraser."""
    update_asset(db_session, contexte, building_id=42)
    convert_asset_to_local(db_session, contexte)

    payload = json.loads(contexte.source_payload_json)
    assert payload["Désignation"] == NOM_ASTECH
