from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.energie import (
    DjuMonthPoint,
    EnergieOverview,
    EnergyDataAudit,
    FluidsClimateOverview,
    FluidsElecObservedPrice,
    FluidsElecSeries,
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
    get_data_audit,
    get_dju_monthly,
    get_energie_overview,
    get_fluids_climate,
    get_fluids_elec_observed_price,
    get_fluids_elec_series,
    get_prm_annual_profile,
    get_prm_daily_consumption,
    get_prm_detail,
    get_prm_dju_performance,
    get_prm_dju_seasonal,
    get_prm_load_curve,
    get_prm_max_power,
)
from app.services.power_recommendations import get_power_recommendations, get_prm_power_recommendation
from app.services.power_real_costs import attach_real_costs, get_real_power_costs_by_prm

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


@router.get("/data-audit", response_model=EnergyDataAudit)
def get_audit(current_user: User = Depends(get_current_user)) -> EnergyDataAudit:
    return EnergyDataAudit.model_validate(get_data_audit())


@router.get("/dju/monthly", response_model=list[DjuMonthPoint])
def get_dju(
    current_user: User = Depends(get_current_user),
) -> list[DjuMonthPoint]:
    return [DjuMonthPoint.model_validate(r) for r in get_dju_monthly()]


@router.get("/fluids/climate", response_model=FluidsClimateOverview)
def get_fluids_climate_route(
    current_user: User = Depends(get_current_user),
) -> FluidsClimateOverview:
    """Vue globale Fluides : trajectoire DJU chauffage/froid (N/N-1/moyenne) et signature thermique."""
    return FluidsClimateOverview.model_validate(get_fluids_climate())


@router.get("/fluids/elec-series", response_model=FluidsElecSeries)
def get_fluids_elec_series_route(
    current_user: User = Depends(get_current_user),
) -> FluidsElecSeries:
    """Détail Électricité : conso mensuelle du parc (multi-années) + conso annuelle par fournisseur."""
    return FluidsElecSeries.model_validate(get_fluids_elec_series())



@router.get("/fluids/elec-observed-price", response_model=FluidsElecObservedPrice)
def get_fluids_elec_observed_price_route(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FluidsElecObservedPrice:
    """Prix moyen observe des factures electricite, toutes composantes facture incluses."""
    return FluidsElecObservedPrice.model_validate(get_fluids_elec_observed_price(db, current_user.city_id))
@router.get("/preconisations", response_model=PowerRecommendationOverview)
def get_preconisations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PowerRecommendationOverview:
    overview = get_power_recommendations()
    costs = get_real_power_costs_by_prm(db, current_user.city_id)
    attach_real_costs(overview["recommendations"], costs)
    return PowerRecommendationOverview.model_validate(overview)


@router.get("/{prm_id}/preconisation", response_model=PrmPowerRecommendation)
def get_preconisation(
    prm_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PrmPowerRecommendation:
    recommendation = get_prm_power_recommendation(prm_id)
    if recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PRM introuvable")
    costs = get_real_power_costs_by_prm(db, current_user.city_id)
    attach_real_costs([recommendation], costs)
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
