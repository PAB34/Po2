import io
import uuid
from datetime import datetime
from difflib import SequenceMatcher

import openpyxl
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.cvc import CvcInventoryItem
from app.models.equipment import EquipmentReference
from app.schemas.cvc import (
    BuildingMatchSuggestion,
    CvcBuildingMapping,
    CvcImportResult,
    CvcInventoryItemRead,
    CvcMatchBuildingsResponse,
    CvcPreviewResponse,
    SiteMatchResult,
)

CURRENT_YEAR = datetime.now().year


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


def _resolve_family(
    famille: str | None, all_refs: list[EquipmentReference], cache: dict
) -> EquipmentReference | None:
    if not famille:
        return None
    if famille in cache:
        return cache[famille]
    best_score = 0.0
    best_ref = None
    for ref in all_refs:
        score = _similarity(famille, ref.equipement)
        if score > best_score:
            best_score = score
            best_ref = ref
    result = best_ref if best_score >= 0.5 else None
    cache[famille] = result
    return result


def import_cvc_from_excel(
    db: Session,
    raw_bytes: bytes,
    building_mappings: list[CvcBuildingMapping],
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
        if building_id is None:
            skipped += 1
            continue

        famille_raw = get_val(row, "FAMILLE")
        famille = str(famille_raw).strip() if famille_raw else None
        ref = _resolve_family(famille, all_refs, family_cache)

        date_raw = get_val(row, "DATE MES")
        try:
            date_mes = int(date_raw) if date_raw is not None else None
        except (ValueError, TypeError):
            date_mes = None

        duree_vie_restante = None
        if date_mes and ref and ref.sypemi_reference_annees:
            age = CURRENT_YEAR - date_mes
            duree_vie_restante = round(ref.sypemi_reference_annees - age, 1)

        qte_raw = get_val(row, "QTE QTE RELEVEE")
        try:
            quantite_relevee = int(qte_raw) if qte_raw is not None else None
        except (ValueError, TypeError):
            quantite_relevee = None

        def clean(col: str) -> str | None:
            v = get_val(row, col)
            s = str(v).strip() if v is not None else ""
            return s or None

        item = CvcInventoryItem(
            building_id=building_id,
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
            marque=clean("MARQUE"),
            modele=clean("MODELE"),
            date_mis_en_service=date_mes,
            duree_vie_restante=duree_vie_restante,
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


def list_cvc_items_for_building(db: Session, building_id: int) -> list[CvcInventoryItemRead]:
    items = list(
        db.scalars(
            select(CvcInventoryItem)
            .where(CvcInventoryItem.building_id == building_id)
            .order_by(CvcInventoryItem.famille, CvcInventoryItem.designation)
        )
    )

    ref_ids = {item.equipment_ref_id for item in items if item.equipment_ref_id}
    refs_map: dict[int, EquipmentReference] = {}
    if ref_ids:
        for ref in db.scalars(select(EquipmentReference).where(EquipmentReference.id.in_(ref_ids))):
            refs_map[ref.id] = ref

    result = []
    for item in items:
        ref = refs_map.get(item.equipment_ref_id) if item.equipment_ref_id else None
        sypemi_years = ref.sypemi_reference_annees if ref else None

        criticite_pct = None
        if item.date_mis_en_service and sypemi_years and sypemi_years > 0:
            age = CURRENT_YEAR - item.date_mis_en_service
            criticite_pct = min(100.0, round(age / sypemi_years * 100, 1))

        read = CvcInventoryItemRead.model_validate(item)
        read.criticite_pct = criticite_pct
        read.sypemi_reference_annees = sypemi_years
        result.append(read)

    return result


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
