"""Enveloppe thermique proposée depuis les calques et portée des calques (docs/thermique/refondation-parcours-decisions.md §15)."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.core.security import get_password_hash
from app.models.thermique import ThermiqueDocument, ThermiqueLevel, ThermiqueSheet, ThermiqueZone
from app.models.user import User
from app.services import thermique_calques, thermique_enveloppe, thermique_metre, thermique_pieces
from app.services.thermique import ThermiqueError, create_project
from thermique_moteur import bande, calques

M = 1000 / 100 / (25.4 / 72)  # points PDF pour 1 m à 1/100
FACE = "trait|1.56|#000000|"
VITRE = "trait|0.24|#000000|"


def _rect(x0, y0, x1, y1):
    return [x0 * M, y0 * M, x1 * M, y0 * M, x1 * M, y1 * M, x0 * M, y1 * M, x0 * M, y0 * M]


def _plan():
    """Bâtiment de 10 × 6 m, murs de 30 cm (deux faces), refend de 10 cm à x = 4 m ; une vitre dans le mur de façade
    (x = 0,15 m) et une vitre intérieure (y = 3 m), de même signature."""
    return calques.assembler(
        [
            (calques.TRAIT, FACE, "grand_ferme", _rect(0, 0, 10, 6)),
            (calques.TRAIT, FACE, "grand_ferme", _rect(0.3, 0.3, 9.7, 5.7)),
            (calques.TRAIT, FACE, "droit", [3.95 * M, 0.3 * M, 3.95 * M, 5.7 * M]),
            (calques.TRAIT, FACE, "droit", [4.05 * M, 0.3 * M, 4.05 * M, 5.7 * M]),
            (calques.TRAIT, VITRE, "droit", [0.15 * M, 1 * M, 0.15 * M, 2 * M]),
            (calques.TRAIT, VITRE, "droit", [5 * M, 3 * M, 6 * M, 3 * M]),
        ],
        100,
    )


def test_deux_lignes_et_bande():
    plan = _plan()
    (batiment,) = bande.proposer(plan, [0, 1, 2, 3], fermeture_m=0.4)
    assert batiment["aire_exterieur_m2"] == pytest.approx(60, abs=1.2)
    assert batiment["aire_interieur_m2"] == pytest.approx(9.4 * 5.4, abs=1.2)
    filtre = bande.Bande([batiment["nu_exterieur"]], [batiment["nu_interieur"]], 100)
    assert filtre.filtrer(plan, [4, 5], bande.ENVELOPPE) == [4]
    assert filtre.filtrer(plan, [4, 5], bande.INTERIEUR) == [5]
    assert filtre.filtrer(plan, [4, 5], bande.PARTOUT) == [4, 5]
    assert filtre.positions(plan, 4) == ["partout", "enveloppe"]
    assert bande.Bande([], [], 100).filtrer(plan, [4, 5], bande.ENVELOPPE) == []
    with pytest.raises(Exception, match="Aucun bâtiment"):
        bande.proposer(plan, [2, 3], fermeture_m=0.4)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_enveloppe_proposee_et_portee_des_calques(db_session, monkeypatch):
    user = User(email="be@example.fr", password_hash=get_password_hash("motdepasse-solide"), nom="Nom", prenom="Prenom", role="USER", is_active=True)
    db_session.add(user)
    db_session.commit()
    projet = create_project(db_session, user, "Médiathèque", None)
    document = ThermiqueDocument(
        project_id=projet.id, original_filename="plans.pdf", stored_filename="plans.pdf", file_format="pdf", size_bytes=1, sha256="0" * 64, page_count=1
    )
    db_session.add(document)
    db_session.flush()
    sheet = ThermiqueSheet(
        project_id=projet.id, document_id=document.id, page_index=0, label="RDC", nature="plan", nature_suggested=None,
        level_label=None, rotation_deg=0, page_width_pt=1684, page_height_pt=2384, scale_denominator=100, scale_source="declaree",
    )
    db_session.add(sheet)
    db_session.flush()
    niveau = ThermiqueLevel(project_id=projet.id, name="RDC", position=0, sheet_id=sheet.id)
    db_session.add(niveau)
    db_session.commit()
    plan = _plan()
    monkeypatch.setattr(thermique_calques, "sheet_elements", lambda s: plan)
    monkeypatch.setattr(thermique_pieces, "sheet_elements", lambda s: plan)

    with pytest.raises(ThermiqueError, match="Aucun calque"):
        thermique_enveloppe.propose_envelope(db_session, niveau, 0.4)
    thermique_calques.save_designation(db_session, projet, FACE, "*", "mur")
    # sans lignes, une règle « dans l'enveloppe » ne s'applique nulle part
    thermique_calques.save_designation(db_session, projet, VITRE, "droit", "menuiserie", "enveloppe")
    liste = thermique_calques.list_designations(db_session, projet)
    assert [(r["nature"], r["perimetre"], r["total"]) for r in liste["regles"]] == [("mur", "partout", 4), ("menuiserie", "enveloppe", 0)]
    assert liste["planches"] == [{"id": sheet.id, "libelle": "RDC", "enveloppe": False}]

    resume = thermique_enveloppe.propose_envelope(db_session, niveau, 0.4)
    assert resume["batiments"] == 1 and resume["nu_exterieur_m2"] == pytest.approx(60, abs=1.2)
    zones = {z.kind: z for z in db_session.scalars(select(ThermiqueZone).where(ThermiqueZone.level_id == niveau.id))}
    assert set(zones) == {"contour", "nu_exterieur"} and zones["contour"].source == "automatique"

    # la même vitre : menuiserie dans l'enveloppe, menuiserie intérieure à l'intérieur
    thermique_calques.save_designation(db_session, projet, VITRE, "droit", "menuiserie_interieure", "interieur")
    liste = thermique_calques.list_designations(db_session, projet)
    assert [(r["nature"], r["total"]) for r in liste["regles"]] == [("mur", 4), ("menuiserie", 1), ("menuiserie_interieure", 1)]
    natures = {i: r["nature"] for i, r in thermique_calques.attribution(projet, sheet, plan).items()}
    assert natures[4] == "menuiserie" and natures[5] == "menuiserie_interieure"
    choix = thermique_calques.pick_element(db_session, projet, sheet, 0.15 * M, 1.5 * M, 2.0)
    assert choix["enveloppe_tracee"] and choix["element"]["positions"] == ["partout", "enveloppe"]
    assert choix["regle"]["nature"] == "menuiserie" and choix["regle"]["perimetre"] == "enveloppe"
    assert len(thermique_calques.family_elements(projet, sheet, VITRE, "droit", "interieur")["traits"]) == 1
    with pytest.raises(ThermiqueError, match="Portée inconnue"):
        thermique_calques.save_designation(db_session, projet, VITRE, "droit", "menuiserie", "dehors")

    # les pièces se ferment aussi sur les deux vitres
    assert "menuiserie" in thermique_pieces.list_rooms(db_session, projet, sheet)["limites"]["natures"]

    # nu extérieur tracé à la main : on ne propose que le nu intérieur, sans y toucher
    zones["nu_exterieur"].source = "manuel"
    db_session.commit()
    thermique_enveloppe.propose_envelope(db_session, niveau, 0.4, genres=("contour",))
    genres = sorted((z.kind, z.source) for z in db_session.scalars(select(ThermiqueZone).where(ThermiqueZone.level_id == niveau.id)))
    assert genres == [("contour", "automatique"), ("nu_exterieur", "manuel")]
    with pytest.raises(ThermiqueError, match="Ligne inconnue"):
        thermique_enveloppe.propose_envelope(db_session, niveau, 0.4, genres=("patio",))
    zones = {z.kind: z for z in db_session.scalars(select(ThermiqueZone).where(ThermiqueZone.level_id == niveau.id))}

    # une ligne corrigée à la main n'est pas remplacée sans confirmation
    points = json.loads(zones["contour"].points_json)
    thermique_metre.update_zone(db_session, zones["contour"], {"points": points[:-1] + [[points[-1][0] + 1, points[-1][1]]]})
    with pytest.raises(ThermiqueError, match="confirmez"):
        thermique_enveloppe.propose_envelope(db_session, niveau, 0.4)
    thermique_enveloppe.propose_envelope(db_session, niveau, 0.4, replace=True)
    sources = [z.source for z in db_session.scalars(select(ThermiqueZone).where(ThermiqueZone.level_id == niveau.id))]
    assert sources == ["automatique", "automatique"]
