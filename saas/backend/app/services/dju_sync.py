"""
DJU sync service — météo Open-Meteo → DJU chauffage (COSTIC) + froid (Météo-France).
Incrémental : reprend depuis la dernière date connue dans DJU/dju_sete.csv.
"""
from __future__ import annotations

import csv as _csv
import logging
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from app.core.config import settings

LOG = logging.getLogger(__name__)

_LOCK = threading.Lock()
_STATE: dict[str, Any] = {
    "status": "idle",
    "last_sync_date": None,
    "rows_added": 0,
    "error": None,
    "log": [],
}
_MAX_LOG = 30

_CITY = "Sète"
_COUNTRY = "FR"
_BASE_H = 18.0
_BASE_C = 22.0
_HISTORY_START = "2015-01-01"

_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
_ARCH_URL = "https://archive-api.open-meteo.com/v1/archive"


def _log(msg: str) -> None:
    LOG.info(msg)
    with _LOCK:
        _STATE["log"].append(f"{datetime.utcnow().strftime('%H:%M:%S')} {msg}")
        if len(_STATE["log"]) > _MAX_LOG:
            _STATE["log"] = _STATE["log"][-_MAX_LOG:]


def get_dju_sync_status() -> dict[str, Any]:
    with _LOCK:
        return dict(_STATE)


def is_dju_running() -> bool:
    with _LOCK:
        return _STATE["status"] == "running"


def _csv_path() -> Path:
    return Path(settings.energie_dir) / "DJU" / "dju_sete.csv"


def _get_location() -> tuple[float, float, str]:
    r = requests.get(_GEO_URL, params={
        "name": _CITY, "count": 1, "language": "fr", "format": "json", "countryCode": _COUNTRY,
    }, timeout=30)
    r.raise_for_status()
    locs = r.json().get("results", [])
    if not locs:
        raise RuntimeError(f"Localisation introuvable : {_CITY} ({_COUNTRY})")
    loc = locs[0]
    return loc["latitude"], loc["longitude"], loc.get("timezone", "Europe/Paris")


def _get_archive(lat: float, lon: float, tz: str, start: str, end: str) -> list[dict]:
    r = requests.get(_ARCH_URL, params={
        "latitude": lat, "longitude": lon,
        "start_date": start, "end_date": end,
        "daily": "temperature_2m_min,temperature_2m_max",
        "timezone": tz,
    }, timeout=60)
    r.raise_for_status()
    d = r.json().get("daily", {})
    return [
        {"date": t, "tmin_c": mn, "tmax_c": mx}
        for t, mn, mx in zip(
            d.get("time", []),
            d.get("temperature_2m_min", []),
            d.get("temperature_2m_max", []),
        )
    ]


def _h_costic(tmin: float | None, tmax: float | None) -> float | None:
    if tmin is None or tmax is None:
        return None
    if _BASE_H >= tmax:
        return round(_BASE_H - (tmin + tmax) / 2, 2)
    if _BASE_H <= tmin:
        return 0.0
    a = tmax - tmin
    if a == 0:
        return 0.0
    b = (_BASE_H - tmin) / a
    return round(a * b * (0.08 + 0.42 * b), 2)


def _c_mean(tmin: float | None, tmax: float | None) -> float | None:
    if tmin is None or tmax is None:
        return None
    return round(max((tmin + tmax) / 2 - _BASE_C, 0), 2)


def _season_h(ds: str) -> str:
    m, y = int(ds[5:7]), int(ds[:4])
    return f"{y}/{y + 1}" if m >= 9 else f"{y - 1}/{y}"


def _season_c(ds: str) -> str:
    m, y = int(ds[5:7]), int(ds[:4])
    return str(y) if 5 <= m <= 9 else ""


def _upsert(new_rows: list[dict], path: Path) -> int:
    existing: dict[str, dict] = {}
    cols: list[str] = []
    if path.exists() and path.stat().st_size > 0:
        with open(path, encoding="utf-8", newline="") as f:
            rdr = _csv.DictReader(f)
            cols = list(rdr.fieldnames or [])
            for r in rdr:
                existing[r["date"]] = dict(r)
    added = sum(1 for r in new_rows if r["date"] not in existing)
    for r in new_rows:
        existing[r["date"]] = {k: "" if v is None else str(v) for k, v in r.items()}
    all_cols = list(dict.fromkeys(cols + (list(new_rows[0]) if new_rows else [])))
    if not all_cols:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=all_cols, extrasaction="ignore")
        w.writeheader()
        for r in sorted(existing.values(), key=lambda x: x.get("date", "")):
            w.writerow({k: r.get(k, "") for k in all_cols})
    return added


def run_dju_sync() -> None:
    """Background task : Open-Meteo → calcul DJU → upsert DJU/dju_sete.csv."""
    with _LOCK:
        if _STATE["status"] == "running":
            return
        _STATE.update({"status": "running", "error": None, "log": [], "rows_added": 0})

    try:
        path = _csv_path()
        today = date.today()
        end_d = today - timedelta(days=1)

        start_d = date.fromisoformat(_HISTORY_START)
        if path.exists() and path.stat().st_size > 0:
            max_d: str | None = None
            with open(path, encoding="utf-8", newline="") as f:
                for r in _csv.DictReader(f):
                    d = r.get("date", "")
                    if d and (max_d is None or d > max_d):
                        max_d = d
            if max_d:
                start_d = date.fromisoformat(max_d) + timedelta(days=1)
                _log(f"Reprise depuis {start_d} (données jusqu'au {max_d})")

        if start_d > end_d:
            _log("DJU déjà à jour.")
            with _LOCK:
                _STATE["status"] = "success"
            return

        _log(f"Collecte Open-Meteo : {start_d} → {end_d} pour {_CITY}")
        lat, lon, tz = _get_location()
        raw = _get_archive(lat, lon, tz, start_d.isoformat(), end_d.isoformat())
        _log(f"{len(raw)} jours récupérés")

        h_col = f"dju_chauffage_base_{int(_BASE_H)}"
        c_col = f"dju_froid_base_{int(_BASE_C)}"
        rows = []
        for r in raw:
            tmin = float(r["tmin_c"]) if r["tmin_c"] not in (None, "") else None
            tmax = float(r["tmax_c"]) if r["tmax_c"] not in (None, "") else None
            tmoy = round((tmin + tmax) / 2, 2) if tmin is not None and tmax is not None else None
            rows.append({
                "date": r["date"],
                "tmin_c": tmin,
                "tmax_c": tmax,
                "tmoy_c": tmoy,
                h_col: _h_costic(tmin, tmax),
                c_col: _c_mean(tmin, tmax),
                "saison_chauffe": _season_h(r["date"]),
                "saison_froid": _season_c(r["date"]),
            })

        added = _upsert(rows, path)
        _log(f"OK — {added} nouveaux jours ({len(rows)} traités)")

        try:
            from app.services.energie import _dju_monthly_index, _dju_rows, get_data_ranges  # noqa: PLC0415
            _dju_monthly_index.cache_clear()
            _dju_rows.cache_clear()
            get_data_ranges.cache_clear()
            _log("Caches DJU invalidés.")
        except Exception:
            pass

        with _LOCK:
            _STATE.update({"status": "success", "last_sync_date": end_d.isoformat(), "rows_added": added})

    except Exception as exc:
        msg = str(exc)
        _log(f"ERREUR : {msg}")
        LOG.exception("DJU sync error")
        with _LOCK:
            _STATE.update({"status": "error", "error": msg})
