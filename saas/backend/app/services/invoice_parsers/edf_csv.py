"""Parseur de l'export CSV de facturation EDF (électricité, éclairage public).

Produit la même structure `parsed` que le parseur ENGIE (parse_engie_xlsx) pour
réutiliser tout le pipeline d'analyse/contrôle/normalisation (apply_parsed_to_invoice_import).

Format source : CSV `;`, UTF-8 BOM, ~140 colonnes, une ligne par site×période.
Plusieurs lignes peuvent partager le même `num_facture` (facture multi-sites) :
on regroupe par numéro de facture -> un bordereau par facture.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

SUPPLIER = "EDF"


def _f(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _s(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _sum(row: dict[str, str], *keys: str) -> float | None:
    total = 0.0
    found = False
    for key in keys:
        val = _f(row.get(key))
        if val is not None:
            total += val
            found = True
    return round(total, 2) if found else None


def _date(value: str | None) -> str | None:
    text = _s(value)
    if not text:
        return None
    # EDF fournit déjà ISO (YYYY-MM-DD).
    return text[:10]


def _split_address(value: str | None) -> tuple[str | None, str | None, str | None]:
    text = _s(value)
    if not text:
        return None, None, None
    parts = [p.strip() for p in text.split(";") if p.strip()]
    street = parts[0] if parts else None
    postcode = city = None
    if len(parts) > 1:
        tail = parts[1].split(None, 1)
        if tail and tail[0].isdigit():
            postcode = tail[0]
            city = tail[1].strip() if len(tail) > 1 else None
        else:
            city = parts[1]
    return street, postcode, city


def _line(family: str, label: str, component: str, amount: float | None, raw: str) -> dict[str, Any] | None:
    if amount is None:
        return None
    return {
        "family": family,
        "label": label,
        "normalized_component": component,
        "poste": None,
        "amount_ht": amount,
        "raw_line": raw,
    }


def _build_site(row: dict[str, str]) -> dict[str, Any]:
    street, postcode, city = _split_address(row.get("adresse_site"))
    period_start = _date(row.get("date_de_debut_de_consommation"))
    period_end = _date(row.get("date_de_fin_de_consommation"))

    subscribed = _f(row.get("puissance_souscrite_base"))
    reached = max(
        [
            v
            for v in (
                _f(row.get(k))
                for k in (
                    "puissance_max_atteinte_base",
                    "puissance_max_atteinte_hp",
                    "puissance_max_atteinte_hc",
                    "puissance_max_atteinte_pointe",
                )
            )
            if v is not None
        ],
        default=None,
    )

    fixed_routing = _sum(
        row,
        "composante_de_soutirage_fixe_reprise_euros",
        "composante_de_soutirage_fixe_echu_euros",
        "composante_de_soutirage_fixe_echoir_euros",
        "composante_de_gestion_reprise_euros",
        "composante_de_gestion_echu_euros",
        "composante_de_gestion_echoir_euros",
        "composante_de_comptage_reprise_euros",
        "composante_de_comptage_echu_euros",
        "composante_de_comptage_echoir_euros",
    )

    lines = [
        _line("electricity", "Fourniture électricité", "supply", _f(row.get("total_fourniture_elec_ht_euros")), "EDF:supply"),
        _line("electricity", "Abonnement", "subscription", _f(row.get("abonnement_ht_euros")), "EDF:subscription"),
        _line("electricity", "Mécanisme de capacité", "capacity", _f(row.get("mecanisme_de_capacite_ht_euros")), "EDF:capacity"),
        _line("electricity", "Contribution CEE", "cee", _f(row.get("cee_ht_euros")), "EDF:cee"),
        _line("network", "Total part fixe acheminement", "network_fixed_total", fixed_routing, "EDF:network:fixed_total"),
        _line("network", "Dépassement de puissance souscrite", "network_overrun", _f(row.get("depassement_euros")), "EDF:network:overrun"),
        _line("taxes", "CSPE", "cspe", _f(row.get("contrib_serv_public_electricite_euros")), "EDF:taxes:cspe"),
        _line("taxes", "CTA Elec", "cta", _f(row.get("contrib_tarifaire_achem_elec_euros")), "EDF:taxes:cta"),
        _line("taxes", "Taxe communale (CCFE)", "tax_communale", _f(row.get("taxe_ccfe_euros")), "EDF:taxes:ccfe"),
        _line("taxes", "Taxe départementale (DCFE)", "tax_departementale", _f(row.get("taxe_dcfe_euros")), "EDF:taxes:dcfe"),
    ]

    return {
        "fic_number": _s(row.get("id_contrat")),
        "prm_id": _s(row.get("ref_acheminement")),
        "site_name": _s(row.get("nom_site")),
        "delivery_site_name": _s(row.get("nom_site")),
        "delivery_address": street,
        "delivery_postcode": postcode,
        "delivery_city": city,
        "installation": _s(row.get("code_imputation")),
        "meter_number": _s(row.get("numero_compteur")),
        "tariff_option_label": _s(row.get("tarif_acheminement")),
        "tariff_code": _s(row.get("fta")),
        "segment": _s(row.get("segment_or")),
        "regroupement": _s(row.get("code_imputation")),
        "period_start": period_start,
        "period_end": period_end,
        "period_days": None,
        "subscribed_power_kva": subscribed,
        "max_reached_power_kva": reached,
        "total_consumption_kwh": _f(row.get("conso_elec_facturee_kwh")),
        "total_ht": _f(row.get("total_htva_euros")) or _f(row.get("total_ht_euros")),
        "total_vat": _f(row.get("tva_totale_euros")),
        "total_ttc": _f(row.get("montant_total_ttc_euros")),
        "invoice_lines": [line for line in lines if line is not None],
    }


def parse_edf_csv(path: str | Path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))

    by_invoice: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        number = _s(row.get("num_facture"))
        if not number:
            continue
        by_invoice.setdefault(number, []).append(row)

    parsed_list: list[dict[str, Any]] = []
    for number, group in by_invoice.items():
        sites = [_build_site(row) for row in group]
        starts = [s["period_start"] for s in sites if s["period_start"]]
        ends = [s["period_end"] for s in sites if s["period_end"]]
        head = group[0]
        total_ttc = round(sum(s["total_ttc"] or 0.0 for s in sites), 2)
        total_ht = round(sum(s["total_ht"] or 0.0 for s in sites), 2)
        total_consumption = sum(s["total_consumption_kwh"] or 0.0 for s in sites)

        parsed_list.append(
            {
                "supplier": SUPPLIER,
                "document_type": "facture",
                "page_count": None,
                "fic_count": len(sites),
                "site_count": len(sites),
                "invoice": {
                    "invoice_number": number,
                    "invoice_date": _date(head.get("date_facture")),
                    "regroupement": _s(head.get("code_imputation")),
                    "contract_holder": _s(head.get("entite_juridique")),
                    "compte_contrat": _s(head.get("compte_de_facturation")),
                    "period_start": min(starts) if starts else None,
                    "period_end": max(ends) if ends else None,
                    "total_ttc": total_ttc,
                    "total_ht": total_ht,
                    "total_consumption_mwh": round(total_consumption / 1000, 3) if total_consumption else None,
                    "market_reference": None,
                },
                "sites": sites,
                "parser_warnings": [],
                "edf_segments": sorted({s["segment"] for s in sites if s["segment"]}),
            }
        )
    return parsed_list
