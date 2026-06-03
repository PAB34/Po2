"""Tests du contrôle « prix unitaire gaz facturé vs prix fixe OS N°3 » (2026-2030).

Le base_price des lignes P1/CHAUFFAGE porte le Pu gaz (€/MWhPCS). Pour 2026-2030, il doit égaler
le prix OS N°3 du tarif du site (cpe_prix_gaz, stocké en PCI → converti en PCS).
Validé sur données réelles : CCAS 04 (T3) facture 70,78 en 2026 = OS N°3 T3.
"""
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe import CpeContractReference, CpeFinanceImportBatch, CpeFinanceInvoice, CpeFinanceLine, CpePrixGaz
from app.models.cpe_dalkia import CpeDalkiaRefImport, CpeDalkiaRefP1Gaz
from app.services.cpe import PCS_PCI_RATIO
from app.services.cpe_accounting import _control_p1_gaz_pu_os3

CONTRACT = "C00190116O"
# OS N°3 T3 : 70,78 €/MWhPCS -> PCI = 70,78 × 1,1068 ≈ 78,34 (doc indique 78,42, on prend la vraie conversion)
PCI_T3 = round(70.78 * PCS_PCI_RATIO, 2)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.add(CpeContractReference(
            city_id=1,
            contract_code=CONTRACT,
            contract_label="SETE LOT 1",
            reference_kind="cpe_contract_scope",
            year=2026,
            market="SCOPE",
            billed_item="CPE_VILLE_LOT_1",
            active=True,
        ))
        # tarif du site CCAS 04 = T3 (import DALKIA actif)
        imp = CpeDalkiaRefImport(city_id=1, lot=1, filename="L1.xlsx", is_active=True)
        session.add(imp)
        session.flush()
        session.add(CpeDalkiaRefP1Gaz(
            import_id=imp.id, city_id=1, code_site="CCAS 04", type_tarif="T3",
            period_idx=1, period_label="2026", period_year=2026,
        ))
        # prix OS N°3 T3 2026 (stocke en PCI)
        session.add(CpePrixGaz(annee=2026, tarif="T3", pu_eur_mwh_pci=PCI_T3))
        session.commit()
        yield session


def _line(db: Session, *, base_price, service="CHAUFFAGE", code="CCAS 04", year=2026, market="P1"):
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
        contract_code=CONTRACT, market=market, service_sold=service, billed_item="P1",
        base_price=base_price, site_code_detected=code,
        period_start=date(year, 1, 1), period_end=date(year, 3, 31),
    )
    db.add(line)
    db.flush()
    return line, inv


def test_pu_conforme_os3(db_session: Session):
    line, inv = _line(db_session, base_price=70.78)
    db_session.commit()
    ctrl = _control_p1_gaz_pu_os3(db_session, line, inv)
    assert ctrl is not None
    assert ctrl.control_type == "p1_gaz_pu_os3"
    assert ctrl.status == "ok"


def test_pu_ecart_detecte(db_session: Session):
    line, inv = _line(db_session, base_price=80.0)
    db_session.commit()
    ctrl = _control_p1_gaz_pu_os3(db_session, line, inv)
    assert ctrl.status == "error"
    assert ctrl.expected_revised_price == pytest.approx(round(PCI_T3 / PCS_PCI_RATIO, 2))


def test_montant_hors_plage_pu_skip(db_session: Session):
    """base_price = montant annuel (2889) → pas une ligne de prix unitaire → None."""
    line, inv = _line(db_session, base_price=2889.26)
    db_session.commit()
    assert _control_p1_gaz_pu_os3(db_session, line, inv) is None


def test_non_chauffage_skip(db_session: Session):
    line, inv = _line(db_session, base_price=70.78, service="REFACTURATION CTA")
    db_session.commit()
    assert _control_p1_gaz_pu_os3(db_session, line, inv) is None


def test_avant_2026_skip(db_session: Session):
    """2025 = prix Annexe 6 base, hors fenetre OS N°3 fixe → None."""
    line, inv = _line(db_session, base_price=89.06, year=2025)
    db_session.commit()
    assert _control_p1_gaz_pu_os3(db_session, line, inv) is None


def test_tarif_introuvable_bloque(db_session: Session):
    line, inv = _line(db_session, base_price=70.78, code="CCAS 99")  # pas dans l'import
    db_session.commit()
    ctrl = _control_p1_gaz_pu_os3(db_session, line, inv)
    assert ctrl.status == "blocked"
