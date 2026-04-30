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


def _csv_rows_path(path: Path) -> list[dict[str, str]]:
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
def _daily_consumption_index() -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for r in _csv_rows("enedis_data.csv"):
        uid = r.get("usage_point_id", "")
        raw = r.get("value_wh")
        if not uid or not raw:
            continue
        try:
            fval = float(raw)
        except ValueError:
            continue
        index.setdefault(uid, []).append({"date": r["date"], "value_wh": fval})
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


@lru_cache(maxsize=1)
def _dju_rows() -> list[dict[str, str]]:
    dju_path = Path(settings.energie_dir) / "DJU" / "dju_sete.csv"
    return _csv_rows_path(dju_path)


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


def _compute_calibration(peak_kva: float, subscribed_kva: float) -> tuple[str, float]:
    """Returns (status_key, ratio_percent)."""
    if subscribed_kva <= 0:
        return "inconnu", 0.0
    ratio = peak_kva / subscribed_kva * 100
    if ratio > 95:
        status = "sous_dimensionne"
    elif ratio > 80:
        status = "proche_seuil"
    elif ratio >= 40:
        status = "bien_calibre"
    else:
        status = "sur_souscrit"
    return status, round(ratio, 1)


def _peak_kva_3y(prm_id: str) -> float | None:
    points = _max_power_index().get(prm_id)
    if not points:
        return None
    return round(max(p["value_va"] for p in points) / 1000, 2)


