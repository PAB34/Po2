"""Orchestre l'import d'un export XLSX ENGIE multi-factures.

Un seul fichier XLSX contient ~100-200 factures (bordereaux). Cet
orchestrateur :

1. Sauve le fichier XLSX une seule fois sur disque
2. Le parse en N `parsed` dicts (un par bordereau)
3. Pour chaque bordereau :
   - Dédup : skip si un EnergyInvoiceImport existe déjà pour cette city
     avec ce invoice_number
   - Sinon crée un EnergyInvoiceImport pointant vers le même fichier XLSX
     (stored_filename / storage_path) et applique le pipeline d'analyse
     standard (mêmes contrôles BPU/TURPE/taxes/périodes)
4. Retourne un résumé chiffré { created, duplicates, errors }
"""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.invoice import EnergyInvoiceImport
from app.services.invoice_analysis import apply_parsed_to_invoice_import
from app.services.invoice_parsers.engie_xlsx import parse_engie_xlsx

LOG = logging.getLogger(__name__)

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SOURCE_TAG = "engie_xlsx_export"


def import_engie_xlsx(
    db: Session,
    *,
    city_id: int,
    user_id: int,
    file_bytes: bytes,
    original_filename: str,
    content_type: str | None = None,
) -> dict[str, Any]:
    """Persiste le XLSX, parse les bordereaux, crée les EnergyInvoiceImport.

    Returns: résumé structuré pour la réponse HTTP :
        {
          "source": "engie_xlsx_export",
          "filename": str,
          "total_bordereaux": int,
          "created": int,
          "duplicates": int,
          "errors": int,
          "imports": [{id, invoice_number, status}, ...],
          "duplicates_detail": [{invoice_number, existing_import_id}, ...],
          "errors_detail": [{invoice_number, message}, ...],
        }
    """
    storage_path, sha256_hex, file_size = _persist_file(file_bytes, original_filename)

    try:
        bordereaux = parse_engie_xlsx(storage_path)
    except Exception as exc:
        LOG.exception("Parse XLSX ENGIE échoué")
        raise ValueError(f"Lecture du XLSX impossible : {exc}") from exc

    created_imports: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for parsed in bordereaux:
        invoice_number = (parsed.get("invoice") or {}).get("invoice_number")
        if not invoice_number:
            errors.append({"invoice_number": None, "message": "Bordereau sans n° de facture, ignoré."})
            continue

        # Dédup : un import avec ce invoice_number existe déjà pour la même city ?
        existing = db.execute(
            select(EnergyInvoiceImport.id, EnergyInvoiceImport.source)
            .where(EnergyInvoiceImport.city_id == city_id)
            .where(EnergyInvoiceImport.invoice_number == invoice_number)
            .limit(1)
        ).first()
        if existing is not None:
            duplicates.append(
                {
                    "invoice_number": invoice_number,
                    "existing_import_id": existing.id,
                    "existing_source": existing.source,
                }
            )
            continue

        # Crée un EnergyInvoiceImport partageant le fichier XLSX commun
        invoice_import = EnergyInvoiceImport(
            city_id=city_id,
            uploaded_by_user_id=user_id,
            source=SOURCE_TAG,
            original_filename=original_filename,
            stored_filename=storage_path.name,
            storage_path=str(storage_path),
            content_type=content_type or XLSX_CONTENT_TYPE,
            file_size_bytes=file_size,
            sha256=sha256_hex,
            supplier_guess="ENGIE",
            status="imported",
            analysis_status="pending",
        )
        db.add(invoice_import)
        db.flush()  # nécessaire pour avoir invoice_import.id avant la persistance des sites

        try:
            apply_parsed_to_invoice_import(db, invoice_import, parsed)
            db.flush()
        except Exception as exc:
            LOG.exception("Analyse bordereau %s échouée", invoice_number)
            errors.append({"invoice_number": invoice_number, "message": str(exc)})
            # On garde l'import même en erreur pour traçabilité (status=failed posé par apply_…)
            continue

        created_imports.append(
            {
                "id": invoice_import.id,
                "invoice_number": invoice_number,
                "control_status": invoice_import.control_status,
                "site_count": invoice_import.site_count,
                "total_ttc": invoice_import.total_ttc,
            }
        )

    db.commit()

    return {
        "source": SOURCE_TAG,
        "filename": original_filename,
        "total_bordereaux": len(bordereaux),
        "created": len(created_imports),
        "duplicates": len(duplicates),
        "errors": len(errors),
        "imports": created_imports,
        "duplicates_detail": duplicates,
        "errors_detail": errors,
    }


# ── Persistance fichier XLSX ────────────────────────────────────────────────


def _persist_file(file_bytes: bytes, original_filename: str) -> tuple[Path, str, int]:
    """Stocke le XLSX dans settings.invoice_storage_dir avec un nom unique.

    Returns: (storage_path, sha256_hex, file_size_bytes).
    """
    sha256_hex = hashlib.sha256(file_bytes).hexdigest()
    storage_dir = Path(settings.invoice_storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    rand = secrets.token_hex(4)
    safe_name = Path(original_filename).stem.replace(" ", "_")[:60]
    stored_filename = f"engie_xlsx_{timestamp}_{rand}_{safe_name}.xlsx"
    storage_path = storage_dir / stored_filename
    storage_path.write_bytes(file_bytes)
    return storage_path, sha256_hex, len(file_bytes)
