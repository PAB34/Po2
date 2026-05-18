from __future__ import annotations

import csv
import hashlib
import json
import logging
import threading
import time as _time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from app.core.config import settings
from app.services.enedis_common import RateLimiter, TokenManager

LOG = logging.getLogger(__name__)

_CUSTOMER_SOURCES: tuple[tuple[str, str, str], ...] = (
    ("enedis_contracts", "/contract/v1", "enedis_contracts.csv"),
    ("enedis_addresses", "/address/v1", "enedis_addresses.csv"),
    ("enedis_connections", "/connection/v1", "enedis_connections.csv"),
    ("enedis_contract_summary", "/contract_summary/v1", "enedis_contract_summary.csv"),
    ("enedis_alimentation", "/alimentation_auto/v1", "enedis_alimentation.csv"),
    ("enedis_situation_contrat", "/situation_contrat_auto/v1", "enedis_situation_contrat.csv"),
)

_CUSTOMER_RATE_LIMITER = RateLimiter(rps=2.0, max_concurrent=1, max_hourly=5000)
_STATE_LOCK = threading.Lock()
_STATE: dict[str, Any] = {
    "status": "idle",
    "started_at": None,
    "finished_at": None,
    "last_sync_at": None,
    "sources_total": len(_CUSTOMER_SOURCES),
    "sources_done": 0,
    "current_source": None,
    "prms_total": 0,
    "prms_done": 0,
    "rows_upserted": 0,
    "changes_detected": 0,
    "error": None,
    "log": [],
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso_now() -> str:
    return _utc_now().isoformat().replace("+00:00", "Z")


def _log(message: str) -> None:
    LOG.info(message)
    with _STATE_LOCK:
        log = list(_STATE.get("log") or [])
        log.append(message)
        _STATE["log"] = log[-80:]


def _set_state(**updates: Any) -> None:
    with _STATE_LOCK:
        _STATE.update(updates)


def get_customer_sync_status() -> dict[str, Any]:
    with _STATE_LOCK:
        return dict(_STATE)


def is_customer_sync_running() -> bool:
    return get_customer_sync_status().get("status") == "running"


def _flatten_into(obj: Any, result: dict[str, Any], prefix: str = "") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_key = f"{prefix}_{key}" if prefix else str(key)
            _flatten_into(value, result, new_key)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            new_key = f"{prefix}_{index}" if prefix else str(index)
            _flatten_into(value, result, new_key)
    else:
        result[prefix] = obj


def _load_prms_from_contracts() -> list[str]:
    csv_path = Path(settings.energie_dir) / "enedis_contracts.csv"
    if not csv_path.exists():
        return []
    prms: list[str] = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            uid = (row.get("usage_point_id") or "").strip()
            if uid.isdigit() and len(uid) == 14:
                prms.append(uid)
    return sorted(set(prms))


def _discover_prms_from_api(token_mgr: TokenManager) -> list[str]:
    headers = {
        "Authorization": f"Bearer {token_mgr.get()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    all_prms: list[str] = []
    page = 1
    while True:
        _CUSTOMER_RATE_LIMITER.acquire()
        try:
            resp = requests.post(
                settings.enedis_perimeter_url,
                headers=headers,
                json={"page_number": page},
                timeout=30,
            )
        finally:
            _CUSTOMER_RATE_LIMITER.release()
        if resp.status_code != 200:
            _log(f"Périmètre PRM indisponible page {page}: HTTP {resp.status_code}")
            return []
        body = resp.json()
        prms_page = body.get("usage_point_id") or []
        all_prms.extend(str(prm) for prm in prms_page)
        params = body.get("query_parameters") or {}
        total_pages = int(params.get("page_total_count") or 1)
        _log(f"Périmètre PRM page {page}/{total_pages}: {len(prms_page)} PRM")
        if page >= total_pages:
            break
        page += 1
    return sorted({prm for prm in all_prms if prm.isdigit() and len(prm) == 14})


def _load_prms(token_mgr: TokenManager) -> list[str]:
    prms = _discover_prms_from_api(token_mgr)
    if prms:
        return prms
    prms = _load_prms_from_contracts()
    if not prms:
        raise RuntimeError("Aucun PRM disponible pour la synchronisation contractuelle ENEDIS.")
    _log(f"Fallback sur enedis_contracts.csv: {len(prms)} PRM")
    return prms


def _row_hash(row: dict[str, Any]) -> str:
    comparable = {
        key: "" if value is None else str(value)
        for key, value in row.items()
        if key != "_ingested_at_utc"
    }
    payload = json.dumps(comparable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_current_rows(csv_path: Path) -> tuple[dict[str, dict[str, str]], list[str]]:
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return {}, []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = {
            (row.get("usage_point_id") or "").strip(): dict(row)
            for row in reader
            if (row.get("usage_point_id") or "").strip()
        }
        return rows, list(reader.fieldnames or [])


def _write_current_rows(csv_path: Path, rows: dict[str, dict[str, Any]], previous_cols: list[str]) -> None:
    all_cols = list(dict.fromkeys(previous_cols + [key for row in rows.values() for key in row.keys()]))
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_cols, extrasaction="ignore")
        writer.writeheader()
        for prm in sorted(rows):
            writer.writerow({key: rows[prm].get(key, "") for key in all_cols})


def _append_history(changes: list[dict[str, Any]]) -> None:
    if not changes:
        return
    history_path = Path(settings.energie_dir) / "history" / "enedis_customer_changes.csv"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "detected_at_utc",
        "source",
        "usage_point_id",
        "change_type",
        "previous_hash",
        "current_hash",
        "previous_json",
        "current_json",
    ]
    write_header = not history_path.exists() or history_path.stat().st_size == 0
    with open(history_path, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        for change in changes:
            writer.writerow(change)


def _upsert_with_history(source: str, csv_name: str, rows: list[dict[str, Any]], detected_at: str) -> tuple[int, int]:
    csv_path = Path(settings.energie_dir) / csv_name
    existing, previous_cols = _read_current_rows(csv_path)
    if not rows and not existing:
        return 0, 0
    merged: dict[str, dict[str, Any]] = {key: dict(value) for key, value in existing.items()}
    changes: list[dict[str, Any]] = []
    rows_upserted = 0

    for row in rows:
        prm = str(row.get("usage_point_id") or "").strip()
        if not prm:
            continue
        previous = existing.get(prm)
        previous_hash = _row_hash(previous) if previous else ""
        current_hash = _row_hash(row)
        if not previous:
            change_type = "created"
        elif previous_hash != current_hash:
            change_type = "updated"
        else:
            change_type = ""
        merged[prm] = {key: "" if value is None else str(value) for key, value in row.items()}
        rows_upserted += 1
        if change_type:
            changes.append(
                {
                    "detected_at_utc": detected_at,
                    "source": source,
                    "usage_point_id": prm,
                    "change_type": change_type,
                    "previous_hash": previous_hash,
                    "current_hash": current_hash,
                    "previous_json": json.dumps(previous or {}, ensure_ascii=False, sort_keys=True),
                    "current_json": json.dumps(row, ensure_ascii=False, sort_keys=True, default=str),
                }
            )

    _write_current_rows(csv_path, merged, previous_cols)
    _append_history(changes)
    return rows_upserted, len(changes)


def _fetch_source_rows(
    token_mgr: TokenManager,
    source: str,
    context: str,
    prms: list[str],
    detected_at: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    retry_waits = (5, 15, 45)
    for index, prm in enumerate(prms, start=1):
        _set_state(prms_done=index, current_source=source)
        resp = None
        for attempt in range(len(retry_waits) + 1):
            _CUSTOMER_RATE_LIMITER.acquire()
            try:
                resp = requests.get(
                    f"{settings.enedis_base_url}{context}/{prm}",
                    headers={"Authorization": f"Bearer {token_mgr.get()}", "Accept": "application/json"},
                    timeout=30,
                )
            except requests.RequestException as exc:
                resp = None
                if attempt == len(retry_waits):
                    _log(f"{source} {prm}: erreur réseau {type(exc).__name__}")
                    break
            finally:
                _CUSTOMER_RATE_LIMITER.release()

            if resp is not None and resp.status_code == 200:
                row: dict[str, Any] = {"usage_point_id": prm, "_ingested_at_utc": detected_at}
                _flatten_into(resp.json(), row)
                rows.append(row)
                break
            if resp is not None and resp.status_code not in (429, 500, 502, 503, 504):
                _log(f"{source} {prm}: HTTP {resp.status_code}")
                break
            if attempt < len(retry_waits):
                _time.sleep(retry_waits[attempt])
        if index == 1 or index % 50 == 0 or index == len(prms):
            _log(f"{source}: {index}/{len(prms)} PRM, {len(rows)} ligne(s)")
    return rows


def _invalidate_energy_caches() -> None:
    try:
        from app.services.energie import (  # noqa: PLC0415
            _addresses,
            _connections,
            _contracts,
            _summaries,
            get_data_audit,
            get_data_ranges,
            get_energie_overview,
        )

        _contracts.cache_clear()
        _addresses.cache_clear()
        _connections.cache_clear()
        _summaries.cache_clear()
        get_energie_overview.cache_clear()
        get_data_audit.cache_clear()
        get_data_ranges.cache_clear()
    except Exception:
        LOG.exception("Cache invalidation failed after customer sync")


def run_customer_sync() -> None:
    if is_customer_sync_running():
        return
    started_at = _iso_now()
    _set_state(
        status="running",
        started_at=started_at,
        finished_at=None,
        error=None,
        sources_total=len(_CUSTOMER_SOURCES),
        sources_done=0,
        current_source=None,
        prms_total=0,
        prms_done=0,
        rows_upserted=0,
        changes_detected=0,
        log=[],
    )
    try:
        token_mgr = TokenManager()
        prms = _load_prms(token_mgr)
        _set_state(prms_total=len(prms))
        _log(f"Synchronisation contractuelle ENEDIS: {len(prms)} PRM, {len(_CUSTOMER_SOURCES)} sources")
        total_rows = 0
        total_changes = 0
        for source_index, (source, context, csv_name) in enumerate(_CUSTOMER_SOURCES, start=1):
            _set_state(current_source=source, prms_done=0)
            detected_at = _iso_now()
            rows = _fetch_source_rows(token_mgr, source, context, prms, detected_at)
            rows_upserted, changes = _upsert_with_history(source, csv_name, rows, detected_at)
            total_rows += rows_upserted
            total_changes += changes
            _set_state(
                sources_done=source_index,
                rows_upserted=total_rows,
                changes_detected=total_changes,
            )
            _log(f"{source}: {rows_upserted} ligne(s) courantes, {changes} changement(s)")
        _invalidate_energy_caches()
        finished_at = _iso_now()
        _set_state(
            status="success",
            finished_at=finished_at,
            last_sync_at=finished_at,
            current_source=None,
        )
        _log(f"Synchronisation contractuelle terminée: {total_changes} changement(s)")
    except Exception as exc:
        LOG.exception("ENEDIS customer sync failed")
        _set_state(status="error", finished_at=_iso_now(), error=str(exc), current_source=None)
        _log(f"Erreur sync contractuelle: {exc}")
