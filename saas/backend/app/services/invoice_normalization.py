from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.models.invoice import (
    EnergyInvoice,
    EnergyInvoiceCheck,
    EnergyInvoiceImport,
    EnergyInvoiceLine,
    EnergyInvoiceMeterRead,
    EnergyInvoicePeriod,
    EnergyInvoiceSite,
)


def replace_normalized_invoice(
    db: Session,
    invoice_import: EnergyInvoiceImport,
    parsed: dict[str, Any],
    control_report: dict[str, Any],
) -> EnergyInvoice:
    if invoice_import.normalized_invoice is not None:
        db.delete(invoice_import.normalized_invoice)
        db.flush()

    invoice_payload = _record(parsed.get("invoice"))
    invoice = EnergyInvoice(
        city_id=invoice_import.city_id,
        import_id=invoice_import.id,
        supplier=_string(parsed.get("supplier") or invoice_import.supplier_guess),
        energy_type=invoice_import.energy_type or "electricity",
        invoice_type=_string(parsed.get("document_type")),
        invoice_number=_string(invoice_payload.get("invoice_number") or invoice_import.invoice_number),
        invoice_date=_date(invoice_payload.get("invoice_date") or invoice_import.invoice_date),
        payment_due_date=_date(invoice_payload.get("payment_due_date")),
        payment_method=_string(invoice_payload.get("payment_method")),
        global_customer_reference=_string(invoice_payload.get("global_customer_reference")),
        contract_holder=_string(invoice_payload.get("contract_holder")),
        contract_siret=_string(invoice_payload.get("contract_siret")),
        market_reference=_string(invoice_payload.get("market_reference")),
        regroupement=_string(invoice_payload.get("regroupement") or invoice_import.regroupement),
        chorus_ej=_string(invoice_payload.get("chorus_ej")),
        chorus_service_code=_string(invoice_payload.get("chorus_service_code")),
        total_consumption_mwh=_number(invoice_payload.get("total_consumption_mwh")),
        total_ht=_number(invoice_payload.get("total_ht")),
        total_taxes=_number(invoice_payload.get("taxes_total")),
        total_vat=_number(invoice_payload.get("vat_total")),
        total_ttc=_number(invoice_payload.get("total_ttc") or invoice_import.total_ttc),
    )
    db.add(invoice)
    db.flush()

    site_index: dict[str, EnergyInvoiceSite] = {}
    for period_payload in _records(parsed.get("sites")):
        site = _site_for_period(invoice, site_index, period_payload)
        period = _build_period(period_payload)
        site.periods.append(period)
        _append_lines(period, period_payload.get("invoice_lines"))
        _append_meter_rows(period, period_payload.get("meter_reads"))
        _append_meter_rows(period, period_payload.get("power_rows"))
        _update_site_summary(site, period)

    for issue in _records(control_report.get("issues")):
        severity = _string(issue.get("severity"))
        code = _string(issue.get("code"))
        message = _string(issue.get("message"))
        if not severity or not code or not message:
            continue
        invoice.checks.append(
            EnergyInvoiceCheck(
                severity=severity,
                code=code,
                message=message,
                scope=_string(issue.get("scope")),
            )
        )

    db.flush()
    return invoice


def _site_for_period(
    invoice: EnergyInvoice,
    site_index: dict[str, EnergyInvoiceSite],
    payload: dict[str, Any],
) -> EnergyInvoiceSite:
    prm_id = _string(payload.get("prm_id"))
    fic_number = _string(payload.get("fic_number"))
    key = prm_id or f"fic:{fic_number or len(site_index) + 1}"
    current = site_index.get(key)
    if current is not None:
        return current

    current = EnergyInvoiceSite(
        prm_id=prm_id,
        site_name=_string(payload.get("delivery_site_name") or payload.get("site_name")),
        delivery_address=_string(payload.get("delivery_address")),
        meter_number=_string(payload.get("meter_number")),
        meter_type=_string(payload.get("meter_type")),
        local_customer_reference=_string(payload.get("local_customer_reference")),
        segment=_string(payload.get("segment")),
        tariff_option_label=_string(payload.get("tariff_option_label")),
        regroupement=_string(payload.get("regroupement") or invoice.regroupement),
    )
    invoice.sites.append(current)
    site_index[key] = current
    return current


