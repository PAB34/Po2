"""Pièces des plans — étape E3 (docs/thermique/refondation-parcours-decisions.md §13, D28 à D30).

Détection des espaces fermés par les calques désignés, lecture des noms (Tesseract, en tâche de fond, gardée en
cache à côté des tuiles), pré-classement d'après le nom, corrections : ajout par clic, fusion, découpe.
"""
from __future__ import annotations

import json
import logging
import threading

from sqlalchemy import select
from sqlalchemy.orm import Session, object_session

from app.core.db import SessionLocal
from app.models.thermique import ThermiqueProject, ThermiqueRoom, ThermiqueSheet
from app.services.thermique import ThermiqueError, document_path
from app.services.thermique_calques import attribution, plan_sheets, sheet_elements
from app.services.thermique_raster import raster_root
from thermique_moteur import calques as calques_moteur
from thermique_moteur import composants
from thermique_moteur import pieces as moteur
from thermique_moteur import quadrilatere
from thermique_moteur import textes
from thermique_moteur.metre import pt_en_m


def room_scale(room: ThermiqueRoom) -> float | None:
    sheet = object_session(room).get(ThermiqueSheet, room.sheet_id) if object_session(room) else None
    return sheet.scale_denominator if sheet is not None else None

LOG = logging.getLogger(__name__)
MOTS_VERSION = "v1"
FERMETURE_MIN_M = 0.0
FERMETURE_MAX_M = 3.0
# paliers essayés au clic, jusqu'à ce que l'espace se referme
PALIERS_FERMETURE_M = (0.4, 0.8, 1.2, 1.6, 2.0, 2.5)
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
    attribues = attribution(project, sheet, elements)
    indices = [i for i, regle in attribues.items() if regle["nature"] in moteur.NATURES_LIMITES]
    natures = sorted({regle["nature"] for regle in attribues.values() if regle["nature"] in moteur.NATURES_LIMITES})
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
        points_json=json.dumps(
            {"contour": piece["contour"], "centre": piece["centre"], **({"detaille": piece["detaille"]} if piece.get("detaille") else {})},
            separators=(",", ":"),
        ),
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
    geometrie = _geometrie(room)
    voisinage = textes.VOISINAGE_NOM_M / pt_en_m(room_scale(room)) if room_scale(room) else None
    nom, repere = textes.nom_de_piece(mots, geometrie["contour"], geometrie.get("centre"), voisinage)
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


def _essayer_au_point(elements: dict, indices: list[int], x: float, y: float, fermeture_m: float) -> dict:
    """Contour au point cliqué, en élargissant la fermeture jusqu'à ce que l'espace se referme.

    Un local dont la façade est vitrée sans que les menuiseries soient désignées reste ouvert : à la
    fermeture demandée, le clic échouait, et le thermicien n'avait aucun moyen de savoir de combien
    l'élargir. On monte donc par paliers jusqu'à `FERMETURE_MAX_M` — le réglage de l'écran n'est plus
    qu'un plancher. Le contour obtenu est ensuite corrigeable à la main.
    """
    derniere: Exception | None = None
    paliers = [fermeture_m] + [p for p in PALIERS_FERMETURE_M if p > fermeture_m]
    for palier in paliers:
        try:
            return _en_quadrilatere(elements, moteur.piece_au_point(elements, indices, x, y, palier))
        except moteur.PiecesError as exc:
            derniere = exc
    raise ThermiqueError(str(derniere) if derniere else "Aucun espace fermé à cet endroit.")


def _en_quadrilatere(elements: dict, piece: dict) -> dict:
    """Simplifie la proposition sans imposer quatre côtés à un grand espace irrégulier.

    Le tracé détaillé est conservé à côté ; une correction manuelle devient ensuite la nouvelle vérité.
    """
    m = 1 / pt_en_m(elements["echelle"])
    try:
        coins = quadrilatere.simplifier_adaptatif(piece["contour"], m)
    except quadrilatere.QuadrilatereError:
        return piece
    if coins == piece["contour"]:
        return piece
    points = [(coins[k], coins[k + 1]) for k in range(0, len(coins), 2)]
    centre = piece.get("centre")
    if not centre or not moteur.dedans(*centre, coins):
        centre = [sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)]
    return {
        **piece,
        "contour": coins,
        "detaille": piece["contour"],
        "centre": centre,
        "surface_m2": round(quadrilatere.aire(points) * pt_en_m(elements["echelle"]) ** 2, 2),
    }


