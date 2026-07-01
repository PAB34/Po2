"""Schémas Pydantic du budget par marché (cadrage refonte-v1)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AccountingBudgetLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    matrix_contract_id: int
    year: int
    operation_number: str
    label: str | None = None
    amount_budget: float
    comment: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AccountingBudgetLineCreateIn(BaseModel):
    matrix_contract_id: int
    year: int = Field(..., ge=2000, le=2100)
    operation_number: str = Field(..., min_length=1)
    label: str | None = None
    amount_budget: float = Field(default=0.0, ge=0)
    comment: str | None = None


class AccountingBudgetLineUpdateIn(BaseModel):
    label: str | None = None
    amount_budget: float | None = Field(default=None, ge=0)
    comment: str | None = None


class BudgetRealizedByOperationOut(BaseModel):
    operation_number: str
    amount_budget: float
    amount_realized: float
    amount_landing: float
    variance_to_budget: float


class BudgetSuiviOut(BaseModel):
    matrix_contract_id: int
    year: int
    year_progress_percent: float
    rows: list[BudgetRealizedByOperationOut]
    unassigned_realized_amount: float
    total_budget: float
    total_realized: float
    total_landing: float
    snapshots_included: int
    snapshots_excluded_unknown_year: int
    snapshots_excluded_other_year: int
    snapshots_total: int
    data_completeness_note: str
