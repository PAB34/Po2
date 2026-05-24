from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.invoice import EnergyInvoiceBatch, EnergyInvoiceBatchItem, EnergyInvoiceImport
from app.services.energie import _daily_consumption_index
from app.services.invoice_analysis import analyze_invoice_import

ALLOWED_EXTENSIONS = {".pdf", ".xml", ".csv", ".txt", ".xlsx", ".xls", ".zip"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
DECISION_STATUSES = {"to_review", "approved", "rejected", "dispute_sent"}
XLSX_PROCESSING_STALE_AFTER = timedelta(minutes=10)


def _safe_original_filename(filename: str | None) -> str:
    name = (filename or "facture").replace("\\", "/").split("/")[-1].strip()
    return (name or "facture")[:255]


def _safe_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format non pris en charge. Formats acceptes : PDF, Factur-X/XML, CSV, TXT, XLSX, ZIP.",
        )
    return suffix


def _guess_supplier(filename: str) -> str | None:
    upper = filename.upper()
    if "ENGIE" in upper:
        return "ENGIE"
    if "EDF" in upper or "ELECTRICITE" in upper:
        return "ELECTRICITE DE FRANCE"
    return None


def list_invoice_imports(db: Session, city_id: int) -> list[EnergyInvoiceImport]:
    return (
        db.query(EnergyInvoiceImport)
        .options(selectinload(EnergyInvoiceImport.normalized_invoice))
        .filter_by(city_id=city_id)
        .order_by(EnergyInvoiceImport.created_at.desc(), EnergyInvoiceImport.id.desc())
        .all()
    )


def list_invoice_batches(db: Session, city_id: int) -> list[EnergyInvoiceBatch]:
    batches = (
        db.query(EnergyInvoiceBatch)
        .filter_by(city_id=city_id)
        .order_by(EnergyInvoiceBatch.created_at.desc(), EnergyInvoiceBatch.id.desc())
        .all()
    )


