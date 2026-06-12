"""Coûts de puissance réellement facturés, agrégés par PRM.

Sert au couplage théorique/réel de la page /energie/preconisations :
le moteur de préconisations (services/power_recommendations.py) chiffre un impact
*théorique* sur la seule part fixe TURPE, à partir des données ENEDIS. Ici on lit
les factures réellement importées (modèle normalisé EnergyInvoice*) pour exposer,
par PRM et sur les 12 derniers mois :
  - les pénalités de dépassement de puissance réellement payées ;
  - le coût réel de la part fixe acheminement (variable avec la puissance souscrite).

Les lignes exploitées sont produites par invoice_parsers/engie_xlsx._build_power_lines
(`network_overrun`, `network_overrun_quadratic`, `network_fixed_total`). Une
réimportation des factures est nécessaire pour que ces lignes existent en base.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.invoice import (
    EnergyInvoice,
    EnergyInvoiceLine,
    EnergyInvoicePeriod,
    EnergyInvoiceSite,
)

PENALTY_CODES = {"network_overrun", "network_overrun_quadratic"}
FIXED_ROUTING_CODES = {"network_fixed_total"}
_RELEVANT_CODES = PENALTY_CODES | FIXED_ROUTING_CODES


def get_real_power_costs_by_prm(
    db: Session,
    city_id: int,
    reference_date: date | None = None,
    months: int = 12,
) -> dict[str, dict[str, Any]]:
    """Agrège par PRM les coûts de puissance réels sur une fenêtre glissante.

    La fenêtre se termine à la dernière période facturée connue de la ville
    (ou `reference_date`) et remonte de `months` mois.
    """
    rows = db.execute(
        select(
            EnergyInvoiceSite.prm_id,
            EnergyInvoiceLine.normalized_code,
            EnergyInvoiceLine.amount_ht,
            EnergyInvoicePeriod.period_start,
            EnergyInvoicePeriod.period_end,
            EnergyInvoicePeriod.subscribed_power_kva,
            EnergyInvoicePeriod.max_reached_power_kva,
            EnergyInvoice.invoice_number,
        )
        .select_from(EnergyInvoiceLine)
        .join(EnergyInvoicePeriod, EnergyInvoiceLine.invoice_period_id == EnergyInvoicePeriod.id)
        .join(EnergyInvoiceSite, EnergyInvoicePeriod.invoice_site_id == EnergyInvoiceSite.id)
        .join(EnergyInvoice, EnergyInvoiceSite.invoice_id == EnergyInvoice.id)
        .where(
            EnergyInvoice.city_id == city_id,
            EnergyInvoiceSite.prm_id.isnot(None),
            EnergyInvoiceLine.normalized_code.in_(_RELEVANT_CODES),
        )
    ).all()

    if not rows:
        return {}

    end = reference_date or max((r.period_end for r in rows if r.period_end), default=None)
    if end is None:
        return {}
    window_start = end - timedelta(days=round(months * 30.4) - 1)

    acc: dict[str, dict[str, Any]] = {}
    for r in rows:
        if r.period_end is None or r.period_end < window_start or r.period_end > end:
            continue
        prm = (r.prm_id or "").strip()
        if not prm:
            continue
        amount = float(r.amount_ht) if r.amount_ht is not None else 0.0
        bucket = acc.setdefault(
            prm,
            {
                "penalties_eur": 0.0,
                "penalty_periods": 0,
                "fixed_routing_eur": 0.0,
                "invoice_numbers": set(),
                "period_start": r.period_end,
                "period_end": r.period_end,
                "max_reached_power_kva": None,
                "subscribed_power_kva": None,
                "_last_period_end": None,
            },
        )
        if r.normalized_code in PENALTY_CODES:
            bucket["penalties_eur"] += amount
            if amount > 0:
                bucket["penalty_periods"] += 1
        elif r.normalized_code in FIXED_ROUTING_CODES:
            bucket["fixed_routing_eur"] += amount

        if r.invoice_number:
            bucket["invoice_numbers"].add(r.invoice_number)
        if r.period_start and r.period_start < bucket["period_start"]:
            bucket["period_start"] = r.period_start
        if r.period_end > bucket["period_end"]:
            bucket["period_end"] = r.period_end
        if r.max_reached_power_kva is not None:
            current = bucket["max_reached_power_kva"]
            bucket["max_reached_power_kva"] = (
                r.max_reached_power_kva if current is None else max(current, r.max_reached_power_kva)
            )
        # Puissance souscrite = celle de la période la plus récente.
        if r.subscribed_power_kva is not None and (
            bucket["_last_period_end"] is None or r.period_end >= bucket["_last_period_end"]
        ):
            bucket["subscribed_power_kva"] = r.subscribed_power_kva
            bucket["_last_period_end"] = r.period_end

    result: dict[str, dict[str, Any]] = {}
    for prm, b in acc.items():
        has_fixed = abs(b["fixed_routing_eur"]) > 0.0001
        result[prm] = {
            "available": True,
            "penalties_eur": round(b["penalties_eur"], 2),
            "penalty_periods": b["penalty_periods"],
            "fixed_routing_eur": round(b["fixed_routing_eur"], 2) if has_fixed else None,
            "invoices_count": len(b["invoice_numbers"]),
            "period_start": b["period_start"].isoformat() if b["period_start"] else None,
            "period_end": b["period_end"].isoformat() if b["period_end"] else None,
            "max_reached_power_kva": b["max_reached_power_kva"],
            "subscribed_power_kva": b["subscribed_power_kva"],
        }
    return result


def _unavailable(reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "penalties_eur": 0.0,
        "penalty_periods": 0,
        "fixed_routing_eur": None,
        "invoices_count": 0,
        "period_start": None,
        "period_end": None,
        "max_reached_power_kva": None,
        "subscribed_power_kva": None,
        "reason": reason,
    }


def attach_real_costs(
    recommendations: list[dict[str, Any]],
    costs_by_prm: dict[str, dict[str, Any]],
) -> None:
    """Greffe le bloc `real_costs` sur chaque préconisation (in place)."""
    for item in recommendations:
        prm = item.get("usage_point_id")
        real = costs_by_prm.get(prm) if prm else None
        if real is None:
            item["real_costs"] = _unavailable(
                "Aucune facture importée avec ces postes pour ce PRM (réimport requis)."
            )
        else:
            item["real_costs"] = {**real, "reason": "Données issues des factures importées."}
