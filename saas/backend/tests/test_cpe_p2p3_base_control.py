"""Tests du contrôle « base P2/P3 facturée vs forfait contractuel DALKIA » (Phase B).

Sémantique validée sur données réelles (VDS-ENS 01 2026) :
  - P2   → p2_total_ht − p2_4_ht   (P2 récurrent = P2.1+P2.2+P2.3)
  - P2-4 → p2_4_ht
  - P3   → p3_total_ht − p3_4_ht
  - P3-4 → p3_4_ht
Les autres postes (P2-11, P2-2, P1…) ne sont pas contrôlés (pas de correspondance référentiel).
`base_price` (euros base) doit égaler ce forfait ; sinon erreur.
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

CONTRACT = "C00190116O"


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        # ENS 01 2026 : p2_total=2647 (récurrent 1173 + p2_4 1474), p3_total=5624 (récurrent 1093 + p3_4 4531)
        imp = CpeDalkiaRefImport(city_id=1, lot=1, filename="L1.xlsx", is_active=True)
        session.add(imp)
        session.flush()
        session.add(CpeDalkiaRefP2P3(
            import_id=imp.id, city_id=1, code_site="VDS-ENS 01", period_idx=2,
            period_label="2026", period_year=2026,
            p2_1_ht=762, p2_2_ht=0, p2_3_ht=411, p2_4_ht=1474, p2_total_ht=2647,
            p3_1_ht=1003, p3_2_ht=0, p3_3_ht=90, p3_4_ht=4531, p3_total_ht=5624,
        ))
        session.commit()
        yield session


def _line(db: Session, *, billed_item, base_price, code="VDS-ENS 01", year=2026, market=None):
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
        contract_code=CONTRACT, market=market or billed_item[:2], billed_item=billed_item,
        base_price=base_price, site_code_detected=code,
        period_start=date(year, 1, 1), period_end=date(year, 3, 31),
    )
    db.add(line)
    db.flush()
    return line, inv


def test_resolver_maps_postes_correctly(db_session: Session):
    f = lambda item: resolve_dalkia_p2p3_forfait(  # noqa: E731
        db_session, code_site="VDS-ENS 01", year=2026, billed_item=item, city_id=1)
    assert f("P2") == pytest.approx(1173)      # 2647 − 1474
    assert f("P2-4") == pytest.approx(1474)
    assert f("P2.4") == pytest.approx(1474)    # point == tiret
    assert f("P3") == pytest.approx(1093)      # 5624 − 4531
    assert f("P3.4") == pytest.approx(4531)
    assert f("P2-11") is None                  # sous-poste non rattachable
    assert f("P1") is None


def test_p2_recurrent_conforme(db_session: Session):
    line, inv = _line(db_session, billed_item="P2", base_price=1173)
    db_session.commit()
    ctrl = _control_p2p3_base_against_dalkia(db_session, line, inv)
    assert ctrl is not None and ctrl.status == "ok"


def test_p2_4_conforme(db_session: Session):
    line, inv = _line(db_session, billed_item="P2-4", base_price=1474, market="P2")
    db_session.commit()
    ctrl = _control_p2p3_base_against_dalkia(db_session, line, inv)
    assert ctrl is not None and ctrl.status == "ok"


def test_p3_recurrent_conforme(db_session: Session):
    line, inv = _line(db_session, billed_item="P3", base_price=1093)
    db_session.commit()
    assert _control_p2p3_base_against_dalkia(db_session, line, inv).status == "ok"


def test_p3_4_conforme(db_session: Session):
    line, inv = _line(db_session, billed_item="P3.4", base_price=4531, market="P3")
    db_session.commit()
    assert _control_p2p3_base_against_dalkia(db_session, line, inv).status == "ok"


def test_p3_ecart_detecte(db_session: Session):
    line, inv = _line(db_session, billed_item="P3", base_price=1700)
    db_session.commit()
    ctrl = _control_p2p3_base_against_dalkia(db_session, line, inv)
    assert ctrl.status == "error"
    assert ctrl.expected_revised_price == pytest.approx(1093)


def test_sous_poste_non_controle(db_session: Session):
    """P2-11 n'a pas de correspondance référentiel → aucun contrôle (None), pas d'erreur."""
    line, inv = _line(db_session, billed_item="P2-11", base_price=5000, market="P2")
    db_session.commit()
    assert _control_p2p3_base_against_dalkia(db_session, line, inv) is None


def test_code_site_non_aligne_bloque(db_session: Session):
    line, inv = _line(db_session, billed_item="P2", base_price=1173, code="CCAS99")
    db_session.commit()
    assert _control_p2p3_base_against_dalkia(db_session, line, inv).status == "blocked"


def test_skip_when_not_current_contract(db_session: Session):
    line, inv = _line(db_session, billed_item="P2", base_price=1173)
    inv.contract_code = "AUTRE"
    line.contract_code = "AUTRE"
    db_session.commit()
    assert _control_p2p3_base_against_dalkia(db_session, line, inv) is None
