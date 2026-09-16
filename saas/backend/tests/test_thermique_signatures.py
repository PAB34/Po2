"""Étape E1 : catalogue des signatures graphiques (calques de l'architecte aplatis dans le PDF).
Voir docs/thermique/refondation-parcours-decisions.md."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.core.security import get_password_hash
from app.models.thermique import ThermiqueDocument, ThermiqueSheet
from app.models.user import User
from app.services import thermique_metre
from app.services.thermique import ThermiqueError, create_project
from thermique_moteur import signatures

M = 1000 / 100 / (25.4 / 72)  # points PDF pour 1 m à 1/100


def _trait(x1, y1, x2, y2, largeur, couleur="#000000", tirets=""):
    rouge, vert, bleu = (int(couleur[k : k + 2], 16) for k in (1, 3, 5))
    return (x1, y1, x2, y2, largeur, round(0.3 * rouge + 0.59 * vert + 0.11 * bleu), couleur, tirets)


def _rectangle(x0, y0, x1, y1, couleur):
    rouge, vert, bleu = (int(couleur[k : k + 2], 16) for k in (1, 3, 5))
    luminance = round(0.3 * rouge + 0.59 * vert + 0.11 * bleu)
    return [([(x0, y0), (x1, y0), (x1, y1)], luminance, couleur), ([(x0, y0), (x1, y1), (x0, y1)], luminance, couleur)]


def test_noms_de_couleur():
    assert signatures.nom_couleur("#000000") == "noir"
    assert signatures.nom_couleur("#767676") == "gris 54 %"
    assert signatures.nom_couleur("#ff0000") == "rouge"
    assert signatures.nom_couleur("#f6fce6") == "vert pâle"
    assert signatures.nom_couleur("#ffffff") == "blanc"


def test_roles_proposes_sur_un_plan_type():
    # Deux murs de 30 cm (6 m chacun) séparés par une baie de 1,2 m fermée par un vitrage fin ; isolant en petits
    # traits gris dans le premier mur ; cote rouge ; projection en tirets ; remplissage gris des murs ; masque blanc.
    L, e, baie = 6 * M, 0.3 * M, 1.2 * M
    traits = [
        _trait(0, 0, L, 0, 1.56),
        _trait(0, e, L, e, 1.56),
        _trait(L + baie, 0, 2 * L + baie, 0, 1.56),
        _trait(L + baie, e, 2 * L + baie, e, 1.56),
        _trait(L, e / 2, L + baie, e / 2, 0.24),
        _trait(0, 3 * M, 5 * M, 3 * M, 0.24, "#ff0000"),
        _trait(0, 5 * M, 8 * M, 5 * M, 0.36, "#000000", "3.0-1.5"),
    ]
    traits += [_trait(10 + k * 0.14 * M, 0.1 * M, 10 + k * 0.14 * M + 0.05 * M, 0.2 * M, 0.48, "#767676") for k in range(38)]
    aplats = _rectangle(0, 0, L, e, "#989898") + _rectangle(L + baie, 0, 2 * L + baie, e, "#989898") + _rectangle(0, 10 * M, M, 11 * M, "#ffffff")

    catalogue = signatures.catalogue_planche(traits, aplats, 100)
    assert catalogue["murs"] == 2
    liste = signatures.fusionner_catalogues([(7, catalogue)])
    roles = {s["cle"]: s["role_propose"] for s in liste}
    assert roles[signatures.cle_trait(1.56, "#000000", "")] == "face_mur"
    assert roles[signatures.cle_trait(0.48, "#767676", "")] == "isolant"
    assert roles[signatures.cle_trait(0.24, "#000000", "")] == "vitrage"
    assert roles[signatures.cle_trait(0.24, "#ff0000", "")] == "annotation"
    assert roles[signatures.cle_trait(0.36, "#000000", "3.0-1.5")] == "projection"
    assert roles[signatures.cle_aplat("#989898")] == "maconnerie"
    assert roles[signatures.cle_aplat("#ffffff")] == "ignorer"
    faces = next(s for s in liste if s["cle"] == signatures.cle_trait(1.56, "#000000", ""))
    assert faces["libelle"] == "1,56 pt · noir" and faces["planches"] == [7] and faces["longueur_m"] == pytest.approx(24.0, abs=0.01)
    # traits d'abord, du plus long au plus court, puis remplissages
    assert [s["genre"] for s in liste] == ["trait"] * 5 + ["aplat"] * 2

    elements = signatures.elements_de_signature(traits, aplats, signatures.cle_trait(0.24, "#000000", ""))
    assert elements == {"segments": [[round(L, 2), round(e / 2, 2), round(L + baie, 2), round(e / 2, 2)]], "tronque": False}
    remplissage = signatures.elements_de_signature(traits, aplats, signatures.cle_aplat("#989898"))
    assert len(remplissage["polygones"]) == 2


def test_fusion_ponderee_entre_planches():
    base = {"genre": "trait", "largeur": 0.24, "couleur": "#000000", "tirets": "", "luminance": 0, "part_courte": 0.0, "part_appariee": 0.0, "part_dans_murs": 0.0}
    a = {"signatures": [{**base, "cle": "trait|0.24|#000000|", "nombre": 10, "longueur_m": 30.0, "part_alignee": 0.4}]}
    b = {"signatures": [{**base, "cle": "trait|0.24|#000000|", "nombre": 5, "longueur_m": 10.0, "part_alignee": 0.0}]}
    (fusion,) = signatures.fusionner_catalogues([(1, a), (2, b)])
    assert (fusion["nombre"], fusion["longueur_m"], fusion["planches"]) == (15, 40.0, [1, 2])
    assert fusion["part_alignee"] == pytest.approx(0.3)
    assert fusion["role_propose"] == "vitrage"


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_catalogue_du_projet_et_validation_des_roles(db_session, monkeypatch):
    user = User(email="be@example.fr", password_hash=get_password_hash("motdepasse-solide"), nom="Nom", prenom="Prenom", role="USER", is_active=True)
    db_session.add(user)
    db_session.commit()
    projet = create_project(db_session, user, "Médiathèque", None)
    with pytest.raises(ThermiqueError, match="Aucune planche"):
        thermique_metre.project_signatures(db_session, projet)

    document = ThermiqueDocument(
        project_id=projet.id, original_filename="plans.pdf", stored_filename="plans.pdf", file_format="pdf", size_bytes=1, sha256="0" * 64, page_count=3
    )
    db_session.add(document)
    db_session.flush()
    for index, (label, nature, echelle) in enumerate([("PC02 Niveau -1", "plan", 100), ("PC10 Coupe AB", "coupe", 100), ("PC03 Niveau 0", "plan", None)]):
        db_session.add(
            ThermiqueSheet(
                project_id=projet.id, document_id=document.id, page_index=index, label=label, nature=None, nature_suggested=nature,
                level_label=None, rotation_deg=0, page_width_pt=1684, page_height_pt=2384, scale_denominator=echelle,
                scale_source="declaree" if echelle else None,
            )
        )
    db_session.commit()

    trait = {"cle": "trait|1.56|#000000|", "genre": "trait", "largeur": 1.56, "couleur": "#000000", "tirets": "", "luminance": 0, "nombre": 4,
             "longueur_m": 20.0, "part_courte": 0.0, "part_appariee": 0.9, "part_dans_murs": 0.0, "part_alignee": 0.0}
    aplat = {"cle": "aplat|#989898", "genre": "aplat", "couleur": "#989898", "luminance": 152, "nombre": 8, "aire_m2": 6.0, "part_dans_murs": 0.95}
    lus = []
    monkeypatch.setattr(thermique_metre, "sheet_signature_catalogue", lambda sheet: lus.append(sheet.label) or {"signatures": [trait, aplat]})

    catalogue = thermique_metre.project_signatures(db_session, projet)
    assert lus == ["PC02 Niveau -1"]  # seules les planches de plan à l'échelle définie
    assert (catalogue["validees"], catalogue["total"]) == (0, 2)
    assert [(s["role_propose"], s["role"]) for s in catalogue["signatures"]] == [("face_mur", None), ("maconnerie", None)]

    thermique_metre.save_signature_roles(db_session, projet, {"trait|1.56|#000000|": "face_mur", "aplat|#989898": "isolant"})
    assert json.loads(projet.signatures_json) == {"trait|1.56|#000000|": "face_mur", "aplat|#989898": "isolant"}
    thermique_metre.save_signature_roles(db_session, projet, {"aplat|#989898": None})
    catalogue = thermique_metre.project_signatures(db_session, projet)
    assert (catalogue["validees"], [s["role"] for s in catalogue["signatures"]]) == (1, ["face_mur", None])

    with pytest.raises(ThermiqueError, match="Rôle inconnu"):
        thermique_metre.save_signature_roles(db_session, projet, {"aplat|#989898": "face_mur"})
    with pytest.raises(ThermiqueError, match="Signature inconnue"):
        thermique_metre.save_signature_roles(db_session, projet, {"calque|x": "face_mur"})
    with pytest.raises(ThermiqueError, match="Signature inconnue"):
        thermique_metre.sheet_signature_elements(db_session.get(ThermiqueSheet, 1), "calque|x")
