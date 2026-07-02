"""Budget RÉVISÉ gaz TotalEnergies — reconstitution FIXE / VARIABLE par PCE.

1er incrément du budget révisé fiable (cf. ``docs/refonte-v1/budget-revise-gaz-decisions.md``).
Contrairement au coefficient global CPE (``accounting_contract_budget``, bon pour un forfait pur
mais faux dès qu'il y a de la conso), ce moteur reconstitue chaque PCE en :

    budget_révisé = Σ parts FIXES + conso attendue × prix de référence
    atterrissage  = réalisé à date + reste projeté (mêmes prix)

- **FIXE** (abo fournisseur, ATRD/ATRT fixe, CTA) : tenu à plat en v1 (termes ~constants).
- **VARIABLE** : ``conso attendue × prix unitaire`` ; la fourniture est **révisée par le PEG**
  (``GasSupplyRevisablePrice``, ratio moyenne Y / moyenne N-1), les autres termes /kWh (accise TICGN,
  ATRD variable, indexation) sont tenus au dernier observé.
- **Conso attendue** : historique N-1 corrigé du climat via DJU (``energie.get_dju_monthly``, profil
  Sète), formule reprise de ``cpe_atterrissage`` (``conso × DJU_projeté / DJU_écoulé``).

Calcul à la volée, aucune persistance, aucune migration. Aucun prix ni contrôle recodé : on **branche**.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.gas_invoice import GasInvoice
from app.services import energie
from app.services.gas_invoice import load_revisable_prices

# Composantes fixes / variables du HT gaz (colonnes GasInvoice).
_FIXE_FIELDS = ("abonnement_fournisseur", "atrt_terme_fixe", "atrd_terme_fixe", "montant_cta")
_VAR_OTHER_FIELDS = ("atrd_terme_variable", "montant_ticgn", "montant_indexation")


def _num(value: float | int | None) -> float:
    return float(value) if value is not None else 0.0


def _invoice_year(inv: GasInvoice) -> int | None:
    """Année de consommation d'une facture (fin > début > date comptable)."""
    for d in (inv.fin_conso, inv.debut_conso, inv.date_comptable):
        if d is not None:
            return d.year
    return None


def _elapsed_months(year: int, today: date) -> int:
    if today.year > year:
        return 12
    if today.year < year:
        return 0
    return today.month


# --------------------------------------------------------------------------- DJU

def _dju_by_year_month() -> dict[tuple[int, int], float]:
    """{(année, mois): DJU chauffage} depuis le profil Sète (base 18)."""
    out: dict[tuple[int, int], float] = {}
    for row in energie.get_dju_monthly():
        ym = str(row.get("month", ""))
        if len(ym) < 7:
            continue
        try:
            y, m = int(ym[:4]), int(ym[5:7])
        except ValueError:
            continue
        out[(y, m)] = _num(row.get("dju_chauffe"))
    return out


def _normal_dju_by_month(dju: dict[tuple[int, int], float], exclude_year: int) -> dict[int, float]:
    """Profil DJU « normal » par mois calendaire = moyenne historique (années ≠ exclude_year)."""
    sums: dict[int, float] = {}
    counts: dict[int, int] = {}
    for (y, m), value in dju.items():
        if y == exclude_year:
            continue
        sums[m] = sums.get(m, 0.0) + value
        counts[m] = counts.get(m, 0) + 1
    return {m: sums[m] / counts[m] for m in sums if counts[m] > 0}


# --------------------------------------------------------------------------- prix

def _peg_ratio(peg: dict[tuple[int, int], float], year: int) -> tuple[float, bool]:
    """Ratio PEG moyen année Y / moyenne N-1 (1,0 si indisponible)."""
    cur = [v for (y, _m), v in peg.items() if y == year and v]
    prev = [v for (y, _m), v in peg.items() if y == year - 1 and v]
    if cur and prev:
        avg_prev = sum(prev) / len(prev)
        if avg_prev > 0:
            return (sum(cur) / len(cur)) / avg_prev, True
    return 1.0, False


