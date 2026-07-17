from datetime import date
from io import BytesIO
from pathlib import Path

import openpyxl
import pytest

from app.models.cpe import CpeAccountingSiteMapping, CpeFinanceControl, CpeFinanceInvoice, CpeFinanceLine
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
        problem_summary=None,
        raw=invoice,
    )

    comptable_report._write_energy_revision_section(None, 303, ws, 1, comptable_report.MARKETS[1], [(worklist, platform)])

    assert ws.cell(row=2, column=2).value == "PRM-1"
    assert ws.cell(row=2, column=4).value == 1.12
    assert ws.cell(row=2, column=5).value == 1.04
    assert ws.cell(row=2, column=9).value == 240.0


def test_cpe_accounting_summary_writes_invoice_level_prices_and_codes() -> None:
    class FakeScalarResult:
        def __init__(self, rows):
            self.rows = rows

        def all(self):
            return self.rows

    class FakeScalarDb:
        def __init__(self, sequences):
            self.sequences = list(sequences)

        def scalars(self, _stmt):
            return FakeScalarResult(self.sequences.pop(0))

    invoice = CpeFinanceInvoice(id=10, invoice_number="D-1", contract_code="C001", total_ht=120.0)
    worklist = WorklistInvoice(
        row_number=2,
        accounting_number="202600001",
        supplier_invoice_number="D-1",
        label="FAC. D-1 DU 30/06/2026",
        total_ttc=144.0,
        invoice_date="30/06/2026",
        arrival_date=None,
        supplier_code=None,
        supplier_name="DALKIA",
        invoice_status=None,
        liquidation_status=None,
        market_code=None,
        raw={},
    )
    platform = PlatformInvoice(
        id=10,
        invoice_number="D-1",
        total_ttc=144.0,
        control_status="blocked",
        decision_status="a_controler",
        problem_summary="Imputation comptable absente",
        raw=invoice,
    )
    lines = [
        CpeFinanceLine(
            id=1,
            invoice_id=10,
            row_number=1,
            market="P2",
            billed_item="P2",
            accounting_site_id=100,
            site_code_detected="S1",
            base_price=1000.0,
            revised_price=1030.0,
            accounting_nature="6156",
            accounting_label="Maintenance",
        ),
        CpeFinanceLine(
            id=2,
            invoice_id=10,
            row_number=2,
            market="P3",
            billed_item="P3.4",
            accounting_site_id=100,
            site_code_detected="S1",
            base_price=500.0,
            revised_price=515.0,
            accounting_nature=None,
        ),
    ]
    controls = [
        CpeFinanceControl(
            invoice_id=10,
            line_id=1,
            control_type="revision_p2",
            index_year=2026,
            index_quarter=2,
            delta_abs=0.01,
        )
    ]
    sites = [
        CpeAccountingSiteMapping(
            id=100,
            code_site="S1",
            site_name="Site 1",
            service_code="020",
            function_code="F01",
            antenna_code="A01",
            operation_code="98004",
        )
    ]
    db = FakeScalarDb([lines, controls, sites])

    summary = comptable_report._cpe_line_enrichments(db, [(worklist, platform)])[10]

    assert summary["base_price"] == 1500.0
    assert summary["revised_price"] == 1545.0
    assert summary["revision_amount"] == 45.0
    assert summary["revision_delta"] == 0.01
    assert summary["revision_control"] == "2026 T2"
    assert "service: 020" in summary["accounting"]
    assert "operation: 98004" in summary["accounting"]
    assert "nature: 6156 - Maintenance" in summary["accounting"]
    assert summary["issue"] == "A completer : 1 nature(s) a completer"



