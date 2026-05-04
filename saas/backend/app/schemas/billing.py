from pydantic import BaseModel


class BillingGroupItem(BaseModel):
    supplier: str
    tariff_code: str
    tariff_label: str
    prm_count: int
    prm_ids: list[str]
    config_id: int | None
    is_configured: bool


class BillingConfigCreate(BaseModel):
    supplier: str
    tariff_code: str
    tariff_label: str | None = None
    has_hphc: bool = False
    representative_prm_id: str | None = None


class BillingConfigPatch(BaseModel):
    has_hphc: bool | None = None
    representative_prm_id: str | None = None
    tariff_label: str | None = None


class BillingConfigOut(BaseModel):
    id: int
    city_id: int
    supplier: str
    tariff_code: str
    tariff_label: str | None
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
