import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.cvc import (
    CvcApplySiteMappingsRequest,
    CvcApplySiteMappingsResult,
    CvcBuildingMapping,
    CvcImportBatchSummary,
    CvcImportResult,
    CvcImportSiteMatchResponse,
    CvcInventoryItemRead,
    CvcInventoryItemUpdate,
    CvcMatchBuildingsRequest,
    CvcMatchBuildingsResponse,
    CvcPreviewResponse,
    CvcRecomputeReferencesResult,
)
from app.services.buildings import get_building_or_404
from app.services.cvc import (
    apply_site_mappings_to_import,
    delete_cvc_item,
    delete_cvc_items_for_building,
    import_cvc_from_excel,
    list_cvc_import_batches,
    list_cvc_items_for_batch,
    list_cvc_items_for_building,
    list_site_matches_for_import,
    match_buildings_for_sites,
    parse_excel_preview,
    recompute_cvc_references_for_batch,
    update_cvc_item,
)

router = APIRouter(prefix="/cvc", tags=["cvc"])


@router.post("/preview", response_model=CvcPreviewResponse)
async def post_cvc_preview(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> CvcPreviewResponse:
    raw = await file.read()
    try:
        return parse_excel_preview(raw)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Erreur lecture fichier : {e}")


@router.post("/match-buildings", response_model=CvcMatchBuildingsResponse)
def post_match_buildings(
    payload: CvcMatchBuildingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CvcMatchBuildingsResponse:
    return match_buildings_for_sites(db, payload.sites, current_user.city_id)


@router.post("/import", response_model=CvcImportResult, status_code=status.HTTP_201_CREATED)
async def post_cvc_import(
    file: UploadFile = File(...),
    mapping_json: str = Form(default="[]"),
    import_batch: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CvcImportResult:
    raw = await file.read()
    try:
        mapping_data = json.loads(mapping_json)
        mappings = [CvcBuildingMapping(**m) for m in mapping_data]
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Mapping invalide : {e}")
    try:
        return import_cvc_from_excel(db, raw, mappings, current_user.city_id, import_batch)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erreur import : {e}"
        )


@router.get("/imports", response_model=list[CvcImportBatchSummary])
def get_cvc_import_batches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CvcImportBatchSummary]:
    return list_cvc_import_batches(db, current_user.city_id)


@router.get("/imports/{import_batch}/items", response_model=list[CvcInventoryItemRead])
def get_cvc_import_items(
    import_batch: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CvcInventoryItemRead]:
    return list_cvc_items_for_batch(db, import_batch, current_user.city_id)


@router.post("/imports/{import_batch}/recompute-references", response_model=CvcRecomputeReferencesResult)
def post_cvc_recompute_import_references(
    import_batch: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CvcRecomputeReferencesResult:
    return recompute_cvc_references_for_batch(db, import_batch, current_user.city_id)


@router.get("/imports/{import_batch}/site-matches", response_model=CvcImportSiteMatchResponse)
def get_cvc_import_site_matches(
    import_batch: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CvcImportSiteMatchResponse:
    return list_site_matches_for_import(db, import_batch, current_user.city_id)


@router.patch("/imports/{import_batch}/site-mappings", response_model=CvcApplySiteMappingsResult)
def patch_cvc_import_site_mappings(
    import_batch: str,
    payload: CvcApplySiteMappingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CvcApplySiteMappingsResult:
    try:
        return apply_site_mappings_to_import(db, import_batch, payload.mappings, current_user.city_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/buildings/{building_id}", response_model=list[CvcInventoryItemRead])
def get_cvc_building_items(
    building_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CvcInventoryItemRead]:
    get_building_or_404(db, building_id, current_user)
    return list_cvc_items_for_building(db, building_id)


@router.patch("/items/{item_id}", response_model=CvcInventoryItemRead)
def patch_cvc_item(
    item_id: int,
    payload: CvcInventoryItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CvcInventoryItemRead:
    try:
        item = update_cvc_item(db, item_id, payload, current_user.city_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item introuvable.")
    return item


@router.delete("/buildings/{building_id}/items", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_cvc_building_items(
    building_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    get_building_or_404(db, building_id, current_user)
    delete_cvc_items_for_building(db, building_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cvc_item_by_id(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    ok = delete_cvc_item(db, item_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item introuvable.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
