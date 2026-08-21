"""Dédoublonnage du référentiel Po2 (§23, décisions Q28/Q29).

Ce que ces tests protègent, dans l'ordre d'importance :

1. **Deux entités homonymes ne sont pas des doublons.** Mesuré en prod le 2026-08-21 :
   sur 5 paires de bâtiments homonymes, une seule en était un. Supprimer sur le nom
   effacerait les deux `WC PUBLIC` de la ville, les deux `ECOLE MATERNELLE LAKANAL`…
2. **Partager une parcelle non plus.** 19 parcelles portent 2 à 4 bâtiments : une école,
   sa cantine et son gymnase y cohabitent normalement.
3. **On ne supprime jamais ce qui porte des liens.** Le dédoublonnage efface des
   coquilles, il ne fusionne rien.
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
from app.models.site import Site  # noqa: F401 (enregistre la table)
from app.models.user import User
from app.services.buildings import BUILDING_REFERENCES, LOCAL_REFERENCES, purge_duplicates


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


def _building(db: Session, **kwargs) -> Building:
    defaults = dict(city_id=1, nom_commune="Sete", nom_batiment="ECOLE PAUL BERT")
    defaults.update(kwargs)
    building = Building(**defaults)
    db.add(building)
    db.commit()
    return building


def test_deux_batiments_identiques_en_tout_le_vide_part(db_session: Session, user: User):
    """Le seul vrai doublon de la prod : mêmes nom, position et parcelle."""
    garde = _building(
        db_session, id=1215, latitude=43.401165, longitude=3.692864,
        dgfip_reference_norm="34301000AP0116",
    )
    _building(
        db_session, id=1214, latitude=43.401165, longitude=3.692864,
        dgfip_reference_norm="34301000AP0116",
    )
    # Le survivant est celui qui porte quelque chose, pas le plus ancien identifiant.
    db_session.add(Local(building_id=garde.id, nom_local="SALLE", type_local="IMPORT"))
    db_session.commit()

    result = purge_duplicates(db_session, user)

    assert [entry["id"] for entry in result["batiments_supprimes"]] == [1214]
    assert db_session.get(Building, 1215) is not None
    assert db_session.get(Building, 1214) is None


def test_deux_wc_publics_homonymes_ailleurs_sont_epargnes(db_session: Session, user: User):
    """Corniche de Neuburg et Quai d'Alger : même nom, deux édicules distincts."""
    _building(db_session, id=1194, nom_batiment="WC PUBLIC", latitude=43.393517, longitude=3.672654)
    _building(db_session, id=1292, nom_batiment="WC PUBLIC", latitude=43.401019, longitude=3.699778)

    result = purge_duplicates(db_session, user)

    assert result["batiments_supprimes"] == []
    assert db_session.get(Building, 1194) is not None
    assert db_session.get(Building, 1292) is not None


def test_une_parcelle_partagee_ne_fait_pas_un_doublon(db_session: Session, user: User):
    """L'école, sa cantine et son gymnase partagent parcelle ET position de parcelle."""
    for id_, nom in ((1245, "ECOLE ELEMENTAIRE PAUL LANGEVIN"), (1246, "ECOLE MATERNELLE PAUL LANGEVIN"), (1247, "SMA FRANCOIS DOLTO")):
        _building(
            db_session, id=id_, nom_batiment=nom, latitude=43.394962, longitude=3.674422,
            dgfip_reference_norm="34301000BO0354",
        )

    result = purge_duplicates(db_session, user)

    assert result["batiments_supprimes"] == []


def test_un_doublon_qui_porte_des_liens_est_signale_pas_efface(db_session: Session, user: User):
    """Deux exemplaires identiques portant chacun quelque chose : on ne choisit pas."""
    for id_ in (1, 2):
        building = _building(
            db_session, id=id_, latitude=43.4, longitude=3.69, dgfip_reference_norm="AP0116",
        )
        db_session.add(Local(building_id=building.id, nom_local=f"SALLE {id_}", type_local="IMPORT"))
    db_session.commit()

    result = purge_duplicates(db_session, user)

    assert result["batiments_supprimes"] == []
    assert [entry["id"] for entry in result["conserves_car_lies"]] == [2]
    assert db_session.get(Building, 1) is not None
    assert db_session.get(Building, 2) is not None


