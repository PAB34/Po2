"""Référentiel comptable et registre finances DALKIA pour le module CPE."""
from __future__ import annotations

import io
import json
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import openpyxl
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.cpe import (
    CpeAccountingNatureRule,
    CpeAccountingSiteMapping,
    CpeFinanceImportBatch,
    CpeFinanceInvoice,
    CpeFinanceLine,
)
from app.schemas.cpe import (
    CpeAccountingImportResult,
    CpeAccountingNatureRuleCreate,
    CpeAccountingNatureRuleUpdate,
    CpeAccountingSiteMappingCreate,
    CpeAccountingSiteMappingUpdate,
    CpeFinanceImportResult,
)

_SITE_CODE_RE = re.compile(r"\b(VDS-[A-Z]+\s+\d+(?:\.\d+)?|CCAS\s+\d+)\b", flags=re.IGNORECASE)


def _norm_header(value: Any) -> str:
    raw = "" if value is None else str(value).strip()
    normalized = unicodedata.normalize("NFKD", raw)
    ascii_value = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "_", ascii_value.lower()).strip("_")


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).strip()
    return text or None


def _upper(value: Any) -> str | None:
    text = _clean(value)
    return text.upper() if text else None


def _float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
    if not text:
        return None
    try:
        return float(Decimal(text))
    except (InvalidOperation, ValueError):
        return None


def _date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _site_code(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    match = _SITE_CODE_RE.search(text)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1).upper()).strip()


def _rows_from_sheet(ws, header_row: int) -> list[dict[str, Any]]:
    headers = [_norm_header(cell.value) for cell in ws[header_row]]
    rows: list[dict[str, Any]] = []
    for excel_row in ws.iter_rows(min_row=header_row + 1, values_only=True):
        if not any(value not in (None, "") for value in excel_row):
            continue
        rows.append({headers[index]: value for index, value in enumerate(excel_row) if index < len(headers)})
    return rows


def list_accounting_nature_rules(db: Session, city_id: int | None = None) -> list[CpeAccountingNatureRule]:
    query = select(CpeAccountingNatureRule)
    if city_id is not None:
        query = query.where(CpeAccountingNatureRule.city_id == city_id)
    query = query.order_by(CpeAccountingNatureRule.market, CpeAccountingNatureRule.service_sold, CpeAccountingNatureRule.billed_item)
    return list(db.scalars(query).all())


def create_accounting_nature_rule(db: Session, payload: CpeAccountingNatureRuleCreate) -> CpeAccountingNatureRule:
    rule = CpeAccountingNatureRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_accounting_nature_rule(
    db: Session,
    rule: CpeAccountingNatureRule,
    payload: CpeAccountingNatureRuleUpdate,
) -> CpeAccountingNatureRule:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


def delete_accounting_nature_rule(db: Session, rule: CpeAccountingNatureRule) -> None:
    db.delete(rule)
    db.commit()


def list_accounting_site_mappings(db: Session, city_id: int | None = None) -> list[CpeAccountingSiteMapping]:
    query = select(CpeAccountingSiteMapping)
    if city_id is not None:
        query = query.where(CpeAccountingSiteMapping.city_id == city_id)
    query = query.order_by(CpeAccountingSiteMapping.code_site)
    return list(db.scalars(query).all())


def create_accounting_site_mapping(db: Session, payload: CpeAccountingSiteMappingCreate) -> CpeAccountingSiteMapping:
    mapping = CpeAccountingSiteMapping(**payload.model_dump())
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


def update_accounting_site_mapping(
    db: Session,
    mapping: CpeAccountingSiteMapping,
    payload: CpeAccountingSiteMappingUpdate,
) -> CpeAccountingSiteMapping:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(mapping, field, value)
    db.commit()
    db.refresh(mapping)
    return mapping


def delete_accounting_site_mapping(db: Session, mapping: CpeAccountingSiteMapping) -> None:
    db.delete(mapping)
    db.commit()


