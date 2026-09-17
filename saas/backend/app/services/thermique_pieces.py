"""Pièces des plans — étape E3 (docs/thermique/refondation-parcours-decisions.md §13, D28 à D30).

Détection des espaces fermés par les calques désignés, lecture des noms (Tesseract, en tâche de fond, gardée en
cache à côté des tuiles), pré-classement d'après le nom, corrections : ajout par clic, fusion, découpe.
"""
from __future__ import annotations

import json
import logging
import threading

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.thermique import ThermiqueProject, ThermiqueRoom, ThermiqueSheet
from app.services.thermique import ThermiqueError, document_path
from app.services.thermique_calques import _regles, plan_sheets, sheet_elements
from app.services.thermique_raster import raster_root
from thermique_moteur import calques as moteur_calques
from thermique_moteur import pieces as moteur
from thermique_moteur import textes

LOG = logging.getLogger(__name__)
MOTS_VERSION = "v1"
FERMETURE_MIN_M = 0.0
FERMETURE_MAX_M = 3.0
_lectures: set[int] = set()
_verrou = threading.Lock()


def _mots_cache(sheet: ThermiqueSheet):
    return raster_root(sheet.project_id, sheet.id) / f"mots_{MOTS_VERSION}.json"


def sheet_words(sheet: ThermiqueSheet) -> list[dict] | None:
    cache = _mots_cache(sheet)
    return json.loads(cache.read_text(encoding="utf-8")) if cache.is_file() else None


def _etat_lecture(sheet: ThermiqueSheet) -> str:
    if sheet.id in _lectures:
        return "en_cours"
    return "faite" if _mots_cache(sheet).is_file() else "a_faire"


def _plan(db: Session, project: ThermiqueProject, sheet: ThermiqueSheet) -> ThermiqueSheet:
    if sheet.id not in {s.id for s in plan_sheets(db, project)}:
        raise ThermiqueError("Les pièces se détectent sur une planche de plan à l'échelle définie.")
    return sheet


def _limites(project: ThermiqueProject, sheet: ThermiqueSheet) -> tuple[dict, list[int], list[str]]:
    elements = sheet_elements(sheet)
    attribution = moteur_calques.attribuer(elements, _regles(project), sheet.id)
    indices = [i for i, regle in attribution.items() if regle["nature"] in moteur.NATURES_LIMITES]
    natures = sorted({regle["nature"] for regle in attribution.values() if regle["nature"] in moteur.NATURES_LIMITES})
    return elements, indices, natures


def _fermeture(fermeture_m: float) -> float:
    if not FERMETURE_MIN_M <= fermeture_m <= FERMETURE_MAX_M:
        raise ThermiqueError("Fermeture des ouvertures hors limites (0 à 3 m).")
    return fermeture_m


def _rooms(db: Session, sheet: ThermiqueSheet) -> list[ThermiqueRoom]:
    return list(db.scalars(select(ThermiqueRoom).where(ThermiqueRoom.sheet_id == sheet.id).order_by(ThermiqueRoom.id)))


def _geometrie(room: ThermiqueRoom) -> dict:
    return json.loads(room.points_json)


def serialize_room(room: ThermiqueRoom) -> dict:
    geometrie = _geometrie(room)
    return {
        "id": room.id,
        "nom": room.name,
        "repere": room.code,
        "nom_source": room.name_source,
        "classe": room.classe,
        "classe_source": room.classe_source,
        "contour": geometrie["contour"],
        "centre": geometrie["centre"],
        "surface_m2": room.area_m2,
        "source": room.source,
    }


def list_rooms(db: Session, project: ThermiqueProject, sheet: ThermiqueSheet) -> dict:
    rooms = _rooms(db, sheet)
    _elements, indices, natures = _limites(project, sheet)
    totaux = {classe: 0.0 for classe in textes.CLASSES}
    for room in rooms:
        totaux[room.classe] = round(totaux.get(room.classe, 0.0) + room.area_m2, 2)
    return {
        "pieces": [serialize_room(room) for room in rooms],
        "lecture_noms": _etat_lecture(sheet),
        "limites": {"elements": len(indices), "natures": natures},
        "classes": textes.CLASSES,
        "totaux": totaux,
    }


def _nouvelle(project: ThermiqueProject, sheet: ThermiqueSheet, piece: dict, source: str, mots: list[dict] | None) -> ThermiqueRoom:
    room = ThermiqueRoom(
        project_id=project.id,
        sheet_id=sheet.id,
        name="",
        points_json=json.dumps({"contour": piece["contour"], "centre": piece["centre"]}, separators=(",", ":")),
        area_m2=piece["surface_m2"],
        source=source,
        classe="chauffe",
        classe_source="propose",
    )
    if mots is not None:
        _nommer(room, mots)
    return room


def _nommer(room: ThermiqueRoom, mots: list[dict]) -> None:
    """Nom et repère lus, sauf nom saisi ; classe proposée d'après le nom, sauf classe choisie."""
    if room.name_source == "saisi":
        return
    nom, repere = textes.nom_de_piece(mots, _geometrie(room)["contour"])
    room.name, room.code, room.name_source = nom, repere, "lu"
    if room.classe_source != "choisi":
        room.classe = textes.classer(nom)


