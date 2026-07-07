from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.models.bpu import (
    EXTRACTION_MANUAL,
    EXTRACTION_OCR_OK,
    EXTRACTION_OK,
    BpuDocument,
    BpuFixedCharge,
    BpuPriceComponent,
    BpuSegment,
    BpuTimePeriod,
)


SUPPORTED_BPU_EXTRACTION_STATUSES = {EXTRACTION_OK, EXTRACTION_OCR_OK, EXTRACTION_MANUAL}

INVOICE_COMPONENT_TO_BPU_COMPONENT = {
    "supply": "fourniture",
    "capacity": "capacite",
    "cee": "cee",
    "green_energy": "go",
    "cee_precarite": "cee_precarite",
    "cpb": "cpb",
}

POSTE_TO_BPU_PERIOD = {
    "base": "BASE",
    "pointe": "POINTE",
    "hph": "HPH",
    "hch": "HCH",
    "hpe": "HPE",
    "hce": "HCE",
    "hpb": "HPE",
    "hcb": "HCE",
    "hp": "HP",
    "hc": "HC",
}


@dataclass(frozen=True)
class HistoricalBpuPrice:
    document_id: int
    supplier: str
    valid_year: int
    lot_number: int
    segment_code: str
    period_code: str
    component_type: str
    price_eur_per_mwh: Decimal
    pdf_filename: str
    amendment_number: int | None = None
    valid_from: date | None = None
    valid_to: date | None = None


def load_historical_bpu_prices(db: Session, supplier: str | None) -> list[HistoricalBpuPrice]:
    normalized_supplier = normalize_bpu_supplier(supplier)
    if normalized_supplier is None:
        return []

    rows = (
        db.query(BpuDocument, BpuSegment, BpuTimePeriod, BpuPriceComponent)
        .join(BpuSegment, BpuSegment.document_id == BpuDocument.id)
        .join(BpuTimePeriod, BpuTimePeriod.segment_id == BpuSegment.id)
        .join(BpuPriceComponent, BpuPriceComponent.period_id == BpuTimePeriod.id)
        .filter(BpuDocument.supplier == normalized_supplier)
        .filter(BpuDocument.extraction_status.in_(SUPPORTED_BPU_EXTRACTION_STATUSES))
        .filter(BpuPriceComponent.price_value_eur_per_mwh.isnot(None))
        .all()
    )
    return historical_bpu_prices_from_rows(rows)


def historical_bpu_prices_from_rows(
    rows: Iterable[tuple[BpuDocument, BpuSegment, BpuTimePeriod, BpuPriceComponent]],
) -> list[HistoricalBpuPrice]:
    references: list[HistoricalBpuPrice] = []
    for document, segment, period, component in rows:
        price = _decimal(component.price_value_eur_per_mwh)
        if price is None:
            continue
        references.append(
            HistoricalBpuPrice(
                document_id=document.id,
                supplier=document.supplier,
                valid_year=document.valid_year,
                lot_number=document.lot_number,
                segment_code=(segment.segment_code or "").upper(),
                period_code=(period.period_code or "").upper(),
                component_type=component.component_type,
                price_eur_per_mwh=price,
                pdf_filename=document.pdf_filename,
                amendment_number=document.amendment_number,
                valid_from=document.valid_from,
                valid_to=document.valid_to,
            )
        )
    return references


def resolve_historical_bpu_price(
    references: Iterable[HistoricalBpuPrice],
    site: dict[str, Any],
    line: dict[str, Any],
) -> HistoricalBpuPrice | None:
    component_type = INVOICE_COMPONENT_TO_BPU_COMPONENT.get(line.get("normalized_component"))
    period_code = POSTE_TO_BPU_PERIOD.get(str(line.get("poste") or "").lower())
    billed_on = _line_reference_date(site, line)
    segment_candidates = _segment_code_candidates(site)
    if component_type is None or period_code is None or billed_on is None or not segment_candidates:
        return None

    matches = [
        reference
        for reference in references
        if reference.segment_code in segment_candidates
        and reference.period_code == period_code
        and reference.component_type == component_type
        and document_applies_to_date(reference, billed_on)
    ]
    if not matches:
        return None

    matches.sort(
        key=lambda reference: (
            reference.valid_from or date(reference.valid_year, 1, 1),
            reference.amendment_number or -1,
            reference.document_id,
        ),
        reverse=True,
    )
    chosen = matches[0]

    # If several market documents claim the exact same historical key for the
    # same billing date, keep the control conservative until the market context
    # can explicitly decide between them.
    ambiguous = {
        (reference.document_id, reference.lot_number, reference.price_eur_per_mwh)
        for reference in matches
        if reference.document_id != chosen.document_id
    }
    return None if ambiguous else chosen


def document_applies_to_date(reference: HistoricalBpuPrice, billed_on: date) -> bool:
    if reference.valid_from is not None and billed_on < reference.valid_from:
        return False
    if reference.valid_to is not None and billed_on > reference.valid_to:
        return False
    if reference.valid_from is not None or reference.valid_to is not None:
        return True
    return reference.valid_year == billed_on.year


@dataclass(frozen=True)
class FixedChargeReference:
    document_id: int
    supplier: str
    charge_type: str
    charge_label: str | None
    value_eur_per_month: Decimal
    pdf_filename: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None


