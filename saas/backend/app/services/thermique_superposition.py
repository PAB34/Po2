"""Superposition des niveaux — étape E2 (docs/thermique/refondation-parcours-decisions.md §12, D24 à D27).

Le thermicien choisit un niveau de référence (RDC par défaut) ; pour chaque autre plan, le moteur propose la
translation qui le pose sur la référence ; il vérifie en transparence, corrige en glissant, puis valide.

Une superposition validée est enregistrée comme **calage** du niveau de la planche (`ThermiqueLevel.calage_json`),
le repère commun déjà utilisé par le métré : la référence a pour points A (0, 0) et B (100, 0) ; un niveau décalé
de (dx, dy) a pour points A (−dx, −dy) et B (100 − dx, −dy). Un plan sans niveau (toiture, sous-sol) en reçoit un.
"""
from __future__ import annotations

import json
from collections import OrderedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.thermique import ThermiqueLevel, ThermiqueProject, ThermiqueSheet
from app.services.thermique import ThermiqueError
from app.services.thermique_calques import plan_sheets, sheet_elements
from thermique_moteur import superposition as moteur
from thermique_moteur.metre import ordre_niveau

SOURCE = "superposition"
LONGUEUR_AB_PT = 100.0
DECALAGE_MAX_PT = 5000
MEMOIRE_MAX = 16
_propositions: OrderedDict[tuple, dict] = OrderedDict()


def _calage(level: ThermiqueLevel | None) -> dict | None:
    if level is None or not level.calage_json:
        return None
    try:
        calage = json.loads(level.calage_json)
    except ValueError:
        return None
    return calage if isinstance(calage, dict) else None


def _levels_by_sheet(db: Session, project: ThermiqueProject) -> dict[int, ThermiqueLevel]:
    levels = db.scalars(
        select(ThermiqueLevel).where(ThermiqueLevel.project_id == project.id).order_by(ThermiqueLevel.position, ThermiqueLevel.id)
    )
    resultat: dict[int, ThermiqueLevel] = {}
    for level in levels:
        if level.sheet_id is not None:
            resultat.setdefault(level.sheet_id, level)
    return resultat


def _plan(db: Session, project: ThermiqueProject, sheet_id: int) -> ThermiqueSheet:
    sheet = next((s for s in plan_sheets(db, project) if s.id == sheet_id), None)
    if sheet is None:
        raise ThermiqueError("Planche de plan introuvable (vérifiez sa nature et son échelle).")
    return sheet


def _reference_id(sheets: list[ThermiqueSheet], levels: dict[int, ThermiqueLevel]) -> int | None:
    for sheet in sheets:
        calage = _calage(levels.get(sheet.id))
        if calage and calage.get("source") == SOURCE and calage.get("reference"):
            return sheet.id
    choix = next((s for s in sheets if ordre_niveau(s.level_label or s.label) == 0), None) or (sheets[0] if sheets else None)
    return choix.id if choix else None


def overview(db: Session, project: ThermiqueProject) -> dict:
    sheets = plan_sheets(db, project)
    levels = _levels_by_sheet(db, project)
    planches = []
    for sheet in sheets:
        level = levels.get(sheet.id)
        calage = _calage(level)
        valide = bool(calage and calage.get("source") == SOURCE)
        planches.append(
            {
                "id": sheet.id,
                "libelle": sheet.label,
                "niveau_id": level.id if level else None,
                "niveau": level.name if level else None,
                "valide": valide,
                "decalage": calage.get("decalage") if valide else None,
                # un calage A-B posé à la main dans « Métré » (rotation possible) : écrasé à la validation
                "cale_main": bool(calage) and not valide,
            }
        )
    return {"reference_id": _reference_id(sheets, levels), "planches": planches}


def _taille(*sheets: ThermiqueSheet) -> tuple[int, int]:
    largeur = int(max(s.page_width_pt for s in sheets)) + 1
    hauteur = int(max(s.page_height_pt for s in sheets)) + 1
    if max(largeur, hauteur) > moteur.TAILLE_MAX_PT:
        raise ThermiqueError("Planche trop grande pour la superposition automatique : calez-la en glissant.")
    return largeur, hauteur


