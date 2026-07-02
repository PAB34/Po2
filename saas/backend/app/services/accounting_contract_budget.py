"""Budget CONTRACTUEL vs réalisé vs atterrissage par poste (CPE DALKIA).

Stratégie atterrissage §5bis (``docs/refonte-v1/atterrissage-strategie-front.md``) :
le budget de référence n'est **pas** une saisie prévisionnelle Ville mais le montant
**contractuel** (pièces qui nous lient au tiers). Pour DALKIA, ces montants sont déjà
agrégés par ``cpe_market_tracking`` (prévu DPGF = budget contractuel, reçu = réalisé
factures). Ce service les met en forme « budget − réalisé = atterrissage vs contrat »
par poste (P1 / P1-ELEC / P2 / P2.4 / P3 / P3.4) et propose une **projection optionnelle**
sur l'axe ``operation_number`` de la matrice comptable (vue hybride demandée), déduite
des règles matrice (``scope`` p1/p2/p3).

Décisions (``docs/refonte-v1/cibles-contractuelles-budget-matrice-audit.md``) :
- réalisé = **reçu factures CPE par poste** (market_tracking), pas les snapshots matrice ;
- **calcul à la volée** (aucune persistance, aucune migration) ;
- atterrissage v1 : les postes DALKIA sont des montants annuels **contractuels fixes**
  (acompte P1, forfait P2, provision P3, forfait APE P3.4) → l'atterrissage du budget est
  le montant contractuel lui-même (on projette d'être facturé le plein annuel) ; l'écart
  réalisé − budget donne le rythme de facturation. Quand le budget contractuel est inconnu
  (prévu = 0), on retombe sur un **pro-rata temporel** du réalisé.
  ⚠️ À ne pas confondre avec l'atterrissage d'**intéressement** (``cpe_atterrissage``, DJU)
  qui projette une pénalité/bonus de consommation, pas le budget contractuel.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.accounting_matrix import (
    AccountingMatrixContract,
    AccountingMatrixRule,
    AccountingMatrixVersion,
)
from app.models.cpe import CpeFinanceInvoice, CpeFinanceLine
from app.services.cpe_accounting import get_current_cpe_contract_codes
from app.services.cpe_market_tracking import build_market_tracking

# Correspondance poste CPE → scope de règle matrice (pour la projection sur operation_number).
POSTE_SCOPE: dict[str, str] = {
    "P1": "p1",
    "P1-ELEC": "p1",
    "P2": "p2",
    "P2-4": "p2",
    "P3": "p3",
    "P3-4": "p3",
}

# Postes révisables par coefficient sur forfait → marché portant le coefficient (revised/base annuel).
# Limité à P2/P3 : leurs prix_de_base/prix_révisé sont les forfaits annuels (P20/P30), le ratio a un sens.
# P1 gaz EXCLU : sa "révision" est le prix unitaire du gaz (OS3/PEG) sur des lignes de consommation ;
# un ratio Σrévisé/Σbase de prix unitaires n'a pas de sens (mécanisme propre à ajouter séparément).
# P1-ELEC exclu : pas de révision par indices (Lot 2 piscines).
REVISABLE_POSTE_MARKET: dict[str, str] = {
    "P2": "P2",
    "P2-4": "P2",
    "P3": "P3",
    "P3-4": "P3",
}


def _current_quarter(year: int, today: date) -> int:
    """Nombre de trimestres écoulés (1..4) pour l'année, 0 si année future."""
    if today.year > year:
        return 4
    if today.year < year:
        return 0
    return (today.month - 1) // 3 + 1


def _line_quarter(line: CpeFinanceLine) -> tuple[int | None, int | None]:
    period_date = line.period_end or line.period_start
    if period_date is None:
        return None, None
    return period_date.year, (period_date.month - 1) // 3 + 1


