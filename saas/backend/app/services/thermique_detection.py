"""« Tout détecter » : reconnaissance des objets d'un plan puis pièces, noms et enveloppe (docs/thermique/
refondation-parcours-decisions.md §18).

Enchaînement (tâche de fond, une planche à la fois) :

1. murs, portes, menuiseries, isolant (`thermique_moteur/reconnaissance.py`) ;
2. largeur d'ouverture choisie automatiquement ;
3. pièces, puis noms lus et pré-classement ;
4. nu intérieur et nu extérieur déduits des pièces chauffées ;
5. menuiseries classées extérieures (dans la bande) ou intérieures.

Rien de ce qui a été fait à la main n'est remplacé : les désignations d'éléments seuls marquées `source: auto`
sont seules effacées à chaque relance, une règle n'est créée que si la famille n'en a pas, et les lignes
corrigées à la main arrêtent l'étape 4.
"""
from __future__ import annotations

import json
import logging
import threading
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.thermique import ThermiqueLevel, ThermiqueProject, ThermiqueRoom, ThermiqueSheet
from app.services.thermique import ThermiqueError
from app.services.thermique_calques import (
    _ponctuels,
    _regles,
    attribution,
    plan_sheets,
    save_designation,
    set_elements,
    sheet_band,
    sheet_elements,
)
from app.services.thermique_enveloppe import LIMITES_ENVELOPPE, ecrire_lignes
from app.services.thermique_pieces import _limites, detect_rooms, read_names
from thermique_moteur import bande as moteur_bande
from thermique_moteur import calques as moteur_calques
from thermique_moteur import reconnaissance
from thermique_moteur.pieces import NATURES_LIMITES, PiecesError

LOG = logging.getLogger(__name__)
ETAPES = ("objets", "pieces", "noms", "enveloppe", "menuiseries")
_etats: dict[int, dict] = {}
_verrou = threading.Lock()


def etat(sheet: ThermiqueSheet) -> dict:
    with _verrou:
        return dict(_etats.get(sheet.id) or {"etape": None, "en_cours": False, "erreur": None, "resume": None})


def _etape(sheet_id: int, etape: str) -> None:
    with _verrou:
        _etats[sheet_id] = {**_etats.get(sheet_id, {}), "etape": etape, "en_cours": True, "erreur": None}


def _fin(sheet_id: int, resume: dict | None, erreur: str | None) -> None:
    with _verrou:
        _etats[sheet_id] = {"etape": None, "en_cours": False, "erreur": erreur, "resume": resume, "fini_a": time.time()}


def start(db: Session, project: ThermiqueProject, sheet: ThermiqueSheet) -> dict:
    if sheet.id not in {s.id for s in plan_sheets(db, project)}:
        raise ThermiqueError("La détection automatique se lance sur une planche de plan à l'échelle définie.")
    with _verrou:
        if (_etats.get(sheet.id) or {}).get("en_cours"):
            return dict(_etats[sheet.id])
        _etats[sheet.id] = {"etape": ETAPES[0], "en_cours": True, "erreur": None, "resume": None}
    return dict(_etats[sheet.id])


def _regle_absente(project: ThermiqueProject, signature: str, forme: str) -> bool:
    return not any(r["signature"] == signature and r["forme"] == forme for r in _regles(project))


def _objets(db: Session, project: ThermiqueProject, sheet: ThermiqueSheet, elements: dict) -> dict:
    """Murs, portes, menuiseries et isolant reconnus, puis désignés."""
    resume = {"murs": 0, "portes": 0, "menuiseries": 0, "isolant": 0}
    signature = reconnaissance.signature_murs(elements)
    if signature and _regle_absente(project, signature, moteur_calques.TOUTES_FORMES):
        save_designation(db, project, signature, moteur_calques.TOUTES_FORMES, "mur")
    resume["murs"] = moteur_calques.nombre_famille(elements, signature, moteur_calques.TOUTES_FORMES) if signature else 0

    # les désignations automatiques précédentes de cette planche laissent la place aux nouvelles
    anciens = [p["element"] for p in _ponctuels(project) if p["planche"] == sheet.id and p.get("source") == "auto"]
    if anciens:
        set_elements(db, project, sheet, anciens, None)
    manuels = {p["element"] for p in _ponctuels(project) if p["planche"] == sheet.id}

    trouvees = reconnaissance.portes(elements)
    elements_portes = sorted({i for porte in trouvees for i in porte["elements"]} - manuels)
    if elements_portes:
        set_elements(db, project, sheet, elements_portes, "porte", source="auto")
    resume["portes"] = len(trouvees)

    groupes = reconnaissance.menuiseries(elements, exclus=set(elements_portes) | manuels)
    elements_menuiseries = sorted({i for groupe in groupes for i in groupe} - manuels)
    if elements_menuiseries:
        set_elements(db, project, sheet, elements_menuiseries, "menuiserie", source="auto")
    resume["menuiseries"] = len(groupes)

    murs = [i for i, regle in attribution(project, sheet, elements).items() if regle["nature"] == "mur"]
    isolants, hachures = reconnaissance.familles_isolant(elements, murs)
    for famille in isolants:
        if _regle_absente(project, famille, "court"):
            save_designation(db, project, famille, "court", "isolant", moteur_bande.ENVELOPPE)
            resume["isolant"] += 1
    # une hachure logée dans les murs est le remplissage du mur, pas un isolant
    for famille in hachures:
        if _regle_absente(project, famille, "court"):
            save_designation(db, project, famille, "court", "mur")
            resume["hachures"] = resume.get("hachures", 0) + 1
    return resume


