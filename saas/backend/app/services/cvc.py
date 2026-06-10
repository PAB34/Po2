import io
import json
import re
import unicodedata
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher

import openpyxl
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.city import City
from app.models.cvc import CvcInventoryItem, CvcRefrigerantItem, CvcSourceBuildingMapping
from app.models.equipment import EquipmentReference
from app.models.local import Local
from app.models.site import Site
from app.schemas.cvc import (
    BuildingMatchSuggestion,
    CvcApplySiteMappingsResult,
    CvcImportSiteMatchResponse,
    CvcImportSiteMatchResult,
    CvcBuildingMapping,
    CvcEquipmentReferenceRead,
    CvcImportBatchSummary,
    CvcImportResult,
    CvcInventoryItemRead,
    CvcInventoryItemUpdate,
    CvcMatchBuildingsResponse,
    CvcRecomputeReferencesResult,
    CvcRefrigerantBatchSummary,
    CvcRefrigerantDashboard,
    CvcRefrigerantDashboardKpi,
    CvcRefrigerantActionSummary,
    CvcRefrigerantImportResult,
    CvcRefrigerantItemRead,
    CvcRefrigerantItemUpdate,
    CvcRefrigerantMatchCandidate,
    CvcInventoryItemCompact,
    CvcSourceBuildingMappingRead,
    CvcSourceBuildingMappingUpdate,
    CvcTechnicalCoverageReport,
    CvcSiteMapping,
    CvcPreviewResponse,
    PatrimoineSiteSuggestion,
    SiteMatchResult,
)

CURRENT_YEAR = datetime.now().year
HEALTH_AGE_RATIOS = {
    "bon": 0.25,
    "moyen": 0.6,
    "mauvais": 0.95,
}
ALLOWED_CVC_REFERENCE_DOMAINS = {"A.2.1", "A.2.2", "A.2.3"}
NO_FUZZY_FAMILIES = {
    "analyseur",
    "appareil de mesure",
    "autre a qualifier",
    "compteur",
    "plomberie",
}
REFRIGERANT_NIVEAU_3 = {"Production de froid :", "Pompes à chaleur Air/Air, Air/Eau, Eau/Eau"}


DEFAULT_ACTION_STATUS = "À créer"


def _add_months(value: date, months: int) -> date:
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    month_lengths = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return date(year, month, min(value.day, month_lengths[month - 1]))


def _fgas_status(teqco2: float | None) -> str:
    if teqco2 is None:
        return "Données à compléter"
    if teqco2 < 5:
        return "Hors seuil contrôle périodique"
    if teqco2 < 50:
        return "Contrôle annuel"
    if teqco2 < 500:
        return "Contrôle semestriel"
    return "Suivi renforcé ≥500"


def _fgas_frequency_months(teqco2: float | None, detection_permanente: bool | None) -> int | None:
    if teqco2 is None or teqco2 < 5:
        return None
    if teqco2 < 50:
        return 24 if detection_permanente else 12
    if teqco2 < 500:
        return 12 if detection_permanente else 6
    return 6 if detection_permanente else 3


def _document_required(fgas_status: str) -> str:
    if fgas_status == "Hors seuil contrôle périodique":
        return "Fiche intervention uniquement si manipulation de fluide"
    if fgas_status == "Données à compléter":
        return "Fiche équipement / plaque signalétique"
    return "Rapport contrôle étanchéité + Cerfa 15497*04 si intervention fluide"


def _conformity_status(item: CvcRefrigerantItem, fgas_status: str, frequency_months: int | None) -> str:
    if fgas_status == "Données à compléter":
        return "Données à compléter"
    if fgas_status == "Hors seuil contrôle périodique":
        return "Non prioritaire"
    if item.dernier_controle_etancheite is None and item.prochaine_echeance is None:
        return "Dernier contrôle à demander"
    due_date = item.prochaine_echeance
    if due_date is None and item.dernier_controle_etancheite and frequency_months:
        due_date = _add_months(item.dernier_controle_etancheite, frequency_months)
    if due_date is None:
        return "Dernier contrôle à demander"
    today = date.today()
    if due_date < today:
        return "En retard"
    if due_date <= today + timedelta(days=60):
        return "À programmer < 60 j"
    return "OK"


def _priority(item: CvcRefrigerantItem, conformity_status: str) -> str:
    esp = _normalize(item.esp_status)
    if (
        conformity_status in {"En retard", "Dernier contrôle à demander", "Données à compléter"}
        or (item.teqco2 is not None and item.teqco2 >= 50)
        or esp == "manque de donnee"
    ):
        return "Haute"
    if conformity_status == "À programmer < 60 j":
        return "Moyenne"
    return "Basse"


def _next_action(conformity_status: str) -> str:
    if conformity_status == "Données à compléter":
        return "Compléter fluide / charge kg / GWP"
    if conformity_status == "Dernier contrôle à demander":
        return "Demander au titulaire le dernier contrôle et la prochaine échéance"
    if conformity_status == "En retard":
        return "Programmer un contrôle d’étanchéité"
    if conformity_status == "À programmer < 60 j":
        return "Créer un OT GMAO de contrôle"
    if conformity_status == "Non prioritaire":
        return "Surveiller uniquement en cas d’intervention"
    return "Conserver les preuves"


def _computed_refrigerant_fields(item: CvcRefrigerantItem) -> dict[str, object]:
    fgas_status = _fgas_status(item.teqco2)
    frequency = _fgas_frequency_months(item.teqco2, item.detection_permanente)
    conformity = _conformity_status(item, fgas_status, frequency)
    return {
        "fgas_status": fgas_status,
        "frequence_controle_mois": frequency,
        "statut_conformite": conformity,
        "action_prioritaire": _next_action(conformity),
        "preuve_attendue": _document_required(fgas_status),
        "priorite": _priority(item, conformity),
    }


def _action_summary(
    item: CvcRefrigerantItem,
    theme: str,
    constat: str,
    action: str | None = None,
) -> CvcRefrigerantActionSummary:
    computed = _computed_refrigerant_fields(item)
    return CvcRefrigerantActionSummary(
        item_id=item.id,
        priority=str(computed["priorite"]),
        theme=theme,
        site=item.site_raw,
        equipment=item.designation,
        constat=constat,
        action=action or str(computed["action_prioritaire"]),
        preuve_attendue=str(computed["preuve_attendue"]),
        responsable=item.titulaire or item.responsable_collectivite,
        echeance_cible=item.prochaine_echeance,
        statut_action=item.statut_action or DEFAULT_ACTION_STATUS,
    )


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_value.lower()).strip()


def _combined_item_text(
    famille: str | None,
    designation: str | None = None,
    marque: str | None = None,
    modele: str | None = None,
) -> str:
    return _normalize(" ".join(part for part in [famille, designation, marque, modele] if part))


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _build_address(b: Building) -> str | None:
    parts = [b.numero_voirie, b.nature_voie, b.nom_voie]
    addr = " ".join(p for p in parts if p)
    if b.nom_commune:
        addr = f"{addr}, {b.nom_commune}" if addr else b.nom_commune
    return addr or None


def parse_excel_preview(raw_bytes: bytes) -> CvcPreviewResponse:
    wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return CvcPreviewResponse(columns=[], total_rows=0, unique_sites=[], unique_families=[], sample_rows=[])

    header = [str(c) if c is not None else "" for c in rows[0]]
    data_rows = [r for r in rows[1:] if any(v is not None for v in r)]

    site_col = next((i for i, c in enumerate(header) if c == "SITE"), None)
    famille_col = next((i for i, c in enumerate(header) if c == "FAMILLE"), None)

    unique_sites: list[str] = []
    unique_families: list[str] = []

    if site_col is not None:
        seen: set[str] = set()
        for r in data_rows:
            v = r[site_col] if site_col < len(r) else None
            if v and str(v) not in seen:
                seen.add(str(v))
                unique_sites.append(str(v))

    if famille_col is not None:
        seen = set()
        for r in data_rows:
            v = r[famille_col] if famille_col < len(r) else None
            if v and str(v) not in seen:
                seen.add(str(v))
                unique_families.append(str(v))

    sample_rows = []
    for r in data_rows[:5]:
        row_dict: dict = {}
        for i, col in enumerate(header):
            if col and i < len(r):
                row_dict[col] = str(r[i]) if r[i] is not None else None
        sample_rows.append(row_dict)

    return CvcPreviewResponse(
        columns=[c for c in header if c],
        total_rows=len(data_rows),
        unique_sites=unique_sites,
        unique_families=unique_families,
        sample_rows=sample_rows,
    )


def _normalize_model(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize(value))


def _parse_float(value) -> float | None:
    if value is None:
        return None
    cleaned = str(value).strip().replace(" ", "").replace(",", ".")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_int(value) -> int | None:
    parsed = _parse_float(value)
    return int(parsed) if parsed is not None else None


def _header_lookup(header: list[str]) -> dict[str, int]:
    return {_normalize(col): idx for idx, col in enumerate(header) if col}


def _get_header_value(row: tuple, header_lookup: dict[str, int], name: str):
    idx = header_lookup.get(_normalize(name))
    if idx is None or idx >= len(row):
        return None
    return row[idx]


