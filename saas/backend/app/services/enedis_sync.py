"""
ENEDIS daily consumption sync service.

Reproduces the core logic of enedis_to_powerbi.py within the FastAPI backend:
  - OAuth2 client_credentials authentication
  - Parallel GET per PRM (4 threads)
  - Upsert into enedis_data.csv (same format as the Fabric notebook)
  - Incremental state persisted in enedis_sync_state.json
  - LRU cache invalidation after successful sync
"""
from __future__ import annotations

import csv
import json
import logging
import threading
import time as _time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from app.core.config import settings

LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory sync state (single-process, thread-safe)
# ---------------------------------------------------------------------------

_SYNC_LOCK = threading.Lock()
_SYNC_STATE: dict[str, Any] = {
    "status": "idle",          # idle | running | success | error
    "started_at": None,
    "finished_at": None,
    "prms_total": 0,
    "prms_done": 0,
    "rows_added": 0,
    "date_from": None,
    "date_to": None,
    "last_sync_date": None,
    "error": None,
    "log": [],                 # last N log lines
}

_MAX_LOG_LINES = 50
_RETRY_429 = [20, 40, 60]
_WORKERS = 4
_CHUNK_DAYS = 365  # one call per PRM covers up to 36 months — chunk by year for progress visibility


def _log(msg: str) -> None:
    LOG.info(msg)
    with _SYNC_LOCK:
        _SYNC_STATE["log"].append(f"{datetime.utcnow().strftime('%H:%M:%S')} {msg}")
        if len(_SYNC_STATE["log"]) > _MAX_LOG_LINES:
            _SYNC_STATE["log"] = _SYNC_STATE["log"][-_MAX_LOG_LINES:]


# ---------------------------------------------------------------------------
# Persistent state (survives restarts)
# ---------------------------------------------------------------------------

def _state_path() -> Path:
    return Path(settings.energie_dir) / "enedis_sync_state.json"


def _load_persistent_state() -> dict[str, Any]:
    p = _state_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_persistent_state(last_sync_date: str) -> None:
    p = _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    state = _load_persistent_state()
    state["last_sync_date"] = last_sync_date
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Public status accessor
# ---------------------------------------------------------------------------

def get_sync_status() -> dict[str, Any]:
    persistent = _load_persistent_state()
    with _SYNC_LOCK:
        snap = dict(_SYNC_STATE)
    # Merge persistent last_sync_date if richer
    if not snap["last_sync_date"] and persistent.get("last_sync_date"):
        snap["last_sync_date"] = persistent["last_sync_date"]
    return snap


def is_sync_running() -> bool:
    with _SYNC_LOCK:
        return _SYNC_STATE["status"] == "running"


# ---------------------------------------------------------------------------
# ENEDIS authentication
# ---------------------------------------------------------------------------

def _get_token() -> str:
    if not settings.enedis_client_id or not settings.enedis_client_secret:
        raise RuntimeError(
            "ENEDIS_CLIENT_ID et ENEDIS_CLIENT_SECRET doivent être définis dans .env"
        )
    resp = requests.post(
        settings.enedis_auth_url,
        data={
            "grant_type": "client_credentials",
            "client_id": settings.enedis_client_id,
            "client_secret": settings.enedis_client_secret,
        },
        timeout=60,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError(f"Pas de access_token dans la réponse ENEDIS : {resp.text[:300]}")
    _log("Token ENEDIS obtenu.")
    return token


# ---------------------------------------------------------------------------
# PRM list — from existing enedis_contracts.csv
# ---------------------------------------------------------------------------

def _load_prms() -> list[str]:
    csv_path = Path(settings.energie_dir) / "enedis_contracts.csv"
    if not csv_path.exists():
        raise RuntimeError(f"enedis_contracts.csv introuvable dans {settings.energie_dir}")
    prms: list[str] = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            uid = row.get("usage_point_id", "").strip()
            if uid and uid.isdigit() and len(uid) == 14:
                prms.append(uid)
    if not prms:
        raise RuntimeError("Aucun PRM valide trouvé dans enedis_contracts.csv")
    return sorted(set(prms))


# ---------------------------------------------------------------------------
# CSV upsert
# ---------------------------------------------------------------------------

def _upsert_csv(rows: list[dict[str, Any]], csv_path: Path) -> int:
    """Merge new rows into existing CSV. Returns count of genuinely new rows."""
    if not rows:
        return 0

    key_cols = ("usage_point_id", "date")
    existing: dict[tuple, dict] = {}
    existing_cols: list[str] = []

    if csv_path.exists() and csv_path.stat().st_size > 0:
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            existing_cols = list(reader.fieldnames or [])
            for r in reader:
                key = tuple(r.get(k, "") for k in key_cols)
                existing[key] = dict(r)

    new_count = 0
    for row in rows:
        key = tuple(str(row.get(k, "")) for k in key_cols)
        if key not in existing:
            new_count += 1
        existing[key] = {k: str(v) if v is not None else "" for k, v in row.items()}

    all_cols = list(dict.fromkeys(existing_cols + [k for r in rows for k in r]))
    sorted_rows = sorted(
        existing.values(),
        key=lambda r: (r.get("usage_point_id", ""), r.get("date", "")),
    )
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_cols, extrasaction="ignore")
        writer.writeheader()
        for r in sorted_rows:
            writer.writerow({k: r.get(k, "") for k in all_cols})

    return new_count


