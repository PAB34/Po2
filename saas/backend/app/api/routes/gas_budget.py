from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.gas_budget import GasBudgetReviseOut
from app.services.gas_budget_revise import build_gas_budget_revise

router = APIRouter(prefix="/marches", tags=["marches"])


@router.get("/gas-budget-revise", response_model=GasBudgetReviseOut)
def get_gas_budget_revise(
    year: int = Query(..., ge=2000, le=2100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Budget révisé gaz TotalEnergies (fixe/variable) par PCE, avec réalisé et atterrissage."""
    return build_gas_budget_revise(db, current_user.city_id, year=year)
