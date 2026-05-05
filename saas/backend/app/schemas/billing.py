from pydantic import BaseModel


class BillingSupplierGroup(BaseModel):
    supplier: str
    prm_count: int
    prm_ids: list[str]
    tariff_codes: list[str]
    tariff_prm_counts: dict[str, int]
    config_id: int | None
    lot: str | None
    has_hphc: bool
    representative_prm_id: str | None
    is_configured: bool


class BillingConfigCreate(BaseModel):
    supplier: str
    lot: str | None = None
    has_hphc: bool = False
    representative_prm_id: str | None = None


class BillingConfigPatch(BaseModel):
    lot: str | None = None
    has_hphc: bool | None = None
    representative_prm_id: str | None = None


class BillingConfigOut(BaseModel):
    id: int
    city_id: int
    supplier: str
    tariff_code: str | None
    lot: str | None
    has_hphc: bool
    representative_prm_id: str | None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class BillingPriceEntryIn(BaseModel):
    year: int | None = None
    component: str
    value: float
    unit: str | None = None


class BillingPriceEntryOut(BaseModel):
    id: int
    config_id: int
    year: int | None
    component: str
    value: float
    unit: str | None

    class Config:
        from_attributes = True


class BillingHphcSlotIn(BaseModel):
    day_type: str
    start_time: str
    end_time: str
    period: str


class BillingHphcSlotOut(BaseModel):
    id: int
    config_id: int
    day_type: str
    start_time: str
    end_time: str
    period: str

    class Config:
        from_attributes = True


class BillingBpuLineIn(BaseModel):
    year: int | None = None
    tariff_code: str
    poste: str
    pu_fourniture: float | None = None
    pu_capacite: float | None = None
    pu_cee: float | None = None
    pu_go: float | None = None
    pu_total: float | None = None
    observation: str | None = None


class BillingBpuLineOut(BaseModel):
    id: int
    config_id: int
    year: int | None
    tariff_code: str
    poste: str
    pu_fourniture: float | None
    pu_capacite: float | None
    pu_cee: float | None
    pu_go: float | None
    pu_total: float | None
    observation: str | None

    class Config:
        from_attributes = True
