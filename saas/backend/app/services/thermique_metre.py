"""Métré sur les plans, lot M1 : niveaux, calage, nord, contours et locaux non chauffés.

Les tracés sont stockés en points PDF de la planche de leur niveau ; surfaces, longueurs et
contrôles sont recalculés par le moteur (`thermique_moteur.metre`) à chaque lecture.
Voir docs/thermique/metre-plans-decisions.md.
"""
from __future__ import annotations

import json
import math
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.thermique import ThermiqueComponent, ThermiqueLevel, ThermiqueProject, ThermiqueSheet, ThermiqueZone
from app.models.user import User
from app.services.thermique import ThermiqueError, document_path
from app.services.thermique_raster import raster_root
from app.services.thermique_composants import create_component
from thermique_moteur import coupes, detection, enveloppe, metre, traits, vecteurs
from thermique_moteur import lignes as lignes_murs
from thermique_moteur import murs as murs_vectoriels

# Change si la lecture des traits évolue : les anciens fichiers en cache sont alors ignorés.
TRAITS_VERSION = "v1"
DETECTION_VERSION = "v1"
# Détection vectorielle des murs (docs/thermique/detection-murs-strategie.md) : à changer à chaque évolution du moteur.
MURS_VERSION = "v1"
# Faces de dalles sur les coupes : traits d'au moins 0,9 pt (1,56 et 0,96 pt sur le projet d'essai).
SEUIL_COUPE = 0.9

LEVEL_NUMBERS = {
    "altitude_m": ("altitude_m", "Altitude", -100.0, 1000.0),
    "hauteur_etage_m": ("floor_height_m", "Hauteur d'étage", 0.5, 30.0),
    "epaisseur_plancher_m": ("slab_thickness_m", "Épaisseur de plancher", 0.0, 3.0),
    "hauteur_sous_plafond_m": ("ceiling_height_m", "Hauteur sous plafond", 0.5, 30.0),
}
HEIGHT_KEYS = ("hauteur_etage_m", "epaisseur_plancher_m", "hauteur_sous_plafond_m")


