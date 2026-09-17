"""Désignation des calques par l'exemple — étape E1 révisée (docs/thermique/refondation-parcours-decisions.md §10).

Le thermicien clique un élément d'un plan et donne sa nature ; la règle (signature + forme → nature) vaut pour
tous les plans du projet. Les éléments de chaque planche sont lus une fois, puis gardés en cache (fichier à côté
des tuiles, et en mémoire pour les dernières planches consultées).
"""
from __future__ import annotations

import json
from collections import OrderedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.thermique import ThermiqueProject, ThermiqueSheet
from app.services.thermique import ThermiqueError, document_path
from app.services.thermique_raster import raster_root
from thermique_moteur import calques as moteur

# Change si la lecture des éléments évolue : les anciens fichiers en cache sont alors ignorés.
ELEMENTS_VERSION = "v1"
MEMOIRE_MAX = 12
MAX_FAMILLE = 30000
MAX_DESIGNES = 60000
_memoire: OrderedDict[str, tuple[float, dict]] = OrderedDict()


def sheet_elements(sheet: ThermiqueSheet) -> dict:
    if not sheet.scale_denominator:
        raise ThermiqueError("Définissez l'échelle de la planche pour y désigner des calques.")
    scale_key = f"{sheet.scale_denominator:g}".replace(".", "_")
    cache = raster_root(sheet.project_id, sheet.id) / f"elements_{ELEMENTS_VERSION}_{scale_key}.json"
    cle = str(cache)
    lues = None
    if not cache.is_file():
        path = document_path(sheet.document)
        if not path.is_file():
            raise ThermiqueError("Fichier absent du stockage.")
        lues = moteur.lire_elements(path, sheet.page_index, sheet.scale_denominator)
        cache.parent.mkdir(parents=True, exist_ok=True)
        partiel = cache.with_suffix(".part")
        partiel.write_text(json.dumps(lues, separators=(",", ":")), encoding="utf-8")
        partiel.replace(cache)
    date = cache.stat().st_mtime
    connu = _memoire.get(cle)
    if lues is not None:
        connu = (date, lues)
    elif connu is None or connu[0] != date:
        connu = (date, json.loads(cache.read_text(encoding="utf-8")))
    _memoire[cle] = connu
    _memoire.move_to_end(cle)
    while len(_memoire) > MEMOIRE_MAX:
        _memoire.popitem(last=False)
    return connu[1]


def plan_sheets(db: Session, project: ThermiqueProject) -> list[ThermiqueSheet]:
    """Planches de plan à l'échelle définie : celles où les règles s'appliquent."""
    sheets = db.scalars(select(ThermiqueSheet).where(ThermiqueSheet.project_id == project.id).order_by(ThermiqueSheet.id))
    return [sheet for sheet in sheets if (sheet.nature or sheet.nature_suggested) == "plan" and sheet.scale_denominator]


def _regles(project: ThermiqueProject) -> list[dict]:
    try:
        donnees = json.loads(project.signatures_json) if project.signatures_json else {}
    except ValueError:
        return []
    return list(donnees.get("regles", [])) if isinstance(donnees, dict) else []


def _enregistrer(db: Session, project: ThermiqueProject, regles: list[dict]) -> None:
    project.signatures_json = json.dumps({"version": 2, "regles": regles}, separators=(",", ":"))
    db.commit()


def _regle(regles: list[dict], regle_id: int) -> dict:
    regle = next((r for r in regles if r["id"] == regle_id), None)
    if regle is None:
        raise ThermiqueError("Calque désigné introuvable.")
    return regle


def _comptes(signature: str, forme: str, planches: list[tuple[ThermiqueSheet, dict]], exclusions: list[dict] = ()) -> list[dict]:
    par_planche = []
    for sheet, elements in planches:
        nombre = moteur.nombre_famille(elements, signature, forme) - sum(1 for e in exclusions if e["planche"] == sheet.id)
        if nombre > 0:
            par_planche.append({"id": sheet.id, "libelle": sheet.label, "nombre": nombre})
    return par_planche


def list_designations(db: Session, project: ThermiqueProject) -> dict:
    sheets = plan_sheets(db, project)
    planches = [(sheet, sheet_elements(sheet)) for sheet in sheets]
    regles = []
    for regle in _regles(project):
        par_planche = _comptes(regle["signature"], regle["forme"], planches, regle["exclusions"])
        regles.append(
            {
                **regle,
                "libelle": moteur.libelle_signature(regle["signature"]),
                "forme_libelle": moteur.libelle_forme(regle["forme"]),
                "nature_libelle": moteur.NATURES.get(regle["nature"], regle["nature"]),
                "total": sum(p["nombre"] for p in par_planche),
                "par_planche": par_planche,
            }
        )
    return {"regles": regles, "natures": moteur.NATURES, "planches": [{"id": s.id, "libelle": s.label} for s in sheets]}


