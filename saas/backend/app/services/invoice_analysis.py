from __future__ import annotations

import json
import unicodedata
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.billing import BillingBpuLine, BillingConfig
from app.models.invoice import EnergyInvoiceImport
from app.services.billing import _extract_tariff_code, ensure_default_bpu_lines
from app.services.energie import _contracts, _daily_consumption_index, _load_curve_index, _max_power_index, _safe_float
from app.services.invoice_parsers.engie_pdf import parse_engie_pdf
from app.services.turpe import evaluate_invoice_turpe


PRICE_TOLERANCE_EUR_MWH = Decimal("0.05")
AMOUNT_TOLERANCE_EUR = Decimal("0.05")
TAX_TOTAL_TOLERANCE_EUR = Decimal("0.10")
VAT_RECALC_TOLERANCE_EUR = Decimal("0.50")
CONSUMPTION_TOLERANCE_RATIO = Decimal("0.05")
CONSUMPTION_TOLERANCE_KWH = Decimal("10")
MIN_ENEDIS_COVERAGE_RATIO = Decimal("0.80")
LOAD_CURVE_SLOT_HOURS = Decimal("0.5")
POWER_TOLERANCE_KVA = Decimal("0.10")
POWER_ENEDIS_TOLERANCE_KVA = Decimal("0.50")
POWER_LOAD_CURVE_TOLERANCE_KVA = Decimal("1.00")


BPU_POSTE_ALIASES: dict[tuple[str, str], list[tuple[str, str]]] = {
    ("CU4", "base"): [("CU", "base"), ("LU", "base")],
    ("MU4", "base"): [("CU", "base"), ("LU", "base")],
    ("C4", "pointe"): [("C4", "hph")],
    ("MUDT", "hph"): [("MUDT", "hp")],
    ("MUDT", "hpe"): [("MUDT", "hp")],
    ("MUDT", "hch"): [("MUDT", "hc")],
    ("MUDT", "hce"): [("MUDT", "hc")],
    ("CU", "hph"): [("CU", "base")],
    ("CU", "hpe"): [("CU", "base")],
    ("CU", "hch"): [("CU", "base")],
    ("CU", "hce"): [("CU", "base")],
    ("LU", "hph"): [("LU", "base")],
    ("LU", "hpe"): [("LU", "base")],
    ("LU", "hch"): [("LU", "base")],
    ("LU", "hce"): [("LU", "base")],
    ("EP", "hph"): [("EP", "base")],
    ("EP", "hpe"): [("EP", "base")],
    ("EP", "hch"): [("EP", "base")],
    ("EP", "hce"): [("EP", "base")],
    ("EP", "hp"): [("EP", "base")],
    ("EP", "hc"): [("EP", "base")],
}


def analyze_invoice_import(db: Session, invoice_import: EnergyInvoiceImport) -> EnergyInvoiceImport:
    invoice_import.error_message = None

    try:
        parsed = _parse_invoice_file(invoice_import)
        control_report = _build_control_report(db, invoice_import, parsed)
    except Exception as exc:
        invoice_import.analysis_status = "failed"
        invoice_import.control_status = "invalid"
        invoice_import.control_errors_count = 1
        invoice_import.control_warnings_count = 0
        invoice_import.error_message = str(exc)
        invoice_import.control_report_json = json.dumps(
            {
                "status": "invalid",
                "issues": [
                    {
                        "severity": "error",
                        "code": "PARSER_FAILED",
                        "message": f"Analyse impossible : {exc}",
                        "scope": "document",
                    }
                ],
            },
            ensure_ascii=False,
        )
        return invoice_import

    invoice = parsed.get("invoice", {})
    invoice_import.supplier_guess = parsed.get("supplier") or invoice_import.supplier_guess
    invoice_import.invoice_number = invoice.get("invoice_number")
    invoice_import.invoice_date = invoice.get("invoice_date")
    invoice_import.period_start = invoice.get("period_start")
    invoice_import.period_end = invoice.get("period_end")
    invoice_import.regroupement = invoice.get("regroupement")
    invoice_import.total_ttc = invoice.get("total_ttc")
    invoice_import.total_consumption_kwh = invoice.get("total_consumption_kwh")
    invoice_import.site_count = parsed.get("site_count")
    invoice_import.control_status = control_report["status"]
    invoice_import.control_errors_count = control_report["error_count"]
    invoice_import.control_warnings_count = control_report["warning_count"]
    invoice_import.analysis_status = "partial" if parsed.get("parser_warnings") else "parsed"
    invoice_import.analysis_result_json = json.dumps(_json_ready(parsed), ensure_ascii=False)
    invoice_import.control_report_json = json.dumps(_json_ready(control_report), ensure_ascii=False)
    return invoice_import


