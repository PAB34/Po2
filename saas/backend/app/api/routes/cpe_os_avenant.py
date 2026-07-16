"""API routes for CPE DALKIA OS / avenant preparation."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.cpe_os_avenant import (
    CpeOsAvenantRequestCreate,
    CpeOsAvenantRequestOut,
    CpeOsAvenantRequestUpdate,
    CpeOsAvenantSiteOption,
)
from app.services import cpe_os_avenant as svc

router = APIRouter(prefix="/cpe/os-avenants", tags=["cpe-os-avenants"])


@router.get("/sites", response_model=list[CpeOsAvenantSiteOption])
def list_sites_for_os_avenant(
    year: int | None = Query(default=None, ge=2025, le=2033),
    lot: int | None = Query(default=None, ge=1, le=2),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CpeOsAvenantSiteOption]:
    target_year = year or date.today().year
    return [CpeOsAvenantSiteOption.model_validate(row) for row in svc.list_site_options(db, current_user.city_id, year=target_year, lot=lot)]


@router.get("", response_model=list[CpeOsAvenantRequestOut])
def list_os_avenant_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CpeOsAvenantRequestOut]:
    return [CpeOsAvenantRequestOut.model_validate(row) for row in svc.list_requests(db, current_user.city_id)]


@router.post("", response_model=CpeOsAvenantRequestOut, status_code=status.HTTP_201_CREATED)
def create_os_avenant_request(
    payload: CpeOsAvenantRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CpeOsAvenantRequestOut:
    return CpeOsAvenantRequestOut.model_validate(
        svc.create_request(db, current_user.city_id, current_user.id, payload)
    )


@router.get("/{request_id}", response_model=CpeOsAvenantRequestOut)
def get_os_avenant_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CpeOsAvenantRequestOut:
    result = svc.get_request(db, current_user.city_id, request_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Dossier OS / avenant introuvable.")
    return CpeOsAvenantRequestOut.model_validate(result)


@router.patch("/{request_id}", response_model=CpeOsAvenantRequestOut)
def update_os_avenant_request(
    request_id: int,
    payload: CpeOsAvenantRequestUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CpeOsAvenantRequestOut:
    try:
        result = svc.update_request(db, current_user.city_id, request_id, payload)
    except ValueError as exc:
        if str(exc) == "INVALID_STATUS":
            raise HTTPException(status_code=400, detail="Statut OS / avenant invalide.") from exc
        raise
    if result is None:
        raise HTTPException(status_code=404, detail="Dossier OS / avenant introuvable.")
    return CpeOsAvenantRequestOut.model_validate(result)