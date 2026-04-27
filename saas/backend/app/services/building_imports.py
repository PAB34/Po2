from __future__ import annotations

from io import BytesIO
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.local import Local
from app.models.user import User
from app.schemas.building import BuildingCreate, BuildingImportConfig, LocalCreate
from app.services.buildings import create_building, create_local
from app.services.cities import get_city_by_id

_SUPPORTED_EXTENSIONS = {".csv", ".xls", ".xlsx", ".xlsm"}
_PREVIEW_LIMIT = 12

_FIELD_CANDIDATES: dict[str, list[str]] = {
    "building_name": ["designation", "nom court", "nom batiment", "bâtiment", "batiment", "libelle"],
    "building_alias": ["nom court", "designation courte", "label"],
    "building_external_id": ["nobatiment", "n batiment", "numero batiment", "id batiment"],
    "local_name": ["designation", "nom court", "nom local", "local"],
    "local_external_id": ["nolocal", "n local", "numero local", "id local"],
    "local_level": ["niveau", "etage", "étage"],
    "local_usage": ["usage", "affectation"],
    "local_occupancy_status": ["statut occupation", "occupation", "statut d occupation"],
    "local_comment": ["commentaire", "observation", "remarque"],
    "local_surface_m2": ["surface", "surface m2", "superficie"],
    "address": ["adresse", "adresse du local", "adresse principale"],
    "address_extra": ["complement adresse", "complément adresse", "adresse complement", "complément d adresse"],
    "city_name": ["commune", "commune du local", "ville", "nom commune"],
    "parcel_reference": ["n parcelle", "noparcelle", "numero parcelle", "reference parcelle", "parcelle", "n° parcelle", "n°parcelle"],
    "parcel_section": ["section cadastrale", "section"],
    "parcel_number": ["numero plan", "num plan", "numero parcelle plan", "plan"],
    "street_number": ["numero voirie", "numero", "num voie", "n voie"],
    "street_repeat": ["indice repetition", "indice répétition", "bis ter", "repetition"],
    "street_type": ["nature voie", "type voie", "voie type"],
    "street_name": ["nom voie", "voie", "nom de voie"],
    "parent_name": ["parent", "batiment parent", "bâtiment parent", "site parent"],
    "local_type": ["type local", "categorie local", "catégorie local"],
}

_ROW_TYPE_CANDIDATES = ["typologie", "type", "nature", "entity type"]


