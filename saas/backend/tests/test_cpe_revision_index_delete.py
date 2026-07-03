"""Tests suppression / purge des indices de révision CPE."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.models.cpe import CpeRevisionIndex
from app.services import cpe_accounting as svc


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


def _seed(db: Session, code: str, source: str) -> CpeRevisionIndex:
    idx = CpeRevisionIndex(city_id=1, index_code=code, year=2025, quarter=1, value=1.0, source=source)
    db.add(idx)
    db.commit()
    db.refresh(idx)
    return idx


def test_delete_revision_index_by_id(db_session):
    idx = _seed(db_session, "ICHT_IME", "csv_dalkia")
    assert svc.delete_revision_index(db_session, 1, idx.id) is True
    assert svc.delete_revision_index(db_session, 1, idx.id) is False  # déjà supprimé


def test_purge_only_manual_source(db_session):
    _seed(db_session, "ICHT_IME", "Saisie Po2")
    _seed(db_session, "FSD2", "Saisie Po2")
    _seed(db_session, "BT40", "csv_dalkia")  # ne doit pas être supprimé

    deleted = svc.delete_revision_indices_by_source(db_session, 1, "Saisie Po2")
    assert deleted == 2
    remaining = svc.list_revision_indices(db_session, 1)
    assert all(item.source != "Saisie Po2" for item in remaining)
