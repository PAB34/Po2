"""Application d'une matrice à une facture + cycle de vie des snapshots.

Doc 38 (invoice_accounting_snapshots) et doc 35 (§2 chaîne, §4 ventilation
100 %, critères 2/5 immutabilité et dédoublonnage).

Le moteur ``apply_matrix`` est pur (règles + lignes -> imputation), donc
testable et indépendant de la source de facture. Le snapshot fige la version
de matrice utilisée : une facture validée reste liée à cette version même si
une nouvelle est créée ensuite.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.accounting_matrix import (
    AccountingMatrixRule,
    AccountingMatrixVersion,
    InvoiceAccountingSnapshot,
)
from app.services import accounting_matrix as svc

_FROZEN_STATUSES = ("validated", "manual_override", "exported")
_TOLERANCE = 0.01


@dataclass
class InvoiceLine:
    billed_item: str | None = None
    site_code: str | None = None
    meter_id: str | None = None
    amount: float | None = None
    line_ref: str | None = None


# ---------------------------------------------------------------------------
# Moteur pur
# ---------------------------------------------------------------------------
def apply_matrix(rules: list[AccountingMatrixRule], lines: list[InvoiceLine]) -> dict:
    """Rapproche chaque ligne de facture aux règles actives d'une version.

    Retourne un dict d'imputation prêt à être figé dans snapshot_json, avec la
    liste des exceptions (lignes non imputées, ventilation ≠ 100 %).

    Les règles ne jouent pas toutes le même rôle :

    - les règles de contexte (site, compteur, axes service/fonction/antenne)
      enrichissent la ligne ;
    - les règles de nature / ventilation (accounting_nature renseignée)
      portent l'imputation financière.

    Une règle compteur à 100 % et une règle nature à 100 % ne doivent donc pas
    produire 200 % de ventilation : elles se complètent.
    """
    active_rules = [r for r in rules if r.is_active]
    result_lines: list[dict] = []
    exceptions: list[dict] = []

    for idx, line in enumerate(lines):
        candidates = [r for r in active_rules if _rule_matches(r, line)]
        context_rules = _select_context_rules(candidates)
        allocation_rules = _select_allocation_rules(candidates)

        if not allocation_rules:
            result_lines.append({
                "line_index": idx, "line_ref": line.line_ref, "billed_item": line.billed_item,
                "amount": line.amount, "matched": False, "imputations": [],
            })
            reason = "aucune règle applicable" if not candidates else "aucune règle de nature comptable applicable"
            exceptions.append({"line_index": idx, "billed_item": line.billed_item, "reason": reason})
            continue

        context = _merged_context(context_rules)
        imputations = [_imputation(r, line, context) for r in allocation_rules]

        alloc_sum = round(sum(r.allocation_percent for r in allocation_rules), 2)
        if abs(alloc_sum - 100.0) > _TOLERANCE:
            exceptions.append({
                "line_index": idx, "billed_item": line.billed_item,
                "reason": f"ventilation = {alloc_sum} % (≠ 100 %)",
            })

        result_lines.append({
            "line_index": idx, "line_ref": line.line_ref, "billed_item": line.billed_item,
            "amount": line.amount, "matched": True, "allocation_total": alloc_sum,
            "imputations": imputations,
        })

    return {
        "lines": result_lines,
        "exceptions": exceptions,
        "matched_lines": sum(1 for l in result_lines if l["matched"]),
        "total_lines": len(result_lines),
    }


def _rule_matches(rule: AccountingMatrixRule, line: InvoiceLine) -> bool:
    if rule.site_code and rule.site_code != line.site_code:
        return False
    if rule.meter_id and rule.meter_id != line.meter_id:
        return False
    if rule.billed_item_pattern:
        if not line.billed_item:
            return False
        if rule.billed_item_pattern.strip().lower() not in line.billed_item.lower():
            return False
    return True


def _is_allocation_rule(rule: AccountingMatrixRule) -> bool:
    """Une règle d'imputation doit porter une nature comptable.

    Les règles issues des mappings site/compteur peuvent ne contenir que les
    axes analytiques. Elles ne ventilent pas le montant à elles seules.
    """
    return bool(rule.accounting_nature)


def _select_allocation_rules(candidates: list[AccountingMatrixRule]) -> list[AccountingMatrixRule]:
    allocation_rules = [r for r in candidates if _is_allocation_rule(r)]
    if not allocation_rules:
        return []
    top_priority = max(r.priority for r in allocation_rules)
    return [r for r in allocation_rules if r.priority == top_priority]


def _select_context_rules(candidates: list[AccountingMatrixRule]) -> list[AccountingMatrixRule]:
    context_rules = [r for r in candidates if not _is_allocation_rule(r)]
    if not context_rules:
        return []
    top_priority = max(r.priority for r in context_rules)
    return [r for r in context_rules if r.priority == top_priority]


def _merged_context(rules: list[AccountingMatrixRule]) -> dict:
    """Fusionne les axes analytiques des règles de contexte.

    Les règles sont lues dans un ordre stable ; la première valeur non vide
    gagne. Une règle d'imputation peut encore surcharger ces axes champ par
    champ si elle porte une valeur plus spécifique.
    """
    context = {"service": None, "function": None, "antenna": None, "operation": None}
    for rule in sorted(rules, key=lambda r: (r.priority, r.id or 0), reverse=True):
        if context["service"] is None and rule.accounting_service:
            context["service"] = rule.accounting_service
        if context["function"] is None and rule.accounting_function:
            context["function"] = rule.accounting_function
        if context["antenna"] is None and rule.accounting_antenna:
            context["antenna"] = rule.accounting_antenna
        if context["operation"] is None and rule.operation_number:
            context["operation"] = rule.operation_number
    return context


def _imputation(rule: AccountingMatrixRule, line: InvoiceLine, context: dict | None = None) -> dict:
    context = context or {}
    pct = rule.allocation_percent
    amount_allocated = round(line.amount * pct / 100.0, 2) if line.amount is not None else None
    return {
        "rule_id": rule.id,
        "stable_rule_key": rule.stable_rule_key,
        "service": rule.accounting_service or context.get("service"),
        "function": rule.accounting_function or context.get("function"),
        "antenna": rule.accounting_antenna or context.get("antenna"),
        "operation": rule.operation_number or context.get("operation"),
        "nature": rule.accounting_nature,
        "label": rule.accounting_label,
        "allocation_percent": pct,
        "amount_allocated": amount_allocated,
    }


# ---------------------------------------------------------------------------
# Orchestration (DB + cycle de vie)
# ---------------------------------------------------------------------------
def apply_to_invoice(
    db: Session, city_id: int | None, *, source: str, invoice_id: str,
    contract_id: int, lines: list[InvoiceLine],
) -> InvoiceAccountingSnapshot:
    """Produit/rafraîchit une proposition d'imputation (statut ``proposed``).

    Refuse d'écraser un snapshot déjà figé (validé / corrigé / transmis) :
    une facture close réimportée n'est pas retraitée silencieusement (doc 35).
    """
    contract = svc._require_contract(db, city_id, contract_id)
    version = svc._active_version(contract)
    if version is None:
        raise ValueError("Aucune version active pour ce contrat matrice : activez une version d'abord.")

    existing = _get_snapshot(db, city_id, source, invoice_id)
    if existing and existing.status in _FROZEN_STATUSES:
        raise ValueError("Facture déjà traitée (snapshot figé). Réouverture explicite requise pour ré-imputer.")

    result = apply_matrix(list(version.rules), lines)
    snapshot = existing or InvoiceAccountingSnapshot(
        city_id=city_id, invoice_source=source, invoice_id=invoice_id,
    )
    snapshot.matrix_contract_id = contract.id
    snapshot.matrix_version_id = version.id
    snapshot.status = "proposed"
    snapshot.snapshot_json = json.dumps(result, ensure_ascii=False)
    snapshot.exceptions_json = json.dumps(result["exceptions"], ensure_ascii=False)
    if existing is None:
        db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def validate_snapshot(
    db: Session, city_id: int | None, *, source: str, invoice_id: str, user_id: int | None,
) -> InvoiceAccountingSnapshot:
    """Fige la proposition. Bloque si exceptions ou ventilation ≠ 100 %."""
    snapshot = _require_snapshot(db, city_id, source, invoice_id)
    if snapshot.status == "exported":
        raise ValueError("Facture déjà transmise aux finances.")

    exceptions = json.loads(snapshot.exceptions_json) if snapshot.exceptions_json else []
    if exceptions:
        raise ValueError(f"Validation impossible : {len(exceptions)} exception(s) à résoudre.")

    snapshot.status = "validated"
    snapshot.validated_by_user_id = user_id
    snapshot.validated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def manual_override(
    db: Session, city_id: int | None, *, source: str, invoice_id: str,
    snapshot_json: str, motif: str, user_id: int | None,
) -> InvoiceAccountingSnapshot:
    """Fige une correction manuelle motivée (doc 35 §6 : compta avec motif)."""
    if not motif or not motif.strip():
        raise ValueError("Un motif est obligatoire pour une correction manuelle.")
    snapshot = _require_snapshot(db, city_id, source, invoice_id)
    if snapshot.status == "exported":
        raise ValueError("Facture déjà transmise aux finances.")

    snapshot.snapshot_json = snapshot_json
    snapshot.exceptions_json = json.dumps([{"manual_override": motif}], ensure_ascii=False)
    snapshot.status = "manual_override"
    snapshot.validated_by_user_id = user_id
    snapshot.validated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def export_finance(
    db: Session, city_id: int | None, *, source: str, invoice_id: str,
) -> InvoiceAccountingSnapshot:
    """Marque la transmission au service finance (statut ``exported``)."""
    snapshot = _require_snapshot(db, city_id, source, invoice_id)
    if snapshot.status not in ("validated", "manual_override"):
        raise ValueError("Seul un snapshot validé ou corrigé peut être transmis aux finances.")
    snapshot.status = "exported"
    snapshot.exported_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(snapshot)
    return snapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_snapshot(db: Session, city_id: int | None, source: str, invoice_id: str) -> InvoiceAccountingSnapshot | None:
    return db.execute(
        select(InvoiceAccountingSnapshot).where(
            InvoiceAccountingSnapshot.city_id == city_id,
            InvoiceAccountingSnapshot.invoice_source == source,
            InvoiceAccountingSnapshot.invoice_id == invoice_id,
        )
    ).scalars().first()


def _require_snapshot(db: Session, city_id: int | None, source: str, invoice_id: str) -> InvoiceAccountingSnapshot:
    snapshot = _get_snapshot(db, city_id, source, invoice_id)
    if snapshot is None:
        raise ValueError("Aucun snapshot pour cette facture : appliquez d'abord la matrice.")
    return snapshot
