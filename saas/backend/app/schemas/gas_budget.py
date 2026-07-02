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
    fixe_budget: float
    variable_budget: float
    budget_revise: float
    realise: float
    kwh_realise: float
    atterrissage: float
    ecart_atterrissage_vs_budget: float
    landing_method: str
    has_history: bool


class GasBudgetReviseTotalsOut(BaseModel):
    fixe_budget: float
    variable_budget: float
    budget_revise: float
    realise: float
    atterrissage: float
    ecart_atterrissage_vs_budget: float


class GasBudgetReviseOut(BaseModel):
    year: int
    generated_on: str
    pce_count: int
    peg_available: bool
    dju_available: bool
    totals: GasBudgetReviseTotalsOut
    points: list[GasBudgetRevisePointOut]
    source_note: str
