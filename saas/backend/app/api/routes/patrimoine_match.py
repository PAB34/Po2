from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.patrimoine_match import (
    PatrimoineMatchBulkOut,
    PatrimoineMatchCollectOut,
    PatrimoineMatchItemOut,
    PatrimoineMatchUpdateIn,
    PatrimoineTargetOut,
)
from app.services import patrimoine_match as svc

router = APIRouter(prefix="/patrimoine/matches", tags=["patrimoine-rapprochement"])


@router.get("", response_model=list[PatrimoineMatchItemOut])
def list_matches(
    source: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.list_matches(db, current_user.city_id, source=source, status=status)


@router.get("/counts")
def matches_counts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.counts_by_status(db, current_user.city_id)


@router.get("/targets", response_model=list[PatrimoineTargetOut])
def search_targets(
    q: str = Query(default=""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.search_targets(db, current_user.city_id, q)


@router.post("/collect", response_model=PatrimoineMatchCollectOut)
def collect_matches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.collect_matches(db, current_user.city_id)


@router.post("/bulk-link", response_model=PatrimoineMatchBulkOut)
def bulk_link(
    min_score: float = Query(default=90.0, ge=0, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.bulk_link_obvious(db, current_user.city_id, min_score=min_score)


@router.patch("/{item_id}", response_model=PatrimoineMatchItemOut)
def update_match(
    item_id: int,
    payload: PatrimoineMatchUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return svc.update_match(
            db,
            current_user.city_id,
            item_id,
            status=payload.status,
            resolved_target_type=payload.resolved_target_type,
            resolved_target_id=payload.resolved_target_id,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
