from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.city import City
from app.services.cpe_accounting import import_codification_workbook, import_finance_workbook


DATA_DIR = Path(__file__).resolve().parents[2] / "energie" / "DALKIA" / "COMPTABILITE"
CODIFICATION = DATA_DIR / "analyse_codification_dalkia_enrichie_par_code_contrat (1).xlsx"
FINANCE_EXPORT = DATA_DIR / "export_finances-20260527_1055.xlsx"


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


@pytest.mark.skipif(not CODIFICATION.exists() or not FINANCE_EXPORT.exists(), reason="DALKIA local workbooks absent")
def test_enriched_codification_matches_finance_export_lines(db_session: Session):
    import_codification_workbook(
        db_session,
        CODIFICATION.read_bytes(),
        filename=CODIFICATION.name,
        city_id=1,
    )
    result = import_finance_workbook(
        db_session,
        FINANCE_EXPORT.read_bytes(),
        filename=FINANCE_EXPORT.name,
        city_id=1,
    )

    assert result.line_count == 2047
    assert result.matched_accounting_rules == 2047
    assert result.matched_site_mappings > 1200
    assert not any("sans nature comptable" in warning for warning in result.warnings)