def read_names(sheet_id: int) -> None:
    """Tâche de fond : lit les mots de la planche (≈ 40 s), les garde en cache et nomme ses pièces."""
    with _verrou:
        if sheet_id in _lectures:
            return
        _lectures.add(sheet_id)
    db = SessionLocal()
    try:
        sheet = db.get(ThermiqueSheet, sheet_id)
        if sheet is None:
            return
        mots = textes.lire_mots(document_path(sheet.document), sheet.page_index)
        cache = _mots_cache(sheet)
        cache.parent.mkdir(parents=True, exist_ok=True)
        partiel = cache.with_suffix(".part")
        partiel.write_text(json.dumps(mots, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        partiel.replace(cache)
        for room in _rooms(db, sheet):
            _nommer(room, mots)
        db.commit()
    except Exception:
        LOG.exception("Lecture des noms impossible sur la planche %s", sheet_id)
        db.rollback()
    finally:
        db.close()
        with _verrou:
            _lectures.discard(sheet_id)


def detect_rooms(db: Session, project: ThermiqueProject, sheet: ThermiqueSheet, fermeture_m: float) -> bool:
    """Remplace les pièces détectées de la planche (les pièces ajoutées, fusionnées ou découpées à la main
    restent). Renvoie True si la lecture des noms reste à lancer."""
    _plan(db, project, sheet)
    elements, indices, _natures = _limites(project, sheet)
    try:
        trouvees = moteur.detecter(elements, indices, _fermeture(fermeture_m))
    except moteur.PiecesError as exc:
        raise ThermiqueError(str(exc)) from exc
    manuelles = [room for room in _rooms(db, sheet) if room.source != "auto"]
    for room in _rooms(db, sheet):
        if room.source == "auto":
            db.delete(room)
    mots = sheet_words(sheet)
    for piece in trouvees:
        # une pièce détectée qui recouvre une pièce faite à la main est écartée
        if any(moteur.dedans(*piece["centre"], _geometrie(room)["contour"]) for room in manuelles):
            continue
        db.add(_nouvelle(project, sheet, piece, "auto", mots))
    db.commit()
    return mots is None and sheet.id not in _lectures


def add_room_at(db: Session, project: ThermiqueProject, sheet: ThermiqueSheet, x: float, y: float, fermeture_m: float) -> bool:
    _plan(db, project, sheet)
    if any(moteur.dedans(x, y, _geometrie(room)["contour"]) for room in _rooms(db, sheet)):
        raise ThermiqueError("Ce point est déjà dans une pièce.")
    elements, indices, _natures = _limites(project, sheet)
    try:
        piece = moteur.piece_au_point(elements, indices, x, y, _fermeture(fermeture_m))
    except moteur.PiecesError as exc:
        raise ThermiqueError(str(exc)) from exc
    mots = sheet_words(sheet)
    db.add(_nouvelle(project, sheet, piece, "manuel", mots))
    db.commit()
    return mots is None and sheet.id not in _lectures


def update_room(db: Session, room: ThermiqueRoom, data: dict) -> None:
    if "nom" in data and data["nom"] is not None:
        room.name = str(data["nom"]).strip()[: textes.NOM_MAX]
        room.name_source = "saisi"
    if "classe" in data and data["classe"] is not None:
        if data["classe"] not in textes.CLASSES:
            raise ThermiqueError("Classe inconnue.")
        room.classe, room.classe_source = data["classe"], "choisi"
    db.commit()


def delete_room(db: Session, room: ThermiqueRoom) -> None:
    db.delete(room)
    db.commit()


def merge_rooms(db: Session, project: ThermiqueProject, sheet: ThermiqueSheet, ids: list[int]) -> None:
    rooms = [room for room in _rooms(db, sheet) if room.id in set(ids)]
    if len(rooms) != len(set(ids)):
        raise ThermiqueError("Pièce introuvable sur ce plan.")
    try:
        piece = moteur.fusionner([_geometrie(room)["contour"] for room in rooms], sheet.scale_denominator)
    except moteur.PiecesError as exc:
        raise ThermiqueError(str(exc)) from exc
    principale = max(rooms, key=lambda room: room.area_m2)
    fusion = _nouvelle(project, sheet, piece, "manuel", None)
    noms = [room.name for room in sorted(rooms, key=lambda room: -room.area_m2) if room.name]
    fusion.name = " + ".join(dict.fromkeys(noms))[: textes.NOM_MAX]
    fusion.name_source = "saisi" if any(room.name_source == "saisi" for room in rooms) else principale.name_source
    fusion.code = principale.code
    fusion.classe, fusion.classe_source = principale.classe, principale.classe_source
    for room in rooms:
        db.delete(room)
    db.add(fusion)
    db.commit()


def split_room(db: Session, project: ThermiqueProject, room: ThermiqueRoom, p1: list[float], p2: list[float]) -> None:
    sheet = db.get(ThermiqueSheet, room.sheet_id)
    try:
        morceaux = moteur.decouper(_geometrie(room)["contour"], p1, p2, sheet.scale_denominator)
    except moteur.PiecesError as exc:
        raise ThermiqueError(str(exc)) from exc
    mots = sheet_words(sheet)
    for morceau in morceaux:
        nouvelle = _nouvelle(project, sheet, morceau, "manuel", mots)
        if room.name_source == "saisi" or mots is None:
            nouvelle.name, nouvelle.name_source, nouvelle.code = room.name, room.name_source, room.code
        if room.classe_source == "choisi":
            nouvelle.classe, nouvelle.classe_source = room.classe, "choisi"
        db.add(nouvelle)
    db.delete(room)
    db.commit()


def get_room(db: Session, room_id: int) -> ThermiqueRoom | None:
    return db.get(ThermiqueRoom, room_id)