def _revision_coef_by_market(
    db: Session,
    city_id: int | None,
    year: int,
    today: date,
    contract_codes: list[str],
) -> dict[str, dict[str, Any]]:
    """Coefficient de révision observé par marché (P2/P3 seulement), Option C (dernier trimestre connu).

    Coefficient = Σ prix_révisé / Σ prix_base sur les lignes de factures du **dernier trimestre écoulé
    avec données**, par marché (P2/P3, où base/révisé sont les forfaits annuels). C'est l'extrapolation
    « dernier coefficient connu », ensuite appliquée au budget base. Retourne, par marché, le coefficient
    et le détail du calcul (trimestre, sommes, nb de lignes) pour l'afficher. {} si aucune facture révisée.
    """
    scope = get_current_cpe_contract_codes(db, city_id, year=year)
    codes = ({c.strip().upper() for c in contract_codes if c} & scope) if contract_codes else scope
    if not codes:
        return {}
    current_quarter = _current_quarter(year, today)
    if current_quarter <= 0:
        return {}

    # Le code contrat est porté par la facture (les lignes ne le renseignent pas toujours).
    stmt = (
        select(CpeFinanceLine)
        .join(CpeFinanceInvoice, CpeFinanceLine.invoice_id == CpeFinanceInvoice.id)
        .where(
            CpeFinanceInvoice.contract_code.in_(codes),
            CpeFinanceLine.market.in_(("P2", "P3")),
            CpeFinanceLine.base_price.is_not(None),
            CpeFinanceLine.revised_price.is_not(None),
        )
    )
    if city_id is not None:
        stmt = stmt.where(CpeFinanceLine.city_id == city_id)

    # {market: {quarter: [Σbase, Σrevised, count]}}
    agg: dict[str, dict[int, list[float]]] = {}
    for line in db.scalars(stmt).all():
        line_year, quarter = _line_quarter(line)
        if line_year != year or quarter is None or quarter > current_quarter:
            continue
        base = line.base_price or 0.0
        revised = line.revised_price or 0.0
        if base <= 0:
            continue
        market = (line.market or "").strip().upper()
        bucket = agg.setdefault(market, {}).setdefault(quarter, [0.0, 0.0, 0.0])
        bucket[0] += base
        bucket[1] += revised
        bucket[2] += 1

    coef_by_market: dict[str, dict[str, Any]] = {}
    for market, by_quarter in agg.items():
        latest = max(by_quarter)  # dernier trimestre écoulé avec données
        total_base, total_revised, count = by_quarter[latest]
        if total_base > 0:
            coef_by_market[market] = {
                "coef": round(total_revised / total_base, 6),
                "quarter": latest,
                "base_sum": round(total_base, 2),
                "revised_sum": round(total_revised, 2),
                "line_count": int(count),
            }
    return coef_by_market