def propose(db: Session, project: ThermiqueProject, sheet_id: int, reference_id: int) -> dict:
    """Translation proposée pour poser la planche sur la référence (gardée en mémoire tant que rien ne change)."""
    sheet = _plan(db, project, sheet_id)
    reference = _plan(db, project, reference_id)
    if sheet.id == reference.id:
        return {"dx": 0, "dy": 0, "score": 1.0, "score_zero": 1.0, "etat": "reference"}
    elements, elements_ref = sheet_elements(sheet), sheet_elements(reference)
    cle = (sheet.id, reference.id, sheet.scale_denominator, reference.scale_denominator, len(elements["elements"]), len(elements_ref["elements"]))
    if cle in _propositions:
        _propositions.move_to_end(cle)
        return _propositions[cle]
    largeur, hauteur = _taille(sheet, reference)
    resultat = moteur.recaler(moteur.image_traits(elements, largeur, hauteur), moteur.image_traits(elements_ref, largeur, hauteur))
    _propositions[cle] = resultat
    while len(_propositions) > MEMOIRE_MAX:
        _propositions.popitem(last=False)
    return resultat


def _level_for(db: Session, project: ThermiqueProject, sheet: ThermiqueSheet, levels: dict[int, ThermiqueLevel]) -> ThermiqueLevel:
    level = levels.get(sheet.id)
    if level is not None:
        return level
    existants = list(db.scalars(select(ThermiqueLevel).where(ThermiqueLevel.project_id == project.id)))
    rang = ordre_niveau(sheet.level_label or sheet.label)
    pris = {item.position for item in existants}
    if rang is None or rang in pris:
        rang = max(pris, default=-1) + 1
    level = ThermiqueLevel(project_id=project.id, name=(sheet.level_label or sheet.label)[:80], position=rang, sheet_id=sheet.id)
    db.add(level)
    db.flush()
    levels[sheet.id] = level
    return level


def _poser(level: ThermiqueLevel, dx: float, dy: float, reference: bool) -> None:
    level.calage_json = json.dumps(
        {
            "a": [round(-dx, 3), round(-dy, 3)],
            "b": [round(LONGUEUR_AB_PT - dx, 3), round(-dy, 3)],
            "source": SOURCE,
            "reference": reference,
            "decalage": [round(dx, 3), round(dy, 3)],
        },
        separators=(",", ":"),
    )


def validate(db: Session, project: ThermiqueProject, reference_id: int, sheet_id: int, dx: float, dy: float) -> dict:
    """Valide la superposition d'une planche sur la référence. Si la référence change, les superpositions déjà
    validées sont ramenées à la nouvelle référence (ou effacées si celle-ci n'était pas encore superposée)."""
    if max(abs(dx), abs(dy)) > DECALAGE_MAX_PT:
        raise ThermiqueError("Décalage trop grand : vérifiez la superposition.")
    sheets = plan_sheets(db, project)
    levels = _levels_by_sheet(db, project)
    reference = _plan(db, project, reference_id)
    sheet = _plan(db, project, sheet_id)
    ancienne = _reference_id(sheets, levels)
    valides = {
        s.id: _calage(levels[s.id])["decalage"]
        for s in sheets
        if s.id in levels and (_calage(levels[s.id]) or {}).get("source") == SOURCE
    }
    if ancienne != reference.id and valides:
        base = valides.get(reference.id)
        for autre_id, (ax, ay) in valides.items():
            if base is None:
                levels[autre_id].calage_json = None
            else:
                _poser(levels[autre_id], ax - base[0], ay - base[1], reference=False)
    _poser(_level_for(db, project, reference, levels), 0.0, 0.0, reference=True)
    if sheet.id != reference.id:
        _poser(_level_for(db, project, sheet, levels), dx, dy, reference=False)
    db.commit()
    return overview(db, project)


def reset(db: Session, project: ThermiqueProject, sheet_id: int) -> dict:
    """Annule la superposition validée d'une planche (la référence ne s'annule qu'en dernier)."""
    sheets = plan_sheets(db, project)
    levels = _levels_by_sheet(db, project)
    level = levels.get(_plan(db, project, sheet_id).id)
    calage = _calage(level)
    if not calage or calage.get("source") != SOURCE:
        raise ThermiqueError("Cette planche n'a pas de superposition validée.")
    if calage.get("reference") and any(
        (_calage(levels.get(s.id)) or {}).get("source") == SOURCE for s in sheets if s.id != sheet_id
    ):
        raise ThermiqueError("Annulez d'abord les superpositions des autres plans, ou choisissez une autre référence.")
    level.calage_json = None
    db.commit()
    return overview(db, project)
