from __future__ import annotations

import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from pypdf import PdfReader


FRENCH_MONTHS = {
    "janvier": 1,
    "fevrier": 2,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
    "décembre": 12,
}

FAMILY_LABELS = {
    "Electricite": "electricity",
    "Electricité": "electricity",
    "Acheminement electricite": "network",
    "Acheminement électricité": "network",
    "Vos services et autres prestations": "services",
    "Taxes et Contributions": "taxes",
}

DETAIL_HEADER_LINES = {
    "Periode de",
    "Période de",
    "consommation",
    "Conso.",
    "kWh/Qté",
    "kWh/Qte",
    "Prix unitaire",
    "(€ HT)",
    "(EUR HT)",
    "Montant HT",
    "(€)",
    "Taux",
    "de TVA",
}


def parse_engie_pdf(path: str | Path) -> dict[str, Any]:
    pdf_path = Path(path)
    pages = _extract_pages(pdf_path)
    text = "\n".join(page["text"] for page in pages)
    compact = _compact(text)

    if "ENGIE" not in compact.upper() or "Facture Unique Multi-Site" not in compact:
        raise ValueError("Le PDF ne ressemble pas a une facture ENGIE multi-site electricite.")

    invoice = _parse_invoice_header(pages[0]["text"] if pages else "", compact)
    fic_groups = _group_fic_pages(pages)
    sites = [_parse_fic_group(fic_number, group) for fic_number, group in fic_groups.items()]

    periods = [site for site in sites if site.get("period_start") and site.get("period_end")]
    if periods:
        invoice["period_start"] = min(site["period_start"] for site in periods)
        invoice["period_end"] = max(site["period_end"] for site in periods)

    unique_prms = {site.get("prm_id") for site in sites if site.get("prm_id")}

    return {
        "supplier": "ENGIE",
        "document_type": "facture_unique_multisite_electricite",
        "page_count": len(pages),
        "invoice": invoice,
        "sites": sites,
        "site_count": len(unique_prms),
        "fic_count": len(sites),
        "parser_warnings": _parser_warnings(invoice, sites),
    }


def _extract_pages(path: Path) -> list[dict[str, Any]]:
    reader = PdfReader(str(path))
    pages: list[dict[str, Any]] = []
    for index, page in enumerate(reader.pages, start=1):
        pages.append({"page_number": index, "text": page.extract_text() or ""})
    return pages


def _parse_invoice_header(first_page_text: str, compact: str) -> dict[str, Any]:
    invoice: dict[str, Any] = {}

    invoice_match = re.search(r"N°\s*([0-9 ]{6,})\s*-\s*([0-9]{1,2}\s+\w+\s+[0-9]{4})", compact)
    if invoice_match:
        invoice["invoice_number"] = _clean_spaces(invoice_match.group(1))
        invoice["invoice_date"] = _parse_french_date(invoice_match.group(2))

    invoice["global_customer_reference"] = _line_value(first_page_text, "Référence client")
    invoice["contract_holder"] = _line_value(first_page_text, "Titulaire du contrat")
    invoice["contract_siret"] = _line_value(first_page_text, "SIREN/SIRET contractant")
    invoice["market_reference"] = _line_value(first_page_text, "Référence du marché")
    invoice["regroupement"] = _line_value(first_page_text, "Regroupement")
    invoice["payment_method"] = _line_value(first_page_text, "Votre mode de paiement")
    invoice["chorus_ej"] = _line_value(first_page_text, "Numéro EJ")
    invoice["chorus_service_code"] = _line_value(first_page_text, "Code SE")

    payment_match = re.search(r"PRELEVE LE\s+([0-9]{1,2}\s+\w+\s+[0-9]{4})", compact, flags=re.IGNORECASE)
    if payment_match:
        invoice["payment_due_date"] = _parse_french_date(payment_match.group(1))

    total_match = re.search(r"MONTANT TTC à payer\*?\s+([0-9 ]+,[0-9]{2})\s*€", compact)
    if total_match:
        invoice["total_ttc"] = _decimal_to_float(_parse_decimal_fr(total_match.group(1)))

    consumption_match = re.search(r"Consommation totale d'électricité\s*:\s*([0-9 ]+,[0-9]+)\s*MWh", compact)
    if consumption_match:
        mwh = _parse_decimal_fr(consumption_match.group(1))
        invoice["total_consumption_mwh"] = _decimal_to_float(mwh)
        invoice["total_consumption_kwh"] = _decimal_to_float(mwh * Decimal("1000"))

    totals_patterns = {
        "supply_total_ht": r"Fourniture d'électricité\s+([0-9 ]+,[0-9]{2})\s*€",
        "network_total_ht": r"Acheminement\s+([0-9 ]+,[0-9]{2})\s*€",
        "taxes_total": r"Total taxe\s+([0-9 ]+,[0-9]{2})\s*€",
        "vat_total": r"Total TVA\s+([0-9 ]+,[0-9]{2})\s*€",
    }
    for key, pattern in totals_patterns.items():
        match = re.search(pattern, compact)
        if match:
            invoice[key] = _decimal_to_float(_parse_decimal_fr(match.group(1)))

    return invoice


