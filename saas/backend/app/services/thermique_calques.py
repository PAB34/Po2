"""Désignation des calques par l'exemple — étape E1 révisée (docs/thermique/refondation-parcours-decisions.md §10).

Le thermicien clique un élément d'un plan et donne sa nature ; la règle (signature + forme → nature) vaut pour
tous les plans du projet. Les éléments de chaque planche sont lus une fois, puis gardés en cache (fichier à côté
des tuiles, et en mémoire pour les dernières planches consultées).
"""
from __future__ import annotations

import json
from collections import OrderedDict

from sqlalchemy import select
from sqlalchemy.orm import Session, object_session

from app.models.thermique import ThermiqueLevel, ThermiqueProject, ThermiqueSheet, ThermiqueZone
from app.services.thermique import ThermiqueError, document_path
from app.services.thermique_raster import raster_root
from thermique_moteur import calques as moteur
from thermique_moteur.bande import PERIMETRES, Bande

# Change si la lecture des éléments évolue : les anciens fichiers en cache sont alors ignorés.
ELEMENTS_VERSION = "v1"
MEMOIRE_MAX = 12
MAX_FAMILLE = 30000
MAX_DESIGNES = 60000
MAX_FAMILLES_ZONE = 30
_memoire: OrderedDict[str, tuple[float, dict]] = OrderedDict()
_bandes: OrderedDict[tuple, Bande] = OrderedDict()


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


def _stockage(project: ThermiqueProject) -> dict:
    try:
        donnees = json.loads(project.signatures_json) if project.signatures_json else {}
    except ValueError:
        return {}
    return donnees if isinstance(donnees, dict) else {}


def _regles(project: ThermiqueProject) -> list[dict]:
    return list(_stockage(project).get("regles", []))


def _ponctuels(project: ThermiqueProject) -> list[dict]:
    """Désignations d'éléments seuls (§14, D33) : planche, élément, nature."""
    return list(_stockage(project).get("elements", []))


def _enregistrer(db: Session, project: ThermiqueProject, regles: list[dict], ponctuels: list[dict] | None = None) -> None:
    if ponctuels is None:
        ponctuels = _ponctuels(project)
    project.signatures_json = json.dumps({"version": 2, "regles": regles, "elements": ponctuels}, separators=(",", ":"))
    db.commit()


def sheet_band(sheet: ThermiqueSheet) -> Bande | None:
    """Nu extérieur et nu intérieur du niveau de la planche (§15), sous forme de filtre ; None sans lignes."""
    db = object_session(sheet)
    if db is None or not sheet.scale_denominator:
        return None
    zones = list(
        db.scalars(
            select(ThermiqueZone)
            .join(ThermiqueLevel, ThermiqueZone.level_id == ThermiqueLevel.id)
            .where(ThermiqueLevel.sheet_id == sheet.id, ThermiqueZone.kind.in_(("contour", "nu_exterieur")))
            .order_by(ThermiqueZone.id)
        )
    )
    exterieurs = [json.loads(z.points_json) for z in zones if z.kind == "nu_exterieur"]
    interieurs = [json.loads(z.points_json) for z in zones if z.kind == "contour"]
    if not exterieurs or not interieurs:
        return None
    cle = (sheet.id, sheet.scale_denominator, tuple((z.id, z.points_json) for z in zones))
    if cle not in _bandes:
        _bandes[cle] = Bande(exterieurs, interieurs, sheet.scale_denominator)
        while len(_bandes) > MEMOIRE_MAX:
            _bandes.popitem(last=False)
    _bandes.move_to_end(cle)
    return _bandes[cle]


def attribution(project: ThermiqueProject, sheet: ThermiqueSheet, elements: dict | None = None) -> dict[int, dict]:
    """Nature de chaque élément désigné de la planche (règles dans leur portée, puis éléments seuls)."""
    return moteur.attribuer(elements or sheet_elements(sheet), _regles(project), sheet.id, _ponctuels(project), sheet_band(sheet))


def _regle(regles: list[dict], regle_id: int) -> dict:
    regle = next((r for r in regles if r["id"] == regle_id), None)
    if regle is None:
        raise ThermiqueError("Calque désigné introuvable.")
    return regle


