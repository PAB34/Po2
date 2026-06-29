import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
import app.models  # noqa: F401  (enregistre toutes les tables, dont supplier_contacts)
from app.services import supplier_contacts as svc


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_upsert_creates_then_updates_same_row(db_session: Session):
    c1 = svc.upsert_contact(db_session, 1, "ENGIE", {"contact_name": "Jean Dupont", "email": "jean@engie.fr"})
    assert c1.id is not None
    assert c1.email == "jean@engie.fr"

    # même (ville, fournisseur) -> on met à jour la même ligne, pas de doublon
    c2 = svc.upsert_contact(db_session, 1, "ENGIE", {"phone": "0102030405"})
    assert c2.id == c1.id
    assert c2.email == "jean@engie.fr"  # champ non fourni conservé
    assert c2.phone == "0102030405"
    assert len(svc.list_contacts(db_session, 1)) == 1


def test_blank_string_is_stored_as_null(db_session: Session):
    c = svc.upsert_contact(db_session, 1, "EDF", {"email": "   "})
    assert c.email is None


def test_contacts_are_city_scoped(db_session: Session):
    svc.upsert_contact(db_session, 1, "EDF", {"email": "a@edf.fr"})
    svc.upsert_contact(db_session, 2, "EDF", {"email": "b@edf.fr"})
    assert len(svc.list_contacts(db_session, 1)) == 1
    assert svc.list_contacts(db_session, 1)[0].email == "a@edf.fr"
