"""File des niveaux à analyser, vidée par le relais qui tourne sur le poste du thermicien (D92 à D95).

Le serveur ne peut pas lancer les agents Claude Code : ils tournent sur le poste, avec l'abonnement de
l'utilisateur. Il tient donc une file, et se contente de la distribuer dans le bon ordre. Toute la logique
qui protège le travail déjà fait est ici, pas dans le relais : un programme sur le poste est plus facile à
contourner qu'une règle de serveur.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.thermique import (
    ThermiqueEtude,
    ThermiqueEtudeVersion,
    ThermiqueProject,
    ThermiqueSheet,
    ThermiqueTravail,
)
from app.models.user import User
from app.services.thermique import ThermiqueError

# Statuts d'un travail. `en_attente` et `en_cours` sont vivants ; les trois autres sont des fins de course.
VIVANTS = ("en_attente", "en_cours")
TERMINES = ("fini", "refuse", "echec")

# Un libellé que l'on ne sait pas classer passe après tous les niveaux connus, plutôt que de bloquer la
# file : la toiture est à 99, on se range juste derrière.
RANG_INCONNU = 999


def rang_du_niveau(label: str | None) -> int | None:
    """Rang d'un niveau d'après son libellé : sous-sols négatifs, RDC à 0, étages positifs, toiture en fin.

    Portage de `levels.ts:levelRank`, côté serveur : l'ordre de la file doit être celui que le thermicien
    voit dans l'interface, et le catalogue monte du bas vers le haut (D95).
    """
    if not label:
        return None
    sans_accent = unicodedata.normalize("NFD", label.lower())
    texte = re.sub(r"\s+", " ", "".join(c for c in sans_accent if unicodedata.category(c) != "Mn")).strip()
    if re.search(r"toit|terrasse|couverture", texte):
        return 99
    if re.search(r"\brdc\b|rez|\br ?0\b|niveau ?0\b|\bn ?0\b", texte):
        return 0
    sous_sol = re.search(r"sous[- ]?sol ?(\d*)|\bss ?(\d*)\b|\br ?- ?(\d+)|niveau ?- ?(\d+)|\bn ?- ?(\d+)", texte)
    if sous_sol:
        chiffres = next((g for g in sous_sol.groups() if g), "")
        return -int(chiffres or 1)
    etage = re.search(r"\br ?\+ ?(\d+)|niveau ?\+? ?(\d+)|\bn ?\+? ?(\d+)\b|etage ?(\d+)|(\d+)(?:er|e|eme) etage", texte)
    if etage:
        return int(next(g for g in etage.groups() if g))
    return None


def _travail_vivant(db: Session, sheet_id: int) -> ThermiqueTravail | None:
    return db.scalar(
        select(ThermiqueTravail)
        .where(ThermiqueTravail.sheet_id == sheet_id, ThermiqueTravail.statut.in_(VIVANTS))
        .order_by(ThermiqueTravail.id.desc())
    )


def travail_humain(db: Session, sheet_id: int) -> str | None:
    """Ce que le thermicien a déjà fait sur ce niveau, en clair, ou `None` s'il n'y a pas touché (D94).

    Deux traces suffisent et existent déjà : un local passé à « validé », ou un enregistrement de
    retouches. Aucune donnée nouvelle n'est nécessaire.
    """
    etude = db.scalar(select(ThermiqueEtude).where(ThermiqueEtude.sheet_id == sheet_id))
    if etude is None:
        return None
    try:
        etats = json.loads(etude.local_states_json)
    except (TypeError, ValueError):
        etats = {}
    valides = sum(1 for etat in etats.values() if isinstance(etat, dict) and etat.get("status") == "valide")
    if valides:
        return f"{valides} local{'aux' if valides > 1 else ''} déjà validé{'s' if valides > 1 else ''}"
    retouches = db.scalar(
        select(func.count())
        .select_from(ThermiqueEtudeVersion)
        .where(ThermiqueEtudeVersion.etude_id == etude.id, ThermiqueEtudeVersion.reason != "import")
    )
    if retouches:
        return f"{retouches} enregistrement{'s' if retouches > 1 else ''} de retouches"
    return None


def motif_d_exclusion(db: Session, sheet: ThermiqueSheet) -> str | None:
    """Pourquoi ce niveau ne peut pas partir en analyse, en clair, ou `None` s'il est éligible (D94)."""
    if sheet.nature != "plan":
        return "ce n'est pas un plan de niveau"
    if sheet.scale_denominator is None:
        return "l'échelle n'est pas définie"
    if _travail_vivant(db, sheet.id) is not None:
        return "déjà dans la file"
    fait = travail_humain(db, sheet.id)
    if fait:
        return f"{fait} : l'analyse écraserait votre travail"
    return None


