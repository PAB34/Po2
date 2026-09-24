"""File d'analyse et relais local (F0, D92 à D98).

Ce qui compte ici n'est pas la mécanique de la file, c'est le **garde-fou** : le relais tourne sur le
poste du thermicien et on ne veut en aucun cas qu'il écrase un niveau sur lequel celui-ci a travaillé.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.core.security import get_password_hash
from app.models.thermique import (
    ThermiqueDocument,
    ThermiqueEtude,
    ThermiqueEtudeVersion,
    ThermiqueProject,
    ThermiqueSheet,
)
from app.models.user import User
from app.services import thermique_travaux as travaux
from app.services.thermique import ThermiqueError


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _socle(db: Session) -> tuple[User, ThermiqueProject, ThermiqueDocument]:
    user = User(
        email="thermicien@bureau.fr",
        password_hash=get_password_hash("motdepasse-solide"),
        nom="Nom",
        prenom="Prenom",
        role="USER",
        is_active=True,
    )
    db.add(user)
    db.flush()
    projet = ThermiqueProject(owner_user_id=user.id, name="Médiathèque")
    db.add(projet)
    db.flush()
    document = ThermiqueDocument(
        project_id=projet.id,
        original_filename="plans.pdf",
        stored_filename="plans.pdf",
        file_format="pdf",
        size_bytes=1,
        sha256="x" * 64,
        page_count=4,
        uploaded_by_user_id=user.id,
    )
    db.add(document)
    db.commit()
    return user, projet, document


def _planche(
    db: Session,
    projet: ThermiqueProject,
    document: ThermiqueDocument,
    page: int,
    niveau: str | None,
    *,
    nature: str | None = "plan",
    echelle: float | None = 100,
) -> ThermiqueSheet:
    sheet = ThermiqueSheet(
        project_id=projet.id,
        document_id=document.id,
        page_index=page,
        label=niveau or f"page {page + 1}",
        nature=nature,
        level_label=niveau,
        scale_denominator=echelle,
        scale_source="declaree" if echelle else None,
        rotation_deg=270,
        page_width_pt=1191,
        page_height_pt=842,
    )
    db.add(sheet)
    db.commit()
    db.refresh(sheet)
    return sheet


def _etude(db: Session, sheet: ThermiqueSheet, etats: dict, *, retouches: int = 0) -> ThermiqueEtude:
    etude = ThermiqueEtude(
        project_id=sheet.project_id,
        sheet_id=sheet.id,
        format_version=3,
        content_json="{}",
        local_states_json=json.dumps(etats),
    )
    db.add(etude)
    db.flush()
    db.add(
        ThermiqueEtudeVersion(
            etude_id=etude.id, version_number=1, reason="import", local_states_json=etude.local_states_json
        )
    )
    for rang in range(retouches):
        db.add(
            ThermiqueEtudeVersion(
                etude_id=etude.id,
                version_number=2 + rang,
                reason="validation_local",
                local_states_json=etude.local_states_json,
            )
        )
    db.commit()
    return etude


# --- Ordre des niveaux ---------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "rang"),
    [
        ("Sous-sol", -1),
        ("SS2", -2),
        ("RDC", 0),
        ("Rez-de-chaussée", 0),
        ("R+1", 1),
        ("R + 12", 12),
        ("Niveau 3", 3),
        ("Toiture", 99),
        ("Terrasse technique", 99),
    ],
)
def test_les_niveaux_se_classent_du_bas_vers_le_haut(label, rang):
    """Le catalogue monte d'un niveau au suivant (D95) : l'ordre doit être celui du bâtiment."""
    assert travaux.rang_du_niveau(label) == rang


def test_un_libelle_illisible_ne_bloque_pas_la_file(db_session):
    """Il part en dernier plutôt que d'arrêter tout le projet (D95)."""
    assert travaux.rang_du_niveau("plan des réseaux") is None
    user, projet, document = _socle(db_session)
    _planche(db_session, projet, document, 0, "mezzanine nord")
    _planche(db_session, projet, document, 1, "RDC")

    resultat = travaux.mettre_en_file(db_session, projet, user)
    rangs = [t["rang"] for t in resultat["ajoutes"]]
    assert rangs == [travaux.RANG_INCONNU, 0]
    file = travaux.file_du_relais(db_session, user)
    assert [t.rang for t in file] == [0, travaux.RANG_INCONNU]


# --- Garde-fou : ne jamais écraser le travail du thermicien --------------------


def test_un_niveau_avec_des_locaux_valides_est_ecarte_avec_son_motif(db_session):
    user, projet, document = _socle(db_session)
    sheet = _planche(db_session, projet, document, 0, "R+1")
    _etude(db_session, sheet, {"p1": {"status": "valide"}, "p2": {"status": "a_verifier"}})

    resultat = travaux.mettre_en_file(db_session, projet, user)
    assert resultat["ajoutes"] == []
    assert "1 local déjà validé" in resultat["ecartes"][0]["motif"]
    assert "écraserait votre travail" in resultat["ecartes"][0]["motif"]


def test_un_niveau_retouche_mais_sans_local_valide_est_ecarte_aussi(db_session):
    """Reprendre un contour sans valider reste du travail humain : on ne l'écrase pas non plus."""
    user, projet, document = _socle(db_session)
    sheet = _planche(db_session, projet, document, 0, "R+1")
    _etude(db_session, sheet, {"p1": {"status": "a_verifier"}}, retouches=2)

    resultat = travaux.mettre_en_file(db_session, projet, user)
    assert resultat["ajoutes"] == []
    assert "2 enregistrements de retouches" in resultat["ecartes"][0]["motif"]


