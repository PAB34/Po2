from pydantic import BaseModel


class EnergieKpis(BaseModel):
    total_prms: int
    total_subscribed_kva: float
    sous_dimensionnes: int
    proche_seuil: int
    sur_souscrits: int


class SupplierDistributionItem(BaseModel):
    supplier: str
    total_kva: float
    prm_count: int


class PrmListItem(BaseModel):
    usage_point_id: str
    name: str
    address: str
    contractor: str
    subscribed_power_kva: float | None
    tariff: str | None
    segment: str | None
    connection_state: str | None
    services_level: str | None
    peak_kva_3y: float | None
    calibration_status: str | None
    calibration_ratio: float | None


class EnergieOverview(BaseModel):
    kpis: EnergieKpis
    supplier_distribution: list[SupplierDistributionItem]
    prms: list[PrmListItem]


class PrmContract(BaseModel):
    usage_point_id: str
    contract_start: str | None
    contract_type: str | None
    contractor: str | None
    tariff: str | None
    subscribed_power_kva: float | None
    segment: str | None
    organization_name: str | None
    name: str | None


class PrmAddress(BaseModel):
    address_number_street_name: str | None
    address_postal_code_city: str | None
    address_staircase_floor_apartment: str | None
    address_building: str | None
    address_insee_code: str | None


class PrmConnection(BaseModel):
    serial_number: str | None
    connection_state: str | None
    voltage_level: str | None
    subscribed_kva: float | None


class PrmSummary(BaseModel):
    segment: str | None
    activation_date: str | None
    last_power_change_date: str | None
    services_level: str | None


class PrmCalibration(BaseModel):
    subscribed_kva: float | None
    peak_kva_3y: float | None
    ratio_percent: float | None
    status: str | None
    recommendation: str | None


class PrmDetail(BaseModel):
    usage_point_id: str
    contract: PrmContract
    address: PrmAddress
    connection: PrmConnection
    summary: PrmSummary
    calibration: PrmCalibration


class MaxPowerPoint(BaseModel):
    date: str
    value_va: float


class PrmMaxPowerData(BaseModel):
    usage_point_id: str
    subscribed_kva: float | None
    points: list[MaxPowerPoint]


class LoadCurvePoint(BaseModel):
    datetime: str
    value_w: float


class PrmLoadCurveData(BaseModel):
    usage_point_id: str
    points: list[LoadCurvePoint]


class AnnualMonthPoint(BaseModel):
    month: str
    max_kva: float


class AnnualYearProfile(BaseModel):
    year: str
    months: list[AnnualMonthPoint]


class PrmAnnualProfile(BaseModel):
    usage_point_id: str
    subscribed_kva: float | None
    profiles: list[AnnualYearProfile]


class DailyConsumptionPoint(BaseModel):
    date: str
    value_kwh: float


class PrmDailyConsumption(BaseModel):
    usage_point_id: str
    points: list[DailyConsumptionPoint]


class DjuMonthPoint(BaseModel):
    month: str
    dju_chauffe: float
    dju_froid: float


class DjuPerfPoint(BaseModel):
    month: str
    kwh: float
    dju: float
    ratio_kwh_per_dju: float


class DjuSidePerf(BaseModel):
    baseline_ratio_kwh_per_dju: float | None
    months_in_baseline: int
    last_month: DjuPerfPoint | None
    last_month_ecart_percent: float | None
    last_month_status: str | None
    timeseries: list[DjuPerfPoint]
    has_data: bool
    is_reliable: bool


class PrmDjuPerformance(BaseModel):
    usage_point_id: str
    heating: DjuSidePerf
    cooling: DjuSidePerf


class DjuSeasonMonthPoint(BaseModel):
    month_num: str
    dju: float
    kwh: float
    ratio: float


class DjuSeasonYear(BaseModel):
    label: str
    months: list[DjuSeasonMonthPoint]


class DjuSeasonData(BaseModel):
    months_order: list[str]
    months_labels: list[str]
    years: list[DjuSeasonYear]
    cible_by_month: dict[str, float | None]
    current_label: str | None
    current_ecart_percent: float | None
    has_data: bool


class PrmDjuSeasonal(BaseModel):
    usage_point_id: str
    winter: DjuSeasonData
    summer: DjuSeasonData


class PowerRecommendationDataQuality(BaseModel):
    status: str
    max_power_days: int
    max_power_months: int
    max_power_years: int
    first_max_power_date: str | None
    last_max_power_date: str | None
    missing: list[str]


class PowerRecommendationScenario(BaseModel):
    key: str
    label: str
    target_power_kva: float
    delta_kva: float
    margin_percent: float | None
    risk: str
    ratio_after_percent: float | None
    is_recommended: bool


class PowerRecommendationEconomicEstimate(BaseModel):
    available: bool
    annual_amount_eur: float | None
    reason: str


class PrmPowerRecommendation(BaseModel):
    usage_point_id: str
    name: str
    address: str
    contractor: str | None
    tariff: str | None
    segment: str | None
    annual_consumption_kwh: float | None
    annual_consumption_start: str | None
    annual_consumption_end: str | None
    annual_consumption_days: int
    subscribed_power_kva: float | None
    peak_kva: float | None
    current_ratio_percent: float | None
    calibration_status: str
    recommended_power_kva: float | None
    recommended_scenario: str | None
    action: str
    confidence: str
    data_quality: PowerRecommendationDataQuality
    scenarios: list[PowerRecommendationScenario]
    economic_estimate: PowerRecommendationEconomicEstimate
    justification: str
    priority_score: float


class PowerRecommendationKpis(BaseModel):
    total: int
    increase: int
    decrease: int
    maintain: int
    insufficient_data: int
    high_confidence: int
    medium_confidence: int


class PowerRecommendationOverview(BaseModel):
    kpis: PowerRecommendationKpis
    recommendations: list[PrmPowerRecommendation]
