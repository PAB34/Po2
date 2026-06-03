"""Suivi de facturation marché CPE : enveloppes prévues (DPGF) vs montants reçus.

Le "prévu" provient du référentiel contractuel DALKIA importé depuis les fichiers DPGF
Lot 1 / Lot 2 (acte d'engagement) :

- P2 / P2.4 / P3 / P3.4 : sommes annuelles de ``cpe_dalkia_ref_p2p3`` (imports actifs) ;
- P1 (gaz) : somme annuelle du détail Annexe 6 ``cpe_dalkia_ref_p1_gaz.p10_total_ht``
  (imports actifs Lot 1 + Lot 2), conformément au choix de la source.

Le "reçu" agrège les lignes de factures DALKIA (``cpe_finance_lines``) du périmètre CPE
Ville, classées par poste à partir de ``market`` (P1/P2/P3) et ``billed_item`` (P2.4/P3.4),
et ventilées par année de période.

La page n'a besoin d'aucun nouveau parser : tout est déjà en base.
"""

from __future__ import annotations

import io
from typing import Any

import openpyxl
from openpyxl.styles import Font, PatternFill
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cpe import CpeFinanceLine
from app.models.cpe_dalkia import CpeDalkiaRefImport, CpeDalkiaRefP1Gaz, CpeDalkiaRefP2P3
from app.services.cpe_accounting import _is_current_cpe_contract, list_finance_invoices
from app.services.cpe_dalkia_db import normalize_p2p3_poste

# Ordre et libellés des postes affichés dans la matrice.
POSTE_ORDER = ["P1", "P2", "P2-4", "P3", "P3-4"]
POSTE_LABELS = {
    "P1": "P1 — Fourniture gaz",
    "P2": "P2 — Maintenance (hors P2.4)",
    "P2-4": "P2.4 — Intéressement / objectifs",
    "P3": "P3 — Gros entretien (hors P3.4)",
    "P3-4": "P3.4 — Travaux obligatoires",
}
# Poste fourre-tout pour les lignes reçues non rattachables à un poste contractuel.
POSTE_OTHER = "AUTRE"
POSTE_OTHER_LABEL = "Autre (reçu non rattaché)"

P1_SOURCE_LABEL = "Annexe 6 DPGF — somme p10_total_ht (imports actifs Lot 1 + Lot 2)"


def _classify_received_poste(line: CpeFinanceLine) -> str | None:
    """Classe une ligne de facture dans un poste contractuel, ou None si hors postes."""
    market = (line.market or "").strip().upper()
    item = normalize_p2p3_poste(line.billed_item)
    if market == "P1":
        return "P1"
    if item == "P2-4":
        return "P2-4"
    if item == "P3-4":
        return "P3-4"
    if market == "P2":
        return "P2"
    if market == "P3":
        return "P3"
    return None


def _line_year(line: CpeFinanceLine) -> int | None:
    anchor = line.period_end or line.period_start
    return anchor.year if anchor else None


def _cell(prevu: float, recu: float) -> dict[str, Any]:
    prevu = round(prevu, 2)
    recu = round(recu, 2)
    ecart = round(recu - prevu, 2)
    return {
        "prevu": prevu,
        "recu": recu,
        "ecart": ecart,
        "ecart_pct": round(ecart / prevu, 4) if prevu else None,
        "taux": round(recu / prevu, 4) if prevu else None,
    }