def _group_fic_pages(pages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for page in pages:
        compact = _compact(page["text"])
        match = re.search(r"Fiche info conso\s+([0-9]+)", compact)
        if not match:
            continue
        fic_number = match.group(1)
        group = groups.setdefault(fic_number, {"fic_number": fic_number, "pages": [], "text_parts": []})
        group["pages"].append(page["page_number"])
        group["text_parts"].append(page["text"])
    return groups


def _parse_fic_group(fic_number: str, group: dict[str, Any]) -> dict[str, Any]:
    text = "\n".join(group["text_parts"])
    compact = _compact(text)
    site: dict[str, Any] = {
        "fic_number": fic_number,
        "pdf_page_start": min(group["pages"]),
        "pdf_page_end": max(group["pages"]),
    }

    site_match = re.search(r"Fiche info conso\s+[0-9]+\s+(.+?)\s+Regroupement\s*:", compact)
    if site_match:
        site["site_name"] = site_match.group(1).strip()

    regroupement_match = re.search(r"Regroupement\s*:\s*(.+?)\s+Consommation du", compact)
    if regroupement_match:
        site["regroupement"] = regroupement_match.group(1).strip()

    period_match = re.search(
        r"Consommation du\s+([0-9]{2}/[0-9]{2}/[0-9]{4})\s+au\s+([0-9]{2}/[0-9]{2}/[0-9]{4})",
        compact,
    )
    if period_match:
        site["period_start"] = _parse_numeric_date(period_match.group(1))
        site["period_end"] = _parse_numeric_date(period_match.group(2))

    site["local_customer_reference"] = _compact_value_match(compact, r"Votre référence client\s*:\s*([0-9 ]+)")
    site["contract_holder"] = _compact_value_match(compact, r"Titulaire du contrat\s*:\s*(.+?)\s+Date d'échéance")
    site["contract_end_date"] = _date_value_match(compact, r"Date d'échéance\s*:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})")
    site["offer"] = _compact_value_match(compact, r"Votre offre\s*:\s*(.+?)\s+Acheminement\s*:")
    site["tariff_option_label"] = _compact_value_match(compact, r"Acheminement\s*:\s*(.+?)\s+Votre point de livraison")
    site["segment"] = _compact_value_match(compact, r"Segment\s+(C[0-9])")
    site["prm_id"] = _compact_value_match(compact, r"PDL/PRM\s*:\s*([0-9]{14})")
    site["delivery_site_name"] = _compact_value_match(compact, r"Désignation du site\s*:\s*(.+?)\s+Adresse de livraison")
    site["delivery_address"] = _compact_value_match(compact, r"Adresse de livraison\s*:\s*(.+?)\s+Type de compteur")
    site["meter_type"] = _compact_value_match(compact, r"Type de compteur\s*:\s*(.+?)(?:\s+Numéro de compteur|\s+Suivez vos consommations)")
    site["meter_number"] = _compact_value_match(compact, r"Numéro de compteur\s*:\s*([0-9A-Z -]+?)\s+Suivez vos consommations")

    total_ht = _money_value_match(compact, r"Total HTVA\s+([0-9 ]+,[0-9]{2})\s*€")
    total_vat = _money_value_match(compact, r"Total TVA\s+[0-9.]+\s*%\s+([0-9 ]+,[0-9]{2})\s*€")
    total_ttc = _money_value_match(compact, r"Total TTC\s+([0-9 ]+,[0-9]{2})\s*€")
    if total_ht is not None:
        site["total_ht"] = total_ht
    if total_vat is not None:
        site["total_vat"] = total_vat
    if total_ttc is not None:
        site["total_ttc"] = total_ttc

    site["family_totals"], site["invoice_lines"] = _parse_detail_lines(text)
    site["meter_reads"], site["power_rows"], subscribed_power = _parse_meter_reads(text)
    if subscribed_power is not None:
        site["subscribed_power_kva"] = subscribed_power
    if site["power_rows"]:
        reached = [row.get("reached_power_kva") for row in site["power_rows"] if row.get("reached_power_kva") is not None]
        subscribed = [row.get("subscribed_power_kva") for row in site["power_rows"] if row.get("subscribed_power_kva") is not None]
        if reached:
            site["max_reached_power_kva"] = max(reached)
        if subscribed:
            site["subscribed_power_kva"] = max(subscribed)

    return site


def _parse_detail_lines(text: str) -> tuple[dict[str, float], list[dict[str, Any]]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    in_detail = False
    family: str | None = None
    family_totals: dict[str, float] = {}
    invoice_lines: list[dict[str, Any]] = []
    pending = ""

    for line in lines:
        if line == "Détail de votre facture":
            in_detail = True
            pending = ""
            continue
        if not in_detail:
            continue
        if line.startswith("Les montants de TVA"):
            break
        if line in DETAIL_HEADER_LINES:
            continue
        if line == "Espace Client Gratuit":
            pending = ""
            continue

        family_match = _match_family_total(line)
        if family_match:
            family = family_match["family"]
            family_totals[family] = family_match["amount"]
            pending = ""
            continue

        combined = f"{pending} {line}".strip() if pending else line
        parsed = _parse_invoice_line(combined, family)
        if parsed:
            invoice_lines.append(parsed)
            pending = ""
        else:
            pending = combined

    return family_totals, invoice_lines


def _match_family_total(line: str) -> dict[str, Any] | None:
    for label, family in FAMILY_LABELS.items():
        pattern = rf"^{re.escape(label)}\s+([0-9 ]+,[0-9]{{2}})$"
        match = re.match(pattern, line)
        if match:
            return {"family": family, "amount": _decimal_to_float(_parse_decimal_fr(match.group(1)))}
    return None


def _parse_invoice_line(line: str, family: str | None) -> dict[str, Any] | None:
    qty_match = re.match(
        r"^(?P<label>.+?)\s+(?P<qty>[0-9 ]+)\s+(?P<unit>[0-9]+,[0-9]{5})\s+(?P<amount>[0-9 ]+,[0-9]{2})\s+(?P<vat>[0-9]{1,2}\.0%)$",
        line,
    )
    amount_match = re.match(
        r"^(?P<label>.+?)\s+(?P<amount>[0-9 ]+,[0-9]{2})\s+(?P<vat>[0-9]{1,2}\.0%)$",
        line,
    )
    match = qty_match or amount_match
    if not match:
        return None

    label = _clean_spaces(match.group("label"))
    item: dict[str, Any] = {
        "family": family or "unknown",
        "label": label,
        "normalized_component": _normalized_component(family, label),
        "poste": _normalized_poste(label),
        "amount_ht": _decimal_to_float(_parse_decimal_fr(match.group("amount"))),
        "vat_rate": _parse_vat_rate(match.group("vat")),
        "raw_line": line,
    }

    period_match = re.search(r"du\s+([0-9]{2}/[0-9]{2}/[0-9]{2})\s+au\s+([0-9]{2}/[0-9]{2}/[0-9]{2})", label)
    if period_match:
        item["period_start"] = _parse_numeric_date(period_match.group(1))
        item["period_end"] = _parse_numeric_date(period_match.group(2))

    if qty_match:
        item["quantity"] = _decimal_to_float(_parse_decimal_fr(match.group("qty")))
        item["quantity_unit"] = "kWh"
        item["unit_price_ht"] = _decimal_to_float(_parse_decimal_fr(match.group("unit")))
        item["unit_price_unit"] = "EUR/kWh"

    return item


def _parse_meter_reads(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float | None]:
    meter_reads: list[dict[str, Any]] = []
    power_rows: list[dict[str, Any]] = []
    subscribed_power: float | None = None
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    simple_power_match = re.search(r"Puissance souscrite\s+([0-9]+(?:,[0-9]+)?)\s*kVA", _compact(text))
    if simple_power_match:
        subscribed_power = _decimal_to_float(_parse_decimal_fr(simple_power_match.group(1)))

    for line in lines:
        read_match = re.match(
            r"^(?P<poste>Base|HCSB|HCSH|HPSB|HPSH|Pointe)\s+(?P<meter>[0-9A-Z -]+)\s+"
            r"(?P<previous_date>[0-9]{2}/[0-9]{2})\s+(?P<previous_index>[0-9 ]+)\s+"
            r"(?P<current_date>[0-9]{2}/[0-9]{2})\s+(?P<current_index>[0-9 ]+)\s+"
            r"(?P<reading_type>[REA])\s+(?P<difference>[0-9 ]+)\s+(?P<energy>[0-9 ]+)$",
            line,
        )
        if read_match:
            meter_reads.append(
                {
                    "poste": _meter_poste_to_normalized(read_match.group("poste")),
                    "raw_poste": read_match.group("poste"),
                    "meter_number": read_match.group("meter").strip(),
                    "previous_read_date": read_match.group("previous_date"),
                    "previous_index": _decimal_to_float(_parse_decimal_fr(read_match.group("previous_index"))),
                    "current_read_date": read_match.group("current_date"),
                    "current_index": _decimal_to_float(_parse_decimal_fr(read_match.group("current_index"))),
                    "reading_type": read_match.group("reading_type"),
                    "difference": _decimal_to_float(_parse_decimal_fr(read_match.group("difference"))),
                    "energy_kwh": _decimal_to_float(_parse_decimal_fr(read_match.group("energy"))),
                    "raw_line": line,
                }
            )
            continue

        power_match = re.match(
            r"^(?P<poste>HCSB|HCSH|HPSB|HPSH|Pointe)\s+(?P<subscribed>[0-9]+(?:,[0-9]+)?)\s+(?P<reached>[0-9]+(?:,[0-9]+)?)$",
            line,
        )
        if power_match:
            power_rows.append(
                {
                    "poste": _meter_poste_to_normalized(power_match.group("poste")),
                    "raw_poste": power_match.group("poste"),
                    "subscribed_power_kva": _decimal_to_float(_parse_decimal_fr(power_match.group("subscribed"))),
                    "reached_power_kva": _decimal_to_float(_parse_decimal_fr(power_match.group("reached"))),
                    "raw_line": line,
                }
            )

    return meter_reads, power_rows, subscribed_power


def _parser_warnings(invoice: dict[str, Any], sites: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    if not sites:
        warnings.append("Aucune fiche info conso detectee.")
    if invoice.get("total_ttc") is None:
        warnings.append("Montant TTC global non detecte.")
    if not invoice.get("regroupement"):
        warnings.append("Regroupement non detecte sur la premiere page.")
    for site in sites:
        if not site.get("invoice_lines"):
            warnings.append(f"Aucune ligne detaillee detectee pour la FIC {site.get('fic_number')}.")
    return warnings


def _normalized_component(family: str | None, label: str) -> str:
    normalized = _strip_accents(label).lower()
    if family == "electricity":
        if "origine renouvelable" in normalized or "100% de la consommation" in normalized:
            return "green_energy"
        if "certificats d'economie" in normalized:
            return "cee"
        if "obligation capacite" in normalized:
            return "capacity"
        if normalized.startswith("consommation"):
            return "supply"
    if family == "network":
        if normalized.startswith("consommation"):
            return "network_variable"
        if "composante de comptage" in normalized:
            return "network_counting"
        if "composante de soutirage" in normalized:
            return "network_withdrawal"
        if "composante de gestion" in normalized:
            return "network_management"
    if family == "taxes":
        if "tarifaire d'acheminement" in normalized:
            return "cta"
        if "service public" in normalized:
            return "cspe"
    return "other"


def _normalized_poste(label: str) -> str | None:
    normalized = _strip_accents(label).lower()
    if "pointe" in normalized:
        return "pointe"
    if "hp saison haute" in normalized:
        return "hph"
    if "hc saison haute" in normalized:
        return "hch"
    if "hp saison basse" in normalized:
        return "hpe"
    if "hc saison basse" in normalized:
        return "hce"
    if "base" in normalized:
        return "base"
    return None


def _meter_poste_to_normalized(poste: str) -> str:
    return {
        "Base": "base",
        "HPSH": "hph",
        "HCSH": "hch",
        "HPSB": "hpe",
        "HCSB": "hce",
        "Pointe": "pointe",
    }.get(poste, poste.lower())


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _clean_spaces(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"\s+", " ", value).strip()


def _line_value(text: str, label: str) -> str | None:
    pattern = re.compile(rf"^{re.escape(label)}\s*:\s*(.+)$", flags=re.MULTILINE)
    match = pattern.search(text)
    return _clean_spaces(match.group(1)) if match else None


def _compact_value_match(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text)
    return _clean_spaces(match.group(1)) if match else None


def _date_value_match(text: str, pattern: str) -> date | None:
    match = re.search(pattern, text)
    return _parse_numeric_date(match.group(1)) if match else None


def _money_value_match(text: str, pattern: str) -> float | None:
    match = re.search(pattern, text)
    if not match:
        return None
    return _decimal_to_float(_parse_decimal_fr(match.group(1)))


def _parse_french_date(raw: str) -> date | None:
    parts = raw.strip().lower().split()
    if len(parts) != 3:
        return None
    day = int(parts[0])
    month = FRENCH_MONTHS.get(parts[1])
    year = int(parts[2])
    if month is None:
        return None
    return date(year, month, day)


def _parse_numeric_date(raw: str) -> date | None:
    parts = raw.strip().split("/")
    if len(parts) != 3:
        return None
    day = int(parts[0])
    month = int(parts[1])
    year = int(parts[2])
    if year < 100:
        year += 2000
    return date(year, month, day)


def _parse_decimal_fr(raw: str) -> Decimal:
    cleaned = raw.replace("\xa0", " ").replace(" ", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal("0")


def _decimal_to_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _parse_vat_rate(raw: str) -> float:
    return float(raw.replace("%", ""))


def _strip_accents(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", value) if unicodedata.category(char) != "Mn"
    )

