"""Extraction des lignes de facture pour l'application des matrices comptables.

La matrice comptable travaille sur un format volontairement générique
(``InvoiceLine``). Ce module fait le pont avec les sources déjà développées :

- imports fluides électricité (ENGIE/EDF) normalisés ;
- factures gaz TotalEnergies ;
- factures CPE/DALKIA issues de l'export finances.

L'objectif est de conserver un moteur d'imputation pur et stable, tout en
branchant progressivement les vraies factures importées.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.cpe import CpeFinanceLine
from app.models.gas_invoice import GasInvoice
from app.models.invoice import (
    EnergyInvoice,
    EnergyInvoiceImport,
    EnergyInvoicePeriod,
    EnergyInvoiceSite,
)
from app.services.accounting_matrix_apply import InvoiceLine
from app.services.prm_scope import inactive_prm_ids, is_in_scope


def extract_invoice_lines(
    db: Session,
    city_id: int | None,
    *,
    source: str,
    invoice_id: str,
) -> list[InvoiceLine]:
    """Retourne les lignes normalisées utilisables par la matrice comptable.

    ``source`` accepte les formats historiques avec tirets ou underscores afin
    de ne pas casser le frontend ni les appels API existants.
    """
    normalized_source = _normalize_source(source)
    if normalized_source in {"energy_import", "fluides_import"}:
        return _extract_energy_import_lines(db, city_id, invoice_id)
    if normalized_source in {"gas_totalenergies", "totalenergies_gas"}:
        return _extract_gas_totalenergies_lines(db, city_id, invoice_id)
    if normalized_source in {"cpe_dalkia", "dalkia_cpe"}:
        return _extract_cpe_dalkia_lines(db, city_id, invoice_id)

    raise ValueError(
        "Source de facture non supportée pour l'application automatique de la matrice "
        f"comptable : {source}."
    )


def _normalize_source(source: str) -> str:
    return (source or "").strip().lower().replace("-", "_")


def _int_id(invoice_id: str, source_label: str) -> int:
    try:
        return int(invoice_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Identifiant facture invalide pour {source_label} : {invoice_id}.") from exc


def _extract_energy_import_lines(db: Session, city_id: int | None, invoice_id: str) -> list[InvoiceLine]:
    import_id = _int_id(invoice_id, "import fluide")
    stmt = (
        select(EnergyInvoiceImport)
        .where(EnergyInvoiceImport.id == import_id)
        .options(
            selectinload(EnergyInvoiceImport.normalized_invoice)
            .selectinload(EnergyInvoice.sites)
            .selectinload(EnergyInvoiceSite.periods)
            .selectinload(EnergyInvoicePeriod.lines)
        )
    )
    if city_id is not None:
        stmt = stmt.where(EnergyInvoiceImport.city_id == city_id)

    invoice_import = db.scalar(stmt)
    if invoice_import is None:
        raise ValueError("Import de facture fluide introuvable.")
    invoice = invoice_import.normalized_invoice
    if invoice is None:
        raise ValueError("Import de facture fluide non normalisé : lancez d'abord l'analyse/normalisation.")

    inactive = inactive_prm_ids(db, city_id)
    lines: list[InvoiceLine] = []
    for site in invoice.sites:
        if not is_in_scope(site.prm_id, inactive):
            continue
        for period in site.periods:
            for line in period.lines:
                billed_item = _first_text(
                    line.label,
                    line.normalized_code,
                    line.poste,
                    line.family,
                    line.raw_line,
                )
                if billed_item is None and line.amount_ht is None:
                    continue
                lines.append(
                    InvoiceLine(
                        billed_item=billed_item,
                        site_code=_first_text(site.regroupement, site.local_customer_reference),
                        meter_id=_first_text(site.prm_id, site.meter_number),
                        amount=line.amount_ht,
                        line_ref=f"energy-line:{line.id}",
                    )
                )

    if not lines:
        raise ValueError("Aucune ligne exploitable trouvée dans la facture fluide normalisée.")
    return lines


def _extract_cpe_dalkia_lines(db: Session, city_id: int | None, invoice_id: str) -> list[InvoiceLine]:
    cpe_invoice_id = _int_id(invoice_id, "facture CPE/DALKIA")
    stmt = (
        select(CpeFinanceLine)
        .where(CpeFinanceLine.invoice_id == cpe_invoice_id)
        .order_by(CpeFinanceLine.row_number.asc(), CpeFinanceLine.id.asc())
    )
    if city_id is not None:
        stmt = stmt.where(CpeFinanceLine.city_id == city_id)

    rows = list(db.scalars(stmt).all())
    if not rows:
        raise ValueError("Aucune ligne finance CPE/DALKIA trouvée pour cette facture.")

    return [
        InvoiceLine(
            billed_item=_first_text(row.billed_item, row.service_sold, row.market_type, row.market, row.detail),
            site_code=row.site_code_detected,
            meter_id=None,
            amount=row.amount_ht,
            line_ref=f"cpe-line:{row.id}",
        )
        for row in rows
    ]


_GAS_AMOUNT_FIELDS: tuple[tuple[str, str], ...] = (
    ("abonnement_fournisseur", "Abonnement fournisseur"),
    ("montant_conso_gaz", "Consommation gaz"),
    ("montant_cee", "CEE"),
    ("montant_cee_precarite", "CEE précarité"),
    ("montant_cpb", "CPB"),
    ("montant_indexation", "Indexation"),
    ("atrt_terme_fixe", "ATRT terme fixe"),
    ("atrd_terme_fixe", "ATRD terme fixe"),
    ("atrd_terme_variable", "ATRD terme variable"),
    ("montant_autres", "Autres prestations"),
    ("montant_ticgn", "Accise gaz / TICGN"),
    ("montant_cta", "CTA"),
)


def _extract_gas_totalenergies_lines(db: Session, city_id: int | None, invoice_id: str) -> list[InvoiceLine]:
    gas_invoice_id = _int_id(invoice_id, "facture gaz TotalEnergies")
    stmt = select(GasInvoice).where(GasInvoice.id == gas_invoice_id)
    if city_id is not None:
        stmt = stmt.where(GasInvoice.city_id == city_id)

    invoice = db.scalar(stmt)
    if invoice is None:
        raise ValueError("Facture gaz TotalEnergies introuvable.")

    lines: list[InvoiceLine] = []
    for field_name, label in _GAS_AMOUNT_FIELDS:
        amount = getattr(invoice, field_name, None)
        if amount is None or abs(float(amount)) < 0.005:
            continue
        lines.append(
            InvoiceLine(
                billed_item=label,
                site_code=_first_text(invoice.code_interne, invoice.ref_site),
                meter_id=_first_text(invoice.pce, invoice.matricule_compteur),
                amount=float(amount),
                line_ref=f"gas:{field_name}",
            )
        )

    if not lines:
        raise ValueError("Aucune ligne HT exploitable trouvée dans la facture gaz.")
    return lines


def _first_text(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
