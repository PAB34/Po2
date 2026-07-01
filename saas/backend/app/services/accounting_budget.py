"""Service du budget par marché (cadrage doc refonte-v1/suivi-financier-budget-atterrissage).

Le budget est saisi à la maille opération (`operation_number`), rattaché à un
`AccountingMatrixContract` (= « le marché »). Le réalisé n'est pas dupliqué en
base : il est recalculé depuis `invoice_accounting_snapshots` (statuts figés)
en additionnant `amount_allocated` par opération.

⚠️ Limite connue (PO2-FIN-001) : la résolution de l'année d'une facture n'est
fiable que pour les sources déjà branchées ci-dessous (CPE/DALKIA, imports
fluides). Les snapshots dont l'année ne peut pas être résolue sont exclus du
réalisé et comptés séparément, pour ne jamais présenter un chiffre trompeur.
"""
from __future__ import annotations

import json
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.accounting_budget import AccountingBudgetLine
from app.models.accounting_matrix import AccountingMatrixContract, InvoiceAccountingSnapshot
from app.models.cpe import CpeFinanceInvoice
from app.models.invoice import EnergyInvoice, EnergyInvoiceImport, EnergyInvoiceSite

_REALIZED_STATUSES = ("validated", "manual_override", "exported")


# ---------------------------------------------------------------------------
# CRUD lignes de budget
# ---------------------------------------------------------------------------
def list_budget_lines(
    db: Session, city_id: int | None, matrix_contract_id: int, year: int
) -> list[AccountingBudgetLine]:
    _require_contract(db, city_id, matrix_contract_id)
    stmt = (
        select(AccountingBudgetLine)
        .where(
            AccountingBudgetLine.city_id == city_id,
            AccountingBudgetLine.matrix_contract_id == matrix_contract_id,
            AccountingBudgetLine.year == year,
        )
        .order_by(AccountingBudgetLine.operation_number)
    )
    return list(db.execute(stmt).scalars().all())


