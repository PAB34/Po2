from pathlib import Path
from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe import CpeAccountingSiteMapping, CpeContractReference, CpeFinanceImportBatch, CpeFinanceInvoice, CpeFinanceLine, CpeRevisionIndex
from app.services import cpe_accounting
from app.services.cpe_accounting import extract_invoice_evidence_pdf, import_codification_workbook, import_finance_workbook, list_revision_observations, recompute_finance_invoice_controls


DATA_DIR = Path(__file__).resolve().parents[2] / "energie" / "DALKIA" / "COMPTABILITE"
CODIFICATION = DATA_DIR / "analyse_codification_dalkia_enrichie_par_code_contrat (1).xlsx"
FINANCE_EXPORT = DATA_DIR / "export_finances-20260527_1055.xlsx"


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.add_all([
            CpeContractReference(
                city_id=1,
                contract_code="C00190116O",
                contract_label="SETE LOT 1",
                reference_kind="cpe_contract_scope",
                year=2026,
                market="SCOPE",
                billed_item="CPE_VILLE_LOT_1",
                active=True,
            ),
            CpeContractReference(
                city_id=1,
                contract_code="C00190155J",
                contract_label="SETE LOT 2",
                reference_kind="cpe_contract_scope",
                year=2026,
                market="SCOPE",
                billed_item="CPE_VILLE_LOT_2",
                active=True,
            ),
        ])
        session.commit()
        yield session


@pytest.mark.skipif(not CODIFICATION.exists() or not FINANCE_EXPORT.exists(), reason="DALKIA local workbooks absent")
def test_enriched_codification_matches_finance_export_lines(db_session: Session):
    import_codification_workbook(
        db_session,
        CODIFICATION.read_bytes(),
        filename=CODIFICATION.name,
        city_id=1,
    )
    result = import_finance_workbook(
        db_session,
        FINANCE_EXPORT.read_bytes(),
        filename=FINANCE_EXPORT.name,
        city_id=1,
    )

    assert result.line_count == 2047
    assert result.matched_accounting_rules == 2047
    assert result.matched_site_mappings > 1200
    assert not any("sans nature comptable" in warning for warning in result.warnings)


def test_recompute_finance_invoice_controls_adds_global_and_accounting_checks(db_session: Session):
    batch = CpeFinanceImportBatch(city_id=1, filename="finance.xlsx")
    db_session.add(batch)
    db_session.flush()
    invoice = CpeFinanceInvoice(
        batch_id=batch.id,
        city_id=1,
        invoice_number="FAC-1",
        contract_code="C00190116O",
        invoice_type="AC",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        total_ht=125.0,
    )
    db_session.add(invoice)
    db_session.flush()
    site = CpeAccountingSiteMapping(city_id=1, code_site="VDS-ENS 01", site_name="Ecole test")
    db_session.add(site)
    db_session.flush()
    db_session.add(
        CpeContractReference(
            city_id=1,
            contract_code="C00190116O",
            contract_label="SETE LOT 1",
            reference_kind="p1_gaz_acompte",
            year=2026,
            market="P1",
            billed_item="P1_GAZ_LOT1",
            annual_amount_ht=341293.06,
            installment_count=4,
            expected_period_months="3,6,9",
            included_billed_items='["P1","CTA"]',
            formula="Acompte P1 gaz = 1/4 du P1 annuel DPGF revise",
            tolerance_pct=0.01,
            tolerance_eur=100.0,
        )
    )
    db_session.add_all(
        [
            CpeFinanceLine(
                batch_id=batch.id,
                invoice_id=invoice.id,
                city_id=1,
                row_number=2,
                contract_code="C00190116O",
                invoice_number="FAC-1",
                market="P1",
                service_sold="CHAUFFAGE",
                billed_item="P1.1",
                amount_ht=100.0,
                site_code_detected="VDS-ENS 01",
                accounting_site_id=site.id,
                accounting_nature="611",
                accounting_label="Energie",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
            ),
            CpeFinanceLine(
                batch_id=batch.id,
                invoice_id=invoice.id,
                city_id=1,
                row_number=3,
                contract_code="C00190116O",
                invoice_number="FAC-1",
                market="P2",
                service_sold="EXPLOITATION",
                billed_item="P2.1",
                amount_ht=25.0,
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
            ),
        ]
    )
    db_session.commit()

    controls = recompute_finance_invoice_controls(db_session, invoice)
    by_type = {}
    for control in controls:
        by_type.setdefault(control.control_type, []).append(control)

    assert by_type["invoice_type"][0].status == "ok"
    assert by_type["invoice_total_ht"][0].status == "ok"
    assert by_type["invoice_period"][0].status == "ok"
    assert [control.status for control in by_type["accounting_nature"]] == ["ok", "error"]
    assert [control.status for control in by_type["accounting_site"]] == ["ok", "blocked"]


