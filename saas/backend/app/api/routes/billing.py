from hashlib import sha256
from threading import Thread

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.db import SessionLocal
from app.models.invoice import EnergyInvoiceBatch, EnergyInvoiceBatchItem
from app.models.user import User
from app.schemas.billing import (
    BillingBpuLineIn,
    BillingBpuLineOut,
    BillingBpuSyncPreviewLine,
    BillingBpuSyncResult,
    BillingConfigOut,
    BillingConfigPatch,
    BillingHphcSlotIn,
    BillingHphcSlotOut,
    BillingPriceEntryIn,
    BillingPriceEntryOut,
    BillingSupplierGroup,
    EnergyAccountingNatureRuleIn,
    EnergyAccountingNatureRuleOut,
    EnergyAccountingSiteMappingIn,
    EnergyAccountingSiteMappingOut,
    EnergyCodificationImportResult,
    EnergyLiaisonPreview,
    EnergyLiaisonPreviewRow,
    TurpeVersionOut,
)
from app.schemas.supplier_contact import SupplierContactIn, SupplierContactOut
from app.services import supplier_contacts as supplier_contacts_svc
from app.schemas.invoice import (
    EnergyInvoiceBatchDetailOut,
    EnergyInvoiceBatchOut,
    EnergyInvoiceDecisionIn,
    EnergyInvoiceImportDetailOut,
    EnergyInvoiceImportOut,
    EnergyInvoiceMonthlyConsumptionOut,
    EnergyInvoiceUploadResponse,
)
from app.services.billing import (
    delete_config,
    get_bpu_lines,
    get_config,
    get_configs,
    get_hphc_slots,
    get_prices,
    get_supplier_groups,
    patch_config,
    replace_bpu_lines,
    replace_hphc_slots,
    replace_prices,
    upsert_supplier_config,
)
from app.services.billing_bpu_sync import apply_config_sync, preview_config_sync
from app.services import energie_accounting as accounting_svc
from app.services.invoices import (
    analyze_existing_invoice_import,
    create_invoice_batch,
    create_invoice_import,
    delete_all_invoice_imports,
    delete_invoice_import,
    purge_duplicate_invoice_imports,
    reanalyze_all_invoice_imports,
    get_invoice_batch,
    get_invoice_import,
    get_monthly_invoice_consumption,
    list_invoice_batches,
    list_invoice_imports,
    update_invoice_decision,
)
from app.services.turpe import list_turpe_versions

router = APIRouter(prefix="/billing", tags=["billing"])


def _require_city(user: User) -> int:
    if user.city_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Utilisateur sans ville associée")
    return user.city_id


def _get_cfg_or_404(db: Session, config_id: int, city_id: int):
    cfg = get_config(db, config_id, city_id)
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration introuvable")
    return cfg


@router.get("/supplier-groups", response_model=list[BillingSupplierGroup])
def list_supplier_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    return get_supplier_groups(db, city_id)


@router.get("/supplier-contacts", response_model=list[SupplierContactOut])
def list_supplier_contacts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    return supplier_contacts_svc.list_contacts(db, city_id)


