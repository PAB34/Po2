from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.invoice import EnergyInvoiceBatch, EnergyInvoiceBatchItem, EnergyInvoiceImport
from app.services.invoice_analysis import analyze_invoice_import

ALLOWED_EXTENSIONS = {".pdf", ".xml", ".csv", ".txt", ".xlsx", ".xls", ".zip"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
DECISION_STATUSES = {"to_review", "approved", "rejected", "dispute_sent"}


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
        .filter_by(city_id=city_id)
        .order_by(EnergyInvoiceImport.created_at.desc(), EnergyInvoiceImport.id.desc())
        .all()
    )


def list_invoice_batches(db: Session, city_id: int) -> list[EnergyInvoiceBatch]:
    return (
        db.query(EnergyInvoiceBatch)
        .filter_by(city_id=city_id)
        .order_by(EnergyInvoiceBatch.created_at.desc(), EnergyInvoiceBatch.id.desc())
        .all()
    )


def get_invoice_batch(db: Session, city_id: int, batch_id: int) -> EnergyInvoiceBatch | None:
    return db.query(EnergyInvoiceBatch).filter_by(city_id=city_id, id=batch_id).first()


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
    try:
        Path(invoice_import.storage_path).unlink(missing_ok=True)
    except OSError:
        pass
    db.delete(invoice_import)
    db.commit()
    return True


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
