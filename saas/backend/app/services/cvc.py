import io
import re
import unicodedata
import uuid
from datetime import datetime
from difflib import SequenceMatcher

import openpyxl
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.cvc import CvcInventoryItem
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
    CvcSiteMapping,
    CvcPreviewResponse,
    PatrimoineSiteSuggestion,
    SiteMatchResult,
)

CURRENT_YEAR = datetime.now().year
ALLOWED_CVC_REFERENCE_DOMAINS = {"A.2.1", "A.2.2", "A.2.3"}
NO_FUZZY_FAMILIES = {
    "analyseur",
    "appareil de mesure",
    "autre a qualifier",
    "compteur",
    "plomberie",
}
REFRIGERANT_NIVEAU_3 = {"Production de froid :", "Pompes à chaleur Air/Air, Air/Eau, Eau/Eau"}


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


def list_site_matches_for_import(
    db: Session, import_batch: str, city_id: int | None
) -> CvcImportSiteMatchResponse:
    stmt = select(CvcInventoryItem).where(CvcInventoryItem.import_batch == import_batch)
    if city_id is not None:
        stmt = stmt.where((CvcInventoryItem.city_id == city_id) | (CvcInventoryItem.city_id.is_(None)))
    items = list(db.scalars(stmt))

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

        site = db.get(Site, mapping.site_id) if mapping.site_id is not None else None
        if mapping.site_id is not None and site is None:
            raise ValueError(f"Site introuvable pour {site_raw}.")
        if site and city_id is not None and site.city_id != city_id:
            raise ValueError(f"Site hors perimetre pour {site_raw}.")

        building = db.get(Building, mapping.building_id) if mapping.building_id is not None else None
        if mapping.building_id is not None and building is None:
            raise ValueError(f"Batiment introuvable pour {site_raw}.")
        if building and city_id is not None and building.city_id != city_id:
            raise ValueError(f"Batiment hors perimetre pour {site_raw}.")

        next_site_id = site.id if site else (building.site_id if building else None)
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

    if "armoire electrique" in family or "tableau electrique" in text or "coffret electrique" in text:
        return _find_ref(all_refs, id_ligne=118, equipment_contains="Armoire électrique")

    if family in {"pompe a chaleur", "groupe thermodynamique"} or "pac" in text or "thermodynamique" in text:
        return _find_ref(all_refs, id_ligne=238, equipment_contains="PAC")

    if family in {"split system", "vrv", "systeme vrv", "climatiseur"} or any(
        token in text
        for token in [
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
            "cassette",
            "daikin",
            "hitachi",
            "mitsubishi",
            "atlantic",
            "fujitsu",
        ]
    ):
        if "armoire de climatisation" in text or "roof" in text:
            return _find_ref(all_refs, id_ligne=237, equipment_contains="Armoires autonomes")
        return _find_ref(all_refs, id_ligne=236, equipment_contains="Split")

    if family in {"centrale traitement air"} or "cta" in text or "centrale traitement air" in text:
        return _find_ref(all_refs, id_ligne=221, equipment_contains="CTA")

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

    if family == "preparateur ecs":
        return _find_ref(all_refs, id_ligne=97, equipment_contains="Ballon")

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


def _compute_remaining_life(date_mes: int | None, ref: EquipmentReference | None) -> float | None:
    if not date_mes or not ref or not ref.sypemi_reference_annees:
        return None
    age = CURRENT_YEAR - date_mes
    return round(ref.sypemi_reference_annees - age, 1)


def _read_item(item: CvcInventoryItem, ref: EquipmentReference | None) -> CvcInventoryItemRead:
    sypemi_years = ref.sypemi_reference_annees if ref else None

    criticite_pct = None
    if item.date_mis_en_service and sypemi_years and sypemi_years > 0:
        age = CURRENT_YEAR - item.date_mis_en_service
        criticite_pct = min(100.0, round(age / sypemi_years * 100, 1))

    read = CvcInventoryItemRead.model_validate(item)
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

        duree_vie_restante = _compute_remaining_life(date_mes, ref)

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
            etat_sante=clean("ETAT SANTE"),
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

    db.commit()
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
        item.duree_vie_restante = _compute_remaining_life(item.date_mis_en_service, next_ref)
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
    item.duree_vie_restante = _compute_remaining_life(item.date_mis_en_service, ref)
    if _requires_refrigerant_quantity(ref):
        if "quantite_fluide_frigorigene" in updates:
            item.quantite_fluide_frigorigene = payload.quantite_fluide_frigorigene
    else:
        item.quantite_fluide_frigorigene = None

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