def _clean_cell(value) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _read_refrigerant_rows(raw_bytes: bytes) -> tuple[list[str], list[dict]]:
    wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], []

    header = [str(c).strip() if c is not None else "" for c in rows[0]]
    lookup = _header_lookup(header)
    years = [str(year) for year in range(2026, 2043)]
    parsed_rows: list[dict] = []

    for row_number, row in enumerate(rows[1:], start=2):
        if not any(value is not None and str(value).strip() for value in row):
            continue
        designation = _clean_cell(_get_header_value(row, lookup, "DESIGNATION"))
        if not designation:
            continue
        schedule = {
            year: value
            for year in years
            if (value := _clean_cell(_get_header_value(row, lookup, year)))
        }
        parsed_rows.append(
            {
                "row_number": row_number,
                "site_raw": _clean_cell(_get_header_value(row, lookup, "SITE")),
                "designation": designation,
                "quantite_relevee": _parse_int(_get_header_value(row, lookup, "QTE QTE RELEVEE")),
                "famille": _clean_cell(_get_header_value(row, lookup, "FAMILLE")),
                "marque": _clean_cell(_get_header_value(row, lookup, "MARQUE")),
                "modele": _clean_cell(_get_header_value(row, lookup, "MODELE")),
                "fluide_frigorigene": _clean_cell(_get_header_value(row, lookup, "Fluide frigo")),
                "quantite_fluide_kg": _parse_float(_get_header_value(row, lookup, "Quantite fluide en Kg")),
                "puissance_froid_kw": _parse_float(_get_header_value(row, lookup, "Puissance Froid en Kw")),
                "date_mis_en_service": _parse_int(_get_header_value(row, lookup, "DATE MES")),
                "gwp": _parse_float(_get_header_value(row, lookup, "GWP")),
                "teqco2": _parse_float(_get_header_value(row, lookup, "tEqCO2")),
                "esp_status": _clean_cell(_get_header_value(row, lookup, "ESP")),
                "cout_desp_date_eur": _parse_float(_get_header_value(row, lookup, "COUT DESP a Date")),
                "cumul_5_ans_eur": _parse_float(_get_header_value(row, lookup, "CUMUL SUR 5 ANS")),
                "schedule_json": json.dumps(schedule, ensure_ascii=False) if schedule else None,
            }
        )
    return header, parsed_rows


def _inventory_compact(item: CvcInventoryItem) -> CvcInventoryItemCompact:
    return CvcInventoryItemCompact(
        id=item.id,
        site_raw=item.site_raw,
        designation=item.designation,
        famille=item.famille,
        marque=item.marque,
        modele=item.modele,
        date_mis_en_service=item.date_mis_en_service,
        import_batch=item.import_batch,
    )


def _refrigerant_key(data: dict, parts: tuple[str, ...]) -> tuple[str, ...]:
    values: list[str] = []
    for part in parts:
        if part == "modele":
            values.append(_normalize_model(data.get("modele")))
        elif part == "date":
            values.append(str(data.get("date_mis_en_service") or ""))
        else:
            values.append(_normalize(data.get(part)))
    return tuple(values)


def _inventory_key(item: CvcInventoryItem, parts: tuple[str, ...]) -> tuple[str, ...]:
    values: list[str] = []
    for part in parts:
        if part == "modele":
            values.append(_normalize_model(item.modele))
        elif part == "date":
            values.append(str(item.date_mis_en_service or ""))
        else:
            values.append(_normalize(getattr(item, part)))
    return tuple(values)


def _score_inventory_candidate(data: dict, item: CvcInventoryItem) -> tuple[float, str] | None:
    if _normalize(data.get("site_raw")) != _normalize(item.site_raw):
        return None
    designation_score = _similarity(_normalize(data.get("designation")), _normalize(item.designation))
    model_left = _normalize_model(data.get("modele"))
    model_right = _normalize_model(item.modele)
    model_score = _similarity(model_left, model_right) if model_left and model_right else 0.0
    brand_score = _similarity(_normalize(data.get("marque")), _normalize(item.marque)) if data.get("marque") else 0.0
    score = round(designation_score * 0.65 + model_score * 0.25 + brand_score * 0.1, 3)
    return (score, "fuzzy_same_site") if score >= 0.82 else None


def _find_refrigerant_candidates(
    data: dict, inventory_items: list[CvcInventoryItem], limit: int = 5
) -> list[CvcRefrigerantMatchCandidate]:
    key_defs: list[tuple[str, tuple[str, ...], float]] = [
        ("site+designation+famille+marque+modele+date", ("site_raw", "designation", "famille", "marque", "modele", "date"), 1.0),
        ("site+designation+famille+modele+date", ("site_raw", "designation", "famille", "modele", "date"), 0.97),
        ("site+designation+modele+date", ("site_raw", "designation", "modele", "date"), 0.94),
        ("site+designation+marque+modele", ("site_raw", "designation", "marque", "modele"), 0.93),
    ]

    candidates: list[tuple[float, str, CvcInventoryItem]] = []
    for method, parts, score in key_defs:
        key = _refrigerant_key(data, parts)
        if not all(key):
            continue
        exact = [item for item in inventory_items if _inventory_key(item, parts) == key]
        if exact:
            candidates.extend((score, method, item) for item in exact)
            break

    if not candidates:
        for item in inventory_items:
            scored = _score_inventory_candidate(data, item)
            if scored:
                score, method = scored
                candidates.append((score, method, item))

    dedup: dict[int, tuple[float, str, CvcInventoryItem]] = {}
    for score, method, item in sorted(candidates, key=lambda row: row[0], reverse=True):
        dedup.setdefault(item.id, (score, method, item))

    return [
        CvcRefrigerantMatchCandidate(item=_inventory_compact(item), score=score, method=method)
        for score, method, item in list(dedup.values())[:limit]
    ]


def _select_auto_refrigerant_candidate(
    candidates: list[CvcRefrigerantMatchCandidate],
) -> CvcRefrigerantMatchCandidate | None:
    if not candidates:
        return None
    if candidates[0].score < 0.93:
        return None
    if len(candidates) > 1 and candidates[0].score == candidates[1].score:
        return None
    return candidates[0]


def _clear_current_cvc_inventory(db: Session, city_id: int | None) -> None:
    inventory_stmt = select(CvcInventoryItem)
    mapping_stmt = select(CvcSourceBuildingMapping).where(CvcSourceBuildingMapping.source_type == "inventory")
    refrigerant_stmt = select(CvcRefrigerantItem)
    if city_id is not None:
        inventory_stmt = inventory_stmt.where((CvcInventoryItem.city_id == city_id) | (CvcInventoryItem.city_id.is_(None)))
        mapping_stmt = mapping_stmt.where((CvcSourceBuildingMapping.city_id == city_id) | (CvcSourceBuildingMapping.city_id.is_(None)))
        refrigerant_stmt = refrigerant_stmt.where((CvcRefrigerantItem.city_id == city_id) | (CvcRefrigerantItem.city_id.is_(None)))

    for refrigerant in db.scalars(refrigerant_stmt):
        refrigerant.cvc_inventory_item_id = None
        refrigerant.match_status = "pending"
        refrigerant.match_method = None
        refrigerant.match_score = None

    for mapping in db.scalars(mapping_stmt):
        db.delete(mapping)
    for item in db.scalars(inventory_stmt):
        db.delete(item)
    db.flush()


def _refresh_refrigerant_inventory_links(db: Session, city_id: int | None) -> int:
    inventory_stmt = select(CvcInventoryItem)
    refrigerant_stmt = select(CvcRefrigerantItem)
    if city_id is not None:
        inventory_stmt = inventory_stmt.where((CvcInventoryItem.city_id == city_id) | (CvcInventoryItem.city_id.is_(None)))
        refrigerant_stmt = refrigerant_stmt.where((CvcRefrigerantItem.city_id == city_id) | (CvcRefrigerantItem.city_id.is_(None)))

    inventory_items = list(db.scalars(inventory_stmt))
    inventory_by_id = {item.id: item for item in inventory_items}
    relinked = 0
    for refrigerant in db.scalars(refrigerant_stmt):
        candidates = _find_refrigerant_candidates(
            {
                "site_raw": refrigerant.site_raw,
                "designation": refrigerant.designation,
                "famille": refrigerant.famille,
                "marque": refrigerant.marque,
                "modele": refrigerant.modele,
                "date_mis_en_service": refrigerant.date_mis_en_service,
            },
            inventory_items,
        )
        auto_candidate = _select_auto_refrigerant_candidate(candidates)
        if auto_candidate is None:
            refrigerant.cvc_inventory_item_id = None
            refrigerant.match_status = "ambiguous" if candidates else "pending"
            refrigerant.match_method = None
            refrigerant.match_score = None
            continue
        matched_inventory = inventory_by_id.get(auto_candidate.item.id)
        if matched_inventory is None:
            continue
        refrigerant.cvc_inventory_item_id = matched_inventory.id
        refrigerant.site_id = matched_inventory.site_id
        refrigerant.building_id = matched_inventory.building_id
        refrigerant.match_status = "auto_matched"
        refrigerant.match_method = auto_candidate.method
        refrigerant.match_score = auto_candidate.score
        if refrigerant.quantite_fluide_kg is not None:
            matched_inventory.quantite_fluide_frigorigene = refrigerant.quantite_fluide_kg
        relinked += 1
    return relinked


def _latest_inventory_batch(items: list[CvcInventoryItem]) -> str | None:
    batches: dict[str, float] = {}
    for item in items:
        if item.import_batch:
            created_at = item.created_at.timestamp() if item.created_at else 0.0
            current = batches.get(item.import_batch)
            if current is None or created_at < current:
                batches[item.import_batch] = created_at
    if not batches:
        return None
    return max(batches.items(), key=lambda item: item[1])[0]


