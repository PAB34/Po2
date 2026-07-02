from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.marches import MarketIndicesVariablesOut
from app.services.marches_indices_variables import build_indices_variables

router = APIRouter(prefix="/marches", tags=["marches"])


@router.get("/indices-variables", response_model=MarketIndicesVariablesOut)
def get_indices_variables(
    year_from: int | None = Query(default=None, ge=2000, le=2100),
    year_to: int | None = Query(default=None, ge=2000, le=2100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MarketIndicesVariablesOut:
    current_year = date.today().year
    return MarketIndicesVariablesOut.model_validate(
        build_indices_variables(db, current_user.city_id, year_from or current_year - 1, year_to or current_year)
    )