def mettre_en_file(db: Session, project: ThermiqueProject, user: User) -> dict[str, list[dict[str, Any]]]:
    """Met en file tous les niveaux éligibles du projet, et dit ce qui a été écarté et pourquoi (D93)."""
    planches = db.scalars(
        select(ThermiqueSheet).where(ThermiqueSheet.project_id == project.id).order_by(ThermiqueSheet.id)
    ).all()
    ajoutes: list[ThermiqueTravail] = []
    ecartes: list[dict[str, Any]] = []
    for sheet in planches:
        motif = motif_d_exclusion(db, sheet)
        if motif:
            ecartes.append({"sheet_id": sheet.id, "label": sheet.label, "motif": motif})
            continue
        rang = rang_du_niveau(sheet.level_label)
        travail = ThermiqueTravail(
            project_id=project.id,
            sheet_id=sheet.id,
            statut="en_attente",
            rang=RANG_INCONNU if rang is None else rang,
            demande_par_user_id=user.id,
        )
        db.add(travail)
        ajoutes.append(travail)
    db.commit()
    for travail in ajoutes:
        db.refresh(travail)
    return {"ajoutes": [serialize_travail(db, t) for t in ajoutes], "ecartes": ecartes}


def travaux_du_projet(db: Session, project_id: int) -> list[ThermiqueTravail]:
    return list(
        db.scalars(
            select(ThermiqueTravail)
            .where(ThermiqueTravail.project_id == project_id)
            .order_by(ThermiqueTravail.rang, ThermiqueTravail.id)
        ).all()
    )


def file_du_relais(db: Session, user: User) -> list[ThermiqueTravail]:
    """Ce que le relais doit faire, tous projets du thermicien confondus, dans l'ordre des niveaux (D95)."""
    return list(
        db.scalars(
            select(ThermiqueTravail)
            .join(ThermiqueProject, ThermiqueProject.id == ThermiqueTravail.project_id)
            .where(ThermiqueProject.owner_user_id == user.id, ThermiqueTravail.statut.in_(VIVANTS))
            .order_by(ThermiqueTravail.project_id, ThermiqueTravail.rang, ThermiqueTravail.id)
        ).all()
    )


def prendre(db: Session, travail: ThermiqueTravail) -> ThermiqueTravail:
    """Le relais s'attribue un travail. Un travail déjà pris n'est jamais redonné en silence."""
    if travail.statut != "en_attente":
        raise ThermiqueError(f"Ce travail n'est pas en attente (état : {travail.statut}).")
    travail.statut = "en_cours"
    travail.pris_a = datetime.now(timezone.utc)
    travail.message = None
    db.commit()
    db.refresh(travail)
    return travail


def _clore(db: Session, travail: ThermiqueTravail, statut: str, message: str | None) -> ThermiqueTravail:
    travail.statut = statut
    travail.message = message
    travail.fini_a = datetime.now(timezone.utc)
    db.commit()
    db.refresh(travail)
    return travail


def terminer(db: Session, travail: ThermiqueTravail) -> ThermiqueTravail:
    return _clore(db, travail, "fini", None)


def echouer(db: Session, travail: ThermiqueTravail, message: str) -> ThermiqueTravail:
    """Un échec de chaîne : pas de réessai automatique (Q5), le message dit ce qu'il faut corriger."""
    return _clore(db, travail, "echec", message)


def remettre_en_attente(db: Session, travail: ThermiqueTravail, message: str) -> ThermiqueTravail:
    """La chaîne attend une intervention, ou la session Claude a expiré (D98) : le travail reste à faire.

    Le relais passe au suivant et ne bloque pas la file sur ce niveau.
    """
    travail.statut = "en_attente"
    travail.pris_a = None
    travail.message = message
    db.commit()
    db.refresh(travail)
    return travail


def serialize_travail(db: Session, travail: ThermiqueTravail) -> dict[str, Any]:
    sheet = db.get(ThermiqueSheet, travail.sheet_id)
    return {
        "id": travail.id,
        "project_id": travail.project_id,
        "sheet_id": travail.sheet_id,
        "label": sheet.label if sheet else "",
        "level_label": sheet.level_label if sheet else None,
        "statut": travail.statut,
        "rang": travail.rang,
        "message": travail.message,
        "pris_a": travail.pris_a,
        "fini_a": travail.fini_a,
        "created_at": travail.created_at,
    }


def consignes_du_travail(db: Session, travail: ThermiqueTravail) -> dict[str, Any]:
    """Tout ce dont `run_etude_niveau.py` a besoin pour ce niveau, pris sur la planche.

    La rotation attendue par la chaîne est l'inverse de celle de la visionneuse : c'est la règle déjà
    documentée dans l'aide de la commande, et le relais ne doit pas avoir à la connaître.
    """
    sheet = db.get(ThermiqueSheet, travail.sheet_id)
    if sheet is None:
        raise ThermiqueError("La planche de ce travail n'existe plus.")
    return {
        "travail_id": travail.id,
        "sheet_id": sheet.id,
        "project_id": sheet.project_id,
        "document_id": sheet.document_id,
        "niveau": sheet.level_label or sheet.label,
        "page": sheet.page_index + 1,
        "rotation": (360 - int(sheet.rotation_deg)) % 360,
        "echelle": sheet.scale_denominator,
    }