def test_recompute_finance_invoice_controls_marks_out_of_scope_site_as_not_required(db_session: Session):
    batch = CpeFinanceImportBatch(city_id=1, filename="finance.xlsx")
    db_session.add(batch)
    db_session.flush()
    invoice = CpeFinanceInvoice(
        batch_id=batch.id,
        city_id=1,
        invoice_number="FAC-HORS-SCOPE",
        contract_code="C00032657J",
        invoice_type="AC",
        period_start=date(2026, 5, 1),
        period_end=date(2026, 5, 31),
        total_ht=100.0,
    )
    db_session.add(invoice)
    db_session.flush()
    db_session.add(
        CpeFinanceLine(
            batch_id=batch.id,
            invoice_id=invoice.id,
            city_id=1,
            row_number=2,
            contract_code="C00032657J",
            invoice_number="FAC-HORS-SCOPE",
            market="P1",
            service_sold="CHAUFFAGE",
            billed_item="P1",
            amount_ht=100.0,
            accounting_nature="60613",
            accounting_label="Chauffage urbain",
            period_start=date(2026, 5, 1),
            period_end=date(2026, 5, 31),
        )
    )
    db_session.commit()

    controls = recompute_finance_invoice_controls(db_session, invoice)
    site_control = next(control for control in controls if control.control_type == "accounting_site")

    assert site_control.status == "ok"
    assert "hors perimetre" in site_control.message


def test_recompute_finance_invoice_controls_checks_p1_gaz_acompte_against_dpgf(db_session: Session):
    batch = CpeFinanceImportBatch(city_id=1, filename="finance.xlsx")
    db_session.add(batch)
    db_session.flush()
    invoice = CpeFinanceInvoice(
        batch_id=batch.id,
        city_id=1,
        invoice_number="FAC-P1-Q1",
        contract_code="C00190116O",
        invoice_type="AC",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        total_ht=85323.27,
    )
    db_session.add(invoice)
    db_session.flush()
    site = CpeAccountingSiteMapping(city_id=1, code_site="VDS-ENS 01", site_name="Ecole test")
    db_session.add(site)
    db_session.flush()
    # Le controle P1 lit sa reference en base (pas de constante hardcodee) : on la cree.
    db_session.add(
        CpeContractReference(
            city_id=1,
            contract_code="C00190116O",
            contract_label="SETE LOT 1",
            reference_kind="p1_gaz_acompte",
            year=2026,
            market="P1",
            billed_item="P1_GAZ_LOT1",
            annual_amount_ht=341293.06,
            installment_count=4,
            expected_period_months="3,6,9",
            included_billed_items='["P1","CTA"]',
            formula="Acompte P1 gaz = 1/4 du P1 annuel DPGF revise",
            tolerance_pct=0.01,
            tolerance_eur=100.0,
        )
    )
    db_session.flush()
    db_session.add_all(
        [
            CpeFinanceLine(
                batch_id=batch.id,
                invoice_id=invoice.id,
                city_id=1,
                row_number=2,
                contract_code="C00190116O",
                invoice_number="FAC-P1-Q1",
                market="P1",
                service_sold="CHAUFFAGE",
                billed_item="P1",
                amount_ht=80000.0,
                site_code_detected="VDS-ENS 01",
                accounting_site_id=site.id,
                accounting_nature="60621",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 3, 31),
            ),
            CpeFinanceLine(
                batch_id=batch.id,
                invoice_id=invoice.id,
                city_id=1,
                row_number=3,
                contract_code="C00190116O",
                invoice_number="FAC-P1-Q1",
                market="P1",
                service_sold="REFACTURATION CTA",
                billed_item="CTA",
                amount_ht=5323.27,
                site_code_detected="VDS-ENS 01",
                accounting_site_id=site.id,
                accounting_nature="60621",
                period_start=date(2026, 1, 1),
                period_end=date(2026, 3, 31),
            ),
        ]
    )
    db_session.commit()

    controls = recompute_finance_invoice_controls(db_session, invoice)
    p1_control = next(control for control in controls if control.control_type == "p1_gaz_acompte_dpgf")

    assert p1_control.status == "ok"
    # acompte attendu = 1/4 du P1 annuel (341293.06 / 4) ; tolérant à l'arrondi flottant
    assert p1_control.expected_revised_price == pytest.approx(341293.06 / 4, abs=0.01)