# --------------------------------------------------------------------------- PCE

def _reference_from_invoices(invoices: list[GasInvoice]) -> dict[str, float]:
    """Agrège les composantes d'un lot de factures (prix unitaires + parts fixes)."""
    kwh = sum(_num(inv.total_conso_kwh) for inv in invoices)
    fourniture = sum(_num(inv.montant_conso_gaz) for inv in invoices)
    autres_var = sum(_num(getattr(inv, f)) for inv in invoices for f in _VAR_OTHER_FIELDS)
    fixe = sum(_num(getattr(inv, f)) for inv in invoices for f in _FIXE_FIELDS)
    return {
        "kwh": kwh,
        "fixe": round(fixe, 2),
        "pu_fourniture": (fourniture / kwh) if kwh > 0 else 0.0,
        "pu_autres_var": (autres_var / kwh) if kwh > 0 else 0.0,
    }


def _expected_consumption(
    kwh_n1: float,
    dju: dict[tuple[int, int], float],
    normal: dict[int, float],
    year: int,
) -> tuple[float, float]:
    """Conso attendue = kwh_N-1 × (DJU_normal_annuel / DJU_N-1_annuel). Retourne (conso, ratio_climat)."""
    dju_n1 = sum(v for (y, _m), v in dju.items() if y == year - 1)
    dju_normal = sum(normal.values())
    if dju_n1 > 0 and dju_normal > 0:
        ratio = dju_normal / dju_n1
        return kwh_n1 * ratio, ratio
    return kwh_n1, 1.0


def _landing(
    realise: float,
    kwh_realise: float,
    fixe_ref: float,
    pu_variable: float,
    dju: dict[tuple[int, int], float],
    normal: dict[int, float],
    year: int,
    today: date,
    budget_revise: float,
) -> tuple[float, str]:
    """Atterrissage = réalisé + reste projeté (conso via DJU, mêmes prix de référence)."""
    if kwh_realise <= 0:
        return round(budget_revise, 2), "budget_revise"

    elapsed = _elapsed_months(year, today)
    if elapsed >= 12:
        return round(realise, 2), "realise_complet"
    months_left = 12 - elapsed

    dju_ecoule = sum(dju.get((year, m), 0.0) for m in range(1, elapsed + 1))
    dju_restant = sum(normal.get(m, 0.0) for m in range(elapsed + 1, 13))

    if dju_ecoule > 0 and dju_restant >= 0 and (dju_ecoule + dju_restant) > 0:
        conso_projetee = kwh_realise * (dju_ecoule + dju_restant) / dju_ecoule
        method = "dju"
    elif elapsed > 0:
        conso_projetee = kwh_realise * 12.0 / elapsed  # fallback pro-rata temporel
        method = "prorata"
    else:
        return round(budget_revise, 2), "budget_revise"

    conso_reste = max(conso_projetee - kwh_realise, 0.0)
    variable_reste = conso_reste * pu_variable
    fixe_reste = (fixe_ref / 12.0) * months_left
    return round(realise + variable_reste + fixe_reste, 2), method


