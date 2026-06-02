"""Tests de la synchro de la référence d'acompte P1 gaz depuis le RECAP (Phase C).

`sync_p1_reference_from_recap` doit écraser `annual_amount_ht` de la référence existante
avec la valeur RECAP (le RECAP fait foi), créer les années manquantes en clonant les
métadonnées, et refuser proprement quand il n'y a ni RECAP P1 ni référence modèle.
"""
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe import CpeContractReference
from app.models.cpe_dalkia import CpeDalkiaRefImport, CpeDalkiaRefRecap
from app.services.cpe_dalkia_db import sync_p1_reference_from_recap


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


def _add_import(db: Session, *, lot: int = 1, city_id: int = 1) -> CpeDalkiaRefImport:
    imp = CpeDalkiaRefImport(city_id=city_id, lot=lot, filename="L1.xlsx", is_active=True)
    db.add(imp)
    db.flush()
    return imp


def _add_recap_p1(db: Session, *, import_id: int, year: int, value: float, city_id: int = 1) -> None:
    db.add(CpeDalkiaRefRecap(
        import_id=import_id, city_id=city_id,
        section="redevance_p1", category="P1",
        metric="p1_total_ht", metric_label="P1 – Total (€HT)",
        period_year=year, period_label=str(year), value=value, unit="EUR_HT",
    ))
    db.flush()


def _seed_reference(db: Session, *, year: int = 2026, amount: float = 341293.06, city_id: int = 1) -> CpeContractReference:
    ref = CpeContractReference(
        city_id=city_id,
        contract_code="C00190116O",
        contract_label="SETE LOT 1",
        reference_kind="p1_gaz_acompte",
        year=year,
        market="P1",
        billed_item="P1_GAZ_LOT1",
        annual_amount_ht=amount,
        installment_count=4,
        expected_period_months="3,6,9",
        included_billed_items='["P1","CTA"]',
        formula="Acompte P1 gaz = 1/4 du P1 annuel DPGF revise",
        tolerance_pct=0.01,
        tolerance_eur=100.0,
    )
    db.add(ref)
    db.flush()
    return ref


def test_overwrites_existing_year_with_recap_value(db_session: Session):
    """Le RECAP fait foi : 341293,06 (seed) → 317775 (RECAP) pour 2026."""
    imp = _add_import(db_session)
    _add_recap_p1(db_session, import_id=imp.id, year=2026, value=317775.0)
    _seed_reference(db_session, year=2026, amount=341293.06)
    db_session.commit()

    res = sync_p1_reference_from_recap(db_session, imp)
    assert res["ok"] is True
    assert 2026 in res["updated"]

    ref = db_session.scalars(
        select(CpeContractReference).where(CpeContractReference.year == 2026)
    ).first()
    assert ref.annual_amount_ht == pytest.approx(317775.0)


def test_creates_missing_years_cloning_template(db_session: Session):
    """Les années sans référence sont créées en clonant contract_code/billed_item/installment."""
    imp = _add_import(db_session)
    _add_recap_p1(db_session, import_id=imp.id, year=2026, value=317775.0)
    _add_recap_p1(db_session, import_id=imp.id, year=2028, value=203625.0)
    _seed_reference(db_session, year=2026, amount=341293.06)
    db_session.commit()

    res = sync_p1_reference_from_recap(db_session, imp)
    assert res["ok"] is True
    assert 2028 in res["created"]

    ref_2028 = db_session.scalars(
        select(CpeContractReference).where(CpeContractReference.year == 2028)
    ).first()
    assert ref_2028 is not None
    assert ref_2028.contract_code == "C00190116O"
    assert ref_2028.billed_item == "P1_GAZ_LOT1"
    assert ref_2028.installment_count == 4
    assert ref_2028.annual_amount_ht == pytest.approx(203625.0)
    # acompte trimestriel attendu côté contrôle = annual / installment
    assert ref_2028.annual_amount_ht / ref_2028.installment_count == pytest.approx(50906.25)


def test_no_template_refuses_cleanly(db_session: Session):
    """Sans référence modèle, on n'invente pas de contract_code : refus explicite."""
    imp = _add_import(db_session)
    _add_recap_p1(db_session, import_id=imp.id, year=2026, value=317775.0)
    db_session.commit()

    res = sync_p1_reference_from_recap(db_session, imp)
    assert res["ok"] is False
    assert res["reason"] == "no_template"
    assert db_session.scalars(select(CpeContractReference)).first() is None


def test_no_recap_p1_returns_noop(db_session: Session):
    """Lot 2 (piscines) sans P1 gaz : aucun montant RECAP → no-op sans erreur dure."""
    imp = _add_import(db_session, lot=2)
    _seed_reference(db_session, year=2026)
    db_session.commit()

    res = sync_p1_reference_from_recap(db_session, imp)
    assert res["ok"] is False
    assert res["reason"] == "no_recap_p1"
    # la référence seed n'est pas touchée
    ref = db_session.scalars(select(CpeContractReference)).first()
    assert ref.annual_amount_ht == pytest.approx(341293.06)