def pick_element(db: Session, project: ThermiqueProject, sheet: ThermiqueSheet, x: float, y: float, tolerance: float) -> dict:
    """Élément sous le clic, ses familles (même forme, tout le trait) comptées sur les plans, et sa règle éventuelle."""
    elements = sheet_elements(sheet)
    index = moteur.element_sous_point(elements, x, y, tolerance)
    if index is None:
        raise ThermiqueError("Aucun élément sous le clic : zoomez et cliquez au plus près d'un trait.")
    element = elements["elements"][index]
    signature = elements["signatures"][element[1]]
    trait = element[0] == moteur.TRAIT
    planches = [(s, sheet_elements(s)) for s in plan_sheets(db, project)]
    if sheet.id not in {s.id for s, _ in planches}:
        planches.append((sheet, elements))
    familles = []
    for forme in [element[2], moteur.TOUTES_FORMES] if trait else [moteur.TOUTES_FORMES]:
        par_planche = _comptes(signature, forme, planches)
        familles.append(
            {"forme": forme, "forme_libelle": moteur.libelle_forme(forme), "total": sum(p["nombre"] for p in par_planche), "par_planche": par_planche}
        )
    regle = moteur.regle_applicable(_regles(project), signature, element[2] if trait else moteur.TOUTES_FORMES)
    return {
        "element": {
            "planche": sheet.id,
            "index": index,
            "genre": "trait" if trait else "remplissage",
            "signature": signature,
            "forme": element[2],
            "libelle": moteur.libelle_signature(signature),
            "forme_libelle": moteur.libelle_forme(element[2]),
            "coords": element[7],
        },
        "familles": familles,
        "regle": None
        if regle is None
        else {
            "id": regle["id"],
            "nature": regle["nature"],
            "nature_libelle": moteur.NATURES.get(regle["nature"], regle["nature"]),
            "forme": regle["forme"],
            "exclu": any(e["planche"] == sheet.id and e["element"] == index for e in regle["exclusions"]),
        },
    }


def save_designation(db: Session, project: ThermiqueProject, signature: str, forme: str, nature: str) -> None:
    """Désigne la nature d'une famille ; une famille déjà désignée change de nature."""
    if nature not in moteur.NATURES:
        raise ThermiqueError("Nature inconnue.")
    if signature.startswith("aplat|"):
        if forme != moteur.TOUTES_FORMES:
            raise ThermiqueError("Un remplissage se désigne pour toutes ses formes.")
    elif not signature.startswith("trait|") or (forme != moteur.TOUTES_FORMES and forme not in moteur.FORMES):
        raise ThermiqueError("Élément inconnu.")
    regles = _regles(project)
    existante = next((r for r in regles if r["signature"] == signature and r["forme"] == forme), None)
    if existante is not None:
        existante["nature"] = nature
    else:
        regles.append(
            {"id": max((r["id"] for r in regles), default=0) + 1, "signature": signature, "forme": forme, "nature": nature, "exclusions": []}
        )
    _enregistrer(db, project, regles)


def delete_designation(db: Session, project: ThermiqueProject, regle_id: int) -> None:
    regles = _regles(project)
    _regle(regles, regle_id)
    _enregistrer(db, project, [r for r in regles if r["id"] != regle_id])


def toggle_exclusion(db: Session, project: ThermiqueProject, regle_id: int, planche_id: int, element: int) -> None:
    """Retire un élément d'une règle, ou l'y remet."""
    regles = _regles(project)
    regle = _regle(regles, regle_id)
    sheet = db.get(ThermiqueSheet, planche_id)
    if sheet is None or sheet.project_id != project.id:
        raise ThermiqueError("Planche introuvable dans ce projet.")
    if not 0 <= element < len(sheet_elements(sheet)["elements"]):
        raise ThermiqueError("Élément introuvable sur cette planche.")
    cible = {"planche": planche_id, "element": element}
    if cible in regle["exclusions"]:
        regle["exclusions"].remove(cible)
    else:
        regle["exclusions"].append(cible)
    _enregistrer(db, project, regles)


def family_elements(sheet: ThermiqueSheet, signature: str, forme: str) -> dict:
    elements = sheet_elements(sheet)
    return moteur.coordonnees(elements, moteur.famille(elements, signature, forme), MAX_FAMILLE)


def sheet_designations(project: ThermiqueProject, sheet: ThermiqueSheet) -> dict:
    """Éléments désignés de la planche, regroupés par nature."""
    regles = _regles(project)
    if not regles:
        return {"natures": {}, "tronque": False}
    elements = sheet_elements(sheet)
    attribution = moteur.attribuer(elements, regles, sheet.id)
    groupes: dict[str, dict] = {}
    for index, regle in list(attribution.items())[:MAX_DESIGNES]:
        element = elements["elements"][index]
        groupe = groupes.setdefault(regle["nature"], {"traits": [], "remplissages": []})
        groupe["traits" if element[0] == moteur.TRAIT else "remplissages"].append(element[7])
    return {"natures": groupes, "tronque": len(attribution) > MAX_DESIGNES}
