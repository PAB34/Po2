"""Étape E3 : pièces et noms (docs/thermique/refondation-parcours-decisions.md §13)."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.core.security import get_password_hash
from app.models.thermique import ThermiqueDocument, ThermiqueSheet
from app.models.user import User
from app.services import thermique_calques, thermique_pieces
from app.services.thermique import ThermiqueError, create_project
from thermique_moteur import calques, pieces, textes

M = 1000 / 100 / (25.4 / 72)  # points PDF pour 1 m à 1/100
MUR = "trait|1.56|#000000|"
MEUBLE = "trait|0.36|#000000|"


def _plan():
    """Bâtiment de 10 × 6 m ; cloison à x = 4 m percée d'une porte de 0,9 m ; une table dans la grande pièce."""
    return calques.assembler(
        [
            (calques.TRAIT, MUR, "grand_ferme", [0, 0, 10 * M, 0, 10 * M, 6 * M, 0, 6 * M, 0, 0]),
            (calques.TRAIT, MUR, "droit", [4 * M, 0, 4 * M, 2 * M]),
            (calques.TRAIT, MUR, "droit", [4 * M, 2.9 * M, 4 * M, 6 * M]),
            (calques.TRAIT, MEUBLE, "petit_ferme", [6 * M, 2 * M, 7 * M, 2 * M, 7 * M, 3 * M, 6 * M, 3 * M, 6 * M, 2 * M]),
        ],
        100,
    )


MURS = [0, 1, 2]


def _mot(texte, x, y, ligne=0, colonne=0):
    return {"texte": texte, "confiance": 90, "boite": [x, y, x + 0.5 * M, y + 0.2 * M], "image": [colonne, ligne, 10]}


def test_detection_des_pieces():
    plan = _plan()
    # porte ouverte : un seul espace
    ouvert = pieces.detecter(plan, MURS, fermeture_m=0.4)
    assert len(ouvert) == 1 and ouvert[0]["surface_m2"] == pytest.approx(60, abs=2)
    deux = pieces.detecter(plan, MURS, fermeture_m=1.0)
    # traits posés pile sur des bords de pixel (pire cas) : au plus un pixel de 5 cm perdu par côté
    assert [p["surface_m2"] for p in deux] == [pytest.approx(36, abs=0.8), pytest.approx(24, abs=0.8)]
    # angles droits restitués : la petite pièce est un rectangle de 4 × 6 m
    petite = deux[1]["contour"]
    assert len(petite) // 2 <= 12
    assert min(petite[0::2]) == pytest.approx(0, abs=0.1 * M) and max(petite[0::2]) == pytest.approx(4 * M, abs=0.1 * M)
    assert pieces.dedans(*deux[1]["centre"], petite)
    # la table (non désignée) n'est pas une limite
    assert pieces.piece_au_point(plan, MURS, 8 * M, 1 * M, 1.0)["surface_m2"] == pytest.approx(36, abs=1)
    assert pieces.piece_au_point(plan, MURS, 8 * M, 1 * M, 0.4)["surface_m2"] == pytest.approx(60, abs=2)
    with pytest.raises(pieces.PiecesError, match="pas fermé"):
        pieces.piece_au_point(plan, MURS, -0.5 * M, 1 * M, 1.0)
    with pytest.raises(pieces.PiecesError, match="hors des limites"):
        pieces.piece_au_point(plan, MURS, 30 * M, 1 * M, 1.0)
    with pytest.raises(pieces.PiecesError, match="Aucun calque"):
        pieces.detecter(plan, [])

    fusion = pieces.fusionner([deux[0]["contour"], deux[1]["contour"]], 100)
    assert fusion["surface_m2"] == pytest.approx(60, abs=2)
    coupe = pieces.decouper(deux[0]["contour"], [7 * M, -1 * M], [7 * M, 7 * M], 100)
    assert [p["surface_m2"] for p in coupe] == [pytest.approx(18, abs=0.8), pytest.approx(18, abs=0.8)]
    with pytest.raises(pieces.PiecesError, match="ne coupe pas"):
        pieces.decouper(deux[0]["contour"], [5 * M, 1 * M], [5.5 * M, 1 * M], 100)
    with pytest.raises(pieces.PiecesError, match="pas voisines"):
        pieces.fusionner([deux[1]["contour"], [20 * M, 0, 22 * M, 0, 22 * M, 2 * M, 20 * M, 2 * M]], 100)


