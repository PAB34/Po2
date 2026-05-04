import csv
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import settings


def _scan_csv_dates(rel_path: str, date_col: str) -> dict[str, Any]:
    """Scanne un CSV en streaming pour trouver première/dernière date et nombre de lignes."""
    path = Path(settings.energie_dir) / rel_path
    if not path.exists() or path.stat().st_size == 0:
        return {"first_date": None, "last_date": None, "row_count": 0}
    min_d = max_d = None
    count = 0
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            return {"first_date": None, "last_date": None, "row_count": 0}
        try:
            col_idx = header.index(date_col)
        except ValueError:
            return {"first_date": None, "last_date": None, "row_count": 0}
        for row in reader:
            if len(row) > col_idx:
                d = row[col_idx][:10]
                if len(d) == 10:
                    count += 1
                    if min_d is None or d < min_d:
                        min_d = d
                    if max_d is None or d > max_d:
                        max_d = d
    return {"first_date": min_d, "last_date": max_d, "row_count": count}


@lru_cache(maxsize=1)
def get_data_ranges() -> dict[str, Any]:
    """Retourne les plages de dates disponibles pour chaque source de données."""
    # Contrats : simple comptage
    contracts_count = 0
    cp = Path(settings.energie_dir) / "enedis_contracts.csv"
    if cp.exists():
        with open(cp, encoding="utf-8-sig") as f:
            contracts_count = max(0, sum(1 for _ in f) - 1)

    return {
        "consumption": _scan_csv_dates("enedis_data.csv", "date"),
        "max_power": _scan_csv_dates("enedis_max_power.csv", "date"),
        "load_curve": _scan_csv_dates("enedis_load_curve.csv", "datetime"),
        "dju": _scan_csv_dates("DJU/dju_sete.csv", "date"),
        "contracts": {"count": contracts_count},
    }


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


@lru_cache(maxsize=1)
def _dju_monthly_index() -> dict[str, dict[str, float]]:
    """Returns {YYYY-MM: {dju_chauffe, dju_froid}}."""
    rows = _dju_rows()
    by_month: dict[str, dict[str, float]] = {}
    for r in rows:
        d = r.get("date", "")
        if len(d) < 7:
            continue
        ym = d[:7]
        h = _safe_float(r.get("dju_chauffage_base_18")) or 0.0
        c = _safe_float(r.get("dju_froid_base_22")) or 0.0
        if ym not in by_month:
            by_month[ym] = {"dju_chauffe": 0.0, "dju_froid": 0.0}
        by_month[ym]["dju_chauffe"] += h
        by_month[ym]["dju_froid"] += c
    return by_month


@lru_cache(maxsize=1)
def _consumption_by_month() -> dict[str, dict[str, float]]:
    """Returns {prm_id: {YYYY-MM: kWh}}."""
    result: dict[str, dict[str, float]] = {}
    for prm_id, points in _daily_consumption_index().items():
        by_month: dict[str, float] = {}
        for p in points:
            ym = p["date"][:7]
            by_month[ym] = by_month.get(ym, 0.0) + p["value_wh"] / 1000.0
        result[prm_id] = {ym: round(v, 2) for ym, v in by_month.items()}
    return result


_DJU_HEATING_MIN = 10.0
_DJU_COOLING_MIN = 5.0
_DJU_PERF_TOLERANCE = 0.10   # ±10 % = "dans la cible"
_DJU_PERF_MIN_MONTHS = 3


