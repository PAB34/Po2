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
from app.services import supplier_registry
from app.services.invoice_analysis import apply_parsed_to_invoice_import
from app.services.invoice_parsers.engie_xlsx import parse_engie_xlsx

LOG = logging.getLogger(__name__)

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SOURCE_TAG = "engie_xlsx_export"
_ENGIE = supplier_registry.SUPPLIERS["ENGIE"]


def import_engie_xlsx(
    db: Session,
    *,
    city_id: int,
    user_id: int,
    file_bytes: bytes,
    original_filename: str,
    content_type: str | None = None,
    force_update: bool = False,
) -> dict[str, Any]:
    """Persiste le XLSX, parse les bordereaux, crée ou met à jour les EnergyInvoiceImport.

    Comportement par bordereau :
    - Inconnu (invoice_number absent en base) → création
    - Connu + force_update=False → skip (par défaut, préserve l'analyse existante)
    - Connu + force_update=True → upsert : on RE-APPLIQUE l'analyse sur l'import existant
      (le contrôle BPU/TURPE/etc est rejoué avec les nouvelles règles), mais on PRÉSERVE
      les champs de décision utilisateur (decision_status, decision_comment,
      decision_by_user_id, decision_updated_at). Le fichier XLSX courant remplace
      le storage_path précédent.

    Returns: résumé structuré pour la réponse HTTP :
        {
          "source": "engie_xlsx_export",
          "filename": str,
          "total_bordereaux": int,
          "created": int,
          "updated": int,
          "duplicates": int,   # skip car déjà existant (mode normal)
          "errors": int,
          "imports": [...],
          "updates": [...],
          "duplicates_detail": [...],
          "errors_detail": [...],
        }
    """
    storage_path, sha256_hex, file_size = _persist_file(file_bytes, original_filename)

    try:
        bordereaux = parse_engie_xlsx(storage_path)
    except Exception as exc:
        LOG.exception("Parse XLSX ENGIE échoué")
        raise ValueError(f"Lecture du XLSX impossible : {exc}") from exc

    created_imports: list[dict[str, Any]] = []
    updated_imports: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    # Storage paths obsolètes après upsert (à nettoyer si plus aucun import ne les référence)
    obsolete_storage_paths: set[str] = set()

    for parsed in bordereaux:
        invoice_number = (parsed.get("invoice") or {}).get("invoice_number")
        if not invoice_number:
            errors.append({"invoice_number": None, "message": "Bordereau sans n° de facture, ignoré."})
            continue

        # Dédup : un import avec ce invoice_number existe déjà pour la même city ?
        existing_import = db.execute(
            select(EnergyInvoiceImport)
            .where(EnergyInvoiceImport.city_id == city_id)
            .where(EnergyInvoiceImport.invoice_number == invoice_number)
            .limit(1)
        ).scalar_one_or_none()

        if existing_import is not None:
            should_repair_failed_xlsx = (
                existing_import.source == SOURCE_TAG
                and existing_import.analysis_status == "failed"
                and _has_parser_failed_issue(existing_import)
            )
            if not force_update and not should_repair_failed_xlsx:
                duplicates.append(
                    {
                        "invoice_number": invoice_number,
                        "existing_import_id": existing_import.id,
                        "existing_source": existing_import.source,
                    }
                )
                continue

            # --- Upsert : on met à jour l'import existant ---
            # Préserve les champs de décision utilisateur (jamais écrasés par l'import)
            preserved_decision = {
                "decision_status": existing_import.decision_status,
                "decision_comment": existing_import.decision_comment,
                "decision_by_user_id": existing_import.decision_by_user_id,
                "decision_updated_at": existing_import.decision_updated_at,
            }
            previous_storage_path = existing_import.storage_path
            # On pointe l'import existant vers le nouveau fichier XLSX
            existing_import.source = SOURCE_TAG
            existing_import.original_filename = original_filename
            existing_import.stored_filename = storage_path.name
            existing_import.storage_path = str(storage_path)
            existing_import.content_type = content_type or XLSX_CONTENT_TYPE
            existing_import.file_size_bytes = file_size
            existing_import.sha256 = sha256_hex
            existing_import.supplier_guess = _ENGIE.code
            existing_import.energy_type = _ENGIE.energy
            existing_import.analysis_status = "pending"
            db.flush()
            try:
                apply_parsed_to_invoice_import(db, existing_import, parsed)
                # Restaure les champs décision après l'analyse
                for field, value in preserved_decision.items():
                    setattr(existing_import, field, value)
                db.flush()
            except Exception as exc:
                LOG.exception("Re-analyse bordereau %s échouée", invoice_number)
                errors.append({"invoice_number": invoice_number, "message": str(exc)})
                continue
            if previous_storage_path and previous_storage_path != str(storage_path):
                obsolete_storage_paths.add(previous_storage_path)
            updated_imports.append(
                {
                    "id": existing_import.id,
                    "invoice_number": invoice_number,
                    "control_status": existing_import.control_status,
                    "site_count": existing_import.site_count,
                    "total_ttc": existing_import.total_ttc,
                    "decision_preserved": preserved_decision["decision_status"],
                    "repair": should_repair_failed_xlsx,
                }
            )
            continue

        # --- Création : nouveau bordereau ---
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
            supplier_guess=_ENGIE.code,
            energy_type=_ENGIE.energy,
            status="imported",
            analysis_status="pending",
        )
        db.add(invoice_import)
        db.flush()
        try:
            apply_parsed_to_invoice_import(db, invoice_import, parsed)
            db.flush()
        except Exception as exc:
            LOG.exception("Analyse bordereau %s échouée", invoice_number)
            errors.append({"invoice_number": invoice_number, "message": str(exc)})
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

    # Nettoyage best-effort des anciens fichiers devenus orphelins après upsert
    for old_path in obsolete_storage_paths:
        still_used = db.execute(
            select(EnergyInvoiceImport.id)
            .where(EnergyInvoiceImport.storage_path == old_path)
            .limit(1)
        ).first()
        if still_used is None:
            try:
                from pathlib import Path as _P
                _P(old_path).unlink(missing_ok=True)
            except OSError:
                pass

    return {
        "source": SOURCE_TAG,
        "filename": original_filename,
        "total_bordereaux": len(bordereaux),
        "created": len(created_imports),
        "updated": len(updated_imports),
        "duplicates": len(duplicates),
        "errors": len(errors),
        "imports": created_imports,
        "updates": updated_imports,
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


def _has_parser_failed_issue(invoice_import: EnergyInvoiceImport) -> bool:
    """Detecte les imports XLSX coinces dans l'ancien parseur fichier PDF-only."""
    try:
        report = json.loads(invoice_import.control_report_json or "{}")
    except (TypeError, json.JSONDecodeError):
        return False
    issues = report.get("issues")
    if not isinstance(issues, list):
        return False
    return any(isinstance(issue, dict) and issue.get("code") == "PARSER_FAILED" for issue in issues)