def _filter_latest_inventory_batch(items: list[CvcInventoryItem]) -> list[CvcInventoryItem]:
    latest_batch = _latest_inventory_batch(items)
    if latest_batch is None:
        return []
    return [item for item in items if item.import_batch == latest_batch]


def match_buildings_for_sites(
    db: Session, sites: list[str], city_id: int | None
) -> CvcMatchBuildingsResponse:
    stmt = select(Building)
    if city_id is not None:
        stmt = stmt.where(Building.city_id == city_id)
    buildings = list(db.scalars(stmt))

    results = []
    for site in sites:
        scored: list[tuple[float, Building]] = []
        for b in buildings:
            name = b.nom_batiment or ""
            score = _similarity(site, name)
            scored.append((score, b))
        scored.sort(key=lambda x: x[0], reverse=True)

        top = scored[:5]
        suggestions = [
            BuildingMatchSuggestion(
                building_id=b.id,
                site_id=b.site_id,
                nom_batiment=b.nom_batiment,
                adresse=_build_address(b),
                score=round(s, 3),
            )
            for s, b in top
            if s > 0.1
        ]
        auto_id = top[0][1].id if top and top[0][0] >= 0.65 else None
        results.append(SiteMatchResult(site_raw=site, suggestions=suggestions, auto_selected_id=auto_id))

    return CvcMatchBuildingsResponse(matches=results)


def _best_current_id(values: list[int | None]) -> int | None:
    counts: dict[int, int] = {}
    for value in values:
        if value is not None:
            counts[value] = counts.get(value, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda item: item[1])[0]


def _create_or_reuse_cvc_placeholder_building(
    db: Session,
    source_name: str,
    city_id: int | None,
) -> Building:
    normalized_source = _normalize(source_name)
    stmt = select(Building).where(Building.source_creation == "CVC_IMPORT", Building.site_id.is_(None))
    if city_id is not None:
        stmt = stmt.where(Building.city_id == city_id)
    for building in db.scalars(stmt):
        if _normalize(building.nom_batiment) == normalized_source:
            return building

    city = db.get(City, city_id) if city_id is not None else None
    building = Building(
        city_id=city_id,
        site_id=None,
        nom_batiment=source_name[:255],
        nom_commune=city.nom_commune if city else "A qualifier",
        adresse_reconstituee=None,
        source_creation="CVC_IMPORT",
        statut_geocodage="NON_FAIT",
    )
    db.add(building)
    db.flush()
    return building


