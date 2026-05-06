from __future__ import annotations

from math import ceil
from typing import Any

from app.services.energie import _addresses, _contracts, _max_power_index, _safe_float
from app.services.turpe import estimate_power_change_annual_impact


SCENARIO_MARGINS = {
    "prudent": 1.20,
    "equilibre": 1.12,
    "agressif": 1.05,
}


def get_power_recommendations() -> dict[str, Any]:
    recommendations = [
        recommendation
        for recommendation in (get_prm_power_recommendation(prm_id) for prm_id in _contracts().keys())
        if recommendation is not None
    ]
    recommendations.sort(key=lambda item: item["priority_score"], reverse=True)

    return {
        "kpis": _build_kpis(recommendations),
        "recommendations": recommendations,
    }


def get_prm_power_recommendation(prm_id: str) -> dict[str, Any] | None:
    contract = _contracts().get(prm_id)
    if contract is None:
        return None

    subscribed_kva = _safe_float(contract.get("0_subscribed_power_value"))
    max_power_points = _max_power_index().get(prm_id, [])
    peak_kva = _peak_kva(max_power_points)
    data_quality = _data_quality(max_power_points, subscribed_kva, peak_kva)
    tariff = contract.get("0_distribution_tariff")
    current_ratio = round(peak_kva / subscribed_kva * 100, 1) if subscribed_kva and peak_kva is not None else None
    status = _status_from_ratio(current_ratio)
    scenarios = _build_scenarios(peak_kva, subscribed_kva, status)
    recommended = _select_recommended_scenario(scenarios, status, subscribed_kva)

    action = _action_from_recommendation(recommended, subscribed_kva, data_quality["status"])
    confidence = _confidence(data_quality, action, current_ratio)
    economic_estimate = _economic_estimate(
        tariff,
        contract.get("0_segment"),
        subscribed_kva,
        recommended.get("target_power_kva"),
    )
    priority_score = _priority_score(action, confidence, current_ratio, subscribed_kva, recommended.get("target_power_kva"))
    address = _addresses().get(prm_id) or {}

    return {
        "usage_point_id": prm_id,
        "name": contract.get("0_organization_commercial_name") or contract.get("0_organization_name") or prm_id,
        "address": _address_display(address),
        "contractor": contract.get("0_contractor"),
        "tariff": tariff,
        "segment": contract.get("0_segment"),
        "subscribed_power_kva": subscribed_kva,
        "peak_kva": peak_kva,
        "current_ratio_percent": current_ratio,
        "calibration_status": status,
        "recommended_power_kva": recommended.get("target_power_kva"),
        "recommended_scenario": recommended.get("key"),
        "action": action,
        "confidence": confidence,
        "data_quality": data_quality,
        "scenarios": scenarios,
        "economic_estimate": economic_estimate,
        "justification": _justification(action, confidence, data_quality, subscribed_kva, peak_kva, recommended),
        "priority_score": priority_score,
    }


def _peak_kva(points: list[dict[str, Any]]) -> float | None:
    if not points:
        return None
    return round(max(point["value_va"] for point in points) / 1000, 2)


def _data_quality(points: list[dict[str, Any]], subscribed_kva: float | None, peak_kva: float | None) -> dict[str, Any]:
    dates = sorted({point["date"][:10] for point in points if point.get("date")})
    months = sorted({date[:7] for date in dates})
    years = sorted({date[:4] for date in dates})
    missing: list[str] = []

    if subscribed_kva is None or subscribed_kva <= 0:
        missing.append("puissance souscrite")
    if peak_kva is None:
        missing.append("historique puissance maximale")

    if missing:
        status = "insufficient"
    elif len(months) >= 10 and len(dates) >= 240:
        status = "strong"
    elif len(months) >= 3 and len(dates) >= 60:
        status = "medium"
    else:
        status = "weak"

    return {
        "status": status,
        "max_power_days": len(dates),
        "max_power_months": len(months),
        "max_power_years": len(years),
        "first_max_power_date": dates[0] if dates else None,
        "last_max_power_date": dates[-1] if dates else None,
        "missing": missing,
    }


def _build_scenarios(
    peak_kva: float | None,
    subscribed_kva: float | None,
    status: str,
) -> list[dict[str, Any]]:
    if peak_kva is None or subscribed_kva is None or subscribed_kva <= 0:
        return []
    if peak_kva <= 0:
        return []

    scenarios = []
    for key, margin in SCENARIO_MARGINS.items():
        target = _round_power(peak_kva * margin)
        # Avoid proposing cosmetic changes. A 1 kVA delta is the practical step
        # used for non-public-lighting sites in the contract analysis.
        if abs(target - subscribed_kva) < 1:
            target = subscribed_kva
        delta = round(target - subscribed_kva, 1)
        ratio_after = round(peak_kva / target * 100, 1) if target > 0 else None
        scenarios.append(
            {
                "key": key,
                "label": {"prudent": "Prudent", "equilibre": "Equilibre", "agressif": "Agressif"}[key],
                "target_power_kva": target,
                "delta_kva": delta,
                "margin_percent": round((target - peak_kva) / target * 100, 1) if target > 0 else None,
                "risk": _risk_from_ratio_after(ratio_after),
                "ratio_after_percent": ratio_after,
                "is_recommended": False,
            }
        )

    recommended_key = "prudent" if status in {"sous_dimensionne", "sur_souscrit"} else None
    for scenario in scenarios:
        scenario["is_recommended"] = scenario["key"] == recommended_key
    return scenarios