# ---------------------------------------------------------------------------
# Daily consumption fetch (one PRM at a time, parallel)
# ---------------------------------------------------------------------------

def _fetch_one_prm(
    token: str,
    prm: str,
    start_date: str,
    end_date: str,
    ingested_at: str,
) -> tuple[list[dict], int, int]:
    """Returns (rows, ok_count, err_count)."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    resp = None
    for attempt in range(4):
        try:
            resp = requests.get(
                settings.enedis_sync_url,
                headers=headers,
                params={"usage_point_id": prm, "start": start_date, "end": end_date},
                timeout=45,
            )
            if resp.status_code == 429 and attempt < len(_RETRY_429):
                _log(f"PRM {prm} → 429 quota, attente {_RETRY_429[attempt]}s…")
                _time.sleep(_RETRY_429[attempt])
                continue
            if resp.status_code >= 500:
                _time.sleep(5 * (attempt + 1))
                continue
            break
        except Exception as exc:
            if attempt == 3:
                LOG.warning("PRM %s réseau : %s", prm, exc)
                return [], 0, 1
            _time.sleep(5)

    if resp is None:
        return [], 0, 1

    if resp.status_code == 200:
        mr = resp.json().get("meter_reading", {})
        unit = mr.get("reading_type", {}).get("unit", "Wh")
        quality = mr.get("quality", "")
        flow_dir = mr.get("reading_type", {}).get("flow_direction", "")
        rows = []
        for ir in mr.get("interval_reading", []):
            raw_date = ir.get("date", "")
            val = ir.get("value")
            try:
                rows.append({
                    "usage_point_id": prm,
                    "date": raw_date[:10],
                    "value_wh": float(val) if val not in (None, "") else None,
                    "unit": unit,
                    "quality": quality,
                    "flow_direction": flow_dir,
                    "_ingested_at_utc": ingested_at,
                })
            except (ValueError, TypeError):
                continue
        return rows, 1, 0

    if resp.status_code in (403, 404):
        # PRM non titulaire ou hors historique — normal, on ignore silencieusement
        return [], 1, 0

    LOG.warning("PRM %s → HTTP %d : %s", prm, resp.status_code, resp.text[:200])
    return [], 0, 1


# ---------------------------------------------------------------------------
# Main sync orchestration
# ---------------------------------------------------------------------------

def run_daily_consumption_sync(history_days: int | None = None) -> None:
    """
    Background task: fetches daily consumption for all PRMs and upserts enedis_data.csv.
    Designed to run in a FastAPI BackgroundTasks context.
    """
    # Guard: only one sync at a time
    with _SYNC_LOCK:
        if _SYNC_STATE["status"] == "running":
            return
        _SYNC_STATE.update({
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
            "finished_at": None,
            "error": None,
            "log": [],
            "prms_total": 0,
            "prms_done": 0,
            "rows_added": 0,
        })

    try:
        _log("Démarrage de la synchronisation ENEDIS — consommation journalière")

        # 1. Charger les PRMs
        prms = _load_prms()
        with _SYNC_LOCK:
            _SYNC_STATE["prms_total"] = len(prms)
        _log(f"{len(prms)} PRMs chargés depuis enedis_contracts.csv")

        # 2. Déterminer la fenêtre temporelle
        persistent = _load_persistent_state()
        last_sync = persistent.get("last_sync_date")
        effective_history = history_days or settings.enedis_history_days
        today = date.today()

        if last_sync and history_days is None:
            # Sync incrémentale : reprend au lendemain de la dernière sync
            start_d = date.fromisoformat(last_sync) + timedelta(days=1)
        else:
            # Backfill explicite : ignore last_sync, force le recalcul complet
            start_d = today - timedelta(days=effective_history)

        end_d = today - timedelta(days=1)  # ENEDIS J-1

        if start_d > end_d:
            _log("Données déjà à jour — aucune collecte nécessaire.")
            with _SYNC_LOCK:
                _SYNC_STATE.update({
                    "status": "success",
                    "finished_at": datetime.utcnow().isoformat(),
                    "last_sync_date": last_sync,
                })
            return

        start_str = start_d.isoformat()
        end_str = end_d.isoformat()
        with _SYNC_LOCK:
            _SYNC_STATE.update({"date_from": start_str, "date_to": end_str})
        _log(f"Fenêtre : {start_str} → {end_str} ({(end_d - start_d).days + 1} jours)")

        # 3. Authentification ENEDIS
        token = _get_token()
        ingested_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

        # 4. Collecter en parallèle par chunks d'un an (pour afficher la progression)
        csv_path = Path(settings.energie_dir) / "enedis_data.csv"
        total_new = 0
        chunk_start = start_d

        while chunk_start <= end_d:
            chunk_end = min(chunk_start + timedelta(days=_CHUNK_DAYS - 1), end_d)
            chunk_start_str = chunk_start.isoformat()
            chunk_end_str = chunk_end.isoformat()
            _log(f"Chunk {chunk_start_str} → {chunk_end_str} ({len(prms)} PRMs, {_WORKERS} threads)")

            all_rows: list[dict] = []
            done_count = 0

            with ThreadPoolExecutor(max_workers=_WORKERS) as executor:
                futures = {
                    executor.submit(
                        _fetch_one_prm, token, prm, chunk_start_str, chunk_end_str, ingested_at
                    ): prm
                    for prm in prms
                }
                for future in as_completed(futures):
                    rows, _ok, _err = future.result()
                    all_rows.extend(rows)
                    done_count += 1
                    with _SYNC_LOCK:
                        _SYNC_STATE["prms_done"] = done_count
                    if done_count % 50 == 0 or done_count == len(prms):
                        _log(f"  {done_count}/{len(prms)} PRMs traités — {len(all_rows)} lignes collectées")

            new_rows = _upsert_csv(all_rows, csv_path)
            total_new += new_rows
            _log(f"  Chunk upsert OK — {new_rows} nouvelles lignes ({total_new} total)")
            chunk_start = chunk_end + timedelta(days=1)

            # Re-auth if token might expire (chunks > 1 hour apart are unlikely but safe)
            if chunk_start <= end_d:
                try:
                    token = _get_token()
                except Exception:
                    pass  # Keep existing token

        # 5. Persister l'état + invalider les caches
        _save_persistent_state(end_str)
        _invalidate_energie_caches()

        _log(f"Synchronisation terminée — {total_new} nouvelles lignes, date max : {end_str}")
        with _SYNC_LOCK:
            _SYNC_STATE.update({
                "status": "success",
                "finished_at": datetime.utcnow().isoformat(),
                "rows_added": total_new,
                "last_sync_date": end_str,
            })

    except Exception as exc:
        msg = str(exc)
        _log(f"ERREUR : {msg}")
        LOG.exception("ENEDIS sync error")
        with _SYNC_LOCK:
            _SYNC_STATE.update({
                "status": "error",
                "finished_at": datetime.utcnow().isoformat(),
                "error": msg,
            })


def _invalidate_energie_caches() -> None:
    """Clear LRU caches in energie service so fresh data is served immediately."""
    try:
        from app.services.energie import (  # noqa: PLC0415
            _daily_consumption_index,
            _consumption_by_month,
            _max_power_index,
            get_data_ranges,
        )
        _daily_consumption_index.cache_clear()
        _consumption_by_month.cache_clear()
        _max_power_index.cache_clear()
        get_data_ranges.cache_clear()
        _log("Caches LRU invalidés — nouvelles données disponibles immédiatement.")
    except Exception as exc:
        LOG.warning("Cache invalidation failed: %s", exc)


# ---------------------------------------------------------------------------
# Puissance max journalière (daily_consumption_max_power)
# ---------------------------------------------------------------------------

_MP_LOCK = threading.Lock()
_MP_STATE: dict[str, Any] = {
    "status": "idle",
    "started_at": None,
    "finished_at": None,
    "prms_total": 0,
    "prms_done": 0,
    "rows_added": 0,
    "date_from": None,
    "date_to": None,
    "last_sync_date": None,
    "error": None,
    "log": [],
}


def _mp_log(msg: str) -> None:
    LOG.info(msg)
    with _MP_LOCK:
        _MP_STATE["log"].append(f"{datetime.utcnow().strftime('%H:%M:%S')} {msg}")
        if len(_MP_STATE["log"]) > _MAX_LOG_LINES:
            _MP_STATE["log"] = _MP_STATE["log"][-_MAX_LOG_LINES:]


def get_max_power_status() -> dict[str, Any]:
    with _MP_LOCK:
        return dict(_MP_STATE)


def is_max_power_running() -> bool:
    with _MP_LOCK:
        return _MP_STATE["status"] == "running"


def _mp_state_path() -> Path:
    return Path(settings.energie_dir) / "enedis_mp_state.json"


def _load_mp_state() -> dict[str, Any]:
    p = _mp_state_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_mp_state(last_date: str) -> None:
    p = _mp_state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    state = _load_mp_state()
    state["last_sync_date"] = last_date
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _fetch_one_max_power(
    token: str,
    prm: str,
    start_date: str,
    end_date: str,
    ingested_at: str,
) -> tuple[list[dict], int, int]:
    """Retourne (rows, ok_count, err_count). Valeurs en VA."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    resp = None
    for attempt in range(4):
        try:
            resp = requests.get(
                settings.enedis_max_power_url,
                headers=headers,
                params={
                    "usage_point_id": prm,
                    "start": start_date,
                    "end": end_date,
                    "measuring_period": "P1D",
                    "grandeurPhysique": "PMA",
                },
                timeout=45,
            )
            if resp.status_code == 429 and attempt < len(_RETRY_429):
                _mp_log(f"PRM {prm} → 429 quota, attente {_RETRY_429[attempt]}s…")
                _time.sleep(_RETRY_429[attempt])
                continue
            if resp.status_code >= 500:
                _time.sleep(5 * (attempt + 1))
                continue
            break
        except Exception as exc:
            if attempt == 3:
                LOG.warning("PRM %s [max_power] réseau : %s", prm, exc)
                return [], 0, 1
            _time.sleep(5)

    if resp is None:
        return [], 0, 1

    if resp.status_code == 200:
        mr = resp.json().get("meter_reading", {})
        unit = mr.get("reading_type", {}).get("unit", "VA")
        quality = mr.get("quality", "")
        flow_dir = mr.get("reading_type", {}).get("flow_direction", "")
        rows = []
        for ir in mr.get("interval_reading", []):
            raw_date = ir.get("date", "")
            val = ir.get("value")
            try:
                rows.append({
                    "usage_point_id": prm,
                    "date": raw_date[:10],
                    "value_va": float(val) if val not in (None, "") else None,
                    "unit": unit,
                    "quality": quality,
                    "flow_direction": flow_dir,
                    "_ingested_at_utc": ingested_at,
                })
            except (ValueError, TypeError):
                continue
        return rows, 1, 0

    if resp.status_code in (403, 404):
        return [], 1, 0

    LOG.warning("PRM %s [max_power] → HTTP %d : %s", prm, resp.status_code, resp.text[:200])
    return [], 0, 1