def _suggest_source_building(
    source_site_raw: str,
    sites: list[Site],
    buildings: list[Building],
) -> tuple[int | None, int | None, float | None, str | None]:
    site_scored = sorted(
        ((_similarity(source_site_raw, site.nom_site), site) for site in sites),
        key=lambda item: item[0],
        reverse=True,
    )
    building_scored = sorted(
        (
            (
                max(
                    _similarity(source_site_raw, building.nom_batiment or ""),
                    _similarity(source_site_raw, building.adresse_reconstituee or ""),
                ),
                building,
            )
            for building in buildings
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    if building_scored and building_scored[0][0] >= 0.72:
        building = building_scored[0][1]
        return building.site_id, building.id, round(building_scored[0][0], 3), "auto_building"
    if site_scored and site_scored[0][0] >= 0.72:
        site = site_scored[0][1]
        return site.id, None, round(site_scored[0][0], 3), "auto_site"
    return None, None, None, None


def _mapping_suggestions(
    source_site_raw: str,
    sites: list[Site],
    buildings: list[Building],
) -> tuple[list[PatrimoineSiteSuggestion], list[BuildingMatchSuggestion]]:
    site_scored = sorted(
        ((_similarity(source_site_raw, site.nom_site), site) for site in sites),
        key=lambda item: item[0],
        reverse=True,
    )
    building_scored = sorted(
        (
            (
                max(
                    _similarity(source_site_raw, building.nom_batiment or ""),
                    _similarity(source_site_raw, building.adresse_reconstituee or ""),
                ),
                building,
            )
            for building in buildings
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    site_suggestions = [
        PatrimoineSiteSuggestion(
            site_id=site.id,
            nom_site=site.nom_site,
            adresse=site.adresse,
            score=round(score, 3),
        )
        for score, site in site_scored[:5]
        if score > 0.1
    ]
    building_suggestions = [
        BuildingMatchSuggestion(
            building_id=building.id,
            site_id=building.site_id,
            nom_batiment=building.nom_batiment,
            adresse=_build_address(building),
            score=round(score, 3),
        )
        for score, building in building_scored[:5]
        if score > 0.1
    ]
    return site_suggestions, building_suggestions


def ensure_cvc_source_building_mappings(db: Session, city_id: int | None) -> int:
    sites_stmt = select(Site)
    buildings_stmt = select(Building)
    inventory_stmt = select(CvcInventoryItem)
    refrigerant_stmt = select(CvcRefrigerantItem)
    mapping_stmt = select(CvcSourceBuildingMapping)
    if city_id is not None:
        sites_stmt = sites_stmt.where(Site.city_id == city_id)
        buildings_stmt = buildings_stmt.where(Building.city_id == city_id)
        inventory_stmt = inventory_stmt.where((CvcInventoryItem.city_id == city_id) | (CvcInventoryItem.city_id.is_(None)))
        refrigerant_stmt = refrigerant_stmt.where((CvcRefrigerantItem.city_id == city_id) | (CvcRefrigerantItem.city_id.is_(None)))
        mapping_stmt = mapping_stmt.where((CvcSourceBuildingMapping.city_id == city_id) | (CvcSourceBuildingMapping.city_id.is_(None)))

    sites = list(db.scalars(sites_stmt))
    buildings = list(db.scalars(buildings_stmt))
    existing = {
        (mapping.source_type, mapping.import_batch, _normalize(mapping.source_site_raw))
        for mapping in db.scalars(mapping_stmt)
    }
    sources: set[tuple[str, str, str]] = set()
    for item in db.scalars(inventory_stmt):
        if item.import_batch and item.site_raw:
            sources.add(("inventory", item.import_batch, item.site_raw.strip()))
    for item in db.scalars(refrigerant_stmt):
        if item.import_batch and item.site_raw:
            sources.add(("refrigerant", item.import_batch, item.site_raw.strip()))

    created = 0
    created_mappings: list[CvcSourceBuildingMapping] = []
    for source_type, import_batch, source_site_raw in sorted(sources):
        key = (source_type, import_batch, _normalize(source_site_raw))
        if key in existing:
            continue
        site_id, building_id, score, method = _suggest_source_building(source_site_raw, sites, buildings)
        status = "matched" if site_id or building_id else "to_review"
        mapping = CvcSourceBuildingMapping(
            city_id=city_id,
            source_type=source_type,
            import_batch=import_batch,
            source_site_raw=source_site_raw,
            site_id=site_id,
            building_id=building_id,
            status=status,
            match_score=score,
            match_method=method,
        )
        db.add(mapping)
        created_mappings.append(mapping)
        created += 1
    if created:
        db.flush()
        for mapping in created_mappings:
            if mapping.status == "matched":
                _apply_source_mapping_to_rows(db, mapping)
        db.commit()
    return created


def _apply_source_mapping_to_rows(db: Session, mapping: CvcSourceBuildingMapping) -> int:
    updated = 0
    building = db.get(Building, mapping.building_id) if mapping.building_id is not None else None
    next_site_id = mapping.site_id if mapping.site_id is not None else (building.site_id if building else None)
    if mapping.source_type == "inventory":
        rows = list(
            db.scalars(
                select(CvcInventoryItem).where(
                    CvcInventoryItem.import_batch == mapping.import_batch,
                    CvcInventoryItem.site_raw == mapping.source_site_raw,
                )
            )
        )
        for item in rows:
            item.site_id = next_site_id
            item.building_id = building.id if building else None
            if building is None:
                item.local_id = None
            linked_refrigerants = list(
                db.scalars(select(CvcRefrigerantItem).where(CvcRefrigerantItem.cvc_inventory_item_id == item.id))
            )
            for refrigerant in linked_refrigerants:
                refrigerant.site_id = item.site_id
                refrigerant.building_id = item.building_id
            updated += 1
    elif mapping.source_type == "refrigerant":
        rows = list(
            db.scalars(
                select(CvcRefrigerantItem).where(
                    CvcRefrigerantItem.import_batch == mapping.import_batch,
                    CvcRefrigerantItem.site_raw == mapping.source_site_raw,
                )
            )
        )
        for item in rows:
            item.site_id = next_site_id
            item.building_id = building.id if building else None
            updated += 1
    return updated


def list_site_matches_for_import(
    db: Session, import_batch: str, city_id: int | None
) -> CvcImportSiteMatchResponse:
    stmt = select(CvcInventoryItem).where(CvcInventoryItem.import_batch == import_batch)
    if city_id is not None:
        stmt = stmt.where((CvcInventoryItem.city_id == city_id) | (CvcInventoryItem.city_id.is_(None)))
    items = _filter_latest_inventory_batch(list(db.scalars(stmt)))

    sites_stmt = select(Site)
    buildings_stmt = select(Building)
    if city_id is not None:
        sites_stmt = sites_stmt.where(Site.city_id == city_id)
        buildings_stmt = buildings_stmt.where(Building.city_id == city_id)
    patrimoine_sites = list(db.scalars(sites_stmt))
    buildings = list(db.scalars(buildings_stmt))

    grouped: dict[str, list[CvcInventoryItem]] = {}
    for item in items:
        key = (item.site_raw or "").strip()
        if key:
            grouped.setdefault(key, []).append(item)

    results: list[CvcImportSiteMatchResult] = []
    for site_raw, site_items in grouped.items():
        site_scored = sorted(
            ((_similarity(site_raw, site.nom_site), site) for site in patrimoine_sites),
            key=lambda item: item[0],
            reverse=True,
        )
        building_scored = sorted(
            (
                (
                    max(
                        _similarity(site_raw, building.nom_batiment or ""),
                        _similarity(site_raw, building.adresse_reconstituee or ""),
                    ),
                    building,
                )
                for building in buildings
            ),
            key=lambda item: item[0],
            reverse=True,
        )

        site_suggestions = [
            PatrimoineSiteSuggestion(
                site_id=site.id,
                nom_site=site.nom_site,
                adresse=site.adresse,
                score=round(score, 3),
            )
            for score, site in site_scored[:5]
            if score > 0.1
        ]
        building_suggestions = [
            BuildingMatchSuggestion(
                building_id=building.id,
                site_id=building.site_id,
                nom_batiment=building.nom_batiment,
                adresse=_build_address(building),
                score=round(score, 3),
            )
            for score, building in building_scored[:5]
            if score > 0.1
        ]

        auto_site_id = site_scored[0][1].id if site_scored and site_scored[0][0] >= 0.72 else None
        auto_building_id = building_scored[0][1].id if building_scored and building_scored[0][0] >= 0.72 else None
        if auto_building_id is not None and auto_site_id is None:
            auto_site_id = building_scored[0][1].site_id

        results.append(
            CvcImportSiteMatchResult(
                site_raw=site_raw,
                item_count=len(site_items),
                current_site_id=_best_current_id([item.site_id for item in site_items]),
                current_building_id=_best_current_id([item.building_id for item in site_items]),
                site_suggestions=site_suggestions,
                building_suggestions=building_suggestions,
                auto_site_id=auto_site_id,
                auto_building_id=auto_building_id,
            )
        )

    return CvcImportSiteMatchResponse(matches=sorted(results, key=lambda item: item.site_raw.lower()))


def apply_site_mappings_to_import(
    db: Session, import_batch: str, mappings: list[CvcSiteMapping], city_id: int | None
) -> CvcApplySiteMappingsResult:
    updated = 0
    applied = 0

    for mapping in mappings:
        site_raw = mapping.site_raw.strip()
        if not site_raw:
            continue

        create_building = bool(mapping.create_building)
        site = None if create_building else (db.get(Site, mapping.site_id) if mapping.site_id is not None else None)
        if not create_building and mapping.site_id is not None and site is None:
            raise ValueError(f"Site introuvable pour {site_raw}.")
        if site and city_id is not None and site.city_id != city_id:
            raise ValueError(f"Site hors perimetre pour {site_raw}.")

        building = (
            _create_or_reuse_cvc_placeholder_building(db, site_raw, city_id)
            if create_building
            else (db.get(Building, mapping.building_id) if mapping.building_id is not None else None)
        )
        if not create_building and mapping.building_id is not None and building is None:
            raise ValueError(f"Batiment introuvable pour {site_raw}.")
        if building and city_id is not None and building.city_id != city_id:
            raise ValueError(f"Batiment hors perimetre pour {site_raw}.")

        next_site_id = None if create_building else (site.id if site else (building.site_id if building else None))
        if building and site and building.site_id not in (None, site.id):
            raise ValueError(f"Le batiment choisi n'appartient pas au site choisi pour {site_raw}.")

        stmt = select(CvcInventoryItem).where(
            CvcInventoryItem.import_batch == import_batch,
            CvcInventoryItem.site_raw == site_raw,
        )
        if city_id is not None:
            stmt = stmt.where((CvcInventoryItem.city_id == city_id) | (CvcInventoryItem.city_id.is_(None)))
        items = list(db.scalars(stmt))
        if not items:
            continue

        for item in items:
            building_changed = item.building_id != (building.id if building else None)
            item.site_id = next_site_id
            item.building_id = building.id if building else None
            if building_changed:
                item.local_id = None
            linked_refrigerants = list(
                db.scalars(select(CvcRefrigerantItem).where(CvcRefrigerantItem.cvc_inventory_item_id == item.id))
            )
            for refrigerant in linked_refrigerants:
                refrigerant.site_id = item.site_id
                refrigerant.building_id = item.building_id
            updated += 1
        applied += 1

    db.commit()
    return CvcApplySiteMappingsResult(updated=updated, mappings_applied=applied)


def _find_ref(
    all_refs: list[EquipmentReference],
    *,
    id_ligne: int | None = None,
    equipment_contains: str | None = None,
    code_niveau_2: str | None = None,
) -> EquipmentReference | None:
    normalized_contains = _normalize(equipment_contains)
    for ref in all_refs:
        if id_ligne is not None and ref.id_ligne != id_ligne:
            continue
        if code_niveau_2 is not None and ref.code_niveau_2 != code_niveau_2:
            continue
        if normalized_contains and normalized_contains not in _normalize(ref.equipement):
            continue
        return ref
    return None


def _resolve_alias_reference(
    famille: str | None,
    designation: str | None,
    marque: str | None,
    modele: str | None,
    all_refs: list[EquipmentReference],
) -> EquipmentReference | None:
    family = _normalize(famille)
    text = _combined_item_text(famille, designation, marque, modele)

    if family in {"analyseur", "appareil de mesure", "compteur", "plomberie"}:
        return None

    if "armoire electrique" in family or "tableau electrique" in text or "coffret electrique" in text:
        return _find_ref(all_refs, id_ligne=118, equipment_contains="Armoire électrique")

    if family in {"centrale traitement air"} or "cta" in text or "centrale traitement air" in text:
        return _find_ref(all_refs, id_ligne=221, equipment_contains="CTA")

    if family == "chaudiere":
        if "murale" in text:
            return _find_ref(all_refs, id_ligne=169, equipment_contains="Chaudi")
        return _find_ref(all_refs, id_ligne=163, equipment_contains="Chaudi")

    if family in {"preparateur ecs", "ballon de stockage"}:
        return _find_ref(all_refs, id_ligne=97, equipment_contains="Ballon")

    if family == "vase expansion" or "vase d expansion" in text or "vase expansion" in text:
        return _find_ref(all_refs, id_ligne=188, equipment_contains="Vase")

    if family == "gtb / gtc" or re.search(r"\bgtb\b|\bgtc\b", text):
        return _find_ref(all_refs, id_ligne=162, equipment_contains="GTB")

    if family == "circulateur":
        return _find_ref(all_refs, id_ligne=186, equipment_contains="Circulateur")

    if family == "echangeur":
        if "froid" in text or "glacee" in text:
            return _find_ref(all_refs, id_ligne=213, equipment_contains="Echangeur")
        return _find_ref(all_refs, id_ligne=179, equipment_contains="Echangeur")

    if family == "robinet / vanne" or "vanne" in text or "robinet" in text:
        return _find_ref(all_refs, id_ligne=181, equipment_contains="Vannes")

    if family in {"pompe a chaleur", "groupe thermodynamique"} or (
        family in {"", "autre a qualifier"} and ("pac" in text or "thermodynamique" in text)
    ):
        return _find_ref(all_refs, id_ligne=238, equipment_contains="PAC")

    split_keywords = [
        "mono-split",
        "monosplit",
        "multi-split",
        "multisplit",
        "split",
        "ue clim",
        "ui clim",
        "unite interieure",
        "unite exterieure",
        "climatisation",
        "climatiseur",
        "cassette",
        "vrv",
        "drv",
    ]
    split_like = any(token in text for token in split_keywords)
    if family in {"split system", "vrv", "systeme vrv", "climatiseur", "cassette"} or (
        family in {"", "autre a qualifier"} and split_like
    ):
        if "armoire de climatisation" in text or "roof" in text:
            return _find_ref(all_refs, id_ligne=237, equipment_contains="Armoires autonomes")
        return _find_ref(all_refs, id_ligne=236, equipment_contains="Split")

    if family in {"groupe froid"} or "groupe froid" in text:
        return _find_ref(all_refs, id_ligne=207, equipment_contains="Groupe")

    if family == "aerotherme" or "aerotherme" in text:
        return _find_ref(all_refs, id_ligne=201, equipment_contains="Aérothermes") or _find_ref(
            all_refs, id_ligne=219, equipment_contains="Rideau"
        )

    if family == "bouches de soufflage" or "bouche" in text:
        return _find_ref(all_refs, id_ligne=223, equipment_contains="Gaine")

    if family == "ventilation":
        if "desenfum" in text:
            return _find_ref(all_refs, id_ligne=244, equipment_contains="Ventilateurs")
        if "vmc" in text or "extract" in text or "ventil" in text:
            return _find_ref(all_refs, id_ligne=233, equipment_contains="Ventilateur")
        return None

    if family == "filtre":
        if "sable" in text or "piscine" in text:
            return _find_ref(all_refs, id_ligne=92, equipment_contains="Filtre")
        if "pot a boue" in text or "chauffage" in text or "vanne" in text:
            return _find_ref(all_refs, id_ligne=181, equipment_contains="filtres")
        return None

    if family == "pompe":
        if "doseuse" in text:
            return _find_ref(all_refs, id_ligne=91, equipment_contains="Pompe doseuse")
        if "froid" in text or "glacee" in text:
            return _find_ref(all_refs, id_ligne=214, equipment_contains="Pompes")
        if "chauffage" in text or "circulateur" in text or "radiateur" in text:
            return _find_ref(all_refs, id_ligne=186, equipment_contains="Circulateur")
        return None

    if family == "batterie":
        if "chaude" in text or "froide" in text or "cta" in text:
            return _find_ref(all_refs, id_ligne=221, equipment_contains="CTA")
        return None

    if family == "regulation":
        return _find_ref(all_refs, id_ligne=200, equipment_contains="régulation")

    if family == "tube radiant":
        return _find_ref(all_refs, id_ligne=194, equipment_contains="Radiateur")

    return None


def _resolve_family(
    famille: str | None,
    all_refs: list[EquipmentReference],
    cache: dict,
    designation: str | None = None,
    marque: str | None = None,
    modele: str | None = None,
) -> EquipmentReference | None:
    if not famille:
        return None
    cache_key = (
        _normalize(famille),
        _normalize(designation),
        _normalize(marque),
        _normalize(modele),
    )
    if cache_key in cache:
        return cache[cache_key]

    alias_ref = _resolve_alias_reference(famille, designation, marque, modele, all_refs)
    if alias_ref is not None:
        cache[cache_key] = alias_ref
        return alias_ref

    normalized_family = _normalize(famille)
    if normalized_family in NO_FUZZY_FAMILIES:
        cache[cache_key] = None
        return None

    best_score = 0.0
    best_ref = None
    for ref in all_refs:
        if ref.code_niveau_2 not in ALLOWED_CVC_REFERENCE_DOMAINS:
            continue
        score = max(
            _similarity(normalized_family, _normalize(ref.equipement)),
            _similarity(normalized_family, _normalize(ref.niveau_4)),
        )
        if score > best_score:
            best_score = score
            best_ref = ref
    result = best_ref if best_score >= 0.72 else None
    cache[cache_key] = result
    return result


def _requires_refrigerant_quantity(ref: EquipmentReference | None) -> bool:
    return bool(ref and ref.niveau_3 in REFRIGERANT_NIVEAU_3)


def _health_age_ratio(etat_sante: str | None) -> float | None:
    normalized = _normalize(etat_sante)
    if not normalized:
        return None
    for key, ratio in HEALTH_AGE_RATIOS.items():
        if key in normalized:
            return ratio
    return None


def _compute_lifecycle(
    date_mes: int | None,
    ref: EquipmentReference | None,
    etat_sante: str | None = None,
) -> tuple[float | None, float | None, str, str | None]:
    if not ref or not ref.sypemi_reference_annees:
        return None, None, "missing", "Reference duree de vie absente"

    if date_mes:
        age = max(0, CURRENT_YEAR - date_mes)
        return (
            round(ref.sypemi_reference_annees - age, 1),
            round(age, 1),
            "date_mes",
            "Calcule depuis DATE MES",
        )

    ratio = _health_age_ratio(etat_sante)
    if ratio is not None:
        age = round(ref.sypemi_reference_annees * ratio, 1)
        return (
            round(ref.sypemi_reference_annees - age, 1),
            age,
            "etat_sante",
            f"DATE MES absente, estime depuis ETAT SANTE : {etat_sante}",
        )

    return None, None, "missing", "DATE MES et ETAT SANTE exploitables absents"


def _compute_remaining_life(
    date_mes: int | None,
    ref: EquipmentReference | None,
    etat_sante: str | None = None,
) -> float | None:
    remaining, _, _, _ = _compute_lifecycle(date_mes, ref, etat_sante)
    return remaining


def _read_item(item: CvcInventoryItem, ref: EquipmentReference | None) -> CvcInventoryItemRead:
    sypemi_years = ref.sypemi_reference_annees if ref else None
    remaining_life, lifecycle_age, lifecycle_source, lifecycle_label = _compute_lifecycle(
        item.date_mis_en_service,
        ref,
        item.etat_sante,
    )

    criticite_pct = None
    if lifecycle_age is not None and sypemi_years and sypemi_years > 0:
        criticite_pct = min(100.0, round(lifecycle_age / sypemi_years * 100, 1))

    read = CvcInventoryItemRead.model_validate(item)
    read.duree_vie_restante = remaining_life
    read.lifecycle_age_years = lifecycle_age
    read.lifecycle_age_source = lifecycle_source
    read.lifecycle_age_label = lifecycle_label
    read.criticite_pct = criticite_pct
    read.sypemi_reference_annees = sypemi_years
    read.sypemi_mini_annees = ref.sypemi_mini_annees if ref else None
    read.sypemi_maxi_annees = ref.sypemi_maxi_annees if ref else None
    read.requires_refrigerant_quantity = _requires_refrigerant_quantity(ref)
    read.equipment_ref = CvcEquipmentReferenceRead.model_validate(ref) if ref else None
    return read


def import_cvc_from_excel(
    db: Session,
    raw_bytes: bytes,
    building_mappings: list[CvcBuildingMapping],
    city_id: int | None,
    import_batch: str | None = None,
) -> CvcImportResult:
    mapping_dict = {m.site_raw: m.building_id for m in building_mappings}
    batch_id = import_batch or f"import_{uuid.uuid4().hex[:8]}"

    wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return CvcImportResult(
            imported=0, skipped=0, errors=[], import_batch=batch_id, sypemi_matched=0, sypemi_unmatched=0
        )

    header = [str(c) if c is not None else "" for c in rows[0]]
    col_idx = {col: i for i, col in enumerate(header) if col}

    def get_val(row: tuple, col_name: str):
        idx = col_idx.get(col_name)
        if idx is None or idx >= len(row):
            return None
        return row[idx]

    all_refs = list(db.scalars(select(EquipmentReference)))
    family_cache: dict = {}

    _clear_current_cvc_inventory(db, city_id)

    imported = 0
    skipped = 0
    errors: list[str] = []
    sypemi_matched = 0
    sypemi_unmatched = 0

    for row in rows[1:]:
        if not any(v is not None for v in row):
            continue

        designation_raw = get_val(row, "DESIGNATION")
        designation = str(designation_raw).strip() if designation_raw else ""
        if not designation:
            skipped += 1
            continue

        site_raw = get_val(row, "SITE")
        site = str(site_raw).strip() if site_raw else ""
        building_id = mapping_dict.get(site)
        building = db.get(Building, building_id) if building_id is not None else None

        def clean(col: str) -> str | None:
            v = get_val(row, col)
            s = str(v).strip() if v is not None else ""
            return s or None

        famille_raw = get_val(row, "FAMILLE")
        famille = str(famille_raw).strip() if famille_raw else None
        marque = clean("MARQUE")
        modele = clean("MODELE")
        ref = _resolve_family(famille, all_refs, family_cache, designation, marque, modele)

        date_raw = get_val(row, "DATE MES")
        try:
            date_mes = int(date_raw) if date_raw is not None else None
        except (ValueError, TypeError):
            date_mes = None

        etat_sante = clean("ETAT SANTE")
        duree_vie_restante = _compute_remaining_life(date_mes, ref, etat_sante)

        qte_raw = get_val(row, "QTE QTE RELEVEE")
        try:
            quantite_relevee = int(qte_raw) if qte_raw is not None else None
        except (ValueError, TypeError):
            quantite_relevee = None

        item = CvcInventoryItem(
            city_id=city_id,
            site_id=building.site_id if building else None,
            building_id=building_id,
            local_id=None,
            equipment_ref_id=ref.id if ref else None,
            site_raw=site or None,
            batiment=clean("BATIMENT"),
            niveau=clean("NIVEAU"),
            local_name=clean("LOCAL"),
            designation=designation,
            statut=clean("STATUT"),
            etat_sante=etat_sante,
            quantite_relevee=quantite_relevee,
            famille=famille,
            marque=marque,
            modele=modele,
            date_mis_en_service=date_mes,
            duree_vie_restante=duree_vie_restante,
            quantite_fluide_frigorigene=None,
            import_batch=batch_id,
        )
        db.add(item)

        if ref:
            sypemi_matched += 1
        else:
            sypemi_unmatched += 1
        imported += 1

    db.flush()
    _refresh_refrigerant_inventory_links(db, city_id)
    db.commit()
    ensure_cvc_source_building_mappings(db, city_id)
    return CvcImportResult(
        imported=imported,
        skipped=skipped,
        errors=errors,
        import_batch=batch_id,
        sypemi_matched=sypemi_matched,
        sypemi_unmatched=sypemi_unmatched,
    )


def list_cvc_import_batches(db: Session, city_id: int | None) -> list[CvcImportBatchSummary]:
    stmt = select(CvcInventoryItem)
    if city_id is not None:
        stmt = stmt.where((CvcInventoryItem.city_id == city_id) | (CvcInventoryItem.city_id.is_(None)))
    items = list(db.scalars(stmt))
    batches: dict[str, list[CvcInventoryItem]] = {}
    for item in items:
        if item.import_batch:
            batches.setdefault(item.import_batch, []).append(item)

    ref_ids = {item.equipment_ref_id for item in items if item.equipment_ref_id}
    refrigerant_ref_ids: set[int] = set()
    if ref_ids:
        refs = db.scalars(select(EquipmentReference).where(EquipmentReference.id.in_(ref_ids)))
        refrigerant_ref_ids = {ref.id for ref in refs if _requires_refrigerant_quantity(ref)}

    summaries = []
    for batch, batch_items in batches.items():
        summaries.append(
            CvcImportBatchSummary(
                import_batch=batch,
                imported=len(batch_items),
                mapped_items=sum(1 for item in batch_items if item.building_id is not None),
                reference_mapped_items=sum(1 for item in batch_items if item.equipment_ref_id is not None),
                refrigerant_items=sum(1 for item in batch_items if item.equipment_ref_id in refrigerant_ref_ids),
                created_at=min((item.created_at for item in batch_items), default=None),
            )
        )
    return sorted(summaries, key=lambda b: b.created_at or datetime.min, reverse=True)


def list_cvc_items_for_batch(
    db: Session, import_batch: str, city_id: int | None
) -> list[CvcInventoryItemRead]:
    stmt = select(CvcInventoryItem).where(CvcInventoryItem.import_batch == import_batch)
    if city_id is not None:
        stmt = stmt.where((CvcInventoryItem.city_id == city_id) | (CvcInventoryItem.city_id.is_(None)))
    items = list(db.scalars(stmt.order_by(CvcInventoryItem.site_raw, CvcInventoryItem.designation)))
    return _hydrate_items(db, items)


def recompute_cvc_references_for_batch(
    db: Session, import_batch: str, city_id: int | None
) -> CvcRecomputeReferencesResult:
    stmt = select(CvcInventoryItem).where(CvcInventoryItem.import_batch == import_batch)
    if city_id is not None:
        stmt = stmt.where((CvcInventoryItem.city_id == city_id) | (CvcInventoryItem.city_id.is_(None)))
    items = list(db.scalars(stmt))
    all_refs = list(db.scalars(select(EquipmentReference)))
    family_cache: dict = {}

    updated = 0
    changed = 0
    matched = 0
    unmatched = 0
    for item in items:
        next_ref = _resolve_family(
            item.famille,
            all_refs,
            family_cache,
            item.designation,
            item.marque,
            item.modele,
        )
        next_ref_id = next_ref.id if next_ref else None
        if item.equipment_ref_id != next_ref_id:
            changed += 1
        item.equipment_ref_id = next_ref_id
        item.duree_vie_restante = _compute_remaining_life(item.date_mis_en_service, next_ref, item.etat_sante)
        if not _requires_refrigerant_quantity(next_ref):
            item.quantite_fluide_frigorigene = None
        if next_ref:
            matched += 1
        else:
            unmatched += 1
        updated += 1

    db.commit()
    return CvcRecomputeReferencesResult(
        import_batch=import_batch,
        updated=updated,
        matched=matched,
        unmatched=unmatched,
        changed=changed,
    )


def import_cvc_refrigerants_from_excel(
    db: Session,
    raw_bytes: bytes,
    city_id: int | None,
    source_filename: str | None = None,
) -> CvcRefrigerantImportResult:
    _, rows = _read_refrigerant_rows(raw_bytes)
    batch_id = f"esp_{uuid.uuid4().hex[:8]}"
    inventory_stmt = select(CvcInventoryItem)
    if city_id is not None:
        inventory_stmt = inventory_stmt.where(
            (CvcInventoryItem.city_id == city_id) | (CvcInventoryItem.city_id.is_(None))
        )
    inventory_items = list(db.scalars(inventory_stmt))

    imported = 0
    auto_matched = 0
    ambiguous = 0
    total_fluide_kg = 0.0
    total_teqco2 = 0.0

    for row in rows:
        candidates = _find_refrigerant_candidates(row, inventory_items)
        auto_candidate = _select_auto_refrigerant_candidate(candidates)
        match_status = "pending"
        match_method = None
        match_score = None
        inventory_item_id = None

        if auto_candidate:
            match_status = "auto_matched"
            match_method = auto_candidate.method
            match_score = auto_candidate.score
            inventory_item_id = auto_candidate.item.id
        elif candidates:
            match_status = "ambiguous"
            ambiguous += 1
        matched_inventory = next((i for i in inventory_items if i.id == inventory_item_id), None)

        item = CvcRefrigerantItem(
            city_id=city_id,
            site_id=matched_inventory.site_id if matched_inventory else None,
            building_id=matched_inventory.building_id if matched_inventory else None,
            cvc_inventory_item_id=inventory_item_id,
            import_batch=batch_id,
            source_filename=source_filename,
            row_number=row["row_number"],
            site_raw=row["site_raw"],
            designation=row["designation"],
            quantite_relevee=row["quantite_relevee"],
            famille=row["famille"],
            marque=row["marque"],
            modele=row["modele"],
            fluide_frigorigene=row["fluide_frigorigene"],
            quantite_fluide_kg=row["quantite_fluide_kg"],
            puissance_froid_kw=row["puissance_froid_kw"],
            date_mis_en_service=row["date_mis_en_service"],
            gwp=row["gwp"],
            teqco2=row["teqco2"],
            esp_status=row["esp_status"],
            cout_desp_date_eur=row["cout_desp_date_eur"],
            cumul_5_ans_eur=row["cumul_5_ans_eur"],
            schedule_json=row["schedule_json"],
            match_status=match_status,
            match_method=match_method,
            match_score=match_score,
        )
        db.add(item)

        if inventory_item_id is not None:
            if matched_inventory is not None and row["quantite_fluide_kg"] is not None:
                matched_inventory.quantite_fluide_frigorigene = row["quantite_fluide_kg"]
            auto_matched += 1
        total_fluide_kg += row["quantite_fluide_kg"] or 0.0
        total_teqco2 += row["teqco2"] or 0.0
        imported += 1

    db.commit()
    ensure_cvc_source_building_mappings(db, city_id)
    return CvcRefrigerantImportResult(
        import_batch=batch_id,
        imported=imported,
        auto_matched=auto_matched,
        pending=imported - auto_matched - ambiguous,
        ambiguous=ambiguous,
        total_fluide_kg=round(total_fluide_kg, 3),
        total_teqco2=round(total_teqco2, 3),
    )


def list_cvc_refrigerant_batches(db: Session, city_id: int | None) -> list[CvcRefrigerantBatchSummary]:
    stmt = select(CvcRefrigerantItem)
    if city_id is not None:
        stmt = stmt.where((CvcRefrigerantItem.city_id == city_id) | (CvcRefrigerantItem.city_id.is_(None)))
    items = list(db.scalars(stmt))
    batches: dict[str, list[CvcRefrigerantItem]] = defaultdict(list)
    for item in items:
        batches[item.import_batch].append(item)

    summaries: list[CvcRefrigerantBatchSummary] = []
    for import_batch, batch_items in batches.items():
        summaries.append(
            CvcRefrigerantBatchSummary(
                import_batch=import_batch,
                source_filename=next((item.source_filename for item in batch_items if item.source_filename), None),
                imported=len(batch_items),
                matched_items=sum(1 for item in batch_items if item.cvc_inventory_item_id is not None),
                pending_items=sum(1 for item in batch_items if item.cvc_inventory_item_id is None),
                total_fluide_kg=round(sum(item.quantite_fluide_kg or 0.0 for item in batch_items), 3),
                total_teqco2=round(sum(item.teqco2 or 0.0 for item in batch_items), 3),
                created_at=min((item.created_at for item in batch_items), default=None),
            )
        )
    return sorted(summaries, key=lambda item: item.created_at or datetime.min, reverse=True)


def get_cvc_refrigerant_dashboard(db: Session, city_id: int | None) -> CvcRefrigerantDashboard:
    stmt = select(CvcRefrigerantItem)
    if city_id is not None:
        stmt = stmt.where((CvcRefrigerantItem.city_id == city_id) | (CvcRefrigerantItem.city_id.is_(None)))
    items = list(db.scalars(stmt.order_by(CvcRefrigerantItem.created_at.desc(), CvcRefrigerantItem.site_raw)))
    batches = list_cvc_refrigerant_batches(db, city_id) if items else []
    latest_batch = batches[0] if batches else None

    status_counts: dict[str, int] = {}
    conformity_counts: dict[str, int] = {}
    priority_counts: dict[str, int] = {}
    open_actions: list[CvcRefrigerantActionSummary] = []
    esp_signals: list[CvcRefrigerantActionSummary] = []

    for item in items:
        computed = _computed_refrigerant_fields(item)
        fgas_status = str(computed["fgas_status"])
        conformity = str(computed["statut_conformite"])
        priority = str(computed["priorite"])
        status_counts[fgas_status] = status_counts.get(fgas_status, 0) + 1
        conformity_counts[conformity] = conformity_counts.get(conformity, 0) + 1
        priority_counts[priority] = priority_counts.get(priority, 0) + 1

        if conformity not in {"OK", "Non prioritaire"}:
            open_actions.append(
                _action_summary(
                    item,
                    "F-Gaz",
                    f"{fgas_status} : {conformity}",
                )
            )
        if _normalize(item.esp_status) in {"soumis", "manque de donnee"}:
            esp_signals.append(
                _action_summary(
                    item,
                    "ESP/DESP",
                    f"Statut source ESP : {item.esp_status or 'Non renseigné'}",
                    "Récupérer dossier ESP, PV IP/RP, prochaine échéance et preuve LUNE si applicable",
                )
            )

    priority_order = {"Haute": 0, "Moyenne": 1, "Basse": 2}
    open_actions.sort(key=lambda action: (priority_order.get(action.priority, 9), action.echeance_cible or date.max, action.site or ""))
    esp_signals.sort(key=lambda action: (priority_order.get(action.priority, 9), action.site or "", action.equipment))

    missing_data = sum(1 for item in items if item.teqco2 is None or not item.fluide_frigorigene or item.quantite_fluide_kg is None or item.gwp is None)
    over_5 = sum(1 for item in items if item.teqco2 is not None and item.teqco2 >= 5)
    over_50 = sum(1 for item in items if item.teqco2 is not None and item.teqco2 >= 50)
    overdue_or_due = sum(
        1
        for item in items
        if str(_computed_refrigerant_fields(item)["statut_conformite"]) in {"En retard", "À programmer < 60 j"}
    )
    last_check_missing = sum(
        1 for item in items if str(_computed_refrigerant_fields(item)["statut_conformite"]) == "Dernier contrôle à demander"
    )
    unmapped = sum(1 for item in items if item.cvc_inventory_item_id is None)

    kpis = [
        CvcRefrigerantDashboardKpi(key="items", label="Équipements inventoriés", value=len(items), helper="Lignes fluides ESP importées"),
        CvcRefrigerantDashboardKpi(key="fgas", label="À suivre F-Gaz ≥ 5 t", value=over_5, tone="warning", helper="Contrôle périodique requis"),
        CvcRefrigerantDashboardKpi(key="fgas50", label="≥ 50 t éq. CO2", value=over_50, tone="danger", helper="Priorité renforcée"),
        CvcRefrigerantDashboardKpi(key="missing", label="Données à compléter", value=missing_data, tone="danger", helper="Fluide, charge ou GWP absent"),
        CvcRefrigerantDashboardKpi(key="check_missing", label="Contrôle à demander", value=last_check_missing, tone="warning", helper="Dernier contrôle non renseigné"),
        CvcRefrigerantDashboardKpi(key="due", label="À programmer / retard", value=overdue_or_due, tone="danger", helper="Échéance dépassée ou proche"),
        CvcRefrigerantDashboardKpi(key="esp", label="Signaux ESP", value=len(esp_signals), tone="warning", helper="Dossier ESP/DESP à suivre à part"),
        CvcRefrigerantDashboardKpi(key="unmapped", label="Non rattachés CVC", value=unmapped, tone="warning", helper="Lien équipement à valider"),
    ]

    return CvcRefrigerantDashboard(
        total_items=len(items),
        latest_batch=latest_batch.import_batch if latest_batch else None,
        latest_batch_label=latest_batch.source_filename if latest_batch else None,
        kpis=kpis,
        status_counts=status_counts,
        conformity_counts=conformity_counts,
        priority_counts=priority_counts,
        open_actions=open_actions[:80],
        esp_signals=esp_signals[:80],
    )


def _read_refrigerant_item(
    item: CvcRefrigerantItem,
    inventory_map: dict[int, CvcInventoryItem],
    inventory_items: list[CvcInventoryItem],
) -> CvcRefrigerantItemRead:
    read = CvcRefrigerantItemRead.model_validate(item)
    read.schedule = json.loads(item.schedule_json) if item.schedule_json else {}
    computed = _computed_refrigerant_fields(item)
    read.fgas_status = str(computed["fgas_status"])
    read.frequence_controle_mois = computed["frequence_controle_mois"] if isinstance(computed["frequence_controle_mois"], int) else None
    read.statut_conformite = str(computed["statut_conformite"])
    read.action_prioritaire = str(computed["action_prioritaire"])
    read.preuve_attendue = str(computed["preuve_attendue"])
    read.priorite = str(computed["priorite"])
    if item.cvc_inventory_item_id:
        matched = inventory_map.get(item.cvc_inventory_item_id)
        read.matched_inventory_item = _inventory_compact(matched) if matched else None
    read.candidates = _find_refrigerant_candidates(
        {
            "site_raw": item.site_raw,
            "designation": item.designation,
            "famille": item.famille,
            "marque": item.marque,
            "modele": item.modele,
            "date_mis_en_service": item.date_mis_en_service,
        },
        inventory_items,
    )
    return read


def list_cvc_refrigerant_items_for_batch(
    db: Session, import_batch: str, city_id: int | None
) -> list[CvcRefrigerantItemRead]:
    stmt = select(CvcRefrigerantItem).where(CvcRefrigerantItem.import_batch == import_batch)
    inventory_stmt = select(CvcInventoryItem)
    if city_id is not None:
        stmt = stmt.where((CvcRefrigerantItem.city_id == city_id) | (CvcRefrigerantItem.city_id.is_(None)))
        inventory_stmt = inventory_stmt.where(
            (CvcInventoryItem.city_id == city_id) | (CvcInventoryItem.city_id.is_(None))
        )
    items = list(db.scalars(stmt.order_by(CvcRefrigerantItem.site_raw, CvcRefrigerantItem.designation)))
    inventory_items = list(db.scalars(inventory_stmt))
    inventory_map = {item.id: item for item in inventory_items}
    return [_read_refrigerant_item(item, inventory_map, inventory_items) for item in items]


def update_cvc_refrigerant_item(
    db: Session,
    item_id: int,
    payload: CvcRefrigerantItemUpdate,
    city_id: int | None,
) -> CvcRefrigerantItemRead | None:
    item = db.scalar(select(CvcRefrigerantItem).where(CvcRefrigerantItem.id == item_id))
    if not item:
        return None
    if city_id is not None and item.city_id not in (None, city_id):
        return None

    updates = payload.model_dump(exclude_unset=True)
    inventory_item = None
    if "cvc_inventory_item_id" in updates and payload.cvc_inventory_item_id is not None:
        inventory_item = db.get(CvcInventoryItem, payload.cvc_inventory_item_id)
        if inventory_item is None:
            raise ValueError("Equipement CVC introuvable.")
        if city_id is not None and inventory_item.city_id not in (None, city_id):
            raise ValueError("Equipement CVC hors perimetre utilisateur.")

    if "cvc_inventory_item_id" in updates:
        item.cvc_inventory_item_id = inventory_item.id if inventory_item else None
        item.site_id = inventory_item.site_id if inventory_item else payload.site_id
        item.building_id = inventory_item.building_id if inventory_item else payload.building_id
        item.match_status = "manual_matched" if inventory_item else "pending"
        item.match_method = "manual" if inventory_item else None
        item.match_score = 1.0 if inventory_item else None
        if inventory_item and item.quantite_fluide_kg is not None:
            inventory_item.quantite_fluide_frigorigene = item.quantite_fluide_kg
    else:
        if "site_id" in updates:
            item.site_id = payload.site_id
        if "building_id" in updates:
            item.building_id = payload.building_id

    for field in (
        "detection_permanente",
        "dernier_controle_etancheite",
        "prochaine_echeance",
        "titulaire",
        "responsable_collectivite",
        "statut_action",
        "commentaire_gmao",
    ):
        if field in updates:
            setattr(item, field, updates[field])

    db.commit()
    db.refresh(item)

    inventory_stmt = select(CvcInventoryItem)
    if city_id is not None:
        inventory_stmt = inventory_stmt.where(
            (CvcInventoryItem.city_id == city_id) | (CvcInventoryItem.city_id.is_(None))
        )
    inventory_items = list(db.scalars(inventory_stmt))
    inventory_map = {inventory.id: inventory for inventory in inventory_items}
    return _read_refrigerant_item(item, inventory_map, inventory_items)


def list_cvc_source_building_mappings(
    db: Session,
    city_id: int | None,
    source_type: str | None = None,
    import_batch: str | None = None,
) -> list[CvcSourceBuildingMappingRead]:
    ensure_cvc_source_building_mappings(db, city_id)
    stmt = select(CvcSourceBuildingMapping)
    sites_stmt = select(Site)
    buildings_stmt = select(Building)
    if city_id is not None:
        stmt = stmt.where((CvcSourceBuildingMapping.city_id == city_id) | (CvcSourceBuildingMapping.city_id.is_(None)))
        sites_stmt = sites_stmt.where(Site.city_id == city_id)
        buildings_stmt = buildings_stmt.where(Building.city_id == city_id)
    if source_type:
        stmt = stmt.where(CvcSourceBuildingMapping.source_type == source_type)
    if import_batch:
        stmt = stmt.where(CvcSourceBuildingMapping.import_batch == import_batch)

    mappings = list(db.scalars(stmt.order_by(CvcSourceBuildingMapping.source_type, CvcSourceBuildingMapping.source_site_raw)))
    sites = list(db.scalars(sites_stmt))
    buildings = list(db.scalars(buildings_stmt))

    inventory_counts: dict[tuple[str, str], int] = {}
    refrigerant_counts: dict[tuple[str, str], int] = {}
    inventory_stmt = select(CvcInventoryItem)
    refrigerant_stmt = select(CvcRefrigerantItem)
    if city_id is not None:
        inventory_stmt = inventory_stmt.where((CvcInventoryItem.city_id == city_id) | (CvcInventoryItem.city_id.is_(None)))
        refrigerant_stmt = refrigerant_stmt.where((CvcRefrigerantItem.city_id == city_id) | (CvcRefrigerantItem.city_id.is_(None)))
    for item in db.scalars(inventory_stmt):
        if item.import_batch and item.site_raw:
            key = (item.import_batch, item.site_raw.strip())
            inventory_counts[key] = inventory_counts.get(key, 0) + 1
    for item in db.scalars(refrigerant_stmt):
        if item.import_batch and item.site_raw:
            key = (item.import_batch, item.site_raw.strip())
            refrigerant_counts[key] = refrigerant_counts.get(key, 0) + 1

    results: list[CvcSourceBuildingMappingRead] = []
    for mapping in mappings:
        site_suggestions, building_suggestions = _mapping_suggestions(mapping.source_site_raw, sites, buildings)
        read = CvcSourceBuildingMappingRead.model_validate(mapping)
        read.site_suggestions = site_suggestions
        read.building_suggestions = building_suggestions
        key = (mapping.import_batch, mapping.source_site_raw.strip())
        read.item_count = inventory_counts.get(key, 0)
        read.refrigerant_count = refrigerant_counts.get(key, 0)
        results.append(read)
    return results


def update_cvc_source_building_mapping(
    db: Session,
    mapping_id: int,
    payload: CvcSourceBuildingMappingUpdate,
    city_id: int | None,
) -> CvcSourceBuildingMappingRead | None:
    mapping = db.get(CvcSourceBuildingMapping, mapping_id)
    if not mapping:
        return None
    if city_id is not None and mapping.city_id not in (None, city_id):
        return None

    site = db.get(Site, payload.site_id) if payload.site_id is not None else None
    if payload.site_id is not None and site is None:
        raise ValueError("Site introuvable.")
    if site and city_id is not None and site.city_id != city_id:
        raise ValueError("Site hors perimetre utilisateur.")

    building = db.get(Building, payload.building_id) if payload.building_id is not None else None
    if payload.building_id is not None and building is None:
        raise ValueError("Batiment introuvable.")
    if building and city_id is not None and building.city_id != city_id:
        raise ValueError("Batiment hors perimetre utilisateur.")
    if building and site and building.site_id not in (None, site.id):
        raise ValueError("Le batiment choisi n'appartient pas au site choisi.")

    mapping.site_id = site.id if site else (building.site_id if building else None)
    mapping.building_id = building.id if building else None
    mapping.status = payload.status
    mapping.notes = payload.notes
    mapping.match_method = "manual"
    mapping.match_score = 1.0 if building or site else None
    updated_rows = _apply_source_mapping_to_rows(db, mapping)
    db.commit()
    db.refresh(mapping)

    read = CvcSourceBuildingMappingRead.model_validate(mapping)
    read.item_count = updated_rows if mapping.source_type == "inventory" else 0
    read.refrigerant_count = updated_rows if mapping.source_type == "refrigerant" else 0
    return read


def get_cvc_technical_coverage_report(db: Session, city_id: int | None) -> CvcTechnicalCoverageReport:
    ensure_cvc_source_building_mappings(db, city_id)
    buildings_stmt = select(Building)
    inventory_stmt = select(CvcInventoryItem)
    refrigerant_stmt = select(CvcRefrigerantItem)
    mapping_stmt = select(CvcSourceBuildingMapping)
    if city_id is not None:
        buildings_stmt = buildings_stmt.where(Building.city_id == city_id)
        inventory_stmt = inventory_stmt.where((CvcInventoryItem.city_id == city_id) | (CvcInventoryItem.city_id.is_(None)))
        refrigerant_stmt = refrigerant_stmt.where((CvcRefrigerantItem.city_id == city_id) | (CvcRefrigerantItem.city_id.is_(None)))
        mapping_stmt = mapping_stmt.where((CvcSourceBuildingMapping.city_id == city_id) | (CvcSourceBuildingMapping.city_id.is_(None)))

    buildings = list(db.scalars(buildings_stmt))
    inventory_items = list(db.scalars(inventory_stmt))
    inventory_items = _filter_latest_inventory_batch(inventory_items)
    refrigerant_items = list(db.scalars(refrigerant_stmt))
    mappings = list(db.scalars(mapping_stmt))

    inventory_building_ids = {item.building_id for item in inventory_items if item.building_id is not None}
    refrigerant_building_ids = {item.building_id for item in refrigerant_items if item.building_id is not None}
    covered_building_ids = inventory_building_ids | refrigerant_building_ids
    patrimoine_without_cvc = [
        BuildingMatchSuggestion(
            building_id=building.id,
            site_id=building.site_id,
            nom_batiment=building.nom_batiment,
            adresse=_build_address(building),
            score=1.0,
        )
        for building in buildings
        if building.id not in covered_building_ids
    ]

    def grouped_unmapped(rows, source_type: str) -> list[dict]:
        grouped: dict[str, int] = {}
        for item in rows:
            if item.building_id is None and item.site_raw:
                grouped[item.site_raw] = grouped.get(item.site_raw, 0) + 1
        return [
            {"source_type": source_type, "source_site_raw": source_site_raw, "count": count}
            for source_site_raw, count in sorted(grouped.items())
        ]

    return CvcTechnicalCoverageReport(
        patrimoine_buildings=len(buildings),
        cvc_inventory_items=len(inventory_items),
        cvc_refrigerant_items=len(refrigerant_items),
        inventory_without_building=sum(1 for item in inventory_items if item.building_id is None),
        refrigerants_without_building=sum(1 for item in refrigerant_items if item.building_id is None),
        refrigerants_without_inventory_item=sum(1 for item in refrigerant_items if item.cvc_inventory_item_id is None),
        source_mappings_to_review=sum(1 for mapping in mappings if mapping.status == "to_review"),
        source_mappings_not_found=sum(1 for mapping in mappings if mapping.status == "not_found"),
        patrimoine_buildings_without_cvc=patrimoine_without_cvc[:300],
        inventory_unmapped_by_source=grouped_unmapped(inventory_items, "inventory"),
        refrigerants_unmapped_by_source=grouped_unmapped(refrigerant_items, "refrigerant"),
    )


def _hydrate_items(db: Session, items: list[CvcInventoryItem]) -> list[CvcInventoryItemRead]:
    ref_ids = {item.equipment_ref_id for item in items if item.equipment_ref_id}
    refs_map: dict[int, EquipmentReference] = {}
    if ref_ids:
        for ref in db.scalars(select(EquipmentReference).where(EquipmentReference.id.in_(ref_ids))):
            refs_map[ref.id] = ref

    return [
        _read_item(item, refs_map.get(item.equipment_ref_id) if item.equipment_ref_id else None)
        for item in items
    ]


def list_cvc_items_for_building(db: Session, building_id: int) -> list[CvcInventoryItemRead]:
    items = list(
        db.scalars(
            select(CvcInventoryItem)
            .where(CvcInventoryItem.building_id == building_id)
            .order_by(CvcInventoryItem.famille, CvcInventoryItem.designation)
        )
    )
    items = _filter_latest_inventory_batch(items)

    return _hydrate_items(db, items)


def update_cvc_item(
    db: Session, item_id: int, payload: CvcInventoryItemUpdate, city_id: int | None
) -> CvcInventoryItemRead | None:
    item = db.scalar(select(CvcInventoryItem).where(CvcInventoryItem.id == item_id))
    if not item:
        return None
    if city_id is not None and item.city_id not in (None, city_id):
        return None

    updates = payload.model_dump(exclude_unset=True)

    next_building_id = updates.get("building_id", item.building_id)
    next_site_id = updates.get("site_id", item.site_id)
    next_local_id = updates.get("local_id", item.local_id)
    next_ref_id = updates.get("equipment_ref_id", item.equipment_ref_id)
    next_date_mes = updates.get("date_mis_en_service", item.date_mis_en_service)

    building = db.get(Building, next_building_id) if next_building_id is not None else None
    if next_building_id is not None and building is None:
        raise ValueError("Bâtiment introuvable.")
    if building and city_id is not None and building.city_id != city_id:
        raise ValueError("Bâtiment hors périmètre utilisateur.")

    site = db.get(Site, next_site_id) if next_site_id is not None else None
    if next_site_id is not None and site is None:
        raise ValueError("Site introuvable.")
    if site and city_id is not None and site.city_id != city_id:
        raise ValueError("Site hors périmètre utilisateur.")

    local = db.get(Local, next_local_id) if next_local_id is not None else None
    if next_local_id is not None and local is None:
        raise ValueError("Local introuvable.")
    if local and next_building_id is not None and local.building_id != next_building_id:
        raise ValueError("Le local sélectionné n'appartient pas au bâtiment.")

    ref = db.get(EquipmentReference, next_ref_id) if next_ref_id is not None else None
    if next_ref_id is not None and ref is None:
        raise ValueError("Référence durée de vie introuvable.")

    if "site_id" in updates:
        item.site_id = next_site_id
    if "building_id" in updates:
        item.building_id = next_building_id
    if "local_id" in updates:
        item.local_id = next_local_id
    if "equipment_ref_id" in updates:
        item.equipment_ref_id = next_ref_id
    if "date_mis_en_service" in updates:
        item.date_mis_en_service = next_date_mes
    item.duree_vie_restante = _compute_remaining_life(item.date_mis_en_service, ref, item.etat_sante)
    if _requires_refrigerant_quantity(ref):
        if "quantite_fluide_frigorigene" in updates:
            item.quantite_fluide_frigorigene = payload.quantite_fluide_frigorigene
    else:
        item.quantite_fluide_frigorigene = None

    linked_refrigerants = list(
        db.scalars(select(CvcRefrigerantItem).where(CvcRefrigerantItem.cvc_inventory_item_id == item.id))
    )
    for refrigerant in linked_refrigerants:
        refrigerant.site_id = item.site_id
        refrigerant.building_id = item.building_id

    db.commit()
    db.refresh(item)
    return _read_item(item, ref)


def delete_cvc_items_for_building(db: Session, building_id: int) -> int:
    items = list(db.scalars(select(CvcInventoryItem).where(CvcInventoryItem.building_id == building_id)))
    count = len(items)
    for item in items:
        db.delete(item)
    db.commit()
    return count


def delete_cvc_item(db: Session, item_id: int) -> bool:
    item = db.scalar(select(CvcInventoryItem).where(CvcInventoryItem.id == item_id))
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True