def import_codification_workbook(
    db: Session,
    raw_bytes: bytes,
    *,
    filename: str | None,
    city_id: int | None,
) -> CpeAccountingImportResult:
    """Importe la matrice `analyse_codification_dalkia.xlsx` en upsert."""
    wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
    errors: list[str] = []
    created_rules = updated_rules = created_sites = updated_sites = 0

    if "Poste facturé vers Nature ctpab" in wb.sheetnames:
        ws = wb["Poste facturé vers Nature ctpab"]
        for row in _rows_from_sheet(ws, 3):
            market = _upper(row.get("marche"))
            billed_item = _upper(row.get("poste_facture"))
            nature = _clean(row.get("nature_proposee"))
            if not market or not billed_item or not nature:
                continue
            service_sold = _upper(row.get("service_vendu"))
            frequency = _clean(row.get("frequence"))
            existing = db.scalars(
                select(CpeAccountingNatureRule).where(
                    CpeAccountingNatureRule.city_id == city_id,
                    CpeAccountingNatureRule.market == market,
                    func.coalesce(CpeAccountingNatureRule.service_sold, "") == (service_sold or ""),
                    CpeAccountingNatureRule.billed_item == billed_item,
                    func.coalesce(CpeAccountingNatureRule.frequency, "") == (frequency or ""),
                )
            ).first()
            payload = {
                "city_id": city_id,
                "market": market,
                "service_sold": service_sold,
                "billed_item": billed_item,
                "frequency": frequency,
                "accounting_nature": nature,
                "accounting_label": _clean(row.get("libelle_nature")),
                "active": True,
            }
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                updated_rules += 1
            else:
                db.add(CpeAccountingNatureRule(**payload))
                created_rules += 1
    else:
        errors.append("Feuille absente : Poste facturé vers Nature ctpab")

    if "Sites vers codes" in wb.sheetnames:
        ws = wb["Sites vers codes"]
        for row in _rows_from_sheet(ws, 1):
            code_site = _upper(row.get("code_site"))
            site_name = _clean(row.get("nom_du_site"))
            if not code_site or not site_name:
                continue
            existing = db.scalars(
                select(CpeAccountingSiteMapping).where(
                    CpeAccountingSiteMapping.city_id == city_id,
                    CpeAccountingSiteMapping.code_site == code_site,
                )
            ).first()
            payload = {
                "city_id": city_id,
                "code_site": code_site,
                "site_name": site_name,
                "family": _clean(row.get("famille")),
                "manager": _clean(row.get("gestionnaire")),
                "alternate_manager": _clean(row.get("gestionnaire_alternatif")),
                "service_code": _clean(row.get("service")),
                "service_label": _clean(row.get("libelle_service")),
                "function_code": _clean(row.get("fonction")),
                "function_label": _clean(row.get("libelle_fonction")),
                "antenna_code": _clean(row.get("antenne")),
                "antenna_label": _clean(row.get("libelle_antenne")),
                "operation_code": _clean(row.get("operation_si_travaux")),
                "operation_label": _clean(row.get("libelle_operation")),
                "active": True,
            }
            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                updated_sites += 1
            else:
                db.add(CpeAccountingSiteMapping(**payload))
                created_sites += 1
    else:
        errors.append("Feuille absente : Sites vers codes")

    db.commit()
    return CpeAccountingImportResult(
        filename=filename,
        nature_rules_created=created_rules,
        nature_rules_updated=updated_rules,
        site_mappings_created=created_sites,
        site_mappings_updated=updated_sites,
        errors=errors,
    )


def _find_accounting_rule(
    rules: list[CpeAccountingNatureRule],
    market: str | None,
    service_sold: str | None,
    billed_item: str | None,
) -> CpeAccountingNatureRule | None:
    market_norm = (market or "").upper()
    service_norm = (service_sold or "").upper()
    item_norm = (billed_item or "").upper()
    for rule in rules:
        if rule.market.upper() == market_norm and (rule.billed_item or "").upper() == item_norm:
            if not rule.service_sold or rule.service_sold.upper() == service_norm:
                return rule
    return None