def add_room_at(db: Session, project: ThermiqueProject, sheet: ThermiqueSheet, x: float, y: float, fermeture_m: float) -> bool:
    _plan(db, project, sheet)
    if any(moteur.dedans(x, y, _geometrie(room)["contour"]) for room in _rooms(db, sheet)):
        raise ThermiqueError("Ce point est déjà dans une pièce.")
    elements, indices, _natures = _limites(project, sheet)
    piece = _essayer_au_point(elements, indices, x, y, _fermeture(fermeture_m))
    mots = sheet_words(sheet)
    db.add(_nouvelle(project, sheet, piece, "manuel", mots))
    db.commit()
    return mots is None and sheet.id not in _lectures


def _piece_tracee(echelle: float | None, contour: list[float]) -> dict:
    """Valide et mesure un contour fourni par l'utilisateur, sans dépendre des calques du plan."""
    if len(contour) < 6 or len(contour) % 2:
        raise ThermiqueError("Un contour demande au moins trois points.")
    if not echelle:
        raise ThermiqueError("Définissez l'échelle de la planche avant de tracer un contour.")
    points = [(contour[k], contour[k + 1]) for k in range(0, len(contour), 2)]
    aire = abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))) / 2
    surface = aire * pt_en_m(echelle) ** 2
    if surface < moteur.SURFACE_MIN_M2:
        raise ThermiqueError(f"Ce contour ne fait que {surface:.1f} m² : trop petit pour une pièce.")
    centre = [sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)]
    return {"contour": list(contour), "centre": centre, "surface_m2": round(surface, 2)}


def trace_room(db: Session, project: ThermiqueProject, sheet: ThermiqueSheet, contour: list[float]) -> bool:
    """Crée une pièce depuis un polygone tracé, sans exiger de murs ou menuiseries désignés."""
    _plan(db, project, sheet)
    piece = _piece_tracee(sheet.scale_denominator, contour)
    mots = sheet_words(sheet)
    db.add(_nouvelle(project, sheet, piece, "manuel", mots))
    db.commit()
    return mots is None and sheet.id not in _lectures


def _redessiner(room: ThermiqueRoom, contour: list[float]) -> None:
    """Contour corrigé à la main : sommet déplacé, ajouté ou retiré (étape 2 du parcours).

    Le contour proposé au clic n'a pas à être parfait puisqu'il est rectifiable — c'est ce qui permet
    de s'en servir sans attendre une détection exacte.
    """
    piece = _piece_tracee(room_scale(room), contour)
    room.points_json = json.dumps({"contour": piece["contour"], "centre": piece["centre"]}, separators=(",", ":"))
    room.area_m2 = piece["surface_m2"]
    room.source = "manuel"


def update_room(db: Session, room: ThermiqueRoom, data: dict) -> None:
    if data.get("contour") is not None:
        _redessiner(room, list(data["contour"]))
    if "nom" in data and data["nom"] is not None:
        room.name = str(data["nom"]).strip()[: textes.NOM_MAX]
        room.name_source = "saisi"
    if "classe" in data and data["classe"] is not None:
        if data["classe"] not in textes.CLASSES:
            raise ThermiqueError("Classe inconnue.")
        room.classe, room.classe_source = data["classe"], "choisi"
    db.commit()


def room_components(db: Session, project: ThermiqueProject, sheet: ThermiqueSheet, room: ThermiqueRoom) -> dict:
    """Ce qui borde ce local, côté par côté (étape 3 du parcours).

    On rend les familles graphiques collées au contour, avec leur longueur de contact et la nature déjà
    connue quand l'élément appartient à un calque désigné. Ce qui reste sans nature est ce sur quoi
    l'utilisateur doit se prononcer — et une seule fois par famille.
    """
    elements = sheet_elements(sheet)
    natures = {i: regle["nature"] for i, regle in attribution(project, sheet, elements).items()}
    contour = _geometrie(room)["contour"]
    familles = composants.bordant(elements, contour, natures)
    for famille in familles:
        famille["libelle"] = calques_moteur.libelle_signature(famille["signature"])
        famille["forme_libelle"] = calques_moteur.libelle_forme(famille["forme"])
        famille["nature_libelle"] = calques_moteur.NATURES.get(famille["nature"] or "")
    return {
        "piece": serialize_room(room),
        "cotes": composants.longueurs_des_cotes(elements, contour),
        "familles": familles,
        "natures": dict(calques_moteur.NATURES),
    }


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