def _parse_invoice_file(invoice_import: EnergyInvoiceImport) -> dict[str, Any]:
    path = Path(invoice_import.storage_path)
    if path.suffix.lower() != ".pdf":
        raise ValueError("Seules les factures PDF ENGIE sont analysees dans cette premiere version.")
    return parse_engie_pdf(path)


def _build_control_report(
    db: Session,
    invoice_import: EnergyInvoiceImport,
    parsed: dict[str, Any],
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    bpu_summary = {"checked_lines": 0, "mismatches": 0, "missing_references": 0}
    turpe_summary: dict[str, Any] = {}
    taxes_summary = {"checked_sites": 0, "mismatches": 0, "missing_references": 0}
    period_summary = {"checked_sites": 0, "gaps": 0, "overlaps": 0, "missing_references": 0}
    consumption_summary = {"checked_sites": 0, "mismatches": 0, "missing_references": 0, "partial_references": 0}
    power_summary = {
        "checked_sites": 0,
        "overruns": 0,
        "mismatches": 0,
        "missing_references": 0,
        "load_curve_checks": 0,
        "max_power_checks": 0,
    }

    def issue(severity: str, code: str, message: str, scope: str = "document") -> None:
        issues.append({"severity": severity, "code": code, "message": message, "scope": scope})

    invoice = parsed.get("invoice", {})
    sites = parsed.get("sites", [])

    _check_document_identity(db, invoice_import, invoice, parsed, issue)
    _check_perimeter(sites, issue)
    _check_arithmetic(invoice, sites, issue)
    _check_bpu(db, invoice_import.city_id, parsed, issue, bpu_summary)
    _check_turpe(parsed, issue, turpe_summary)
    _check_tax_and_vat(invoice, sites, issue, taxes_summary)
    _check_period_continuity(db, invoice_import, sites, issue, period_summary)
    _check_consumption_against_enedis(sites, issue, consumption_summary)
    _check_power_controls(sites, issue, power_summary)

    error_count = sum(1 for item in issues if item["severity"] == "error")
    warning_count = sum(1 for item in issues if item["severity"] == "warning")
    status = "invalid" if error_count else "review" if warning_count else "valid"

    return {
        "status": status,
        "error_count": error_count,
        "warning_count": warning_count,
        "issues": issues,
        "bpu": bpu_summary,
        "turpe": turpe_summary,
        "taxes": taxes_summary,
        "periods": period_summary,
        "consumption": consumption_summary,
        "power": power_summary,
    }


def _check_document_identity(
    db: Session,
    invoice_import: EnergyInvoiceImport,
    invoice: dict[str, Any],
    parsed: dict[str, Any],
    issue,
) -> None:
    if parsed.get("supplier") != "ENGIE":
        issue("error", "SUPPLIER_UNKNOWN", "Fournisseur non reconnu comme ENGIE.")
    if not invoice.get("invoice_number"):
        issue("error", "MISSING_INVOICE_NUMBER", "Numero de facture absent.")
    if not invoice.get("invoice_date"):
        issue("error", "MISSING_INVOICE_DATE", "Date de facture absente.")
    if invoice.get("total_ttc") is None:
        issue("error", "MISSING_TOTAL_TTC", "Montant TTC global absent.")
    if not invoice.get("regroupement"):
        issue("error", "MISSING_REGROUPEMENT", "Regroupement absent.")
    if not invoice.get("chorus_ej") or not invoice.get("chorus_service_code"):
        issue("warning", "MISSING_CHORUS_DATA", "Donnees Chorus incompletes.")

    market_reference = invoice.get("market_reference")
    if not market_reference:
        issue("error", "MISSING_MARKET_REFERENCE", "Reference marche absente.")
    elif market_reference != "2024-FCS-03":
        issue("error", "MARKET_REFERENCE_MISMATCH", f"Reference marche inattendue : {market_reference}.")

    invoice_number = invoice.get("invoice_number")
    if invoice_number:
        duplicate = (
            db.query(EnergyInvoiceImport.id)
            .filter(EnergyInvoiceImport.city_id == invoice_import.city_id)
            .filter(EnergyInvoiceImport.id != invoice_import.id)
            .filter(EnergyInvoiceImport.invoice_number == invoice_number)
            .first()
        )
        if duplicate:
            issue("error", "DUPLICATE_INVOICE_NUMBER", f"Numero de facture deja importe : {invoice_number}.")


def _check_perimeter(sites: list[dict[str, Any]], issue) -> None:
    contracts = _contracts()
    if not sites:
        issue("error", "NO_SITE_FOUND", "Aucun PRM/FIC detecte dans la facture.")
        return

    for site in sites:
        fic = site.get("fic_number") or "FIC inconnue"
        prm_id = site.get("prm_id")
        if not prm_id:
            issue("error", "MISSING_PRM", f"PRM absent sur {fic}.", fic)
            continue
        if prm_id not in contracts:
            issue("error", "UNKNOWN_PRM", f"PRM inconnu dans les donnees energie : {prm_id}.", prm_id)
            continue
        contractor = (contracts[prm_id].get("0_contractor") or "").upper()
        if contractor and "ENGIE" not in contractor:
            issue(
                "warning",
                "SUPPLIER_CONTRACT_MISMATCH",
                f"Le PRM {prm_id} est rattache a un fournisseur ENEDIS different : {contracts[prm_id].get('0_contractor')}.",
                prm_id,
            )


def _check_arithmetic(invoice: dict[str, Any], sites: list[dict[str, Any]], issue) -> None:
    total_ttc = _decimal(invoice.get("total_ttc"))
    fic_totals = [_decimal(site.get("total_ttc")) for site in sites if site.get("total_ttc") is not None]
    if total_ttc is not None and fic_totals:
        fic_sum = sum(fic_totals, Decimal("0"))
        delta = abs(fic_sum - total_ttc)
        if delta > AMOUNT_TOLERANCE_EUR:
            issue(
                "error",
                "TOTAL_TTC_MISMATCH",
                f"Somme des FIC ({fic_sum:.2f} EUR) differente du total facture ({total_ttc:.2f} EUR).",
            )

    for site in sites:
        scope = site.get("prm_id") or site.get("fic_number") or "fic"
        for line in site.get("invoice_lines", []):
            quantity = _decimal(line.get("quantity"))
            unit_price = _decimal(line.get("unit_price_ht"))
            amount = _decimal(line.get("amount_ht"))
            if quantity is None or unit_price is None or amount is None:
                continue
            expected = quantity * unit_price
            if abs(expected - amount) > AMOUNT_TOLERANCE_EUR:
                issue(
                    "error",
                    "LINE_AMOUNT_MISMATCH",
                    f"Ligne incoherente sur {scope}: {quantity} x {unit_price} = {expected:.2f}, facture {amount:.2f}.",
                    scope,
                )


def _check_bpu(
    db: Session,
    city_id: int,
    parsed: dict[str, Any],
    issue,
    bpu_summary: dict[str, int],
) -> None:
    configs = db.query(BillingConfig).filter(BillingConfig.city_id == city_id).all()
    engie_configs = [cfg for cfg in configs if "ENGIE" in (cfg.supplier or "").upper()]
    if not engie_configs:
        issue("warning", "BPU_CONFIG_MISSING", "Aucune configuration BPU ENGIE trouvee pour controler les prix.")
        return

    seeded = False
    for cfg in engie_configs:
        seeded = ensure_default_bpu_lines(db, cfg) or seeded
    if seeded:
        db.flush()

    bpu_lines = (
        db.query(BillingBpuLine)
        .filter(BillingBpuLine.config_id.in_([cfg.id for cfg in engie_configs]))
        .all()
    )
    bpu_index = {(line.tariff_code, line.poste): line for line in bpu_lines}
    if not bpu_index:
        issue("warning", "BPU_LINES_MISSING", "Configuration ENGIE presente mais aucune ligne BPU disponible.")
        return

    for site in parsed.get("sites", []):
        tariff_code = _tariff_code_for_site(site)
        scope = site.get("prm_id") or site.get("fic_number") or "fic"
        for line in site.get("invoice_lines", []):
            component_field = _bpu_component_field(line.get("normalized_component"))
            if component_field is None or line.get("unit_price_ht") is None:
                continue

            poste = line.get("poste") or _first_poste_for_tariff(bpu_index, tariff_code)
            bpu_line = _find_bpu_line_for_invoice_line(bpu_index, site, line, tariff_code, poste)
            if bpu_line is None:
                bpu_summary["missing_references"] += 1
                issue(
                    "warning",
                    "BPU_REFERENCE_MISSING",
                    f"Aucune ligne BPU pour {tariff_code}/{poste or 'sans poste'} sur {scope}.",
                    scope,
                )
                continue

            expected_value = getattr(bpu_line, component_field)
            if expected_value is None:
                bpu_summary["missing_references"] += 1
                issue(
                    "warning",
                    "BPU_PRICE_MISSING",
                    f"Prix BPU non renseigne pour {component_field} {bpu_line.tariff_code}/{bpu_line.poste}.",
                    scope,
                )
                continue

            bpu_summary["checked_lines"] += 1
            invoice_value_mwh = _decimal(line["unit_price_ht"]) * Decimal("1000")
            expected = _decimal(expected_value)
            if expected is None:
                continue
            delta = abs(invoice_value_mwh - expected)
            if delta > PRICE_TOLERANCE_EUR_MWH:
                bpu_summary["mismatches"] += 1
                issue(
                    "error",
                    "BPU_PRICE_MISMATCH",
                    (
                        f"Prix facture {invoice_value_mwh:.2f} EUR/MWh different du BPU "
                        f"{expected:.2f} EUR/MWh pour {bpu_line.tariff_code}/{bpu_line.poste}."
                    ),
                    scope,
                )


def _check_turpe(parsed: dict[str, Any], issue, turpe_summary: dict[str, Any]) -> None:
    report = evaluate_invoice_turpe(parsed)
    turpe_summary.update(report["summary"])
    for item in report["issues"]:
        issue(
            item.get("severity", "warning"),
            item.get("code", "TURPE_CONTROL"),
            item.get("message", "Controle TURPE incomplet."),
            item.get("scope") or "document",
        )


def _check_tax_and_vat(
    invoice: dict[str, Any],
    sites: list[dict[str, Any]],
    issue,
    taxes_summary: dict[str, int],
) -> None:
    site_vat_total = Decimal("0")
    site_vat_count = 0

    for site in sites:
        scope = site.get("prm_id") or site.get("fic_number") or "fic"
        total_ht = _decimal(site.get("total_ht"))
        total_vat = _decimal(site.get("total_vat"))
        total_ttc = _decimal(site.get("total_ttc"))
        if total_ht is None or total_vat is None or total_ttc is None:
            taxes_summary["missing_references"] += 1
            issue("warning", "TAX_TOTALS_MISSING", f"Totaux HT/TVA/TTC incomplets sur {scope}.", scope)
            continue

        taxes_summary["checked_sites"] += 1
        site_vat_total += total_vat
        site_vat_count += 1

        if abs(total_ht + total_vat - total_ttc) > TAX_TOTAL_TOLERANCE_EUR:
            taxes_summary["mismatches"] += 1
            issue(
                "error",
                "VAT_TOTAL_MISMATCH",
                f"Total HT + TVA different du TTC sur {scope}: attendu {(total_ht + total_vat):.2f} EUR, facture {total_ttc:.2f} EUR.",
                scope,
            )

        line_vat = Decimal("0")
        has_line_vat = False
        for line in site.get("invoice_lines", []):
            amount = _decimal(line.get("amount_ht"))
            vat_rate = _decimal(line.get("vat_rate"))
            if amount is None or vat_rate is None:
                continue
            has_line_vat = True
            line_vat += amount * vat_rate / Decimal("100")
        if has_line_vat and abs(line_vat - total_vat) > VAT_RECALC_TOLERANCE_EUR:
            taxes_summary["mismatches"] += 1
            issue(
                "error",
                "VAT_RECALC_MISMATCH",
                f"TVA recalculée depuis les lignes ({line_vat:.2f} EUR) differente de la TVA facturee ({total_vat:.2f} EUR) sur {scope}.",
                scope,
            )

        family_totals = site.get("family_totals") or {}
        if family_totals:
            family_total = sum((_decimal(value) or Decimal("0")) for value in family_totals.values())
            if abs(family_total - total_ht) > TAX_TOTAL_TOLERANCE_EUR:
                taxes_summary["mismatches"] += 1
                issue(
                    "error",
                    "HT_TOTAL_MISMATCH",
                    f"Somme des familles HT ({family_total:.2f} EUR) differente du total HT ({total_ht:.2f} EUR) sur {scope}.",
                    scope,
                )

    invoice_vat = _decimal(invoice.get("vat_total"))
    if invoice_vat is not None and site_vat_count and abs(invoice_vat - site_vat_total) > TAX_TOTAL_TOLERANCE_EUR:
        taxes_summary["mismatches"] += 1
        issue(
            "error",
            "INVOICE_VAT_TOTAL_MISMATCH",
            f"TVA globale ({invoice_vat:.2f} EUR) differente de la somme des FIC ({site_vat_total:.2f} EUR).",
        )


def _check_period_continuity(
    db: Session,
    invoice_import: EnergyInvoiceImport,
    sites: list[dict[str, Any]],
    issue,
    period_summary: dict[str, int],
) -> None:
    current_periods: list[tuple[str, date, date]] = []
    for site in sites:
        scope = site.get("prm_id") or site.get("fic_number") or "fic"
        prm_id = site.get("prm_id")
        start = _date_value(site.get("period_start"))
        end = _date_value(site.get("period_end"))
        if not prm_id or start is None or end is None:
            period_summary["missing_references"] += 1
            issue("warning", "PERIOD_MISSING", f"Periode facturee incomplete sur {scope}.", scope)
            continue
        if end < start:
            period_summary["missing_references"] += 1
            issue("error", "PERIOD_INVALID", f"Periode facturee incoherente sur {scope}: fin avant debut.", scope)
            continue
        period_summary["checked_sites"] += 1
        current_periods.append((prm_id, start, end))

        for line in site.get("invoice_lines", []):
            line_start = _date_value(line.get("period_start"))
            line_end = _date_value(line.get("period_end"))
            if line_start is None or line_end is None:
                continue
            if line_start < start or line_end > end:
                period_summary["missing_references"] += 1
                issue(
                    "warning",
                    "LINE_PERIOD_OUTSIDE_SITE_PERIOD",
                    f"Ligne facturee hors periode FIC sur {scope}: {line_start.isoformat()} - {line_end.isoformat()}.",
                    scope,
                )

    if not current_periods:
        return

    previous_by_prm: dict[str, list[tuple[date, date, str]]] = {}
    previous_imports = (
        db.query(EnergyInvoiceImport)
        .filter(EnergyInvoiceImport.city_id == invoice_import.city_id)
        .filter(EnergyInvoiceImport.id != invoice_import.id)
        .filter(EnergyInvoiceImport.analysis_result_json.isnot(None))
        .all()
    )
    for previous in previous_imports:
        label = previous.invoice_number or previous.original_filename
        for previous_site in _iter_import_sites(previous):
            prm_id = previous_site.get("prm_id")
            start = _date_value(previous_site.get("period_start"))
            end = _date_value(previous_site.get("period_end"))
            if prm_id and start and end:
                previous_by_prm.setdefault(prm_id, []).append((start, end, label))

    for prm_id, start, end in current_periods:
        previous_periods = sorted(previous_by_prm.get(prm_id, []), key=lambda item: item[1])
        previous_before = [period for period in previous_periods if period[1] < start]
        if previous_before:
            previous_start, previous_end, previous_label = previous_before[-1]
            expected_start = previous_end + timedelta(days=1)
            if start > expected_start:
                period_summary["gaps"] += 1
                issue(
                    "warning",
                    "PERIOD_GAP",
                    f"Trou de facturation detecte sur {prm_id}: precedente fin {previous_end.isoformat()} ({previous_label}), nouvelle debut {start.isoformat()}.",
                    prm_id,
                )

        for previous_start, previous_end, previous_label in previous_periods:
            if previous_start <= end and previous_end >= start:
                period_summary["overlaps"] += 1
                issue(
                    "warning",
                    "PERIOD_OVERLAP",
                    f"Chevauchement de periode sur {prm_id} avec {previous_label}: {previous_start.isoformat()} - {previous_end.isoformat()}.",
                    prm_id,
                )
                break


def _check_consumption_against_enedis(
    sites: list[dict[str, Any]],
    issue,
    consumption_summary: dict[str, int],
) -> None:
    daily_consumption = _daily_consumption_index()
    load_curve = _load_curve_index()

    for site in sites:
        scope = site.get("prm_id") or site.get("fic_number") or "fic"
        prm_id = site.get("prm_id")
        start = _date_value(site.get("period_start"))
        end = _date_value(site.get("period_end"))
        invoice_kwh = _invoice_site_consumption_kwh(site)
        if not prm_id or start is None or end is None or invoice_kwh is None:
            consumption_summary["missing_references"] += 1
            issue("warning", "CONSUMPTION_REFERENCE_MISSING", f"Consommation facturee ou periode incomplete sur {scope}.", scope)
            continue

        load_curve_metrics = _load_curve_metrics(load_curve.get(prm_id, []), start, end)
        if load_curve_metrics is not None and load_curve_metrics["coverage_ratio"] >= MIN_ENEDIS_COVERAGE_RATIO:
            consumption_summary["checked_sites"] += 1
            enedis_kwh = load_curve_metrics["energy_kwh"]
            tolerance = max(CONSUMPTION_TOLERANCE_KWH, invoice_kwh * CONSUMPTION_TOLERANCE_RATIO)
            delta = abs(invoice_kwh - enedis_kwh)
            if delta > tolerance:
                consumption_summary["mismatches"] += 1
                issue(
                    "warning",
                    "CONSUMPTION_LOAD_CURVE_MISMATCH",
                    (
                        f"Consommation facturee {invoice_kwh:.1f} kWh differente de la courbe de charge "
                        f"{enedis_kwh:.1f} kWh sur {scope} (ecart {delta:.1f} kWh)."
                    ),
                    scope,
                )
            continue

        if load_curve_metrics is not None:
            consumption_summary["partial_references"] += 1
            issue(
                "warning",
                "LOAD_CURVE_CONSUMPTION_PARTIAL",
                (
                    f"Courbe de charge partielle pour controler la consommation sur {scope}: "
                    f"{load_curve_metrics['covered_slots']}/{load_curve_metrics['expected_slots']} pas 30 min."
                ),
                scope,
            )

        points = [
            point
            for point in daily_consumption.get(prm_id, [])
            if start.isoformat() <= point.get("date", "") <= end.isoformat()
        ]
        expected_days = max(1, (end - start).days + 1)
        covered_days = len({point["date"] for point in points})
        if not points:
            consumption_summary["missing_references"] += 1
            issue("warning", "ENEDIS_CONSUMPTION_MISSING", f"Aucune consommation ENEDIS disponible sur la periode facturee pour {scope}.", scope)
            continue

        enedis_kwh = sum(Decimal(str(point["value_wh"])) for point in points) / Decimal("1000")
        coverage_ratio = Decimal(covered_days) / Decimal(expected_days)
        if coverage_ratio < MIN_ENEDIS_COVERAGE_RATIO:
            consumption_summary["partial_references"] += 1
            issue(
                "warning",
                "ENEDIS_CONSUMPTION_PARTIAL",
                f"Consommation ENEDIS partielle sur {scope}: {covered_days}/{expected_days} jour(s).",
                scope,
            )
            continue

        consumption_summary["checked_sites"] += 1
        tolerance = max(CONSUMPTION_TOLERANCE_KWH, invoice_kwh * CONSUMPTION_TOLERANCE_RATIO)
        delta = abs(invoice_kwh - enedis_kwh)
        if delta > tolerance:
            consumption_summary["mismatches"] += 1
            issue(
                "warning",
                "CONSUMPTION_ENEDIS_MISMATCH",
                f"Consommation facturee {invoice_kwh:.1f} kWh differente d'ENEDIS {enedis_kwh:.1f} kWh sur {scope} (ecart {delta:.1f} kWh).",
                scope,
            )


def _check_power_controls(
    sites: list[dict[str, Any]],
    issue,
    power_summary: dict[str, int],
) -> None:
    contracts = _contracts()
    max_power = _max_power_index()
    load_curve = _load_curve_index()

    for site in sites:
        scope = site.get("prm_id") or site.get("fic_number") or "fic"
        prm_id = site.get("prm_id")
        start = _date_value(site.get("period_start"))
        end = _date_value(site.get("period_end"))
        invoice_subscribed = _decimal(site.get("subscribed_power_kva"))
        invoice_reached = _decimal(site.get("max_reached_power_kva"))
        contract_subscribed = _decimal(_safe_float((contracts.get(prm_id) or {}).get("0_subscribed_power_value")) if prm_id else None)

        if prm_id is None or start is None or end is None:
            power_summary["missing_references"] += 1
            issue("warning", "POWER_REFERENCE_MISSING", f"PRM ou periode absent pour controler la puissance sur {scope}.", scope)
            continue

        checked = False
        if invoice_subscribed is None:
            power_summary["missing_references"] += 1
            issue("warning", "SUBSCRIBED_POWER_MISSING", f"Puissance souscrite absente de la facture sur {scope}.", scope)
        elif contract_subscribed is not None:
            checked = True
            if abs(invoice_subscribed - contract_subscribed) > POWER_TOLERANCE_KVA:
                power_summary["mismatches"] += 1
                issue(
                    "warning",
                    "SUBSCRIBED_POWER_CONTRACT_MISMATCH",
                    f"Puissance souscrite facture {invoice_subscribed:.1f} kVA differente du contrat ENEDIS {contract_subscribed:.1f} kVA sur {scope}.",
                    scope,
                )

        if invoice_reached is not None and invoice_subscribed is not None:
            checked = True
            if invoice_reached > invoice_subscribed + POWER_TOLERANCE_KVA:
                power_summary["overruns"] += 1
                issue(
                    "warning",
                    "POWER_OVERRUN",
                    f"Puissance atteinte {invoice_reached:.1f} kVA superieure a la puissance souscrite {invoice_subscribed:.1f} kVA sur {scope}.",
                    scope,
                )

        billed_overrun = _billed_power_overrun_amount(site)
        if billed_overrun > Decimal("0"):
            power_summary["overruns"] += 1
            issue("warning", "POWER_OVERRUN_BILLED", f"Depassement de puissance facture sur {scope}: {billed_overrun:.2f} EUR HT.", scope)

        load_curve_metrics = _load_curve_metrics(load_curve.get(prm_id, []), start, end)
        if load_curve_metrics is not None and load_curve_metrics["coverage_ratio"] >= MIN_ENEDIS_COVERAGE_RATIO:
            power_summary["load_curve_checks"] += 1
            enedis_peak = load_curve_metrics["peak_kva"]
            if invoice_reached is not None:
                checked = True
                delta = abs(invoice_reached - enedis_peak)
                if delta > POWER_LOAD_CURVE_TOLERANCE_KVA:
                    power_summary["mismatches"] += 1
                    issue(
                        "warning",
                        "POWER_LOAD_CURVE_MISMATCH",
                        f"Puissance atteinte facture {invoice_reached:.1f} kVA differente du pic courbe de charge {enedis_peak:.1f} kVA sur {scope}.",
                        scope,
                    )
            elif invoice_subscribed is not None and enedis_peak > invoice_subscribed + POWER_TOLERANCE_KVA:
                power_summary["overruns"] += 1
                issue(
                    "warning",
                    "POWER_LOAD_CURVE_OVERRUN",
                    f"Pic courbe de charge {enedis_peak:.1f} kVA superieur a la puissance souscrite {invoice_subscribed:.1f} kVA sur {scope}.",
                    scope,
                )
        else:
            if load_curve_metrics is not None:
                power_summary["missing_references"] += 1
                issue(
                    "warning",
                    "LOAD_CURVE_POWER_PARTIAL",
                    (
                        f"Courbe de charge partielle sur {scope}: "
                        f"{load_curve_metrics['covered_slots']}/{load_curve_metrics['expected_slots']} pas 30 min."
                    ),
                    scope,
                )
            selected_power_points = [
                point
                for point in max_power.get(prm_id, [])
                if start.isoformat() <= point.get("date", "") <= end.isoformat()
            ]
            if selected_power_points:
                power_summary["max_power_checks"] += 1
                enedis_peak = max(Decimal(str(point["value_va"])) for point in selected_power_points) / Decimal("1000")
                if invoice_reached is not None:
                    checked = True
                    delta = abs(invoice_reached - enedis_peak)
                    if delta > POWER_ENEDIS_TOLERANCE_KVA:
                        power_summary["mismatches"] += 1
                        issue(
                            "warning",
                            "POWER_ENEDIS_MISMATCH",
                            f"Puissance atteinte facture {invoice_reached:.1f} kVA differente du max ENEDIS {enedis_peak:.1f} kVA sur {scope}.",
                            scope,
                        )
                elif invoice_subscribed is not None and enedis_peak > invoice_subscribed + POWER_TOLERANCE_KVA:
                    power_summary["overruns"] += 1
                    issue(
                        "warning",
                        "POWER_ENEDIS_OVERRUN",
                        f"Max ENEDIS {enedis_peak:.1f} kVA superieur a la puissance souscrite {invoice_subscribed:.1f} kVA sur {scope}.",
                        scope,
                    )
            else:
                power_summary["missing_references"] += 1
                issue(
                    "warning",
                    "ENEDIS_POWER_MISSING",
                    f"Aucune courbe de charge ni puissance max ENEDIS disponible sur la periode facturee pour {scope}.",
                    scope,
                )

        if checked:
            power_summary["checked_sites"] += 1


def _tariff_code_for_site(site: dict[str, Any]) -> str:
    label = site.get("tariff_option_label") or site.get("segment") or ""
    upper = label.upper()
    extracted = _extract_tariff_code(label)
    if "SEGMENT C4" in upper or site.get("segment") == "C4":
        return "C4"
    if ("SEGMENT C5" in upper or site.get("segment") == "C5") and "4 PLAGES" in upper:
        if extracted in {"CU4", "MU4"}:
            return extracted
        return "CU4"
    return extracted


def _bpu_component_field(component: str | None) -> str | None:
    return {
        "supply": "pu_fourniture",
        "capacity": "pu_capacite",
        "cee": "pu_cee",
        "green_energy": "pu_go",
    }.get(component or "")


def _first_poste_for_tariff(bpu_index: dict[tuple[str, str], BillingBpuLine], tariff_code: str) -> str | None:
    for code, poste in bpu_index:
        if code == tariff_code:
            return poste
    return None


def _find_bpu_line_for_invoice_line(
    bpu_index: dict[tuple[str, str], BillingBpuLine],
    site: dict[str, Any],
    line: dict[str, Any],
    tariff_code: str,
    poste: str | None,
) -> BillingBpuLine | None:
    for candidate in _bpu_candidate_keys(tariff_code, poste):
        if candidate in bpu_index:
            return bpu_index[candidate]

    return None


def _bpu_candidate_keys(tariff_code: str, poste: str | None) -> list[tuple[str, str]]:
    if not poste:
        return []
    candidates = [(tariff_code, poste)]
    candidates.extend(BPU_POSTE_ALIASES.get((tariff_code, poste), []))
    return candidates


def _iter_import_sites(invoice_import: EnergyInvoiceImport) -> list[dict[str, Any]]:
    parsed = invoice_import.analysis_result
    if not parsed:
        return []
    sites = parsed.get("sites")
    return sites if isinstance(sites, list) else []


def _date_value(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _invoice_site_consumption_kwh(site: dict[str, Any]) -> Decimal | None:
    total = Decimal("0")
    has_consumption = False
    for line in site.get("invoice_lines", []):
        if line.get("normalized_component") not in {"supply", "network_variable"}:
            continue
        quantity = _decimal(line.get("quantity"))
        if quantity is None:
            continue
        has_consumption = True
        total += quantity
    if has_consumption:
        return total

    total_from_reads = Decimal("0")
    has_reads = False
    for read in site.get("meter_reads", []):
        energy = _decimal(read.get("energy_kwh"))
        if energy is not None:
            has_reads = True
            total_from_reads += energy
    return total_from_reads if has_reads else None


def _billed_power_overrun_amount(site: dict[str, Any]) -> Decimal:
    total = Decimal("0")
    for line in site.get("invoice_lines", []):
        normalized = _strip_accents(str(line.get("label") or line.get("raw_line") or "")).lower()
        if "depassement" not in normalized or "puissance" not in normalized:
            continue
        amount = _decimal(line.get("amount_ht"))
        if amount is not None:
            total += amount
    return total


def _load_curve_metrics(points: list[dict[str, Any]], start: date, end: date) -> dict[str, Any] | None:
    selected = [
        point
        for point in points
        if start.isoformat() <= str(point.get("datetime", ""))[:10] <= end.isoformat()
    ]
    if not selected:
        return None

    expected_slots = max(1, (end - start).days + 1) * 48
    covered_slots = len({str(point.get("datetime")) for point in selected if point.get("datetime")})
    peak_kva = max(Decimal(str(point["value_w"])) for point in selected) / Decimal("1000")
    energy_kwh = sum(Decimal(str(point["value_w"])) * LOAD_CURVE_SLOT_HOURS for point in selected) / Decimal("1000")
    return {
        "peak_kva": peak_kva,
        "energy_kwh": energy_kwh,
        "covered_slots": covered_slots,
        "expected_slots": expected_slots,
        "coverage_ratio": Decimal(covered_slots) / Decimal(expected_slots),
    }


def _strip_accents(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFD", value) if unicodedata.category(char) != "Mn")


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, date):
        return value.isoformat()
    return value