def get_monthly_invoice_consumption(
    db: Session,
    city_id: int,
    year: int,
    *,
    search: str | None = None,
    control_statuses: list[str] | None = None,
    decision_statuses: list[str] | None = None,
    regroupements: list[str] | None = None,
    contract_holders: list[str] | None = None,
    issue_families: list[str] | None = None,
    issue_codes: list[str] | None = None,
) -> dict:
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    today = date.today()
    generated_to = min(today, year_end) if today.year == year else year_end

    imports = list_invoice_imports(db, city_id)
    imports = [
        invoice_import
        for invoice_import in imports
        if _invoice_import_matches_monthly_filters(
            invoice_import,
            search=search,
            control_statuses=control_statuses or [],
            decision_statuses=decision_statuses or [],
            regroupements=regroupements or [],
            contract_holders=contract_holders or [],
            issue_families=issue_families or [],
            issue_codes=issue_codes or [],
        )
    ]

    month_keys = [f"{year}-{month:02d}" for month in range(1, 13)]
    billed_by_month = {month: Decimal("0") for month in month_keys}
    invoice_ids_by_month: dict[str, set[int]] = {month: set() for month in month_keys}
    prm_ids: set[str] = set()

    for invoice_import in imports:
        allocated = False
        for site in _iter_invoice_import_sites(invoice_import):
            prm_id = _clean_prm(site.get("prm_id"))
            if prm_id:
                prm_ids.add(prm_id)
            consumption = _invoice_site_consumption_kwh(site)
            start = _date_value(site.get("period_start")) or invoice_import.period_start
            end = _date_value(site.get("period_end")) or invoice_import.period_end
            if consumption is None or start is None or end is None:
                continue
            if _allocate_consumption_to_months(consumption, start, end, year, billed_by_month):
                allocated = True
                for month in _months_between(max(start, year_start), min(end, year_end)):
                    invoice_ids_by_month[month].add(invoice_import.id)

        if allocated:
            continue

        consumption = _decimal(invoice_import.total_consumption_kwh)
        if consumption is None or invoice_import.period_start is None or invoice_import.period_end is None:
            continue
        if _allocate_consumption_to_months(
            consumption,
            invoice_import.period_start,
            invoice_import.period_end,
            year,
            billed_by_month,
        ):
            for month in _months_between(
                max(invoice_import.period_start, year_start),
                min(invoice_import.period_end, year_end),
            ):
                invoice_ids_by_month[month].add(invoice_import.id)

    enedis_by_month = {month: Decimal("0") for month in month_keys}
    enedis_prms_by_month: dict[str, set[str]] = {month: set() for month in month_keys}
    daily_consumption = _daily_consumption_index()
    for prm_id in prm_ids:
        for point in daily_consumption.get(prm_id, []):
            point_date = str(point.get("date", ""))[:10]
            if not (f"{year}-01-01" <= point_date <= f"{year}-12-31"):
                continue
            month = point_date[:7]
            if month not in enedis_by_month:
                continue
            enedis_by_month[month] += Decimal(str(point["value_wh"])) / Decimal("1000")
            enedis_prms_by_month[month].add(prm_id)

    months = []
    for month in month_keys:
        billed = billed_by_month[month]
        enedis = enedis_by_month[month]
        has_enedis = len(enedis_prms_by_month[month]) > 0
        months.append(
            {
                "month": month,
                "billed_kwh": _round_float(billed),
                "enedis_kwh": _round_float(enedis) if has_enedis else None,
                "delta_kwh": _round_float(billed - enedis) if has_enedis else None,
                "invoice_count": len(invoice_ids_by_month[month]),
                "prm_count": len(prm_ids),
                "enedis_prm_count": len(enedis_prms_by_month[month]),
            }
        )

    billed_total = sum(billed_by_month.values(), Decimal("0"))
    enedis_total = sum(enedis_by_month.values(), Decimal("0"))
    has_any_enedis = any(enedis_prms_by_month[month] for month in month_keys)
    return {
        "year": year,
        "generated_from": year_start,
        "generated_to": generated_to,
        "billed_total_kwh": _round_float(billed_total),
        "enedis_total_kwh": _round_float(enedis_total) if has_any_enedis else None,
        "delta_total_kwh": _round_float(billed_total - enedis_total) if has_any_enedis else None,
        "invoice_count": len(imports),
        "prm_count": len(prm_ids),
        "enedis_prm_count": len({prm for month in month_keys for prm in enedis_prms_by_month[month]}),
        "months": months,
    }


def _invoice_import_matches_monthly_filters(
    invoice_import: EnergyInvoiceImport,
    *,
    search: str | None,
    control_statuses: list[str],
    decision_statuses: list[str],
    regroupements: list[str],
    contract_holders: list[str],
    issue_families: list[str],
    issue_codes: list[str],
) -> bool:
    if control_statuses and invoice_import.control_status not in control_statuses:
        return False
    if decision_statuses and invoice_import.decision_status not in decision_statuses:
        return False
    if regroupements and (not invoice_import.regroupement or invoice_import.regroupement not in regroupements):
        return False
    if contract_holders and (not invoice_import.contract_holder or invoice_import.contract_holder not in contract_holders):
        return False
    if issue_families or issue_codes:
        if not any(
            (not issue_families or _invoice_issue_family(issue) in issue_families)
            and (not issue_codes or issue.get("code") in issue_codes)
            for issue in invoice_import.control_issues
            if isinstance(issue, dict)
        ):
            return False
    needle = (search or "").strip().lower()
    if not needle:
        return True
    values = [
        invoice_import.original_filename,
        invoice_import.invoice_number,
        invoice_import.regroupement,
        invoice_import.contract_holder,
        invoice_import.supplier_guess,
    ]
    return any(needle in str(value).lower() for value in values if value)


