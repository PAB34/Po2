"""Import des devis petits travaux P3 (type P6) + atterrissage P3 vs provision.

Scope = COMMUNE DE SETE uniquement (les devis CA SETE AGGLOPOLE sont hors périmètre CPE Ville).
"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe import CpeContractReference, CpeP3Devis
from app.models.cpe_dalkia import CpeDalkiaRefImport, CpeDalkiaRefP2P3
from app.services.cpe_p3_devis import build_p3_atterrissage, import_p3_devis_csv, list_p3_devis

# CSV minimal au format DALKIA (cp1252, séparateur ';') : 2 COMMUNE + 1 AGGLO.
CSV = (
    "LOCALISATION;DATE;NUMÉRO;LIBELLÉ;DOMAINE;TYPE;DESTINAIRE;ÉTAT;MONTANT HT;MONTANT TTC\r\n"
    "S001 - SETE CSU VDS-BAM 10;2026-02-10;C26000001-1;Travaux X;Génie Climatique;P6;COMMUNE DE SETE;Travaux terminés;1000,50;1200,60\r\n"
    "S002 - SETE MIAM VDS-CULT 03;2026-03-15;C26000002-1;Travaux Y;Génie Climatique;P6;COMMUNE DE SETE;Attente de réponse;2000,00;2400,00\r\n"
    "S003 - SETE FONQUERNE;2026-04-01;C26000003-1;Travaux Z;Génie Climatique;P6;CA SETE AGGLOPOLE MEDITERRANEE;Travaux en cours;9000,00;10800,00\r\n"
).encode("cp1252")


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.add(
            CpeContractReference(
                city_id=1, contract_code="C00190116O", contract_label="LOT 1",
                reference_kind="cpe_contract_scope", year=2026, market="SCOPE",
                billed_item="CPE_VILLE_LOT_1", active=True,
            )
        )
        session.commit()
        yield session


def test_import_scopes_to_commune(db_session):
    result = import_p3_devis_csv(db_session, CSV, city_id=1)
    assert result["created"] == 3
    assert result["in_scope"] == 2          # 2 COMMUNE
    assert result["out_of_scope"] == 1      # 1 AGGLO
    # in_scope_only=True ne renvoie que les 2 devis Commune
    scoped = list_p3_devis(db_session, 1, in_scope_only=True)
    assert {d.numero for d in scoped} == {"C26000001-1", "C26000002-1"}
    # le devis Agglo est bien marqué hors scope
    agglo = next(d for d in list_p3_devis(db_session, 1, in_scope_only=False) if d.numero == "C26000003-1")
    assert agglo.in_scope is False
    # extraction du code site VDS
    csu = next(d for d in scoped if d.numero == "C26000001-1")
    assert csu.site_code == "VDS-BAM 10"
    assert csu.montant_ht == 1000.5


def test_import_is_idempotent(db_session):
    import_p3_devis_csv(db_session, CSV, city_id=1)
    result = import_p3_devis_csv(db_session, CSV, city_id=1)
    assert result["created"] == 0 and result["updated"] == 3
    assert db_session.query(CpeP3Devis).count() == 3


def test_atterrissage_engage_vs_provision(db_session):
    # Provision P3 2026 = p3_total - p3_4 = 50000 - 10000 = 40000 (P3) + 10000 (P3.4) = 50000
    imp = CpeDalkiaRefImport(city_id=1, lot=1, filename="L1.xlsx", is_active=True)
    db_session.add(imp)
    db_session.flush()
    db_session.add(
        CpeDalkiaRefP2P3(
            import_id=imp.id, city_id=1, code_site="VDS-BAM 10", period_idx=1,
            period_label="2026", period_year=2026, p2_total_ht=0.0, p2_4_ht=0.0,
            p3_total_ht=50000.0, p3_4_ht=10000.0,
        )
    )
    db_session.commit()
    import_p3_devis_csv(db_session, CSV, city_id=1)

    report = build_p3_atterrissage(db_session, 1, year=2026)
    assert report["provision_p3"] == 40000.0
    assert report["provision_p3_4"] == 10000.0
    assert report["provision_total"] == 50000.0
    # engagé = 2 devis Commune 2026 (1000.5 + 2000) ; Agglo exclu
    assert report["engage_total"] == 3000.5
    assert report["devis_count"] == 2
    assert report["reste_provision"] == 46999.5
    etats = {b["etat"]: b["montant_ht"] for b in report["by_etat"]}
    assert etats["Travaux terminés"] == 1000.5
    assert etats["Attente de réponse"] == 2000.0