def _comptes(
    signature: str, forme: str, planches: list[tuple[ThermiqueSheet, dict]], exclusions: list[dict] = (), perimetre: str = moteur.PARTOUT
) -> list[dict]:
    par_planche = []
    for sheet, elements in planches:
        if perimetre == moteur.PARTOUT:
            nombre = moteur.nombre_famille(elements, signature, forme) - sum(1 for e in exclusions if e["planche"] == sheet.id)
        else:
            regle = {"signature": signature, "forme": forme, "perimetre": perimetre, "exclusions": exclusions}
            nombre = len(moteur.membres(elements, regle, sheet.id, sheet_band(sheet)))
        if nombre > 0:
            par_planche.append({"id": sheet.id, "libelle": sheet.label, "nombre": nombre})
    return par_planche


def _meme_regle(regle: dict, signature: str, forme: str, perimetre: str) -> bool:
    return regle["signature"] == signature and regle["forme"] == forme and moteur.perimetre(regle) == perimetre


def _exclusions(regles: list[dict], signature: str, forme: str, perimetre: str = moteur.PARTOUT) -> list[dict]:
    """Éléments retirés du calque déjà désigné pour cette famille et cette portée (aucun s'il n'existe pas)."""
    regle = next((r for r in regles if _meme_regle(r, signature, forme, perimetre)), None)
    return regle["exclusions"] if regle else []


def _sans_enveloppe(planches: list[tuple[ThermiqueSheet, dict]]) -> list[str]:
    return [sheet.label for sheet, _ in planches if sheet_band(sheet) is None]


def list_designations(db: Session, project: ThermiqueProject) -> dict:
    sheets = plan_sheets(db, project)
    planches = [(sheet, sheet_elements(sheet)) for sheet in sheets]
    regles = []
    for regle in _regles(project):
        par_planche = _comptes(regle["signature"], regle["forme"], planches, regle["exclusions"], moteur.perimetre(regle))
        regles.append(
            {
                **regle,
                "perimetre": moteur.perimetre(regle),
                "perimetre_libelle": PERIMETRES[moteur.perimetre(regle)],
                "libelle": moteur.libelle_signature(regle["signature"]),
                "forme_libelle": moteur.libelle_forme(regle["forme"]),
                "nature_libelle": moteur.NATURES.get(regle["nature"], regle["nature"]),
                "total": sum(p["nombre"] for p in par_planche),
                "par_planche": par_planche,
            }
        )
    par_nature: dict[str, dict] = {}
    libelles = {s.id: s.label for s in sheets}
    for ponctuel in _ponctuels(project):
        groupe = par_nature.setdefault(
            ponctuel["nature"],
            {"nature": ponctuel["nature"], "nature_libelle": moteur.NATURES.get(ponctuel["nature"], ponctuel["nature"]), "nombre": 0, "planches": []},
        )
        groupe["nombre"] += 1
        libelle = libelles.get(ponctuel["planche"])
        if libelle and libelle not in groupe["planches"]:
            groupe["planches"].append(libelle)
    return {
        "regles": regles,
        "ponctuels": list(par_nature.values()),
        "natures": moteur.NATURES,
        "perimetres": PERIMETRES,
        "planches": [{"id": s.id, "libelle": s.label, "enveloppe": sheet_band(s) is not None} for s in sheets],
    }


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
    regles = _regles(project)
    for forme in [element[2], moteur.TOUTES_FORMES] if trait else [moteur.TOUTES_FORMES]:
        par_planche = _comptes(signature, forme, planches, _exclusions(regles, signature, forme))
        familles.append(
            {"forme": forme, "forme_libelle": moteur.libelle_forme(forme), "total": sum(p["nombre"] for p in par_planche), "par_planche": par_planche}
        )
    bande = sheet_band(sheet)
    positions = bande.positions(elements, index) if bande is not None else [moteur.PARTOUT]
    regle = moteur.regle_applicable(regles, signature, element[2] if trait else moteur.TOUTES_FORMES, positions)
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
            # portées qui s'appliquent à cet élément (« dans l'enveloppe », « à l'intérieur »)
            "positions": positions,
        },
        "enveloppe_tracee": bande is not None,
        "familles": familles,
        "regle": None
        if regle is None
        else {
            "id": regle["id"],
            "nature": regle["nature"],
            "nature_libelle": moteur.NATURES.get(regle["nature"], regle["nature"]),
            "forme": regle["forme"],
            "perimetre": moteur.perimetre(regle),
            "exclu": any(e["planche"] == sheet.id and e["element"] == index for e in regle["exclusions"]),
        },
        "ponctuel": next(
            (
                {"nature": p["nature"], "nature_libelle": moteur.NATURES.get(p["nature"], p["nature"])}
                for p in _ponctuels(project)
                if p["planche"] == sheet.id and p["element"] == index
            ),
            None,
        ),
    }