def _invoice_issue_family(issue: dict) -> str:
    code = str(issue.get("code") or "")
    if code.startswith("BPU_"):
        return "bpu"
    if code.startswith("TURPE_"):
        return "turpe"
    if "CONSUMPTION" in code or code.startswith("ENEDIS_CONSUMPTION") or code.startswith("LOAD_CURVE_CONSUMPTION"):
        return "consumption"
    if "POWER" in code or code.startswith("SUBSCRIBED_POWER"):
        return "power"
    if "VAT" in code or "TAX" in code or code in {"HT_TOTAL_MISMATCH", "INVOICE_VAT_TOTAL_MISMATCH"}:
        return "taxes"
    if "PERIOD" in code:
        return "periods"
    if any(token in code for token in ("PRM", "SUPPLIER", "MARKET", "REGROUPEMENT", "INVOICE", "CHORUS", "DOCUMENT")):
        return "document"
    return "other"


def _iter_invoice_import_sites(invoice_import: EnergyInvoiceImport) -> list[dict]:
    result = invoice_import.analysis_result
    sites = result.get("sites") if isinstance(result, dict) else None
    return sites if isinstance(sites, list) else []


def _clean_prm(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _date_value(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _invoice_site_consumption_kwh(site: dict) -> Decimal | None:
    supply_total = Decimal("0")
    has_supply = False
    network_total = Decimal("0")
    has_network = False
    for line in site.get("invoice_lines", []):
        if not isinstance(line, dict):
            continue
        quantity = _decimal(line.get("quantity"))
        if quantity is None:
            continue
        component = line.get("normalized_component")
        if component == "supply":
            has_supply = True
            supply_total += quantity
        elif component == "network_variable":
            has_network = True
            network_total += quantity
    if has_supply:
        return supply_total
    if has_network:
        return network_total
    total = _decimal(site.get("total_consumption_kwh"))
    if total is not None:
        return total
    return None


def _allocate_consumption_to_months(
    consumption_kwh: Decimal,
    start: date,
    end: date,
    year: int,
    target: dict[str, Decimal],
) -> bool:
    if end < start:
        return False
    clipped_start = max(start, date(year, 1, 1))
    clipped_end = min(end, date(year, 12, 31))
    if clipped_end < clipped_start:
        return False
    total_days = Decimal((end - start).days + 1)
    if total_days <= 0:
        return False
    for month in _months_between(clipped_start, clipped_end):
        month_start = date.fromisoformat(f"{month}-01")
        month_end = _month_end(month_start)
        overlap_start = max(clipped_start, month_start)
        overlap_end = min(clipped_end, month_end)
        overlap_days = Decimal((overlap_end - overlap_start).days + 1)
        target[month] += consumption_kwh * (overlap_days / total_days)
    return True


def _months_between(start: date, end: date) -> list[str]:
    if end < start:
        return []
    months = []
    current = date(start.year, start.month, 1)
    limit = date(end.year, end.month, 1)
    while current <= limit:
        months.append(f"{current.year}-{current.month:02d}")
        current = date(current.year + (1 if current.month == 12 else 0), 1 if current.month == 12 else current.month + 1, 1)
    return months


def _month_end(month_start: date) -> date:
    if month_start.month == 12:
        return date(month_start.year, 12, 31)
    return date(month_start.year, month_start.month + 1, 1) - timedelta(days=1)


def _round_float(value: Decimal) -> float:
    return round(float(value), 1)
    _mark_stale_xlsx_batches(db, batches)
    return batches


def get_invoice_batch(db: Session, city_id: int, batch_id: int) -> EnergyInvoiceBatch | None:
    batch = db.query(EnergyInvoiceBatch).filter_by(city_id=city_id, id=batch_id).first()
    if batch is not None:
        _mark_stale_xlsx_batches(db, [batch])
    return batch


def _mark_stale_xlsx_batches(db: Session, batches: list[EnergyInvoiceBatch]) -> None:
    now = datetime.now(timezone.utc)
    changed = False
    for batch in batches:
        if batch.source != "engie_xlsx_export" or batch.status != "processing":
            continue
        created_at = batch.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if now - created_at < XLSX_PROCESSING_STALE_AFTER:
            continue
        batch.status = "completed_with_errors"
        batch.error_count = max(batch.error_count, 1)
        for item in batch.items:
            if item.status == "processing":
                item.status = "error"
                item.message = "Analyse XLSX interrompue ou trop longue. Relance l'import avec le meme fichier."
        changed = True
    if changed:
        db.commit()


def get_invoice_import(db: Session, city_id: int, invoice_import_id: int) -> EnergyInvoiceImport | None:
    return db.query(EnergyInvoiceImport).filter_by(city_id=city_id, id=invoice_import_id).first()


def analyze_existing_invoice_import(
    db: Session,
    city_id: int,
    invoice_import_id: int,
) -> EnergyInvoiceImport | None:
    invoice_import = get_invoice_import(db, city_id, invoice_import_id)
    if invoice_import is None:
        return None
    analyze_invoice_import(db, invoice_import)
    db.commit()
    db.refresh(invoice_import)
    return invoice_import


def update_invoice_decision(
    db: Session,
    city_id: int,
    invoice_import_id: int,
    user_id: int,
    decision_status: str,
    decision_comment: str | None,
) -> EnergyInvoiceImport | None:
    if decision_status not in DECISION_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Statut de decision facture invalide.")

    invoice_import = get_invoice_import(db, city_id, invoice_import_id)
    if invoice_import is None:
        return None

    invoice_import.decision_status = decision_status
    invoice_import.decision_comment = (decision_comment or "").strip() or None
    invoice_import.decision_by_user_id = user_id
    invoice_import.decision_updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(invoice_import)
    return invoice_import


def delete_invoice_import(db: Session, city_id: int, invoice_import_id: int) -> bool:
    invoice_import = get_invoice_import(db, city_id, invoice_import_id)
    if invoice_import is None:
        return False
    storage_path = invoice_import.storage_path
    db.delete(invoice_import)
    db.commit()
    _cleanup_storage_path_if_orphan(db, storage_path)
    return True


def delete_all_invoice_imports(db: Session, city_id: int) -> dict[str, int]:
    """Supprime tous les EnergyInvoiceImport d'une city + fichiers physiques.

    Gère correctement les fichiers XLSX partagés par plusieurs imports :
    on collecte les storage_path uniques avant suppression DB, puis on
    nettoie les fichiers une seule fois après le commit. Retour :
        {"deleted": N, "files_removed": M, "files_kept": K}
    où "files_kept" = chemins manquants ou inaccessibles.
    """
    imports = (
        db.query(EnergyInvoiceImport)
        .filter(EnergyInvoiceImport.city_id == city_id)
        .all()
    )
    deleted_count = len(imports)
    storage_paths: set[str] = {imp.storage_path for imp in imports if imp.storage_path}

    for imp in imports:
        db.delete(imp)
    db.commit()

    files_removed = 0
    files_kept = 0
    for path_str in storage_paths:
        try:
            removed = _cleanup_storage_path_if_orphan(db, path_str)
            if removed:
                files_removed += 1
            else:
                files_kept += 1
        except Exception:
            files_kept += 1
    return {"deleted": deleted_count, "files_removed": files_removed, "files_kept": files_kept}


def _cleanup_storage_path_if_orphan(db: Session, storage_path: str | None) -> bool:
    """Supprime le fichier sur disque uniquement si plus AUCUN EnergyInvoiceImport
    ne référence ce chemin. Utilisé pour ne pas casser l'analyse XLSX (1 fichier
    partagé par N imports). Retour True si fichier effectivement supprimé.
    """
    if not storage_path:
        return False
    still_referenced = (
        db.query(EnergyInvoiceImport.id)
        .filter(EnergyInvoiceImport.storage_path == storage_path)
        .first()
    )
    if still_referenced is not None:
        return False
    try:
        Path(storage_path).unlink(missing_ok=True)
        return True
    except OSError:
        return False


async def create_invoice_import(
    db: Session,
    city_id: int,
    uploaded_by_user_id: int,
    file: UploadFile,
) -> tuple[EnergyInvoiceImport, bool]:
    data = await file.read()
    return create_invoice_import_from_bytes(
        db,
        city_id,
        uploaded_by_user_id,
        filename=file.filename,
        content_type=file.content_type,
        data=data,
        source="manual_upload",
    )


def create_invoice_import_from_bytes(
    db: Session,
    city_id: int,
    uploaded_by_user_id: int,
    *,
    filename: str | None,
    content_type: str | None,
    data: bytes,
    source: str,
    commit: bool = True,
) -> tuple[EnergyInvoiceImport, bool]:
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fichier vide.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Fichier limite a 50 Mo.")

    original_filename = _safe_original_filename(filename)
    suffix = _safe_suffix(original_filename)
    checksum = sha256(data).hexdigest()

    existing = (
        db.query(EnergyInvoiceImport)
        .filter_by(city_id=city_id, sha256=checksum)
        .order_by(EnergyInvoiceImport.id.asc())
        .first()
    )
    if existing is not None:
        if existing.analysis_status in {"pending", "failed"}:
            analyze_invoice_import(db, existing)
            if commit:
                db.commit()
                db.refresh(existing)
            else:
                db.flush()
        return existing, True

    target_dir = Path(settings.invoice_storage_dir) / str(city_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{uuid4().hex}{suffix}"
    storage_path = target_dir / stored_filename
    storage_path.write_bytes(data)

    invoice_import = EnergyInvoiceImport(
        city_id=city_id,
        uploaded_by_user_id=uploaded_by_user_id,
        source=source,
        original_filename=original_filename,
        stored_filename=stored_filename,
        storage_path=str(storage_path),
        content_type=content_type,
        file_size_bytes=len(data),
        sha256=checksum,
        supplier_guess=_guess_supplier(original_filename),
        status="imported",
        analysis_status="pending",
    )
    db.add(invoice_import)
    db.flush()
    analyze_invoice_import(db, invoice_import)
    if commit:
        db.commit()
        db.refresh(invoice_import)
    else:
        db.flush()
    return invoice_import, False


async def create_invoice_batch(
    db: Session,
    city_id: int,
    uploaded_by_user_id: int,
    files: list[UploadFile],
) -> EnergyInvoiceBatch:
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Aucun fichier recu.")

    batch = EnergyInvoiceBatch(city_id=city_id, uploaded_by_user_id=uploaded_by_user_id)
    db.add(batch)
    db.flush()

    for file in files:
        data = await file.read()
        original_filename = _safe_original_filename(file.filename)
        suffix = Path(original_filename).suffix.lower()
        if not data:
            _append_batch_item(batch, original_filename, "error", "Fichier vide.", file.content_type, 0)
            continue
        if len(data) > MAX_UPLOAD_BYTES:
            _append_batch_item(
                batch,
                original_filename,
                "error",
                "Fichier limite a 50 Mo.",
                file.content_type,
                len(data),
            )
            continue
        if suffix == ".zip":
            _append_zip_members(db, batch, city_id, uploaded_by_user_id, original_filename, data)
            continue
        if suffix != ".pdf":
            _append_batch_item(
                batch,
                original_filename,
                "ignored",
                "Import lot V1 limite aux PDF ENGIE ou archives ZIP de PDF.",
                file.content_type,
                len(data),
                checksum=sha256(data).hexdigest(),
            )
            continue
        _append_pdf_item(
            db,
            batch,
            city_id,
            uploaded_by_user_id,
            original_filename,
            file.content_type,
            data,
            source="manual_batch",
        )

    _refresh_batch_counts(batch)
    db.commit()
    db.refresh(batch)
    return batch


def _append_zip_members(
    db: Session,
    batch: EnergyInvoiceBatch,
    city_id: int,
    uploaded_by_user_id: int,
    archive_filename: str,
    data: bytes,
) -> None:
    try:
        archive = ZipFile(BytesIO(data))
    except BadZipFile:
        _append_batch_item(batch, archive_filename, "error", "Archive ZIP illisible.", "application/zip", len(data))
        return

    with archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            filename = _safe_original_filename(member.filename)
            if Path(filename).suffix.lower() != ".pdf":
                _append_batch_item(
                    batch,
                    filename,
                    "ignored",
                    "Fichier ZIP ignore : seuls les PDF sont traites.",
                    None,
                    member.file_size,
                    archive_filename=archive_filename,
                )
                continue
            if member.file_size > MAX_UPLOAD_BYTES:
                _append_batch_item(
                    batch,
                    filename,
                    "error",
                    "PDF ZIP limite a 50 Mo.",
                    "application/pdf",
                    member.file_size,
                    archive_filename=archive_filename,
                )
                continue
            try:
                member_data = archive.read(member)
            except Exception as exc:
                _append_batch_item(
                    batch,
                    filename,
                    "error",
                    f"Lecture ZIP impossible : {exc}",
                    "application/pdf",
                    member.file_size,
                    archive_filename=archive_filename,
                )
                continue
            _append_pdf_item(
                db,
                batch,
                city_id,
                uploaded_by_user_id,
                filename,
                "application/pdf",
                member_data,
                source="manual_zip",
                archive_filename=archive_filename,
            )


def _append_pdf_item(
    db: Session,
    batch: EnergyInvoiceBatch,
    city_id: int,
    uploaded_by_user_id: int,
    filename: str,
    content_type: str | None,
    data: bytes,
    *,
    source: str,
    archive_filename: str | None = None,
) -> None:
    checksum = sha256(data).hexdigest()
    try:
        invoice_import, is_duplicate = create_invoice_import_from_bytes(
            db,
            city_id,
            uploaded_by_user_id,
            filename=filename,
            content_type=content_type,
            data=data,
            source=source,
            commit=False,
        )
    except HTTPException as exc:
        _append_batch_item(
            batch,
            filename,
            "error",
            str(exc.detail),
            content_type,
            len(data),
            checksum=checksum,
            archive_filename=archive_filename,
        )
        return
    except Exception as exc:
        _append_batch_item(
            batch,
            filename,
            "error",
            f"Import impossible : {exc}",
            content_type,
            len(data),
            checksum=checksum,
            archive_filename=archive_filename,
        )
        return

    if is_duplicate:
        item_status = "duplicate"
        message = "Facture deja importee."
    elif invoice_import.analysis_status == "failed":
        item_status = "error"
        message = invoice_import.error_message or "Analyse facture impossible."
    else:
        item_status = "imported"
        message = "Facture importee et analysee."
    _append_batch_item(
        batch,
        filename,
        item_status,
        message,
        content_type,
        len(data),
        checksum=checksum,
        archive_filename=archive_filename,
        invoice_import=invoice_import,
    )


def _append_batch_item(
    batch: EnergyInvoiceBatch,
    filename: str,
    status_value: str,
    message: str,
    content_type: str | None,
    file_size_bytes: int | None,
    *,
    checksum: str | None = None,
    archive_filename: str | None = None,
    invoice_import: EnergyInvoiceImport | None = None,
) -> None:
    batch.items.append(
        EnergyInvoiceBatchItem(
            original_filename=filename,
            archive_filename=archive_filename,
            content_type=content_type,
            file_size_bytes=file_size_bytes,
            sha256=checksum,
            status=status_value,
            message=message,
            invoice_import=invoice_import,
        )
    )


def _refresh_batch_counts(batch: EnergyInvoiceBatch) -> None:
    batch.file_count = len(batch.items)
    batch.imported_count = sum(1 for item in batch.items if item.status == "imported")
    batch.duplicate_count = sum(1 for item in batch.items if item.status == "duplicate")
    batch.ignored_count = sum(1 for item in batch.items if item.status == "ignored")
    batch.error_count = sum(1 for item in batch.items if item.status == "error")
    batch.status = "completed_with_errors" if batch.error_count else "completed"