def build_market_tracking(
    db: Session,
    city_id: int | None = None,
    *,
    year_from: int = 2026,
    year_to: int = 2030,
) -> dict[str, Any]:
    """Construit la matrice poste × année (prévu DPGF vs reçu factures)."""
    if year_to < year_from:
        year_from, year_to = year_to, year_from
    years = list(range(year_from, year_to + 1))
    year_set = set(years)

    # ── Prévu (référentiel DALKIA actif) ─────────────────────────────────────
    prevu: dict[str, dict[int, float]] = {poste: {y: 0.0 for y in years} for poste in POSTE_ORDER}

    p2p3_stmt = (
        select(CpeDalkiaRefP2P3)
        .join(CpeDalkiaRefImport, CpeDalkiaRefP2P3.import_id == CpeDalkiaRefImport.id)
        .where(CpeDalkiaRefImport.is_active.is_(True))
    )
    if city_id is not None:
        p2p3_stmt = p2p3_stmt.where(CpeDalkiaRefImport.city_id == city_id)
    reference_rows = 0
    for row in db.scalars(p2p3_stmt).all():
        if row.period_year not in year_set:
            continue
        reference_rows += 1
        p2_4 = row.p2_4_ht or 0.0
        p3_4 = row.p3_4_ht or 0.0
        prevu["P2"][row.period_year] += (row.p2_total_ht or 0.0) - p2_4
        prevu["P2-4"][row.period_year] += p2_4
        prevu["P3"][row.period_year] += (row.p3_total_ht or 0.0) - p3_4
        prevu["P3-4"][row.period_year] += p3_4

    p1_stmt = (
        select(CpeDalkiaRefP1Gaz)
        .join(CpeDalkiaRefImport, CpeDalkiaRefP1Gaz.import_id == CpeDalkiaRefImport.id)
        .where(CpeDalkiaRefImport.is_active.is_(True))
    )
    if city_id is not None:
        p1_stmt = p1_stmt.where(CpeDalkiaRefImport.city_id == city_id)
    for row in db.scalars(p1_stmt).all():
        if row.period_year not in year_set:
            continue
        reference_rows += 1
        prevu["P1"][row.period_year] += row.p10_total_ht or 0.0

    # ── Reçu (factures DALKIA, périmètre CPE Ville) ──────────────────────────
    recu: dict[str, dict[int, float]] = {poste: {y: 0.0 for y in years} for poste in POSTE_ORDER}
    recu_other: dict[int, float] = {y: 0.0 for y in years}

    invoices = [
        invoice
        for invoice in list_finance_invoices(db, city_id=city_id)
        if _is_current_cpe_contract(
            db,
            invoice.contract_code,
            city_id=invoice.city_id,
            year=(invoice.period_end.year if invoice.period_end else None),
        )
    ]
    invoice_ids = [invoice.id for invoice in invoices]
    if invoice_ids:
        for line in db.scalars(
            select(CpeFinanceLine).where(CpeFinanceLine.invoice_id.in_(invoice_ids))
        ).all():
            year = _line_year(line)
            if year not in year_set:
                continue
            poste = _classify_received_poste(line)
            amount = line.amount_ht or 0.0
            if poste is None:
                recu_other[year] += amount
            else:
                recu[poste][year] += amount

    has_other = any(value for value in recu_other.values())

    # ── Construction de la sortie ────────────────────────────────────────────
    def _poste_row(poste: str, label: str, prevu_by_year: dict[int, float], recu_by_year: dict[int, float]) -> dict[str, Any]:
        by_year = [{"year": y, **_cell(prevu_by_year.get(y, 0.0), recu_by_year.get(y, 0.0))} for y in years]
        total_prevu = round(sum(prevu_by_year.get(y, 0.0) for y in years), 2)
        total_recu = round(sum(recu_by_year.get(y, 0.0) for y in years), 2)
        total = _cell(total_prevu, total_recu)
        return {"poste": poste, "label": label, "by_year": by_year, "total": total}

    postes = [_poste_row(poste, POSTE_LABELS[poste], prevu[poste], recu[poste]) for poste in POSTE_ORDER]
    if has_other:
        postes.append(_poste_row(POSTE_OTHER, POSTE_OTHER_LABEL, {y: 0.0 for y in years}, recu_other))

    totals_by_year = []
    for y in years:
        prevu_y = sum(prevu[poste][y] for poste in POSTE_ORDER)
        recu_y = sum(recu[poste][y] for poste in POSTE_ORDER) + recu_other[y]
        totals_by_year.append({"year": y, **_cell(prevu_y, recu_y)})

    grand_prevu = round(sum(cell["prevu"] for cell in totals_by_year), 2)
    grand_recu = round(sum(cell["recu"] for cell in totals_by_year), 2)
    grand_total = _cell(grand_prevu, grand_recu)

    return {
        "years": years,
        "postes": postes,
        "totals_by_year": totals_by_year,
        "grand_total": grand_total,
        "p1_source": P1_SOURCE_LABEL,
        "has_reference": reference_rows > 0,
    }


def build_market_tracking_workbook(
    db: Session,
    city_id: int | None = None,
    *,
    year_from: int = 2026,
    year_to: int = 2030,
) -> bytes:
    """Export XLSX de la matrice de suivi marché (prévu vs reçu, poste × année)."""
    report = build_market_tracking(db, city_id, year_from=year_from, year_to=year_to)
    years = report["years"]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Suivi marche"
    ws["A1"] = "Suivi facturation marché CPE — prévu (DPGF) vs reçu"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = f"Source du prévu P1 : {report['p1_source']}"
    ws["A2"].font = Font(italic=True, size=10, color="6B7280")

    header_row = 4
    headers = ["Poste"]
    for year in years:
        headers += [f"{year} Prévu", f"{year} Reçu", f"{year} Écart", f"{year} Taux"]
    headers += ["Total Prévu", "Total Reçu", "Total Écart", "Total Taux"]
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")

    def _write_cell_group(ws_row: int, start_col: int, cell: dict[str, Any]) -> None:
        ws.cell(row=ws_row, column=start_col, value=cell["prevu"]).number_format = '#,##0 "€"'
        ws.cell(row=ws_row, column=start_col + 1, value=cell["recu"]).number_format = '#,##0 "€"'
        ws.cell(row=ws_row, column=start_col + 2, value=cell["ecart"]).number_format = '#,##0 "€"'
        taux_cell = ws.cell(row=ws_row, column=start_col + 3, value=cell["taux"])
        taux_cell.number_format = "0.0%"

    row = header_row + 1
    for poste in report["postes"]:
        ws.cell(row=row, column=1, value=poste["label"]).font = Font(bold=True)
        col = 2
        for cell in poste["by_year"]:
            _write_cell_group(row, col, cell)
            col += 4
        _write_cell_group(row, col, poste["total"])
        row += 1

    # Ligne TOTAL marché
    ws.cell(row=row, column=1, value="TOTAL marché").font = Font(bold=True)
    ws.cell(row=row, column=1).fill = PatternFill("solid", fgColor="E5E7EB")
    col = 2
    for cell in report["totals_by_year"]:
        _write_cell_group(row, col, cell)
        col += 4
    _write_cell_group(row, col, report["grand_total"])
    for c in range(1, len(headers) + 1):
        ws.cell(row=row, column=c).fill = PatternFill("solid", fgColor="E5E7EB")

    ws.column_dimensions["A"].width = 34
    for c in range(2, len(headers) + 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(c)].width = 13
    ws.freeze_panes = "B5"

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()
