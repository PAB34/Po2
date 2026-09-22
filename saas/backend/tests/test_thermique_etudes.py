"""Lot E2 : fichier d'étude unique, import strict, versions et migration 0083."""
from __future__ import annotations

import importlib.util
import json
from io import BytesIO
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from pypdf import PdfWriter
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.thermique import (
    ThermiqueDocument,
    ThermiqueEtudeVersion,
    ThermiqueProject,
    ThermiqueSheet,
)
from app.models.user import User
from app.services.thermique import ThermiqueError, update_project
from app.services.thermique_etudes import (
    EtudeConflict,
    assembler_etude_niveau,
    importer_etude,
    serialize_etude,
    valider_et_convertir,
)


def _pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=1000, height=500)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


@pytest.fixture()
def contexte():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(email="thermicien@example.test", password_hash="test", nom="Thermicien", prenom="Test", role="USER", is_active=True)
        db.add(user)
        db.flush()
        project = ThermiqueProject(owner_user_id=user.id, name="Médiathèque")
        db.add(project)
        db.flush()
        data = _pdf()
        import hashlib

        document = ThermiqueDocument(
            project_id=project.id,
            original_filename="plan.pdf",
            stored_filename="plan.pdf",
            file_format="pdf",
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            page_count=1,
            uploaded_by_user_id=user.id,
        )
        db.add(document)
        db.flush()
        sheet = ThermiqueSheet(
            project_id=project.id,
            document_id=document.id,
            page_index=0,
            label="R+1",
            nature="plan",
            level_label="R+1",
            scale_denominator=100,
            scale_source="declaree",
            rotation_deg=0,
            page_width_pt=1000,
            page_height_pt=500,
        )
        db.add(sheet)
        db.commit()
        yield db, user, project, sheet


def _payload(sha256: str) -> dict:
    fiche = {
        "piece": "Bureau",
        "local": "chauffe",
        "surface_m2": 12.5,
        "perimetre_m": 15.0,
        "cotes": [],
        "alertes": [],
    }
    return {
        "format": "thermique.etude_niveau",
        "format_version": 1,
        "uses_pdf_vectors": False,
        "niveau": "R1",
        "source": {
            "filename": "plan.pdf",
            "sha256": sha256,
            "page_index": 0,
            "scale_denominator": 100,
            "viewer_rotation_deg": 0,
            "page_width_px": 2000,
            "page_height_px": 1000,
        },
        "analyse": {},
        "locaux": [
            {
                "id": "piece-001",
                "nom": "Bureau",
                "nature": "chauffe",
                "contour": [[100, 200], [300, 200], [300, 500], [100, 500]],
                "surface_m2": 12.5,
                "fiche": fiche,
                "synthese": {},
                "demandes": [],
            }
        ],
        "locaux_ecartes": [],
        "enveloppe": {"manifeste": {}, "releve": {"elements": [], "raccords": [], "observations": []}, "catalogue": [], "synthese_pieces": [], "fiches_locaux": [fiche], "controle": {}, "demandes": []},
    }


def _raster() -> dict:
    # PDF → raster : px=2*x ; py=-2*y+1000. Le retour attendu est donc vérifiable exactement.
    return {"rotation": 0, "width_px": 2000, "height_px": 1000, "transform": [2, 0, 0, -2, 0, 1000]}


def test_validation_convertit_le_repere_feuille_en_points_pdf(contexte):
    _db, _user, _project, sheet = contexte
    contenu = valider_et_convertir(_payload(sheet.document.sha256), sheet, _raster())
    assert contenu["locaux"][0]["contour_pdf"] == [[100.0, 400.0], [300.0, 400.0], [300.0, 250.0], [100.0, 250.0]]


def test_validation_refuse_mauvais_pdf_page_et_geometrie(contexte):
    _db, _user, _project, sheet = contexte
    payload = _payload("0" * 64)
    with pytest.raises(ThermiqueError, match="ne correspond pas au PDF"):
        valider_et_convertir(payload, sheet, _raster())
    payload = _payload(sheet.document.sha256)
    payload["source"]["page_index"] = 1
    with pytest.raises(ThermiqueError, match="page"):
        valider_et_convertir(payload, sheet, _raster())
    payload = _payload(sheet.document.sha256)
    payload["locaux"][0]["contour"][0] = [-1, 10]
    with pytest.raises(ThermiqueError, match="sort de la feuille"):
        valider_et_convertir(payload, sheet, _raster())


