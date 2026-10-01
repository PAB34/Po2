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
    ThermiqueVue,
)
from app.models.user import User
from app.services.thermique import ThermiqueError
from app.services.thermique_etudes import MOTIFS_D_IMPORT
from app.services.thermique_lecture_coupes import vue_a_relire, vues_a_relire

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


# Types de travail (S5, D181). Les lectures de coupes passent après tous les niveaux.
# « vues » : relire les seules vues dont le thermicien a corrigé le cadre ou le haut (D205).
NIVEAU, TRAITS, COUPES, VUES = "niveau", "traits", "coupes", "vues"
TYPES = (NIVEAU, TRAITS, COUPES, VUES)
RANG_TRAITS = 1000
RANG_COUPES = 1001
RANG_VUES = 1002


def _travail_vivant(db: Session, sheet_id: int, type_travail: str = NIVEAU) -> ThermiqueTravail | None:
    return db.scalar(
        select(ThermiqueTravail)
        .where(
            ThermiqueTravail.sheet_id == sheet_id,
            ThermiqueTravail.statut.in_(VIVANTS),
            ThermiqueTravail.type == type_travail,
        )
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
    # Tout motif qui n'est pas celui d'un import est une retouche : le libellé exact vient de
    # `thermique_etudes`, pour que les deux ne puissent pas diverger en silence.
    retouches = db.scalar(
        select(func.count())
        .select_from(ThermiqueEtudeVersion)
        .where(
            ThermiqueEtudeVersion.etude_id == etude.id,
            ThermiqueEtudeVersion.reason.notin_(MOTIFS_D_IMPORT),
        )
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


def _lectures_de_coupes(db: Session, sheet: ThermiqueSheet, avec_coupes: bool) -> list[tuple[str, int]]:
    """Les lectures de coupes à demander pour cette planche (D181), sans jamais en doubler une en file.

    Une planche de coupes ou de façades est lue en entier ; un plan voit ses traits de coupe relevés dès
    que le projet a des coupes. Une lecture n'écrase que des données d'agent : pas de garde-fou D94.
    """
    if sheet.scale_denominator is None:
        return []
    if sheet.nature in ("coupe", "facade"):
        # Une planche déjà lue n'est pas relue en entier : ce serait effacer les cadres corrigés à la main
        # (D205). Seules ses vues marquées « à relire » repartent.
        if db.scalar(select(func.count()).select_from(ThermiqueVue).where(ThermiqueVue.sheet_id == sheet.id)):
            if vues_a_relire(db, sheet.id) and not _travail_vivant(db, sheet.id, VUES):
                return [(VUES, RANG_VUES)]
            return []
        return [] if _travail_vivant(db, sheet.id, COUPES) else [(COUPES, RANG_COUPES)]
    if sheet.nature == "plan" and avec_coupes and not sheet.traits_coupe_json:
        return [] if _travail_vivant(db, sheet.id, TRAITS) else [(TRAITS, RANG_TRAITS)]
    return []


def mettre_en_file(db: Session, project: ThermiqueProject, user: User) -> dict[str, list[dict[str, Any]]]:
    """Met en file tous les niveaux éligibles du projet, et dit ce qui a été écarté et pourquoi (D93).

    Les planches de coupes et de façades, et les traits de coupe des plans, suivent les niveaux (D181).
    """
    planches = db.scalars(
        select(ThermiqueSheet).where(ThermiqueSheet.project_id == project.id).order_by(ThermiqueSheet.id)
    ).all()
    avec_coupes = any(p.nature == "coupe" for p in planches)
    ajoutes: list[ThermiqueTravail] = []
    ecartes: list[dict[str, Any]] = []

    def ajouter(sheet: ThermiqueSheet, type_travail: str, rang: int) -> None:
        travail = ThermiqueTravail(
            project_id=project.id,
            sheet_id=sheet.id,
            statut="en_attente",
            type=type_travail,
            rang=rang,
            demande_par_user_id=user.id,
        )
        db.add(travail)
        ajoutes.append(travail)

    for sheet in planches:
        lectures = _lectures_de_coupes(db, sheet, avec_coupes)
        for type_travail, rang in lectures:
            ajouter(sheet, type_travail, rang)
        if sheet.nature in ("coupe", "facade"):
            if not lectures:
                if sheet.scale_denominator is None:
                    motif = "l'échelle n'est pas définie"
                elif _travail_vivant(db, sheet.id, COUPES) or _travail_vivant(db, sheet.id, VUES):
                    motif = "déjà dans la file"
                else:
                    motif = "déjà lue : vérifiez ses vues, puis « Faire lire par l'IA » vue par vue"
                ecartes.append({"sheet_id": sheet.id, "label": sheet.label, "motif": motif})
            continue
        motif = motif_d_exclusion(db, sheet)
        if motif:
            ecartes.append({"sheet_id": sheet.id, "label": sheet.label, "motif": motif})
            continue
        rang = rang_du_niveau(sheet.level_label)
        ajouter(sheet, NIVEAU, RANG_INCONNU if rang is None else rang)
    db.commit()
    for travail in ajoutes:
        db.refresh(travail)
    return {"ajoutes": [serialize_travail(db, t) for t in ajoutes], "ecartes": ecartes}


def mettre_en_file_la_relecture(db: Session, sheet: ThermiqueSheet, user: User) -> ThermiqueTravail | None:
    """Après une correction de cadre (D205) : la relecture des vues de la planche part dans la file."""
    vivant = _travail_vivant(db, sheet.id, VUES)
    if vivant is not None or not vues_a_relire(db, sheet.id):
        return vivant
    travail = ThermiqueTravail(
        project_id=sheet.project_id, sheet_id=sheet.id, statut="en_attente", type=VUES, rang=RANG_VUES,
        demande_par_user_id=user.id,
    )
    db.add(travail)
    db.commit()
    db.refresh(travail)
    return travail


def travaux_du_projet(db: Session, project_id: int) -> list[ThermiqueTravail]:
    return list(
        db.scalars(
            select(ThermiqueTravail)
            .where(ThermiqueTravail.project_id == project_id)
            .order_by(ThermiqueTravail.rang, ThermiqueTravail.id)
        ).all()
    )


def file_du_relais(db: Session, user: User, types: tuple[str, ...] = (NIVEAU,)) -> list[ThermiqueTravail]:
    """Ce que le relais doit faire, tous projets du thermicien confondus, dans l'ordre des niveaux (D95).

    Un relais ne reçoit que les types de travail qu'il annonce savoir faire : un ancien relais, qui ne
    connaît que l'étude d'un niveau, lancerait sinon cette étude sur une planche de coupes.
    """
    return list(
        db.scalars(
            select(ThermiqueTravail)
            .join(ThermiqueProject, ThermiqueProject.id == ThermiqueTravail.project_id)
            .where(
                ThermiqueProject.owner_user_id == user.id,
                ThermiqueTravail.statut.in_(VIVANTS),
                ThermiqueTravail.type.in_(types),
            )
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


def clore_si_en_file(db: Session, sheet_id: int, type_travail: str) -> None:
    """Une analyse importée à la main (D204) vaut le travail en attente : le relais ne la refera pas.

    Un travail déjà pris par le relais reste à lui : il rendra sa propre lecture, qui remplacera celle-ci.
    """
    travail = _travail_vivant(db, sheet_id, type_travail)
    if travail is not None and travail.statut == "en_attente":
        _clore(db, travail, "fini", "Importé à la main depuis la fiche de la planche.")


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
        "type": travail.type or NIVEAU,
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
        "type": travail.type or NIVEAU,
        "sheet_id": sheet.id,
        "label": sheet.label,
        "nature": sheet.nature,
        "project_id": sheet.project_id,
        "document_id": sheet.document_id,
        "niveau": sheet.level_label or sheet.label,
        "page": sheet.page_index + 1,
        "rotation": (360 - int(sheet.rotation_deg)) % 360,
        "echelle": sheet.scale_denominator,
        # Relecture (D205) : les vues à relire, avec le cadre et le haut donnés par le thermicien.
        **({"vues": [vue_a_relire(v) for v in vues_a_relire(db, sheet.id)]} if travail.type == VUES else {}),
    }
