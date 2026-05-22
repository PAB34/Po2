"""Persistence and first P1 control view for DALKIA finance exports."""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from hashlib import sha256
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.cpe import CpeFinanceImportBatch, CpeFinanceInvoice, CpeFinanceLine, CpeSite
from app.schemas.cpe import (
    CpeFinanceGroupSummary,
    CpeFinanceImportBatchDetail,
    CpeFinanceImportBatchOut,
    CpeFinanceP1Summary,
)
from app.services.cpe_finance_preview import CPE_FINANCE_MARKETS, DalkiaFinanceRow, parse_finance_rows

TARGET_CPE_CONTRACT_CODE = "C00190116O"


def _safe_filename(filename: str | None) -> str:
    name = (filename or "export-finances-dalkia.csv").replace("\\", "/").split("/")[-1].strip()
    return (name or "export-finances-dalkia.csv")[:255]


def _parse_iso_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _to_float(value) -> float | None:
    return None if value is None else float(value)


def _load_batch_options():
    return (
        selectinload(CpeFinanceImportBatch.invoices),
        selectinload(CpeFinanceImportBatch.lines).selectinload(CpeFinanceLine.invoice),
        selectinload(CpeFinanceImportBatch.lines).selectinload(CpeFinanceLine.cpe_site),
    )


def list_finance_batches(db: Session, city_id: int) -> list[CpeFinanceImportBatch]:
    return list(
        db.scalars(
            select(CpeFinanceImportBatch)
            .where(CpeFinanceImportBatch.city_id == city_id)
            .order_by(CpeFinanceImportBatch.created_at.desc(), CpeFinanceImportBatch.id.desc())
        ).all()
    )


def get_finance_batch(db: Session, city_id: int, batch_id: int) -> CpeFinanceImportBatch | None:
    return db.scalars(
        select(CpeFinanceImportBatch)
        .where(CpeFinanceImportBatch.city_id == city_id, CpeFinanceImportBatch.id == batch_id)
        .options(*_load_batch_options())
    ).first()


def list_finance_lines(
    db: Session,
    city_id: int,
    batch_id: int,
    *,
    site_validation_status: str | None = None,
    market: str | None = None,
    limit: int = 100,
) -> list[CpeFinanceLine]:
    query = (
        select(CpeFinanceLine)
        .join(CpeFinanceImportBatch, CpeFinanceLine.batch_id == CpeFinanceImportBatch.id)
        .where(CpeFinanceImportBatch.city_id == city_id, CpeFinanceLine.batch_id == batch_id)
        .options(selectinload(CpeFinanceLine.invoice), selectinload(CpeFinanceLine.cpe_site))
        .order_by(CpeFinanceLine.source_row_number, CpeFinanceLine.id)
        .limit(limit)
    )
    if site_validation_status:
        query = query.where(CpeFinanceLine.site_validation_status == site_validation_status)
    if market:
        query = query.where(CpeFinanceLine.market == market)
    return list(db.scalars(query).all())


def create_finance_batch_from_bytes(
    db: Session,
    city_id: int,
    uploaded_by_user_id: int,
    *,
    filename: str | None,
    content_type: str | None,
    data: bytes,
    target_contract_code: str = TARGET_CPE_CONTRACT_CODE,
) -> CpeFinanceImportBatch:
    if not data:
        raise ValueError("Fichier vide.")
    if Path(filename or "").suffix.lower() not in {".csv", ".txt"}:
        raise ValueError("Format finances DALKIA attendu : CSV ou TXT.")

    checksum = sha256(data).hexdigest()
    existing = db.scalars(
        select(CpeFinanceImportBatch)
        .where(
            CpeFinanceImportBatch.city_id == city_id,
            CpeFinanceImportBatch.sha256 == checksum,
            CpeFinanceImportBatch.target_contract_code == target_contract_code,
        )
        .options(*_load_batch_options())
        .order_by(CpeFinanceImportBatch.id.asc())
    ).first()
    if existing is not None:
        return existing

    rows = parse_finance_rows(data)
    imported_rows = [
        row for row in rows if row.contract_code == target_contract_code and row.market in CPE_FINANCE_MARKETS
    ]
    if not imported_rows:
        raise ValueError(
            f"Aucune ligne du contrat {target_contract_code} avec marche P1, P2 ou P3 dans cet export."
        )

    sites_by_code = _sites_by_code(db, city_id, imported_rows)
    batch = CpeFinanceImportBatch(
        city_id=city_id,
        uploaded_by_user_id=uploaded_by_user_id,
        original_filename=_safe_filename(filename),
        content_type=content_type,
        file_size_bytes=len(data),
        sha256=checksum,
        target_contract_code=target_contract_code,
        source_row_count=len(rows),
        imported_line_count=len(imported_rows),
        ignored_line_count=len(rows) - len(imported_rows),
    )
    db.add(batch)
    db.flush()

    invoices: dict[str, CpeFinanceInvoice] = {}
    for row in imported_rows:
        invoice_key = row.invoice_number or f"SANS-NUMERO-LIGNE-{row.source_row_number}"
        invoice = invoices.get(invoice_key)
        if invoice is None:
            invoice = _invoice_from_row(batch, row, invoice_key)
            invoices[invoice_key] = invoice
            db.add(invoice)
            db.flush()
        _append_line(batch, invoice, row, sites_by_code.get(row.detected_site_code))

    batch.invoice_count = len(invoices)
    batch.matched_site_line_count = sum(1 for line in batch.lines if line.site_validation_status == "auto_matched")
    batch.unknown_site_line_count = sum(1 for line in batch.lines if line.site_validation_status == "site_unknown")
    batch.missing_site_code_line_count = sum(
        1 for line in batch.lines if line.site_validation_status == "site_code_missing"
    )
    db.commit()
    db.refresh(batch)
    return get_finance_batch(db, city_id, batch.id) or batch


