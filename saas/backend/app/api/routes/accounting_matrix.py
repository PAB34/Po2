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
    ApplyInvoiceIn,
    InvoiceAccountingSnapshotOut,
    ManualOverrideIn,
)
from app.services import accounting_matrix as svc
from app.services import accounting_matrix_apply as apply_svc
from app.services import accounting_matrix_invoice_lines as invoice_line_svc
from app.services import accounting_matrix_xlsx as xlsx_svc

router = APIRouter(prefix="/accounting-matrices", tags=["accounting-matrices"])

MATRIX_WRITE_DENIED_ROLES = {"FLUIDES", "FLUIDE", "RESPONSABLE_FLUIDES", "TECHNICIEN_CVC", "TECHNICIEN CVC"}
MATRIX_WRITE_ALLOWED_ROLES = {
    "ADMIN", "SUPERADMIN", "DIRECTION", "RESPONSABLE_MAINTENANCE",
    "RESPONSABLE MAINTENANCE", "PATRIMOINE", "FINANCE", "COMPTA", "COMPTABILITE",
}


def _normalize_role(role: str | None) -> str:
    return (role or "").strip().upper().replace("-", "_")


def _require_matrix_write_access(user: User) -> None:
    role = _normalize_role(user.role)
    if role in MATRIX_WRITE_DENIED_ROLES or role not in MATRIX_WRITE_ALLOWED_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Action reservee aux roles autorises hors Fluides et Technicien CVC.",
        )



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
    """CrÃ©e les matrices versionnÃ©es (en brouillon) depuis les codifications
    Ã©nergie/CPE existantes. Idempotent : saute les matrices dÃ©jÃ  prÃ©sentes."""
    _require_matrix_write_access(current_user)
    return svc.seed_from_existing(db, current_user.city_id, user_id=current_user.id)


@router.post("/contracts", response_model=AccountingMatrixContractOut, status_code=201)
def create_contract(
    payload: AccountingMatrixContractCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_matrix_write_access(current_user)
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
    _require_matrix_write_access(current_user)
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
    _require_matrix_write_access(current_user)
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
    _require_matrix_write_access(current_user)
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
    _require_matrix_write_access(current_user)
    try:
        return svc.archive_version(db, current_user.city_id, version_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Import / export XLSX (doc 35 Â§5)
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
    """Charge un XLSX et renvoie les diffÃ©rences vs la version de rÃ©fÃ©rence,
    sans rien Ã©crire. Le commit crÃ©e ensuite une version brouillon."""
    _require_matrix_write_access(current_user)
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
    """CrÃ©e une nouvelle version brouillon depuis le classeur. N'altÃ¨re jamais
    une version active."""
    _require_matrix_write_access(current_user)
    raw = await file.read()
    try:
        return xlsx_svc.commit_import(
            db, current_user.city_id, contract_id, raw,
            version_label=version_label, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# RÃ¨gles
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
    _require_matrix_write_access(current_user)
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
    _require_matrix_write_access(current_user)
    try:
        return svc.update_rule(db, current_user.city_id, rule_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Snapshot facture : lecture + application / cycle de vie
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


@router.post("/invoices/{source}/{invoice_id}/apply", response_model=InvoiceAccountingSnapshotOut)
def apply_matrix_to_invoice(
    source: str,
    invoice_id: str,
    payload: ApplyInvoiceIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Produit une proposition d'imputation depuis la version active du contrat
    matrice. N'Ã©crase pas un snapshot dÃ©jÃ  figÃ©."""
    _require_matrix_write_access(current_user)
    try:
        lines = [
            apply_svc.InvoiceLine(
                billed_item=l.billed_item, site_code=l.site_code, meter_id=l.meter_id,
                amount=l.amount, line_ref=l.line_ref,
            )
            for l in payload.invoice_lines
        ] or invoice_line_svc.extract_invoice_lines(
            db, current_user.city_id, source=source, invoice_id=invoice_id,
        )
        return apply_svc.apply_to_invoice(
            db, current_user.city_id, source=source, invoice_id=invoice_id,
            contract_id=payload.matrix_contract_id, lines=lines,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/invoices/{source}/{invoice_id}/validate-snapshot", response_model=InvoiceAccountingSnapshotOut)
def validate_invoice_snapshot(
    source: str,
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_matrix_write_access(current_user)
    try:
        return apply_svc.validate_snapshot(
            db, current_user.city_id, source=source, invoice_id=invoice_id, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/invoices/{source}/{invoice_id}/manual-override", response_model=InvoiceAccountingSnapshotOut)
def manual_override_snapshot(
    source: str,
    invoice_id: str,
    payload: ManualOverrideIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_matrix_write_access(current_user)
    try:
        return apply_svc.manual_override(
            db, current_user.city_id, source=source, invoice_id=invoice_id,
            snapshot_json=payload.snapshot_json, motif=payload.motif, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/invoices/{source}/{invoice_id}/export-finance", response_model=InvoiceAccountingSnapshotOut)
def export_invoice_finance(
    source: str,
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_matrix_write_access(current_user)
    try:
        return apply_svc.export_finance(
            db, current_user.city_id, source=source, invoice_id=invoice_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
