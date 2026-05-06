from __future__ import annotations

import unicodedata
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Callable


CENT = Decimal("0.01")
AMOUNT_TOLERANCE_EUR = Decimal("0.10")
LINE_AMOUNT_TOLERANCE_EUR = Decimal("0.05")
UNIT_PRICE_TOLERANCE_EUR_KWH = Decimal("0.00005")

ENEDIS_TURPE_7_SOURCE_URL = (
    "https://www.enedis.fr/sites/default/files/documents/pdf/brochure-tarifaire-turpe-7.pdf"
)
CRE_TURPE_7_SOURCE_URL = (
    "https://www.cre.fr/documents/deliberations/tarif-dutilisation-des-reseaux-publics-de-distribution-delectricite-turpe-7-hta-bt.html"
)
CRE_TURPE_7_2026_MODIFICATION_URL = (
    "https://www.cre.fr/documents/deliberations/modification-des-tarifs-dutilisation-des-reseaux-publics-de-distribution-et-transport-delectricite-turpe-7-hta-bt-et-turpe-7-htb.html"
)

POSTE_ORDER = {
    "HTA": ["pointe", "hph", "hch", "hpe", "hce"],
    "BT>36": ["hph", "hch", "hpe", "hce"],
}


def _dec(value: str | int | float | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _year_days(year: int) -> Decimal:
    start = date(year, 1, 1)
    end = date(year + 1, 1, 1)
    return Decimal((end - start).days)


def _days_inclusive(start: date, end: date) -> int:
    return (end - start).days + 1


def _strip_accents(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", value) if unicodedata.category(char) != "Mn"
    )


TURPE_TABLES: list[dict[str, Any]] = [
    {
        "code": "TURPE_7_HTA_BT_2025_08",
        "family": "TURPE 7 HTA-BT",
        "label": "TURPE 7 HTA-BT - bareme Enedis au 1er aout 2025",
        "valid_from": date(2025, 8, 1),
        "valid_to": date(2026, 7, 31),
        "next_expected_update": date(2026, 8, 1),
        "successor_hint": "Importer le bareme publie pour l'indexation annuelle du 1er aout 2026.",
        "source_label": "Enedis, brochure tarifaire TURPE 7 HTA/BT, tarifs en vigueur au 1er aout 2025",
        "source_url": ENEDIS_TURPE_7_SOURCE_URL,
        "cre_deliberation_url": CRE_TURPE_7_SOURCE_URL,
        "cre_modification_url": CRE_TURPE_7_2026_MODIFICATION_URL,
        "fixed_components": {
            "BT<=36": {"management_contract_unique": Decimal("16.80"), "counting": Decimal("22.00")},
            "BT>36": {"management_contract_unique": Decimal("217.80"), "counting": Decimal("283.27")},
            "HTA": {"management_contract_unique": Decimal("435.72"), "counting": Decimal("376.39")},
        },
        "withdrawal": {
            "BT<=36_CU4": {
                "voltage_domain": "BT<=36",
                "label": "BT <= 36 kVA - courte utilisation 4 plages",
                "power_coefficients": {"base": Decimal("10.11")},
                "energy_coefficients_cents": {
                    "hph": Decimal("7.49"),
                    "hch": Decimal("3.97"),
                    "hpe": Decimal("1.66"),
                    "hce": Decimal("1.16"),
                },
            },
            "BT<=36_MU4": {
                "voltage_domain": "BT<=36",
                "label": "BT <= 36 kVA - moyenne utilisation 4 plages",
                "power_coefficients": {"base": Decimal("12.12")},
                "energy_coefficients_cents": {
                    "hph": Decimal("7.00"),
                    "hch": Decimal("3.73"),
                    "hpe": Decimal("1.61"),
                    "hce": Decimal("1.11"),
                },
            },
            "BT<=36_LU": {
                "voltage_domain": "BT<=36",
                "label": "BT <= 36 kVA - longue utilisation",
                "power_coefficients": {"base": Decimal("93.13")},
                "energy_coefficients_cents": {
                    "base": Decimal("1.25"),
                    "hph": Decimal("1.25"),
                    "hch": Decimal("1.25"),
                    "hpe": Decimal("1.25"),
                    "hce": Decimal("1.25"),
                },
            },
            "BT<=36_CU": {
                "voltage_domain": "BT<=36",
                "label": "BT <= 36 kVA - courte utilisation derogatoire",
                "power_coefficients": {"base": Decimal("11.07")},
                "energy_coefficients_cents": {
                    "base": Decimal("4.84"),
                    "hph": Decimal("4.84"),
                    "hch": Decimal("4.84"),
                    "hpe": Decimal("4.84"),
                    "hce": Decimal("4.84"),
                },
            },
            "BT<=36_MUDT": {
                "voltage_domain": "BT<=36",
                "label": "BT <= 36 kVA - moyenne utilisation 2 plages derogatoire",
                "power_coefficients": {"base": Decimal("13.49")},
                "energy_coefficients_cents": {
                    "hp": Decimal("4.94"),
                    "hc": Decimal("3.50"),
                    "hph": Decimal("4.94"),
                    "hch": Decimal("3.50"),
                    "hpe": Decimal("4.94"),
                    "hce": Decimal("3.50"),
                },
            },
            "BT>36_CU": {
                "voltage_domain": "BT>36",
                "label": "BT > 36 kVA - courte utilisation",
                "power_coefficients": {
                    "hph": Decimal("17.61"),
                    "hch": Decimal("15.96"),
                    "hpe": Decimal("14.56"),
                    "hce": Decimal("11.98"),
                },
                "energy_coefficients_cents": {
                    "hph": Decimal("6.91"),
                    "hch": Decimal("4.21"),
                    "hpe": Decimal("2.13"),
                    "hce": Decimal("1.52"),
                },
            },
            "BT>36_LU": {
                "voltage_domain": "BT>36",
                "label": "BT > 36 kVA - longue utilisation",
                "power_coefficients": {
                    "hph": Decimal("30.16"),
                    "hch": Decimal("21.18"),
                    "hpe": Decimal("16.64"),
                    "hce": Decimal("12.37"),
                },
                "energy_coefficients_cents": {
                    "hph": Decimal("5.69"),
                    "hch": Decimal("3.47"),
                    "hpe": Decimal("2.01"),
                    "hce": Decimal("1.49"),
                },
            },
            "HTA_CU_PF": {
                "voltage_domain": "HTA",
                "label": "HTA - courte utilisation pointe fixe",
                "power_coefficients": {
                    "pointe": Decimal("14.41"),
                    "hph": Decimal("14.41"),
                    "hch": Decimal("14.41"),
                    "hpe": Decimal("12.55"),
                    "hce": Decimal("11.22"),
                },
                "energy_coefficients_cents": {
                    "pointe": Decimal("5.74"),
                    "hph": Decimal("4.23"),
                    "hch": Decimal("1.99"),
                    "hpe": Decimal("1.01"),
                    "hce": Decimal("0.69"),
                },
            },
            "HTA_CU_PM": {
                "voltage_domain": "HTA",
                "label": "HTA - courte utilisation pointe mobile",
                "power_coefficients": {
                    "pointe": Decimal("14.41"),
                    "hph": Decimal("14.41"),
                    "hch": Decimal("14.41"),
                    "hpe": Decimal("12.55"),
                    "hce": Decimal("11.22"),
                },
                "energy_coefficients_cents": {
                    "pointe": Decimal("7.01"),
                    "hph": Decimal("4.05"),
                    "hch": Decimal("1.99"),
                    "hpe": Decimal("1.01"),
                    "hce": Decimal("0.69"),
                },
            },
            "HTA_LU_PF": {
                "voltage_domain": "HTA",
                "label": "HTA - longue utilisation pointe fixe",
                "power_coefficients": {
                    "pointe": Decimal("35.33"),
                    "hph": Decimal("32.30"),
                    "hch": Decimal("20.39"),
                    "hpe": Decimal("14.33"),
                    "hce": Decimal("11.56"),
                },
                "energy_coefficients_cents": {
                    "pointe": Decimal("2.65"),
                    "hph": Decimal("2.10"),
                    "hch": Decimal("1.47"),
                    "hpe": Decimal("0.92"),
                    "hce": Decimal("0.68"),
                },
            },
            "HTA_LU_PM": {
                "voltage_domain": "HTA",
                "label": "HTA - longue utilisation pointe mobile",
                "power_coefficients": {
                    "pointe": Decimal("38.27"),
                    "hph": Decimal("34.30"),
                    "hch": Decimal("20.39"),
                    "hpe": Decimal("14.33"),
                    "hce": Decimal("11.56"),
                },
                "energy_coefficients_cents": {
                    "pointe": Decimal("3.15"),
                    "hph": Decimal("1.87"),
                    "hch": Decimal("1.47"),
                    "hpe": Decimal("0.92"),
                    "hce": Decimal("0.68"),
                },
            },
        },
    }
]


def list_turpe_versions() -> list[dict[str, Any]]:
    versions: list[dict[str, Any]] = []
    for table in TURPE_TABLES:
        versions.append(
            {
                "code": table["code"],
                "family": table["family"],
                "label": table["label"],
                "valid_from": table["valid_from"],
                "valid_to": table["valid_to"],
                "next_expected_update": table["next_expected_update"],
                "successor_hint": table["successor_hint"],
                "source_label": table["source_label"],
                "source_url": table["source_url"],
                "cre_deliberation_url": table["cre_deliberation_url"],
                "cre_modification_url": table["cre_modification_url"],
                "tariff_keys": sorted(table["withdrawal"].keys()),
            }
        )
    return versions


def find_turpe_table(on_date: date) -> dict[str, Any] | None:
    for table in TURPE_TABLES:
        if table["valid_from"] <= on_date <= table["valid_to"]:
            return table
    return None


def evaluate_invoice_turpe(parsed: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    summary = {
        "checked_sites": 0,
        "checked_lines": 0,
        "mismatches": 0,
        "missing_versions": 0,
        "partial_sites": 0,
        "expected_network_ht": 0.0,
        "invoice_network_ht": 0.0,
        "source": list_turpe_versions()[0] if TURPE_TABLES else None,
    }

    for site in parsed.get("sites", []):
        site_report = evaluate_site_turpe(site)
        site_summary = site_report["summary"]
        summary["checked_sites"] += 1 if site_summary["has_network_lines"] else 0
        summary["checked_lines"] += site_summary["checked_lines"]
        summary["mismatches"] += site_summary["mismatches"]
        summary["missing_versions"] += site_summary["missing_versions"]
        summary["partial_sites"] += 1 if site_summary["partial"] else 0
        summary["expected_network_ht"] += float(site_summary["expected_network_ht"])
        summary["invoice_network_ht"] += float(site_summary["invoice_network_ht"])
        issues.extend(site_report["issues"])

    summary["expected_network_ht"] = round(summary["expected_network_ht"], 2)
    summary["invoice_network_ht"] = round(summary["invoice_network_ht"], 2)
    return {"summary": summary, "issues": issues}


def evaluate_site_turpe(site: dict[str, Any]) -> dict[str, Any]:
    scope = site.get("prm_id") or site.get("fic_number") or "fic"
    issues: list[dict[str, Any]] = []
    lines = [line for line in site.get("invoice_lines", []) if line.get("family") == "network"]
    invoice_total = _dec((site.get("family_totals") or {}).get("network")) or Decimal("0")
    expected_total = Decimal("0")
    checked_lines = 0
    mismatches = 0
    missing_versions = 0
    partial = False

    if not lines:
        return {
            "summary": {
                "has_network_lines": False,
                "checked_lines": 0,
                "mismatches": 0,
                "missing_versions": 0,
                "partial": False,
                "expected_network_ht": Decimal("0"),
                "invoice_network_ht": invoice_total,
            },
            "issues": [],
        }

    tariff_key = infer_turpe_tariff_key(site)
    if tariff_key is None:
        partial = True
        issues.append(
            {
                "severity": "warning",
                "code": "TURPE_TARIFF_UNKNOWN",
                "message": f"TURPE non verifiable sur {scope}: formule d'acheminement non reconnue.",
                "scope": scope,
            }
        )

    for line in lines:
        component = line.get("normalized_component")
        result = _expected_line_amount(site, line, tariff_key)
        if result.get("missing_version"):
            missing_versions += 1
        if result.get("partial"):
            partial = True
            if result.get("message"):
                issues.append(
                    {
                        "severity": "warning",
                        "code": result["code"],
                        "message": f"TURPE partiel sur {scope}: {result['message']}",
                        "scope": scope,
                    }
                )
            continue

        expected_amount = result.get("expected_amount")
        if expected_amount is None:
            partial = True
            continue

        checked_lines += 1
        expected_total += expected_amount
        invoice_amount = _dec(line.get("amount_ht"))
        if invoice_amount is not None and abs(invoice_amount - expected_amount) > LINE_AMOUNT_TOLERANCE_EUR:
            mismatches += 1
            issues.append(
                {
                    "severity": "error",
                    "code": "TURPE_AMOUNT_MISMATCH",
                    "message": (
                        f"Ligne TURPE {component} differente sur {scope}: "
                        f"attendu {expected_amount:.2f} EUR HT, facture {invoice_amount:.2f} EUR HT."
                    ),
                    "scope": scope,
                }
            )

        invoice_unit = _dec(line.get("unit_price_ht"))
        expected_unit = result.get("expected_unit_price")
        if invoice_unit is not None and expected_unit is not None:
            if abs(invoice_unit - expected_unit) > UNIT_PRICE_TOLERANCE_EUR_KWH:
                mismatches += 1
                issues.append(
                    {
                        "severity": "error",
                        "code": "TURPE_UNIT_PRICE_MISMATCH",
                        "message": (
                            f"Prix unitaire TURPE different sur {scope}: "
                            f"attendu {expected_unit:.5f} EUR/kWh, facture {invoice_unit:.5f} EUR/kWh."
                        ),
                        "scope": scope,
                    }
                )

    if not partial and checked_lines == len(lines):
        delta = abs(invoice_total - expected_total)
        if delta > AMOUNT_TOLERANCE_EUR:
            mismatches += 1
            issues.append(
                {
                    "severity": "error",
                    "code": "TURPE_TOTAL_MISMATCH",
                    "message": (
                        f"Total acheminement different sur {scope}: attendu {expected_total:.2f} EUR HT, "
                        f"facture {invoice_total:.2f} EUR HT."
                    ),
                    "scope": scope,
                }
            )

    return {
        "summary": {
            "has_network_lines": True,
            "checked_lines": checked_lines,
            "mismatches": mismatches,
            "missing_versions": missing_versions,
            "partial": partial,
            "expected_network_ht": expected_total,
            "invoice_network_ht": invoice_total,
        },
        "issues": issues,
    }


def _expected_line_amount(
    site: dict[str, Any],
    line: dict[str, Any],
    tariff_key: str | None,
) -> dict[str, Any]:
    component = line.get("normalized_component")
    if tariff_key is None:
        return {"partial": True}

    if component == "network_variable":
        return _expected_variable_line(line, tariff_key)

    period = _line_period(line, site)
    if period is None:
        return {
            "partial": True,
            "code": "TURPE_PERIOD_MISSING",
            "message": "periode de ligne absente.",
        }
    start, end = period

    if component == "network_management":
        return _prorated_fixed_line(
            start,
            end,
            lambda table: _fixed_component_rate(table, tariff_key, "management_contract_unique"),
        )

    if component == "network_counting":
        return _prorated_fixed_line(
            start,
            end,
            lambda table: _fixed_component_rate(table, tariff_key, "counting"),
        )

    if component == "network_withdrawal":
        return _prorated_fixed_line(
            start,
            end,
            lambda table: _annual_withdrawal_fixed_amount(table, tariff_key, site),
        )

    return {
        "partial": True,
        "code": "TURPE_COMPONENT_UNSUPPORTED",
        "message": f"composante non supportee ({component or 'inconnue'}).",
    }


def _expected_variable_line(line: dict[str, Any], tariff_key: str) -> dict[str, Any]:
    start = line.get("period_start")
    end = line.get("period_end")
    line_date = start or end
    if not isinstance(line_date, date):
        return {
            "partial": True,
            "code": "TURPE_PERIOD_MISSING",
            "message": "periode de consommation absente.",
        }

    table = find_turpe_table(line_date)
    if table is None:
        return {
            "partial": True,
            "missing_version": True,
            "code": "TURPE_VERSION_MISSING",
            "message": f"aucun bareme charge pour le {line_date.isoformat()}.",
        }
    if isinstance(start, date) and isinstance(end, date):
        end_table = find_turpe_table(end)
        if end_table is None:
            return {
                "partial": True,
                "missing_version": True,
                "code": "TURPE_VERSION_MISSING",
                "message": f"aucun bareme charge pour le {end.isoformat()}.",
            }
        if end_table["code"] != table["code"]:
            return {
                "partial": True,
                "code": "TURPE_PERIOD_CROSSES_VERSION",
                "message": "ligne de consommation a cheval sur deux baremes TURPE.",
            }

    withdrawal = table["withdrawal"].get(tariff_key)
    if withdrawal is None:
        return {
            "partial": True,
            "code": "TURPE_TARIFF_UNSUPPORTED",
            "message": f"tarif {tariff_key} absent du referentiel.",
        }

    poste = line.get("poste") or "base"
    coeff = withdrawal["energy_coefficients_cents"].get(poste)
    if coeff is None and poste == "pointe" and withdrawal["voltage_domain"] == "BT>36":
        coeff = withdrawal["energy_coefficients_cents"].get("hph")
    if coeff is None:
        return {
            "partial": True,
            "code": "TURPE_POSTE_UNSUPPORTED",
            "message": f"poste {poste} absent du referentiel {tariff_key}.",
        }

    quantity = _dec(line.get("quantity"))
    if quantity is None:
        return {
            "partial": True,
            "code": "TURPE_QUANTITY_MISSING",
            "message": "quantite de consommation absente.",
        }

    expected_unit = (coeff / Decimal("100")).quantize(Decimal("0.00001"))
    return {
        "partial": False,
        "expected_amount": _money(quantity * expected_unit),
        "expected_unit_price": expected_unit,
        "version_code": table["code"],
    }


def _prorated_fixed_line(
    start: date,
    end: date,
    annual_rate_getter: Callable[[dict[str, Any]], Decimal | None],
) -> dict[str, Any]:
    cursor = start
    total = Decimal("0")
    while cursor <= end:
        table = find_turpe_table(cursor)
        if table is None:
            return {
                "partial": True,
                "missing_version": True,
                "code": "TURPE_VERSION_MISSING",
                "message": f"aucun bareme charge pour le {cursor.isoformat()}.",
            }

        segment_end = min(end, table["valid_to"], date(cursor.year, 12, 31))
        annual_rate = annual_rate_getter(table)
        if annual_rate is None:
            return {
                "partial": True,
                "code": "TURPE_TARIFF_UNSUPPORTED",
                "message": "tarif ou puissance non exploitable pour cette composante.",
            }

        total += annual_rate * Decimal(_days_inclusive(cursor, segment_end)) / _year_days(cursor.year)
        cursor = segment_end + timedelta(days=1)

    return {"partial": False, "expected_amount": _money(total)}


def _fixed_component_rate(table: dict[str, Any], tariff_key: str, component: str) -> Decimal | None:
    withdrawal = table["withdrawal"].get(tariff_key)
    if withdrawal is None:
        return None
    fixed = table["fixed_components"].get(withdrawal["voltage_domain"])
    if fixed is None:
        return None
    return fixed.get(component)


def _annual_withdrawal_fixed_amount(
    table: dict[str, Any],
    tariff_key: str,
    site: dict[str, Any],
) -> Decimal | None:
    withdrawal = table["withdrawal"].get(tariff_key)
    if withdrawal is None:
        return None

    power_coeffs = withdrawal["power_coefficients"]
    voltage = withdrawal["voltage_domain"]
    if voltage == "BT<=36":
        subscribed = _dec(site.get("subscribed_power_kva"))
        if subscribed is None:
            return None
        return power_coeffs["base"] * subscribed

    powers = _power_by_poste(site)
    order = POSTE_ORDER.get(voltage)
    if not powers or not order:
        return None

    previous = Decimal("0")
    total = Decimal("0")
    for poste in order:
        current = powers.get(poste)
        coeff = power_coeffs.get(poste)
        if current is None or coeff is None:
            return None
        delta = max(current - previous, Decimal("0"))
        total += coeff * delta
        previous = current
    return total


def _power_by_poste(site: dict[str, Any]) -> dict[str, Decimal]:
    powers: dict[str, Decimal] = {}
    for row in site.get("power_rows", []):
        poste = row.get("poste")
        power = _dec(row.get("subscribed_power_kva"))
        if poste and power is not None:
            powers[poste] = power
    return powers


def _line_period(line: dict[str, Any], site: dict[str, Any]) -> tuple[date, date] | None:
    start = line.get("period_start") or site.get("period_start")
    end = line.get("period_end") or site.get("period_end")
    if isinstance(start, date) and isinstance(end, date) and start <= end:
        return start, end
    return None


def infer_turpe_tariff_key(site: dict[str, Any]) -> str | None:
    return infer_turpe_tariff_key_from_values(
        tariff_label=site.get("tariff_option_label"),
        segment=site.get("segment"),
    )


def infer_turpe_tariff_key_from_values(tariff_label: str | None, segment: str | None = None) -> str | None:
    text = _strip_accents(f"{tariff_label or ''} {segment or ''}").upper()

    if "HTA" in text or segment == "C2":
        is_lu = "LONGUE" in text
        is_mobile = "MOBILE" in text
        if is_lu and is_mobile:
            return "HTA_LU_PM"
        if is_lu:
            return "HTA_LU_PF"
        if is_mobile:
            return "HTA_CU_PM"
        if "COURTE" in text:
            return "HTA_CU_PF"
        return None

    if "BT>36" in text or "BT > 36" in text or segment == "C4":
        if "LONGUE" in text:
            return "BT>36_LU"
        if "COURTE" in text or segment == "C4":
            return "BT>36_CU"
        return None

    if "BT" in text or segment == "C5":
        if "MUDT" in text or ("MOYENNE" in text and "2 PLAGE" in text):
            return "BT<=36_MUDT"
        if "4 PLAGE" in text and "MOYENNE" in text:
            return "BT<=36_MU4"
        if "4 PLAGE" in text and "COURTE" in text:
            return "BT<=36_CU4"
        if "LONGUE" in text:
            return "BT<=36_LU"
        if "COURTE" in text:
            return "BT<=36_CU"
        if segment == "C5":
            return "BT<=36_CU4"

    return None


def estimate_power_change_annual_impact(
    tariff_label: str | None,
    segment: str | None,
    current_power_kva: float | None,
    target_power_kva: float | None,
    on_date: date | None = None,
) -> dict[str, Any]:
    if current_power_kva is None or target_power_kva is None:
        return {
            "available": False,
            "annual_amount_eur": None,
            "reason": "Impact TURPE non chiffre : puissance actuelle ou cible absente.",
        }

    table = find_turpe_table(on_date or date.today())
    if table is None:
        return {
            "available": False,
            "annual_amount_eur": None,
            "reason": "Impact TURPE non chiffre : bareme applicable non charge.",
        }

    tariff_key = infer_turpe_tariff_key_from_values(tariff_label, segment)
    if tariff_key is None:
        return {
            "available": False,
            "annual_amount_eur": None,
            "reason": "Impact TURPE non chiffre : formule d'acheminement non reconnue.",
        }

    withdrawal = table["withdrawal"].get(tariff_key)
    if withdrawal is None or withdrawal["voltage_domain"] != "BT<=36":
        return {
            "available": False,
            "annual_amount_eur": None,
            "reason": "Impact TURPE non chiffre : puissance multi-postes a traiter avec le detail Enedis.",
        }

    coeff = withdrawal["power_coefficients"]["base"]
    delta = Decimal(str(target_power_kva)) - Decimal(str(current_power_kva))
    amount = _money(delta * coeff)
    return {
        "available": True,
        "annual_amount_eur": float(amount),
        "reason": (
            f"Estimation limitee a la part fixe TURPE ({coeff} EUR/kVA/an), "
            "hors fourniture, taxes, depassements et effet horosaisonnier."
        ),
        "version_code": table["code"],
        "tariff_key": tariff_key,
    }