def test_dalkia_sheet_matches_accountant_model_for_p3_invoice() -> None:
    class FakeScalarResult:
        def __init__(self, rows):
            self.rows = rows

        def all(self):
            return self.rows

    class FakeScalarDb:
        def __init__(self, sequences):
            self.sequences = list(sequences)

        def scalars(self, _stmt):
            return FakeScalarResult(self.sequences.pop(0))

    invoice = CpeFinanceInvoice(
        id=10,
        invoice_number="0001E2607QRY8",
        contract_code="C00190116O",
        invoice_date=date(2026, 6, 30),
        total_ht=457.86,
        status="valide",
    )
    worklist = WorklistInvoice(
        row_number=2,
        accounting_number="202605379",
        supplier_invoice_number="0001E2607QRY8",
        label="FAC. 0001E2607QRY8 DU 30/06/2026",
        total_ttc=549.43,
        invoice_date=date(2026, 6, 30),
        arrival_date=None,
        supplier_code=None,
        supplier_name="DALKIA",
        invoice_status=None,
        liquidation_status=None,
        market_code=None,
        raw={},
    )
    platform = {
        "0001E2607QRY8": PlatformInvoice(
            id=10,
            invoice_number="0001E2607QRY8",
            total_ttc=549.43,
            control_status="valid",
            decision_status="valide",
            problem_summary=None,
            raw=invoice,
        )
    }
    line = CpeFinanceLine(
        id=1,
        invoice_id=10,
        row_number=1,
        contract_code="C00190116O",
        market="P3",
        billed_item="P3",
        service_sold="P3 - GARANTIE TOTALE",
        vat_rate=20,
        amount_ht=457.86,
        base_price=1775.0,
        revised_price=1831.42,
        detail="ENTRETIEN VDS-ENS 19 - CENTRE DE LOISIR LE VALLON-ALSH P3 - GARANTIE TOTALE",
        accounting_site_id=100,
        site_code_detected="VDS-ENS 19",
        accounting_nature="6156",
        accounting_label="Maintenance",
    )
    site = CpeAccountingSiteMapping(
        id=100,
        code_site="VDS-ENS 19",
        site_name="Centre de loisir Le Vallon",
        manager="BATI",
        service_code="XSCO",
        function_code="331",
        antenna_code="ALSH",
    )
    db = FakeScalarDb([[line], [site]])
    workbook = openpyxl.Workbook()
    ws = workbook.active
    parsed = comptable_report.WorklistParseResult(sheet_name="_ShowList-001", rows=[worklist])

    comptable_report._write_market_sheet(db, 303, ws, comptable_report.MARKETS[0], parsed, platform)

    assert ws.cell(row=4, column=1).value == "CODE CONTRAT"
    assert ws.cell(row=4, column=13).value == "VIREMENT OK"
    assert ws.cell(row=5, column=4).value == "P3"
    assert ws.cell(row=5, column=6).value == 457.86
    assert ws.cell(row=5, column=7).value == '=IFERROR(+J5*F5/H5,"")'
    assert ws.cell(row=5, column=8).value == 1831.42
    assert ws.cell(row=5, column=9).value == 1775.0
    assert ws.cell(row=5, column=10).value == "=+H5-I5"
    assert ws.cell(row=5, column=12).value == "BATI-331-21351-98003-XSCO-ALSH"
    assert ws.cell(row=5, column=13).value == '=IFERROR(+F5*(1+E5/100),"")'
    assert ws.cell(row=5, column=16).value is None


