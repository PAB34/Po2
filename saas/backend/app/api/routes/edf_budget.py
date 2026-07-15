from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.engie_budget import EngieBudgetReviseOut
from app.services.engie_elec_budget_revise import build_edf_elec_budget_revise

router = APIRouter(prefix="/marches", tags=["marches"])


@router.get("/edf-elec-budget-revise", response_model=EngieBudgetReviseOut)
def get_edf_elec_budget_revise(
    year: int | None = Query(None, ge=2000, le=2100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Budget révisé EDF éclairage public (fixe/variable) par PRM, avec réalisé et atterrissage.

    ``year`` omis → l'année significative recommandée (évite d'ouvrir sur une année trop partielle).
    """
    return build_edf_elec_budget_revise(db, current_user.city_id, year=year)