def load_bpu_fixed_charges(db: Session, supplier: str | None) -> list[FixedChargeReference]:
    normalized_supplier = normalize_bpu_supplier(supplier)
    if normalized_supplier is None:
        return []

    rows = (
        db.query(BpuDocument, BpuFixedCharge)
        .join(BpuFixedCharge, BpuFixedCharge.document_id == BpuDocument.id)
        .filter(BpuDocument.supplier == normalized_supplier)
        .filter(BpuDocument.extraction_status.in_(SUPPORTED_BPU_EXTRACTION_STATUSES))
        .filter(BpuFixedCharge.charge_value_eur_per_month.isnot(None))
        .all()
    )
    return fixed_charge_references_from_rows(rows)


def fixed_charge_references_from_rows(
    rows: Iterable[tuple[BpuDocument, BpuFixedCharge]],
) -> list[FixedChargeReference]:
    references: list[FixedChargeReference] = []
    for document, charge in rows:
        value = _decimal(charge.charge_value_eur_per_month)
        if value is None:
            continue
        references.append(
            FixedChargeReference(
                document_id=document.id,
                supplier=document.supplier,
                charge_type=charge.charge_type,
                charge_label=charge.charge_label,
                value_eur_per_month=value,
                pdf_filename=document.pdf_filename,
                valid_from=charge.applicable_from,
                valid_to=charge.applicable_to,
            )
        )
    return references


def resolve_fixed_charge(
    references: Iterable[FixedChargeReference],
    charge_type: str,
    billed_on: date | None,
) -> FixedChargeReference | None:
    """Choisit le frais fixe contractuel applicable à une date pour un type donné.

    Abstention si plusieurs documents donnent un montant différent pour la même
    date (cohérent avec resolve_historical_bpu_price) — évite un faux contrôle.
    """
    matches = [
        reference
        for reference in references
        if reference.charge_type == charge_type
        and _fixed_charge_applies_to_date(reference, billed_on)
    ]
    if not matches:
        return None
    distinct_values = {reference.value_eur_per_month for reference in matches}
    if len(distinct_values) > 1:
        return None
    return matches[0]


def _fixed_charge_applies_to_date(reference: FixedChargeReference, billed_on: date | None) -> bool:
    if billed_on is None:
        # Sans date de référence, on n'applique que si la charge n'a pas de fenêtre.
        return reference.valid_from is None and reference.valid_to is None
    if reference.valid_from is not None and billed_on < reference.valid_from:
        return False
    if reference.valid_to is not None and billed_on > reference.valid_to:
        return False
    return True


def normalize_bpu_supplier(supplier: str | None) -> str | None:
    upper = (supplier or "").upper()
    if "ENGIE" in upper:
        return "ENGIE"
    if "EDF" in upper or "ELECTRICITE DE FRANCE" in upper:
        return "EDF"
    if "TOTAL" in upper:
        return "TOTALENERGIES"
    return None


def historical_segment_code_for_site(site: dict[str, Any]) -> str | None:
    segment = str(site.get("segment") or "").upper().strip()
    if segment in {"C1", "C2", "C3", "C4"}:
        return segment

    if segment == "C5":
        labels = " ".join(
            str(site.get(key) or "")
            for key in ("site_name", "delivery_site_name", "regroupement", "tariff_option_label")
        ).upper()
        if "ECLAIRAGE" in labels or "ÉCLAIRAGE" in labels:
            return "C5_EP"
        # C5 bâtiment (hors éclairage public) → segment "BATIMENT" dans le BPU historique
        # (code produit par import_bpu_xlsx._normalize_segment via le label "Bâtiment")
        return "BATIMENT"

    # Profils gaz TotalEnergies Lot 7 (Hérault Énergie)
    if segment in {"T1", "T2", "T3", "T4"}:
        return segment

    return None


def _segment_code_candidates(site: dict[str, Any]) -> set[str]:
    """Codes de segment BPU acceptables pour un site (match EXACT, ADDITIF).

    Le nouveau marché Hérault Énergie 2026 code les bâtiments par usage+tension
    (BATIMENT_HTA/BT/BT36), l'ancien par classe ENEDIS (C1..C4, C5_BAT_*). On propose
    le code historique du site ET la traduction vers le nouveau marché, de sorte que la
    résolution matche l'un OU l'autre selon l'année (filtrée par date). N'enlève aucun
    match (précision C1/C2/C3 conservée), en ajoute (C2/C4 bâtiments 2026 désormais matchés).
    """
    base = historical_segment_code_for_site(site)
    if base is None:
        return set()
    candidates = {base}
    segment = str(site.get("segment") or "").upper().strip()
    if base in {"C1", "C2", "C3"} or segment in {"C1", "C2", "C3"}:
        candidates.add("BATIMENT_HTA")
    elif base == "C4" or segment == "C4":
        candidates.add("BATIMENT_BT")
    if base == "BATIMENT":  # site C5 bâtiment (hors éclairage public)
        candidates.add("BATIMENT_BT36")
    elif base == "C5_EP":
        candidates.add("ECLAIRAGE_PUBLIC")
    return candidates


def _line_reference_date(site: dict[str, Any], line: dict[str, Any]) -> date | None:
    for value in (
        line.get("period_start"),
        site.get("period_start"),
        line.get("period_end"),
        site.get("period_end"),
    ):
        parsed = _date_value(value)
        if parsed is not None:
            return parsed
    return None


def _date_value(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:  # noqa: BLE001
        return None
