"""Étape E2 : superposition des niveaux (docs/thermique/refondation-parcours-decisions.md §12)."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.core.security import get_password_hash
from app.models.thermique import ThermiqueDocument, ThermiqueLevel, ThermiqueSheet
from app.models.user import User
from app.services import thermique_superposition
from app.services.thermique import ThermiqueError, create_project
from thermique_moteur import calques, superposition

TRAIT = "trait|0.36|#000000|"
LARGEUR, HAUTEUR = 600, 400


def _plan(dx=0.0, dy=0.0, meubles=()):
    """Un bâtiment (contour, refends, un patio) décalé de (dx, dy), et des meubles propres au niveau."""
    lignes = [
        [100, 100, 400, 100, 400, 300, 100, 300, 100, 100],
        [200, 100, 200, 300],
        [300, 180, 400, 180],
        [230, 200, 270, 200, 270, 240, 230, 240, 230, 200],
        [120, 260, 180, 130],
    ]
    elements = [
        (calques.TRAIT, TRAIT, "polyligne", [v + (dx if k % 2 == 0 else dy) for k, v in enumerate(ligne)]) for ligne in lignes
    ]
    elements += [(calques.TRAIT, TRAIT, "court", list(m)) for m in meubles]
    return calques.assembler(elements, 100)


def _recaler(plan, reference):
    return superposition.recaler(
        superposition.image_traits(plan, LARGEUR, HAUTEUR), superposition.image_traits(reference, LARGEUR, HAUTEUR)
    )


def test_recalage_des_traits():
    reference = _plan(meubles=[(110, 110, 150, 110)])
    assert superposition.image_traits(reference, LARGEUR, HAUTEUR)[100, 100:401].all()
    meme = _recaler(_plan(meubles=[(330, 250, 380, 250)]), reference)
    assert (meme["dx"], meme["dy"], meme["etat"]) == (0, 0, "superpose")
    # le niveau est dessiné 60 pt plus à droite et 25 pt plus bas : il faut le ramener de (−60, +25)
    decale = _recaler(_plan(dx=60, dy=-25), reference)
    assert (decale["dx"], decale["dy"], decale["etat"]) == (-60, 25, "decale")
    assert decale["score"] > 0.9 and decale["score_zero"] < 0.3
    autre = calques.assembler([(calques.TRAIT, TRAIT, "droit", [10, 390, 590, 10])], 100)
    assert _recaler(autre, reference)["etat"] == "incertain"


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _calage(db, sheet_id):
    level = db.scalars(select(ThermiqueLevel).where(ThermiqueLevel.sheet_id == sheet_id)).first()
    return json.loads(level.calage_json) if level and level.calage_json else None


def test_superposition_validee_comme_calage(db_session, monkeypatch):
    user = User(email="be@example.fr", password_hash=get_password_hash("motdepasse-solide"), nom="Nom", prenom="Prenom", role="USER", is_active=True)
    db_session.add(user)
    db_session.commit()
    projet = create_project(db_session, user, "Médiathèque", None)
    document = ThermiqueDocument(
        project_id=projet.id, original_filename="plans.pdf", stored_filename="plans.pdf", file_format="pdf", size_bytes=1, sha256="0" * 64, page_count=3
    )
    db_session.add(document)
    db_session.flush()
    planches = {}
    for index, label in enumerate(["R+1", "RDC", "TOITURE"]):
        planche = ThermiqueSheet(
            project_id=projet.id, document_id=document.id, page_index=index, label=label, nature="plan", nature_suggested=None,
            level_label=None, rotation_deg=0, page_width_pt=LARGEUR - 1, page_height_pt=HAUTEUR - 1, scale_denominator=50, scale_source="declaree",
        )
        db_session.add(planche)
        planches[label] = planche
    db_session.flush()
    db_session.add(ThermiqueLevel(project_id=projet.id, name="R+1", position=1, sheet_id=planches["R+1"].id))
    db_session.add(ThermiqueLevel(project_id=projet.id, name="RDC", position=0, sheet_id=planches["RDC"].id))
    db_session.commit()
    rdc, r1, toit = planches["RDC"].id, planches["R+1"].id, planches["TOITURE"].id
    donnees = {rdc: _plan(), r1: _plan(dx=60, dy=-25), toit: _plan()}
    monkeypatch.setattr(thermique_superposition, "sheet_elements", lambda sheet: donnees[sheet.id])

    vue = thermique_superposition.overview(db_session, projet)
    assert vue["reference_id"] == rdc
    assert [(p["libelle"], p["niveau"], p["valide"]) for p in vue["planches"]] == [("R+1", "R+1", False), ("RDC", "RDC", False), ("TOITURE", None, False)]
    proposition = thermique_superposition.propose(db_session, projet, r1, rdc)
    assert (proposition["dx"], proposition["dy"], proposition["etat"]) == (-60, 25, "decale")
    assert thermique_superposition.propose(db_session, projet, rdc, rdc)["etat"] == "reference"

    vue = thermique_superposition.validate(db_session, projet, rdc, r1, -60, 25)
    assert _calage(db_session, rdc) == {"a": [0.0, 0.0], "b": [100.0, 0.0], "source": "superposition", "reference": True, "decalage": [0.0, 0.0]}
    assert _calage(db_session, r1)["a"] == [60, -25] and _calage(db_session, r1)["decalage"] == [-60, 25]
    # la toiture n'a pas de niveau : elle en reçoit un, au-dessus des autres
    vue = thermique_superposition.validate(db_session, projet, rdc, toit, 0, 0)
    toiture = next(p for p in vue["planches"] if p["id"] == toit)
    assert toiture["niveau"] == "TOITURE" and toiture["valide"]
    assert db_session.scalars(select(ThermiqueLevel).where(ThermiqueLevel.sheet_id == toit)).one().position == 2

    # changement de référence : les superpositions validées sont ramenées au R+1
    vue = thermique_superposition.validate(db_session, projet, r1, r1, 0, 0)
    assert vue["reference_id"] == r1
    assert _calage(db_session, r1)["decalage"] == [0, 0] and _calage(db_session, r1)["reference"]
    assert _calage(db_session, rdc)["decalage"] == [60, -25] and not _calage(db_session, rdc)["reference"]
    assert _calage(db_session, toit)["decalage"] == [60, -25]

    with pytest.raises(ThermiqueError, match="Annulez d'abord"):
        thermique_superposition.reset(db_session, projet, r1)
    thermique_superposition.reset(db_session, projet, rdc)
    thermique_superposition.reset(db_session, projet, toit)
    vue = thermique_superposition.reset(db_session, projet, r1)
    assert not any(p["valide"] for p in vue["planches"])
    with pytest.raises(ThermiqueError, match="pas de superposition"):
        thermique_superposition.reset(db_session, projet, r1)
    with pytest.raises(ThermiqueError, match="trop grand"):
        thermique_superposition.validate(db_session, projet, rdc, r1, 9000, 0)