def run_max_power_sync(history_days: int | None = None) -> None:
    """Background task : récupère la puissance max journalière pour tous les PRMs."""
    with _MP_LOCK:
        if _MP_STATE["status"] == "running":
            return
        _MP_STATE.update({
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
            "finished_at": None,
            "error": None,
            "log": [],
            "prms_total": 0,
            "prms_done": 0,
            "rows_added": 0,
        })

    try:
        _mp_log("Démarrage sync puissance max ENEDIS")

        prms = _load_prms()
        with _MP_LOCK:
            _MP_STATE["prms_total"] = len(prms)
        _mp_log(f"{len(prms)} PRMs chargés")

        persistent = _load_mp_state()
        last_sync = persistent.get("last_sync_date")
        effective_history = history_days or settings.enedis_history_days
        today = date.today()

        if last_sync and history_days is None:
            start_d = date.fromisoformat(last_sync) + timedelta(days=1)
        else:
            start_d = today - timedelta(days=effective_history)

        end_d = today - timedelta(days=1)

        if start_d > end_d:
            _mp_log("Puissance max déjà à jour — aucune collecte nécessaire.")
            with _MP_LOCK:
                _MP_STATE.update({"status": "success", "finished_at": datetime.utcnow().isoformat(), "last_sync_date": last_sync})
            return

        start_str, end_str = start_d.isoformat(), end_d.isoformat()
        with _MP_LOCK:
            _MP_STATE.update({"date_from": start_str, "date_to": end_str})
        _mp_log(f"Fenêtre : {start_str} → {end_str}")

        token = _get_token()
        ingested_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        csv_path = Path(settings.energie_dir) / "enedis_max_power.csv"
        total_new = 0
        chunk_start = start_d

        while chunk_start <= end_d:
            chunk_end = min(chunk_start + timedelta(days=_CHUNK_DAYS - 1), end_d)
            cs, ce = chunk_start.isoformat(), chunk_end.isoformat()
            _mp_log(f"Chunk {cs} → {ce} ({len(prms)} PRMs)")

            all_rows: list[dict] = []
            done_count = 0

            with ThreadPoolExecutor(max_workers=_WORKERS) as executor:
                futures = {
                    executor.submit(_fetch_one_max_power, token, prm, cs, ce, ingested_at): prm
                    for prm in prms
                }
                for future in as_completed(futures):
                    rows, _ok, _err = future.result()
                    all_rows.extend(rows)
                    done_count += 1
                    with _MP_LOCK:
                        _MP_STATE["prms_done"] = done_count
                    if done_count % 50 == 0 or done_count == len(prms):
                        _mp_log(f"  {done_count}/{len(prms)} PRMs — {len(all_rows)} lignes")

            new_rows = _upsert_csv(all_rows, csv_path)
            total_new += new_rows
            _mp_log(f"  Chunk OK — {new_rows} nouvelles lignes ({total_new} total)")
            chunk_start = chunk_end + timedelta(days=1)

            if chunk_start <= end_d:
                try:
                    token = _get_token()
                except Exception:
                    pass

        _save_mp_state(end_str)

        try:
            from app.services.energie import _max_power_index, get_data_ranges  # noqa: PLC0415
            _max_power_index.cache_clear()
            get_data_ranges.cache_clear()
            _mp_log("Cache puissance max invalidé.")
        except Exception:
            pass

        _mp_log(f"Terminé — {total_new} nouvelles lignes, date max : {end_str}")
        with _MP_LOCK:
            _MP_STATE.update({
                "status": "success",
                "finished_at": datetime.utcnow().isoformat(),
                "rows_added": total_new,
                "last_sync_date": end_str,
            })

    except Exception as exc:
        msg = str(exc)
        _mp_log(f"ERREUR : {msg}")
        LOG.exception("Max power sync error")
        with _MP_LOCK:
            _MP_STATE.update({"status": "error", "finished_at": datetime.utcnow().isoformat(), "error": msg})