def _build_period(payload: dict[str, Any]) -> EnergyInvoicePeriod:
    return EnergyInvoicePeriod(
        fic_number=_string(payload.get("fic_number")),
        period_start=_date(payload.get("period_start")),
        period_end=_date(payload.get("period_end")),
        pdf_page_start=_integer(payload.get("pdf_page_start")),
        pdf_page_end=_integer(payload.get("pdf_page_end")),
        total_ht=_number(payload.get("total_ht")),
        total_vat=_number(payload.get("total_vat")),
        total_ttc=_number(payload.get("total_ttc")),
        subscribed_power_kva=_number(payload.get("subscribed_power_kva")),
        max_reached_power_kva=_number(payload.get("max_reached_power_kva")),
    )


def _append_lines(period: EnergyInvoicePeriod, value: Any) -> None:
    for payload in _records(value):
        period.lines.append(
            EnergyInvoiceLine(
                family=_string(payload.get("family")),
                label=_string(payload.get("label")),
                normalized_code=_string(payload.get("normalized_code") or payload.get("normalized_component")),
                poste=_string(payload.get("poste")),
                period_start=_date(payload.get("period_start")),
                period_end=_date(payload.get("period_end")),
                quantity=_number(payload.get("quantity")),
                quantity_unit=_string(payload.get("quantity_unit")),
                unit_price_ht=_number(payload.get("unit_price_ht")),
                unit_price_unit=_string(payload.get("unit_price_unit")),
                amount_ht=_number(payload.get("amount_ht")),
                vat_rate=_number(payload.get("vat_rate")),
                raw_line=_string(payload.get("raw_line")),
            )
        )


def _append_meter_rows(period: EnergyInvoicePeriod, value: Any) -> None:
    for payload in _records(value):
        period.meter_reads.append(
            EnergyInvoiceMeterRead(
                period_code=_string(payload.get("period_code") or payload.get("poste")),
                meter_number=_string(payload.get("meter_number")),
                previous_read_date=_date(payload.get("previous_read_date")),
                previous_index=_number(payload.get("previous_index")),
                current_read_date=_date(payload.get("current_read_date")),
                current_index=_number(payload.get("current_index")),
                reading_type=_string(payload.get("reading_type")),
                difference=_number(payload.get("difference")),
                energy_kwh=_number(payload.get("energy_kwh")),
                subscribed_power_kva=_number(payload.get("subscribed_power_kva")),
                reached_power_kva=_number(payload.get("reached_power_kva")),
            )
        )


def _update_site_summary(site: EnergyInvoiceSite, period: EnergyInvoicePeriod) -> None:
    if period.period_start and (site.summary_period_start is None or period.period_start < site.summary_period_start):
        site.summary_period_start = period.period_start
    if period.period_end and (site.summary_period_end is None or period.period_end > site.summary_period_end):
        site.summary_period_end = period.period_end
    if period.total_ttc is not None:
        site.summary_total_ttc = (site.summary_total_ttc or 0) + period.total_ttc


def _record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _records(value: Any) -> Iterable[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _date(value: Any) -> date | None:
    # Le parser PDF produit des objets date ; le parser XLSX ENGIE produit des
    # chaines ISO (ex. "2026-03-10"). On accepte les deux pour que les periodes
    # normalisees (EnergyInvoicePeriod.period_start/end) soient renseignees.
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None
    return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _integer(value: Any) -> int | None:
    number = _number(value)
    return int(number) if number is not None else None