def _build_dju_side(
    dju_idx: dict[str, dict[str, float]],
    conso_idx: dict[str, float],
    current_ym: str,
    dju_key: str,
    dju_min: float,
) -> dict[str, Any]:
    """Compute baseline + last-month indicator for one DJU side (heating or cooling)."""
    timeseries: list[dict[str, Any]] = []
    for ym in sorted(dju_idx.keys()):
        if ym >= current_ym:
            continue
        dju_val = dju_idx[ym].get(dju_key, 0.0)
        if dju_val < dju_min:
            continue
        kwh = conso_idx.get(ym)
        if kwh is None or kwh <= 0:
            continue
        timeseries.append({
            "month": ym,
            "kwh": round(kwh, 1),
            "dju": round(dju_val, 1),
            "ratio_kwh_per_dju": round(kwh / dju_val, 4),
        })

    has_data = len(timeseries) > 0
    is_reliable = len(timeseries) >= _DJU_PERF_MIN_MONTHS

    baseline: float | None = None
    if is_reliable:
        baseline = round(sum(p["ratio_kwh_per_dju"] for p in timeseries) / len(timeseries), 4)

    last = timeseries[-1] if timeseries else None
    ecart: float | None = None
    status: str | None = None

    if last and baseline:
        e = (last["ratio_kwh_per_dju"] - baseline) / baseline
        ecart = round(e * 100, 1)
        if abs(e) <= _DJU_PERF_TOLERANCE:
            status = "dans_cible"
        elif e > _DJU_PERF_TOLERANCE:
            status = "depassement"
        else:
            status = "economie"

    return {
        "baseline_ratio_kwh_per_dju": baseline,
        "months_in_baseline": len(timeseries),
        "last_month": last,
        "last_month_ecart_percent": ecart,
        "last_month_status": status,
        "timeseries": timeseries,
        "has_data": has_data,
        "is_reliable": is_reliable,
    }


def get_prm_dju_performance(prm_id: str) -> dict[str, Any]:
    """
    kWh/DJU performance indicator split into heating (DJU_chauffage) and cooling (DJU_froid).
    Only past completed months are included; the current month is excluded.
    """
    dju_idx = _dju_monthly_index()
    conso_idx = _consumption_by_month().get(prm_id, {})
    current_ym = date.today().strftime("%Y-%m")

    return {
        "usage_point_id": prm_id,
        "heating": _build_dju_side(dju_idx, conso_idx, current_ym, "dju_chauffe", _DJU_HEATING_MIN),
        "cooling": _build_dju_side(dju_idx, conso_idx, current_ym, "dju_froid", _DJU_COOLING_MIN),
    }


# ---------------------------------------------------------------------------
# DJU saisonnier — graphique Hiver (Oct→Avr) et Été (Mai→Sep), multi-années
# ---------------------------------------------------------------------------

_WINTER_MONTHS = ["10", "11", "12", "01", "02", "03", "04"]
_WINTER_LABELS = ["Oct", "Nov", "Déc", "Jan", "Fév", "Mar", "Avr"]
_SUMMER_MONTHS = ["05", "06", "07", "08", "09"]
_SUMMER_LABELS = ["Mai", "Jun", "Jul", "Aoû", "Sep"]


