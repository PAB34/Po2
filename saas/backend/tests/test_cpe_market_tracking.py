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
    CpeSite,
)
from app.models.cpe_dalkia import (
    CpeDalkiaRefImport,
    CpeDalkiaRefP1Elec,
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


def test_quarters_billed_counts_distinct_quarters(db_session):
    _seed_reference(db_session)
    # Q1 (jan-mars) via _seed_invoice
    _seed_invoice(db_session)
    report = build_market_tracking(db_session, 1, year_from=2026, year_to=2026)
    assert report["installments_per_year"] == 4
    q2026 = next(q for q in report["quarters_billed"] if q["year"] == 2026)
    assert q2026 == {"year": 2026, "billed": 1, "expected": 4}

    # Ajoute une facture Q2 (avr-juin) -> 2 trimestres facturés
    batch = CpeFinanceImportBatch(city_id=1, filename="fin_q2.xlsx")
    db_session.add(batch)
    db_session.flush()
    inv = CpeFinanceInvoice(
        batch_id=batch.id, city_id=1, invoice_number="INV-Q2", contract_code="C00190116O",
        period_start=date(2026, 4, 1), period_end=date(2026, 6, 30), total_ht=0.0,
    )
    db_session.add(inv)
    db_session.flush()
    db_session.add(CpeFinanceLine(
        batch_id=batch.id, invoice_id=inv.id, city_id=1, row_number=1,
        market="P1", billed_item="ABT", amount_ht=2000.0,
        period_start=date(2026, 4, 1), period_end=date(2026, 6, 30),
    ))
    db_session.commit()
    report2 = build_market_tracking(db_session, 1, year_from=2026, year_to=2026)
    q2026b = next(q for q in report2["quarters_billed"] if q["year"] == 2026)
    assert q2026b["billed"] == 2


def test_dju_block_real_vs_reference(db_session, monkeypatch):
    import app.services.energie as energie_mod

    # 2026 complet (12 mois, somme 1610), 2027 partiel (3 mois, somme 400)
    fake = [{"month": f"2026-{m:02d}", "dju_chauffe": 1610.0 / 12, "dju_froid": 0.0} for m in range(1, 13)]
    fake += [{"month": f"2027-{m:02d}", "dju_chauffe": 400.0 / 3, "dju_froid": 0.0} for m in range(1, 4)]
    monkeypatch.setattr(energie_mod, "get_dju_monthly", lambda: fake)

    # reference contractuelle lue depuis cpe_sites (mode = 1426)
    db_session.add(CpeSite(city_id=1, code_site="VDS-ENS 01", nom_site="X", categorie="ENS", nb_mwh_pci=0.0, dju_reference=1426.0))
    db_session.commit()

    report = build_market_tracking(db_session, 1, year_from=2026, year_to=2027)
    dju = report["dju"]
    assert dju["has_data"] is True
    assert dju["reference"] == 1426.0 and dju["base"] == 18
    y2026 = next(d for d in dju["by_year"] if d["year"] == 2026)
    assert y2026["months"] == 12 and y2026["complete"] is True
    assert round(y2026["dju_real"]) == 1610
    assert y2026["ratio"] == round(1610.0 / 1426.0, 4)  # ~1.129 => hiver +13 %
    y2027 = next(d for d in dju["by_year"] if d["year"] == 2027)
    assert y2027["months"] == 3 and y2027["complete"] is False  # annee incomplete -> partiel


def test_dju_block_absent_without_source(db_session, monkeypatch):
    import app.services.energie as energie_mod
    monkeypatch.setattr(energie_mod, "get_dju_monthly", lambda: [])
    report = build_market_tracking(db_session, 1, year_from=2026, year_to=2026)
    assert report["dju"]["has_data"] is False
    assert report["dju"]["by_year"] == []


def test_p1_elec_lot2_prevu_and_recu_routing(db_session):
    """Lot 2 piscines : le P1 Élec (Annexe 6.2) alimente le poste P1-ELEC en prévu,
    et un P1 facturé sur le contrat Lot 2 est routé vers P1-ELEC (pas P1 gaz)."""
    # Périmètre Lot 2 (C00190155J) avec billed_item lot-conscient
    db_session.add(
        CpeContractReference(
            city_id=1, contract_code="C00190155J", contract_label="LOT 2",
            reference_kind="cpe_contract_scope", year=2026, market="SCOPE",
            billed_item="CPE_VILLE_LOT_2", active=True,
        )
    )
    db_session.flush()

    imp = CpeDalkiaRefImport(city_id=1, lot=2, filename="L2.xlsx", is_active=True)
    db_session.add(imp)
    db_session.flush()
    db_session.add(CpeDalkiaRefP1Elec(
        import_id=imp.id, city_id=1, code_site="VDS-PSC-01", period_idx=2,
        period_label="2026", period_year=2026, p10_total_ht=94936.4,
    ))

    batch = CpeFinanceImportBatch(city_id=1, filename="finL2.xlsx")
    db_session.add(batch)
    db_session.flush()
    inv = CpeFinanceInvoice(
        batch_id=batch.id, city_id=1, invoice_number="INVL2", contract_code="C00190155J",
        period_start=date(2026, 1, 1), period_end=date(2026, 3, 31), total_ht=0.0,
    )
    db_session.add(inv)
    db_session.flush()
    db_session.add(CpeFinanceLine(
        batch_id=batch.id, invoice_id=inv.id, city_id=1, row_number=1,
        market="P1", billed_item="ABT", amount_ht=23734.0,
        period_start=date(2026, 1, 1), period_end=date(2026, 3, 31),
    ))
    db_session.commit()

    report = build_market_tracking(db_session, 1, year_from=2026, year_to=2026)
    by_poste = {p["poste"]: p for p in report["postes"]}
    # Prévu P1 Élec = 94936.4 ; le P1 gaz reste 0 (piscines sans gaz)
    assert by_poste["P1-ELEC"]["by_year"][0]["prevu"] == 94936.4
    assert by_poste["P1"]["by_year"][0]["prevu"] == 0.0
    # Le P1 facturé du Lot 2 est routé vers P1-ELEC, pas vers P1
    assert by_poste["P1-ELEC"]["by_year"][0]["recu"] == 23734.0
    assert by_poste["P1"]["by_year"][0]["recu"] == 0.0
    # Découpage par lot : le Lot 2 porte le P1 Élec
    lot2 = next(e for e in report["by_lot"] if e["lot"] == 2)
    l2_postes = {p["poste"]: p["total"] for p in lot2["postes"]}
    assert l2_postes["P1-ELEC"]["prevu"] == 94936.4 and l2_postes["P1-ELEC"]["recu"] == 23734.0


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
