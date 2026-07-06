"""Guard T1 — moteur métier « Référentiel des marchés ».

Verrouille le CONTRAT DE LECTURE dont dépendra l'onglet « Référentiel » de
`/refonte-v1/marches` (consultation), pour les deux référentiels de fourniture :

- BPU élec (tiers ENGIE / EDF) : route `list_documents` (GET /api/bpu/documents),
  filtre par fournisseur + ordre d'affichage.
- BPU gaz lot 7 (tier TotalEnergies) : service `list_bpu` (GET /api/gas/invoices/bpu),
  périmètre ville (réfs propres + partagées city_id NULL) + tri.

Le référentiel DPGF DALKIA (active-summary / imports / diff) est déjà couvert par
test_cpe_dalkia_history.py et test_cpe_dalkia_diff.py.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([
            City(id=1, nom_commune="Sete", code_commune="34301"),
            City(id=2, nom_commune="Autre", code_commune="00000"),
        ])
        session.commit()
        yield session


# --------------------------------------------------------------------------- #
# BPU élec (ENGIE / EDF) — GET /api/bpu/documents
# --------------------------------------------------------------------------- #

def test_bpu_documents_filter_by_supplier(db_session):
    from app.api.routes.bpu import list_documents
    from app.models.bpu import BpuDocument

    db_session.add_all([
        BpuDocument(supplier="ENGIE", valid_year=2026, lot_number=1, pdf_filename="engie-2026.pdf"),
        BpuDocument(supplier="EDF", valid_year=2026, lot_number=3, pdf_filename="edf-2026.pdf"),
    ])
    db_session.commit()
    user = SimpleNamespace(city_id=1)
    # NB : appel direct de la route -> passer explicitement les filtres à None
    # (sinon les défauts FastAPI Query(None) ne sont pas résolus).
    kw = dict(valid_year=None, lot_number=None, market_subsequent=None, extraction_status=None,
              db=db_session, current_user=user)

    engie = list_documents(supplier="ENGIE", **kw)
    assert [d.supplier for d in engie] == ["ENGIE"]

    edf = list_documents(supplier="edf", **kw)  # casse insensible
    assert [d.supplier for d in edf] == ["EDF"]

    allrows = list_documents(supplier=None, **kw)
    assert {d.supplier for d in allrows} == {"ENGIE", "EDF"}


def test_bpu_documents_ordering_recent_first(db_session):
    from app.api.routes.bpu import list_documents
    from app.models.bpu import BpuDocument

    db_session.add_all([
        BpuDocument(supplier="ENGIE", valid_year=2024, lot_number=1, pdf_filename="a.pdf"),
        BpuDocument(supplier="ENGIE", valid_year=2026, lot_number=1, pdf_filename="b.pdf"),
        BpuDocument(supplier="ENGIE", valid_year=2025, lot_number=1, pdf_filename="c.pdf"),
    ])
    db_session.commit()

    rows = list_documents(supplier="ENGIE", valid_year=None, lot_number=None, market_subsequent=None,
                          extraction_status=None, db=db_session, current_user=SimpleNamespace(city_id=1))
    # année de validité décroissante (plus récent en tête) — cf. order_by de la route
    assert [d.valid_year for d in rows] == [2026, 2025, 2024]


# --------------------------------------------------------------------------- #
# BPU gaz lot 7 (TotalEnergies) — GET /api/gas/invoices/bpu
# --------------------------------------------------------------------------- #

def test_gas_bpu_scope_city_and_shared(db_session):
    from app.models.gas_bpu import GasBpuPrice
    from app.services.gas_invoice import list_bpu

    db_session.add_all([
        GasBpuPrice(city_id=1, annee=2026, profil="T1", fourniture_ht_mwh=30.0),   # ville 1
        GasBpuPrice(city_id=None, annee=2026, profil="T2", fourniture_ht_mwh=31.0),  # réf partagée
        GasBpuPrice(city_id=2, annee=2026, profil="T3", fourniture_ht_mwh=99.0),   # autre ville -> exclue
    ])
    db_session.commit()

    rows = list_bpu(db_session, city_id=1)
    profils = {r.profil for r in rows}
    assert profils == {"T1", "T2"}  # propre + partagée, jamais l'autre ville


def test_gas_bpu_sort_year_desc_then_profil(db_session):
    from app.models.gas_bpu import GasBpuPrice
    from app.services.gas_invoice import list_bpu

    db_session.add_all([
        GasBpuPrice(city_id=1, annee=2025, profil="T2"),
        GasBpuPrice(city_id=1, annee=2026, profil="T3"),
        GasBpuPrice(city_id=1, annee=2026, profil="T1"),
    ])
    db_session.commit()

    rows = list_bpu(db_session, city_id=1)
    assert [(r.annee, r.profil) for r in rows] == [(2026, "T1"), (2026, "T3"), (2025, "T2")]