def import_finance_workbook(
    db: Session,
    raw_bytes: bytes,
    *,
    filename: str | None,
    city_id: int | None,
) -> CpeFinanceImportResult:
    """Importe un export finances DALKIA XLSX et persiste factures + lignes."""
    wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = _rows_from_sheet(ws, 1)
    if not rows:
        raise ValueError("Aucune ligne exploitable dans l'export finances.")

    batch = CpeFinanceImportBatch(city_id=city_id, filename=filename)
    db.add(batch)
    db.flush()

    rules = list_accounting_nature_rules(db, city_id)
    site_mappings = {m.code_site.upper(): m for m in list_accounting_site_mappings(db, city_id)}
    invoice_by_number: dict[str, CpeFinanceInvoice] = {}
    invoice_lines: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    total_ht = 0.0
    matched_rules = matched_sites = 0
    warnings: list[str] = []

    for index, row in enumerate(rows, start=2):
        invoice_number = _clean(row.get("numero_de_facture")) or f"sans-numero-ligne-{index}"
        amount_ht = _float(row.get("montant_ht")) or 0.0
        total_ht += amount_ht
        invoice_lines[invoice_number].append((index, row))
        if invoice_number not in invoice_by_number:
            invoice = CpeFinanceInvoice(
                batch_id=batch.id,
                city_id=city_id,
                invoice_number=invoice_number,
                contract_code=_clean(row.get("code_contrat")),
                contract_label=_clean(row.get("libelle_contrat")),
                invoice_type=_clean(row.get("type_de_facture")),
                supplier=_clean(row.get("societe")),
                customer_code=_clean(row.get("code_du_client")),
                customer_name=_clean(row.get("nom_du_client")),
                invoice_date=_date(row.get("date_d_edition")),
                due_date=_date(row.get("date_d_echeance_de_la_facture")),
                period_start=_date(row.get("debut_periode_de_facturation")),
                period_end=_date(row.get("fin_periode_de_facturation")),
                total_ht=0.0,
            )
            db.add(invoice)
            db.flush()
            invoice_by_number[invoice_number] = invoice

        invoice = invoice_by_number[invoice_number]
        invoice.total_ht = round((invoice.total_ht or 0.0) + amount_ht, 2)
        start = _date(row.get("debut_periode_de_facturation"))
        end = _date(row.get("fin_periode_de_facturation"))
        if start and (invoice.period_start is None or start < invoice.period_start):
            invoice.period_start = start
        if end and (invoice.period_end is None or end > invoice.period_end):
            invoice.period_end = end

    for invoice_number, source_rows in invoice_lines.items():
        invoice = invoice_by_number[invoice_number]
        for row_number, source_row in source_rows:
            market = _upper(source_row.get("marche"))
            service_sold = _upper(source_row.get("service_vendu"))
            billed_item = _upper(source_row.get("poste_facture"))
            detail = _clean(source_row.get("lieu_ou_detail_de_la_prestation"))
            detected_site = _site_code(detail)
            site_mapping = site_mappings.get(detected_site or "") if detected_site else None
            rule = _find_accounting_rule(rules, market, service_sold, billed_item)
            if site_mapping:
                matched_sites += 1
            if rule:
                matched_rules += 1
            line = CpeFinanceLine(
                batch_id=batch.id,
                invoice_id=invoice.id,
                city_id=city_id,
                row_number=row_number,
                contract_code=_clean(source_row.get("code_contrat")),
                invoice_number=invoice_number,
                market=market,
                market_type=_clean(source_row.get("type_de_marche")),
                service_sold=service_sold,
                billed_item=billed_item,
                vat_rate=_float(source_row.get("taux_de_tva")),
                amount_ht=_float(source_row.get("montant_ht")) or 0.0,
                consumption=_float(source_row.get("consommation")),
                unit=_clean(source_row.get("unite")),
                detail=detail,
                site_code_detected=detected_site,
                accounting_site_id=site_mapping.id if site_mapping else None,
                accounting_rule_id=rule.id if rule else None,
                accounting_nature=rule.accounting_nature if rule else None,
                accounting_label=rule.accounting_label if rule else None,
                period_start=_date(source_row.get("debut_periode_de_facturation")),
                period_end=_date(source_row.get("fin_periode_de_facturation")),
                raw_json=json.dumps({key: str(value) if value is not None else None for key, value in source_row.items()}),
            )
            db.add(line)

    batch.line_count = len(rows)
    batch.invoice_count = len(invoice_by_number)
    batch.total_ht = round(total_ht, 2)
    if matched_rules < len(rows):
        warnings.append(f"{len(rows) - matched_rules} ligne(s) sans nature comptable rattachee.")
    if matched_sites == 0:
        warnings.append("Aucun code site VDS/CCAS detecte dans les lignes : un mapping detail DALKIA -> site sera necessaire.")
    db.commit()
    db.refresh(batch)
    invoices = list(invoice_by_number.values())
    for invoice in invoices:
        db.refresh(invoice)
    return CpeFinanceImportResult(
        batch=batch,
        invoices=sorted(invoices, key=lambda item: item.invoice_number),
        line_count=len(rows),
        matched_accounting_rules=matched_rules,
        matched_site_mappings=matched_sites,
        warnings=warnings,
    )


def list_finance_batches(db: Session, city_id: int | None = None) -> list[CpeFinanceImportBatch]:
    query = select(CpeFinanceImportBatch)
    if city_id is not None:
        query = query.where(CpeFinanceImportBatch.city_id == city_id)
    query = query.order_by(CpeFinanceImportBatch.created_at.desc())
    return list(db.scalars(query).all())


def list_finance_invoices(
    db: Session,
    city_id: int | None = None,
    batch_id: int | None = None,
) -> list[CpeFinanceInvoice]:
    query = select(CpeFinanceInvoice)
    if city_id is not None:
        query = query.where(CpeFinanceInvoice.city_id == city_id)
    if batch_id is not None:
        query = query.where(CpeFinanceInvoice.batch_id == batch_id)
    query = query.order_by(CpeFinanceInvoice.invoice_date.desc().nullslast(), CpeFinanceInvoice.invoice_number)
    return list(db.scalars(query).all())


def delete_finance_batch(db: Session, batch: CpeFinanceImportBatch) -> None:
    db.execute(delete(CpeFinanceLine).where(CpeFinanceLine.batch_id == batch.id))
    db.execute(delete(CpeFinanceInvoice).where(CpeFinanceInvoice.batch_id == batch.id))
    db.delete(batch)
    db.commit()
