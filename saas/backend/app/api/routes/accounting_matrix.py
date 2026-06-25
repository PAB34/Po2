from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.accounting_matrix import (
    AccountingMatrixContractCreateIn,
    AccountingMatrixContractDetailOut,
    AccountingMatrixContractOut,
    AccountingMatrixContractUpdateIn,
    AccountingMatrixRuleCreateIn,
    AccountingMatrixRuleOut,
    AccountingMatrixRuleUpdateIn,
    AccountingMatrixSeedOut,
    AccountingMatrixVersionCreateIn,
    AccountingMatrixVersionOut,
    InvoiceAccountingSnapshotOut,
)
from app.services import accounting_matrix as svc
from app.services import accounting_matrix_xlsx as xlsx_svc

router = APIRouter(prefix="/accounting-matrices", tags=["accounting-matrices"])


# ---------------------------------------------------------------------------
# Contrats matrice
# ---------------------------------------------------------------------------
@router.get("/contracts", response_model=list[AccountingMatrixContractOut])
def list_contracts(
    domain: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.list_contracts(db, current_user.city_id, domain=domain, supplier=supplier)


@router.post("/seed", response_model=AccountingMatrixSeedOut)
def seed_from_existing(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crée les matrices versionnées (en brouillon) depuis les codifications
    énergie/CPE existantes. Idempotent : saute les matrices déjà présentes."""
    return svc.seed_from_existing(db, current_user.city_id, user_id=current_user.id)


@router.post("/contracts", response_model=AccountingMatrixContractOut, status_code=201)
def create_contract(
    payload: AccountingMatrixContractCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.create_contract(db, current_user.city_id, payload)


@router.get("/contracts/{contract_id}", response_model=AccountingMatrixContractDetailOut)
def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return svc.get_contract(db, current_user.city_id, contract_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/contracts/{contract_id}", response_model=AccountingMatrixContractOut)
def update_contract(
    contract_id: int,
    payload: AccountingMatrixContractUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return svc.update_contract(db, current_user.city_id, contract_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------
@router.post("/contracts/{contract_id}/versions", response_model=AccountingMatrixVersionOut, status_code=201)
def create_version(
    contract_id: int,
    payload: AccountingMatrixVersionCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return svc.create_version(db, current_user.city_id, contract_id, payload, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/versions/{version_id}/activate", response_model=AccountingMatrixVersionOut)
def activate_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return svc.activate_version(db, current_user.city_id, version_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/versions/{version_id}/archive", response_model=AccountingMatrixVersionOut)
def archive_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return svc.archive_version(db, current_user.city_id, version_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Import / export XLSX (doc 35 §5)
# ---------------------------------------------------------------------------
@router.get("/versions/{version_id}/export.xlsx")
def export_version_xlsx(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        content, filename = xlsx_svc.export_version_xlsx(db, current_user.city_id, version_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/contracts/{contract_id}/import-preview")
async def import_preview(
    contract_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Charge un XLSX et renvoie les différences vs la version de référence,
    sans rien écrire. Le commit crée ensuite une version brouillon."""
    raw = await file.read()
    try:
        return xlsx_svc.preview_import(db, current_user.city_id, contract_id, raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/contracts/{contract_id}/import-commit", response_model=AccountingMatrixVersionOut, status_code=201)
async def import_commit(
    contract_id: int,
    version_label: str = Query(..., min_length=1),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crée une nouvelle version brouillon depuis le classeur. N'altère jamais
    une version active."""
    raw = await file.read()
    try:
        return xlsx_svc.commit_import(
            db, current_user.city_id, contract_id, raw,
            version_label=version_label, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Règles
# ---------------------------------------------------------------------------
@router.get("/versions/{version_id}/rules", response_model=list[AccountingMatrixRuleOut])
def list_version_rules(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return svc.list_version_rules(db, current_user.city_id, version_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/versions/{version_id}/rules", response_model=AccountingMatrixRuleOut, status_code=201)
def create_rule(
    version_id: int,
    payload: AccountingMatrixRuleCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return svc.create_rule(db, current_user.city_id, version_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/rules/{rule_id}", response_model=AccountingMatrixRuleOut)
def update_rule(
    rule_id: int,
    payload: AccountingMatrixRuleUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return svc.update_rule(db, current_user.city_id, rule_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Snapshot facture (lecture seule)
# ---------------------------------------------------------------------------
@router.get(
    "/invoices/{source}/{invoice_id}/snapshot",
    response_model=InvoiceAccountingSnapshotOut,
)
def get_invoice_snapshot(
    source: str,
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    snapshot = svc.get_invoice_snapshot(db, current_user.city_id, source, invoice_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Aucun snapshot comptable pour cette facture.")
    return snapshot