def create_budget_line(db: Session, city_id: int | None, payload) -> AccountingBudgetLine:
    _require_contract(db, city_id, payload.matrix_contract_id)
    existing = db.execute(
        select(AccountingBudgetLine).where(
            AccountingBudgetLine.city_id == city_id,
            AccountingBudgetLine.matrix_contract_id == payload.matrix_contract_id,
            AccountingBudgetLine.year == payload.year,
            AccountingBudgetLine.operation_number == payload.operation_number,
        )
    ).scalars().first()
    if existing is not None:
        raise ValueError(
            f"Une ligne de budget existe déjà pour l'opération {payload.operation_number} en {payload.year}."
        )
    line = AccountingBudgetLine(
        city_id=city_id,
        matrix_contract_id=payload.matrix_contract_id,
        year=payload.year,
        operation_number=payload.operation_number,
        label=payload.label,
        amount_budget=payload.amount_budget,
        comment=payload.comment,
    )
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def update_budget_line(db: Session, city_id: int | None, line_id: int, payload) -> AccountingBudgetLine:
    line = _require_budget_line(db, city_id, line_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(line, field, value)
    db.commit()
    db.refresh(line)
    return line


def delete_budget_line(db: Session, city_id: int | None, line_id: int) -> None:
    line = _require_budget_line(db, city_id, line_id)
    db.delete(line)
    db.commit()


# ---------------------------------------------------------------------------
# Suivi : budget vs réalisé vs atterrissage (pro-rata temporel v1)
# ---------------------------------------------------------------------------
def compute_suivi(
    db: Session, city_id: int | None, matrix_contract_id: int, year: int, *, today: date | None = None
) -> dict:
    _require_contract(db, city_id, matrix_contract_id)
    budget_lines = list_budget_lines(db, city_id, matrix_contract_id, year)
    realized = compute_realized_by_operation(db, city_id, matrix_contract_id, year)

    progress = _year_progress_percent(year, today or date.today())
    operations = sorted(set(realized["by_operation"]) | {l.operation_number for l in budget_lines})
    budget_by_operation = {l.operation_number: l.amount_budget for l in budget_lines}

    rows = []
    total_budget = total_realized = total_landing = 0.0
    for operation in operations:
        amount_budget = round(budget_by_operation.get(operation, 0.0), 2)
        amount_realized = round(realized["by_operation"].get(operation, 0.0), 2)
        amount_landing = _prorata_landing(amount_realized, progress)
        rows.append({
            "operation_number": operation,
            "amount_budget": amount_budget,
            "amount_realized": amount_realized,
            "amount_landing": amount_landing,
            "variance_to_budget": round(amount_budget - amount_landing, 2),
        })
        total_budget += amount_budget
        total_realized += amount_realized
        total_landing += amount_landing

    total_snapshots = realized["snapshots_total"]
    unresolved = realized["snapshots_excluded_unknown_year"]
    note = (
        "Réalisé fiable : toutes les factures figées de ce marché ont une année résolue."
        if total_snapshots == 0 or unresolved == 0
        else (
            f"{unresolved} facture(s) figée(s) sur {total_snapshots} n'ont pas pu être rattachées à une "
            "année (source non encore branchée) et sont exclues du réalisé ci-dessus."
        )
    )

    return {
        "matrix_contract_id": matrix_contract_id,
        "year": year,
        "year_progress_percent": progress,
        "rows": rows,
        "unassigned_realized_amount": realized["unassigned_amount"],
        "total_budget": round(total_budget, 2),
        "total_realized": round(total_realized, 2),
        "total_landing": round(total_landing, 2),
        "snapshots_included": realized["snapshots_included"],
        "snapshots_excluded_unknown_year": realized["snapshots_excluded_unknown_year"],
        "snapshots_excluded_other_year": realized["snapshots_excluded_other_year"],
        "snapshots_total": total_snapshots,
        "data_completeness_note": note,
    }


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


def _prorata_landing(amount_realized: float, progress_percent: float) -> float:
    """Atterrissage v1 : pro-rata temporel simple (doc §7, moteur physique en v2)."""
    if progress_percent <= 0:
        return 0.0
    return round(amount_realized / (progress_percent / 100.0), 2)


# ---------------------------------------------------------------------------
# Réalisé : agrégat des snapshots figés par opération
# ---------------------------------------------------------------------------
def compute_realized_by_operation(db: Session, city_id: int | None, matrix_contract_id: int, year: int) -> dict:
    snapshots = db.execute(
        select(InvoiceAccountingSnapshot).where(
            InvoiceAccountingSnapshot.city_id == city_id,
            InvoiceAccountingSnapshot.matrix_contract_id == matrix_contract_id,
            InvoiceAccountingSnapshot.status.in_(_REALIZED_STATUSES),
        )
    ).scalars().all()

    by_operation: dict[str, float] = {}
    unassigned_amount = 0.0
    included = excluded_unknown_year = excluded_other_year = 0

    for snapshot in snapshots:
        invoice_year = _resolve_invoice_year(db, city_id, snapshot.invoice_source, snapshot.invoice_id)
        if invoice_year is None:
            excluded_unknown_year += 1
            continue
        if invoice_year != year:
            excluded_other_year += 1
            continue
        included += 1
        if not snapshot.snapshot_json:
            continue
        try:
            payload = json.loads(snapshot.snapshot_json)
        except (TypeError, ValueError):
            continue
        for line in payload.get("lines", []):
            for imputation in line.get("imputations", []):
                amount = imputation.get("amount_allocated")
                if amount is None:
                    continue
                operation = imputation.get("operation")
                if operation:
                    by_operation[operation] = round(by_operation.get(operation, 0.0) + amount, 2)
                else:
                    unassigned_amount = round(unassigned_amount + amount, 2)

    return {
        "by_operation": by_operation,
        "unassigned_amount": unassigned_amount,
        "snapshots_included": included,
        "snapshots_excluded_unknown_year": excluded_unknown_year,
        "snapshots_excluded_other_year": excluded_other_year,
        "snapshots_total": len(snapshots),
    }


def _resolve_invoice_year(db: Session, city_id: int | None, source: str, invoice_id: str) -> int | None:
    normalized = (source or "").strip().lower().replace("-", "_")
    if normalized in {"cpe_dalkia", "dalkia_cpe"}:
        return _resolve_cpe_dalkia_year(db, city_id, invoice_id)
    if normalized in {"energy_import", "fluides_import"}:
        return _resolve_energy_import_year(db, city_id, invoice_id)
    # Sources pas encore branchées (gaz TotalEnergies...) : année non résolue,
    # exclue explicitement plutôt que devinée (cf. note de complétude).
    return None


def _resolve_cpe_dalkia_year(db: Session, city_id: int | None, invoice_id: str) -> int | None:
    try:
        cpe_invoice_id = int(invoice_id)
    except (TypeError, ValueError):
        return None
    invoice = db.get(CpeFinanceInvoice, cpe_invoice_id)
    if invoice is None or (city_id is not None and invoice.city_id != city_id):
        return None
    reference_date = invoice.invoice_date or invoice.period_start or invoice.period_end
    return reference_date.year if reference_date else None


def _resolve_energy_import_year(db: Session, city_id: int | None, invoice_id: str) -> int | None:
    try:
        import_id = int(invoice_id)
    except (TypeError, ValueError):
        return None
    stmt = (
        select(EnergyInvoiceImport)
        .where(EnergyInvoiceImport.id == import_id)
        .options(
            selectinload(EnergyInvoiceImport.normalized_invoice)
            .selectinload(EnergyInvoice.sites)
            .selectinload(EnergyInvoiceSite.periods)
        )
    )
    if city_id is not None:
        stmt = stmt.where(EnergyInvoiceImport.city_id == city_id)
    invoice_import = db.scalar(stmt)
    if invoice_import is None or invoice_import.normalized_invoice is None:
        return None
    for site in invoice_import.normalized_invoice.sites:
        for period in site.periods:
            reference_date = period.period_start or period.period_end
            if reference_date:
                return reference_date.year
    return None


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------
def _require_contract(db: Session, city_id: int | None, contract_id: int) -> AccountingMatrixContract:
    contract = db.get(AccountingMatrixContract, contract_id)
    if contract is None or contract.city_id != city_id:
        raise ValueError("Contrat matrice (marché) introuvable.")
    return contract


def _require_budget_line(db: Session, city_id: int | None, line_id: int) -> AccountingBudgetLine:
    line = db.get(AccountingBudgetLine, line_id)
    if line is None or line.city_id != city_id:
        raise ValueError("Ligne de budget introuvable.")
    return line
