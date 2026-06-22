"""
Moteur de la boîte de rapprochement patrimoine (PO2-PAT-003).

Collecte les objets externes (PRM ENEDIS, PCE GRDF), propose un candidat
Bâtiment/Site par similarité de libellé, et applique la décision utilisateur en
écrivant le rattachement canonique dans les tables métier.

Aucune dépendance lourde : la normalisation/similarité est locale (pas de pandas).
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.building_meter import BuildingMeterLink
from app.models.gas import GasPce
from app.models.invoice import EnergyAccountingSiteMapping
from app.models.patrimoine_match import (
    PatrimoineMatchItem,
    SOURCE_ENEDIS_PRM,
    SOURCE_GRDF_PCE,
    STATUS_IGNORED,
    STATUS_LINKED,
    STATUS_TODO,
    STATUS_TO_CREATE,
    TARGET_BUILDING,
    TARGET_SITE,
)
from app.models.site import Site

# Statuts considérés comme « décidés par l'utilisateur » : la collecte ne les écrase pas.
_USER_DECIDED = {STATUS_LINKED, STATUS_IGNORED, STATUS_TO_CREATE}

# Score minimal pour proposer un candidat (en dessous : aucun candidat fiable).
# Volontairement bas : un candidat faible reste utile (l'utilisateur confirme),
# tandis que le rattachement automatique en masse exige un score >= 90.
_CANDIDATE_MIN_SCORE = 35.0


# --------------------------------------------------------------------------- #
# Normalisation / similarité
# --------------------------------------------------------------------------- #
def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# Mots vides qui n'aident pas le matching de libellés de sites/bâtiments.
_STOPWORDS = {"DE", "DU", "DES", "LA", "LE", "LES", "ET", "A", "L", "D"}


def _tokens(value: Any) -> set[str]:
    return {tok for tok in _normalize(value).split() if tok and tok not in _STOPWORDS}


def _similarity(a: Any, b: Any) -> float:
    """Score 0-100 : Jaccard des tokens, 100 si normalisés identiques."""
    na, nb = _normalize(a), _normalize(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 100.0
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    if inter == 0:
        return 0.0
    union = len(ta | tb)
    base = 100.0 * inter / union
    # Bonus si tous les tokens du libellé externe sont inclus dans la cible.
    if ta.issubset(tb) or tb.issubset(ta):
        base = min(100.0, base + 15.0)
    return round(base, 1)


# --------------------------------------------------------------------------- #
# Proposition de candidat
# --------------------------------------------------------------------------- #
def _city_filter(model, city_id: int | None):
    """Items de la ville courante OU sans ville (données non scopées historiques)."""
    if city_id is None:
        return True
    return (model.city_id == city_id) | (model.city_id.is_(None))


def _load_targets(db: Session, city_id: int | None) -> dict[str, list[tuple[int, str]]]:
    buildings = db.execute(
        select(Building.id, Building.nom_batiment, Building.ign_name).where(_city_filter(Building, city_id))
    ).all()
    sites = db.execute(
        select(Site.id, Site.nom_site).where(_city_filter(Site, city_id))
    ).all()
    return {
        "building": [(row[0], row[1] or row[2] or "") for row in buildings],
        "site": [(row[0], row[1] or "") for row in sites],
    }


def _propose_candidate(label: str | None, targets: dict[str, list[tuple[int, str]]]) -> dict[str, Any]:
    """Meilleur candidat Bâtiment puis Site (le bâtiment est prioritaire à score égal)."""
    best = {"type": None, "id": None, "label": None, "score": 0.0, "reason": None}
    if not label:
        return best
    for target_type in (TARGET_BUILDING, TARGET_SITE):
        for target_id, target_name in targets.get(target_type, []):
            if not target_name:
                continue
            score = _similarity(label, target_name)
            if score > best["score"]:
                best = {
                    "type": target_type,
                    "id": target_id,
                    "label": target_name,
                    "score": score,
                    "reason": "nom identique" if score >= 100 else "nom approchant",
                }
    if best["score"] < _CANDIDATE_MIN_SCORE:
        return {"type": None, "id": None, "label": None, "score": best["score"], "reason": None}
    return best


# --------------------------------------------------------------------------- #
# Détection des liens canoniques existants (-> statut « lié »)
# --------------------------------------------------------------------------- #
def _existing_prm_building(db: Session, prm_id: str) -> int | None:
    return db.execute(
        select(BuildingMeterLink.building_id).where(
            BuildingMeterLink.meter_identifier == prm_id,
            BuildingMeterLink.fluid.in_(("elec", "ELEC", "electricite", "ELECTRICITE")),
        )
    ).scalars().first()


# --------------------------------------------------------------------------- #
# Collecte
# --------------------------------------------------------------------------- #
def collect_matches(db: Session, city_id: int | None) -> dict[str, int]:
    """Upsert des objets externes dans la file. Préserve les décisions utilisateur."""
    targets = _load_targets(db, city_id)
    existing = {
        (item.source, item.external_id): item
        for item in db.execute(
            select(PatrimoineMatchItem).where(_city_filter(PatrimoineMatchItem, city_id))
        ).scalars()
    }
    summary = {"prm": 0, "pce": 0, "created": 0, "linked_detected": 0}

    def upsert(source: str, external_id: str, label: str | None, context: dict[str, Any], linked_building_id: int | None):
        key = (source, external_id)
        item = existing.get(key)
        if item is None:
            item = PatrimoineMatchItem(city_id=city_id, source=source, external_id=external_id)
            db.add(item)
            existing[key] = item
            summary["created"] += 1
        item.label = label
        item.context_json = json.dumps(context, ensure_ascii=False) if context else None
        # Lien canonique déjà présent -> statut lié (sauf si l'utilisateur a explicitement ignoré).
        if linked_building_id is not None and item.status != STATUS_IGNORED:
            item.status = STATUS_LINKED
            item.resolved_target_type = TARGET_BUILDING
            item.resolved_target_id = linked_building_id
            summary["linked_detected"] += 1
            return
        # On ne touche pas aux items déjà décidés par l'utilisateur.
        if item.status in _USER_DECIDED:
            return
        candidate = _propose_candidate(label, targets)
        item.candidate_target_type = candidate["type"]
        item.candidate_target_id = candidate["id"]
        item.candidate_label = candidate["label"]
        item.candidate_score = candidate["score"]
        item.candidate_reason = candidate["reason"]
        item.status = STATUS_TODO

    # PRM ENEDIS (référentiel matrice comptable)
    prm_rows = db.execute(
        select(EnergyAccountingSiteMapping).where(_city_filter(EnergyAccountingSiteMapping, city_id))
    ).scalars()
    for mapping in prm_rows:
        if not mapping.prm_id:
            continue
        summary["prm"] += 1
        upsert(
            SOURCE_ENEDIS_PRM,
            mapping.prm_id,
            mapping.site_name,
            {"regroupement": mapping.regroupement, "manager": mapping.manager},
            _existing_prm_building(db, mapping.prm_id),
        )

    # PCE GRDF
    pce_rows = db.execute(select(GasPce).where(_city_filter(GasPce, city_id))).scalars()
    for pce in pce_rows:
        if not pce.id_pce:
            continue
        summary["pce"] += 1
        upsert(
            SOURCE_GRDF_PCE,
            pce.id_pce,
            pce.nom_site,
            {"code_postal": pce.code_postal, "tarif_acheminement": pce.tarif_acheminement},
            pce.building_id,
        )

    db.commit()
    return summary


# --------------------------------------------------------------------------- #
# Lecture
# --------------------------------------------------------------------------- #
def list_matches(
    db: Session,
    city_id: int | None,
    source: str | None = None,
    status: str | None = None,
) -> list[PatrimoineMatchItem]:
    query = select(PatrimoineMatchItem).where(_city_filter(PatrimoineMatchItem, city_id))
    if source:
        query = query.where(PatrimoineMatchItem.source == source)
    if status:
        query = query.where(PatrimoineMatchItem.status == status)
    query = query.order_by(
        PatrimoineMatchItem.status,
        PatrimoineMatchItem.candidate_score.desc().nullslast(),
        PatrimoineMatchItem.id,
    )
    return list(db.execute(query).scalars())


def counts_by_status(db: Session, city_id: int | None) -> dict[str, int]:
    out = {STATUS_TODO: 0, STATUS_LINKED: 0, STATUS_TO_CREATE: 0, STATUS_IGNORED: 0}
    for item in db.execute(
        select(PatrimoineMatchItem.status).where(_city_filter(PatrimoineMatchItem, city_id))
    ).scalars():
        out[item] = out.get(item, 0) + 1
    return out


def search_targets(db: Session, city_id: int | None, query_text: str, limit: int = 20) -> list[dict[str, Any]]:
    """Recherche Bâtiments/Sites pour le sélecteur de rattachement."""
    needle = _normalize(query_text)
    results: list[dict[str, Any]] = []
    targets = _load_targets(db, city_id)
    for target_type, rows in targets.items():
        for target_id, name in rows:
            if not name:
                continue
            if not needle or needle in _normalize(name):
                results.append({"target_type": target_type, "target_id": target_id, "label": name})
    results.sort(key=lambda r: (r["target_type"] != TARGET_BUILDING, r["label"].lower()))
    return results[:limit]


# --------------------------------------------------------------------------- #
# Application de la décision (écrit le lien canonique)
# --------------------------------------------------------------------------- #
def _link_building(db: Session, fluid: str, meter_identifier: str, building_id: int, label: str | None) -> None:
    existing = db.execute(
        select(BuildingMeterLink).where(
            BuildingMeterLink.building_id == building_id,
            BuildingMeterLink.fluid == fluid,
            BuildingMeterLink.meter_identifier == meter_identifier,
        )
    ).scalars().first()
    if existing is None:
        db.add(
            BuildingMeterLink(
                building_id=building_id,
                fluid=fluid,
                meter_identifier=meter_identifier,
                meter_label=label,
                confidence="VALIDE",
                validation_status="VALIDE",
                source="RAPPROCHEMENT",
            )
        )
    else:
        existing.validation_status = "VALIDE"
        existing.confidence = "VALIDE"
        if label and not existing.meter_label:
            existing.meter_label = label


def _apply_link(db: Session, item: PatrimoineMatchItem, target_type: str, target_id: int) -> None:
    """Écrit le rattachement canonique selon la source. Le rattachement à un Site
    (sans bâtiment) est enregistré sur l'item mais n'écrit pas de lien compteur."""
    if target_type != TARGET_BUILDING:
        return
    if item.source == SOURCE_ENEDIS_PRM:
        _link_building(db, "elec", item.external_id, target_id, item.label)
    elif item.source == SOURCE_GRDF_PCE:
        pce = db.execute(
            select(GasPce).where(GasPce.id_pce == item.external_id)
        ).scalars().first()
        if pce is not None:
            pce.building_id = target_id
        _link_building(db, "gaz", item.external_id, target_id, item.label)


def update_match(
    db: Session,
    city_id: int | None,
    item_id: int,
    status: str,
    resolved_target_type: str | None = None,
    resolved_target_id: int | None = None,
    notes: str | None = None,
) -> PatrimoineMatchItem:
    item = db.execute(
        select(PatrimoineMatchItem).where(
            PatrimoineMatchItem.id == item_id,
            _city_filter(PatrimoineMatchItem, city_id),
        )
    ).scalars().first()
    if item is None:
        raise ValueError("Rapprochement introuvable.")

    if status == STATUS_LINKED:
        target_type = resolved_target_type or item.candidate_target_type
        target_id = resolved_target_id or item.candidate_target_id
        if not target_type or not target_id:
            raise ValueError("Une cible (bâtiment ou site) est requise pour lier.")
        if target_type not in (TARGET_BUILDING, TARGET_SITE):
            raise ValueError(f"Type de cible invalide : {target_type}")
        _apply_link(db, item, target_type, target_id)
        item.resolved_target_type = target_type
        item.resolved_target_id = target_id
    elif status in (STATUS_IGNORED, STATUS_TO_CREATE, STATUS_TODO):
        if status != STATUS_LINKED:
            item.resolved_target_type = None
            item.resolved_target_id = None
    else:
        raise ValueError(f"Statut invalide : {status}")

    item.status = status
    if notes is not None:
        item.notes = notes
    item.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return item


def bulk_link_obvious(db: Session, city_id: int | None, min_score: float = 90.0) -> dict[str, int]:
    """Lie automatiquement les items « à traiter » dont le candidat Bâtiment dépasse min_score."""
    linked = 0
    for item in list_matches(db, city_id, status=STATUS_TODO):
        if (
            item.candidate_target_type == TARGET_BUILDING
            and item.candidate_target_id
            and (item.candidate_score or 0) >= min_score
        ):
            _apply_link(db, item, TARGET_BUILDING, item.candidate_target_id)
            item.status = STATUS_LINKED
            item.resolved_target_type = TARGET_BUILDING
            item.resolved_target_id = item.candidate_target_id
            linked += 1
    db.commit()
    return {"linked": linked}
