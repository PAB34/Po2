"""Bibliothèque de projet et modèles réutilisables de l'outil thermique (lot L1).

Un composant appartient à un projet ou aux modèles d'un compte (`project_id` vide). Importer un
modèle dans un projet, dupliquer ou « enregistrer comme modèle » crée une copie indépendante
(décision BP-D2). Le résultat est recalculé à chaque enregistrement avec les éditions du
référentiel Th-Bât (BP-D3). Voir docs/thermique/bibliotheque-projet-decisions.md.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.thermique import ThermiqueComponent, ThermiqueProject
from app.models.user import User
from app.services.thermique import ThermiqueError, get_project_for_user
from thermique_moteur import composants as moteur
from thermique_moteur.bibliotheque import elements as bibliotheque_elements
from thermique_moteur.bibliotheque import materiaux as bibliotheque_materiaux


def _referentiel() -> tuple[dict, dict, dict[str, str]]:
    editions = {
        "materiaux": bibliotheque_materiaux.charger_edition()["edition"],
        "elements": bibliotheque_elements.charger_edition()["edition"],
    }
    return bibliotheque_materiaux.index_materiaux(), bibliotheque_elements.index_elements(), editions


def evaluate(category: str, composition: dict[str, Any]) -> dict[str, Any]:
    materiaux, elements, _ = _referentiel()
    try:
        return moteur.evaluer(category, composition, materiaux, elements)
    except moteur.ComposantError as exc:
        raise ThermiqueError(str(exc)) from exc


def _store_result(component: ThermiqueComponent, composition: dict[str, Any]) -> None:
    materiaux, elements, editions = _referentiel()
    try:
        result = moteur.evaluer(component.category, composition, materiaux, elements)
    except moteur.ComposantError as exc:
        raise ThermiqueError(str(exc)) from exc
    component.composition_json = json.dumps(composition, ensure_ascii=False)
    component.result_json = json.dumps(result, ensure_ascii=False)
    component.reference_json = json.dumps(editions)


def _scope_filter(user: User, project: ThermiqueProject | None):
    if project is not None:
        return ThermiqueComponent.project_id == project.id
    return (ThermiqueComponent.owner_user_id == user.id) & ThermiqueComponent.project_id.is_(None)


def list_components(db: Session, user: User, project: ThermiqueProject | None) -> list[ThermiqueComponent]:
    """Composants d'un projet, ou modèles du compte quand `project` vaut None."""
    statement = select(ThermiqueComponent).where(_scope_filter(user, project)).order_by(ThermiqueComponent.id)
    return list(db.scalars(statement))


def get_component_for_user(db: Session, user: User, component_id: int) -> ThermiqueComponent | None:
    component = db.get(ThermiqueComponent, component_id)
    if component is None:
        return None
    if component.project_id is not None:
        return component if get_project_for_user(db, user, component.project_id) else None
    return component if component.owner_user_id == user.id else None


def _codes(db: Session, user: User, project: ThermiqueProject | None, sauf: int | None = None) -> list[str]:
    return [c.code for c in list_components(db, user, project) if c.id != sauf]


def _status(value: str | None) -> str:
    status = value or "hypothese"
    if status not in moteur.STATUTS:
        raise ThermiqueError("Statut inconnu (hypothèse ou conforme CCTP).")
    return status


def create_component(db: Session, user: User, project: ThermiqueProject | None, data: dict[str, Any]) -> ThermiqueComponent:
    try:
        category = moteur.categorie(data.get("categorie"))
    except moteur.ComposantError as exc:
        raise ThermiqueError(str(exc)) from exc
    codes = _codes(db, user, project)
    code = (data.get("code") or "").strip()[:20] or moteur.code_suivant(category["id"], codes)
    if code in codes:
        raise ThermiqueError(f"Le code « {code} » est déjà utilisé.")
    component = ThermiqueComponent(
        owner_user_id=project.owner_user_id if project is not None else user.id,
        project_id=project.id if project is not None else None,
        category=category["id"],
        code=code,
        name=(data.get("nom") or "").strip()[:200] or category["nouveau"],
        status=_status(data.get("statut")),
        notes=(data.get("notes") or "").strip() or None,
        source_component_id=data.get("source_component_id"),
    )
    _store_result(component, data.get("composition") or moteur.composition_par_defaut(category["id"]))
    db.add(component)
    db.commit()
    db.refresh(component)
    return component


def update_component(db: Session, user: User, component: ThermiqueComponent, changes: dict[str, Any]) -> ThermiqueComponent:
    if changes.get("code") is not None:
        code = changes["code"].strip()[:20]
        if not code:
            raise ThermiqueError("Le code est obligatoire.")
        project = db.get(ThermiqueProject, component.project_id) if component.project_id else None
        if code in _codes(db, user, project, sauf=component.id):
            raise ThermiqueError(f"Le code « {code} » est déjà utilisé.")
        component.code = code
    if changes.get("nom") is not None:
        name = changes["nom"].strip()[:200]
        if not name:
            raise ThermiqueError("Le nom est obligatoire.")
        component.name = name
    if "statut" in changes:
        component.status = _status(changes["statut"])
    if "notes" in changes:
        component.notes = (changes["notes"] or "").strip() or None
    if changes.get("composition") is not None:
        _store_result(component, changes["composition"])
    db.commit()
    db.refresh(component)
    return component


def copy_component(
    db: Session, user: User, component: ThermiqueComponent, project: ThermiqueProject | None, suffix: str = ""
) -> ThermiqueComponent:
    """Copie indépendante vers un projet ou vers les modèles ; le code est gardé s'il est libre."""
    codes = _codes(db, user, project)
    code = component.code if component.code not in codes else moteur.code_suivant(component.category, codes)
    return create_component(
        db,
        user,
        project,
        {
            "categorie": component.category,
            "code": code,
            "nom": f"{component.name}{suffix}",
            "statut": component.status,
            "notes": component.notes,
            "composition": json.loads(component.composition_json),
            "source_component_id": component.id,
        },
    )


def delete_component(db: Session, component: ThermiqueComponent) -> None:
    db.delete(component)
    db.commit()


def serialize_component(component: ThermiqueComponent) -> dict[str, Any]:
    return {
        "id": component.id,
        "project_id": component.project_id,
        "categorie": component.category,
        "code": component.code,
        "nom": component.name,
        "statut": component.status,
        "composition": json.loads(component.composition_json),
        "resultat": json.loads(component.result_json) if component.result_json else None,
        "referentiel": json.loads(component.reference_json) if component.reference_json else None,
        "notes": component.notes,
        "source_component_id": component.source_component_id,
        "created_at": component.created_at.isoformat() if component.created_at else None,
        "updated_at": component.updated_at.isoformat() if component.updated_at else None,
    }
