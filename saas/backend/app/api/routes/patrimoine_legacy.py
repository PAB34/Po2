from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.patrimoine_legacy import (
    LegacyAssetOut,
    LegacyAssetUpdateIn,
    LegacyCandidatesResult,
    LegacyImportResult,
)
from app.services import patrimoine_legacy as svc

router = APIRouter(prefix="/patrimoine/legacy", tags=["patrimoine-historique"])


@router.post("/import", response_model=LegacyImportResult)
async def import_astech_export(
    file: UploadFile = File(...),
    genres: str = Query(
        default="BATI,SITE",
        description="Genres ASTECH importés, séparés par des virgules. Défaut = contenu de la feuille BAT. Vide = tous.",
    ),
    include_out_of_park: bool = Query(
        default=True,
        description="Inclure les biens sortis du parc (HORSPARC=O). Défaut : oui, ils font partie de la feuille BAT.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LegacyImportResult:
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fichier vide.")
    selected = tuple(g.strip().upper() for g in genres.split(",") if g.strip()) if genres else ()
    try:
        result = svc.import_astech_file(
            db,
            city_id=svc.resolve_city_id(db, current_user.city_id),
            filename=file.filename or "export_astech.xlsx",
            raw_bytes=raw_bytes,
            genres=selected,
            include_out_of_park=include_out_of_park,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return LegacyImportResult(**result)


@router.post("/candidates", response_model=LegacyCandidatesResult)
def compute_candidates(
    auto_link: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LegacyCandidatesResult:
    result = svc.compute_candidates(
        db, svc.resolve_city_id(db, current_user.city_id), auto_link=auto_link
    )
    return LegacyCandidatesResult(**result)


@router.get("", response_model=list[LegacyAssetOut])
def list_assets(
    status_filter: str | None = Query(default=None, alias="status"),
    genre: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=500, le=2000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LegacyAssetOut]:
    assets = svc.list_assets(
        db,
        svc.resolve_city_id(db, current_user.city_id),
        status=status_filter,
        genre=genre,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [LegacyAssetOut.model_validate(asset) for asset in assets]


@router.get("/counts")
def counts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    return svc.counts_by_status(db, svc.resolve_city_id(db, current_user.city_id))


@router.post("/from-building/{building_id}", response_model=LegacyAssetOut, status_code=status.HTTP_201_CREATED)
def create_asset_from_building(
    building_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LegacyAssetOut:
    """Ajoute un bâtiment Po2 à la liste ASTECH comme bien « à créer » (décision Q13)."""
    city_id = svc.resolve_city_id(db, current_user.city_id)
    building = svc.get_building_for_city(db, city_id, building_id)
    if building is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bâtiment introuvable.")
    return LegacyAssetOut.model_validate(svc.create_asset_from_building(db, city_id, building))


@router.patch("/{asset_id}", response_model=LegacyAssetOut)
def update_asset(
    asset_id: int,
    payload: LegacyAssetUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LegacyAssetOut:
    asset = svc.get_asset_or_none(db, svc.resolve_city_id(db, current_user.city_id), asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bien historique introuvable.")
    updated = svc.update_asset(
        db,
        asset,
        status=payload.status,
        building_id=payload.building_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        notes=payload.notes,
        clear_building=payload.clear_building,
    )
    return LegacyAssetOut.model_validate(updated)