def test_import_initial_et_remplacement_sont_versionnes(contexte):
    db, user, _project, sheet = contexte
    payload = _payload(sheet.document.sha256)
    etude = importer_etude(db, sheet, user, payload, _raster())
    assert serialize_etude(db, etude)["version_number"] == 1
    assert json.loads(etude.local_states_json) == {"piece-001": {"status": "a_verifier", "motif": None}}
    with pytest.raises(EtudeConflict):
        importer_etude(db, sheet, user, payload, _raster())
    payload["locaux"][0]["surface_m2"] = 13.0
    etude = importer_etude(db, sheet, user, payload, _raster(), remplacer=True)
    assert serialize_etude(db, etude)["version_number"] == 2
    versions = list(db.scalars(select(ThermiqueEtudeVersion).order_by(ThermiqueEtudeVersion.version_number)))
    assert [version.reason for version in versions] == ["import_initial", "import_remplacement"]
    assert json.loads(versions[0].content_json)["locaux"][0]["surface_m2"] == 12.5


def test_plan_de_reference_doit_appartenir_au_projet(contexte):
    db, user, project, sheet = contexte
    assert update_project(db, project, {"reference_sheet_id": sheet.id}).reference_sheet_id == sheet.id
    other_project = ThermiqueProject(owner_user_id=user.id, name="Autre")
    db.add(other_project)
    db.flush()
    other_sheet = ThermiqueSheet(
        project_id=other_project.id,
        document_id=sheet.document_id,
        page_index=0,
        label="Autre",
        nature="plan",
        scale_denominator=100,
        rotation_deg=0,
        page_width_pt=100,
        page_height_pt=100,
    )
    db.add(other_sheet)
    db.commit()
    with pytest.raises(ThermiqueError, match="appartenir au projet"):
        update_project(db, project, {"reference_sheet_id": other_sheet.id})


def test_assemblage_numerote_les_homonymes_et_retire_les_chemins():
    source = Path(__file__)
    objects = [
        {"id": f"piece-{index:03d}", "category": "piece", "subtype": "Bureau", "local": "chauffe", "points": [[10 + index, 10], [20 + index, 10], [20 + index, 20]]}
        for index in (1, 2)
    ]
    analyse = {
        "uses_pdf_vectors": False,
        "viewer_rotation_deg": 0,
        "objects": objects,
        "locaux_ecartes": [],
        "manifest": {"page_width_px": 2000, "page_height_px": 1000, "overview": "C:/secret/overview.jpg", "tiles": [{"path": "C:/secret/tile.jpg", "box_norm": [0, 0, 1, 1]}]},
    }
    fiches = [
        {"piece": f"Bureau ({index})", "local": "chauffe", "surface_m2": 10 + index, "perimetre_m": 12, "cotes": [], "alertes": []}
        for index in (1, 2)
    ]
    resultat = assembler_etude_niveau(
        source=source,
        niveau="R1",
        page_number=1,
        echelle=100,
        analyse=analyse,
        manifeste={"page_px": [2000, 1000], "px_par_m": 10, "troncons": [], "guide": "C:/secret/guide.jpg", "planches": []},
        releve_brut={"catalogue": [], "elements": [], "observations": []},
        restitution={"enveloppe": {"bibliotheque": {"fiches_locaux": fiches, "pieces": [], "demandes": []}}},
        controle={"isolant": {}, "cellules": [1, 2, 3]},
    )
    assert [(local["id"], local["nom"]) for local in resultat["locaux"]] == [
        ("piece-001", "Bureau (1)"),
        ("piece-002", "Bureau (2)"),
    ]
    serialized = json.dumps(resultat)
    assert "C:/secret" not in serialized
    assert "cellules" not in resultat["enveloppe"]["controle"]


def test_migration_0083_monte_et_redescend_isolee():
    engine = create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table("users", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    sa.Table("thermique_projects", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    sa.Table(
        "thermique_sheets",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("thermique_projects.id", ondelete="CASCADE"), nullable=False),
    )
    metadata.create_all(engine)
    path = Path(__file__).parents[1] / "alembic" / "versions" / "0083_add_thermique_etudes.py"
    spec = importlib.util.spec_from_file_location("migration_0083", path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        inspector = inspect(connection)
        assert {"thermique_etudes", "thermique_etude_versions"}.issubset(inspector.get_table_names())
        assert "reference_sheet_id" in {column["name"] for column in inspector.get_columns("thermique_projects")}
        migration.downgrade()
        inspector = inspect(connection)
        assert "thermique_etudes" not in inspector.get_table_names()
        assert "reference_sheet_id" not in {column["name"] for column in inspector.get_columns("thermique_projects")}