def _build_point(
    pce: str,
    inv_n1: list[GasInvoice],
    inv_y: list[GasInvoice],
    peg_ratio: float,
    dju: dict[tuple[int, int], float],
    normal: dict[int, float],
    year: int,
    today: date,
) -> dict[str, Any]:
    ref = _reference_from_invoices(inv_n1)
    label_src = inv_y or inv_n1
    nom_site = next((i.nom_site for i in label_src if i.nom_site), None)
    building_id = next((i.building_id for i in label_src if i.building_id is not None), None)

    conso_attendue, climate_ratio = _expected_consumption(ref["kwh"], dju, normal, year)
    pu_variable = ref["pu_fourniture"] * peg_ratio + ref["pu_autres_var"]
    variable_budget = conso_attendue * pu_variable
    fixe_budget = ref["fixe"]
    budget_revise = variable_budget + fixe_budget

    realise = round(sum(_num(inv.total_hors_tva) for inv in inv_y), 2)
    kwh_realise = sum(_num(inv.total_conso_kwh) for inv in inv_y)
    atterrissage, method = _landing(
        realise, kwh_realise, fixe_budget, pu_variable, dju, normal, year, today, budget_revise
    )

    has_history = ref["kwh"] > 0
    return {
        "pce": pce,
        "nom_site": nom_site,
        "building_id": building_id,
        "kwh_n1": round(ref["kwh"], 0),
        "conso_attendue_kwh": round(conso_attendue, 0),
        "climate_ratio": round(climate_ratio, 4),
        "peg_ratio": round(peg_ratio, 4),
        "pu_variable_eur_kwh": round(pu_variable, 6),
        "fixe_budget": round(fixe_budget, 2),
        "variable_budget": round(variable_budget, 2),
        "budget_revise": round(budget_revise, 2),
        "realise": realise,
        "kwh_realise": round(kwh_realise, 0),
        "atterrissage": atterrissage,
        "ecart_atterrissage_vs_budget": round(atterrissage - budget_revise, 2),
        "landing_method": method,
        "has_history": has_history,
    }


def build_gas_budget_revise(
    db: Session,
    city_id: int | None = None,
    *,
    year: int,
    today: date | None = None,
) -> dict[str, Any]:
    """Budget révisé gaz par PCE (fixe/variable), réalisé et atterrissage pour l'année ``year``."""
    resolved_today = today or date.today()

    invoices = list(
        db.execute(select(GasInvoice).where(GasInvoice.city_id == city_id)).scalars()
    )
    by_pce_n1: dict[str, list[GasInvoice]] = {}
    by_pce_y: dict[str, list[GasInvoice]] = {}
    for inv in invoices:
        y = _invoice_year(inv)
        if y == year - 1:
            by_pce_n1.setdefault(inv.pce, []).append(inv)
        elif y == year:
            by_pce_y.setdefault(inv.pce, []).append(inv)

    peg = load_revisable_prices(db, city_id)
    peg_ratio, peg_available = _peg_ratio(peg, year)
    dju = _dju_by_year_month()
    normal = _normal_dju_by_month(dju, exclude_year=year)

    points: list[dict[str, Any]] = []
    for pce in sorted(set(by_pce_n1) | set(by_pce_y)):
        points.append(
            _build_point(
                pce, by_pce_n1.get(pce, []), by_pce_y.get(pce, []),
                peg_ratio, dju, normal, year, resolved_today,
            )
        )
    points.sort(key=lambda p: p["budget_revise"], reverse=True)

    totals = {
        "fixe_budget": round(sum(p["fixe_budget"] for p in points), 2),
        "variable_budget": round(sum(p["variable_budget"] for p in points), 2),
        "budget_revise": round(sum(p["budget_revise"] for p in points), 2),
        "realise": round(sum(p["realise"] for p in points), 2),
        "atterrissage": round(sum(p["atterrissage"] for p in points), 2),
    }
    totals["ecart_atterrissage_vs_budget"] = round(totals["atterrissage"] - totals["budget_revise"], 2)

    return {
        "year": year,
        "generated_on": resolved_today.isoformat(),
        "pce_count": len(points),
        "peg_available": peg_available,
        "dju_available": bool(dju),
        "totals": totals,
        "points": points,
        "source_note": (
            "Budget révisé = parts fixes N-1 (abo, ATRD/ATRT fixe, CTA, tenues à plat) + conso attendue "
            "× prix de référence. Conso attendue = kWh N-1 corrigés du climat (DJU normal / DJU N-1, profil "
            "Sète). Fourniture révisée par le PEG (moyenne Y / N-1) ; accise, ATRD variable et indexation "
            "tenues au dernier /kWh observé. Atterrissage = réalisé Y + reste projeté DJU aux mêmes prix. "
            "Modèle pur-DJU (part ECS non thermosensible non isolée) — v1."
        ),
    }