def _select_recommended_scenario(
    scenarios: list[dict[str, Any]],
    status: str,
    subscribed_kva: float | None,
) -> dict[str, Any]:
    if subscribed_kva is None:
        return {}
    if status in {"bien_calibre", "proche_seuil"}:
        return {
            "key": "maintien",
            "target_power_kva": subscribed_kva,
            "delta_kva": 0,
            "is_recommended": True,
        }
    for scenario in scenarios:
        if scenario["is_recommended"]:
            return scenario
    return {}


def _status_from_ratio(ratio: float | None) -> str:
    if ratio is None:
        return "donnees_insuffisantes"
    if ratio > 95:
        return "sous_dimensionne"
    if ratio > 80:
        return "proche_seuil"
    if ratio >= 40:
        return "bien_calibre"
    return "sur_souscrit"


def _action_from_recommendation(recommended: dict[str, Any], subscribed_kva: float | None, data_status: str) -> str:
    if data_status == "insufficient" or subscribed_kva is None or not recommended:
        return "insufficient_data"
    target = recommended.get("target_power_kva")
    if target is None:
        return "insufficient_data"
    if target > subscribed_kva:
        return "increase"
    if target < subscribed_kva:
        return "decrease"
    return "maintain"


def _confidence(data_quality: dict[str, Any], action: str, ratio: float | None) -> str:
    if action == "insufficient_data" or data_quality["status"] == "insufficient":
        return "insufficient"
    if data_quality["status"] == "strong":
        return "high"
    if data_quality["status"] == "medium":
        return "medium"
    if action == "decrease" and ratio is not None and ratio < 20:
        return "low"
    return "low"


def _economic_estimate(
    tariff: str | None,
    segment: str | None,
    subscribed_kva: float | None,
    target_kva: float | None,
) -> dict[str, Any]:
    return estimate_power_change_annual_impact(tariff, segment, subscribed_kva, target_kva)


def _priority_score(
    action: str,
    confidence: str,
    ratio: float | None,
    subscribed_kva: float | None,
    recommended_kva: float | None,
) -> float:
    if action == "insufficient_data":
        return 0
    score = {"increase": 80, "decrease": 65, "maintain": 20}.get(action, 0)
    score += {"high": 20, "medium": 10, "low": 2, "insufficient": 0}.get(confidence, 0)
    if action == "increase" and ratio is not None:
        score += max(0, ratio - 95)
    if action == "decrease" and subscribed_kva and recommended_kva:
        score += min(20, max(0, subscribed_kva - recommended_kva))
    return round(score, 1)


def _justification(
    action: str,
    confidence: str,
    data_quality: dict[str, Any],
    subscribed_kva: float | None,
    peak_kva: float | None,
    recommended: dict[str, Any],
) -> str:
    if action == "insufficient_data":
        missing = ", ".join(data_quality["missing"]) or "historique insuffisant"
        return f"Preconisation impossible : {missing}."
    if action == "maintain":
        return "Maintien recommande : le pic observe reste dans une zone de marge acceptable."

    target = recommended.get("target_power_kva")
    if action == "increase":
        return (
            f"Hausse prudente proposee : pic observe {peak_kva} kVA pour {subscribed_kva} kVA souscrits, "
            f"cible {target} kVA avec niveau de confiance {confidence}."
        )
    return (
        f"Baisse possible a confirmer : pic observe {peak_kva} kVA pour {subscribed_kva} kVA souscrits, "
        f"cible prudente {target} kVA avec niveau de confiance {confidence}."
    )


def _risk_from_ratio_after(ratio_after: float | None) -> str:
    if ratio_after is None:
        return "unknown"
    if ratio_after > 95:
        return "high"
    if ratio_after > 85:
        return "medium"
    return "low"


def _round_power(value: float) -> float:
    if value <= 0:
        return 0
    return float(max(3, ceil(value)))


def _address_display(addr: dict[str, str]) -> str:
    parts = [
        addr.get("address_number_street_name", ""),
        addr.get("address_postal_code_city", ""),
    ]
    return ", ".join(part for part in parts if part)


def _build_kpis(recommendations: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total": len(recommendations),
        "increase": sum(1 for item in recommendations if item["action"] == "increase"),
        "decrease": sum(1 for item in recommendations if item["action"] == "decrease"),
        "maintain": sum(1 for item in recommendations if item["action"] == "maintain"),
        "insufficient_data": sum(1 for item in recommendations if item["action"] == "insufficient_data"),
        "high_confidence": sum(1 for item in recommendations if item["confidence"] == "high"),
        "medium_confidence": sum(1 for item in recommendations if item["confidence"] == "medium"),
    }
