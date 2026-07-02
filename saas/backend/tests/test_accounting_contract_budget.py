"""Tests du budget contractuel → atterrissage par poste (stratégie §5bis).

Le budget de référence est le montant CONTRACTUEL (prévu DPGF DALKIA), le réalisé
vient des factures CPE par poste (`cpe_market_tracking`). Calcul à la volée, sans
persistance. Voir `docs/refonte-v1/cibles-contractuelles-budget-matrice-audit.md`.
"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.accounting_matrix import (
    AccountingMatrixContract,
    AccountingMatrixRule,
    AccountingMatrixVersion,
)
from app.models.city import City
from app.models.cpe import (
    CpeContractReference,
    CpeFinanceImportBatch,
    CpeFinanceInvoice,
    CpeFinanceLine,
)
from app.models.cpe_dalkia import CpeDalkiaRefImport, CpeDalkiaRefP1Gaz, CpeDalkiaRefP2P3
from app.services.accounting_contract_budget import build_contract_budget_landing


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        # Périmètre Lot 1 (billed_item lot-conscient pour le découpage par lot).
        session.add(
            CpeContractReference(
                city_id=1, contract_code="C00190116O", contract_label="LOT 1",
                reference_kind="cpe_contract_scope", year=2026, market="SCOPE",
                billed_item="CPE_VILLE_LOT_1", active=True,
            )
        )
        session.commit()
        yield session


def _seed_budget_and_invoices(db: Session) -> None:
    # Budget contractuel (prévu DPGF) : P1 gaz 8000, P2 1000 (dont P2.4 200), P3 5000 (dont P3.4 4000).
    imp = CpeDalkiaRefImport(city_id=1, lot=1, filename="L1.xlsx", is_active=True)
    db.add(imp)
    db.flush()
    db.add(CpeDalkiaRefP2P3(
        import_id=imp.id, city_id=1, code_site="VDS-ENS 01", period_idx=1,
        period_label="2026", period_year=2026,
        p2_total_ht=1000.0, p2_4_ht=200.0, p3_total_ht=5000.0, p3_4_ht=4000.0,
    ))
    db.add(CpeDalkiaRefP1Gaz(
        import_id=imp.id, city_id=1, code_site="VDS-ENS 01", period_idx=1,
        period_label="2026", period_year=2026, p10_total_ht=8000.0,
    ))
    # Réalisé : facture CPE T1 (P1 2000, P2 200, P2.4 50, P3 250, P3.4 1000).
    batch = CpeFinanceImportBatch(city_id=1, filename="fin.xlsx")
    db.add(batch)
    db.flush()
    invoice = CpeFinanceInvoice(
        batch_id=batch.id, city_id=1, invoice_number="INV1", contract_code="C00190116O",
        period_start=date(2026, 1, 1), period_end=date(2026, 3, 31), total_ht=0.0,
    )
    db.add(invoice)
    db.flush()
    for idx, (market, item, amount) in enumerate(
        [("P1", "ABT", 2000.0), ("P2", "P2", 200.0), ("P2", "P2.4", 50.0),
         ("P3", "P3", 250.0), ("P3", "P3.4", 1000.0)],
        start=1,
    ):
        db.add(CpeFinanceLine(
            batch_id=batch.id, invoice_id=invoice.id, city_id=1, row_number=idx,
            market=market, billed_item=item, amount_ht=amount,
            period_start=date(2026, 1, 1), period_end=date(2026, 3, 31),
        ))
    db.commit()


def _seed_matrix(db: Session) -> None:
    """Matrice DALKIA (contrat = même contract_code) avec règles scope→operation."""
    contract = AccountingMatrixContract(
        city_id=1, domain="cpe", supplier="DALKIA", contract_code="C00190116O", status="active",
    )
    db.add(contract)
    db.flush()
    version = AccountingMatrixVersion(
        matrix_contract_id=contract.id, version_label="v1", status="active",
    )
    db.add(version)
    db.flush()
    for scope, operation in [("p1", "OP-CHAUF"), ("p2", "OP-MAINT"), ("p3", "OP-TRAV")]:
        db.add(AccountingMatrixRule(
            matrix_version_id=version.id, stable_rule_key=f"k-{scope}",
            scope=scope, operation_number=operation, is_active=True,
        ))
    db.commit()


def test_budget_is_contractual_and_realise_is_cpe(db_session):
    _seed_budget_and_invoices(db_session)
    report = build_contract_budget_landing(db_session, 1, year=2026, today=date(2026, 3, 31))
    by_poste = {p["poste"]: p for p in report["postes"]}

    # Budget = prévu DPGF (contractuel) ; réalisé = reçu factures CPE.
    assert by_poste["P1"]["budget_contractuel"] == 8000.0
    assert by_poste["P1"]["realise"] == 2000.0
    assert by_poste["P2"]["budget_contractuel"] == 800.0  # 1000 - 200 (P2.4)
    assert by_poste["P2"]["realise"] == 200.0
    assert by_poste["P2-4"]["budget_contractuel"] == 200.0
    assert by_poste["P3"]["budget_contractuel"] == 1000.0  # 5000 - 4000 (P3.4)
    assert by_poste["P3-4"]["budget_contractuel"] == 4000.0


def test_atterrissage_is_fixed_contractual_amount(db_session):
    _seed_budget_and_invoices(db_session)
    report = build_contract_budget_landing(db_session, 1, year=2026, today=date(2026, 3, 31))
    by_poste = {p["poste"]: p for p in report["postes"]}

    # Poste avec budget connu : atterrissage = montant contractuel (on projette le plein annuel).
    p1 = by_poste["P1"]
    assert p1["atterrissage"] == 8000.0
    assert p1["landing_method"] == "contractuel_fixe"
    assert p1["reste_a_facturer"] == 6000.0  # 8000 - 2000 facturés
    assert p1["ecart_realise_vs_budget"] == -6000.0
    assert p1["ecart_atterrissage_vs_budget"] == 0.0


def test_prorata_fallback_when_budget_unknown(db_session):
    """Un poste facturé sans budget contractuel (prévu=0) retombe sur un pro-rata temporel."""
    # Facture P1 sans aucune référence DPGF -> budget 0, réalisé 2500 à 50 % de l'année.
    batch = CpeFinanceImportBatch(city_id=1, filename="fin.xlsx")
    db_session.add(batch)
    db_session.flush()
    invoice = CpeFinanceInvoice(
        batch_id=batch.id, city_id=1, invoice_number="INV1", contract_code="C00190116O",
        period_start=date(2026, 1, 1), period_end=date(2026, 6, 30), total_ht=0.0,
    )
    db_session.add(invoice)
    db_session.flush()
    db_session.add(CpeFinanceLine(
        batch_id=batch.id, invoice_id=invoice.id, city_id=1, row_number=1,
        market="P1", billed_item="ABT", amount_ht=2500.0,
        period_start=date(2026, 1, 1), period_end=date(2026, 6, 30),
    ))
    db_session.commit()

    # 2026-07-02 ~ 50 % de l'année -> atterrissage ~ 2 * réalisé.
    report = build_contract_budget_landing(db_session, 1, year=2026, today=date(2026, 7, 2))
    p1 = next(p for p in report["postes"] if p["poste"] == "P1")
    assert p1["budget_contractuel"] == 0.0
    assert p1["landing_method"] == "prorata"
    assert p1["atterrissage"] > p1["realise"]  # extrapolation fin d'année


def test_projection_on_operations_from_matrix_rules(db_session):
    _seed_budget_and_invoices(db_session)
    _seed_matrix(db_session)
    report = build_contract_budget_landing(db_session, 1, year=2026, today=date(2026, 3, 31))
    by_op = {r["operation_number"]: r for r in report["by_operation"]}

    # P1 -> OP-CHAUF ; P2 + P2.4 -> OP-MAINT ; P3 + P3.4 -> OP-TRAV.
    assert by_op["OP-CHAUF"]["budget_contractuel"] == 8000.0
    assert set(by_op["OP-MAINT"]["postes"]) == {"P2", "P2-4"}
    assert by_op["OP-MAINT"]["budget_contractuel"] == 1000.0  # 800 + 200
    assert by_op["OP-TRAV"]["budget_contractuel"] == 5000.0  # 1000 + 4000


def test_no_matrix_means_poste_only(db_session):
    _seed_budget_and_invoices(db_session)  # pas de matrice seedée
    report = build_contract_budget_landing(db_session, 1, year=2026, today=date(2026, 3, 31))
    assert report["by_operation"] == []
    assert "indisponible" in report["projection_note"]


def test_lot_filter(db_session):
    _seed_budget_and_invoices(db_session)
    report = build_contract_budget_landing(db_session, 1, year=2026, lot=1, today=date(2026, 3, 31))
    assert report["lot"] == 1
    assert report["contract_codes"] == ["C00190116O"]
    assert any(p["budget_contractuel"] for p in report["postes"])


def _seed_revised_p2_line(db: Session, *, base: float, revised: float, quarter_end: date) -> None:
    """Ajoute une ligne P2 facturée avec prix_de_base et prix_revise (coefficient de révision)."""
    batch = CpeFinanceImportBatch(city_id=1, filename="rev.xlsx")
    db.add(batch)
    db.flush()
    invoice = CpeFinanceInvoice(
        batch_id=batch.id, city_id=1, invoice_number="INV-REV", contract_code="C00190116O",
        period_start=date(quarter_end.year, quarter_end.month - 2, 1), period_end=quarter_end, total_ht=0.0,
    )
    db.add(invoice)
    db.flush()
    db.add(CpeFinanceLine(
        batch_id=batch.id, invoice_id=invoice.id, city_id=1, row_number=1,
        market="P2", billed_item="P2", amount_ht=revised / 4,
        base_price=base, revised_price=revised,
        period_start=date(quarter_end.year, quarter_end.month - 2, 1), period_end=quarter_end,
    ))
    db.commit()


def test_revision_coefficient_inflates_budget(db_session):
    """Le budget contractuel P2 = budget base × coefficient de révision observé (revised/base)."""
    _seed_budget_and_invoices(db_session)  # budget base P2 = 800
    # Coefficient observé T1 = 220/200 = 1,10 sur une ligne P2 révisée.
    _seed_revised_p2_line(db_session, base=200.0, revised=220.0, quarter_end=date(2026, 3, 31))

    report = build_contract_budget_landing(db_session, 1, year=2026, today=date(2026, 3, 31))
    p2 = next(p for p in report["postes"] if p["poste"] == "P2")
    assert p2["budget_base"] == 800.0
    assert p2["coefficient_revision"] == 1.1
    assert p2["budget_contractuel"] == 880.0  # 800 × 1,10 (gonflé par la révision)
    assert p2["landing_method"] == "contractuel_revise"
    # P1 (aucune ligne révisée) reste au budget base, coef 1,0.
    p1 = next(p for p in report["postes"] if p["poste"] == "P1")
    assert p1["coefficient_revision"] == 1.0
    assert p1["budget_contractuel"] == p1["budget_base"]


def test_p3_4_is_revised_like_p3(db_session):
    """P3.4 (travaux programmés) suit le coefficient de révision du marché P3."""
    _seed_budget_and_invoices(db_session)  # budget base P3.4 = 4000
    # Ligne P3 révisée -> coefficient P3 = 1050/1000 = 1,05, appliqué à P3 ET P3-4.
    batch = CpeFinanceImportBatch(city_id=1, filename="rev3.xlsx")
    db_session.add(batch)
    db_session.flush()
    invoice = CpeFinanceInvoice(
        batch_id=batch.id, city_id=1, invoice_number="INV-P3", contract_code="C00190116O",
        period_start=date(2026, 1, 1), period_end=date(2026, 3, 31), total_ht=0.0,
    )
    db_session.add(invoice)
    db_session.flush()
    db_session.add(CpeFinanceLine(
        batch_id=batch.id, invoice_id=invoice.id, city_id=1, row_number=1,
        market="P3", billed_item="P3", amount_ht=262.5, base_price=1000.0, revised_price=1050.0,
        period_start=date(2026, 1, 1), period_end=date(2026, 3, 31),
    ))
    db_session.commit()

    report = build_contract_budget_landing(db_session, 1, year=2026, today=date(2026, 3, 31))
    by_poste = {p["poste"]: p for p in report["postes"]}
    assert by_poste["P3"]["coefficient_revision"] == 1.05
    assert by_poste["P3-4"]["coefficient_revision"] == 1.05
    assert by_poste["P3-4"]["budget_contractuel"] == 4200.0  # 4000 × 1,05