def test_report_translates_decisions_and_writes_problem_summary(monkeypatch) -> None:
    monkeypatch.setattr(
        comptable_report,
        "_market_line_enrichments",
        lambda *args: {1: {"issue": "Codification incomplete", "revision_amount": 12.0, "revision_delta": 0.5, "revision_control": "BPU 1.0"}},
    )
    workbook = openpyxl.Workbook()
    ws = workbook.active
    parsed = comptable_report.WorklistParseResult(
        sheet_name="_ShowList-001",
        rows=[
            WorklistInvoice(
                row_number=2,
                accounting_number="202600001",
                supplier_invoice_number="F-ENGIE-1",
                label="FAC. F-ENGIE-1 DU 01/07/2026",
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
        ],
    )
    platform = {
        "F-ENGIE-1": PlatformInvoice(
            id=1,
            invoice_number="F-ENGIE-1",
            total_ttc=120.0,
            control_status="valid (0 erreur(s), 1 alerte(s))",
            decision_status="to_review",
            problem_summary="Ecart prix BPU",
            raw=EnergyInvoiceImport(invoice_number="F-ENGIE-1"),
        )
    }

    comptable_report._write_market_sheet(None, 303, ws, comptable_report.MARKETS[1], parsed, platform)

    assert ws.cell(row=4, column=5).value == "TTC Chorus / compta"
    assert ws.cell(row=4, column=6).value == "TTC Po2 reconstruit"
    assert ws.cell(row=4, column=7).value == "Ecart TTC Po2 - Chorus"
    assert ws.cell(row=4, column=13).value == "Revision appliquee"
    assert ws.cell(row=4, column=14).value == "Ecart revision"
    assert ws.cell(row=4, column=15).value == "Controle indices / ratios"
    assert ws.cell(row=4, column=17).value == "Point a corriger"
    assert ws.cell(row=5, column=9).value == "Conforme (0 erreur(s), 1 alerte(s))"
    assert ws.cell(row=5, column=10).value == comptable_report._decision_label("energy", "to_review")
    assert ws.cell(row=5, column=13).value == 12.0
    assert ws.cell(row=5, column=14).value == 0.5
    assert ws.cell(row=5, column=15).value == "BPU 1.0"
    assert ws.cell(row=5, column=17).value == "Ecart prix BPU ; Codification incomplete"
    assert ws.cell(row=8, column=1).value is None


def test_report_forces_review_when_chorus_total_differs_from_po2(monkeypatch) -> None:
    monkeypatch.setattr(comptable_report, "_market_line_enrichments", lambda *args: {})
    workbook = openpyxl.Workbook()
    ws = workbook.active
    parsed = comptable_report.WorklistParseResult(
        sheet_name="_ShowList-001",
        rows=[
            WorklistInvoice(
                row_number=2,
                accounting_number="202600001",
                supplier_invoice_number="F-ENGIE-1",
                label="FAC. F-ENGIE-1 DU 01/07/2026",
                total_ttc=5359.09,
                invoice_date="01/07/2026",
                arrival_date=None,
                supplier_code=None,
                supplier_name="ENGIE",
                invoice_status=None,
                liquidation_status=None,
                market_code=None,
                raw={},
            )
        ],
    )
    invoice = EnergyInvoiceImport(invoice_number="F-ENGIE-1")
    invoice.normalized_invoice = EnergyInvoice(
        sites=[EnergyInvoiceSite(prm_id=f"PRM-{index}") for index in range(1, 6)]
    )
    platform = {
        "F-ENGIE-1": PlatformInvoice(
            id=1,
            invoice_number="F-ENGIE-1",
            total_ttc=2084.66,
            control_status="valid",
            decision_status="approved",
            problem_summary=None,
            raw=invoice,
        )
    }

    comptable_report._write_market_sheet(None, 303, ws, comptable_report.MARKETS[1], parsed, platform)

    assert ws.cell(row=5, column=1).value == "\u00c9cart TTC"
    assert ws.cell(row=5, column=7).value == -3274.43
    assert ws.cell(row=5, column=9).value == "\u00c9cart TTC"
    assert ws.cell(row=5, column=10).value == "\u00c0 contr\u00f4ler"
    assert ws.cell(row=5, column=17).value == (
        "\u00c9cart TTC Po2 - Chorus : -3274.43 EUR. "
        "Po2 contient 5 site(s) ; 5 PRM ; 2084.66 EUR TTC import\u00e9s ; "
        "Chorus/compta attend 5359.09 EUR TTC. "
        "Il manque probablement une ou plusieurs FIC/sites dans l'export fournisseur import\u00e9. "
        "Comparer avec le PDF fournisseur Chorus."
    )

def test_row_problem_summary_explains_ttc_gap_before_decision() -> None:
    current = PlatformInvoice(
        id=1,
        invoice_number="F-1",
        total_ttc=130.0,
        control_status="valid",
        decision_status="approved",
        problem_summary=None,
        raw=object(),
    )

    assert comptable_report._row_problem_summary("Écart TTC", 10.0, current) == "Écart TTC Po2 - Chorus : 10.00 EUR."


class _FakeExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDb:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, _stmt):
        return _FakeExecuteResult(self._rows)


def test_cpe_control_summaries_identify_real_dalkia_control_reasons() -> None:
    db = _FakeDb(
        [
            (1, "error", "p2p3_base_dpgf", "Montant divergent"),
            (1, "blocked", "accounting_site", "Site absent"),
            (2, "ok", "invoice_total_ht", "OK"),
        ]
    )

    summaries = comptable_report._cpe_control_summaries(db, [1, 2, 3])

    assert summaries[1]["control_status"] == "error (1 écart(s), 1 bloqué(s))"
    assert "Montant P2/P3 différent du DPGF" in summaries[1]["problem_summary"]
    assert "Site comptable non rattaché" in summaries[1]["problem_summary"]
    assert summaries[2] == {"control_status": "valid", "problem_summary": None}
    assert summaries[3] == {
        "control_status": "not_checked",
        "problem_summary": "Aucun contrôle CPE disponible pour cette facture.",
    }