def build_contract_budget_landing(
    db: Session,
    city_id: int | None = None,
    *,
    year: int,
    lot: int | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Budget contractuel vs réalisé vs atterrissage par poste, pour une année.

    ``lot`` 1/2 restreint à un lot contractuel ; absent = cumulé (les deux lots).
    """
    tracking = build_market_tracking(db, city_id, year_from=year, year_to=year)

    if lot is None:
        postes_src = tracking["postes"]
        contract_codes = sorted(
            {code for entry in tracking.get("by_lot", []) for code in entry.get("contract_codes", [])}
        )
    else:
        entry = next((e for e in tracking.get("by_lot", []) if e["lot"] == lot), None)
        if entry is None:
            postes_src = []
            contract_codes = []
        else:
            postes_src = entry["postes"]
            contract_codes = sorted(entry.get("contract_codes", []))

    resolved_today = today or date.today()
    progress = _year_progress_percent(year, resolved_today)
    coef_by_market = _revision_coef_by_market(db, city_id, year, resolved_today, contract_codes)

    postes: list[dict[str, Any]] = []
    total_base = total_budget = total_realise = total_landing = 0.0
    for row in postes_src:
        cell = row["by_year"][0]
        poste_out = _poste_landing(row["poste"], row["label"], cell["prevu"], cell["recu"], progress, coef_by_market)
        postes.append(poste_out)
        total_base += poste_out["budget_base"]
        total_budget += poste_out["budget_contractuel"]
        total_realise += poste_out["realise"]
        total_landing += poste_out["atterrissage"]

    by_operation, projection_note = _project_on_operations(db, city_id, contract_codes, postes)

    return {
        "year": year,
        "lot": lot,
        "contract_codes": contract_codes,
        "year_progress_percent": progress,
        "postes": postes,
        "totals": {
            "budget_base": round(total_base, 2),
            "budget_contractuel": round(total_budget, 2),
            "realise": round(total_realise, 2),
            "atterrissage": round(total_landing, 2),
            "reste_a_facturer": round(max(total_budget - total_realise, 0.0), 2),
            "ecart_atterrissage_vs_budget": round(total_landing - total_budget, 2),
        },
        "by_operation": by_operation,
        "projection_note": projection_note,
        "source_note": (
            "Budget base = prévu DPGF DALKIA (P20/P30/P10 nus) ; budget contractuel = base × coefficient de "
            "révision observé (Σrévisé/Σbase du dernier trimestre facturé, extrapolé — Option C) ; réalisé = "
            "reçu factures CPE (déjà révisé). Révision appliquée : P2 et P3/P3.4 (forfaits annuels). P1 gaz : "
            "révision par prix unitaire du gaz (OS3/PEG), mécanisme propre non encore intégré ici → budget base. "
            "P1-ELEC non révisé. Ne pas confondre avec l'intéressement (moteur DJU cpe_atterrissage)."
        ),
    }


def _poste_landing(
    poste: str,
    label: str,
    prevu: float,
    recu: float,
    progress: float,
    coef_by_market: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    budget_base = round(prevu, 2)
    realise = round(recu, 2)
    market = REVISABLE_POSTE_MARKET.get(poste)
    info = coef_by_market.get(market) if market else None
    coef = info["coef"] if info else 1.0
    budget = round(budget_base * coef, 2)  # budget contractuel révisé
    if budget > 0:
        atterrissage = budget
        method = "contractuel_revise" if coef != 1.0 else "contractuel_fixe"
    elif realise:
        atterrissage = _prorata_landing(realise, progress)
        method = "prorata"
    else:
        atterrissage = 0.0
        method = "nul"
    return {
        "poste": poste,
        "label": label,
        "budget_base": budget_base,
        "coefficient_revision": round(coef, 6),
        "revision_detail": _revision_detail(market, info),
        "budget_contractuel": budget,
        "realise": realise,
        "atterrissage": atterrissage,
        "reste_a_facturer": round(max(budget - realise, 0.0), 2),
        "ecart_realise_vs_budget": round(realise - budget, 2),
        "ecart_atterrissage_vs_budget": round(atterrissage - budget, 2),
        "taux_facturation": round(realise / budget, 4) if budget else None,
        "landing_method": method,
    }


def _revision_detail(market: str | None, info: dict[str, Any] | None) -> str | None:
    """Formule lisible de l'extrapolation (affichée en petit sous la ligne du poste)."""
    if market is None:
        return None
    if info is None:
        return f"Marché {market} : aucune facture révisée trouvée → budget = base (coef 1,0000)."
    return (
        f"Coef. révision {market} = Σrévisé / Σbase (T{info['quarter']} = dernier trimestre facturé) "
        f"= {info['revised_sum']:.0f} / {info['base_sum']:.0f} = {info['coef']:.4f}, "
        f"extrapolé à l'année sur {info['line_count']} ligne(s). "
        f"Budget révisé = budget base × {info['coef']:.4f}."
    )


def _project_on_operations(
    db: Session,
    city_id: int | None,
    contract_codes: list[str],
    postes: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    """Projette (hybride) le budget/réalisé par poste sur l'axe ``operation_number``.

    Best-effort : la correspondance poste → opération est déduite des règles de la
    matrice active (``scope`` p1/p2/p3 → ``operation_number``). Un poste dont le scope
    ne mappe pas exactement une seule opération n'est pas projeté (laissé au niveau poste).
    """
    scope_operations = _scope_operation_map(db, city_id, contract_codes)
    if not scope_operations:
        return [], (
            "Aucune règle matrice avec operation_number trouvée pour ces contrats : "
            "projection par opération indisponible (vue par poste seule)."
        )

    by_operation: dict[str, dict[str, Any]] = {}
    unmapped: list[str] = []
    for poste in postes:
        scope = POSTE_SCOPE.get(poste["poste"])
        operations = scope_operations.get(scope, set()) if scope else set()
        if len(operations) != 1:
            if poste["budget_contractuel"] or poste["realise"]:
                unmapped.append(poste["poste"])
            continue
        operation = next(iter(operations))
        agg = by_operation.setdefault(
            operation,
            {"operation_number": operation, "postes": [], "budget_contractuel": 0.0, "realise": 0.0, "atterrissage": 0.0},
        )
        agg["postes"].append(poste["poste"])
        agg["budget_contractuel"] = round(agg["budget_contractuel"] + poste["budget_contractuel"], 2)
        agg["realise"] = round(agg["realise"] + poste["realise"], 2)
        agg["atterrissage"] = round(agg["atterrissage"] + poste["atterrissage"], 2)

    rows = sorted(by_operation.values(), key=lambda r: r["operation_number"])
    if unmapped:
        note = (
            "Projection partielle : poste(s) "
            + ", ".join(sorted(set(unmapped)))
            + " non rattaché(s) à une opération unique (scope absent ou ambigu dans la matrice)."
        )
    else:
        note = "Projection par opération déduite des règles matrice (scope → operation_number)."
    return rows, note


def _scope_operation_map(
    db: Session, city_id: int | None, contract_codes: list[str]
) -> dict[str, set[str]]:
    """scope (p1/p2/p3) → ensemble des operation_number, lu dans la matrice active des contrats."""
    if not contract_codes:
        return {}
    contracts = db.execute(
        select(AccountingMatrixContract).where(
            AccountingMatrixContract.city_id == city_id,
            AccountingMatrixContract.contract_code.in_(contract_codes),
        )
    ).scalars().all()

    scope_operations: dict[str, set[str]] = {}
    for contract in contracts:
        active = next((v for v in contract.versions if v.status == "active"), None)
        if active is None:
            continue
        rules = db.execute(
            select(AccountingMatrixRule).where(
                AccountingMatrixRule.matrix_version_id == active.id,
                AccountingMatrixRule.is_active.is_(True),
            )
        ).scalars().all()
        for rule in rules:
            scope = (rule.scope or "").strip().lower()
            operation = (rule.operation_number or "").strip()
            if scope and operation:
                scope_operations.setdefault(scope, set()).add(operation)
    return scope_operations


def _year_progress_percent(year: int, today: date) -> float:
    if today.year < year:
        return 0.0
    if today.year > year:
        return 100.0
    day_of_year = today.timetuple().tm_yday
    days_in_year = 366 if _is_leap(year) else 365
    return round(min(100.0, day_of_year / days_in_year * 100.0), 2)


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _prorata_landing(realise: float, progress_percent: float) -> float:
    if progress_percent <= 0:
        return 0.0
    return round(realise / (progress_percent / 100.0), 2)