def finance_batch_detail(batch: CpeFinanceImportBatch) -> CpeFinanceImportBatchDetail:
    return CpeFinanceImportBatchDetail(
        **CpeFinanceImportBatchOut.model_validate(batch).model_dump(),
        invoices=batch.invoices,
        p1=_p1_summary(batch.lines),
    )


def _sites_by_code(db: Session, city_id: int, rows: list[DalkiaFinanceRow]) -> dict[str | None, CpeSite]:
    codes = {row.detected_site_code for row in rows if row.detected_site_code}
    if not codes:
        return {}
    sites = db.scalars(
        select(CpeSite).where(
            CpeSite.code_site.in_(codes),
            or_(CpeSite.city_id == city_id, CpeSite.city_id.is_(None)),
        )
    ).all()
    return {site.code_site: site for site in sites}


def _invoice_from_row(batch: CpeFinanceImportBatch, row: DalkiaFinanceRow, invoice_number: str) -> CpeFinanceInvoice:
    invoice = CpeFinanceInvoice(
        batch=batch,
        invoice_number=invoice_number,
        contract_code=row.contract_code,
        contract_label=row.contract_label or None,
        market_type=row.market_type or None,
        invoice_type=row.invoice_type or None,
        due_date=_parse_iso_date(row.invoice_due_date),
        issued_at=_parse_iso_date(row.issued_at),
        period_start=_parse_iso_date(row.period_start),
        period_end=_parse_iso_date(row.period_end),
        original_invoice_number=row.original_invoice_number or None,
        customer_code=row.customer_code or None,
        customer_name=row.customer_name or None,
        total_ht=0.0,
        line_count=0,
    )
    return invoice


def _append_line(
    batch: CpeFinanceImportBatch,
    invoice: CpeFinanceInvoice,
    row: DalkiaFinanceRow,
    matched_site: CpeSite | None,
) -> None:
    if matched_site is not None:
        status = "auto_matched"
    elif row.detected_site_code:
        status = "site_unknown"
    else:
        status = "site_code_missing"

    line = CpeFinanceLine(
        batch=batch,
        invoice=invoice,
        cpe_site=matched_site,
        source_row_number=row.source_row_number,
        market=row.market,
        sold_service=row.sold_service or None,
        billed_item=row.billed_item or None,
        amount_ht=float(row.amount_ht),
        vat_rate=_to_float(row.vat_rate),
        consumption=_to_float(row.consumption),
        consumption_unit=row.consumption_unit or None,
        prestation_detail=row.prestation_detail or None,
        customer_reference=row.customer_reference or None,
        recipient_reference=row.recipient_reference or None,
        base_price=_to_float(row.base_price),
        revised_price=_to_float(row.revised_price),
        reading_index_start=_to_float(row.reading_index_start),
        reading_index_end=_to_float(row.reading_index_end),
        reading_date_start=_parse_iso_date(row.reading_date_start),
        reading_date_end=_parse_iso_date(row.reading_date_end),
        reading_type=row.reading_type or None,
        detected_site_code=row.detected_site_code,
        site_validation_status=status,
        raw_payload_json=json.dumps(row.raw, ensure_ascii=True, sort_keys=True),
    )
    invoice.total_ht += line.amount_ht
    invoice.line_count += 1


@dataclass
class _Summary:
    amount: float = 0.0
    rows: int = 0
    invoices: set[str] = field(default_factory=set)

    def add(self, line: CpeFinanceLine) -> None:
        self.amount += line.amount_ht
        self.rows += 1
        self.invoices.add(line.invoice.invoice_number)


def _group_summary(code: str, summary: _Summary) -> CpeFinanceGroupSummary:
    return CpeFinanceGroupSummary(
        code=code or "Non renseigne",
        nb_lignes=summary.rows,
        nb_factures=len(summary.invoices),
        montant_ht=round(summary.amount, 2),
    )


def _p1_summary(lines: list[CpeFinanceLine]) -> CpeFinanceP1Summary:
    p1_lines = [line for line in lines if line.market == "P1"]
    invoice_numbers = {line.invoice.invoice_number for line in p1_lines}
    invoice_types: dict[str, _Summary] = defaultdict(_Summary)
    billed_items: dict[str, _Summary] = defaultdict(_Summary)
    matched_sites = {line.cpe_site for line in p1_lines if line.cpe_site is not None}

    for line in p1_lines:
        invoice_types[line.invoice.invoice_type or "Non renseigne"].add(line)
        billed_items[line.billed_item or "Non renseigne"].add(line)

    return CpeFinanceP1Summary(
        nb_lignes=len(p1_lines),
        nb_factures=len(invoice_numbers),
        montant_ht=round(sum(line.amount_ht for line in p1_lines), 2),
        types_facture=sorted(
            (_group_summary(code, summary) for code, summary in invoice_types.items()),
            key=lambda item: item.montant_ht,
            reverse=True,
        ),
        postes_factures=sorted(
            (_group_summary(code, summary) for code, summary in billed_items.items()),
            key=lambda item: item.montant_ht,
            reverse=True,
        ),
        nb_lignes_consommation=sum(1 for line in p1_lines if line.consumption is not None),
        nb_lignes_index_releve=sum(
            1 for line in p1_lines if line.reading_index_start is not None or line.reading_index_end is not None
        ),
        nb_sites_cpe_rapproches=len(matched_sites),
        nb_sites_cpe_avec_pce=sum(1 for site in matched_sites if site.pce),
        nb_lignes_site_a_reconcilier=sum(1 for line in p1_lines if line.cpe_site is None),
    )