def test_deux_etages_du_meme_local_ne_sont_pas_un_doublon(db_session: Session, user: User):
    """`LOCAL 343010345389` existe aux niveaux 2 et 3 du bâtiment 1223 : deux étages."""
    building = _building(db_session, id=1223, nom_batiment="ECOLE MATERNELLE LAKANAL")
    db_session.add(Local(building_id=building.id, nom_local="LOCAL 343010345389", type_local="IMPORT", niveau="2"))
    db_session.add(Local(building_id=building.id, nom_local="LOCAL 343010345389", type_local="IMPORT", niveau="3"))
    db_session.commit()

    result = purge_duplicates(db_session, user)

    assert result["locaux_supprimes"] == []
    assert db_session.scalar(select(Local).where(Local.niveau == "2")) is not None
    assert db_session.scalar(select(Local).where(Local.niveau == "3")) is not None


def test_deux_locaux_identiques_champ_pour_champ_partent(db_session: Session, user: User):
    building = _building(db_session, id=1144, nom_batiment="36 RUE PIERRE SEMARD")
    for _ in range(2):
        db_session.add(
            Local(
                building_id=building.id, nom_local="LOCAL 343010599151", type_local="IMPORT",
                adresse_reconstituee="36 Rue PIERRE SEMARD", dgfip_reference_norm="34301000AM0047",
            )
        )
    db_session.commit()

    result = purge_duplicates(db_session, user)

    assert len(result["locaux_supprimes"]) == 1
    assert db_session.scalars(select(Local)).all().__len__() == 1


def test_un_local_vise_par_un_bien_astech_survit_a_son_jumeau(db_session: Session, user: User):
    """Le survivant est celui qui porte le lien, pas le plus ancien identifiant."""
    building = _building(db_session, id=1, nom_batiment="MAIRIE")
    orphelin = Local(id=10, building_id=building.id, nom_local="SALLE", type_local="IMPORT")
    vise = Local(id=11, building_id=building.id, nom_local="SALLE", type_local="IMPORT")
    db_session.add_all([orphelin, vise])
    db_session.flush()
    db_session.add(
        PatrimoineLegacyAsset(
            city_id=1, code_bien="BATI00001", designation="SALLE",
            building_id=building.id, local_id=vise.id,
        )
    )
    db_session.commit()

    result = purge_duplicates(db_session, user)

    assert [entry["id"] for entry in result["locaux_supprimes"]] == [10]
    assert db_session.get(Local, 11) is not None


def test_a_blanc_ne_supprime_rien(db_session: Session, user: User):
    _building(db_session, id=1, latitude=43.4, longitude=3.69, dgfip_reference_norm="AP0116")
    _building(db_session, id=2, latitude=43.4, longitude=3.69, dgfip_reference_norm="AP0116")

    result = purge_duplicates(db_session, user, dry_run=True)

    assert [entry["id"] for entry in result["batiments_supprimes"]] == [2]
    assert db_session.get(Building, 2) is not None


def test_la_liste_des_references_couvre_tout_le_schema():
    """Garde-fou : une table qui pointerait vers un bâtiment sans être inscrite ici
    rendrait la suppression moins prudente — un doublon « vide » ne le serait plus."""
    def declared(target: str) -> set[tuple[str, str]]:
        found: set[tuple[str, str]] = set()
        for table in Base.metadata.tables.values():
            for column in table.columns:
                for fk in column.foreign_keys:
                    if fk.column.table.name == target:
                        found.add((table.name, column.name))
        return found

    assert declared("buildings") == set(BUILDING_REFERENCES)
    assert declared("locals") == set(LOCAL_REFERENCES)
