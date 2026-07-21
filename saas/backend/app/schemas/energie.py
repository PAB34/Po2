from pydantic import BaseModel


class EnergieKpis(BaseModel):
    total_prms: int
    total_subscribed_kva: float
    sous_dimensionnes: int
    proche_seuil: int
    sur_souscrits: int
    calibration_inconnue: int = 0
    annual_consumption_kwh: float | None = None
    annual_consumption_prms: int = 0
    annual_consumption_start: str | None = None
    annual_consumption_end: str | None = None


class SupplierDistributionItem(BaseModel):
    supplier: str
    total_kva: float
    prm_count: int


class EnergyPowerBandItem(BaseModel):
    band: str
    label: str
    prm_count: int
    total_kva: float
    annual_consumption_kwh: float | None


class EnergyCalibrationDistributionItem(BaseModel):
    status: str
    label: str
    prm_count: int


class EnergyTopConsumerItem(BaseModel):
    usage_point_id: str
    name: str
    contractor: str | None
    subscribed_power_kva: float | None
    annual_consumption_kwh: float


class EnergyDistributionItem(BaseModel):
    label: str
    prm_count: int
    total_kva: float | None = None


class DjuSeasonMonthPoint(BaseModel):
    month_num: str
    dju: float
    kwh: float
    ratio: float


class DjuSeasonYear(BaseModel):
    label: str
    months: list[DjuSeasonMonthPoint]


class DjuSeasonMonthDiagnostic(BaseModel):
    season_label: str
    month_num: str
    month_label: str
    status: str
    reason: str
    dju: float | None = None
    kwh: float | None = None


class DjuSeasonData(BaseModel):
    months_order: list[str]
    months_labels: list[str]
    years: list[DjuSeasonYear]
    cible_by_month: dict[str, float | None]
    current_label: str | None
    current_ecart_percent: float | None
    current_months_count: int = 0
    expected_months_count: int = 0
    current_is_complete: bool = False
    month_diagnostics: list[DjuSeasonMonthDiagnostic] = []
    has_data: bool


class PrmDjuSeasonal(BaseModel):
    usage_point_id: str
    winter: DjuSeasonData
    summer: DjuSeasonData


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
    power_bands: list[EnergyPowerBandItem] = []
    calibration_distribution: list[EnergyCalibrationDistributionItem] = []
    top_consumers: list[EnergyTopConsumerItem] = []
    service_level_distribution: list[EnergyDistributionItem] = []
    segment_distribution: list[EnergyDistributionItem] = []
    tariff_distribution: list[EnergyDistributionItem] = []
    connection_state_distribution: list[EnergyDistributionItem] = []
    dju_seasonal: PrmDjuSeasonal | None = None
    prms: list[PrmListItem]


class EnergyDataAuditSource(BaseModel):
    label: str
    filename: str
    first_date: str | None
    last_date: str | None
    row_count: int
    prm_count: int
    missing_prm_count: int
    weak_prm_count: int
    outside_contract_prm_count: int
    bad_date_rows: int


class EnergyDataAuditSummary(BaseModel):
    all_sources: int
    partial_sources: int
    no_source: int
    info: int = 0
    with_warnings: int
    critical: int


class EnergyDataAuditRow(BaseModel):
    usage_point_id: str
    name: str
    segment: str
    contractor: str | None
    tariff: str | None
    subscribed_power_kva: float | None
    service_level: str | None
    connection_state: str | None
    meter_profile: str = "unknown"
    present_sources: list[str]
    missing_sources: list[str]
    weak_sources: list[str]
    coverage_days: dict[str, int]
    first_dates: dict[str, str | None]
    last_dates: dict[str, str | None]
    enedis_outcomes: dict[str, str | None] = {}
    probable_reason: str
    correctable_actions: list[str]
    severity: str


class EnergyDataAudit(BaseModel):
    contracts_count: int
    sources: dict[str, EnergyDataAuditSource]
    combo_counts: dict[str, int]
    missing_by_segment: dict[str, dict[str, int]]
    profile_counts: dict[str, int] = {}
    summary: EnergyDataAuditSummary
    correctable: dict[str, int]
    rows: list[EnergyDataAuditRow]


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


class PrmDataDiagnostic(BaseModel):
    source: str
    label: str
    has_data: bool
    outcome: str | None = None
    severity: str
    message: str
    action: str | None = None


class PrmDetail(BaseModel):
    usage_point_id: str
    contract: PrmContract
    address: PrmAddress
    connection: PrmConnection
    summary: PrmSummary
    calibration: PrmCalibration
    data_diagnostics: dict[str, PrmDataDiagnostic]


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


class FluidsClimateMonth(BaseModel):
    month: int
    current: float | None
    previous: float | None
    average: float | None


class FluidsClimateSeries(BaseModel):
    base_c: float
    monthly: list[FluidsClimateMonth]
    current_total: float | None
    previous_total: float | None
    average_total: float | None
    delta_previous_pct: float | None
    delta_average_pct: float | None


class FluidsThermal(BaseModel):
    scope: str
    sensitivity_kwh_per_dju: float | None
    sensitivity_previous: float | None
    sensitivity_delta_pct: float | None
    base_load_kwh_per_month: float | None
    thermosensitive_share_pct: float | None
    base_load_share_pct: float | None
    r2: float | None
    months_used: int
    window_months: int
    current_period: str | None
    previous_period: str | None
    reliable: bool


class FluidsClimateOverview(BaseModel):
    current_year: int
    previous_year: int
    years_in_average: int
    heating: FluidsClimateSeries
    cooling: FluidsClimateSeries
    thermal: FluidsThermal


class FluidsElecMonthPoint(BaseModel):
    month: str
    kwh: float


class FluidsElecSupplierPoint(BaseModel):
    supplier: str
    annual_kwh: float


class FluidsElecSeries(BaseModel):
    monthly: list[FluidsElecMonthPoint]
    suppliers: list[FluidsElecSupplierPoint]


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


class RealPowerCosts(BaseModel):
    """Coûts de puissance réellement facturés (12 mois), issus des factures."""

    available: bool
    penalties_eur: float
    penalty_periods: int
    fixed_routing_eur: float | None
    invoices_count: int
    period_start: str | None
    period_end: str | None
    max_reached_power_kva: float | None
    subscribed_power_kva: float | None
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
    real_costs: RealPowerCosts | None = None
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
