"""Tests du contrôle « base P2/P3 facturée vs forfait contractuel DALKIA » (Phase B).

Sémantique validée sur données réelles (CCAS 01) :
  - P2         → cpe_dalkia_ref_p2p3.p2_total_ht
  - P3.4       → p3_4_ht
  - P3 (autre) → p3_total_ht − p3_4_ht
`base_price` (euros base, stable) doit égaler ce forfait ; sinon erreur.
"""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe import CpeFinanceImportBatch, CpeFinanceInvoice, CpeFinanceLine
from app.models.cpe_dalkia import CpeDalkiaRefImport, CpeDalkiaRefP2P3
from app.services.cpe_accounting import _control_p2p3_base_against_dalkia
from app.services.cpe_dalkia_db import resolve_dalkia_p2p3_forfait

CONTRACT = "C00190116O"  # contrat CPE Ville courant


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


def _ref_p2p3(db: Session, **kw):
    imp = db.query(CpeDalkiaRefImport).first()
    if imp is None:
        imp = CpeDalkiaRefImport(city_id=1, lot=1, filename="L1.xlsx", is_active=True)
        db.add(imp)
        db.flush()
    db.add(CpeDalkiaRefP2P3(
        import_id=imp.id, city_id=1, period_idx=kw.get("period_idx", 1),
        period_label=str(kw["period_year"]), **kw,
    ))
    db.flush()


def _line(db: Session, *, market, billed_item, base_price, code_site="CCAS 01", year=2026):
    batch = db.query(CpeFinanceImportBatch).first()
    if batch is None:
        batch = CpeFinanceImportBatch(city_id=1, filename="finance.xlsx")
        db.add(batch)
        db.flush()
    inv = CpeFinanceInvoice(
        batch_id=batch.id, city_id=1, invoice_number="FAC-1", contract_code=CONTRACT,
        period_start=date(year, 1, 1), period_end=date(year, 3, 31),
    )
    db.add(inv)
    db.flush()
    line = CpeFinanceLine(
        batch_id=batch.id, invoice_id=inv.id, city_id=1, row_number=1,
        contract_code=CONTRACT, market=market, billed_item=billed_item,
        base_price=base_price, site_code_detected=code_site,
        period_start=date(year, 1, 1), period_end=date(year, 3, 31),
    )
    db.add(line)
    db.flush()
    return line, inv


def test_resolver_maps_postes_correctly(db_session: Session):
    """p3_total 7214 = P3 (1615) + P3.4 (5599) ; le resolver renvoie la bonne part par poste."""
    _ref_p2p3(db_session, code_site="CCAS 01", period_year=2026,
              p2_total_ht=3199, p3_total_ht=7214, p3_4_ht=5599)
    db_session.commit()
    f = lambda item: resolve_dalkia_p2p3_forfait(  # noqa: E731
        db_session, code_site="CCAS 01", year=2026, billed_item=item, city_id=1)
    assert f("P2") == pytest.approx(3199)
    assert f("P3.4") == pytest.approx(5599)
    assert f("P3") == pytest.approx(1615)  # 7214 − 5599


def test_p2_base_conforme(db_session: Session):
    _ref_p2p3(db_session, code_site="CCAS 01", period_year=2026, p2_total_ht=3199, p3_total_ht=7214, p3_4_ht=5599)
    line, inv = _line(db_session, market="P2", billed_item="P2", base_price=3199)
    db_session.commit()
    ctrl = _control_p2p3_base_against_dalkia(db_session, line, inv)
    assert ctrl is not None
    assert ctrl.control_type == "p2p3_base_dpgf"
    assert ctrl.status == "ok"


def test_p3_4_base_conforme(db_session: Session):
    _ref_p2p3(db_session, code_site="CCAS 01", period_year=2026, p2_total_ht=3199, p3_total_ht=7214, p3_4_ht=5599)
    line, inv = _line(db_session, market="P3", billed_item="P3.4", base_price=5599)
    db_session.commit()
    ctrl = _control_p2p3_base_against_dalkia(db_session, line, inv)
    assert ctrl.status == "ok"


def test_p3_base_ecart_detecte(db_session: Session):
    """Base P3 facturée 1700 alors que le contrat dit 1615 → erreur."""
    _ref_p2p3(db_session, code_site="CCAS 01", period_year=2026, p2_total_ht=3199, p3_total_ht=7214, p3_4_ht=5599)
    line, inv = _line(db_session, market="P3", billed_item="P3", base_price=1700)
    db_session.commit()
    ctrl = _control_p2p3_base_against_dalkia(db_session, line, inv)
    assert ctrl.status == "error"
    assert ctrl.expected_revised_price == pytest.approx(1615)
    assert ctrl.actual_revised_price == pytest.approx(1700)


def test_code_site_non_aligne_bloque(db_session: Session):
    """Aucun forfait pour ce code → statut blocked (détecteur de désalignement)."""
    _ref_p2p3(db_session, code_site="CCAS 01", period_year=2026, p2_total_ht=3199, p3_total_ht=7214, p3_4_ht=5599)
    line, inv = _line(db_session, market="P2", billed_item="P2", base_price=3199, code_site="CCAS01")  # sans espace
    db_session.commit()
    ctrl = _control_p2p3_base_against_dalkia(db_session, line, inv)
    assert ctrl.status == "blocked"


def test_skip_when_not_current_contract(db_session: Session):
    """Ligne hors contrat CPE Ville : pas de contrôle (None)."""
    _ref_p2p3(db_session, code_site="CCAS 01", period_year=2026, p2_total_ht=3199, p3_total_ht=7214, p3_4_ht=5599)
    line, inv = _line(db_session, market="P2", billed_item="P2", base_price=3199)
    inv.contract_code = "AUTRE_CONTRAT"
    line.contract_code = "AUTRE_CONTRAT"
    db_session.commit()
    assert _control_p2p3_base_against_dalkia(db_session, line, inv) is None