def _normalize_text(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_text(value: object) -> str:
    text = str(value or "").strip()
    return re.sub(r"\s+", " ", text)


def _clean_optional(value: object) -> str | None:
    text = _clean_text(value)
    return text or None


def _dedupe_columns(columns: list[object]) -> list[str]:
    result: list[str] = []
    seen: dict[str, int] = {}
    for index, column in enumerate(columns, start=1):
        label = _clean_text(column) or f"Colonne {index}"
        counter = seen.get(label, 0)
        seen[label] = counter + 1
        result.append(label if counter == 0 else f"{label} ({counter + 1})")
    return result


def _read_upload_bytes(upload_file: UploadFile) -> tuple[str, bytes, str]:
    filename = upload_file.filename or "import"
    suffix = Path(filename).suffix.lower()
    if suffix not in _SUPPORTED_EXTENSIONS:
        raise ValueError("Format non pris en charge. Utilise CSV, XLS, XLSX ou XLSM.")
    content = upload_file.file.read()
    if not content:
        raise ValueError("Le fichier importé est vide.")
    return filename, content, suffix


def _read_dataframe_from_upload(
    upload_file: UploadFile,
    sheet_name: str | None,
    header_row_index: int,
) -> tuple[str, list[str], str, pd.DataFrame]:
    if header_row_index < 0:
        raise ValueError("La ligne d'entête doit être positive ou nulle.")

    filename, content, suffix = _read_upload_bytes(upload_file)
    buffer = BytesIO(content)

    try:
        if suffix == ".csv":
            dataframe = pd.read_csv(buffer, sep=None, engine="python", dtype=str, keep_default_na=False)
            sheet_names = ["CSV"]
            selected_sheet = "CSV"
        else:
            workbook = pd.ExcelFile(buffer)
            sheet_names = list(workbook.sheet_names)
            if not sheet_names:
                raise ValueError("Le fichier Excel ne contient aucune feuille exploitable.")
            selected_sheet = sheet_name or sheet_names[0]
            if selected_sheet not in sheet_names:
                raise ValueError(f"Feuille introuvable : {selected_sheet}")
            dataframe = pd.read_excel(
                workbook,
                sheet_name=selected_sheet,
                header=header_row_index,
                dtype=str,
                keep_default_na=False,
            )
    except ValueError:
        raise
    except Exception as error:
        raise ValueError(f"Impossible de lire le fichier importé : {error}") from error

    dataframe.columns = _dedupe_columns(list(dataframe.columns))
    dataframe = dataframe.fillna("")
    dataframe = dataframe.astype(str)
    dataframe["_source_row_number"] = list(range(header_row_index + 2, header_row_index + 2 + len(dataframe)))
    return filename, sheet_names, selected_sheet, dataframe


def _suggest_column(columns: list[str], candidates: list[str]) -> str | None:
    normalized_candidates = [_normalize_text(candidate) for candidate in candidates]
    normalized_columns = {column: _normalize_text(column) for column in columns}

    for candidate in normalized_candidates:
        for column, normalized in normalized_columns.items():
            if normalized == candidate:
                return column
    for candidate in normalized_candidates:
        for column, normalized in normalized_columns.items():
            if candidate and candidate in normalized:
                return column
    return None


def _default_row_type_values(series: pd.Series) -> tuple[list[str], list[str]]:
    normalized_map: dict[str, str] = {}
    for raw in series.tolist():
        label = _clean_text(raw)
        if label:
            normalized_map.setdefault(_normalize_text(label), label)
    building_values = [value for key, value in normalized_map.items() if key == "batiment" or key == "building"]
    local_values = [value for key, value in normalized_map.items() if key == "local"]
    return building_values, local_values


def _build_suggested_config(dataframe: pd.DataFrame) -> dict[str, Any]:
    columns = [column for column in dataframe.columns if column != "_source_row_number"]
    row_type_column = _suggest_column(columns, _ROW_TYPE_CANDIDATES)
    building_row_types: list[str] = []
    local_row_types: list[str] = []
    if row_type_column and row_type_column in dataframe.columns:
        building_row_types, local_row_types = _default_row_type_values(dataframe[row_type_column])

    mapping = {field: _suggest_column(columns, candidates) for field, candidates in _FIELD_CANDIDATES.items()}
    return {
        "row_type_column": row_type_column,
        "building_row_types": building_row_types or (["BATIMENT"] if row_type_column else []),
        "local_row_types": local_row_types or (["LOCAL"] if row_type_column else []),
        "mapping": mapping,
        "skip_existing_buildings": True,
        "create_missing_buildings_for_locals": True,
    }


def analyze_building_import_file(upload_file: UploadFile, sheet_name: str | None, header_row_index: int) -> dict[str, Any]:
    filename, sheet_names, selected_sheet, dataframe = _read_dataframe_from_upload(upload_file, sheet_name, header_row_index)
    suggested_config = _build_suggested_config(dataframe)
    row_type_column = suggested_config["row_type_column"]
    detected_values: list[str] = []
    if row_type_column and row_type_column in dataframe.columns:
        detected_values = [
            value
            for value in dict.fromkeys(_clean_text(item) for item in dataframe[row_type_column].tolist() if _clean_text(item)).keys()
        ]

    sample_rows = dataframe.drop(columns=["_source_row_number"], errors="ignore").head(5).to_dict(orient="records")
    return {
        "filename": filename,
        "available_sheets": sheet_names,
        "selected_sheet": selected_sheet,
        "header_row_index": header_row_index,
        "columns": [column for column in dataframe.columns if column != "_source_row_number"],
        "total_rows": int(len(dataframe)),
        "sample_rows": [{key: _clean_text(value) for key, value in row.items()} for row in sample_rows],
        "detected_row_type_values": detected_values[:20],
        "suggested_config": suggested_config,
    }


def _get_row_value(row: dict[str, Any], mapping: dict[str, str | None], field: str) -> str:
    column = mapping.get(field)
    if not column:
        return ""
    return _clean_text(row.get(column, ""))


def _split_parcel_reference(parcel_reference: str) -> tuple[str | None, str | None]:
    cleaned = re.sub(r"\s+", "", parcel_reference.upper())
    match = re.search(r"([A-Z]{1,3})(\d{1,4})$", cleaned)
    if not match:
        return None, None
    return match.group(1), match.group(2).zfill(4)


def _compose_address(row: dict[str, Any], mapping: dict[str, str | None], city_name: str | None) -> str | None:
    address = _get_row_value(row, mapping, "address")
    address_extra = _get_row_value(row, mapping, "address_extra")
    if address and address_extra and _normalize_text(address_extra) not in _normalize_text(address):
        address = f"{address} {address_extra}".strip()
    if address:
        return address

    parts = [
        _get_row_value(row, mapping, "street_number"),
        _get_row_value(row, mapping, "street_repeat"),
        _get_row_value(row, mapping, "street_type"),
        _get_row_value(row, mapping, "street_name"),
    ]
    address = " ".join(part for part in parts if part).strip()
    if address and city_name:
        return f"{address}, {city_name}"
    return address or city_name


def _safe_float(value: str) -> float | None:
    cleaned = value.strip().replace(",", ".")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _build_building_identity(
    source_external_id: str | None,
    parcel_reference: str | None,
    address: str | None,
    city_name: str | None,
    building_name: str | None,
) -> str:
    if source_external_id:
        return f"ext::{_normalize_text(source_external_id)}"
    payload = "|".join(
        value for value in [_normalize_text(parcel_reference), _normalize_text(address), _normalize_text(city_name), _normalize_text(building_name)] if value
    )
    return f"fp::{payload}" if payload else ""


def _build_local_identity(source_external_id: str | None, local_name: str | None, local_type: str | None, level: str | None) -> str:
    if source_external_id:
        return f"ext::{_normalize_text(source_external_id)}"
    payload = "|".join(value for value in [_normalize_text(local_name), _normalize_text(local_type), _normalize_text(level)] if value)
    return f"fp::{payload}" if payload else ""


def _build_building_payload_from_row(
    row: dict[str, Any],
    mapping: dict[str, str | None],
    filename: str,
    selected_sheet: str,
    default_city_name: str | None,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    city_name = _get_row_value(row, mapping, "city_name") or (default_city_name or "")
    parcel_reference = _get_row_value(row, mapping, "parcel_reference")
    section = _get_row_value(row, mapping, "parcel_section")
    numero_plan = _get_row_value(row, mapping, "parcel_number")
    derived_section, derived_numero_plan = _split_parcel_reference(parcel_reference)
    section = section or (derived_section or "")
    numero_plan = numero_plan or (derived_numero_plan or "")
    building_name = (
        _get_row_value(row, mapping, "building_name")
        or _get_row_value(row, mapping, "building_alias")
        or _get_row_value(row, mapping, "parent_name")
        or parcel_reference
    )
    address = _compose_address(row, mapping, city_name or None)
    source_external_id = _get_row_value(row, mapping, "building_external_id") or None
    identity = _build_building_identity(source_external_id, parcel_reference or None, address, city_name or None, building_name or None)
    if not identity:
        warnings.append("Impossible de construire une clé stable pour ce bâtiment.")

    source_payload = {
        "kind": "building",
        "filename": filename,
        "sheet_name": selected_sheet,
        "source_row_number": row.get("_source_row_number"),
        "row": {key: _clean_text(value) for key, value in row.items() if key != "_source_row_number"},
    }
    payload = {
        "identity": identity,
        "source_external_id": source_external_id,
        "nom_batiment": building_name or None,
        "nom_commune": city_name or None,
        "adresse_reconstituee": address,
        "numero_voirie": _clean_optional(_get_row_value(row, mapping, "street_number")),
        "indice_repetition": _clean_optional(_get_row_value(row, mapping, "street_repeat")),
        "nature_voie": _clean_optional(_get_row_value(row, mapping, "street_type")),
        "nom_voie": _clean_optional(_get_row_value(row, mapping, "street_name")),
        "section": section or None,
        "numero_plan": numero_plan or None,
        "dgfip_reference_norm": parcel_reference or None,
        "dgfip_source_file": filename,
        "dgfip_source_rows_json": json.dumps([row.get("_source_row_number")], ensure_ascii=False),
        "source_payload_json": json.dumps(source_payload, ensure_ascii=False),
    }
    if payload["nom_commune"] is None:
        warnings.append("Commune absente : la commune du compte sera utilisée si disponible.")
    return payload, warnings


def _build_local_payload_from_row(
    row: dict[str, Any],
    mapping: dict[str, str | None],
    filename: str,
    selected_sheet: str,
) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    local_name = _get_row_value(row, mapping, "local_name") or _get_row_value(row, mapping, "local_external_id") or "Local importé"
    local_type = _get_row_value(row, mapping, "local_type") or "EXTERNE"
    local_level = _get_row_value(row, mapping, "local_level") or None
    surface_m2 = _safe_float(_get_row_value(row, mapping, "local_surface_m2"))
    source_external_id = _get_row_value(row, mapping, "local_external_id") or None
    identity = _build_local_identity(source_external_id, local_name, local_type, local_level)
    if not identity:
        warnings.append("Impossible de construire une clé stable pour ce local.")

    source_payload = {
        "kind": "local",
        "filename": filename,
        "sheet_name": selected_sheet,
        "source_row_number": row.get("_source_row_number"),
        "row": {key: _clean_text(value) for key, value in row.items() if key != "_source_row_number"},
    }
    payload = {
        "identity": identity,
        "source_external_id": source_external_id,
        "nom_local": local_name,
        "type_local": local_type,
        "niveau": local_level,
        "surface_m2": surface_m2,
        "usage": _clean_optional(_get_row_value(row, mapping, "local_usage")),
        "statut_occupation": _clean_optional(_get_row_value(row, mapping, "local_occupancy_status")),
        "commentaire": _clean_optional(_get_row_value(row, mapping, "local_comment")),
        "source_payload_json": json.dumps(source_payload, ensure_ascii=False),
    }
    return payload, warnings


def _get_target_city(current_user: User, db: Session) -> tuple[int | None, str | None]:
    if current_user.city_id is None:
        return None, None
    city = get_city_by_id(db, current_user.city_id)
    if city is None:
        return None, None
    return city.id, city.nom_commune


def _match_row_type(raw_value: str, allowed_values: list[str]) -> bool:
    if not allowed_values:
        return True
    normalized_value = _normalize_text(raw_value)
    return any(normalized_value == _normalize_text(entry) for entry in allowed_values if entry)


def _load_existing_building_indexes(db: Session, target_city_id: int | None) -> tuple[dict[str, Building], dict[str, Building]]:
    statement = select(Building)
    if target_city_id is not None:
        statement = statement.where(Building.city_id == target_city_id)
    buildings = list(db.scalars(statement))
    by_external_id: dict[str, Building] = {}
    by_fingerprint: dict[str, Building] = {}
    for building in buildings:
        if building.source_external_id:
            by_external_id[_normalize_text(building.source_external_id)] = building
        fingerprint = _build_building_identity(
            None,
            building.dgfip_reference_norm,
            building.adresse_reconstituee,
            building.nom_commune,
            building.nom_batiment,
        )
        if fingerprint:
            by_fingerprint[fingerprint] = building
    return by_external_id, by_fingerprint


def _load_existing_local_indexes(db: Session, building_id: int) -> tuple[dict[str, Local], dict[str, Local]]:
    statement = select(Local).where(Local.building_id == building_id)
    locals_list = list(db.scalars(statement))
    by_external_id: dict[str, Local] = {}
    by_fingerprint: dict[str, Local] = {}
    for local in locals_list:
        if local.source_external_id:
            by_external_id[_normalize_text(local.source_external_id)] = local
        fingerprint = _build_local_identity(None, local.nom_local, local.type_local, local.niveau)
        if fingerprint:
            by_fingerprint[fingerprint] = local
    return by_external_id, by_fingerprint


def _prepare_import_plan(
    db: Session,
    dataframe: pd.DataFrame,
    filename: str,
    selected_sheet: str,
    config: BuildingImportConfig,
    current_user: User,
) -> dict[str, Any]:
    target_city_id, target_city_name = _get_target_city(current_user, db)
    rows = dataframe.to_dict(orient="records")
    building_entries: dict[str, dict[str, Any]] = {}
    local_entries: list[dict[str, Any]] = []
    warnings: list[str] = []

    for row in rows:
        row_type_value = _clean_text(row.get(config.row_type_column or "", "")) if config.row_type_column else ""
        is_building_row = bool(config.building_row_types) and _match_row_type(row_type_value, config.building_row_types)
        is_local_row = config.row_type_column is not None and bool(config.local_row_types) and _match_row_type(row_type_value, config.local_row_types)
        if config.row_type_column and not is_building_row and not is_local_row:
            continue
        if not config.row_type_column:
            is_building_row = True
            is_local_row = False

        building_payload, building_warnings = _build_building_payload_from_row(
            row,
            config.mapping,
            filename,
            selected_sheet,
            target_city_name,
        )
        warnings.extend(f"Ligne {row.get('_source_row_number')} : {warning}" for warning in building_warnings)

        if is_building_row and building_payload["identity"]:
            existing_entry = building_entries.get(building_payload["identity"])
            if existing_entry is None:
                building_entries[building_payload["identity"]] = {
                    "payload": building_payload,
                    "source_rows": [row.get("_source_row_number")],
                    "warnings": list(building_warnings),
                }
            else:
                existing_entry["source_rows"].append(row.get("_source_row_number"))

        if is_local_row:
            local_payload, local_warnings = _build_local_payload_from_row(row, config.mapping, filename, selected_sheet)
            warnings.extend(f"Ligne {row.get('_source_row_number')} : {warning}" for warning in local_warnings)
            parent_name = _get_row_value(row, config.mapping, "parent_name") or building_payload.get("nom_batiment") or local_payload["nom_local"]
            parent_key = _build_building_identity(
                building_payload.get("source_external_id"),
                building_payload.get("dgfip_reference_norm"),
                building_payload.get("adresse_reconstituee"),
                building_payload.get("nom_commune"),
                parent_name,
            )
            if not parent_key:
                warnings.append(f"Ligne {row.get('_source_row_number')} : local ignoré car aucun rattachement bâtiment exploitable.")
                continue
            if parent_key not in building_entries and config.create_missing_buildings_for_locals:
                synthetic_payload = dict(building_payload)
                synthetic_payload["identity"] = parent_key
                synthetic_payload["nom_batiment"] = parent_name or synthetic_payload.get("nom_batiment")
                building_entries[parent_key] = {
                    "payload": synthetic_payload,
                    "source_rows": [row.get("_source_row_number")],
                    "warnings": ["Bâtiment synthétique créé depuis une ligne local."],
                }
            elif parent_key not in building_entries:
                warnings.append(f"Ligne {row.get('_source_row_number')} : bâtiment parent introuvable pour le local.")
                continue
            local_entries.append(
                {
                    "payload": local_payload,
                    "parent_key": parent_key,
                    "source_row_number": row.get("_source_row_number"),
                    "warnings": local_warnings,
                }
            )

    existing_buildings_by_external, existing_buildings_by_fingerprint = _load_existing_building_indexes(db, target_city_id)
    building_resolution: dict[str, dict[str, Any]] = {}
    building_preview: list[dict[str, Any]] = []

    for key, entry in building_entries.items():
        payload = entry["payload"]
        existing_building = None
        normalized_external_id = _normalize_text(payload.get("source_external_id") or "")
        if normalized_external_id:
            existing_building = existing_buildings_by_external.get(normalized_external_id)
        if existing_building is None:
            existing_building = existing_buildings_by_fingerprint.get(key)
        action = "create"
        if existing_building is not None and config.skip_existing_buildings:
            action = "use_existing"
        building_resolution[key] = {
            "action": action,
            "building": existing_building,
            "payload": payload,
            "source_rows": entry["source_rows"],
            "warnings": entry["warnings"],
        }
        if len(building_preview) < _PREVIEW_LIMIT:
            building_preview.append(
                {
                    "source_row_number": int(entry["source_rows"][0]),
                    "action": action,
                    "identifier": key,
                    "nom_batiment": payload.get("nom_batiment"),
                    "adresse_reconstituee": payload.get("adresse_reconstituee"),
                    "nom_commune": payload.get("nom_commune") or target_city_name,
                    "dgfip_reference_norm": payload.get("dgfip_reference_norm"),
                    "source_external_id": payload.get("source_external_id"),
                    "warnings": list(entry["warnings"]),
                }
            )

    local_preview: list[dict[str, Any]] = []
    for entry in local_entries[:_PREVIEW_LIMIT]:
        payload = entry["payload"]
        if len(local_preview) < _PREVIEW_LIMIT:
            local_preview.append(
                {
                    "source_row_number": int(entry["source_row_number"]),
                    "action": "attach",
                    "parent_identifier": entry["parent_key"],
                    "nom_local": payload.get("nom_local"),
                    "type_local": payload.get("type_local"),
                    "niveau": payload.get("niveau"),
                    "usage": payload.get("usage"),
                    "statut_occupation": payload.get("statut_occupation"),
                    "source_external_id": payload.get("source_external_id"),
                    "warnings": list(entry["warnings"]),
                }
            )

    return {
        "filename": filename,
        "selected_sheet": selected_sheet,
        "total_rows": int(len(dataframe)),
        "building_rows_detected": len(building_entries),
        "local_rows_detected": len(local_entries),
        "building_preview": building_preview,
        "local_preview": local_preview,
        "warnings": warnings[:100],
        "building_resolution": building_resolution,
        "local_entries": local_entries,
        "target_city_id": target_city_id,
        "target_city_name": target_city_name,
    }


def preview_building_import(
    db: Session,
    upload_file: UploadFile,
    config: BuildingImportConfig,
    current_user: User,
) -> dict[str, Any]:
    filename, _sheet_names, selected_sheet, dataframe = _read_dataframe_from_upload(upload_file, config.sheet_name, config.header_row_index)
    plan = _prepare_import_plan(db, dataframe, filename, selected_sheet, config, current_user)
    return {
        "filename": plan["filename"],
        "selected_sheet": plan["selected_sheet"],
        "total_rows": plan["total_rows"],
        "building_rows_detected": plan["building_rows_detected"],
        "local_rows_detected": plan["local_rows_detected"],
        "building_preview": plan["building_preview"],
        "local_preview": plan["local_preview"],
        "warnings": plan["warnings"],
    }


def execute_building_import(
    db: Session,
    upload_file: UploadFile,
    config: BuildingImportConfig,
    current_user: User,
) -> dict[str, Any]:
    filename, _sheet_names, selected_sheet, dataframe = _read_dataframe_from_upload(upload_file, config.sheet_name, config.header_row_index)
    plan = _prepare_import_plan(db, dataframe, filename, selected_sheet, config, current_user)

    created_buildings = 0
    skipped_existing_buildings = 0
    created_locals = 0
    skipped_existing_locals = 0
    linked_building_ids: dict[str, int] = {}
    local_indexes_cache: dict[int, tuple[dict[str, Local], dict[str, Local]]] = {}

    for key, resolution in plan["building_resolution"].items():
        payload = resolution["payload"]
        building = resolution["building"]
        if resolution["action"] == "use_existing" and building is not None:
            linked_building_ids[key] = int(building.id)
            skipped_existing_buildings += 1
            continue

        building_payload = BuildingCreate(
            city_id=plan["target_city_id"],
            dgfip_source_file=payload.get("dgfip_source_file"),
            dgfip_source_rows_json=json.dumps(resolution["source_rows"], ensure_ascii=False),
            dgfip_reference_norm=payload.get("dgfip_reference_norm"),
            nom_batiment=payload.get("nom_batiment"),
            nom_commune=payload.get("nom_commune") or plan["target_city_name"],
            numero_voirie=payload.get("numero_voirie"),
            indice_repetition=payload.get("indice_repetition"),
            nature_voie=payload.get("nature_voie"),
            nom_voie=payload.get("nom_voie"),
            section=payload.get("section"),
            numero_plan=payload.get("numero_plan"),
            adresse_reconstituee=payload.get("adresse_reconstituee"),
            source_external_id=payload.get("source_external_id"),
            source_payload_json=payload.get("source_payload_json"),
            source_creation="IMPORT",
            statut_geocodage="NON_FAIT",
        )
        building = create_building(db, building_payload, current_user, create_default_local=False, commit=False)
        linked_building_ids[key] = int(building.id)
        created_buildings += 1

    for entry in plan["local_entries"]:
        payload = entry["payload"]
        building_id = linked_building_ids.get(entry["parent_key"])
        if building_id is None:
            continue
        building = db.get(Building, building_id)
        if building is None:
            continue
        if building.id not in local_indexes_cache:
            local_indexes_cache[building.id] = _load_existing_local_indexes(db, building.id)
        by_external_id, by_fingerprint = local_indexes_cache[building.id]
        existing_local = None
        normalized_external_id = _normalize_text(payload.get("source_external_id") or "")
        if normalized_external_id:
            existing_local = by_external_id.get(normalized_external_id)
        if existing_local is None:
            fingerprint = _build_local_identity(None, payload.get("nom_local"), payload.get("type_local"), payload.get("niveau"))
            if fingerprint:
                existing_local = by_fingerprint.get(fingerprint)
        if existing_local is not None:
            skipped_existing_locals += 1
            continue
        local_payload = LocalCreate(
            nom_local=payload.get("nom_local") or "Local importé",
            type_local=payload.get("type_local") or "EXTERNE",
            niveau=payload.get("niveau"),
            surface_m2=payload.get("surface_m2"),
            usage=payload.get("usage"),
            statut_occupation=payload.get("statut_occupation"),
            commentaire=payload.get("commentaire"),
            source_external_id=payload.get("source_external_id"),
            source_payload_json=payload.get("source_payload_json"),
        )
        local = create_local(db, building, local_payload, commit=False)
        created_locals += 1
        if payload.get("source_external_id"):
            by_external_id[_normalize_text(payload["source_external_id"])] = local
        fingerprint = _build_local_identity(None, local.nom_local, local.type_local, local.niveau)
        if fingerprint:
            by_fingerprint[fingerprint] = local

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "filename": filename,
        "selected_sheet": selected_sheet,
        "created_buildings": created_buildings,
        "skipped_existing_buildings": skipped_existing_buildings,
        "created_locals": created_locals,
        "skipped_existing_locals": skipped_existing_locals,
        "warnings": plan["warnings"],
    }


def parse_import_config(config_json: str) -> BuildingImportConfig:
    try:
        return BuildingImportConfig.model_validate_json(config_json)
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Configuration d'import invalide : {error}") from error
