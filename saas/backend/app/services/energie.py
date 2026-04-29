import csv
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import settings


def _csv_rows(filename: str) -> list[dict[str, str]]:
    path = Path(settings.energie_dir) / filename
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def _contracts() -> dict[str, dict[str, str]]:
    return {r["usage_point_id"]: r for r in _csv_rows("enedis_contracts.csv")}


@lru_cache(maxsize=1)
def _addresses() -> dict[str, dict[str, str]]:
    return {r["usage_point_id"]: r for r in _csv_rows("enedis_addresses.csv")}


@lru_cache(maxsize=1)
def _connections() -> dict[str, dict[str, str]]:
    return {r["usage_point_id"]: r for r in _csv_rows("enedis_connections.csv")}


@lru_cache(maxsize=1)
def _summaries() -> dict[str, dict[str, str]]:
    return {r["usage_point_id"]: r for r in _csv_rows("enedis_contract_summary.csv")}


@lru_cache(maxsize=1)
def _max_power_index() -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for r in _csv_rows("enedis_max_power.csv"):
        uid = r.get("usage_point_id", "")
        raw = r.get("value_va")
        if not uid or not raw:
            continue
        try:
            fval = float(raw)
        except ValueError:
            continue
        index.setdefault(uid, []).append({"date": r["date"], "value_va": fval})
    for uid in index:
        index[uid].sort(key=lambda x: x["date"])
    return index


@lru_cache(maxsize=1)
def _load_curve_index() -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for r in _csv_rows("enedis_load_curve.csv"):
        uid = r.get("usage_point_id", "")
        raw = r.get("value_w")
        if not uid or not raw:
            continue
        try:
            fval = float(raw)
        except ValueError:
            continue
        index.setdefault(uid, []).append({"datetime": r["datetime"], "value_w": fval})
    for uid in index:
        index[uid].sort(key=lambda x: x["datetime"])
    return index


def _safe_float(val: str | None) -> float | None:
    if not val:
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _addr_display(addr: dict[str, str] | None) -> str:
    if not addr:
        return ""
    parts = [
        addr.get("address_number_street_name", ""),
        addr.get("address_postal_code_city", ""),
    ]
    return ", ".join(p for p in parts if p)


def get_energie_overview() -> dict[str, Any]:
    contracts = _contracts()
    addresses = _addresses()
    connections = _connections()
    summaries = _summaries()

    prms = []
    total_kva = 0.0
    for uid, contract in contracts.items():
        kva = _safe_float(contract.get("0_subscribed_power_value"))
        if kva:
            total_kva += kva
        addr = addresses.get(uid)
        conn = connections.get(uid)
        summary = summaries.get(uid)
        prms.append(
            {
                "usage_point_id": uid,
                "name": contract.get("0_organization_commercial_name") or contract.get("0_organization_name") or uid,
                "address": _addr_display(addr),
                "contractor": contract.get("0_contractor") or "",
                "subscribed_power_kva": kva,
                "tariff": contract.get("0_distribution_tariff"),
                "segment": contract.get("0_segment"),
                "connection_state": conn.get("connection_state") if conn else None,
                "services_level": summary.get("services_level") if summary else None,
            }
        )

    prms.sort(key=lambda x: (x["name"] or "").lower())
    return {
        "kpis": {
            "total_prms": len(prms),
            "total_subscribed_kva": round(total_kva, 1),
        },
        "prms": prms,
    }


def get_prm_detail(prm_id: str) -> dict[str, Any] | None:
    contracts = _contracts()
    if prm_id not in contracts:
        return None
    contract = contracts[prm_id]
    addr = _addresses().get(prm_id) or {}
    conn = _connections().get(prm_id) or {}
    summary = _summaries().get(prm_id) or {}

    return {
        "usage_point_id": prm_id,
        "contract": {
            "usage_point_id": prm_id,
            "contract_start": contract.get("0_contract_start"),
            "contract_type": contract.get("0_contract_type"),
            "contractor": contract.get("0_contractor"),
            "tariff": contract.get("0_distribution_tariff"),
            "subscribed_power_kva": _safe_float(contract.get("0_subscribed_power_value")),
            "segment": contract.get("0_segment"),
            "organization_name": contract.get("0_organization_name"),
            "name": contract.get("0_organization_commercial_name") or contract.get("0_organization_name"),
        },
        "address": {
            "address_number_street_name": addr.get("address_number_street_name"),
            "address_postal_code_city": addr.get("address_postal_code_city"),
            "address_staircase_floor_apartment": addr.get("address_staircase_floor_apartment"),
            "address_building": addr.get("address_building"),
            "address_insee_code": addr.get("address_insee_code"),
        },
        "connection": {
            "serial_number": conn.get("serial_number"),
            "connection_state": conn.get("connection_state"),
            "voltage_level": conn.get("voltage_level"),
            "subscribed_kva": _safe_float(conn.get("generation_connection_power_value")),
        },
        "summary": {
            "segment": summary.get("segments_0_segment"),
            "activation_date": summary.get("consumption_last_activation_date"),
            "last_power_change_date": summary.get("last_subscribed_power_change_date"),
            "services_level": summary.get("services_level"),
        },
    }


def get_prm_max_power(prm_id: str) -> dict[str, Any]:
    return {
        "usage_point_id": prm_id,
        "points": _max_power_index().get(prm_id, []),
    }


def get_prm_load_curve(prm_id: str, days: int | None = None) -> dict[str, Any]:
    points = list(_load_curve_index().get(prm_id, []))
    if days and points:
        try:
            end_date = date.fromisoformat(points[-1]["datetime"][:10])
            start_str = (end_date - timedelta(days=days - 1)).isoformat()
            points = [p for p in points if p["datetime"][:10] >= start_str]
        except ValueError:
            pass
    return {
        "usage_point_id": prm_id,
        "points": points,
    }
