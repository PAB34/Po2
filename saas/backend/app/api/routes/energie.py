from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.energie import (
    EnergieOverview,
    PrmDetail,
    PrmLoadCurveData,
    PrmMaxPowerData,
)
from app.services.energie import (
    get_energie_overview,
    get_prm_detail,
    get_prm_load_curve,
    get_prm_max_power,
)

router = APIRouter(prefix="/energie", tags=["energie"])


@router.get("", response_model=EnergieOverview)
def get_overview(
    current_user: User = Depends(get_current_user),
) -> EnergieOverview:
    return EnergieOverview.model_validate(get_energie_overview())


@router.get("/{prm_id}", response_model=PrmDetail)
def get_prm(
    prm_id: str,
    current_user: User = Depends(get_current_user),
) -> PrmDetail:
    detail = get_prm_detail(prm_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PRM introuvable")
    return PrmDetail.model_validate(detail)


@router.get("/{prm_id}/max-power", response_model=PrmMaxPowerData)
def get_max_power(
    prm_id: str,
    current_user: User = Depends(get_current_user),
) -> PrmMaxPowerData:
    return PrmMaxPowerData.model_validate(get_prm_max_power(prm_id))


@router.get("/{prm_id}/load-curve", response_model=PrmLoadCurveData)
def get_load_curve(
    prm_id: str,
    days: int | None = Query(default=7, ge=1, le=365),
    current_user: User = Depends(get_current_user),
) -> PrmLoadCurveData:
    return PrmLoadCurveData.model_validate(get_prm_load_curve(prm_id, days=days))
