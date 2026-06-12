"""Orchestre l'import d'un export CSV de facturation EDF (un fichier = N factures).

Même flux que l'import XLSX ENGIE : persiste le fichier, parse les factures,
crée/met à jour un EnergyInvoiceImport par numéro de facture, en réutilisant le
pipeline d'analyse/contrôle/normalisation partagé (apply_parsed_to_invoice_import).
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.invoice import EnergyInvoiceImport
from app.services import supplier_registry
from app.services.invoice_analysis import apply_parsed_to_invoice_import
from app.services.invoice_parsers.edf_csv import parse_edf_csv

LOG = logging.getLogger(__name__)

CSV_CONTENT_TYPE = "text/csv"
SOURCE_TAG = "edf_csv_export"
_EDF = supplier_registry.SUPPLIERS["EDF"]


def _persist_file(file_bytes: bytes, original_filename: str) -> tuple[Path, str, int]:
    sha256_hex = hashlib.sha256(file_bytes).hexdigest()
    storage_dir = Path(settings.invoice_storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    rand = secrets.token_hex(4)
    safe_name = Path(original_filename).stem.replace(" ", "_")[:60]
    storage_path = storage_dir / f"edf_csv_{timestamp}_{rand}_{safe_name}.csv"
    storage_path.write_bytes(file_bytes)
    return storage_path, sha256_hex, len(file_bytes)


def import_edf_csv(
    db: Session,
    *,
    city_id: int,
    user_id: int,
    file_bytes: bytes,
    original_filename: str,
    content_type: str | None = None,
    force_update: bool = False,
) -> dict[str, Any]:
    storage_path, sha256_hex, file_size = _persist_file(file_bytes, original_filename)

    try:
        bordereaux = parse_edf_csv(storage_path)
    except Exception as exc:
        LOG.exception("Parse CSV EDF échoué")
        raise ValueError(f"Lecture du CSV EDF impossible : {exc}") from exc

    created: list[dict[str, Any]] = []
    updated: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for parsed in bordereaux:
        invoice_number = (parsed.get("invoice") or {}).get("invoice_number")
        if not invoice_number:
            errors.append({"invoice_number": None, "message": "Facture sans numéro, ignorée."})
            continue

        existing = db.execute(
            select(EnergyInvoiceImport)
            .where(EnergyInvoiceImport.city_id == city_id)
            .where(EnergyInvoiceImport.invoice_number == invoice_number)
            .limit(1)
        ).scalar_one_or_none()

        if existing is not None:
            if not force_update:
                duplicates.append({"invoice_number": invoice_number, "existing_import_id": existing.id})
                continue
            preserved = {
                "decision_status": existing.decision_status,
                "decision_comment": existing.decision_comment,
                "decision_by_user_id": existing.decision_by_user_id,
                "decision_updated_at": existing.decision_updated_at,
            }
            existing.source = SOURCE_TAG
            existing.original_filename = original_filename
            existing.stored_filename = storage_path.name
            existing.storage_path = str(storage_path)
            existing.content_type = content_type or CSV_CONTENT_TYPE
            existing.file_size_bytes = file_size
            existing.sha256 = sha256_hex
            existing.supplier_guess = _EDF.code
            existing.energy_type = _EDF.energy
            existing.analysis_status = "pending"
            db.flush()
            try:
                apply_parsed_to_invoice_import(db, existing, parsed)
                for field, value in preserved.items():
                    setattr(existing, field, value)
                db.flush()
            except Exception as exc:
                LOG.exception("Re-analyse facture EDF %s échouée", invoice_number)
                errors.append({"invoice_number": invoice_number, "message": str(exc)})
                continue
            updated.append({"id": existing.id, "invoice_number": invoice_number})
            continue

        invoice_import = EnergyInvoiceImport(
            city_id=city_id,
            uploaded_by_user_id=user_id,
            source=SOURCE_TAG,
            original_filename=original_filename,
            stored_filename=storage_path.name,
            storage_path=str(storage_path),
            content_type=content_type or CSV_CONTENT_TYPE,
            file_size_bytes=file_size,
            sha256=sha256_hex,
            supplier_guess=_EDF.code,
            energy_type=_EDF.energy,
            status="imported",
            analysis_status="pending",
        )
        db.add(invoice_import)
        db.flush()
        try:
            apply_parsed_to_invoice_import(db, invoice_import, parsed)
            db.flush()
        except Exception as exc:
            LOG.exception("Analyse facture EDF %s échouée", invoice_number)
            errors.append({"invoice_number": invoice_number, "message": str(exc)})
            continue
        created.append({"id": invoice_import.id, "invoice_number": invoice_number})

    db.commit()

    return {
        "source": SOURCE_TAG,
        "filename": original_filename,
        "total_bordereaux": len(bordereaux),
        "created": len(created),
        "updated": len(updated),
        "duplicates": len(duplicates),
        "errors": len(errors),
        "imports": created,
        "updates": updated,
        "duplicates_detail": duplicates,
        "errors_detail": errors,
    }
