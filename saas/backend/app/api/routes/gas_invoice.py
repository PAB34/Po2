from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.gas_invoice import GasInvoiceDecisionIn, GasInvoiceOut
from app.services import gas_invoice as svc

router = APIRouter(prefix="/gas/invoices", tags=["gaz-factures"])


@router.get("", response_model=list[GasInvoiceOut])
def list_invoices(
    control_status: str | None = Query(default=None),
    decision_status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.list_invoices(db, current_user.city_id, control_status=control_status, decision_status=decision_status)


@router.get("/portfolio")
def portfolio(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.portfolio(db, current_user.city_id)


@router.post("/import")
async def import_invoices(
    file: UploadFile = File(...),
    force_update: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raw = await file.read()
    try:
        return svc.import_invoices(db, current_user.city_id, raw, force_update=force_update)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/recompute")
def recompute(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.recompute_controls(db, current_user.city_id)


@router.patch("/{invoice_id}/decision", response_model=GasInvoiceOut)
def set_decision(
    invoice_id: int,
    payload: GasInvoiceDecisionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return svc.set_decision(db, current_user.city_id, invoice_id, payload.decision_status, payload.comment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
