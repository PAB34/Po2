import pytest

from app.models.invoice import EnergyInvoice, EnergyInvoiceImport, EnergyInvoiceSite
from app.services import supplier_invoice_pdf_control as svc


def _platform_invoice() -> EnergyInvoiceImport:
    invoice = EnergyInvoiceImport(
        invoice_number="150000071272",
        total_ttc=2084.66,
        supplier_guess="ENGIE",
        original_filename="MesFactures.xlsx",
        source="engie_xlsx",
    )
    invoice.normalized_invoice = EnergyInvoice(
        sites=[
            EnergyInvoiceSite(prm_id="24350217015563", site_name="GYMNASE FERRARI", segment="C5", summary_total_ttc=123.07),
            EnergyInvoiceSite(prm_id="24379594630562", site_name="GYMNASE MAURICE VIE", segment="C5", summary_total_ttc=308.15),
            EnergyInvoiceSite(prm_id="30002430947866", site_name="GYMNASE PAUL DI STEFANO", segment="C4", summary_total_ttc=492.01),
            EnergyInvoiceSite(prm_id="30002430957107", site_name="COMPLEXE SPORTIF DU BARROU", segment="C4", summary_total_ttc=354.80),
            EnergyInvoiceSite(prm_id="30002431203509", site_name="GYMNASE NAKACHE", segment="C4", summary_total_ttc=806.63),
        ]
    )
    return invoice


def _parsed_pdf() -> dict:
    return {
        "invoice": {"invoice_number": "150000071272", "total_ttc": 5359.09},
        "sites": [
            {"prm_id": "24350217015563", "delivery_site_name": "GYMNASE FERRARI", "segment": "C5", "fic_number": "220008710757", "total_ttc": 123.07},
            {"prm_id": "24379594630562", "delivery_site_name": "GYMNASE MAURICE VIE", "segment": "C5", "fic_number": "980006330534", "total_ttc": 308.15},
            {"prm_id": "30002430947866", "delivery_site_name": "GYMNASE PAUL DI STEFANO", "segment": "C4", "fic_number": "980006330456", "total_ttc": 492.01},
            {"prm_id": "30002430957107", "delivery_site_name": "COMPLEXE SPORTIF DU BARROU", "segment": "C4", "fic_number": "980006330467", "total_ttc": 354.80},
            {"prm_id": "30002431203509", "delivery_site_name": "GYMNASE NAKACHE", "segment": "C4", "fic_number": "980006330453", "total_ttc": 806.63},
            {"prm_id": "50023226811934", "delivery_site_name": "HALLES MARTY", "segment": "C4", "fic_number": "980006330511", "total_ttc": 3274.43},
        ],
        "parser_warnings": [],
    }


def test_engie_pdf_control_identifies_fic_missing_from_platform_export() -> None:
    result = svc.build_engie_pdf_control(_platform_invoice(), _parsed_pdf(), requested_number="150000071272")

    assert result["status"] == "export_incomplet"
    assert result["totals"]["platform_total_ttc"] == 2084.66
    assert result["totals"]["pdf_total_ttc"] == 5359.09
    assert result["totals"]["delta_platform_minus_pdf"] == -3274.43
    assert result["counts"] == {
        "pdf_sites_count": 6,
        "platform_sites_count": 5,
        "missing_in_platform_count": 1,
        "missing_in_pdf_count": 0,
    }
    assert result["missing_in_platform"] == [
        {
            "prm": "50023226811934",
            "site_name": "HALLES MARTY",
            "segment": "C4",
            "fic_number": "980006330511",
            "total_ttc": 3274.43,
            "pdf_page_start": None,
            "pdf_page_end": None,
        }
    ]
    assert "HALLES MARTY" in result["diagnosis"]
    assert "Reexporter/importer ENGIE" in result["recommendation"]


def test_engie_pdf_control_rejects_wrong_invoice_number() -> None:
    parsed = _parsed_pdf()
    parsed["invoice"]["invoice_number"] = "150000000000"

    with pytest.raises(svc.PdfControlError, match="pas la facture 150000071272"):
        svc.build_engie_pdf_control(_platform_invoice(), parsed, requested_number="150000071272")
