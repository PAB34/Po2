from pydantic import BaseModel


class EnergieKpis(BaseModel):
    total_prms: int
    total_subscribed_kva: float


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


class EnergieOverview(BaseModel):
    kpis: EnergieKpis
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


class PrmDetail(BaseModel):
    usage_point_id: str
    contract: PrmContract
    address: PrmAddress
    connection: PrmConnection
    summary: PrmSummary


class MaxPowerPoint(BaseModel):
    date: str
    value_va: float


class PrmMaxPowerData(BaseModel):
    usage_point_id: str
    points: list[MaxPowerPoint]


class LoadCurvePoint(BaseModel):
    datetime: str
    value_w: float


class PrmLoadCurveData(BaseModel):
    usage_point_id: str
    points: list[LoadCurvePoint]
