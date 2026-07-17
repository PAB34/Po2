"""Index SQLite de la courbe de charge ENEDIS.

`enedis_load_curve.csv` agrège tous les PRM au pas 30 min sur plusieurs années
et dépasse le Go. Le charger entièrement en mémoire fait exploser la RAM (OOM).
Ce module construit un index SQLite `enedis_load_curve.sqlite` indexé sur
`(prm_id, dt)` à partir du CSV, et expose un accès **par PRM et par période**
rapide et à mémoire bornée (seules les lignes demandées sont lues).

Le CSV reste la source de vérité (produit par la sync ENEDIS). L'index est
reconstruit automatiquement dès que le CSV est plus récent que la base SQLite
(détection par mtime), de façon atomique (build dans un fichier temporaire puis
renommage), pour que les lecteurs voient toujours une base complète.
"""

from __future__ import annotations

import csv
import sqlite3
import threading
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from app.core.config import settings

_BUILD_LOCK = threading.Lock()
_INSERT_BATCH = 50_000


def _csv_path() -> Path:
    return Path(settings.energie_dir) / "enedis_load_curve.csv"


def _sqlite_path() -> Path:
    return Path(settings.energie_dir) / "enedis_load_curve.sqlite"


def _is_stale() -> bool:
    csv_path = _csv_path()
    if not csv_path.exists():
        return False
    db_path = _sqlite_path()
    if not db_path.exists():
        return True
    return csv_path.stat().st_mtime > db_path.stat().st_mtime


def ensure_index(force: bool = False) -> None:
    """Construit/reconstruit l'index SQLite si le CSV a changé (ou si force)."""
    if not force and not _is_stale():
        return
    with _BUILD_LOCK:
        if not force and not _is_stale():
            return
        _rebuild()


def _rebuild() -> None:
    csv_path = _csv_path()
    if not csv_path.exists():
        return
    building = _sqlite_path().with_name(_sqlite_path().name + ".building")
    if building.exists():
        building.unlink()

    con = sqlite3.connect(str(building))
    try:
        con.execute("PRAGMA journal_mode=OFF")
        con.execute("PRAGMA synchronous=OFF")
        con.execute("CREATE TABLE load_curve (prm_id TEXT NOT NULL, dt TEXT NOT NULL, value_w REAL NOT NULL)")
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            batch: list[tuple[str, str, float]] = []
            for row in reader:
                uid = row.get("usage_point_id", "")
                dt = row.get("datetime", "")
                raw = row.get("value_w")
                if not uid or not dt or not raw:
                    continue
                try:
                    value = float(raw)
                except ValueError:
                    continue
                batch.append((uid, dt, value))
                if len(batch) >= _INSERT_BATCH:
                    con.executemany("INSERT INTO load_curve VALUES (?, ?, ?)", batch)
                    batch.clear()
            if batch:
                con.executemany("INSERT INTO load_curve VALUES (?, ?, ?)", batch)
        con.execute("CREATE INDEX idx_load_curve_prm_dt ON load_curve (prm_id, dt)")
        con.commit()
    finally:
        con.close()

    # Swap atomique : les lecteurs voient soit l'ancienne base, soit la nouvelle.
    building.replace(_sqlite_path())


def _connect_ro() -> sqlite3.Connection | None:
    db_path = _sqlite_path()
    if not db_path.exists():
        return None
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


def data_range_summary() -> dict[str, Any]:
    """Return global load-curve date range from SQLite without scanning the huge CSV."""
    con = _connect_ro()
    if con is None:
        return {"first_date": None, "last_date": None, "row_count": 0, "stale": _is_stale()}
    try:
        first_date, last_date, row_count = con.execute(
            "SELECT MIN(substr(dt, 1, 10)), MAX(substr(dt, 1, 10)), COUNT(*) FROM load_curve"
        ).fetchone()
    finally:
        con.close()
    return {
        "first_date": first_date,
        "last_date": last_date,
        "row_count": int(row_count or 0),
        "stale": _is_stale(),
    }


def coverage_summary() -> dict[str, Any]:
    """Return per-PRM coverage from the SQLite index, shaped like energie._source_coverage."""
    con = _connect_ro()
    empty = {
        "first_date": None,
        "last_date": None,
        "row_count": 0,
        "bad_date_rows": 0,
        "prms": {},
        "stale": _is_stale(),
    }
    if con is None:
        return empty

    try:
        rows = con.execute(
            """
            SELECT
                prm_id,
                MIN(substr(dt, 1, 10)),
                MAX(substr(dt, 1, 10)),
                COUNT(DISTINCT substr(dt, 1, 10)),
                COUNT(*)
            FROM load_curve
            WHERE prm_id <> ''
            GROUP BY prm_id
            """
        ).fetchall()
    finally:
        con.close()

    first_date = None
    last_date = None
    row_count = 0
    prms: dict[str, dict[str, Any]] = {}
    for prm_id, prm_first, prm_last, covered_days, prm_rows in rows:
        row_count += int(prm_rows or 0)
        if prm_first and (first_date is None or prm_first < first_date):
            first_date = prm_first
        if prm_last and (last_date is None or prm_last > last_date):
            last_date = prm_last
        prms[str(prm_id)] = {
            "row_count": int(prm_rows or 0),
            "covered_days": int(covered_days or 0),
            "first_date": prm_first,
            "last_date": prm_last,
        }

    return {
        "first_date": first_date,
        "last_date": last_date,
        "row_count": row_count,
        "bad_date_rows": 0,
        "prms": prms,
        "stale": _is_stale(),
    }


def points_for_prm(
    prm_id: str,
    start: date | None = None,
    end: date | None = None,
) -> list[dict[str, Any]]:
    """Points de courbe de charge d'un PRM, optionnellement bornés à [start, end].

    Retourne `[{"datetime": str, "value_w": float}, ...]` trié par horodatage.
    Mémoire bornée au seul résultat (une période d'un PRM), grâce à l'index.
    """
    if not prm_id:
        return []
    ensure_index()
    con = _connect_ro()
    if con is None:
        return []
    try:
        if start is not None and end is not None:
            lo = start.isoformat()
            hi = (end + timedelta(days=1)).isoformat()
            rows = con.execute(
                "SELECT dt, value_w FROM load_curve WHERE prm_id = ? AND dt >= ? AND dt < ? ORDER BY dt",
                (prm_id, lo, hi),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT dt, value_w FROM load_curve WHERE prm_id = ? ORDER BY dt",
                (prm_id,),
            ).fetchall()
    finally:
        con.close()
    return [{"datetime": dt, "value_w": value} for dt, value in rows]


def has_data(prm_id: str) -> bool:
    if not prm_id:
        return False
    ensure_index()
    con = _connect_ro()
    if con is None:
        return False
    try:
        row = con.execute(
            "SELECT 1 FROM load_curve WHERE prm_id = ? LIMIT 1",
            (prm_id,),
        ).fetchone()
    finally:
        con.close()
    return row is not None
