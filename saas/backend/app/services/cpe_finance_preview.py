"""Preview of DALKIA finance exports before CPE invoice ingestion."""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from app.schemas.cpe import CpeFinanceContractSummary, CpeFinanceGroupSummary, CpeFinancePreview

CPE_FINANCE_MARKETS = {"P1", "P2", "P3"}
_CPE_SITE_CODE_RE = re.compile(r"\b(VDS-[A-Z]+\s+\d+(?:\.\d+)?|CCAS\s+\d+)\b", flags=re.IGNORECASE)


def _decode(content: str | bytes) -> str:
    if isinstance(content, str):
        return content
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("latin-1", errors="replace")


def _normalize_header(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip())
    ascii_value = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "_", ascii_value.lower()).strip("_")


def _detect_delimiter(sample: str) -> str:
    candidates = (";", "\t", ",")
    return max(candidates, key=sample.count)


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _decimal(value: str | None) -> Decimal:
    raw = _clean(value).replace(" ", "").replace("\xa0", "").replace(",", ".")
    if not raw:
        return Decimal("0")
    try:
        return Decimal(raw)
    except InvalidOperation:
        return Decimal("0")


def _site_code(value: str | None) -> str | None:
    match = _CPE_SITE_CODE_RE.search(_clean(value))
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1).upper()).strip()


def _required_columns(reader: csv.DictReader) -> dict[str, str]:
    header_map = {_normalize_header(name): name for name in reader.fieldnames or []}
    required = {
        "code_contrat": "CODE CONTRAT",
        "numero_de_facture": "NUMERO DE FACTURE",
        "marche": "MARCHE",
        "montant_ht": "MONTANT HT",
    }
    missing = [label for key, label in required.items() if key not in header_map]
    if missing:
        raise ValueError(f"Colonnes obligatoires absentes : {', '.join(missing)}")
    return header_map


def _row_value(row: dict[str, str], header_map: dict[str, str], normalized_name: str) -> str:
    original_name = header_map.get(normalized_name)
    return _clean(row.get(original_name)) if original_name else ""


@dataclass
class _Group:
    amount: Decimal = Decimal("0")
    rows: int = 0
    invoices: set[str] = field(default_factory=set)

    def add(self, amount: Decimal, invoice_number: str) -> None:
        self.amount += amount
        self.rows += 1
        if invoice_number:
            self.invoices.add(invoice_number)


@dataclass
class _Contract(_Group):
    label: str = ""
    period_starts: set[str] = field(default_factory=set)
    period_ends: set[str] = field(default_factory=set)
    markets: set[str] = field(default_factory=set)
    market_types: set[str] = field(default_factory=set)
    site_codes: set[str] = field(default_factory=set)
    site_code_rows: int = 0
    consumption_rows: int = 0
    reading_rows: int = 0


@dataclass(frozen=True)
class DalkiaFinanceRow:
    source_row_number: int
    contract_code: str
    contract_label: str
    affair: str
    market_type: str
    invoice_due_date: str
    invoice_type: str
    period_start: str
    period_end: str
    company: str
    invoice_number: str
    issued_at: str
    original_invoice_number: str
    customer_code: str
    customer_name: str
    market: str
    sold_service: str
    customer_reference: str
    billed_item: str
    vat_rate: Decimal
    amount_ht: Decimal
    consumption: Decimal | None
    consumption_unit: str
    prestation_detail: str
    recipient_code: str
    recipient_reference: str
    base_price: Decimal | None
    reading_index_start: Decimal | None
    reading_index_end: Decimal | None
    reading_date_start: str
    reading_date_end: str
    revised_price: Decimal | None
    reading_type: str
    detected_site_code: str | None
    raw: dict[str, str]

    @property
    def has_consumption(self) -> bool:
        return self.consumption is not None

    @property
    def has_reading(self) -> bool:
        return self.reading_index_start is not None or self.reading_index_end is not None


def _optional_decimal(value: str | None) -> Decimal | None:
    return _decimal(value) if _clean(value) else None


