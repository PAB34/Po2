"""Étape E1 révisée : désignation des calques par l'exemple (clic sur un élément, nature, semblables sur tous les
plans). Voir docs/thermique/refondation-parcours-decisions.md §10."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.core.security import get_password_hash
from app.models.thermique import ThermiqueDocument, ThermiqueSheet
from app.models.user import User
from app.services import thermique_calques
from app.services.thermique import ThermiqueError, create_project
from thermique_moteur import calques

M = 1000 / 100 / (25.4 / 72)  # points PDF pour 1 m à 1/100
MUR = "trait|1.56|#000000|"
FIN = "trait|0.36|#000000|"
GRIS = "aplat|#989898"


def test_formes_des_traits():
    assert calques.forme_trait([(0, 0), (3 * M, 0)], False, False, 100) == "droit"
    assert calques.forme_trait([(0, 0), (0.2 * M, 0)], False, False, 100) == "court"
    assert calques.forme_trait([(0, 0), (2 * M, 0), (2 * M, 2 * M)], False, False, 100) == "polyligne"
    assert calques.forme_trait([(0, 0), (M, 0), (M, M), (0, M)], True, False, 100) == "petit_ferme"
    assert calques.forme_trait([(0, 0), (3 * M, 0), (3 * M, 3 * M), (0, 3 * M)], True, False, 100) == "grand_ferme"
    assert calques.forme_trait([(0, 0), (M, M)], False, True, 100) == "courbe"
    assert calques.libelle_signature(MUR) == "1,56 pt · noir"
    assert calques.libelle_signature(GRIS) == "Remplissage gris 40 %"
    assert calques.libelle_forme("*") == "toutes formes"


def test_lasso_en_biais():
    # deux traits parallèles en biais, proches : un rectangle droit ne sait pas isoler le premier, le lasso si
    plan = calques.assembler(
        [
            (calques.TRAIT, FIN, "droit", [0, 0, 10 * M, 5 * M]),
            (calques.TRAIT, FIN, "droit", [0, 1 * M, 10 * M, 6 * M]),
        ],
        100,
    )
    droit = [-1, -1, 10 * M + 1, -1, 10 * M + 1, 6 * M + 1, -1, 6 * M + 1]
    assert calques.dans_zone(plan, droit) == [0, 1]
    biais = [-0.5 * M, -0.5 * M, 10.5 * M, 4.5 * M, 10.5 * M, 5.5 * M, -0.5 * M, 0.5 * M]
    assert calques.dans_zone(plan, biais) == [0]
    assert calques.dans_zone(plan, [20 * M, 20 * M, 21 * M, 20 * M, 21 * M, 21 * M]) == []


def _plan(decalage=0.0):
    # un mur (contour fermé), une cloison fine (trait droit), trois marches (traits courts), un remplissage
    return calques.assembler(
        [
            (calques.TRAIT, MUR, "grand_ferme", [0, 0, 10 * M, 0, 10 * M, 0.3 * M, 0, 0.3 * M, 0, 0]),
            (calques.TRAIT, FIN, "droit", [0, 5 * M, 4 * M + decalage, 5 * M]),
            *[(calques.TRAIT, FIN, "court", [k * M, 8 * M, k * M + 0.2 * M, 8 * M]) for k in range(3)],
            (calques.REMPLISSAGE, GRIS, "remplissage", [0, 0, 10 * M, 0, 10 * M, 0.3 * M, 0, 0.3 * M]),
        ],
        100,
    )


def test_element_sous_le_clic_et_familles():
    plan = _plan()
    # sur la cloison, à 2 pt près
    assert calques.element_sous_point(plan, 2 * M, 5 * M + 1.5, 2.0) == 1
    # dans l'épaisseur du mur, loin de ses faces : c'est le remplissage
    assert calques.element_sous_point(plan, 5 * M, 0.15 * M, 2.0) == 5
    # sur la face du mur : le trait l'emporte
    assert calques.element_sous_point(plan, 5 * M, 0.5, 2.0) == 0
    assert calques.element_sous_point(plan, 5 * M, 20 * M, 2.0) is None
    # un trait fin dessiné par-dessus la face du mur : le mur, plus épais, l'emporte
    double = calques.assembler(
        [
            (calques.TRAIT, MUR, "droit", [0, 0, 10 * M, 0]),
            (calques.TRAIT, FIN, "droit", [0, 0.1, 10 * M, 0.1]),
        ],
        100,
    )
    assert calques.element_sous_point(double, 5 * M, 0.3, 2.0) == 0
    assert calques.nombre_famille(plan, FIN, "court") == 3
    assert calques.nombre_famille(plan, FIN, "*") == 4
    assert calques.famille(plan, FIN, "court") == [2, 3, 4]
    assert calques.famille(plan, "trait|9.99|#000000|", "*") == []


def test_regle_precise_prioritaire_et_exclusions():
    plan = _plan()
    regles = [
        {"id": 1, "signature": FIN, "forme": "*", "nature": "cloison", "exclusions": []},
        {"id": 2, "signature": FIN, "forme": "court", "nature": "garde_corps", "exclusions": [{"planche": 7, "element": 3}]},
    ]
    attribution = calques.attribuer(plan, regles, 7)
    assert {i: r["nature"] for i, r in attribution.items()} == {1: "cloison", 2: "garde_corps", 3: "cloison", 4: "garde_corps"}
    assert calques.regle_applicable(regles, FIN, "court")["id"] == 2
    assert calques.regle_applicable(regles, FIN, "polyligne")["id"] == 1
    geometrie = calques.coordonnees(plan, [0, 5], 1)
    assert geometrie["tronque"] and len(geometrie["traits"]) + len(geometrie["remplissages"]) == 1


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_designation_sur_tous_les_plans(db_session, monkeypatch):
    user = User(email="be@example.fr", password_hash=get_password_hash("motdepasse-solide"), nom="Nom", prenom="Prenom", role="USER", is_active=True)
    db_session.add(user)
    db_session.commit()
    projet = create_project(db_session, user, "Médiathèque", None)
    assert thermique_calques.list_designations(db_session, projet) == {"regles": [], "natures": calques.NATURES, "planches": []}

    document = ThermiqueDocument(
        project_id=projet.id, original_filename="plans.pdf", stored_filename="plans.pdf", file_format="pdf", size_bytes=1, sha256="0" * 64, page_count=3
    )
    db_session.add(document)
    db_session.flush()
    planches = []
    for index, (label, nature) in enumerate([("RDC", "plan"), ("R+1", "plan"), ("Coupe AA", "coupe")]):
        planche = ThermiqueSheet(
            project_id=projet.id, document_id=document.id, page_index=index, label=label, nature=None, nature_suggested=nature,
            level_label=None, rotation_deg=0, page_width_pt=1684, page_height_pt=2384, scale_denominator=100, scale_source="declaree",
        )
        db_session.add(planche)
        planches.append(planche)
    db_session.commit()
    rdc, etage, coupe = planches
    donnees = {rdc.id: _plan(), etage.id: _plan(decalage=1.0), coupe.id: _plan()}
    monkeypatch.setattr(thermique_calques, "sheet_elements", lambda sheet: donnees[sheet.id])

    choix = thermique_calques.pick_element(db_session, projet, rdc, 1.0 * M, 8 * M, 2.0)
    assert choix["element"]["signature"] == FIN and choix["element"]["forme"] == "court"
    assert [(f["forme"], f["total"], len(f["par_planche"])) for f in choix["familles"]] == [("court", 6, 2), ("*", 8, 2)]
    assert choix["regle"] is None
    with pytest.raises(ThermiqueError, match="Aucun élément"):
        thermique_calques.pick_element(db_session, projet, rdc, 5 * M, 30 * M, 2.0)

    thermique_calques.save_designation(db_session, projet, FIN, "court", "garde_corps")
    thermique_calques.save_designation(db_session, projet, GRIS, "*", "mur")
    thermique_calques.save_designation(db_session, projet, FIN, "court", "cloison")  # même famille : nature changée
    liste = thermique_calques.list_designations(db_session, projet)
    assert [(r["id"], r["nature"], r["total"], r["forme_libelle"]) for r in liste["regles"]] == [
        (1, "cloison", 6, "trait court (< 40 cm)"),
        (2, "mur", 2, "toutes formes"),
    ]
    assert [p["libelle"] for p in liste["planches"]] == ["RDC", "R+1"]

    thermique_calques.toggle_exclusion(db_session, projet, 1, rdc.id, 3)
    assert thermique_calques.list_designations(db_session, projet)["regles"][0]["total"] == 5
    assert thermique_calques.pick_element(db_session, projet, rdc, 1.0 * M, 8 * M, 2.0)["regle"]["exclu"] is True
    designes = thermique_calques.sheet_designations(projet, rdc)
    assert {k: (len(v["traits"]), len(v["remplissages"])) for k, v in designes["natures"].items()} == {"cloison": (2, 0), "mur": (0, 1)}
    thermique_calques.toggle_exclusion(db_session, projet, 1, rdc.id, 3)
    assert thermique_calques.list_designations(db_session, projet)["regles"][0]["total"] == 6
    assert len(thermique_calques.family_elements(projet, rdc, FIN, "*")["traits"]) == 4

    with pytest.raises(ThermiqueError, match="Nature inconnue"):
        thermique_calques.save_designation(db_session, projet, FIN, "droit", "fenetre")
    with pytest.raises(ThermiqueError, match="toutes ses formes"):
        thermique_calques.save_designation(db_session, projet, GRIS, "remplissage", "mur")
    with pytest.raises(ThermiqueError, match="Élément inconnu"):
        thermique_calques.save_designation(db_session, projet, "calque|x", "*", "mur")
    with pytest.raises(ThermiqueError, match="introuvable"):
        thermique_calques.toggle_exclusion(db_session, projet, 1, rdc.id, 99)

    # zone autour des trois marches du RDC : on les retire d'un coup, puis on les remet
    thermique_calques.save_designation(db_session, projet, FIN, "*", "isolant")
    zone = [-0.1 * M, 7.5 * M, 3 * M, 7.5 * M, 3 * M, 8.5 * M, -0.1 * M, 8.5 * M]
    resume = thermique_calques.zone_summary(projet, rdc, zone)
    assert [(c["id"], c["actifs"], c["retires"]) for c in resume["calques"]] == [(1, 3, 0)]
    assert len(resume["traits"]) == 3
    thermique_calques.apply_zone(db_session, projet, rdc, zone, [1, 3], retirer=True)
    resume = thermique_calques.zone_summary(projet, rdc, zone)
    assert [(c["id"], c["actifs"], c["retires"]) for c in resume["calques"]] == [(1, 0, 3), (3, 0, 3)]
    assert thermique_calques.list_designations(db_session, projet)["regles"][0]["total"] == 3
    # « Voir » le calque et recliquer une marche : les éléments retirés ne reviennent pas
    assert len(thermique_calques.family_elements(projet, rdc, FIN, "court")["traits"]) == 0
    assert thermique_calques.pick_element(db_session, projet, rdc, 1.0 * M, 8 * M, 2.0)["familles"][0]["total"] == 3
    assert "cloison" not in thermique_calques.sheet_designations(projet, rdc)["natures"]
    thermique_calques.apply_zone(db_session, projet, rdc, zone, [1, 3], retirer=False)
    assert [(c["id"], c["actifs"]) for c in thermique_calques.zone_summary(projet, rdc, zone)["calques"]] == [(1, 3)]
    with pytest.raises(ThermiqueError, match="au moins un calque"):
        thermique_calques.apply_zone(db_session, projet, rdc, zone, [], retirer=True)
    thermique_calques.delete_designation(db_session, projet, 3)

    thermique_calques.delete_designation(db_session, projet, 1)
    assert [r["id"] for r in json.loads(projet.signatures_json)["regles"]] == [2]
    with pytest.raises(ThermiqueError, match="introuvable"):
        thermique_calques.delete_designation(db_session, projet, 1)
