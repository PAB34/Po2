from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.invoice import EnergyInvoiceImport
from app.services.invoice_parsers.engie_pdf import parse_engie_pdf

_TTC_TOLERANCE = 0.05


class PdfControlError(ValueError):
    """Raised when a supplier PDF cannot be controlled against Po2 data."""


class PlatformInvoiceNotFound(LookupError):
    """Raised when no imported invoice exists for the requested supplier number."""


def control_engie_supplier_pdf(
    db: Session,
    city_id: int,
    invoice_number: str,
    pdf_bytes: bytes,
    *,
    filename: str | None = None,
) -> dict[str, Any]:
    requested_number = (invoice_number or "").strip()
    if not requested_number:
        raise PdfControlError("Numero de facture fournisseur requis.")
    if not pdf_bytes:
        raise PdfControlError("PDF fournisseur vide.")

    platform_invoice = _find_engie_invoice(db, city_id, requested_number)
    if platform_invoice is None:
        raise PlatformInvoiceNotFound(f"Facture ENGIE {requested_number} absente de Po2 pour cette ville.")

    parsed_pdf = _parse_engie_pdf_bytes(pdf_bytes, filename=filename)
    return build_engie_pdf_control(platform_invoice, parsed_pdf, requested_number=requested_number)


def build_engie_pdf_control(
    platform_invoice: EnergyInvoiceImport,
    parsed_pdf: dict[str, Any],
    *,
    requested_number: str | None = None,
) -> dict[str, Any]:
    pdf_invoice = parsed_pdf.get("invoice") or {}
    pdf_number = _clean_number(pdf_invoice.get("invoice_number"))
    expected_number = _clean_number(requested_number or platform_invoice.invoice_number)
    if expected_number and pdf_number and pdf_number != expected_number:
        raise PdfControlError(
            f"Le PDF concerne la facture {pdf_number}, pas la facture {expected_number}."
        )

    platform_sites = _platform_sites(platform_invoice)
    pdf_sites = [_pdf_site(site) for site in parsed_pdf.get("sites") or []]
    platform_by_prm = {site["prm"]: site for site in platform_sites if site.get("prm")}
    pdf_by_prm = {site["prm"]: site for site in pdf_sites if site.get("prm")}

    missing_in_platform = [site for prm, site in pdf_by_prm.items() if prm not in platform_by_prm]
    missing_in_pdf = [site for prm, site in platform_by_prm.items() if prm not in pdf_by_prm]

    pdf_total = _round_money(pdf_invoice.get("total_ttc"))
    platform_total = _round_money(platform_invoice.total_ttc)
    total_delta = _money_delta(platform_total, pdf_total)
    pdf_sites_total = _round_money(sum((site.get("total_ttc") or 0.0) for site in pdf_sites)) if pdf_sites else None

    status = _status(total_delta, missing_in_platform, missing_in_pdf)
    diagnosis = _diagnosis(status, platform_total, pdf_total, missing_in_platform, missing_in_pdf)

    return {
        "supplier": "ENGIE",
        "invoice_number": expected_number or pdf_number or platform_invoice.invoice_number,
        "status": status,
        "diagnosis": diagnosis,
        "recommendation": _recommendation(status),
        "totals": {
            "pdf_total_ttc": pdf_total,
            "platform_total_ttc": platform_total,
            "delta_platform_minus_pdf": total_delta,
            "pdf_sites_total_ttc": pdf_sites_total,
        },
        "counts": {
            "pdf_sites_count": len(pdf_by_prm) or len(pdf_sites),
            "platform_sites_count": len(platform_by_prm) or len(platform_sites),
            "missing_in_platform_count": len(missing_in_platform),
            "missing_in_pdf_count": len(missing_in_pdf),
        },
        "missing_in_platform": missing_in_platform,
        "missing_in_pdf": missing_in_pdf,
        "pdf_sites": pdf_sites,
        "platform_sites": platform_sites,
        "parser_warnings": parsed_pdf.get("parser_warnings") or [],
    }


def _find_engie_invoice(db: Session, city_id: int, invoice_number: str) -> EnergyInvoiceImport | None:
    stmt = (
        select(EnergyInvoiceImport)
        .where(EnergyInvoiceImport.city_id == city_id)
        .where(EnergyInvoiceImport.invoice_number == invoice_number)
        .order_by(EnergyInvoiceImport.updated_at.desc(), EnergyInvoiceImport.id.desc())
    )
    for invoice in db.scalars(stmt).all():
        if _looks_like_engie(invoice):
            return invoice
    return None


