"""Tests du suivi marché CPE (prévu DPGF vs reçu factures)."""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe import (
    CpeContractReference,
    CpeFinanceImportBatch,
    CpeFinanceInvoice,
    CpeFinanceLine,
)
from app.models.cpe_dalkia import (
    CpeDalkiaRefImport,
    CpeDalkiaRefP1Gaz,
    CpeDalkiaRefP2P3,
)
from app.services.cpe_market_tracking import build_market_tracking, build_market_tracking_workbook


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.add(
            CpeContractReference(
                city_id=1,
                contract_code="C00190116O",
                contract_label="LOT 1",
                reference_kind="cpe_contract_scope",
                year=2026,
                market="SCOPE",
                billed_item="CPE",
                active=True,
            )
        )
        session.commit()
        yield session


def _seed_reference(db: Session) -> None:
    imp = CpeDalkiaRefImport(city_id=1, lot=1, filename="L1.xlsx", is_active=True)
    db.add(imp)
    db.flush()
    db.add(
        CpeDalkiaRefP2P3(
            import_id=imp.id,
            city_id=1,
            code_site="VDS-ENS 01",
            period_idx=1,
            period_label="2026",
            period_year=2026,
            p2_total_ht=1000.0,
            p2_4_ht=200.0,
            p3_total_ht=5000.0,
            p3_4_ht=4000.0,
        )
    )
    db.add(
        CpeDalkiaRefP1Gaz(
            import_id=imp.id,
            city_id=1,
            code_site="VDS-ENS 01",
            period_idx=1,
            period_label="2026",
            period_year=2026,
            p10_total_ht=8000.0,
        )
    )
    db.commit()


def _seed_invoice(db: Session) -> None:
    batch = CpeFinanceImportBatch(city_id=1, filename="fin.xlsx")
    db.add(batch)
    db.flush()
    invoice = CpeFinanceInvoice(
        batch_id=batch.id,
        city_id=1,
        invoice_number="INV1",
        contract_code="C00190116O",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        total_ht=0.0,
    )
    db.add(invoice)
    db.flush()
    lines = [
        # P1 reçu = 2000 (market P1)
        ("P1", "ABT", 2000.0),
        # P2 reçu = 200 (market P2, billed_item P2 récurrent)
        ("P2", "P2", 200.0),
        # P2.4 reçu = 50
        ("P2", "P2.4", 50.0),
        # P3 reçu = 250 (market P3, hors P3.4)
        ("P3", "P3", 250.0),
        # P3.4 reçu = 1000
        ("P3", "P3.4", 1000.0),
        # non rattachable -> Autre
        ("EAU", "DIVERS", 99.0),
    ]
    for idx, (market, item, amount) in enumerate(lines, start=1):
        db.add(
            CpeFinanceLine(
                batch_id=batch.id,
                invoice_id=invoice.id,
                city_id=1,
                row_number=idx,
                market=market,
                billed_item=item,
                amount_ht=amount,
                period_start=date(2026, 1, 1),
                period_end=date(2026, 3, 31),
            )
        )
    db.commit()


def test_prevu_decomposition_by_poste(db_session):
    _seed_reference(db_session)
    report = build_market_tracking(db_session, 1, year_from=2026, year_to=2026)
    assert report["has_reference"] is True
    prevu = {p["poste"]: p["by_year"][0]["prevu"] for p in report["postes"]}
    # P2 récurrent = p2_total - p2_4 = 800 ; P2.4 = 200
    assert prevu["P2"] == 800.0
    assert prevu["P2-4"] == 200.0
    # P3 récurrent = p3_total - p3_4 = 1000 ; P3.4 = 4000
    assert prevu["P3"] == 1000.0
    assert prevu["P3-4"] == 4000.0
    # P1 = somme p10_total_ht
    assert prevu["P1"] == 8000.0


def test_recu_classification_and_other_bucket(db_session):
    _seed_reference(db_session)
    _seed_invoice(db_session)
    report = build_market_tracking(db_session, 1, year_from=2026, year_to=2026)
    recu = {p["poste"]: p["by_year"][0]["recu"] for p in report["postes"]}
    assert recu["P1"] == 2000.0
    assert recu["P2"] == 200.0
    assert recu["P2-4"] == 50.0
    assert recu["P3"] == 250.0
    assert recu["P3-4"] == 1000.0
    # ligne non rattachable -> poste AUTRE
    assert recu.get("AUTRE") == 99.0
    # totaux cohérents
    grand = report["grand_total"]
    assert grand["recu"] == round(2000 + 200 + 50 + 250 + 1000 + 99, 2)


