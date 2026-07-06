"""Operational diagnostics for the private PRONO value workflow."""
from __future__ import annotations

import os
import time
from typing import Any

from app.ligue1 import data as ligue1_data
from app.ligue1 import service as ligue1_service
from app.value import service as value_service


def _cache_info() -> dict[str, Any]:
    path = ligue1_data.RAW_CACHE
    exists = os.path.exists(path)
    age_hours = None
    if exists:
        try:
            age_hours = round((time.time() - os.path.getmtime(path)) / 3600.0, 2)
        except OSError:
            age_hours = None
    return {
        "path": path,
        "exists": exists,
        "fresh": bool(exists and ligue1_data._cache_fresh()),
        "age_hours": age_hours,
        "ttl_hours": ligue1_data.RAW_CACHE_TTL_HOURS,
    }


def _check_history() -> dict[str, Any]:
    cache = _cache_info()
    try:
        history = ligue1_data.load_history()
        count = int(len(history))
        seasons = sorted(history["Season"].astype(str).unique().tolist()) if count and "Season" in history else []
        return {
            "name": "ligue1_history",
            "status": "ok" if count else "error",
            "ok": count > 0,
            "count": count,
            "first_kickoff": str(history["Kickoff"].min()) if count and "Kickoff" in history else None,
            "last_kickoff": str(history["Kickoff"].max()) if count and "Kickoff" in history else None,
            "seasons": seasons,
            "cache": cache,
            "message": "Historical Ligue 1 data loaded." if count else "No historical Ligue 1 data available.",
        }
    except Exception as exc:
        return {
            "name": "ligue1_history",
            "status": "error",
            "ok": False,
            "cache": cache,
            "error": str(exc),
            "message": "Historical Ligue 1 data failed to load.",
        }


def _check_upcoming() -> dict[str, Any]:
    try:
        upcoming = ligue1_data.load_upcoming()
        count = int(len(upcoming))
        return {
            "name": "ligue1_upcoming",
            "status": "ok" if count else "degraded",
            "ok": True,
            "count": count,
            "first_kickoff": str(upcoming["Kickoff"].min()) if count and "Kickoff" in upcoming else None,
            "message": "Upcoming fixtures available." if count else "No upcoming fixtures; PRONO can use historical demo mode.",
        }
    except Exception as exc:
        return {
            "name": "ligue1_upcoming",
            "status": "degraded",
            "ok": True,
            "count": 0,
            "error": str(exc),
            "message": "Upcoming fixtures failed; historical demo mode may still work.",
        }


def _check_scenarios(refresh: bool = False) -> dict[str, Any]:
    try:
        payload = ligue1_service.build_journee(force=refresh)
        count = len(payload.get("matches", [])) if isinstance(payload, dict) else 0
        source = payload.get("source") if isinstance(payload, dict) else None
        return {
            "name": "ligue1_scenarios",
            "status": "ok" if count else "error",
            "ok": count > 0,
            "count": count,
            "source": source,
            "demo_mode": bool(source and "Demo" in source),
            "message": "Scenario payload can be built." if count else "Scenario payload has no match.",
        }
    except Exception as exc:
        return {
            "name": "ligue1_scenarios",
            "status": "error",
            "ok": False,
            "count": 0,
            "error": str(exc),
            "message": "Scenario payload failed to build.",
        }


def _check_odds_store() -> dict[str, Any]:
    try:
        stats = value_service.snapshot_store_stats()
        total = int(stats.total_count)
        return {
            "name": "odds_snapshots",
            "status": "ok" if total else "degraded",
            "ok": True,
            "count": total,
            "db_path": stats.db_path,
            "by_source": dict(stats.by_source),
            "odds_api_key_configured": bool(os.environ.get("PRONO_ODDS_API_KEY")),
            "message": "Odds snapshots are available." if total else "No odds snapshot yet; CSV/API collection is still needed.",
        }
    except Exception as exc:
        return {
            "name": "odds_snapshots",
            "status": "degraded",
            "ok": True,
            "count": 0,
            "odds_api_key_configured": bool(os.environ.get("PRONO_ODDS_API_KEY")),
            "error": str(exc),
            "message": "Odds snapshot store failed to load.",
        }


def build_value_diagnostics(refresh: bool = False) -> dict[str, Any]:
    checks = [
        _check_history(),
        _check_upcoming(),
        _check_scenarios(refresh=refresh),
        _check_odds_store(),
    ]
    has_error = any(check["status"] == "error" for check in checks)
    has_degraded = any(check["status"] == "degraded" for check in checks)
    status = "error" if has_error else ("degraded" if has_degraded else "ok")
    return {
        "ok": not has_error,
        "status": status,
        "checks": checks,
        "summary": {
            "can_build_scenarios": next((c["ok"] for c in checks if c["name"] == "ligue1_scenarios"), False),
            "has_upcoming_fixtures": next((c.get("count", 0) > 0 for c in checks if c["name"] == "ligue1_upcoming"), False),
            "has_odds_snapshots": next((c.get("count", 0) > 0 for c in checks if c["name"] == "odds_snapshots"), False),
            "needs_user_odds_action": not next((c.get("count", 0) > 0 for c in checks if c["name"] == "odds_snapshots"), False),
        },
        "warning": "Diagnostics are operational only; odds data must stay outside the sports scenario engine.",
    }