def save_designation(
    db: Session, project: ThermiqueProject, signature: str, forme: str, nature: str, perimetre: str = moteur.PARTOUT
) -> None:
    """Désigne la nature d'une famille dans une portée ; une famille déjà désignée dans cette portée change de
    nature."""
    if nature not in moteur.NATURES:
        raise ThermiqueError("Nature inconnue.")
    if perimetre not in PERIMETRES:
        raise ThermiqueError("Portée inconnue.")
    if signature.startswith("aplat|"):
        if forme != moteur.TOUTES_FORMES:
            raise ThermiqueError("Un remplissage se désigne pour toutes ses formes.")
    elif not signature.startswith("trait|") or (forme != moteur.TOUTES_FORMES and forme not in moteur.FORMES):
        raise ThermiqueError("Élément inconnu.")
    regles = _regles(project)
    existante = next((r for r in regles if _meme_regle(r, signature, forme, perimetre)), None)
    if existante is not None:
        existante["nature"] = nature
    else:
        regles.append(
            {
                "id": max((r["id"] for r in regles), default=0) + 1,
                "signature": signature,
                "forme": forme,
                "perimetre": perimetre,
                "nature": nature,
                "exclusions": [],
            }
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


def _zone_par_regle(elements: dict, regles: list[dict], zone: list[int]) -> dict[int, list[int]]:
    """Éléments de la zone appartenant à la famille de chaque règle (retirés compris)."""
    signatures = elements["signatures"]
    resultat: dict[int, list[int]] = {}
    for regle in regles:
        if regle["signature"] not in signatures:
            continue
        numero = signatures.index(regle["signature"])
        membres = [
            i for i in zone
            if elements["elements"][i][1] == numero and regle["forme"] in (moteur.TOUTES_FORMES, elements["elements"][i][2])
        ]
        if membres:
            resultat[regle["id"]] = membres
    return resultat


def _contour(contour: list[float]) -> list[float]:
    if len(contour) % 2 or len(contour) < 6:
        raise ThermiqueError("Tracez une zone d'au moins trois points.")
    return contour


def zone_summary(project: ThermiqueProject, sheet: ThermiqueSheet, contour: list[float]) -> dict:
    """Calques désignés présents dans un lasso : éléments actifs et retirés, par calque (§11)."""
    regles = _regles(project)
    elements = sheet_elements(sheet)
    zone = moteur.dans_zone(elements, _contour(contour))
    attribues = {i: r["id"] for i, r in attribution(project, sheet, elements).items()}
    calques = []
    montres: set[int] = set()
    for regle in regles:
        membres = _zone_par_regle(elements, [regle], zone).get(regle["id"], [])
        exclus = {e["element"] for e in regle["exclusions"] if e["planche"] == sheet.id}
        actifs = [i for i in membres if attribues.get(i) == regle["id"]]
        retires = [i for i in membres if i in exclus]
        if not actifs and not retires:
            continue
        montres.update(actifs)
        montres.update(retires)
        calques.append(
            {
                "id": regle["id"],
                "nature": regle["nature"],
                "nature_libelle": moteur.NATURES.get(regle["nature"], regle["nature"]),
                "libelle": moteur.libelle_signature(regle["signature"]),
                "forme_libelle": moteur.libelle_forme(regle["forme"]),
                "actifs": len(actifs),
                "retires": len(retires),
            }
        )
    familles = []
    planches = None
    for signature, forme, nombre in moteur.familles_de(elements, zone)[:MAX_FAMILLES_ZONE]:
        if planches is None:
            planches = [(s, sheet_elements(s)) for s in _plan_sheets_of(project)]
        familles.append(
            {
                "signature": signature,
                "forme": forme,
                "libelle": moteur.libelle_signature(signature),
                "forme_libelle": moteur.libelle_forme(forme),
                "dans_zone": nombre,
                "total": sum(p["nombre"] for p in _comptes(signature, forme, planches, _exclusions(regles, signature, forme))),
                "nature": (moteur.regle_applicable(regles, signature, forme) or {}).get("nature"),
            }
        )
    return {"calques": calques, "familles": familles, **moteur.coordonnees(elements, sorted(montres), MAX_FAMILLE)}


def _plan_sheets_of(project: ThermiqueProject) -> list[ThermiqueSheet]:
    db = object_session(project)
    return plan_sheets(db, project) if db is not None else []


def set_elements(db: Session, project: ThermiqueProject, sheet: ThermiqueSheet, indices: list[int], nature: str | None) -> None:
    """Donne une nature à des éléments seuls de la planche, ou la leur retire (`nature` vide)."""
    if nature is not None and nature not in moteur.NATURES:
        raise ThermiqueError("Nature inconnue.")
    nombre = len(sheet_elements(sheet)["elements"])
    if not indices or any(not 0 <= i < nombre for i in indices):
        raise ThermiqueError("Élément introuvable sur cette planche.")
    cibles = set(indices)
    ponctuels = [p for p in _ponctuels(project) if p["planche"] != sheet.id or p["element"] not in cibles]
    if nature is not None:
        ponctuels += [{"planche": sheet.id, "element": i, "nature": nature} for i in sorted(cibles)]
    _enregistrer(db, project, _regles(project), ponctuels)


def designate_zone(
    db: Session,
    project: ThermiqueProject,
    sheet: ThermiqueSheet,
    contour: list[float],
    familles: list[tuple[str, str]],
    nature: str,
    partout: bool,
    perimetre: str = moteur.PARTOUT,
) -> None:
    """Lasso « Désigner » (§14, D32) : les familles cochées prennent la nature sur tous les plans, ou seuls leurs
    éléments situés dans la zone."""
    if nature not in moteur.NATURES:
        raise ThermiqueError("Nature inconnue.")
    if not familles:
        raise ThermiqueError("Cochez au moins un type de trait.")
    if partout:
        for signature, forme in familles:
            save_designation(db, project, signature, forme, nature, perimetre)
        return
    elements = sheet_elements(sheet)
    choisies = set(familles)
    indices = []
    for index in moteur.dans_zone(elements, _contour(contour)):
        element = elements["elements"][index]
        forme = element[2] if element[0] == moteur.TRAIT else moteur.TOUTES_FORMES
        if (elements["signatures"][element[1]], forme) in choisies:
            indices.append(index)
    if not indices:
        raise ThermiqueError("Aucun élément de ces types dans la zone.")
    set_elements(db, project, sheet, indices, nature)


def apply_zone(
    db: Session, project: ThermiqueProject, sheet: ThermiqueSheet, contour: list[float], regle_ids: list[int], retirer: bool
) -> None:
    """Retire de calques désignés tous leurs éléments situés dans le lasso, ou les y remet."""
    regles = _regles(project)
    choisies = [_regle(regles, regle_id) for regle_id in regle_ids]
    if not choisies:
        raise ThermiqueError("Choisissez au moins un calque.")
    elements = sheet_elements(sheet)
    zone = moteur.dans_zone(elements, _contour(contour))
    for regle_id, membres in _zone_par_regle(elements, choisies, zone).items():
        regle = _regle(regles, regle_id)
        cibles = set(membres)
        autres = [e for e in regle["exclusions"] if e["planche"] != sheet.id or e["element"] not in cibles]
        if retirer:
            autres += [{"planche": sheet.id, "element": i} for i in sorted(cibles)]
        regle["exclusions"] = autres
    _enregistrer(db, project, regles)


def family_elements(
    project: ThermiqueProject, sheet: ThermiqueSheet, signature: str, forme: str, perimetre: str = moteur.PARTOUT
) -> dict:
    """Éléments d'une famille sur la planche, dans la portée, sans ceux retirés de son calque (§11 D23, §15)."""
    if perimetre not in PERIMETRES:
        raise ThermiqueError("Portée inconnue.")
    elements = sheet_elements(sheet)
    regle = {"signature": signature, "forme": forme, "perimetre": perimetre, "exclusions": _exclusions(_regles(project), signature, forme, perimetre)}
    return moteur.coordonnees(elements, moteur.membres(elements, regle, sheet.id, sheet_band(sheet)), MAX_FAMILLE)


def sheet_designations(project: ThermiqueProject, sheet: ThermiqueSheet) -> dict:
    """Éléments désignés de la planche, regroupés par nature."""
    if not _regles(project) and not _ponctuels(project):
        return {"natures": {}, "tronque": False}
    elements = sheet_elements(sheet)
    attribues = attribution(project, sheet, elements)
    groupes: dict[str, dict] = {}
    for index, regle in list(attribues.items())[:MAX_DESIGNES]:
        element = elements["elements"][index]
        groupe = groupes.setdefault(regle["nature"], {"traits": [], "remplissages": []})
        groupe["traits" if element[0] == moteur.TRAIT else "remplissages"].append(element[7])
    return {"natures": groupes, "tronque": len(attribues) > MAX_DESIGNES}