# ---------------------------------------------------------------------------
# Courbe de charge 30 min (consumption_load_curve) — depuis 2026-01-01
# Limite ENEDIS : 7 jours max par appel → chunks de 7 jours, append CSV
# ---------------------------------------------------------------------------

_LC_LOCK = threading.Lock()
_LC_STATE: dict[str, Any] = {
    "status": "idle",
    "started_at": None,
    "finished_at": None,
    "chunks_total": 0,
    "chunks_done": 0,
    "rows_added": 0,
    "date_from": None,
    "date_to": None,
    "last_sync_date": None,
    "error": None,
    "log": [],
}
_LC_CHUNK_DAYS = 7   # limite API ENEDIS
_LC_FIELDNAMES = ["usage_point_id", "datetime", "value_w", "unit", "quality", "_ingested_at_utc"]


def _lc_log(msg: str) -> None:
    LOG.info(msg)
    with _LC_LOCK:
        _LC_STATE["log"].append(f"{datetime.utcnow().strftime('%H:%M:%S')} {msg}")
        if len(_LC_STATE["log"]) > _MAX_LOG_LINES:
            _LC_STATE["log"] = _LC_STATE["log"][-_MAX_LOG_LINES:]


def get_load_curve_status() -> dict[str, Any]:
    persistent = _load_lc_state()
    with _LC_LOCK:
        snap = dict(_LC_STATE)
    if not snap["last_sync_date"] and persistent.get("last_sync_date"):
        snap["last_sync_date"] = persistent["last_sync_date"]
    return snap