def _linear_trend(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Régression linéaire y = slope*x + intercept."""
    n = len(xs)
    if n < 2:
        return 0.0, ys[0] if ys else 0.0
    sx, sy = sum(xs), sum(ys)
    sxy = sum(x * y for x, y in zip(xs, ys))
    sx2 = sum(x * x for x in xs)
    denom = n * sx2 - sx * sx
    if denom == 0:
        return 0.0, sy / n
    slope = (n * sxy - sx * sy) / denom
    return slope, (sy - slope * sx) / n


def _winter_label(year: int, month: int) -> str:
    if month >= 10:
        return f"{year}-{str(year + 1)[2:]}"
    return f"{year - 1}-{str(year)[2:]}"


def _summer_label(year: int) -> str:
    return str(year)


def get_prm_dju_seasonal(prm_id: str) -> dict[str, Any]:
    """
    Performance kWh/DJU par saison (Hiver Oct→Avr, Été Mai→Sep), multi-années.
    Cible par mois = moyenne historique avec correction de tendance linéaire.
    """
    dju_idx = _dju_monthly_index()
    conso_idx = _consumption_by_month().get(prm_id, {})
    current_ym = date.today().strftime("%Y-%m")
    today = date.today()

    current_winter_label = _winter_label(today.year, today.month)
    current_summer_label = _summer_label(today.year)

    winter_by_season: dict[str, dict[str, dict[str, float]]] = {}
    summer_by_season: dict[str, dict[str, dict[str, float]]] = {}

    for ym in sorted(dju_idx.keys()):
        if ym >= current_ym:
            continue
        y, m = int(ym[:4]), int(ym[5:7])
        mn = f"{m:02d}"
        kwh = conso_idx.get(ym)
        if kwh is None or kwh <= 0:
            continue
        dju_vals = dju_idx[ym]

        if mn in _WINTER_MONTHS:
            dju = dju_vals.get("dju_chauffe", 0.0)
            if dju > 0:
                lbl = _winter_label(y, m)
                winter_by_season.setdefault(lbl, {})[mn] = {"dju": round(dju, 1), "kwh": round(kwh, 1)}

        if mn in _SUMMER_MONTHS:
            dju = dju_vals.get("dju_froid", 0.0)
            if dju > 0:
                lbl = _summer_label(y)
                summer_by_season.setdefault(lbl, {})[mn] = {"dju": round(dju, 1), "kwh": round(kwh, 1)}

    def _build_season(
        by_season: dict[str, dict[str, dict[str, float]]],
        months_order: list[str],
        months_labels: list[str],
        current_label: str,
    ) -> dict[str, Any]:
        ratio_history: dict[str, list[tuple[float, float]]] = {mn: [] for mn in months_order}
        years_data: list[dict[str, Any]] = []

        for lbl in sorted(by_season.keys()):
            season_months = []
            for mn in months_order:
                d = by_season[lbl].get(mn)
                if d is None:
                    continue
                dju, kwh = d["dju"], d["kwh"]
                ratio = round(kwh / dju, 4)
                ratio_history[mn].append((float(lbl[:4]), ratio))
                season_months.append({"month_num": mn, "dju": dju, "kwh": kwh, "ratio": ratio})
            if season_months:
                years_data.append({"label": lbl, "months": season_months})

        # Cible par mois : moyenne historique avec tendance linéaire projetée sur la saison courante
        current_x = float(current_label[:4])
        cible_by_month: dict[str, float | None] = {}
        for mn in months_order:
            pts = ratio_history[mn]
            if not pts:
                cible_by_month[mn] = None
            elif len(pts) == 1:
                cible_by_month[mn] = round(pts[0][1], 4)
            else:
                slope, intercept = _linear_trend([p[0] for p in pts], [p[1] for p in pts])
                cible_by_month[mn] = round(max(slope * current_x + intercept, 0.0), 4)

        # Écart saison courante vs cible (pondéré par DJU)
        current_ecart: float | None = None
        current_data = by_season.get(current_label, {})
        if current_data:
            sum_kwh_actual = sum_kwh_cible = 0.0
            for mn, d in current_data.items():
                cible = cible_by_month.get(mn)
                if cible is not None and cible > 0:
                    sum_kwh_actual += d["kwh"]
                    sum_kwh_cible += cible * d["dju"]
            if sum_kwh_cible > 0:
                current_ecart = round((sum_kwh_actual / sum_kwh_cible - 1) * 100, 1)

        return {
            "months_order": months_order,
            "months_labels": months_labels,
            "years": years_data,
            "cible_by_month": cible_by_month,
            "current_label": current_label,
            "current_ecart_percent": current_ecart,
            "has_data": len(years_data) > 0,
        }

    return {
        "usage_point_id": prm_id,
        "winter": _build_season(winter_by_season, _WINTER_MONTHS, _WINTER_LABELS, current_winter_label),
        "summer": _build_season(summer_by_season, _SUMMER_MONTHS, _SUMMER_LABELS, current_summer_label),
    }
