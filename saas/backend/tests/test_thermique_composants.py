"""Bibliothèque de projet et modèles réutilisables (lot L1) : catégories, codes, calcul d'un
composant, copies modèle ↔ projet, isolement entre comptes.
Voir docs/thermique/bibliotheque-projet-decisions.md."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.core.security import get_password_hash
from app.models.user import User
from app.services.thermique import ThermiqueError, create_project
from app.services.thermique_composants import (
    copy_component,
    create_component,
    get_component_for_user,
    list_components,
    serialize_component,
    update_component,
)
from thermique_moteur import composants

MUR_BETON = {
    "type": "mur",
    "donne_sur": "exterieur",
    "couches": [
        {"type": "materiau", "materiau_id": "2.3.1-8", "epaisseur_m": 0.013},  # plaque de plâtre
        {"type": "materiau", "materiau_id": "2.6.2.2-4", "epaisseur_m": 0.10, "isolant": True},  # laine de verre
        {"type": "materiau", "materiau_id": "2.2.1.1-1", "epaisseur_m": 0.20},  # béton plein
    ],
}


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _user(db: Session, email: str) -> User:
    user = User(email=email, password_hash=get_password_hash("motdepasse-solide"), nom="Nom", prenom="Prenom", role="USER", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# --- Moteur ------------------------------------------------------------------------------------


def test_codes_proposes_par_categorie():
    assert composants.code_suivant("murs", []) == "MUR 1"
    assert composants.code_suivant("murs", ["MUR 1", "mur 4", "Façade nord"]) == "MUR 5"
    assert composants.code_suivant("ponts_thermiques", ["PT 2"]) == "PT 3"
    with pytest.raises(composants.ComposantError):
        composants.code_suivant("inconnue", [])


def test_resultat_d_une_paroi_d_une_menuiserie_et_d_un_brouillon():
    from thermique_moteur.bibliotheque.materiaux import index_materiaux

    mur = composants.evaluer("murs", MUR_BETON, index_materiaux())
    assert mur["grandeur"] == "Up" and mur["valeur"] == 0.36
    assert mur["epaisseur_m"] == pytest.approx(0.313) and mur["epaisseur_complete"]
    assert mur["resume"].endswith("20 cm") and " + " in mur["resume"]
    fenetre = composants.evaluer("menuiseries", {"uw": 1.3, "sw": 0.42, "tlw": 0.6})
    assert (fenetre["valeur"], fenetre["sw"]) == (1.3, 0.42)
    assert composants.evaluer("murs", {"couches": []})["valeur"] is None  # brouillon enregistrable
    with pytest.raises(composants.ComposantError, match="Sw"):
        composants.evaluer("menuiseries", {"uw": 1.3, "sw": 1.4})
    with pytest.raises(composants.ComposantError, match="matériau inconnu"):
        composants.evaluer("murs", {"couches": [{"type": "materiau", "materiau_id": "zzz", "epaisseur_m": 0.1}]}, {})


# --- Bibliothèque de projet et modèles --------------------------------------------------------


def test_bibliotheque_de_projet_et_modeles(db_session):
    thermicien = _user(db_session, "be@example.fr")
    projet_a = create_project(db_session, thermicien, "Groupe scolaire", None)
    projet_b = create_project(db_session, thermicien, "Logements", None)

    mur = create_component(db_session, thermicien, projet_a, {"categorie": "murs", "nom": "Mur extérieur ITI", "composition": MUR_BETON})
    assert (mur.code, serialize_component(mur)["resultat"]["valeur"]) == ("MUR 1", 0.36)
    brouillon = create_component(db_session, thermicien, projet_a, {"categorie": "murs"})
    assert (brouillon.code, brouillon.name) == ("MUR 2", "Nouveau mur")
    with pytest.raises(ThermiqueError, match="déjà utilisé"):
        update_component(db_session, thermicien, brouillon, {"code": "MUR 1"})

    # « Enregistrer comme modèle » puis import dans un autre projet : copies indépendantes.
    modele = copy_component(db_session, thermicien, mur, None)
    assert modele.project_id is None and modele.source_component_id == mur.id
    importe = copy_component(db_session, thermicien, modele, projet_b)
    assert (importe.project_id, importe.code, importe.name) == (projet_b.id, "MUR 1", "Mur extérieur ITI")
    plus_isole = {**MUR_BETON, "couches": [*MUR_BETON["couches"][:1], {**MUR_BETON["couches"][1], "epaisseur_m": 0.16}, MUR_BETON["couches"][2]]}
    update_component(db_session, thermicien, modele, {"composition": plus_isole, "statut": "conforme_cctp"})
    assert serialize_component(modele)["resultat"]["valeur"] < 0.36
    db_session.refresh(importe)
    assert serialize_component(importe)["resultat"]["valeur"] == 0.36  # le projet B n'a pas bougé

    copie = copy_component(db_session, thermicien, mur, projet_a, suffix=" (copie)")
    assert (copie.code, copie.name) == ("MUR 3", "Mur extérieur ITI (copie)")
    assert [c.code for c in list_components(db_session, thermicien, projet_a)] == ["MUR 1", "MUR 2", "MUR 3"]
    assert [c.id for c in list_components(db_session, thermicien, None)] == [modele.id]


def test_composants_isoles_entre_comptes(db_session):
    thermicien = _user(db_session, "be@example.fr")
    autre = _user(db_session, "autre@example.fr")
    projet = create_project(db_session, thermicien, "Projet", None)
    composant = create_component(db_session, thermicien, projet, {"categorie": "ponts_thermiques", "composition": {"psi": 0.45}})
    modele = copy_component(db_session, thermicien, composant, None)
    assert get_component_for_user(db_session, thermicien, composant.id) is composant
    assert get_component_for_user(db_session, autre, composant.id) is None
    assert get_component_for_user(db_session, autre, modele.id) is None
    assert list_components(db_session, autre, None) == []