def is_load_curve_running() -> bool:
    with _LC_LOCK:
        return _LC_STATE["status"] == "running"


def _lc_state_path() -> Path:
    return Path(settings.energie_dir) / "enedis_lc_state.json"


def _load_lc_state() -> dict[str, Any]:
    p = _lc_state_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_lc_state(last_date: str) -> None:
    p = _lc_state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    state = _load_lc_state()
    state["last_sync_date"] = last_date
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _append_lc_csv(rows: list[dict], csv_path: Path) -> int:
    """Ajoute des lignes à la fin du CSV courbe de charge (sans relire l'existant)."""
    if not rows:
        return 0
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with open(csv_path, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_LC_FIELDNAMES, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        for row in rows:
            writer.writerow({k: "" if row.get(k) is None else str(row[k]) for k in _LC_FIELDNAMES})
    return len(rows)


def _fetch_lc_prm(
    token: str,
    prm: str,
    start_date: str,
    end_date: str,
    ingested_at: str,
) -> tuple[list[dict], int, int]:
    """Fetch courbe de charge pour un PRM sur une fenêtre ≤ 7 jours."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    resp = None
    for attempt in range(4):
        try:
            resp = requests.get(
                settings.enedis_load_curve_url,
                headers=headers,
                params={"usage_point_id": prm, "start": start_date, "end": end_date},
                timeout=45,
            )
            if resp.status_code == 429 and attempt < len(_RETRY_429):
                _lc_log(f"PRM {prm} → 429, attente {_RETRY_429[attempt]}s…")
                _time.sleep(_RETRY_429[attempt])
                continue
            if resp.status_code >= 500:
                _time.sleep(5 * (attempt + 1))
                continue
            break
        except Exception as exc:
            if attempt == 3:
                LOG.warning("PRM %s [load_curve] réseau : %s", prm, exc)
                return [], 0, 1
            _time.sleep(5)

    if resp is None:
        return [], 0, 1

    if resp.status_code == 200:
        mr = resp.json().get("meter_reading", {})
        unit = mr.get("reading_type", {}).get("unit", "W")
        quality = mr.get("quality", "")
        rows = []
        for ir in mr.get("interval_reading", []):
            raw_dt = ir.get("date", "")
            val = ir.get("value")
            try:
                rows.append({
                    "usage_point_id": prm,
                    "datetime": raw_dt,
                    "value_w": float(val) if val not in (None, "") else None,
                    "unit": unit,
                    "quality": quality,
                    "_ingested_at_utc": ingested_at,
                })
            except (ValueError, TypeError):
                continue
        return rows, 1, 0

    if resp.status_code in (403, 404):
        return [], 1, 0

    LOG.warning("PRM %s [load_curve] → HTTP %d : %s", prm, resp.status_code, resp.text[:200])
    return [], 0, 1


def run_load_curve_sync() -> None:
    """
    Background task : récupère la courbe de charge 30 min pour tous les PRMs
    depuis settings.enedis_load_curve_start (défaut 2026-01-01), en chunks de 7 jours.
    """
    with _LC_LOCK:
        if _LC_STATE["status"] == "running":
            return
        _LC_STATE.update({
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
            "finished_at": None,
            "error": None,
            "log": [],
            "chunks_total": 0,
            "chunks_done": 0,
            "rows_added": 0,
        })

    try:
        _lc_log("Démarrage sync courbe de charge 30 min")

        prms = _load_prms()
        _lc_log(f"{len(prms)} PRMs chargés")

        persistent = _load_lc_state()
        last_sync = persistent.get("last_sync_date")
        today = date.today()
        end_d = today - timedelta(days=1)

        if last_sync:
            start_d = date.fromisoformat(last_sync) + timedelta(days=1)
            _lc_log(f"Reprise depuis {start_d} (données jusqu'au {last_sync})")
        else:
            start_d = date.fromisoformat(settings.enedis_load_curve_start)
            _lc_log(f"Premier backfill depuis {start_d}")

        if start_d > end_d:
            _lc_log("Courbe de charge déjà à jour.")
            with _LC_LOCK:
                _LC_STATE.update({"status": "success", "finished_at": datetime.utcnow().isoformat(), "last_sync_date": last_sync})
            return

        # Calculer le nombre de chunks
        total_days = (end_d - start_d).days + 1
        chunks_total = (total_days + _LC_CHUNK_DAYS - 1) // _LC_CHUNK_DAYS
        with _LC_LOCK:
            _LC_STATE.update({"chunks_total": chunks_total, "date_from": start_d.isoformat(), "date_to": end_d.isoformat()})
        _lc_log(f"Fenêtre : {start_d} → {end_d} ({total_days} jours, {chunks_total} chunks de 7j)")

        csv_path = Path(settings.energie_dir) / "enedis_load_curve.csv"
        token = _get_token()
        ingested_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        total_rows = 0
        chunk_start = start_d
        chunk_idx = 0

        while chunk_start <= end_d:
            chunk_end = min(chunk_start + timedelta(days=_LC_CHUNK_DAYS - 1), end_d)
            cs, ce = chunk_start.isoformat(), chunk_end.isoformat()
            chunk_idx += 1
            _lc_log(f"Chunk {chunk_idx}/{chunks_total} : {cs} → {ce} ({len(prms)} PRMs)")

            all_rows: list[dict] = []
            done_count = 0

            with ThreadPoolExecutor(max_workers=_WORKERS) as executor:
                futures = {
                    executor.submit(_fetch_lc_prm, token, prm, cs, ce, ingested_at): prm
                    for prm in prms
                }
                for future in as_completed(futures):
                    rows, _ok, _err = future.result()
                    all_rows.extend(rows)
                    done_count += 1
                    if done_count % 100 == 0 or done_count == len(prms):
                        _lc_log(f"  {done_count}/{len(prms)} PRMs — {len(all_rows)} pts collectés")

            appended = _append_lc_csv(all_rows, csv_path)
            total_rows += appended
            _save_lc_state(ce)
            with _LC_LOCK:
                _LC_STATE.update({"chunks_done": chunk_idx, "rows_added": total_rows, "last_sync_date": ce})
            _lc_log(f"  Chunk OK — {appended} pts écrits ({total_rows} total)")

            chunk_start = chunk_end + timedelta(days=1)

            # Re-auth toutes les 3 chunks (~21 jours)
            if chunk_idx % 3 == 0 and chunk_start <= end_d:
                try:
                    token = _get_token()
                except Exception:
                    pass

        try:
            from app.services.energie import _load_curve_index, get_data_ranges  # noqa: PLC0415
            _load_curve_index.cache_clear()
            get_data_ranges.cache_clear()
            _lc_log("Cache courbe de charge invalidé.")
        except Exception:
            pass

        _lc_log(f"Terminé — {total_rows} points écrits, date max : {end_d.isoformat()}")
        with _LC_LOCK:
            _LC_STATE.update({
                "status": "success",
                "finished_at": datetime.utcnow().isoformat(),
                "rows_added": total_rows,
                "last_sync_date": end_d.isoformat(),
            })

    except Exception as exc:
        msg = str(exc)
        _lc_log(f"ERREUR : {msg}")
        LOG.exception("Load curve sync error")
        with _LC_LOCK:
            _LC_STATE.update({"status": "error", "finished_at": datetime.utcnow().isoformat(), "error": msg})
