from __future__ import annotations

from pydantic import BaseModel


class GasBudgetRevisePointOut(BaseModel):
    pce: str
    nom_site: str | None = None
    building_id: int | None = None
    kwh_n1: float
    conso_attendue_kwh: float
    climate_ratio: float
    peg_ratio: float
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


class GasBudgetReviseTotalsOut(BaseModel):
    fixe_prevision: float
    variable_prevision: float
    prevision_reference: float
    realise: float
    realise_fixe: float
    realise_variable: float
    atterrissage: float
    ecart_atterrissage_vs_prevision: float


class GasBudgetReviseOut(BaseModel):
    year: int
    generated_on: str
    pce_count: int
    peg_available: bool
    dju_available: bool
    totals: GasBudgetReviseTotalsOut
    points: list[GasBudgetRevisePointOut]
    source_note: str