def test_workbook_builds(db_session):
    _seed_reference(db_session)
    _seed_invoice(db_session)
    content = build_market_tracking_workbook(db_session, 1, year_from=2026, year_to=2030)
    assert content[:2] == b"PK"  # xlsx = zip


def test_empty_reference_flag(db_session):
    report = build_market_tracking(db_session, 1, year_from=2026, year_to=2030)
    assert report["has_reference"] is False
    assert report["grand_total"]["prevu"] == 0.0
    assert report["by_lot"] == []


def _seed_two_lots(db: Session) -> None:
    """Périmètre Lot 1 (C00190116O) + Lot 2 (C00190155J), références + factures par lot."""
    db.add_all(
        [
            CpeContractReference(
                city_id=1, contract_code="C00190155J", contract_label="LOT 2",
                reference_kind="cpe_contract_scope", year=2026, market="SCOPE",
                billed_item="CPE_VILLE_LOT_2", active=True,
            ),
            # remplace le billed_item du Lot 1 (fixture = 'CPE') par le format lot
            CpeContractReference(
                city_id=1, contract_code="C00190116O", contract_label="LOT 1",
                reference_kind="cpe_contract_scope", year=2027, market="SCOPE",
                billed_item="CPE_VILLE_LOT_1", active=True,
            ),
        ]
    )
    db.flush()
    for lot, code, p2, p1 in [(1, "C00190116O", 1000.0, 8000.0), (2, "C00190155J", 500.0, 0.0)]:
        imp = CpeDalkiaRefImport(city_id=1, lot=lot, filename=f"L{lot}.xlsx", is_active=True)
        db.add(imp)
        db.flush()
        db.add(CpeDalkiaRefP2P3(
            import_id=imp.id, city_id=1, code_site=f"S{lot}", period_idx=1,
            period_label="2026", period_year=2026, p2_total_ht=p2, p2_4_ht=0.0,
            p3_total_ht=0.0, p3_4_ht=0.0,
        ))
        if p1:
            db.add(CpeDalkiaRefP1Gaz(
                import_id=imp.id, city_id=1, code_site=f"S{lot}", period_idx=1,
                period_label="2026", period_year=2026, p10_total_ht=p1,
            ))
        batch = CpeFinanceImportBatch(city_id=1, filename=f"fin{lot}.xlsx")
        db.add(batch)
        db.flush()
        invoice = CpeFinanceInvoice(
            batch_id=batch.id, city_id=1, invoice_number=f"INV{lot}", contract_code=code,
            period_start=date(2026, 1, 1), period_end=date(2026, 3, 31), total_ht=0.0,
        )
        db.add(invoice)
        db.flush()
        db.add(CpeFinanceLine(
            batch_id=batch.id, invoice_id=invoice.id, city_id=1, row_number=1,
            market="P2", billed_item="P2", amount_ht=float(100 * lot),
            period_start=date(2026, 1, 1), period_end=date(2026, 3, 31),
        ))
    db.commit()


def test_by_lot_split(db_session):
    _seed_two_lots(db_session)
    report = build_market_tracking(db_session, 1, year_from=2026, year_to=2026)
    lots = {entry["lot"]: entry for entry in report["by_lot"]}
    assert set(lots) == {1, 2}
    # Lot 1 : prévu P2 = 1000, reçu P2 = 100 ; Lot 2 : prévu P2 = 500, reçu P2 = 200
    l1 = {p["poste"]: p["total"] for p in lots[1]["postes"]}
    l2 = {p["poste"]: p["total"] for p in lots[2]["postes"]}
    assert l1["P2"]["prevu"] == 1000.0 and l1["P2"]["recu"] == 100.0
    assert l2["P2"]["prevu"] == 500.0 and l2["P2"]["recu"] == 200.0
    assert lots[1]["contract_codes"] == ["C00190116O"]
    assert lots[2]["contract_codes"] == ["C00190155J"]
    # Le combiné reste la somme des lots.
    combined = {p["poste"]: p["total"] for p in report["postes"]}
    assert combined["P2"]["prevu"] == 1500.0 and combined["P2"]["recu"] == 300.0
