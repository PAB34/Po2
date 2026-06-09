from datetime import date, datetime

from pydantic import BaseModel


class TurpeVersionOut(BaseModel):
    code: str
    family: str
    label: str
    valid_from: date
    valid_to: date
    next_expected_update: date
    successor_hint: str
    source_label: str
    source_url: str
    cre_deliberation_url: str
    cre_modification_url: str
    tariff_keys: list[str]


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
    created_at: datetime
    updated_at: datetime

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


class BillingBpuSyncPreviewLine(BaseModel):
    tariff_code: str
    poste: str
    pu_fourniture: float | None = None
    pu_capacite: float | None = None
    pu_cee: float | None = None
    pu_go: float | None = None
    pu_total: float | None = None


class BillingBpuSyncResult(BaseModel):
    """Résultat d'une sync BPU → BillingBpuLine (preview ou appliquée)."""

    applied: bool
    lot_number: int
    source_filename: str | None = None
    source_year: int | None = None
    source_supplier: str | None = None
    lines_count: int = 0
    warnings: list[str] = []
    lines: list[BillingBpuSyncPreviewLine] = []


# ---------------------------------------------------------------------------
# Matrice comptable ENGIE (codification) + fiche de liaison
# ---------------------------------------------------------------------------


class EnergyAccountingSiteMappingIn(BaseModel):
    prm_id: str
    site_name: str | None = None
    regroupement: str | None = None
    family: str | None = None
    manager: str | None = None
    alternate_manager: str | None = None
    service_code: str | None = None
    service_label: str | None = None
    function_code: str | None = None
    function_label: str | None = None
    antenna_code: str | None = None
    antenna_label: str | None = None
    operation_code: str | None = None
    operation_label: str | None = None
    active: bool = True
    notes: str | None = None


class EnergyAccountingSiteMappingOut(EnergyAccountingSiteMappingIn):
    id: int
    city_id: int | None = None

    class Config:
        from_attributes = True


class EnergyAccountingNatureRuleIn(BaseModel):
    supplier: str = "ENGIE"
    market: str | None = None
    billed_item: str
    frequency: str | None = None
    accounting_nature: str
    accounting_label: str | None = None
    active: bool = True
    notes: str | None = None


class EnergyAccountingNatureRuleOut(EnergyAccountingNatureRuleIn):
    id: int
    city_id: int | None = None

    class Config:
        from_attributes = True


class EnergyCodificationImportResult(BaseModel):
    filename: str | None = None
    nature_rules_created: int = 0
    nature_rules_updated: int = 0
    site_mappings_created: int = 0
    site_mappings_updated: int = 0
    errors: list[str] = []


class EnergyLiaisonPreviewRow(BaseModel):
    prm_id: str | None = None
    site_name: str | None = None
    poste: str | None = None
    label: str | None = None
    amount_ht: float | None = None
    service_code: str | None = None
    function_code: str | None = None
    antenna_code: str | None = None
    operation_code: str | None = None
    accounting_nature: str | None = None
    accounting_label: str | None = None
    status: str


class EnergyLiaisonPreview(BaseModel):
    invoice_number: str | None = None
    rows_count: int = 0
    blocked_count: int = 0
    rows: list[EnergyLiaisonPreviewRow] = []
