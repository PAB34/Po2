from pathlib import Path
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe import CpeAccountingSiteMapping, CpeFinanceImportBatch, CpeFinanceInvoice, CpeFinanceLine
from app.services.cpe_accounting import import_codification_workbook, import_finance_workbook, recompute_finance_invoice_controls


DATA_DIR = Path(__file__).resolve().parents[2] / "energie" / "DALKIA" / "COMPTABILITE"
CODIFICATION = DATA_DIR / "analyse_codification_dalkia_enrichie_par_code_contrat (1).xlsx"
FINANCE_EXPORT = DATA_DIR / "export_finances-20260527_1055.xlsx"


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
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
    assert p1_control.expected_revised_price == 85323.27
