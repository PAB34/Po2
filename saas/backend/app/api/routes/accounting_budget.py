from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.accounting_budget import (
    AccountingBudgetLineCreateIn,
    AccountingBudgetLineOut,
    AccountingBudgetLineUpdateIn,
    BudgetSuiviOut,
)
from app.services import accounting_budget as svc

router = APIRouter(prefix="/accounting-budget", tags=["accounting-budget"])

# Même politique d'écriture que les matrices comptables : le budget par
# marché rattache directement une décision financière au contrat matrice.
BUDGET_WRITE_DENIED_ROLES = {"FLUIDES", "FLUIDE", "RESPONSABLE_FLUIDES", "TECHNICIEN_CVC", "TECHNICIEN CVC"}
BUDGET_WRITE_ALLOWED_ROLES = {
    "ADMIN", "SUPERADMIN", "DIRECTION", "RESPONSABLE_MAINTENANCE",
    "RESPONSABLE MAINTENANCE", "PATRIMOINE", "FINANCE", "COMPTA", "COMPTABILITE",
}


def _normalize_role(role: str | None) -> str:
    return (role or "").strip().upper().replace("-", "_")


def _require_budget_write_access(user: User) -> None:
    role = _normalize_role(user.role)
    if role in BUDGET_WRITE_DENIED_ROLES or role not in BUDGET_WRITE_ALLOWED_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Action reservee aux roles autorises hors Fluides et Technicien CVC.",
        )


@router.get("/contracts/{matrix_contract_id}/lines", response_model=list[AccountingBudgetLineOut])
def list_budget_lines(
    matrix_contract_id: int,
    year: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return svc.list_budget_lines(db, current_user.city_id, matrix_contract_id, year)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/lines", response_model=AccountingBudgetLineOut, status_code=201)
def create_budget_line(
    payload: AccountingBudgetLineCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_budget_write_access(current_user)
    try:
        return svc.create_budget_line(db, current_user.city_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/lines/{line_id}", response_model=AccountingBudgetLineOut)
def update_budget_line(
    line_id: int,
    payload: AccountingBudgetLineUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_budget_write_access(current_user)
    try:
        return svc.update_budget_line(db, current_user.city_id, line_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/lines/{line_id}", status_code=204)
def delete_budget_line(
    line_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_budget_write_access(current_user)
    try:
        svc.delete_budget_line(db, current_user.city_id, line_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/contracts/{matrix_contract_id}/suivi", response_model=BudgetSuiviOut)
def get_budget_suivi(
    matrix_contract_id: int,
    year: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return svc.compute_suivi(db, current_user.city_id, matrix_contract_id, year)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