def get_energie_overview() -> dict[str, Any]:
    contracts = _contracts()
    addresses = _addresses()
    connections = _connections()
    summaries = _summaries()

    prms = []
    total_kva = 0.0
    calibration_counts: dict[str, int] = {
        "sous_dimensionne": 0,
        "proche_seuil": 0,
        "bien_calibre": 0,
        "sur_souscrit": 0,
        "inconnu": 0,
    }
    supplier_kva: dict[str, float] = {}
    supplier_count: dict[str, int] = {}

    for uid, contract in contracts.items():
        kva = _safe_float(contract.get("0_subscribed_power_value"))
        if kva:
            total_kva += kva

        supplier = contract.get("0_contractor") or "Inconnu"
        supplier_kva[supplier] = supplier_kva.get(supplier, 0.0) + (kva or 0.0)
        supplier_count[supplier] = supplier_count.get(supplier, 0) + 1

        peak = _peak_kva_3y(uid)
        calibration_status: str | None = None
        calibration_ratio: float | None = None
        if peak is not None and kva and kva > 0:
            calibration_status, calibration_ratio = _compute_calibration(peak, kva)
            calibration_counts[calibration_status] = calibration_counts.get(calibration_status, 0) + 1
        else:
            calibration_counts["inconnu"] += 1

        addr = addresses.get(uid)
        conn = connections.get(uid)
        summary = summaries.get(uid)
        prms.append(
            {
                "usage_point_id": uid,
                "name": contract.get("0_organization_commercial_name") or contract.get("0_organization_name") or uid,
                "address": _addr_display(addr),
                "contractor": supplier,
                "subscribed_power_kva": kva,
                "tariff": contract.get("0_distribution_tariff"),
                "segment": contract.get("0_segment"),
                "connection_state": conn.get("connection_state") if conn else None,
                "services_level": summary.get("services_level") if summary else None,
                "peak_kva_3y": peak,
                "calibration_status": calibration_status,
                "calibration_ratio": calibration_ratio,
            }
        )

    prms.sort(key=lambda x: (x["name"] or "").lower())

    supplier_distribution = [
        {
            "supplier": s,
            "total_kva": round(supplier_kva[s], 1),
            "prm_count": supplier_count[s],
        }
        for s in sorted(supplier_kva, key=lambda k: -supplier_kva[k])
    ]

    return {
        "kpis": {
            "total_prms": len(prms),
            "total_subscribed_kva": round(total_kva, 1),
            "sous_dimensionnes": calibration_counts["sous_dimensionne"],
            "proche_seuil": calibration_counts["proche_seuil"],
            "sur_souscrits": calibration_counts["sur_souscrit"],
        },
        "supplier_distribution": supplier_distribution,
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

    subscribed_kva = _safe_float(contract.get("0_subscribed_power_value"))
    peak = _peak_kva_3y(prm_id)
    calibration_status = None
    calibration_ratio = None
    calibration_recommendation = None
    if peak is not None and subscribed_kva and subscribed_kva > 0:
        calibration_status, calibration_ratio = _compute_calibration(peak, subscribed_kva)
        recommendations = {
            "sous_dimensionne": "Risque de dépassement — augmenter la puissance souscrite.",
            "proche_seuil": "Proche du seuil — surveiller et anticiper une révision à la hausse.",
            "bien_calibre": "Contrat bien dimensionné.",
            "sur_souscrit": "Sur-souscrit — négocier une puissance inférieure pour réduire les coûts.",
        }
        calibration_recommendation = recommendations.get(calibration_status)

    return {
        "usage_point_id": prm_id,
        "contract": {
            "usage_point_id": prm_id,
            "contract_start": contract.get("0_contract_start"),
            "contract_type": contract.get("0_contract_type"),
            "contractor": contract.get("0_contractor"),
            "tariff": contract.get("0_distribution_tariff"),
            "subscribed_power_kva": subscribed_kva,
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
        "calibration": {
            "subscribed_kva": subscribed_kva,
            "peak_kva_3y": peak,
            "ratio_percent": calibration_ratio,
            "status": calibration_status,
            "recommendation": calibration_recommendation,
        },
    }


def get_prm_annual_profile(prm_id: str) -> dict[str, Any]:
    """Monthly max kVA per year (N, N-1, N-2) from max_power data."""
    points = _max_power_index().get(prm_id, [])
    subscribed_kva = None
    contract = _contracts().get(prm_id)
    if contract:
        subscribed_kva = _safe_float(contract.get("0_subscribed_power_value"))

    by_year_month: dict[str, dict[str, float]] = {}
    for p in points:
        year = p["date"][:4]
        month = p["date"][5:7]
        kva = round(p["value_va"] / 1000, 2)
        by_year_month.setdefault(year, {})
        if month not in by_year_month[year] or kva > by_year_month[year][month]:
            by_year_month[year][month] = kva

    profiles = []
    for year in sorted(by_year_month.keys(), reverse=True)[:3]:
        months = [
            {"month": m, "max_kva": by_year_month[year][m]}
            for m in sorted(by_year_month[year].keys())
        ]
        profiles.append({"year": year, "months": months})

    return {
        "usage_point_id": prm_id,
        "subscribed_kva": subscribed_kva,
        "profiles": profiles,
    }


def get_prm_daily_consumption(prm_id: str, days: int | None = 90) -> dict[str, Any]:
    points = list(_daily_consumption_index().get(prm_id, []))
    if days and points:
        try:
            end_date = date.fromisoformat(points[-1]["date"])
            start_str = (end_date - timedelta(days=days - 1)).isoformat()
            points = [p for p in points if p["date"] >= start_str]
        except ValueError:
            pass
    return {
        "usage_point_id": prm_id,
        "points": [
            {"date": p["date"], "value_kwh": round(p["value_wh"] / 1000, 3)}
            for p in points
        ],
    }


def get_prm_max_power(prm_id: str) -> dict[str, Any]:
    contract = _contracts().get(prm_id)
    subscribed_kva = None
    if contract:
        subscribed_kva = _safe_float(contract.get("0_subscribed_power_value"))
    return {
        "usage_point_id": prm_id,
        "subscribed_kva": subscribed_kva,
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


def get_dju_monthly() -> list[dict[str, Any]]:
    """Monthly aggregated DJU (heating + cooling) from dju_sete.csv."""
    rows = _dju_rows()
    by_month: dict[str, dict[str, float]] = {}
    for r in rows:
        d = r.get("date", "")
        if len(d) < 7:
            continue
        ym = d[:7]  # YYYY-MM
        h = _safe_float(r.get("dju_chauffage_base_18")) or 0.0
        c = _safe_float(r.get("dju_froid_base_22")) or 0.0
        if ym not in by_month:
            by_month[ym] = {"dju_chauffe": 0.0, "dju_froid": 0.0}
        by_month[ym]["dju_chauffe"] += h
        by_month[ym]["dju_froid"] += c

    return [
        {
            "month": ym,
            "dju_chauffe": round(by_month[ym]["dju_chauffe"], 1),
            "dju_froid": round(by_month[ym]["dju_froid"], 1),
        }
        for ym in sorted(by_month.keys())
    ]