def test_revision_observations_detect_dalkia_factor_and_compare_validated_indices(db_session: Session):
    batch = CpeFinanceImportBatch(city_id=1, filename="finance.xlsx")
    db_session.add(batch)
    db_session.flush()
    invoice = CpeFinanceInvoice(
        batch_id=batch.id,
        city_id=1,
        invoice_number="0001E2604AYR3",
        contract_code="C00190155J",
        invoice_type="EC",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        total_ht=23821.76,
    )
    db_session.add(invoice)
    db_session.flush()
    db_session.add_all(
        [
            CpeFinanceLine(
                batch_id=batch.id,
                invoice_id=invoice.id,
                city_id=1,
                row_number=2,
                contract_code="C00190155J",
                invoice_number=invoice.invoice_number,
                market="P2",
                amount_ht=11485.17,
                base_price=44920.0,
                revised_price=45940.67,
                period_start=invoice.period_start,
                period_end=invoice.period_end,
            ),
            CpeFinanceLine(
                batch_id=batch.id,
                invoice_id=invoice.id,
                city_id=1,
                row_number=3,
                contract_code="C00190155J",
                invoice_number=invoice.invoice_number,
                market="P2",
                amount_ht=12336.59,
                base_price=48250.0,
                revised_price=49346.34,
                period_start=invoice.period_start,
                period_end=invoice.period_end,
            ),
            CpeRevisionIndex(city_id=1, index_code="ICHT_IME", year=2026, quarter=1, value=138.5),
            CpeRevisionIndex(city_id=1, index_code="FSD2", year=2026, quarter=1, value=163.9),
        ]
    )
    db_session.commit()

    observations = list_revision_observations(db_session, 1)
    assert len(observations) == 1
    assert observations[0]["observed_factor"] == 1.022722
    assert observations[0]["expected_factor"] == 0.980432
    assert observations[0]["status"] == "conflict"
    assert observations[0]["line_count"] == 2

    for index in db_session.scalars(select(CpeRevisionIndex).where(CpeRevisionIndex.quarter == 1)).all():
        index.value = 146.9 if index.index_code == "ICHT_IME" else 164.7
    db_session.commit()

    observations = list_revision_observations(db_session, 1)
    assert observations[0]["expected_factor"] == 1.022722
    assert observations[0]["status"] == "matches_validated"


def test_extract_invoice_evidence_pdf_reads_declared_dalkia_indices(monkeypatch):
    text = """
    Facture n°0001E2604AYR3 du 31/03/2026
    Révision A - Révision au 31/03/2026
    ICHT SIME 146,90000 / 141,40000
    FSD2 FRAIS ET SERVICES DIVERS 2 164,70000 / 169,80000
    Coefficient de révision 1,022722
    """

    class FakePage:
        def extract_text(self):
            return text

    class FakeReader:
        def __init__(self, _stream):
            self.pages = [FakePage()]

    monkeypatch.setattr(cpe_accounting, "PdfReader", FakeReader)
    extracted = extract_invoice_evidence_pdf(b"fake-pdf")

    assert extracted["declared_invoice_number"] == "0001E2604AYR3"
    assert extracted["revision_date"] == date(2026, 3, 31)
    assert extracted["declared_factor"] == 1.022722
    assert extracted["declared_icht_ime"] == 146.9
    assert extracted["declared_fsd2"] == 164.7