def _dump(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


def _load(text: str | None, default: Any) -> Any:
    return json.loads(text) if text else default


# --- Accès ---------------------------------------------------------------------------------------


def _owner_ok(db: Session, user: User, project_id: int) -> bool:
    project = db.get(ThermiqueProject, project_id)
    return project is not None and project.owner_user_id == user.id


def get_level_for_user(db: Session, user: User, level_id: int) -> ThermiqueLevel | None:
    level = db.get(ThermiqueLevel, level_id)
    return level if level is not None and _owner_ok(db, user, level.project_id) else None


def get_zone_for_user(db: Session, user: User, zone_id: int) -> ThermiqueZone | None:
    zone = db.get(ThermiqueZone, zone_id)
    return zone if zone is not None and _owner_ok(db, user, zone.project_id) else None


def _levels(db: Session, project: ThermiqueProject) -> list[ThermiqueLevel]:
    statement = (
        select(ThermiqueLevel)
        .where(ThermiqueLevel.project_id == project.id)
        .order_by(ThermiqueLevel.position, ThermiqueLevel.id)
    )
    return list(db.scalars(statement))


# --- Niveaux -------------------------------------------------------------------------------------


def _number(value: Any, label: str, minimum: float, maximum: float) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ThermiqueError(f"{label} : valeur invalide.") from exc
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ThermiqueError(f"{label} : valeur hors limites ({minimum:g} à {maximum:g} m).")
    return number


def _sheet_id(db: Session, project: ThermiqueProject, value: Any) -> int | None:
    if value is None:
        return None
    sheet = db.get(ThermiqueSheet, int(value))
    if sheet is None or sheet.project_id != project.id:
        raise ThermiqueError("Cette planche n'appartient pas au projet.")
    return sheet.id


def _calage(value: Any) -> dict | None:
    if value is None:
        return None
    try:
        a = [float(v) for v in value["a"]]
        b = [float(v) for v in value["b"]]
    except (KeyError, TypeError, ValueError) as exc:
        raise ThermiqueError("Calage invalide : deux points A et B attendus.") from exc
    if len(a) != 2 or len(b) != 2:
        raise ThermiqueError("Calage invalide : deux points A et B attendus.")
    if math.hypot(b[0] - a[0], b[1] - a[1]) < 5.0:
        raise ThermiqueError("Les deux points de calage sont trop proches : choisissez deux repères éloignés.")
    return {"a": [round(a[0], 3), round(a[1], 3)], "b": [round(b[0], 3), round(b[1], 3)]}


def _apply_level(db: Session, project: ThermiqueProject, level: ThermiqueLevel, data: dict[str, Any]) -> None:
    if "nom" in data:
        name = (data["nom"] or "").strip()[:80]
        if not name:
            raise ThermiqueError("Le nom du niveau est obligatoire.")
        level.name = name
    if data.get("ordre") is not None:
        level.position = int(data["ordre"])
    for key, (attribute, label, minimum, maximum) in LEVEL_NUMBERS.items():
        if key in data:
            setattr(level, attribute, _number(data[key], label, minimum, maximum))
    if any(key in data for key in HEIGHT_KEYS):
        level.heights_source = "manuel"
    if "planche_id" in data:
        sheet_id = _sheet_id(db, project, data["planche_id"])
        if sheet_id != level.sheet_id:
            level.sheet_id = sheet_id
            # Le calage est propre à la planche : il ne survit pas à un changement de plan.
            if "calage" not in data:
                level.calage_json = None
    if "calage" in data:
        calage = _calage(data["calage"])
        level.calage_json = _dump(calage) if calage else None


def create_level(db: Session, project: ThermiqueProject, data: dict[str, Any]) -> ThermiqueLevel:
    existing = _levels(db, project)
    level = ThermiqueLevel(
        project_id=project.id,
        name=f"Niveau {len(existing)}",
        position=max((item.position for item in existing), default=-1) + 1,
    )
    _apply_level(db, project, level, data)
    db.add(level)
    db.commit()
    return level


def update_level(db: Session, project: ThermiqueProject, level: ThermiqueLevel, data: dict[str, Any]) -> ThermiqueLevel:
    _apply_level(db, project, level, data)
    db.commit()
    return level


def delete_level(db: Session, level: ThermiqueLevel) -> None:
    db.delete(level)
    db.commit()


def create_levels_from_sheets(db: Session, project: ThermiqueProject) -> int:
    """Un niveau par planche de plan au niveau reconnu (« Niveau 0 », « RDC », « R+1 »…)."""
    existing = _levels(db, project)
    used_sheets = {item.sheet_id for item in existing}
    used_positions = {item.position for item in existing}
    sheets = db.scalars(select(ThermiqueSheet).where(ThermiqueSheet.project_id == project.id).order_by(ThermiqueSheet.id))
    suggestions = metre.suggestion_niveaux(
        [{"id": sheet.id, "nature": sheet.nature or sheet.nature_suggested, "niveau": sheet.level_label} for sheet in sheets]
    )
    if not suggestions:
        raise ThermiqueError(
            "Aucune planche de plan avec un niveau reconnu (ex. « Niveau 0 », « RDC », « R+1 ») : renseignez le "
            "niveau des planches dans « Plans et planches » ou ajoutez les niveaux à la main."
        )
    created = 0
    for suggestion in suggestions:
        if suggestion["planche_id"] in used_sheets or suggestion["ordre"] in used_positions:
            continue
        db.add(
            ThermiqueLevel(
                project_id=project.id,
                name=suggestion["nom"],
                position=suggestion["ordre"],
                sheet_id=suggestion["planche_id"],
            )
        )
        created += 1
    db.commit()
    return created


def _level_sheet(db: Session, level: ThermiqueLevel) -> ThermiqueSheet | None:
    return db.get(ThermiqueSheet, level.sheet_id) if level.sheet_id else None


def set_north(db: Session, project: ThermiqueProject, level: ThermiqueLevel, p1: list[float], p2: list[float]) -> None:
    calage = _load(level.calage_json, None)
    sheet = _level_sheet(db, level)
    if not calage or sheet is None or not sheet.scale_denominator:
        raise ThermiqueError(
            "Calez d'abord ce niveau et vérifiez l'échelle de sa planche : le nord est exprimé dans le repère commun des niveaux."
        )
    project.north_deg = metre.angle_nord(metre.repere(calage, sheet.scale_denominator), p1, p2)
    db.commit()


# --- Tracés --------------------------------------------------------------------------------------


def _lnc_type(value: Any) -> str:
    value = value or "autre"
    if value not in metre.TYPES_LNC:
        raise ThermiqueError("Type de local non chauffé inconnu.")
    return value


def _check_components(db: Session, project_id: int, cotes: list[dict]) -> None:
    wanted = {cote["composant_id"] for cote in cotes if cote["composant_id"] is not None}
    if not wanted:
        return
    found = set(
        db.scalars(
            select(ThermiqueComponent.id).where(
                ThermiqueComponent.project_id == project_id, ThermiqueComponent.id.in_(wanted)
            )
        )
    )
    if wanted - found:
        raise ThermiqueError("Composant inconnu dans la bibliothèque de ce projet.")


def create_zone(db: Session, level: ThermiqueLevel, data: dict[str, Any]) -> ThermiqueZone:
    kind = data.get("type")
    if kind not in metre.TYPES_ZONE:
        raise ThermiqueError("Type de tracé inconnu.")
    if level.sheet_id is None:
        raise ThermiqueError("Associez d'abord une planche de plan à ce niveau.")
    points = metre.nettoyer_points(data.get("points"))
    cotes = [] if kind in metre.ZONES_SANS_COTES else metre.normaliser_cotes(data.get("cotes"), len(points), metre.DONNE_SUR_DEFAUT[kind])
    _check_components(db, level.project_id, cotes)
    lnc_type = _lnc_type(data.get("type_lnc")) if kind == "lnc" else None
    count = sum(1 for zone in level.zones if zone.kind == kind)
    default_name = metre.TYPES_LNC[lnc_type] if lnc_type and lnc_type != "autre" else metre.TYPES_ZONE[kind]
    name = (data.get("nom") or "").strip()[:120] or (default_name if count == 0 else f"{default_name} {count + 1}")
    zone = ThermiqueZone(
        project_id=level.project_id,
        level_id=level.id,
        kind=kind,
        name=name,
        lnc_type=lnc_type,
        points_json=_dump(points),
        edges_json=_dump(cotes),
        source="manuel",
    )
    db.add(zone)
    db.commit()
    return zone


def update_zone(db: Session, zone: ThermiqueZone, data: dict[str, Any]) -> ThermiqueZone:
    if "nom" in data:
        name = (data["nom"] or "").strip()[:120]
        if name:
            zone.name = name
    if "type_lnc" in data and zone.kind == "lnc":
        zone.lnc_type = _lnc_type(data["type_lnc"])
    points = _load(zone.points_json, [])
    if data.get("points") is not None:
        points = metre.nettoyer_points(data["points"])
        if points != _load(zone.points_json, []) and zone.source == "automatique":
            zone.source = "corrige"  # une correction n'est jamais écrasée par une nouvelle détection
        zone.points_json = _dump(points)
    if zone.kind not in metre.ZONES_SANS_COTES:
        source = data["cotes"] if data.get("cotes") is not None else _load(zone.edges_json, [])
        cotes = metre.normaliser_cotes(source, len(points), metre.DONNE_SUR_DEFAUT[zone.kind])
        _check_components(db, zone.project_id, cotes)
        zone.edges_json = _dump(cotes)
    db.commit()
    return zone


def delete_zone(db: Session, zone: ThermiqueZone) -> None:
    db.delete(zone)
    db.commit()


# --- Traits d'aimantation ------------------------------------------------------------------------


def sheet_traits(sheet: ThermiqueSheet, seuil: float | None) -> dict:
    """Traits épais de la planche (faces de murs) pour aimanter le tracé, mis en cache par seuil."""
    folder = raster_root(sheet.project_id, sheet.id)
    key = "auto" if seuil is None else f"{seuil:.2f}"
    cache = folder / f"traits_{TRAITS_VERSION}_{key}.json"
    if cache.is_file():
        return json.loads(cache.read_text(encoding="utf-8"))
    path = document_path(sheet.document)
    if not path.is_file():
        raise ThermiqueError("Fichier absent du stockage.")
    result = traits.extraire_aimantation(path, sheet.page_index, seuil)
    folder.mkdir(parents=True, exist_ok=True)
    partial = cache.with_suffix(".part")
    partial.write_text(_dump(result), encoding="utf-8")
    partial.replace(cache)
    return result


# --- Détection automatique (lot M3) ---------------------------------------------------------------


def _cached(sheet: ThermiqueSheet, name: str, compute) -> Any:
    folder = raster_root(sheet.project_id, sheet.id)
    cache = folder / f"{name}.json"
    if cache.is_file():
        return json.loads(cache.read_text(encoding="utf-8"))
    path = document_path(sheet.document)
    if not path.is_file():
        raise ThermiqueError("Fichier absent du stockage.")
    result = compute(path)
    folder.mkdir(parents=True, exist_ok=True)
    partial = cache.with_suffix(".part")
    partial.write_text(_dump(result), encoding="utf-8")
    partial.replace(cache)
    return result


def detect_contour(db: Session, level: ThermiqueLevel, replace: bool = False) -> dict:
    """Propose le contour au nu intérieur du niveau à partir de son plan.

    Un contour détecté précédemment et non retouché est remplacé ; un contour tracé ou corrigé par le
    thermicien ne l'est que sur confirmation (`replace`)."""
    sheet = _level_sheet(db, level)
    if sheet is None:
        raise ThermiqueError("Associez d'abord une planche de plan à ce niveau.")
    if not sheet.scale_denominator:
        raise ThermiqueError("Définissez l'échelle de la planche avant la détection.")
    kept = [zone for zone in level.zones if zone.kind == "contour" and zone.source != "automatique"]
    if kept and not replace:
        raise ThermiqueError("Ce niveau a déjà un contour tracé ou corrigé à la main : confirmez son remplacement.")

    def compute(path):
        lus = traits.lire_traits(path, sheet.page_index, avec_couleur=True)
        seuil = traits.seuil_propose(traits.classes_epaisseur(lus))
        found = detection.detecter_contour(lus, seuil, sheet.scale_denominator) if seuil else None
        return {"seuil": seuil, "echelle": sheet.scale_denominator, "contour": found}

    scale_key = f"{sheet.scale_denominator:g}".replace(".", "_")
    result = _cached(sheet, f"contour_{DETECTION_VERSION}_{scale_key}", compute)
    found = result.get("contour")
    if not found:
        raise ThermiqueError("Aucun contour n'a pu être détecté sur ce plan : tracez-le avec l'outil « Contour ».")
    for zone in [zone for zone in level.zones if zone.kind == "contour"]:
        if zone.source == "automatique" or replace:
            db.delete(zone)
    db.flush()
    points = metre.nettoyer_points(found["points"])
    db.add(
        ThermiqueZone(
            project_id=level.project_id,
            level_id=level.id,
            kind="contour",
            name="Contour détecté",
            points_json=_dump(points),
            edges_json=_dump(metre.normaliser_cotes(None, len(points), "exterieur")),
            source="automatique",
        )
    )
    db.commit()
    db.refresh(level)
    return {key: found[key] for key in ("aire_m2", "perimetre_m", "zones_exterieures_ecartees")} | {"sommets": len(points)}


def sheet_section(sheet: ThermiqueSheet) -> dict:
    """Planchers repérés sur une coupe, avec les hauteurs par niveau dans les deux sens de lecture."""

    def compute(path):
        found = coupes.detecter_planchers(traits.lire_traits(path, sheet.page_index), SEUIL_COUPE, sheet.scale_denominator)
        return {
            "axe": found["axe"],
            "dessins": [
                {
                    "index": index,
                    "planchers": [{key: p[key] for key in ("position_m", "epaisseur_m", "portee_m")} for p in dessin["planchers"]],
                    "hauteurs_etage_m": dessin["hauteurs_etage_m"],
                    "niveaux_montant": coupes.niveaux_depuis_coupe(dessin, found["pt_par_m"], True),
                    "niveaux_descendant": coupes.niveaux_depuis_coupe(dessin, found["pt_par_m"], False),
                }
                for index, dessin in enumerate(found["dessins"])
            ],
        }

    if not sheet.scale_denominator:
        raise ThermiqueError("Définissez l'échelle de la coupe avant de lire les hauteurs.")
    scale_key = f"{sheet.scale_denominator:g}".replace(".", "_")
    return _cached(sheet, f"coupe_{DETECTION_VERSION}_{scale_key}", compute)


def sheet_walls(sheet: ThermiqueSheet) -> dict:
    """Murs coupés d'un plan lus sur les vecteurs du PDF (paires de faces), sans contour préalable."""
    if not sheet.scale_denominator:
        raise ThermiqueError("Définissez l'échelle de la planche avant la détection des murs.")

    def compute(path):
        lignes = vecteurs.fusionner_lignes(traits.lire_traits(path, sheet.page_index, avec_couleur=True))
        return murs_vectoriels.detecter_murs(lignes, traits.lire_aplats(path, sheet.page_index), sheet.scale_denominator)

    scale_key = f"{sheet.scale_denominator:g}".replace(".", "_")
    return _cached(sheet, f"murs_{MURS_VERSION}_{scale_key}", compute)


def detect_lines(db: Session, level: ThermiqueLevel, replace: bool = False) -> dict:
    """Propose le nu intérieur (contour chauffé) et le nu extérieur du niveau, déduits des murs vectoriels
    (lot G1). Les lignes détectées et non retouchées sont remplacées ; celles tracées ou corrigées à la main ne
    le sont que sur confirmation (`replace`)."""
    sheet = _level_sheet(db, level)
    if sheet is None:
        raise ThermiqueError("Associez d'abord une planche de plan à ce niveau.")
    if not sheet.scale_denominator:
        raise ThermiqueError("Définissez l'échelle de la planche avant la détection.")
    kinds = ("contour", "nu_exterieur")
    if not replace and any(zone.kind in kinds and zone.source != "automatique" for zone in level.zones):
        raise ThermiqueError("Ce niveau a déjà un nu intérieur ou un nu extérieur tracé ou corrigé à la main : confirmez son remplacement.")
    murs_plan = sheet_walls(sheet)
    scale_key = f"{sheet.scale_denominator:g}".replace(".", "_")

    def compute(path):
        lus = vecteurs.fusionner_lignes(traits.lire_traits(path, sheet.page_index, avec_couleur=True))
        barrieres = lignes_murs.traits_barrieres(lus)
        return {"lignes": lignes_murs.detecter_deux_lignes(murs_plan["murs"], sheet.scale_denominator, barrieres)}

    result = _cached(sheet, f"lignes_{MURS_VERSION}_{scale_key}", compute)
    found = result.get("lignes")
    if not found:
        raise ThermiqueError("Les deux lignes n'ont pas pu être détectées sur ce plan : tracez-les avec les outils « Contour » et « Nu extérieur ».")
    for zone in [zone for zone in level.zones if zone.kind in kinds]:
        if zone.source == "automatique" or replace:
            db.delete(zone)
    db.flush()
    sommets = {}
    for kind, key, name in (("contour", "nu_interieur", "Nu intérieur détecté"), ("nu_exterieur", "nu_exterieur", "Nu extérieur détecté")):
        points = metre.nettoyer_points(found[key]["points"])
        sommets[key] = len(points)
        cotes = [] if kind in metre.ZONES_SANS_COTES else metre.normaliser_cotes(None, len(points), metre.DONNE_SUR_DEFAUT[kind])
        db.add(
            ThermiqueZone(
                project_id=level.project_id,
                level_id=level.id,
                kind=kind,
                name=name,
                points_json=_dump(points),
                edges_json=_dump(cotes),
                source="automatique",
            )
        )
    db.commit()
    db.refresh(level)
    return {
        "nu_interieur_m2": found["nu_interieur"]["aire_m2"],
        "nu_exterieur_m2": found["nu_exterieur"]["aire_m2"],
        "sommets_interieur": sommets["nu_interieur"],
        "sommets_exterieur": sommets["nu_exterieur"],
        "epaisseur_typique_m": found["epaisseur_typique_m"],
    }


def apply_section_heights(
    db: Session, project: ThermiqueProject, sheet: ThermiqueSheet, drawing: int, upward: bool, first_interval: int
) -> int:
    """Reporte les hauteurs lues sur la coupe : le niveau le plus bas reçoit l'intervalle `first_interval`,
    les suivants les intervalles suivants."""
    if sheet.project_id != project.id:
        raise ThermiqueError("Cette planche n'appartient pas au projet.")
    section = sheet_section(sheet)
    if not 0 <= drawing < len(section["dessins"]):
        raise ThermiqueError("Dessin de coupe introuvable.")
    intervals = section["dessins"][drawing]["niveaux_montant" if upward else "niveaux_descendant"]
    applied = 0
    for offset, level in enumerate(_levels(db, project)):
        index = first_interval + offset
        if 0 <= index < len(intervals):
            values = intervals[index]
            level.floor_height_m = values["hauteur_etage_m"]
            level.slab_thickness_m = values["epaisseur_plancher_m"]
            level.ceiling_height_m = values["hauteur_sous_plafond_m"]
            level.heights_source = "coupe"
            applied += 1
    if not applied:
        raise ThermiqueError("Aucun niveau ne correspond aux intervalles choisis.")
    db.commit()
    return applied


def detect_walls(db: Session, zone: ThermiqueZone) -> dict:
    """Lit sur le plan l'épaisseur du mur et la position de l'isolant de chaque côté du tracé (lot M4a)."""
    if zone.kind in metre.ZONES_SANS_COTES:
        raise ThermiqueError("Les types de murs se lisent sur un contour chauffé ou un patio.")
    level = db.get(ThermiqueLevel, zone.level_id)
    sheet = _level_sheet(db, level)
    if sheet is None or not sheet.scale_denominator:
        raise ThermiqueError("Associez une planche à l'échelle définie à ce niveau.")
    path = document_path(sheet.document)
    if not path.is_file():
        raise ThermiqueError("Fichier absent du stockage.")
    lus = traits.lire_traits(path, sheet.page_index, avec_couleur=True)
    seuil = traits.seuil_propose(traits.classes_epaisseur(lus))
    if not seuil:
        raise ThermiqueError("Aucun trait de mur lisible sur ce plan.")
    points = _load(zone.points_json, [])
    analyse = enveloppe.analyser_murs(lus, traits.lire_aplats(path, sheet.page_index), points, seuil, sheet.scale_denominator)
    cotes = metre.normaliser_cotes(_load(zone.edges_json, []), len(points), metre.DONNE_SUR_DEFAUT[zone.kind])
    for cote, lu in zip(cotes, analyse["cotes"]):
        cote["mur"] = {"epaisseur_m": lu["epaisseur_m"], "isolant": lu["isolant"], "part_lue": lu["part_lue"]}
    zone.edges_json = _dump(cotes)
    db.commit()
    longueurs = [longueur * metre.pt_en_m(sheet.scale_denominator) for longueur in metre.longueurs_cotes(points)]
    return {
        "cotes_lues": sum(1 for cote in cotes if cote["mur"]["epaisseur_m"]),
        "cotes": len(cotes),
        "types": len(enveloppe.types_de_murs(cotes, longueurs)),
    }


def accept_wall_type(db: Session, user: User, zone: ThermiqueZone, thickness_m: float, component_id: int | None) -> int:
    """Rattache tous les côtés d'un type de mur détecté à un composant ; le crée s'il n'est pas donné."""
    project = db.get(ThermiqueProject, zone.project_id)
    level = db.get(ThermiqueLevel, zone.level_id)
    sheet = _level_sheet(db, level)
    points = _load(zone.points_json, [])
    cotes = metre.normaliser_cotes(_load(zone.edges_json, []), len(points), metre.DONNE_SUR_DEFAUT.get(zone.kind, "exterieur"))
    echelle = sheet.scale_denominator if sheet and sheet.scale_denominator else 100
    longueurs = [longueur * metre.pt_en_m(echelle) for longueur in metre.longueurs_cotes(points)]
    wall_type = next(
        (t for t in enveloppe.types_de_murs(cotes, longueurs) if abs(t["epaisseur_m"] - thickness_m) <= enveloppe.TOLERANCE_TYPE_M + 1e-9),
        None,
    )
    if wall_type is None:
        raise ThermiqueError("Ce type de mur n'existe plus : relancez la détection des murs.")
    if component_id is None:
        label = f"Mur {round(wall_type['epaisseur_m'] * 100)} cm"
        if wall_type["isolant"]:
            label += f", {enveloppe.ISOLANTS[wall_type['isolant']]}"
        component = create_component(
            db,
            user,
            project,
            {
                "categorie": "murs",
                "nom": label,
                "notes": (
                    f"Type détecté sur le plan ({zone.name}) : épaisseur {wall_type['epaisseur_m']:.2f} m sur "
                    f"{wall_type['longueur_m']:.1f} m. Composition à compléter."
                ).replace(".", ",", 2),
            },
        )
        component_id = component.id
    else:
        _check_components(db, zone.project_id, [{"composant_id": component_id}])
    for index in wall_type["cotes"]:
        cotes[index]["composant_id"] = component_id
    zone.edges_json = _dump(cotes)
    db.commit()
    return component_id


# --- Lecture -------------------------------------------------------------------------------------


def _serialize_zone(zone: ThermiqueZone) -> dict[str, Any]:
    return {
        "id": zone.id,
        "niveau_id": zone.level_id,
        "type": zone.kind,
        "nom": zone.name,
        "type_lnc": zone.lnc_type,
        "points": _load(zone.points_json, []),
        "cotes": _load(zone.edges_json, []),
        "source": zone.source,
    }


def serialize_metre(db: Session, project: ThermiqueProject) -> dict[str, Any]:
    levels = _levels(db, project)
    sheets = {sheet.id: sheet for sheet in db.scalars(select(ThermiqueSheet).where(ThermiqueSheet.project_id == project.id))}
    rows = []
    for level in levels:
        sheet = sheets.get(level.sheet_id) if level.sheet_id else None
        rows.append((level, sheet, sheet.scale_denominator if sheet else None, _load(level.calage_json, None)))
    checks = metre.controle_calages(
        [{"id": level.id, "nom": level.name, "echelle": scale, "calage": calage} for level, _sheet, scale, calage in rows]
    )
    niveaux = []
    for level, sheet, scale, calage in rows:
        zones = [_serialize_zone(zone) for zone in level.zones]
        synthese = metre.synthese_niveau(scale, level.floor_height_m, level.slab_thickness_m, zones, level.ceiling_height_m)
        for zone, resume in zip(zones, synthese["zones"]):
            zone["types_murs"] = (
                enveloppe.types_de_murs(zone["cotes"], resume["cotes_m"])
                if zone["type"] not in metre.ZONES_SANS_COTES and resume["cotes_m"]
                else []
            )
        if sheet is None:
            synthese["alertes"].insert(0, "Aucune planche de plan associée à ce niveau.")
        check = checks["par_niveau"].get(level.id, {})
        niveaux.append(
            {
                "id": level.id,
                "nom": level.name,
                "ordre": level.position,
                "altitude_m": level.altitude_m,
                "hauteur_etage_m": level.floor_height_m,
                "epaisseur_plancher_m": level.slab_thickness_m,
                "hauteur_sous_plafond_m": level.ceiling_height_m,
                "hauteurs_source": level.heights_source,
                "planche_id": sheet.id if sheet else None,
                "planche_libelle": sheet.label if sheet else None,
                "echelle": scale,
                "calage": calage,
                "calage_ab_m": check.get("ab_m"),
                "calage_ecart_m": check.get("ecart_m"),
                "zones": zones,
                "synthese": synthese,
            }
        )
    return {
        "niveaux": niveaux,
        "nord_deg": project.north_deg,
        "alertes": checks["alertes"],
        "listes": {"donne_sur": metre.DONNE_SUR, "types_zone": metre.TYPES_ZONE, "types_lnc": metre.TYPES_LNC},
    }