def _enveloppe(db: Session, project: ThermiqueProject, sheet: ThermiqueSheet, elements: dict) -> dict:
    """Deux lignes déduites des pièces chauffées de la planche."""
    level = db.scalars(select(ThermiqueLevel).where(ThermiqueLevel.sheet_id == sheet.id)).first()
    if level is None:
        return {"enveloppe": "sans niveau"}
    if any(zone.kind in ("contour", "nu_exterieur") and zone.source != "automatique" for zone in level.zones):
        return {"enveloppe": "lignes tracées à la main : gardées"}
    chauffees = [
        json.loads(room.points_json)["contour"]
        for room in db.scalars(select(ThermiqueRoom).where(ThermiqueRoom.sheet_id == sheet.id))
        if room.classe == "chauffe"
    ]
    indices = [i for i, regle in attribution(project, sheet, elements).items() if regle["nature"] in LIMITES_ENVELOPPE]
    batiments = moteur_bande.depuis_pieces(elements, indices, chauffees)
    ecrire_lignes(db, level, batiments, ("contour", "nu_exterieur"))
    return {
        "enveloppe": f"{len(batiments)} bâtiment(s)",
        "nu_exterieur_m2": round(sum(b["aire_exterieur_m2"] for b in batiments), 2),
        "nu_interieur_m2": round(sum(b["aire_interieur_m2"] for b in batiments), 2),
    }


def _menuiseries_exterieures(db: Session, project: ThermiqueProject, sheet: ThermiqueSheet, elements: dict) -> dict:
    """Les menuiseries automatiques hors de la bande deviennent des menuiseries intérieures."""
    band = sheet_band(sheet)
    if band is None:
        return {"menuiseries_exterieures": 0, "menuiseries_interieures": 0}
    auto = [p["element"] for p in _ponctuels(project) if p["planche"] == sheet.id and p.get("source") == "auto" and p["nature"].startswith("menuiserie")]
    dans = set(band.filtrer(elements, auto, moteur_bande.ENVELOPPE))
    dehors = [i for i in auto if i not in dans]
    if dans:
        set_elements(db, project, sheet, sorted(dans), "menuiserie", source="auto")
    if dehors:
        set_elements(db, project, sheet, dehors, "menuiserie_interieure", source="auto")
    return {"menuiseries_exterieures": len(dans), "menuiseries_interieures": len(dehors)}


def run(sheet_id: int) -> None:
    """Tâche de fond : tout l'enchaînement sur une planche."""
    db = SessionLocal()
    resume: dict = {}
    try:
        sheet = db.get(ThermiqueSheet, sheet_id)
        project = db.get(ThermiqueProject, sheet.project_id) if sheet else None
        if sheet is None or project is None:
            raise ThermiqueError("Planche introuvable.")
        elements = sheet_elements(sheet)
        _etape(sheet_id, "objets")
        resume |= _objets(db, project, sheet, elements)

        _etape(sheet_id, "pieces")
        indices = [i for i, regle in attribution(project, sheet, elements).items() if regle["nature"] in NATURES_LIMITES]
        fermeture = moteur_bande.fermeture_auto(elements, indices)
        resume["fermeture_cm"] = round(fermeture * 100)
        detect_rooms(db, project, sheet, fermeture)

        _etape(sheet_id, "noms")
        read_names(sheet_id)

        _etape(sheet_id, "enveloppe")
        db.expire_all()
        try:
            resume |= _enveloppe(db, project, sheet, elements)
        except (PiecesError, ThermiqueError) as exc:
            resume["enveloppe"] = str(exc)

        _etape(sheet_id, "menuiseries")
        resume |= _menuiseries_exterieures(db, project, sheet, elements)
        pieces = db.scalars(select(ThermiqueRoom).where(ThermiqueRoom.sheet_id == sheet_id)).all()
        resume["pieces"] = len(pieces)
        resume["surface_chauffee_m2"] = round(sum(p.area_m2 for p in pieces if p.classe == "chauffe"), 2)
        _fin(sheet_id, resume, None)
    except Exception as exc:  # noqa: BLE001 — l'erreur est rendue à l'écran
        LOG.exception("Détection automatique impossible sur la planche %s", sheet_id)
        db.rollback()
        _fin(sheet_id, resume or None, str(exc) if isinstance(exc, ThermiqueError) else "Détection automatique impossible.")
    finally:
        db.close()
