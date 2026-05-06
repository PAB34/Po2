from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.energie import (
    DjuMonthPoint,
    EnergieOverview,
    PowerRecommendationOverview,
    PrmAnnualProfile,
    PrmDailyConsumption,
    PrmDetail,
    PrmDjuPerformance,
    PrmDjuSeasonal,
    PrmLoadCurveData,
    PrmMaxPowerData,
    PrmPowerRecommendation,
)
from app.services.energie import (
    get_data_ranges,
    get_dju_monthly,
    get_energie_overview,
    get_prm_annual_profile,
    get_prm_daily_consumption,
    get_prm_detail,
    get_prm_dju_performance,
    get_prm_dju_seasonal,
    get_prm_load_curve,
    get_prm_max_power,
)
from app.services.power_recommendations import get_power_recommendations, get_prm_power_recommendation

router = APIRouter(prefix="/energie", tags=["energie"])


@router.get("", response_model=EnergieOverview)
def get_overview(
    current_user: User = Depends(get_current_user),
) -> EnergieOverview:
    return EnergieOverview.model_validate(get_energie_overview())


# Static sub-paths must come before /{prm_id} to avoid being caught as a path param.
@router.get("/data-ranges")
def get_ranges(current_user: User = Depends(get_current_user)) -> dict:
    return get_data_ranges()


@router.get("/dju/monthly", response_model=list[DjuMonthPoint])
def get_dju(
    current_user: User = Depends(get_current_user),
) -> list[DjuMonthPoint]:
    return [DjuMonthPoint.model_validate(r) for r in get_dju_monthly()]


@router.get("/preconisations", response_model=PowerRecommendationOverview)
def get_preconisations(
    current_user: User = Depends(get_current_user),
) -> PowerRecommendationOverview:
    return PowerRecommendationOverview.model_validate(get_power_recommendations())


@router.get("/{prm_id}/preconisation", response_model=PrmPowerRecommendation)
def get_preconisation(
    prm_id: str,
    current_user: User = Depends(get_current_user),
) -> PrmPowerRecommendation:
    recommendation = get_prm_power_recommendation(prm_id)
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PRM introuvable")
    return PrmPowerRecommendation.model_validate(recommendation)


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


@router.get("/{prm_id}/annual-profile", response_model=PrmAnnualProfile)
def get_annual_profile(
    prm_id: str,
    current_user: User = Depends(get_current_user),
) -> PrmAnnualProfile:
    return PrmAnnualProfile.model_validate(get_prm_annual_profile(prm_id))


@router.get("/{prm_id}/daily-consumption", response_model=PrmDailyConsumption)
def get_daily_consumption(
    prm_id: str,
    days: int | None = Query(default=90, ge=1, le=730),
    current_user: User = Depends(get_current_user),
) -> PrmDailyConsumption:
    return PrmDailyConsumption.model_validate(get_prm_daily_consumption(prm_id, days=days))


@router.get("/{prm_id}/dju-performance", response_model=PrmDjuPerformance)
def get_dju_performance(
    prm_id: str,
    current_user: User = Depends(get_current_user),
) -> PrmDjuPerformance:
    return PrmDjuPerformance.model_validate(get_prm_dju_performance(prm_id))


@router.get("/{prm_id}/dju-seasonal", response_model=PrmDjuSeasonal)
def get_dju_seasonal(
    prm_id: str,
    current_user: User = Depends(get_current_user),
) -> PrmDjuSeasonal:
    return PrmDjuSeasonal.model_validate(get_prm_dju_seasonal(prm_id))