def parse_finance_rows(content: str | bytes) -> list[DalkiaFinanceRow]:
    """Parse les lignes brutes d'un export finances DALKIA."""
    text = _decode(content)
    reader = csv.DictReader(io.StringIO(text), delimiter=_detect_delimiter(text[:4000]))
    header_map = _required_columns(reader)
    rows: list[DalkiaFinanceRow] = []

    for source_row_number, raw_row in enumerate(reader, start=2):
        raw = {_normalize_header(key): _clean(value) for key, value in raw_row.items() if key}
        prestation_detail = _row_value(raw_row, header_map, "lieu_ou_detail_de_la_prestation")
        rows.append(
            DalkiaFinanceRow(
                source_row_number=source_row_number,
                contract_code=_row_value(raw_row, header_map, "code_contrat") or "Non renseigne",
                contract_label=_row_value(raw_row, header_map, "libelle_contrat"),
                affair=_row_value(raw_row, header_map, "affaire"),
                market_type=_row_value(raw_row, header_map, "type_de_marche"),
                invoice_due_date=_row_value(raw_row, header_map, "date_d_echeance_de_la_facture"),
                invoice_type=_row_value(raw_row, header_map, "type_de_facture") or "Non renseigne",
                period_start=_row_value(raw_row, header_map, "debut_periode_de_facturation"),
                period_end=_row_value(raw_row, header_map, "fin_periode_de_facturation"),
                company=_row_value(raw_row, header_map, "societe"),
                invoice_number=_row_value(raw_row, header_map, "numero_de_facture"),
                issued_at=_row_value(raw_row, header_map, "date_d_edition"),
                original_invoice_number=_row_value(raw_row, header_map, "numero_de_facture_d_origine"),
                customer_code=_row_value(raw_row, header_map, "code_du_client"),
                customer_name=_row_value(raw_row, header_map, "nom_du_client"),
                market=_row_value(raw_row, header_map, "marche") or "Non renseigne",
                sold_service=_row_value(raw_row, header_map, "service_vendu"),
                customer_reference=_row_value(raw_row, header_map, "reference_interne_client"),
                billed_item=_row_value(raw_row, header_map, "poste_facture"),
                vat_rate=_decimal(_row_value(raw_row, header_map, "taux_de_tva")),
                amount_ht=_decimal(_row_value(raw_row, header_map, "montant_ht")),
                consumption=_optional_decimal(_row_value(raw_row, header_map, "consommation")),
                consumption_unit=_row_value(raw_row, header_map, "unite"),
                prestation_detail=prestation_detail,
                recipient_code=_row_value(raw_row, header_map, "destinataire_1"),
                recipient_reference=_row_value(raw_row, header_map, "ref_destinataire_1"),
                base_price=_optional_decimal(_row_value(raw_row, header_map, "prix_de_base")),
                reading_index_start=_optional_decimal(_row_value(raw_row, header_map, "index_debut_de_releve")),
                reading_index_end=_optional_decimal(_row_value(raw_row, header_map, "index_fin_de_releve")),
                reading_date_start=_row_value(raw_row, header_map, "date_debut_de_releve"),
                reading_date_end=_row_value(raw_row, header_map, "date_fin_de_releve"),
                revised_price=_optional_decimal(_row_value(raw_row, header_map, "prix_ou_forfait_revise")),
                reading_type=_row_value(raw_row, header_map, "type_de_releve"),
                detected_site_code=_site_code(prestation_detail),
                raw=raw,
            )
        )
    return rows


def _summary(code: str, group: _Group) -> CpeFinanceGroupSummary:
    return CpeFinanceGroupSummary(
        code=code or "Non renseigne",
        nb_lignes=group.rows,
        nb_factures=len(group.invoices),
        montant_ht=round(float(group.amount), 2),
    )


