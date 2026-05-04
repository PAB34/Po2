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


_OUTCOME_RANK: dict[str, int] = {
    "ok_data": 0, "ok_empty": 1, "not_found": 2, "forbidden": 3, "error": 4,
}


def _best_outcome(a: str, b: str) -> str:
    return a if _OUTCOME_RANK.get(a, 4) <= _OUTCOME_RANK.get(b, 4) else b


def _fetch_one_max_power(
    token: str,
    prm: str,
    start_date: str,
    end_date: str,
    ingested_at: str,
) -> tuple[list[dict], str]:
    """Retourne (rows, outcome). outcome: ok_data | ok_empty | forbidden | not_found | error."""
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
                return [], "error"
            _time.sleep(5)

    if resp is None:
        return [], "error"

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
        return rows, ("ok_data" if rows else "ok_empty")

    if resp.status_code == 403:
        return [], "forbidden"
    if resp.status_code == 404:
        return [], "not_found"

    LOG.warning("PRM %s [max_power] → HTTP %d : %s", prm, resp.status_code, resp.text[:200])
    return [], "error"


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
        prm_outcomes: dict[str, str] = {prm: "error" for prm in prms}

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
                    prm_id = futures[future]
                    rows, outcome = future.result()
                    all_rows.extend(rows)
                    prm_outcomes[prm_id] = _best_outcome(prm_outcomes.get(prm_id, "error"), outcome)
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
            diag_path = Path(settings.energie_dir) / "enedis_mp_diagnostic.json"
            diag_path.write_text(
                json.dumps({"generated_at": datetime.utcnow().isoformat() + "Z",
                            "date_from": start_str, "date_to": end_str,
                            "outcomes": prm_outcomes}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

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
# Courbe de charge 30 min (consumption_load_curve)
# Contraintes API ENEDIS synchrone :
#   - 1 PRM par appel, 7 jours max par appel
#   - max 5 req/s, max 1000 appels/heure, max 10 simultanés (tous clients)
#   - token OAuth valable ~1h → renouveler avant expiration
# Pour les gros volumes (>1000 PRMs), préférer l'API asynchrone ENEDIS
# qui accepte jusqu'à 1000 PRMs en entrée et publie le résultat en FTP.
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
_LC_CHUNK_DAYS = 7
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


# --- Utilitaires CDC : rate limiter et token manager ---

class _RateLimiter:
    """
    Applique les limites ENEDIS sync : 5 req/s, 5 simultanés (marge sur les 10
    tous clients), 950 appels/heure (marge sur les 1000 documentés).
    """

    def __init__(self, rps: float = 5.0, max_concurrent: int = 5, max_hourly: int = 950) -> None:
        self._sem = threading.Semaphore(max_concurrent)
        self._min_interval = 1.0 / rps
        self._last_t = 0.0
        self._rps_lock = threading.Lock()
        self._hourly_ts: list[float] = []
        self._hourly_lock = threading.Lock()
        self._max_hourly = max_hourly

    def acquire(self) -> None:
        # Quota horaire : bloquer si nécessaire
        while True:
            with self._hourly_lock:
                now = _time.monotonic()
                cutoff = now - 3600
                self._hourly_ts = [t for t in self._hourly_ts if t > cutoff]
                if len(self._hourly_ts) < self._max_hourly:
                    break
                wait_s = self._hourly_ts[0] + 3600 - now + 2
            _lc_log(f"Quota horaire ({self._max_hourly}/h) atteint — pause {wait_s:.0f}s")
            _time.sleep(max(wait_s, 1.0))

        # Concurrence
        self._sem.acquire()

        # Débit req/s
        with self._rps_lock:
            now = _time.monotonic()
            elapsed = now - self._last_t
            if elapsed < self._min_interval:
                _time.sleep(self._min_interval - elapsed)
            self._last_t = _time.monotonic()

        with self._hourly_lock:
            self._hourly_ts.append(_time.monotonic())

    def release(self) -> None:
        self._sem.release()


class _TokenManager:
    """Renouvelle le token OAuth ENEDIS 5 min avant expiration, thread-safe."""

    _MARGIN_S = 300

    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._lock = threading.Lock()

    def get(self) -> str:
        with self._lock:
            if not self._token or _time.monotonic() > self._expires_at - self._MARGIN_S:
                self._refresh()
            return self._token  # type: ignore[return-value]

    def _refresh(self) -> None:
        if not settings.enedis_client_id or not settings.enedis_client_secret:
            raise RuntimeError("ENEDIS_CLIENT_ID / ENEDIS_CLIENT_SECRET manquants")
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
        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError(f"Pas de access_token ENEDIS : {resp.text[:300]}")
        expires_in = int(data.get("expires_in", 3600))
        self._token = token
        self._expires_at = _time.monotonic() + expires_in
        _lc_log(f"Token ENEDIS renouvelé (expire dans {expires_in}s)")


def _classify_lc_error(status: int, body: str) -> str:
    """Traduit un code HTTP + corps en outcome métier CDC."""
    if status == 403:
        return "forbidden"
    if status == 404:
        return "not_found"
    if status == 429:
        return "quota_exceeded"
    if status >= 500:
        return "error_technical"
    if status == 400:
        if "ADAM-ERR0069" in body:
            return "cdc_inactive"
        if "ADAM-ERR0023" in body:
            return "not_eligible"
        if "ADAM-ERR0025" in body or "PERIOD" in body.upper():
            return "invalid_period"
    return "error_technical"


def _fetch_lc_prm(
    token_mgr: _TokenManager,
    rl: _RateLimiter,
    prm: str,
    start_date: str,
    end_date: str,
    ingested_at: str,
) -> tuple[list[dict], str, str | None]:
    """
    Fetch CDC pour 1 PRM sur une fenêtre ≤ 7 jours (1 appel API).
    Retourne (rows, outcome, error_detail).
    outcome: ok_data | ok_empty | forbidden | not_found | not_eligible |
             cdc_inactive | invalid_period | quota_exceeded | error_technical
    """
    _RETRY_WAITS = (20, 40, 80)
    resp = None

    for attempt in range(len(_RETRY_WAITS) + 1):
        rl.acquire()
        try:
            resp = requests.get(
                settings.enedis_load_curve_url,
                headers={"Authorization": f"Bearer {token_mgr.get()}", "Accept": "application/json"},
                params={"usage_point_id": prm, "start": start_date, "end": end_date},
                timeout=45,
            )
        except Exception as exc:
            rl.release()
            if attempt < len(_RETRY_WAITS):
                wait = _RETRY_WAITS[attempt]
                LOG.warning(
                    "PRM %s [CDC] %s→%s réseau tentative %d/%d : %s — pause %ds",
                    prm, start_date, end_date, attempt + 1, len(_RETRY_WAITS) + 1, exc, wait,
                )
                _time.sleep(wait)
                continue
            LOG.error("PRM %s [CDC] %s→%s réseau échec définitif : %s", prm, start_date, end_date, exc)
            return [], "error_technical", f"Réseau: {exc}"
        else:
            rl.release()

        status = resp.status_code
        body = resp.text
        LOG.info("PRM %s [CDC] %s→%s → HTTP %d", prm, start_date, end_date, status)

        if status == 200:
            mr = resp.json().get("meter_reading", {})
            unit = mr.get("reading_type", {}).get("unit", "W")
            quality = mr.get("quality", "")
            rows: list[dict] = []
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
            if not rows:
                LOG.info("PRM %s [CDC] %s→%s : 0 point (ok_empty)", prm, start_date, end_date)
            return rows, ("ok_data" if rows else "ok_empty"), None

        # Erreurs retriables : 429 et 5xx
        if status == 429 or status >= 500:
            if attempt < len(_RETRY_WAITS):
                wait = _RETRY_WAITS[attempt]
                LOG.warning(
                    "PRM %s [CDC] %s→%s HTTP %d tentative %d/%d — pause %ds",
                    prm, start_date, end_date, status, attempt + 1, len(_RETRY_WAITS) + 1, wait,
                )
                _time.sleep(wait)
                continue
            outcome = "quota_exceeded" if status == 429 else "error_technical"
            LOG.error("PRM %s [CDC] %s→%s HTTP %d échec définitif", prm, start_date, end_date, status)
            return [], outcome, f"HTTP {status} après {len(_RETRY_WAITS) + 1} tentatives: {body[:300]}"

        # Erreurs définitives (4xx sauf 429)
        outcome = _classify_lc_error(status, body)
        LOG.warning("PRM %s [CDC] %s→%s HTTP %d → %s : %s", prm, start_date, end_date, status, outcome, body[:300])
        return [], outcome, f"HTTP {status}: {body[:300]}"

    outcome = "quota_exceeded" if (resp and resp.status_code == 429) else "error_technical"
    return [], outcome, "Épuisement des tentatives"


def _generate_lc_report(
    prms: list[str],
    results: dict[tuple[str, str, str], tuple[str, str | None]],
    start_str: str,
    end_str: str,
) -> None:
    """Écrit enedis_lc_report.json : PRMs traités/vides/en erreur, chunks manquants, liste à relancer."""
    start_d = date.fromisoformat(start_str)
    end_d = date.fromisoformat(end_str)

    expected_chunks: list[tuple[str, str]] = []
    c = start_d
    while c <= end_d:
        ce = min(c + timedelta(days=_LC_CHUNK_DAYS - 1), end_d)
        expected_chunks.append((c.isoformat(), ce.isoformat()))
        c = ce + timedelta(days=1)

    _OK_RANK = {
        "ok_data": 0, "ok_empty": 1, "cdc_inactive": 2, "not_eligible": 3,
        "forbidden": 4, "not_found": 5, "invalid_period": 6,
        "quota_exceeded": 7, "error_technical": 8,
    }
    prm_best: dict[str, str] = {p: "error_technical" for p in prms}
    for (prm, _, _), (outcome, _) in results.items():
        if _OK_RANK.get(outcome, 8) < _OK_RANK.get(prm_best.get(prm, "error_technical"), 8):
            prm_best[prm] = outcome

    _PERMANENT = {"forbidden", "not_found", "not_eligible", "cdc_inactive", "invalid_period"}
    missing_chunks: list[dict] = []
    retry_list: list[dict] = []
    for prm in prms:
        for cs, ce in expected_chunks:
            key = (prm, cs, ce)
            if key not in results:
                missing_chunks.append({"prm": prm, "start": cs, "end": ce, "reason": "non traité"})
            else:
                outcome, err = results[key]
                if outcome not in ("ok_data", "ok_empty") and outcome not in _PERMANENT:
                    retry_list.append({"prm": prm, "start": cs, "end": ce, "outcome": outcome, "error": err})

    prms_by_outcome: dict[str, list[str]] = {}
    for prm, best in prm_best.items():
        prms_by_outcome.setdefault(best, []).append(prm)

    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "date_from": start_str,
        "date_to": end_str,
        "stats": {
            "prms_total": len(prms),
            "prms_ok_data": len(prms_by_outcome.get("ok_data", [])),
            "prms_ok_empty": len(prms_by_outcome.get("ok_empty", [])),
            "prms_cdc_inactive": len(prms_by_outcome.get("cdc_inactive", [])),
            "prms_not_eligible": len(prms_by_outcome.get("not_eligible", [])),
            "prms_forbidden": len(prms_by_outcome.get("forbidden", [])),
            "prms_not_found": len(prms_by_outcome.get("not_found", [])),
            "prms_error": len(prms_by_outcome.get("error_technical", [])) + len(prms_by_outcome.get("quota_exceeded", [])),
            "chunks_missing": len(missing_chunks),
            "chunks_to_retry": len(retry_list),
        },
        "prms_by_outcome": {k: sorted(v) for k, v in prms_by_outcome.items()},
        "missing_chunks": missing_chunks,
        "retry_list": retry_list,
    }

    path = Path(settings.energie_dir) / "enedis_lc_report.json"
    try:
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        LOG.warning("Impossible d'écrire le rapport CDC : %s", exc)

    s = report["stats"]
    _lc_log(
        f"Rapport complétude — {s['prms_ok_data']} avec données, {s['prms_ok_empty']} vides, "
        f"{s['prms_cdc_inactive']} CDC inactif, {s['prms_not_eligible']} non éligibles, "
        f"{s['prms_error']} erreurs, {s['chunks_missing']} chunks manquants, "
        f"{s['chunks_to_retry']} à relancer → enedis_lc_report.json"
    )


def run_load_curve_sync() -> None:
    """
    Background task : courbe de charge 30 min pour tous les PRMs.
    Respecte les contraintes API ENEDIS sync (1 PRM/appel, 7j max, rate limits).
    Produit un rapport de complétude dans enedis_lc_report.json.
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
                _LC_STATE.update({
                    "status": "success",
                    "finished_at": datetime.utcnow().isoformat(),
                    "last_sync_date": last_sync,
                })
            return

        total_days = (end_d - start_d).days + 1
        chunks_total = (total_days + _LC_CHUNK_DAYS - 1) // _LC_CHUNK_DAYS
        start_str, end_str = start_d.isoformat(), end_d.isoformat()
        total_calls = chunks_total * len(prms)
        with _LC_LOCK:
            _LC_STATE.update({"chunks_total": chunks_total, "date_from": start_str, "date_to": end_str})
        _lc_log(
            f"Fenêtre : {start_str} → {end_str} "
            f"({total_days}j, {chunks_total} chunks × {len(prms)} PRMs = {total_calls} appels)"
        )

        csv_path = Path(settings.energie_dir) / "enedis_load_curve.csv"
        token_mgr = _TokenManager()
        rl = _RateLimiter(rps=5.0, max_concurrent=5, max_hourly=950)
        ingested_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

        # Tracking complet (prm, chunk_start, chunk_end) → (outcome, error_detail)
        all_results: dict[tuple[str, str, str], tuple[str, str | None]] = {}
        total_rows = 0
        chunk_start = start_d
        chunk_idx = 0

        while chunk_start <= end_d:
            chunk_end = min(chunk_start + timedelta(days=_LC_CHUNK_DAYS - 1), end_d)
            cs, ce = chunk_start.isoformat(), chunk_end.isoformat()
            chunk_idx += 1
            _lc_log(f"Chunk {chunk_idx}/{chunks_total} : {cs} → {ce} ({len(prms)} PRMs)")

            chunk_rows: list[dict] = []
            chunk_done = 0
            log_every = max(1, len(prms) // 5)

            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_prm = {
                    executor.submit(_fetch_lc_prm, token_mgr, rl, prm, cs, ce, ingested_at): prm
                    for prm in prms
                }
                for future in as_completed(future_to_prm):
                    prm_id = future_to_prm[future]
                    rows, outcome, err = future.result()
                    chunk_rows.extend(rows)
                    all_results[(prm_id, cs, ce)] = (outcome, err)
                    chunk_done += 1
                    if chunk_done % log_every == 0 or chunk_done == len(prms):
                        _lc_log(f"  {chunk_done}/{len(prms)} PRMs — {len(chunk_rows)} pts collectés")

            ok_n = sum(1 for (_, s, _), (o, _) in all_results.items() if s == cs and o == "ok_data")
            empty_n = sum(1 for (_, s, _), (o, _) in all_results.items() if s == cs and o == "ok_empty")
            err_n = sum(
                1 for (_, s, _), (o, _) in all_results.items()
                if s == cs and o not in ("ok_data", "ok_empty", "forbidden", "not_found", "not_eligible", "cdc_inactive")
            )
            _lc_log(f"  → {ok_n} avec données, {empty_n} vides, {err_n} erreurs techniques")

            appended = _append_lc_csv(chunk_rows, csv_path)
            total_rows += appended
            _save_lc_state(ce)
            with _LC_LOCK:
                _LC_STATE.update({"chunks_done": chunk_idx, "rows_added": total_rows, "last_sync_date": ce})
            _lc_log(f"  Chunk OK — {appended} pts écrits ({total_rows} total)")

            chunk_start = chunk_end + timedelta(days=1)

        _generate_lc_report(prms, all_results, start_str, end_str)

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
