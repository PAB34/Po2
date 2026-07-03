from __future__ import annotations

from pydantic import BaseModel


class EngieBudgetRevisePointOut(BaseModel):
    prm: str
    site_name: str | None = None
    segment: str | None = None
    building_id: int | None = None
    building_name: str | None = None
    kwh_n1: float
    enedis_kwh_n1: float
    conso_attendue_kwh: float
    thermo_share: float
    conso_method: str
    enedis_available: bool
    bpu_ratio: float
    bpu_available: bool
    turpe_ratio: float
    pu_variable_eur_kwh: float
    fixe_prevision: float
    variable_prevision: float
    prevision_reference: float
    realise: float
    realise_fixe: float
    realise_variable: float
    kwh_realise: float
    months_covered: int
    atterrissage: float
    ecart_atterrissage_vs_prevision: float
    landing_method: str
    has_history: bool


class EngieBudgetReviseTotalsOut(BaseModel):
    fixe_prevision: float
    variable_prevision: float
    prevision_reference: float
    realise: float
    realise_fixe: float
    realise_variable: float
    atterrissage: float
    ecart_atterrissage_vs_prevision: float


class EngieBudgetReviseBuildingOut(BaseModel):
    building_id: int | None = None
    building_name: str | None = None
    prm_count: int
    prevision_reference: float
    realise: float
    atterrissage: float


class EngieBudgetReviseOut(BaseModel):
    year: int
    generated_on: str
    prm_count: int
    turpe_available: bool
    bpu_available: bool
    enedis_available: bool
    totals: EngieBudgetReviseTotalsOut
    points: list[EngieBudgetRevisePointOut]
    buildings: list[EngieBudgetReviseBuildingOut]
    source_note: str
