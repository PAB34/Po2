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