@router.put("/supplier-contacts/{supplier}", response_model=SupplierContactOut)
def upsert_supplier_contact(
    supplier: str,
    payload: SupplierContactIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    return supplier_contacts_svc.upsert_contact(db, city_id, supplier, payload.model_dump(exclude_unset=True))


@router.get("/configs", response_model=list[BillingConfigOut])
def list_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    return get_configs(db, city_id)


@router.get("/turpe/versions", response_model=list[TurpeVersionOut])
def list_turpe_reference_versions(
    current_user: User = Depends(get_current_user),
):
    _require_city(current_user)
    return list_turpe_versions()


@router.put("/configs/supplier/{supplier}", response_model=BillingConfigOut)
def upsert_config(
    supplier: str,
    payload: BillingConfigPatch,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    return upsert_supplier_config(
        db,
        city_id,
        supplier,
        lot=payload.lot,
        has_hphc=payload.has_hphc,
        representative_prm_id=payload.representative_prm_id,
    )


@router.patch("/configs/{config_id}", response_model=BillingConfigOut)
def update_config(
    config_id: int,
    payload: BillingConfigPatch,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    cfg = _get_cfg_or_404(db, config_id, city_id)
    return patch_config(db, cfg, payload.lot, payload.has_hphc, payload.representative_prm_id)


@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_billing_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    city_id = _require_city(current_user)
    cfg = _get_cfg_or_404(db, config_id, city_id)
    delete_config(db, cfg)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/configs/{config_id}/prices", response_model=list[BillingPriceEntryOut])
def list_prices(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    _get_cfg_or_404(db, config_id, city_id)
    return get_prices(db, config_id)


@router.put("/configs/{config_id}/prices", response_model=list[BillingPriceEntryOut])
def set_prices(
    config_id: int,
    entries: list[BillingPriceEntryIn],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    _get_cfg_or_404(db, config_id, city_id)
    return replace_prices(db, config_id, [e.model_dump() for e in entries])


@router.get("/configs/{config_id}/hphc-slots", response_model=list[BillingHphcSlotOut])
def list_hphc_slots(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    _get_cfg_or_404(db, config_id, city_id)
    return get_hphc_slots(db, config_id)


@router.put("/configs/{config_id}/hphc-slots", response_model=list[BillingHphcSlotOut])
def set_hphc_slots(
    config_id: int,
    slots: list[BillingHphcSlotIn],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    _get_cfg_or_404(db, config_id, city_id)
    return replace_hphc_slots(db, config_id, [s.model_dump() for s in slots])


@router.get("/configs/{config_id}/bpu-lines", response_model=list[BillingBpuLineOut])
def list_bpu_lines(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    _get_cfg_or_404(db, config_id, city_id)
    return get_bpu_lines(db, config_id)


@router.put("/configs/{config_id}/bpu-lines", response_model=list[BillingBpuLineOut])
def set_bpu_lines(
    config_id: int,
    lines: list[BillingBpuLineIn],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    _get_cfg_or_404(db, config_id, city_id)
    return replace_bpu_lines(db, config_id, [ln.model_dump() for ln in lines])


@router.post("/configs/{config_id}/bpu-lines/sync", response_model=BillingBpuSyncResult)
def sync_bpu_lines_from_bpu(
    config_id: int,
    apply: bool = Query(False, description="False = aperçu (dry-run) ; True = écrit en base."),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reprend les prix BPU du fichier de référence (xlsx audité) dans `BillingBpuLine`.

    Source = le xlsx canonique, document de l'année la plus récente pour le lot du config.
    `apply=false` renvoie l'aperçu sans rien écrire ; `apply=true` remplace les lignes
    courantes (year IS NULL). Voir `services/billing_bpu_sync.py`.
    """
    city_id = _require_city(current_user)
    cfg = _get_cfg_or_404(db, config_id, city_id)
    res = apply_config_sync(db, cfg) if apply else preview_config_sync(db, cfg)
    return BillingBpuSyncResult(
        applied=apply and bool(res.lines),
        lot_number=res.lot_number,
        source_filename=res.source_filename,
        source_year=res.source_year,
        source_supplier=res.source_supplier,
        lines_count=len(res.lines),
        warnings=res.warnings,
        lines=[BillingBpuSyncPreviewLine(**{k: v for k, v in ln.items() if k != "year" and k != "observation"}) for ln in res.lines],
    )


@router.get("/invoices/imports", response_model=list[EnergyInvoiceImportOut])
def list_energy_invoice_imports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    return list_invoice_imports(db, city_id)


@router.get("/invoices/consumption-monthly", response_model=EnergyInvoiceMonthlyConsumptionOut)
def get_energy_invoice_consumption_monthly(
    year: int = Query(..., ge=2000, le=2100),
    search: str | None = None,
    control_status: list[str] = Query(default_factory=list),
    decision_status: list[str] = Query(default_factory=list),
    regroupement: list[str] = Query(default_factory=list),
    contract_holder: list[str] = Query(default_factory=list),
    issue_family: list[str] = Query(default_factory=list),
    issue_code: list[str] = Query(default_factory=list),
    invoice_month: list[str] = Query(default_factory=list),
    prm_id: list[str] = Query(default_factory=list),
    fic_number: list[str] = Query(default_factory=list),
    site_name: list[str] = Query(default_factory=list),
    site_city: list[str] = Query(default_factory=list),
    segment: list[str] = Query(default_factory=list),
    tariff_code: list[str] = Query(default_factory=list),
    tariff_option_label: list[str] = Query(default_factory=list),
    document_type: list[str] = Query(default_factory=list),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    return get_monthly_invoice_consumption(
        db,
        city_id,
        year,
        search=search,
        control_statuses=control_status,
        decision_statuses=decision_status,
        regroupements=regroupement,
        contract_holders=contract_holder,
        issue_families=issue_family,
        issue_codes=issue_code,
        invoice_months=invoice_month,
        prm_ids=prm_id,
        fic_numbers=fic_number,
        site_names=site_name,
        site_cities=site_city,
        segments=segment,
        tariff_codes=tariff_code,
        tariff_option_labels=tariff_option_label,
        document_types=document_type,
    )


@router.get("/invoices/batches", response_model=list[EnergyInvoiceBatchOut])
def list_energy_invoice_batches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    return list_invoice_batches(db, city_id)


@router.get("/invoices/batches/{batch_id}", response_model=EnergyInvoiceBatchDetailOut)
def get_energy_invoice_batch(
    batch_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    batch = get_invoice_batch(db, city_id, batch_id)
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lot factures introuvable")
    return batch


@router.post("/invoices/batches", response_model=EnergyInvoiceBatchDetailOut, status_code=status.HTTP_201_CREATED)
async def upload_energy_invoice_batch(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    return await create_invoice_batch(db, city_id, current_user.id, files)


@router.get("/invoices/imports/{invoice_import_id}", response_model=EnergyInvoiceImportDetailOut)
def get_energy_invoice_import(
    invoice_import_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    invoice_import = get_invoice_import(db, city_id, invoice_import_id)
    if invoice_import is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import facture introuvable")
    return invoice_import


@router.patch("/invoices/imports/{invoice_import_id}/decision", response_model=EnergyInvoiceImportDetailOut)
def patch_energy_invoice_decision(
    invoice_import_id: int,
    payload: EnergyInvoiceDecisionIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    invoice_import = update_invoice_decision(
        db,
        city_id,
        invoice_import_id,
        current_user.id,
        payload.decision_status,
        payload.decision_comment,
    )
    if invoice_import is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import facture introuvable")
    return invoice_import


@router.post("/invoices/imports", response_model=EnergyInvoiceUploadResponse)
async def upload_energy_invoice_import(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    invoice_import, is_duplicate = await create_invoice_import(db, city_id, current_user.id, file)
    return {
        "invoice_import": invoice_import,
        "is_duplicate": is_duplicate,
        "message": "Facture deja importee." if is_duplicate else "Facture importee.",
    }


@router.post(
    "/invoices/imports/xlsx",
    response_model=EnergyInvoiceBatchDetailOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_engie_xlsx_export(
    file: UploadFile = File(...),
    force_update: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload de l'export XLSX ENGIE 'Mes Factures' : un fichier = N bordereaux.

    Chaque bordereau du XLSX devient un EnergyInvoiceImport indépendant
    (analysé via le même pipeline que les PDF).

    - force_update=False (défaut) : bordereaux déjà présents en base (même
      invoice_number) sont skip et tracés comme doublons dans le résumé.
    - force_update=True : bordereaux déjà présents sont re-analysés avec les
      nouvelles données du fichier. Les champs decision_status / comment /
      by / updated_at sont PRÉSERVÉS pour ne pas perdre l'historique utilisateur.
    """
    city_id = _require_city(current_user)
    filename = file.filename or ""
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format attendu : fichier .xlsx ENGIE (export 'Mes Factures').",
        )
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fichier vide.",
        )
    batch = EnergyInvoiceBatch(
        city_id=city_id,
        uploaded_by_user_id=current_user.id,
        source="engie_xlsx_export",
        status="processing",
        file_count=1,
    )
    batch.items.append(
        EnergyInvoiceBatchItem(
            original_filename=filename,
            content_type=file.content_type,
            file_size_bytes=len(content),
            sha256=sha256(content).hexdigest(),
            status="processing",
            message="Analyse XLSX lancee en arriere-plan.",
        )
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    worker = Thread(
        target=_run_engie_xlsx_import_job,
        args=(batch.id, city_id, current_user.id, content, filename, file.content_type, force_update),
        daemon=True,
    )
    worker.start()
    return batch


def _run_engie_xlsx_import_job(
    batch_id: int,
    city_id: int,
    user_id: int,
    file_bytes: bytes,
    original_filename: str,
    content_type: str | None,
    force_update: bool,
) -> None:
    from app.services.engie_xlsx_import import import_engie_xlsx

    db = SessionLocal()
    try:
        batch = db.query(EnergyInvoiceBatch).filter_by(id=batch_id, city_id=city_id).first()
        item = batch.items[0] if batch and batch.items else None
        if item is not None:
            item.message = "Analyse XLSX en cours : lecture et controle des bordereaux."
            db.commit()
        try:
            summary = import_engie_xlsx(
                db,
                city_id=city_id,
                user_id=user_id,
                file_bytes=file_bytes,
                original_filename=original_filename,
                content_type=content_type,
                force_update=force_update,
            )
        except Exception as exc:
            if batch is not None:
                batch.status = "completed_with_errors"
                batch.error_count = 1
                if item is not None:
                    item.status = "error"
                    item.message = f"Analyse XLSX impossible : {exc}"
                db.commit()
            return

        if batch is not None:
            batch.status = "completed_with_errors" if summary["errors"] else "completed"
            batch.file_count = summary["total_bordereaux"]
            batch.imported_count = summary["created"] + summary["updated"]
            batch.duplicate_count = summary["duplicates"]
            batch.error_count = summary["errors"]
            batch.ignored_count = 0
            if item is not None:
                item.status = "imported" if summary["errors"] == 0 else "error"
                item.message = (
                    f"Export XLSX traite : {summary['total_bordereaux']} bordereau(x), "
                    f"{summary['created']} cree(s), {summary['updated']} mis a jour, "
                    f"{summary['duplicates']} doublon(s), {summary['errors']} erreur(s)."
                )
            db.commit()
    finally:
        db.close()


@router.post(
    "/invoices/imports/edf-csv",
    response_model=EnergyInvoiceBatchDetailOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_edf_csv_export(
    file: UploadFile = File(...),
    force_update: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload de l'export CSV de facturation EDF (un fichier = N factures)."""
    city_id = _require_city(current_user)
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format attendu : fichier .csv EDF.",
        )
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fichier vide.")
    batch = EnergyInvoiceBatch(
        city_id=city_id,
        uploaded_by_user_id=current_user.id,
        source="edf_csv_export",
        status="processing",
        file_count=1,
    )
    batch.items.append(
        EnergyInvoiceBatchItem(
            original_filename=filename,
            content_type=file.content_type,
            file_size_bytes=len(content),
            sha256=sha256(content).hexdigest(),
            status="processing",
            message="Analyse CSV EDF lancee en arriere-plan.",
        )
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    worker = Thread(
        target=_run_edf_csv_import_job,
        args=(batch.id, city_id, current_user.id, content, filename, file.content_type, force_update),
        daemon=True,
    )
    worker.start()
    return batch


def _run_edf_csv_import_job(
    batch_id: int,
    city_id: int,
    user_id: int,
    file_bytes: bytes,
    original_filename: str,
    content_type: str | None,
    force_update: bool,
) -> None:
    from app.services.edf_csv_import import import_edf_csv

    db = SessionLocal()
    try:
        batch = db.query(EnergyInvoiceBatch).filter_by(id=batch_id, city_id=city_id).first()
        item = batch.items[0] if batch and batch.items else None
        if item is not None:
            item.message = "Analyse CSV EDF en cours : lecture et controle des factures."
            db.commit()
        try:
            summary = import_edf_csv(
                db,
                city_id=city_id,
                user_id=user_id,
                file_bytes=file_bytes,
                original_filename=original_filename,
                content_type=content_type,
                force_update=force_update,
            )
        except Exception as exc:
            if batch is not None:
                batch.status = "completed_with_errors"
                batch.error_count = 1
                if item is not None:
                    item.status = "error"
                    item.message = f"Analyse CSV EDF impossible : {exc}"
                db.commit()
            return

        if batch is not None:
            batch.status = "completed_with_errors" if summary["errors"] else "completed"
            batch.file_count = summary["total_bordereaux"]
            batch.imported_count = summary["created"] + summary["updated"]
            batch.duplicate_count = summary["duplicates"]
            batch.error_count = summary["errors"]
            batch.ignored_count = 0
            if item is not None:
                item.status = "imported" if summary["errors"] == 0 else "error"
                item.message = (
                    f"CSV EDF traite : {summary['total_bordereaux']} facture(s), "
                    f"{summary['created']} cree(s), {summary['updated']} mis a jour, "
                    f"{summary['duplicates']} doublon(s), {summary['errors']} erreur(s)."
                )
            db.commit()
    finally:
        db.close()


@router.delete("/invoices/imports/{invoice_import_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_energy_invoice_import(
    invoice_import_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    city_id = _require_city(current_user)
    found = delete_invoice_import(db, city_id, invoice_import_id)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import facture introuvable")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/invoices/imports/purge-duplicates")
def purge_duplicate_energy_invoice_imports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    """Supprime les factures énergie en double (même numéro), garde la plus récente."""
    city_id = _require_city(current_user)
    return purge_duplicate_invoice_imports(db, city_id)


@router.post("/invoices/imports/reanalyze-all")
def reanalyze_all_energy_invoice_imports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    """Recalcule les contrôles de toutes les factures énergie (après correctif moteur)."""
    city_id = _require_city(current_user)
    return reanalyze_all_invoice_imports(db, city_id)


@router.delete("/invoices/imports")
def delete_all_energy_invoice_imports(
    confirm: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Suppression en masse de TOUS les EnergyInvoiceImport de la city courante.

    Requiert le paramètre ?confirm=DELETE pour éviter les appels accidentels.
    Gère correctement les fichiers physiques partagés (cas XLSX 1 fichier = N imports).
    Retourne le résumé chiffré.
    """
    if confirm != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action destructive : ajouter ?confirm=DELETE pour confirmer.",
        )
    city_id = _require_city(current_user)
    return delete_all_invoice_imports(db, city_id)


@router.post("/invoices/imports/{invoice_import_id}/analyze", response_model=EnergyInvoiceImportOut)
def analyze_energy_invoice_import(
    invoice_import_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    invoice_import = analyze_existing_invoice_import(db, city_id, invoice_import_id)
    if invoice_import is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import facture introuvable")
    return invoice_import


# ---------------------------------------------------------------------------
# Matrice comptable ENGIE (codification) + fiche de liaison finances
# ---------------------------------------------------------------------------


@router.post("/accounting/import-codification", response_model=EnergyCodificationImportResult)
async def import_energy_codification(
    file: UploadFile = File(..., description="Classeur de codification comptable ENGIE (xlsx)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    raw = await file.read()
    res = accounting_svc.import_codification_workbook(db, raw, filename=file.filename, city_id=city_id)
    return EnergyCodificationImportResult(
        filename=res.filename,
        nature_rules_created=res.nature_rules_created,
        nature_rules_updated=res.nature_rules_updated,
        site_mappings_created=res.site_mappings_created,
        site_mappings_updated=res.site_mappings_updated,
        errors=res.errors,
    )


@router.post("/accounting/site-mappings/bootstrap")
def bootstrap_energy_site_mappings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    return accounting_svc.bootstrap_site_mappings_from_invoices(db, city_id)


@router.get("/accounting/site-mappings", response_model=list[EnergyAccountingSiteMappingOut])
def list_energy_site_mappings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return accounting_svc.list_site_mappings(db, _require_city(current_user))


@router.post("/accounting/site-mappings", response_model=EnergyAccountingSiteMappingOut, status_code=status.HTTP_201_CREATED)
def create_energy_site_mapping(
    payload: EnergyAccountingSiteMappingIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    return accounting_svc.create_site_mapping(db, {**payload.model_dump(), "city_id": city_id})


@router.patch("/accounting/site-mappings/{mapping_id}", response_model=EnergyAccountingSiteMappingOut)
def update_energy_site_mapping(
    mapping_id: int,
    payload: EnergyAccountingSiteMappingIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    obj = accounting_svc.get_site_mapping(db, mapping_id, city_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Codification site introuvable")
    return accounting_svc.update_site_mapping(db, obj, payload.model_dump(exclude={"prm_id"}))


@router.delete("/accounting/site-mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_energy_site_mapping(
    mapping_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    city_id = _require_city(current_user)
    obj = accounting_svc.get_site_mapping(db, mapping_id, city_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Codification site introuvable")
    accounting_svc.delete_site_mapping(db, obj)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/accounting/nature-rules", response_model=list[EnergyAccountingNatureRuleOut])
def list_energy_nature_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return accounting_svc.list_nature_rules(db, _require_city(current_user))


@router.post("/accounting/nature-rules", response_model=EnergyAccountingNatureRuleOut, status_code=status.HTTP_201_CREATED)
def create_energy_nature_rule(
    payload: EnergyAccountingNatureRuleIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    return accounting_svc.create_nature_rule(db, {**payload.model_dump(), "city_id": city_id})


@router.patch("/accounting/nature-rules/{rule_id}", response_model=EnergyAccountingNatureRuleOut)
def update_energy_nature_rule(
    rule_id: int,
    payload: EnergyAccountingNatureRuleIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    obj = accounting_svc.get_nature_rule(db, rule_id, city_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Règle de nature introuvable")
    return accounting_svc.update_nature_rule(db, obj, payload.model_dump())


@router.delete("/accounting/nature-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_energy_nature_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    city_id = _require_city(current_user)
    obj = accounting_svc.get_nature_rule(db, rule_id, city_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Règle de nature introuvable")
    accounting_svc.delete_nature_rule(db, obj)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/invoices/imports/{invoice_import_id}/codification", response_model=EnergyLiaisonPreview)
def preview_invoice_codification(
    invoice_import_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    city_id = _require_city(current_user)
    invoice_import = get_invoice_import(db, city_id, invoice_import_id)
    if invoice_import is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import facture introuvable")
    rows = accounting_svc.resolve_invoice_codification(db, invoice_import)
    preview_rows = [
        EnergyLiaisonPreviewRow(
            prm_id=r.prm_id, site_name=r.site_name, poste=r.poste, label=r.label, amount_ht=r.amount_ht,
            service_code=r.service_code, function_code=r.function_code, antenna_code=r.antenna_code,
            operation_code=r.operation_code, accounting_nature=r.accounting_nature,
            accounting_label=r.accounting_label, status=r.status,
        )
        for r in rows
    ]
    return EnergyLiaisonPreview(
        invoice_number=invoice_import.invoice_number,
        rows_count=len(preview_rows),
        blocked_count=sum(1 for r in preview_rows if r.status == "blocked"),
        rows=preview_rows,
    )


@router.get("/invoices/imports/{invoice_import_id}/liaison.xlsx")
def export_invoice_liaison(
    invoice_import_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    city_id = _require_city(current_user)
    invoice_import = get_invoice_import(db, city_id, invoice_import_id)
    if invoice_import is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import facture introuvable")
    content = accounting_svc.build_energy_liaison_workbook(db, invoice_import)
    accounting_svc.mark_energy_liaison_exported(db, invoice_import)
    label = invoice_import.invoice_number or str(invoice_import.id)
    filename = f"fiche-liaison-{accounting_svc.liaison_supplier_slug(invoice_import)}-{label}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