def preview_finance_export(content: str | bytes, filename: str | None = None) -> CpeFinancePreview:
    """Summarize an export finances CSV without persisting its invoice lines."""
    total_amount = Decimal("0")
    invoices: set[str] = set()
    contracts: dict[str, _Contract] = defaultdict(_Contract)
    markets: dict[str, _Group] = defaultdict(_Group)
    invoice_types: dict[str, _Group] = defaultdict(_Group)
    site_codes: set[str] = set()
    total_rows = cpe_market_rows = site_code_rows = consumption_rows = reading_rows = 0

    for row in parse_finance_rows(content):
        total_rows += 1
        contract_code = row.contract_code
        contract_label = row.contract_label
        invoice_number = row.invoice_number
        market = row.market
        market_type = row.market_type
        invoice_type = row.invoice_type
        period_start = row.period_start
        period_end = row.period_end
        amount = row.amount_ht
        detected_site_code = row.detected_site_code

        total_amount += amount
        if invoice_number:
            invoices.add(invoice_number)
        if market in CPE_FINANCE_MARKETS:
            cpe_market_rows += 1
        has_consumption = row.has_consumption
        has_reading = row.has_reading
        if has_consumption:
            consumption_rows += 1
        if has_reading:
            reading_rows += 1

        markets[market].add(amount, invoice_number)
        invoice_types[invoice_type].add(amount, invoice_number)

        contract = contracts[contract_code]
        contract.label = contract.label or contract_label
        contract.add(amount, invoice_number)
        if period_start:
            contract.period_starts.add(period_start)
        if period_end:
            contract.period_ends.add(period_end)
        if market:
            contract.markets.add(market)
        if market_type:
            contract.market_types.add(market_type)
        if has_consumption:
            contract.consumption_rows += 1
        if has_reading:
            contract.reading_rows += 1
        if detected_site_code:
            site_code_rows += 1
            site_codes.add(detected_site_code)
            contract.site_code_rows += 1
            contract.site_codes.add(detected_site_code)

    contract_summaries = [
        CpeFinanceContractSummary(
            code_contrat=code,
            libelle_contrat=group.label or None,
            nb_lignes=group.rows,
            nb_factures=len(group.invoices),
            montant_ht=round(float(group.amount), 2),
            periode_debut_min=min(group.period_starts) if group.period_starts else None,
            periode_fin_max=max(group.period_ends) if group.period_ends else None,
            marches=sorted(group.markets),
            types_marche=sorted(group.market_types),
            nb_lignes_code_site_cpe=group.site_code_rows,
            nb_sites_cpe_distincts=len(group.site_codes),
            nb_lignes_consommation=group.consumption_rows,
            nb_lignes_index_releve=group.reading_rows,
        )
        for code, group in contracts.items()
    ]
    contract_summaries.sort(key=lambda item: item.nb_lignes, reverse=True)

    alerts = []
    if any(code not in CPE_FINANCE_MARKETS for code in markets):
        alerts.append("L'export contient des marches hors P1/P2/P3 : filtrer avant ingestion CPE definitive.")
    if site_code_rows < total_rows:
        alerts.append("Certaines lignes ne portent pas de code site CPE VDS/CCAS dans le detail de prestation.")
    if consumption_rows == 0:
        alerts.append("Aucune consommation n'est renseignee dans cet export : controle GRDF a faire avec une autre source.")
    contracts_without_consumption = [
        item.code_contrat
        for item in contract_summaries
        if item.nb_lignes_code_site_cpe > 0 and item.nb_lignes_consommation == 0
    ]
    if contracts_without_consumption:
        alerts.append(
            "Contrat(s) avec codes sites CPE mais sans consommation dans l'export : "
            + ", ".join(contracts_without_consumption)
            + "."
        )

    return CpeFinancePreview(
        filename=filename,
        nb_lignes=total_rows,
        nb_factures=len(invoices),
        nb_contrats=len(contracts),
        montant_ht=round(float(total_amount), 2),
        nb_lignes_p1_p2_p3=cpe_market_rows,
        nb_lignes_code_site_cpe=site_code_rows,
        nb_sites_cpe_distincts=len(site_codes),
        nb_lignes_consommation=consumption_rows,
        nb_lignes_index_releve=reading_rows,
        marches=sorted((_summary(code, group) for code, group in markets.items()), key=lambda item: item.montant_ht, reverse=True),
        types_facture=sorted(
            (_summary(code, group) for code, group in invoice_types.items()),
            key=lambda item: item.nb_lignes,
            reverse=True,
        ),
        contrats=contract_summaries,
        sites_cpe_detectes=sorted(site_codes),
        alertes=alerts,
    )
