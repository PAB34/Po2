from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.billing import BillingBpuLine, BillingConfig
from app.models.invoice import EnergyInvoiceImport
from app.services.billing import _extract_tariff_code, ensure_default_bpu_lines
from app.services.energie import _contracts
from app.services.invoice_parsers.engie_pdf import parse_engie_pdf
from app.services.turpe import evaluate_invoice_turpe


PRICE_TOLERANCE_EUR_MWH = Decimal("0.05")
AMOUNT_TOLERANCE_EUR = Decimal("0.05")


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

    def issue(severity: str, code: str, message: str, scope: str = "document") -> None:
        issues.append({"severity": severity, "code": code, "message": message, "scope": scope})

    invoice = parsed.get("invoice", {})
    sites = parsed.get("sites", [])

    _check_document_identity(db, invoice_import, invoice, parsed, issue)
    _check_perimeter(sites, issue)
    _check_arithmetic(invoice, sites, issue)
    _check_bpu(db, invoice_import.city_id, parsed, issue, bpu_summary)
    _check_turpe(parsed, issue, turpe_summary)

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
            bpu_line = bpu_index.get((tariff_code, poste)) if poste else None
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
                    f"Prix BPU non renseigne pour {component_field} {tariff_code}/{poste}.",
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
                        f"{expected:.2f} EUR/MWh pour {tariff_code}/{poste}."
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


def _tariff_code_for_site(site: dict[str, Any]) -> str:
    label = site.get("tariff_option_label") or site.get("segment") or ""
    upper = label.upper()
    if "SEGMENT C4" in upper or site.get("segment") == "C4":
        return "C4"
    if ("SEGMENT C5" in upper or site.get("segment") == "C5") and "4 PLAGES" in upper:
        return "CU4"
    return _extract_tariff_code(label)


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
