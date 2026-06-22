from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.gas_invoice import (
    GasBpuPriceOut,
    GasBpuPriceUpdateIn,
    GasInvoiceDecisionIn,
    GasInvoiceOut,
    GasNetworkTariffOut,
    GasNetworkTariffUpdateIn,
    GasTaxRateOut,
    GasTaxRateUpdateIn,
)
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


@router.get("/bpu", response_model=list[GasBpuPriceOut])
def list_bpu(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.list_bpu(db, current_user.city_id)


@router.patch("/bpu/{row_id}", response_model=GasBpuPriceOut)
def update_bpu(
    row_id: int,
    payload: GasBpuPriceUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return svc.update_bpu(db, row_id, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/network-tariff", response_model=list[GasNetworkTariffOut])
def list_network_tariffs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.list_network_tariffs(db, current_user.city_id)


@router.patch("/network-tariff/{row_id}", response_model=GasNetworkTariffOut)
def update_network_tariff(
    row_id: int,
    payload: GasNetworkTariffUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return svc.update_network_tariff(db, row_id, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tax-rates", response_model=list[GasTaxRateOut])
def list_tax_rates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.load_tax_rates(db, current_user.city_id)


@router.patch("/tax-rates/{row_id}", response_model=GasTaxRateOut)
def update_tax_rate(
    row_id: int,
    payload: GasTaxRateUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return svc.update_tax_rate(db, row_id, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/export")
def export_xlsx(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = svc.export_xlsx(db, current_user.city_id)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="liaison_finance_gaz_totalenergies.xlsx"'},
    )


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