def test_le_service_conserve_le_contour_detaille_apres_simplification():
    contour = [
        0, 0, 2.4 * M, 0, 2.4 * M, 0.12 * M, 3.3 * M, 0.12 * M,
        3.3 * M, 0, 6 * M, 0, 6 * M, 4 * M, 0, 4 * M,
    ]
    piece = {"contour": contour, "centre": [3 * M, 2 * M], "surface_m2": 23.9}
    simplifiee = thermique_pieces._en_quadrilatere(_plan(), piece)
    assert simplifiee["detaille"] == contour
    assert len(simplifiee["contour"]) == 8
    assert simplifiee["centre"] == piece["centre"]
    assert simplifiee["surface_m2"] == pytest.approx(24.0, abs=0.1)


def test_noms_et_classement():
    salle = [0, 0, 4 * M, 0, 4 * M, 6 * M, 0, 6 * M]
    mots = [
        _mot("conte", 1 * M, 2 * M, ligne=20),
        _mot("salle", 1 * M, 3 * M, ligne=0),
        _mot("6-B14", 1 * M, 1 * M, ligne=40),
        _mot("LL", 2 * M, 1 * M, ligne=40, colonne=50),
        _mot("Ti", 2 * M, 4 * M),
        _mot("garage", 8 * M, 3 * M),
    ]
    assert textes.nom_de_piece(mots, salle) == ("salle conte", "6-B14")
    assert textes.classer("Garage à vélos") == "non_chauffe"
    assert textes.classer("cour anglaise") == "exterieur"
    assert textes.classer("Salle d'activité") == "chauffe"


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_pieces_du_plan(db_session, monkeypatch):
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
    db_session.commit()
    plan = _plan()
    mots = {"valeur": None}
    monkeypatch.setattr(thermique_calques, "sheet_elements", lambda s: plan)
    monkeypatch.setattr(thermique_pieces, "sheet_elements", lambda s: plan)
    monkeypatch.setattr(thermique_pieces, "sheet_words", lambda s: mots["valeur"])

    vue = thermique_pieces.list_rooms(db_session, projet, sheet)
    assert vue["pieces"] == [] and vue["limites"] == {"elements": 0, "natures": []}
    with pytest.raises(ThermiqueError, match="Aucun calque"):
        thermique_pieces.detect_rooms(db_session, projet, sheet, 1.0)

    # le tracé manuel crée d'abord la pièce, même sans mur, porte ou menuiserie désigné
    contour_manuel = [0, 0, 4 * M, 0, 4 * M, 6 * M, 0, 6 * M]
    assert thermique_pieces.trace_room(db_session, projet, sheet, contour_manuel) is True
    vue = thermique_pieces.list_rooms(db_session, projet, sheet)
    assert vue["limites"] == {"elements": 0, "natures": []}
    assert [(p["source"], p["surface_m2"]) for p in vue["pieces"]] == [("manuel", pytest.approx(24.0, abs=0.1))]
    piece_manuelle = thermique_pieces.get_room(db_session, vue["pieces"][0]["id"])
    bordants = thermique_pieces.room_components(db_session, projet, sheet, piece_manuelle)
    assert {famille["signature"] for famille in bordants["familles"]} == {MUR}
    assert bordants["familles"][0]["nature"] is None  # attaché au contour avant toute qualification
    thermique_pieces.delete_room(db_session, piece_manuelle)

    thermique_calques.save_designation(db_session, projet, MUR, "*", "mur")

    # sans mots lus : les pièces arrivent sans nom et la lecture est à lancer
    assert thermique_pieces.detect_rooms(db_session, projet, sheet, 1.0) is True
    vue = thermique_pieces.list_rooms(db_session, projet, sheet)
    assert [(p["nom"], p["classe"]) for p in vue["pieces"]] == [("", "chauffe"), ("", "chauffe")]
    assert vue["pieces"][0]["surface_m2"] > 30 > vue["pieces"][1]["surface_m2"] > 20
    assert vue["limites"] == {"elements": 3, "natures": ["mur"]}

    mots["valeur"] = [_mot("garage", 8 * M, 3 * M), _mot("bureau", 1 * M, 3 * M)]
    assert thermique_pieces.detect_rooms(db_session, projet, sheet, 1.0) is False
    vue = thermique_pieces.list_rooms(db_session, projet, sheet)
    grande, petite = vue["pieces"]
    assert (grande["nom"], grande["classe"], grande["nom_source"]) == ("garage", "non_chauffe", "lu")
    assert vue["totaux"]["non_chauffe"] == grande["surface_m2"]

    # corrections : nom saisi et classe choisie survivent à une nouvelle lecture ; une redétection les remplace
    thermique_pieces.update_room(db_session, thermique_pieces.get_room(db_session, grande["id"]), {"nom": "Atelier", "classe": "chauffe"})
    thermique_pieces._nommer(thermique_pieces.get_room(db_session, grande["id"]), mots["valeur"])
    atelier = thermique_pieces.get_room(db_session, grande["id"])
    assert (atelier.name, atelier.classe, atelier.classe_source) == ("Atelier", "chauffe", "choisi")
    with pytest.raises(ThermiqueError, match="Classe inconnue"):
        thermique_pieces.update_room(db_session, atelier, {"classe": "tiede"})

    # le recalage manuel accepte un sommet ajouté sur un côté et devient la nouvelle géométrie de référence
    geometrie = json.loads(atelier.points_json)
    contour = geometrie["contour"]
    milieu = [(contour[0] + contour[2]) / 2, (contour[1] + contour[3]) / 2]
    thermique_pieces.update_room(db_session, atelier, {"contour": contour[:2] + milieu + contour[2:]})
    corrigee = json.loads(atelier.points_json)
    assert len(corrigee["contour"]) == len(contour) + 2
    assert "detaille" not in corrigee and atelier.source == "manuel"

    thermique_pieces.split_room(db_session, projet, atelier, [7 * M, -1 * M], [7 * M, 7 * M])
    vue = thermique_pieces.list_rooms(db_session, projet, sheet)
    assert sorted((p["nom"], p["source"]) for p in vue["pieces"]) == [("Atelier", "manuel"), ("Atelier", "manuel"), ("bureau", "auto")]
    moities = [p["id"] for p in vue["pieces"] if p["source"] == "manuel"]
    thermique_pieces.merge_rooms(db_session, projet, sheet, moities)
    vue = thermique_pieces.list_rooms(db_session, projet, sheet)
    atelier = next(p for p in vue["pieces"] if p["nom"] == "Atelier")
    assert len(vue["pieces"]) == 2 and atelier["surface_m2"] == pytest.approx(36, abs=1)

    # une redétection garde la pièce faite à la main et ne la double pas
    thermique_pieces.detect_rooms(db_session, projet, sheet, 1.0)
    assert sorted(p["nom"] for p in thermique_pieces.list_rooms(db_session, projet, sheet)["pieces"]) == ["Atelier", "bureau"]
    with pytest.raises(ThermiqueError, match="déjà dans une pièce"):
        thermique_pieces.add_room_at(db_session, projet, sheet, 1 * M, 1 * M, 1.0)
    bureau = next(p for p in thermique_pieces.list_rooms(db_session, projet, sheet)["pieces"] if p["nom"] == "bureau")
    thermique_pieces.delete_room(db_session, thermique_pieces.get_room(db_session, bureau["id"]))
    thermique_pieces.add_room_at(db_session, projet, sheet, 1 * M, 1 * M, 1.0)
    vue = thermique_pieces.list_rooms(db_session, projet, sheet)
    assert sorted((p["nom"], p["source"]) for p in vue["pieces"]) == [("Atelier", "manuel"), ("bureau", "manuel")]
    with pytest.raises(ThermiqueError, match="hors limites"):
        thermique_pieces.detect_rooms(db_session, projet, sheet, 5.0)