def test_une_etude_importee_mais_jamais_touchee_se_reanalyse_sans_rien_demander(db_session):
    """Réponse Q4 : l'ancienne étude reste en version, donc rien n'est perdu."""
    user, projet, document = _socle(db_session)
    sheet = _planche(db_session, projet, document, 0, "R+1")
    _etude(db_session, sheet, {"p1": {"status": "a_verifier"}})

    resultat = travaux.mettre_en_file(db_session, projet, user)
    assert [t["sheet_id"] for t in resultat["ajoutes"]] == [sheet.id]
    assert resultat["ecartes"] == []


@pytest.mark.parametrize(
    ("nature", "echelle", "motif"),
    [
        ("coupe", 100, "ce n'est pas un plan de niveau"),
        (None, 100, "ce n'est pas un plan de niveau"),
        ("plan", None, "l'échelle n'est pas définie"),
    ],
)
def test_une_planche_non_prete_est_ecartee(db_session, nature, echelle, motif):
    user, projet, document = _socle(db_session)
    _planche(db_session, projet, document, 0, "R+1", nature=nature, echelle=echelle)

    resultat = travaux.mettre_en_file(db_session, projet, user)
    assert resultat["ajoutes"] == []
    assert resultat["ecartes"][0]["motif"] == motif


def test_demander_deux_fois_ne_met_pas_le_niveau_deux_fois(db_session):
    """Un double clic sur « Analyser » ne doit pas faire travailler les agents deux fois."""
    user, projet, document = _socle(db_session)
    _planche(db_session, projet, document, 0, "R+1")

    assert len(travaux.mettre_en_file(db_session, projet, user)["ajoutes"]) == 1
    second = travaux.mettre_en_file(db_session, projet, user)
    assert second["ajoutes"] == []
    assert second["ecartes"][0]["motif"] == "déjà dans la file"
    assert len(travaux.file_du_relais(db_session, user)) == 1


# --- Cycle de vie d'un travail -------------------------------------------------


def test_un_travail_pris_porte_les_consignes_de_la_chaine(db_session):
    user, projet, document = _socle(db_session)
    sheet = _planche(db_session, projet, document, 2, "R+1")
    travaux.mettre_en_file(db_session, projet, user)
    travail = travaux.file_du_relais(db_session, user)[0]

    travaux.prendre(db_session, travail)
    consignes = travaux.consignes_du_travail(db_session, travail)
    assert travail.statut == "en_cours"
    assert travail.pris_a is not None
    # La visionneuse affiche à 270° ; la chaîne attend la rotation inverse.
    assert consignes["rotation"] == 90
    assert consignes["page"] == 3
    assert consignes["niveau"] == "R+1"
    assert consignes["echelle"] == 100


def test_un_travail_deja_pris_n_est_pas_redonne(db_session):
    user, projet, document = _socle(db_session)
    _planche(db_session, projet, document, 0, "R+1")
    travaux.mettre_en_file(db_session, projet, user)
    travail = travaux.file_du_relais(db_session, user)[0]
    travaux.prendre(db_session, travail)

    with pytest.raises(ThermiqueError, match="en attente"):
        travaux.prendre(db_session, travail)


def test_une_session_claude_expiree_remet_le_niveau_a_faire(db_session):
    """D98 : ce n'est pas un échec d'analyse, le niveau reste à traiter et la file continue."""
    user, projet, document = _socle(db_session)
    _planche(db_session, projet, document, 0, "R+1")
    travaux.mettre_en_file(db_session, projet, user)
    travail = travaux.file_du_relais(db_session, user)[0]
    travaux.prendre(db_session, travail)

    travaux.remettre_en_attente(db_session, travail, "session Claude expirée : claude auth login")
    assert travail.statut == "en_attente"
    assert travail.pris_a is None
    assert travaux.file_du_relais(db_session, user)[0].id == travail.id


def test_un_echec_sort_de_la_file_avec_son_message(db_session):
    """Q5 : pas de réessai automatique, l'échec vient presque toujours d'une donnée à corriger."""
    user, projet, document = _socle(db_session)
    _planche(db_session, projet, document, 0, "R+1")
    travaux.mettre_en_file(db_session, projet, user)
    travail = travaux.file_du_relais(db_session, user)[0]
    travaux.prendre(db_session, travail)

    travaux.echouer(db_session, travail, "plan illisible au-delà de la passe globale")
    assert travail.statut == "echec"
    assert travail.fini_a is not None
    assert travaux.file_du_relais(db_session, user) == []


def test_la_file_d_un_thermicien_ne_montre_pas_les_projets_d_un_autre(db_session):
    user, projet, document = _socle(db_session)
    _planche(db_session, projet, document, 0, "R+1")
    travaux.mettre_en_file(db_session, projet, user)

    autre = User(
        email="autre@bureau.fr",
        password_hash=get_password_hash("motdepasse-solide"),
        nom="Nom",
        prenom="Prenom",
        role="USER",
        is_active=True,
    )
    db_session.add(autre)
    db_session.commit()
    assert travaux.file_du_relais(db_session, autre) == []
