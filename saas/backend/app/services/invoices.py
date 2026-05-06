from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.invoice import EnergyInvoiceImport
from app.services.invoice_analysis import analyze_invoice_import

ALLOWED_EXTENSIONS = {".pdf", ".xml", ".csv", ".txt", ".xlsx", ".xls", ".zip"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


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


async def create_invoice_import(
    db: Session,
    city_id: int,
    uploaded_by_user_id: int,
    file: UploadFile,
) -> tuple[EnergyInvoiceImport, bool]:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fichier vide.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Fichier limite a 50 Mo.")

    original_filename = _safe_original_filename(file.filename)
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
            db.commit()
            db.refresh(existing)
        return existing, True

    target_dir = Path(settings.invoice_storage_dir) / str(city_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{uuid4().hex}{suffix}"
    storage_path = target_dir / stored_filename
    storage_path.write_bytes(data)

    invoice_import = EnergyInvoiceImport(
        city_id=city_id,
        uploaded_by_user_id=uploaded_by_user_id,
        source="manual_upload",
        original_filename=original_filename,
        stored_filename=stored_filename,
        storage_path=str(storage_path),
        content_type=file.content_type,
        file_size_bytes=len(data),
        sha256=checksum,
        supplier_guess=_guess_supplier(original_filename),
        status="imported",
        analysis_status="pending",
    )
    db.add(invoice_import)
    db.flush()
    analyze_invoice_import(db, invoice_import)
    db.commit()
    db.refresh(invoice_import)
    return invoice_import, False