def _parse_engie_pdf_bytes(pdf_bytes: bytes, *, filename: str | None) -> dict[str, Any]:
    suffix = Path(filename or "facture-engie.pdf").suffix.lower()
    if suffix != ".pdf":
        raise PdfControlError("Format attendu : PDF fournisseur ENGIE.")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = Path(tmp.name)
    try:
        return parse_engie_pdf(tmp_path)
    except Exception as exc:  # pragma: no cover - message API operateur
        raise PdfControlError(f"Lecture du PDF ENGIE impossible : {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)


def _platform_sites(invoice: EnergyInvoiceImport) -> list[dict[str, Any]]:
    normalized = invoice.normalized_invoice
    if normalized is None:
        return []
    sites: list[dict[str, Any]] = []
    for site in normalized.sites:
        prm = _clean_number(site.prm_id)
        total = _round_money(site.summary_total_ttc)
        if total is None:
            total = _round_money(sum((period.total_ttc or 0.0) for period in site.periods)) if site.periods else None
        sites.append(
            {
                "prm": prm,
                "site_name": site.site_name,
                "segment": site.segment,
                "total_ttc": total,
            }
        )
    return sites


def _pdf_site(site: dict[str, Any]) -> dict[str, Any]:
    return {
        "prm": _clean_number(site.get("prm_id")),
        "site_name": site.get("delivery_site_name") or site.get("site_name"),
        "segment": site.get("segment"),
        "fic_number": site.get("fic_number"),
        "total_ttc": _round_money(site.get("total_ttc")),
        "pdf_page_start": site.get("pdf_page_start"),
        "pdf_page_end": site.get("pdf_page_end"),
    }


def _status(
    total_delta: float | None,
    missing_in_platform: list[dict[str, Any]],
    missing_in_pdf: list[dict[str, Any]],
) -> str:
    if missing_in_platform:
        return "export_incomplet"
    if missing_in_pdf:
        return "po2_contient_plus_de_sites"
    if total_delta is not None and abs(total_delta) > _TTC_TOLERANCE:
        return "ecart_total_meme_perimetre"
    return "coherent"


def _diagnosis(
    status: str,
    platform_total: float | None,
    pdf_total: float | None,
    missing_in_platform: list[dict[str, Any]],
    missing_in_pdf: list[dict[str, Any]],
) -> str:
    if status == "export_incomplet":
        missing = _site_list(missing_in_platform)
        return (
            f"Le PDF fournisseur contient {len(missing_in_platform)} FIC/site absent(s) de Po2 : {missing}. "
            f"Total PDF { _money_label(pdf_total) }, total Po2 { _money_label(platform_total) }."
        )
    if status == "po2_contient_plus_de_sites":
        extra = _site_list(missing_in_pdf)
        return (
            f"Po2 contient {len(missing_in_pdf)} site(s) non retrouv?s dans le PDF : {extra}. "
            "Verifier que le bon PDF fournisseur a ete transmis."
        )
    if status == "ecart_total_meme_perimetre":
        return (
            "Le PDF et Po2 portent les memes PRM, mais le total TTC differe. "
            "Comparer les taxes, arrondis, avoirs ou lignes de regularisation."
        )
    return "Le PDF fournisseur et la facture Po2 sont coherents sur les PRM et le total TTC."


def _recommendation(status: str) -> str:
    if status == "export_incomplet":
        return "Reexporter/importer ENGIE avec toutes les FIC du bordereau, ou corriger l'import source avant validation comptable."
    if status == "po2_contient_plus_de_sites":
        return "Verifier que le PDF fournisseur correspond au meme numero de facture et au meme bordereau."
    if status == "ecart_total_meme_perimetre":
        return "Controler le detail des montants PDF vs export fournisseur avant validation."
    return "Aucune action corrective detectee par le controle PDF."


def _site_list(sites: list[dict[str, Any]]) -> str:
    parts = []
    for site in sites[:5]:
        label = site.get("site_name") or "site sans libelle"
        prm = site.get("prm") or "PRM inconnu"
        amount = _money_label(site.get("total_ttc"))
        parts.append(f"{label} ({prm}, {amount})")
    remaining = len(sites) - len(parts)
    if remaining > 0:
        parts.append(f"+{remaining} autre(s)")
    return " ; ".join(parts)


def _money_delta(platform_total: float | None, pdf_total: float | None) -> float | None:
    if platform_total is None or pdf_total is None:
        return None
    return round(platform_total - pdf_total, 2)


def _round_money(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _money_label(value: Any) -> str:
    amount = _round_money(value)
    return "inconnu" if amount is None else f"{amount:.2f} EUR TTC"


def _clean_number(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().replace(" ", "")
    return text or None


def _looks_like_engie(invoice: EnergyInvoiceImport) -> bool:
    value = " ".join([invoice.supplier_guess or "", invoice.source or "", invoice.original_filename or ""]).upper()
    return "ENGIE" in value


__all__ = [
    "PdfControlError",
    "PlatformInvoiceNotFound",
    "build_engie_pdf_control",
    "control_engie_supplier_pdf",
]
