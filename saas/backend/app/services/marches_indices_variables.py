from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.services import cpe_accounting, gas_invoice
from app.services.turpe import list_turpe_evolution_events


INDEX_LABELS: dict[str, str] = {
    "ICHT_IME": "ICHT-IME",
    "FSD2": "FSD2",
    "BT40": "BT40",
}


def build_indices_variables(
    db: Session,
    city_id: int | None,
    year_from: int,
    year_to: int,
) -> dict[str, Any]:
    if year_from > year_to:
        year_from, year_to = year_to, year_from

    series: list[dict[str, Any]] = []
    series.extend(_cpe_index_series(db, city_id, year_from, year_to))
    series.extend(_cpe_observed_factor_series(db, city_id, year_from, year_to))
    series.append(_gas_peg_series(db, city_id, year_from, year_to))
    series.extend(_turpe_series(year_from, year_to))

    return {
        "year_from": year_from,
        "year_to": year_to,
        "series": [item for item in series if item["points"]],
    }


def _period_quarter(year: int, quarter: int) -> str:
    return f"{year}-T{quarter}"


def _period_month(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


def _source(value: Any) -> str | None:
    source = getattr(value, "source", None)
    return str(source) if source else None


def _cpe_index_series(db: Session, city_id: int | None, year_from: int, year_to: int) -> list[dict[str, Any]]:
    points_by_code: dict[str, list[dict[str, Any]]] = {code: [] for code in INDEX_LABELS}

    for year in range(year_from, year_to + 1):
        for item in cpe_accounting.list_revision_indices(db, city_id, year=year):
            if item.index_code not in points_by_code or item.quarter <= 0:
                continue
            points_by_code[item.index_code].append(
                {
                    "period": _period_quarter(item.year, item.quarter),
                    "value": float(item.value),
                    "label": INDEX_LABELS[item.index_code],
                    "source": _source(item),
                }
            )

    return [
        {
            "code": code,
            "label": label,
            "unit": "indice",
            "market": "DALKIA",
            "family": "dalkia",
            "periodicity": "trimestre",
            "points": sorted(points, key=lambda point: point["period"]),
        }
        for code, label in INDEX_LABELS.items()
        for points in [points_by_code[code]]
    ]


def _cpe_observed_factor_series(db: Session, city_id: int | None, year_from: int, year_to: int) -> list[dict[str, Any]]:
    grouped: dict[str, dict[tuple[int, int], dict[str, Any]]] = {"P2": {}, "P3": {}}
    for observation in cpe_accounting.list_revision_observations(db, city_id):
        year = int(observation["year"])
        if year < year_from or year > year_to:
            continue
        market = str(observation["market"])
        if market not in grouped:
            continue
        quarter = int(observation["quarter"])
        line_count = max(int(observation.get("line_count") or 1), 1)
        bucket = grouped[market].setdefault(
            (year, quarter),
            {"weighted_sum": 0.0, "line_count": 0, "invoice_numbers": set()},
        )
        bucket["weighted_sum"] += float(observation["observed_factor"]) * line_count
        bucket["line_count"] += line_count
        bucket["invoice_numbers"].update(observation.get("invoice_numbers") or [])

    points_by_market: dict[str, list[dict[str, Any]]] = {"P2": [], "P3": []}
    for market, periods in grouped.items():
        for (year, quarter), bucket in periods.items():
            line_count = int(bucket["line_count"])
            invoices = sorted(bucket["invoice_numbers"])
            shown_invoices = invoices[:5]
            extra_count = max(len(invoices) - len(shown_invoices), 0)
            source = ", ".join(shown_invoices)
            if extra_count:
                source = f"{source} (+{extra_count})" if source else f"{extra_count} factures"
            points_by_market[market].append(
                {
                    "period": _period_quarter(year, quarter),
                    "value": round(float(bucket["weighted_sum"]) / line_count, 6),
                    "label": f"{line_count} ligne(s) facture",
                    "source": source or None,
                }
            )

    return [
        {
            "code": f"DALKIA_COEF_OBSERVE_{market}",
            "label": f"Coefficient observe {market}",
            "unit": "coefficient",
            "market": market,
            "family": "dalkia",
            "periodicity": "trimestre",
            "points": sorted(points, key=lambda point: point["period"]),
        }
        for market, points in points_by_market.items()
    ]


def _gas_peg_series(db: Session, city_id: int | None, year_from: int, year_to: int) -> dict[str, Any]:
    points = [
        {
            "period": _period_month(item.annee, item.mois),
            "value": float(item.fourniture_eur_mwh),
            "label": "PEG gaz",
            "source": _source(item),
        }
        for item in gas_invoice.list_revisable(db, city_id)
        if item.fourniture_eur_mwh is not None and year_from <= item.annee <= year_to
    ]
    return {
        "code": "PEG_GAZ",
        "label": "PEG gaz fourniture",
        "unit": "EUR/MWh",
        "market": "Gaz TotalEnergies",
        "family": "gaz",
        "periodicity": "mois",
        "points": sorted(points, key=lambda point: point["period"]),
    }


def _turpe_series(year_from: int, year_to: int) -> list[dict[str, Any]]:
    evolution_points: list[dict[str, Any]] = []
    cumulative_points: list[dict[str, Any]] = []
    start = date(year_from, 1, 1)
    end = date(year_to, 12, 31)
    for event in list_turpe_evolution_events():
        effective_date = event["effective_date"]
        if effective_date < start or effective_date > end:
            continue
        common = {
            "period": effective_date.isoformat(),
            "label": event.get("event_label"),
            "source": event.get("source_label"),
        }
        evolution_points.append({**common, "value": float(event["evolution_percent"])})
        cumulative_points.append({**common, "value": float(event["cumulative_index"])})

    return [
        {
            "code": "TURPE_EVOLUTION_HTA_BT",
            "label": "Evolution TURPE HTA-BT",
            "unit": "%",
            "market": "Electricite",
            "family": "elec",
            "periodicity": "date",
            "points": sorted(evolution_points, key=lambda point: point["period"]),
        },
        {
            "code": "TURPE_INDEX_CUMULE_HTA_BT",
            "label": "Indice cumule TURPE HTA-BT",
            "unit": "indice",
            "market": "Electricite",
            "family": "elec",
            "periodicity": "date",
            "points": sorted(cumulative_points, key=lambda point: point["period"]),
        },
    ]
