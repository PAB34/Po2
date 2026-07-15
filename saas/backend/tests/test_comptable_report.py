from io import BytesIO
from pathlib import Path

import openpyxl
import pytest

from app.models.invoice import EnergyInvoice, EnergyInvoiceImport, EnergyInvoiceSite
from app.services import comptable_report
from app.services.comptable_report import (
    PlatformInvoice,
    WorklistInvoice,
    build_comptable_control_workbook,
    extract_supplier_invoice_number,
    parse_comptable_worklist,
)


COMPTA_DIR = Path(__file__).resolve().parents[2] / "energie" / "COMPTA"


@pytest.mark.parametrize(
    ("filename", "expected_count", "first_number"),
    [
        ("FACTURES ENGIE.xlsx", 25, "150000071294"),
        ("FACTURES DALKIA 2IEME TRIMESTRE.xlsx", 50, "0001E2607QRY8"),
    ],
)
def test_parse_comptable_worklist_real_files(filename: str, expected_count: int, first_number: str) -> None:
    workbook = COMPTA_DIR / filename
    if not workbook.exists():
        pytest.skip(f"Worklist comptable reelle absente: {workbook}")

    parsed = parse_comptable_worklist(workbook)

    assert parsed.sheet_name.startswith("_ShowList-")
    assert len(parsed.rows) == expected_count
    assert parsed.rows[0].supplier_invoice_number == first_number
    assert all(row.supplier_invoice_number for row in parsed.rows)
    assert all(row.total_ttc is not None for row in parsed.rows)


def test_extract_supplier_invoice_number_strict_token() -> None:
    assert extract_supplier_invoice_number("FAC. 150000071294 DU 07/07/2026") == "150000071294"
    assert extract_supplier_invoice_number(" FAC. 0001E2607QRY8 DU 30/06/2026 ") == "0001E2607QRY8"
    assert extract_supplier_invoice_number("TOTAL") is None


def test_build_report_creates_one_sheet_per_market_without_uploads() -> None:
    content = build_comptable_control_workbook(db=None, city_id=303, files_by_market={})
    wb = openpyxl.load_workbook(BytesIO(content), read_only=True, data_only=True)

    assert wb.sheetnames == ["Synthèse", "DALKIA", "ENGIE", "EDF", "TotalEnergies"]
    assert wb["Synthèse"]["A1"].value == "Synthèse - rapport de contrôle comptable"
    for sheet_name in ["DALKIA", "ENGIE", "EDF", "TotalEnergies"]:
        assert wb[sheet_name]["A1"].value == "Aucune facture à analyser"


def test_energy_revision_section_writes_bpu_and_turpe_ratios(monkeypatch) -> None:
    def fake_budget(_db, _city_id, *, year):
        return {
            "points": [
                {
                    "prm": "PRM-1",
                    "bpu_ratio": 1.12,
                    "turpe_ratio": 1.04,
                    "bpu_available": True,
                    "reference_source": "bpu",
                    "realise": 120.0,
                    "atterrissage": 240.0,
                }
            ]
        }

    monkeypatch.setattr(comptable_report.engie_elec_budget_revise, "build_engie_elec_budget_revise", fake_budget)
    workbook = openpyxl.Workbook()
    ws = workbook.active
    invoice = EnergyInvoiceImport(invoice_number="F-1", period_end="2026-07-01")
    invoice.normalized_invoice = EnergyInvoice(sites=[EnergyInvoiceSite(prm_id="PRM-1")])
    worklist = WorklistInvoice(
        row_number=2,
        accounting_number="202600001",
        supplier_invoice_number="F-1",
        label="FAC. F-1 DU 01/07/2026",
        total_ttc=120.0,
        invoice_date="01/07/2026",
        arrival_date=None,
        supplier_code=None,
        supplier_name="ENGIE",
        invoice_status=None,
        liquidation_status=None,
        market_code=None,
        raw={},
    )
    platform = PlatformInvoice(
        id=1,
        invoice_number="F-1",
        total_ttc=120.0,
        control_status="ok",
        decision_status="approved",
        raw=invoice,
    )

    comptable_report._write_energy_revision_section(None, 303, ws, 1, comptable_report.MARKETS[1], [(worklist, platform)])

    assert ws.cell(row=2, column=2).value == "PRM-1"
    assert ws.cell(row=2, column=4).value == 1.12
    assert ws.cell(row=2, column=5).value == 1.04
    assert ws.cell(row=2, column=9).value == 240.0