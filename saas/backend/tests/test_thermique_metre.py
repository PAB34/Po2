"""Métré sur les plans, lot M1 : traits d'aimantation, repère commun, synthèse d'un niveau,
niveaux créés depuis les planches, tracés et isolement entre comptes.
Voir docs/thermique/metre-plans-decisions.md."""
from __future__ import annotations

import math

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.core.security import get_password_hash
from app.models.thermique import ThermiqueDocument, ThermiqueSheet
from app.models.user import User
from app.services import thermique_metre
from app.services.thermique import ThermiqueError, create_project
from app.services.thermique_composants import create_component
from thermique_moteur import metre, traits

M = 1000 / 100 / (25.4 / 72)  # points PDF pour 1 m à 1/100
RECTANGLE = [[100, 100], [100 + 10 * M, 100], [100 + 10 * M, 100 + 8 * M], [100, 100 + 8 * M]]  # 10 × 8 m


def _pdf(contenu: bytes) -> bytes:
    objets = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 400] /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(contenu) + contenu + b"\nendstream",
    ]
    sortie = b"%PDF-1.4\n"
    positions = []
    for numero, objet in enumerate(objets, 1):
        positions.append(len(sortie))
        sortie += b"%d 0 obj\n" % numero + objet + b"\nendobj\n"
    xref = len(sortie)
    sortie += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objets) + 1)
    sortie += b"".join(b"%010d 00000 n \n" % position for position in positions)
    sortie += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objets) + 1, xref)
    return sortie


# --- Moteur : traits ---------------------------------------------------------------------------


def test_traits_epais_retenus_pour_l_aimantation(tmp_path):
    # Une face de mur épaisse sous une matrice ×2, deux traits fins, un rectangle rempli (ignoré).
    contenu = b"q 2 0 0 2 0 0 cm 0.5 w 10 10 m 110 10 l S Q 0.2 w 10 50 m 200 50 l S 10 60 m 200 60 l S 10 100 50 50 re f"
    chemin = tmp_path / "plan.pdf"
    chemin.write_bytes(_pdf(contenu))

    lus = traits.lire_traits(chemin, 0)
    assert len(lus) == 3
    classes = traits.classes_epaisseur(lus)
    assert [(c["largeur"], c["nombre"]) for c in classes] == [(1.0, 1), (0.2, 2)]
    resultat = traits.extraire_aimantation(chemin, 0)
    assert resultat["seuil_propose"] == 1.0
    assert resultat["segments"] == [[20.0, 20.0, 220.0, 20.0]]
    assert len(traits.extraire_aimantation(chemin, 0, seuil=0.1)["segments"]) == 3


def test_seuil_propose_sur_les_plumes_du_plan_d_essai():
    # Plumes tracées du niveau 0 du projet d'essai (longueur en pt) : les murs sont en 0,96 et 1,56.
    classes = [
        {"largeur": 1.56, "longueur_pt": 13545}, {"largeur": 0.96, "longueur_pt": 10818},
        {"largeur": 0.48, "longueur_pt": 68090}, {"largeur": 0.36, "longueur_pt": 43033},
        {"largeur": 0.24, "longueur_pt": 10794}, {"largeur": 0.12, "longueur_pt": 34798},
    ]
    assert traits.seuil_propose(classes) == 0.96
    assert traits.seuil_propose([]) is None


# --- Moteur : repère, nord, tracés ------------------------------------------------------------


def test_repere_commun_et_nord():
    calage = {"a": [100.0, 100.0], "b": [100.0, 400.0]}  # A → B vers le haut de la feuille
    rep = metre.repere(calage, 100)
    x, y = metre.vers_projet(rep, [100 + M, 100])
    assert (x, y) == (pytest.approx(0.0, abs=1e-9), pytest.approx(-1.0))
    retour = metre.depuis_projet(rep, (x, y))
    assert retour == (pytest.approx(100 + M), pytest.approx(100.0))
    assert metre.angle_nord(rep, [0, 0], [0, 10]) == 0.0
    assert metre.angle_nord(rep, [0, 0], [-10, 0]) == 90.0
    with pytest.raises(metre.MetreError):
        metre.angle_nord(rep, [5, 5], [5, 5])
    assert metre.repere(calage, None) is None


def test_controle_des_calages_entre_niveaux():
    niveaux = [
        {"id": 1, "nom": "RDC", "echelle": 100, "calage": {"a": [0, 0], "b": [300, 0]}},
        {"id": 2, "nom": "R+1", "echelle": 100, "calage": {"a": [50, 0], "b": [350.5, 0]}},
        {"id": 3, "nom": "R+2", "echelle": 100, "calage": {"a": [0, 0], "b": [310, 0]}},
        {"id": 4, "nom": "Sans calage", "echelle": 100, "calage": None},
    ]
    controle = metre.controle_calages(niveaux)
    assert controle["par_niveau"][1]["ab_m"] == pytest.approx(10.583, abs=1e-3)
    assert abs(controle["par_niveau"][2]["ecart_m"]) < metre.TOLERANCE_CALAGE_M
    assert len(controle["alertes"]) == 1 and "R+2" in controle["alertes"][0]
    assert 4 not in controle["par_niveau"]


def test_nettoyage_des_points_et_des_cotes():
    points = metre.nettoyer_points([[0, 0], [0, 0.001], [100, 0], [100, 100], [0, 100], [0, 0]])
    assert len(points) == 4
    with pytest.raises(metre.MetreError, match="trois"):
        metre.nettoyer_points([[0, 0], [10, 0]])
    with pytest.raises(metre.MetreError, match="plat"):
        metre.nettoyer_points([[0, 0], [10, 0], [20, 0]])
    cotes = metre.normaliser_cotes([{"donne_sur": "lnc", "composant_id": "7"}], 3, "exterieur")
    assert cotes == [{"donne_sur": "lnc", "composant_id": 7}, {"donne_sur": "exterieur", "composant_id": None}] + [
        {"donne_sur": "exterieur", "composant_id": None}
    ]
    with pytest.raises(metre.MetreError, match="inconnu"):
        metre.normaliser_cotes([{"donne_sur": "jardin"}], 1, "exterieur")
    assert metre.auto_intersections([[0, 0], [100, 100], [100, 0], [0, 100]]) == [(0, 2)]
    assert metre.auto_intersections(RECTANGLE) == []


def test_synthese_d_un_niveau():
    garage = [[100, 100], [100 + 3 * M, 100], [100 + 3 * M, 100 + 4 * M], [100, 100 + 4 * M]]  # 12 m² dans le contour
    cave_voisine = [[100 + 10 * M, 100], [100 + 13 * M, 100], [100 + 13 * M, 100 + 4 * M], [100 + 10 * M, 100 + 4 * M]]
    zones = [
        {
            "id": 1,
            "type": "contour",
            "points": RECTANGLE,
            "cotes": [{"donne_sur": d, "composant_id": None} for d in ("exterieur", "lnc", "exterieur", "mitoyen")],
        },
        {"id": 2, "type": "lnc", "points": garage, "cotes": []},
        {"id": 3, "type": "lnc", "points": cave_voisine, "cotes": []},
    ]
    # Le nu extérieur borde le contour : ni déduit, ni signalé comme débordant.
    nu_exterieur = [[100 - 0.3 * M, 100 - 0.3 * M], [100 + 10.3 * M, 100 - 0.3 * M], [100 + 10.3 * M, 100 + 8.3 * M], [100 - 0.3 * M, 100 + 8.3 * M]]
    avec_nu = metre.synthese_niveau(100, 2.8, 0.2, zones + [{"id": 9, "type": "nu_exterieur", "points": nu_exterieur, "cotes": []}])
    assert avec_nu["surface_nu_exterieur_m2"] == pytest.approx(10.6 * 8.6)
    assert avec_nu["surface_chauffee_m2"] == pytest.approx(68.0)
    assert avec_nu["zones"][3]["alertes"] == [] and avec_nu["zones"][3]["incluse_dans_contour"] is None

    synthese = metre.synthese_niveau(100, 2.8, 0.2, zones)
    assert synthese["surface_contour_m2"] == pytest.approx(80.0)
    assert synthese["surface_chauffee_m2"] == pytest.approx(68.0)  # le garage est déduit, la cave voisine non
    assert [z["incluse_dans_contour"] for z in synthese["zones"]] == [None, True, False]
    assert synthese["zones"][0]["cotes_m"] == [pytest.approx(10), pytest.approx(8), pytest.approx(10), pytest.approx(8)]
    assert synthese["lineaires_m"] == {"exterieur": 20.0, "lnc": 8.0, "sol": 0.0, "mitoyen": 8.0}
    assert synthese["hauteur_interieure_m"] == pytest.approx(2.6)
    assert synthese["surfaces_murs_m2"]["exterieur"] == pytest.approx(52.0)
    assert synthese["alertes"] == [] and all(z["alertes"] == [] for z in synthese["zones"])

    debordant = [[100 + 8 * M, 100 + 2 * M], [100 + 12 * M, 100 + 2 * M], [100 + 12 * M, 100 + 4 * M], [100 + 8 * M, 100 + 4 * M]]
    noeud = [[0, 0], [100, 100], [100, 0], [0, 100]]
    synthese = metre.synthese_niveau(None, None, None, [zones[0], {"id": 4, "type": "lnc", "points": debordant, "cotes": []}])
    assert synthese["surface_chauffee_m2"] is None and "Échelle" in synthese["alertes"][0]
    synthese = metre.synthese_niveau(100, None, None, [zones[0], {"id": 4, "type": "lnc", "points": debordant, "cotes": []}])
    assert "Déborde" in synthese["zones"][1]["alertes"][0]
    synthese = metre.synthese_niveau(100, None, None, [{"id": 5, "type": "contour", "points": noeud, "cotes": []}])
    assert "recoupe" in synthese["zones"][0]["alertes"][0]


def test_niveaux_reconnus_dans_les_libelles():
    assert [metre.ordre_niveau(t) for t in ("Niveau -1", "Niveau 2", "RDC", "R+3", "R-1", "Sous-sol", "Toiture", "Coupe", None)] == [
        -1, 2, 0, 3, -1, -1, None, None, None,
    ]
    planches = [
        {"id": 11, "nature": "plan", "niveau": "Niveau 1"},
        {"id": 12, "nature": "plan", "niveau": "Niveau -1"},
        {"id": 13, "nature": "coupe", "niveau": "Niveau 0"},
        {"id": 14, "nature": "plan", "niveau": "Toiture"},
        {"id": 15, "nature": "plan", "niveau": "Niveau 0"},
    ]
    assert [(n["nom"], n["planche_id"]) for n in metre.suggestion_niveaux(planches)] == [
        ("Niveau -1", 12), ("Niveau 0", 15), ("Niveau 1", 11),
    ]


# --- Service ------------------------------------------------------------------------------------


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _user(db: Session, email: str) -> User:
    user = User(email=email, password_hash=get_password_hash("motdepasse-solide"), nom="Nom", prenom="Prenom", role="USER", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _planches(db: Session, project) -> list[ThermiqueSheet]:
    document = ThermiqueDocument(
        project_id=project.id, original_filename="plans.pdf", stored_filename="plans.pdf", file_format="pdf",
        size_bytes=1, sha256="0" * 64, page_count=5,
    )
    db.add(document)
    db.flush()
    planches = []
    for index, (label, nature, niveau) in enumerate(
        [("PC02 Niveau -1", "plan", "Niveau -1"), ("PC03 Niveau 0", "plan", "Niveau 0"), ("PC04 Niveau 1", "plan", "Niveau 1"),
         ("PC07 Toiture", "plan", "Toiture"), ("PC10 Coupe AB", "coupe", None)]
    ):
        planche = ThermiqueSheet(
            project_id=project.id, document_id=document.id, page_index=index, label=label, nature=None,
            nature_suggested=nature, level_label=niveau, rotation_deg=0, page_width_pt=1684, page_height_pt=2384,
            scale_denominator=100, scale_source="declaree",
        )
        db.add(planche)
        planches.append(planche)
    db.commit()
    return planches


def test_niveaux_traces_et_synthese(db_session):
    thermicien = _user(db_session, "be@example.fr")
    projet = create_project(db_session, thermicien, "Médiathèque", None)
    planches = _planches(db_session, projet)

    assert thermique_metre.create_levels_from_sheets(db_session, projet) == 3
    assert thermique_metre.create_levels_from_sheets(db_session, projet) == 0  # pas de doublon
    metre_projet = thermique_metre.serialize_metre(db_session, projet)
    assert [(n["nom"], n["ordre"], n["planche_id"]) for n in metre_projet["niveaux"]] == [
        ("Niveau -1", -1, planches[0].id), ("Niveau 0", 0, planches[1].id), ("Niveau 1", 1, planches[2].id),
    ]
    rdc = thermique_metre.get_level_for_user(db_session, thermicien, metre_projet["niveaux"][1]["id"])

    with pytest.raises(ThermiqueError, match="Calez"):
        thermique_metre.set_north(db_session, projet, rdc, [0, 0], [0, 10])
    thermique_metre.update_level(
        db_session, projet, rdc,
        {"hauteur_etage_m": 3.0, "epaisseur_plancher_m": 0.25, "calage": {"a": [100, 100], "b": [400, 100]}},
    )
    thermique_metre.set_north(db_session, projet, rdc, [0, 0], [0, 10])
    assert projet.north_deg == 90.0
    with pytest.raises(ThermiqueError, match="hors limites"):
        thermique_metre.update_level(db_session, projet, rdc, {"hauteur_etage_m": 80})
    db_session.rollback()

    mur = create_component(db_session, thermicien, projet, {"categorie": "murs"})
    contour = thermique_metre.create_zone(
        db_session, rdc, {"type": "contour", "points": RECTANGLE, "cotes": [{"donne_sur": "exterieur", "composant_id": mur.id}]}
    )
    garage = thermique_metre.create_zone(
        db_session, rdc, {"type": "lnc", "type_lnc": "garage", "points": [[100, 100], [100 + 3 * M, 100], [100 + 3 * M, 100 + 4 * M], [100, 100 + 4 * M]]}
    )
    assert (contour.name, garage.name) == ("Nu intérieur", "Garage, parking")
    nu_ext = thermique_metre.create_zone(db_session, rdc, {"type": "nu_exterieur", "points": RECTANGLE})
    assert nu_ext.name == "Nu extérieur" and nu_ext.edges_json == "[]"
    thermique_metre.update_zone(db_session, nu_ext, {"points": RECTANGLE[:3]})
    assert nu_ext.edges_json == "[]"
    with pytest.raises(ThermiqueError, match="contour chauffé"):
        thermique_metre.detect_walls(db_session, nu_ext)
    thermique_metre.delete_zone(db_session, nu_ext)
    with pytest.raises(ThermiqueError, match="Composant inconnu"):
        thermique_metre.update_zone(db_session, contour, {"cotes": [{"donne_sur": "exterieur", "composant_id": 9999}]})
    db_session.rollback()

    # Un sommet ajouté : les qualifications existantes sont gardées, la nouvelle prend la valeur par défaut.
    cinq_points = RECTANGLE[:2] + [[100 + 10 * M, 100 + 4 * M]] + RECTANGLE[2:]
    thermique_metre.update_zone(db_session, contour, {"points": cinq_points})
    niveau = thermique_metre.serialize_metre(db_session, projet)["niveaux"][1]
    zone = niveau["zones"][0]
    assert len(zone["cotes"]) == 5 and zone["cotes"][0]["composant_id"] == mur.id
    assert niveau["synthese"]["surface_chauffee_m2"] == pytest.approx(68.0)
    assert niveau["synthese"]["surfaces_murs_m2"]["exterieur"] == pytest.approx(36 * 2.75)
    assert niveau["calage_ab_m"] == pytest.approx(300 / M, abs=1e-3)

    # Changer de planche efface le calage, propre au plan.
    thermique_metre.update_level(db_session, projet, rdc, {"planche_id": planches[2].id})
    assert rdc.calage_json is None
    thermique_metre.delete_level(db_session, rdc)
    assert len(thermique_metre.serialize_metre(db_session, projet)["niveaux"]) == 2


def test_metre_isole_entre_comptes(db_session):
    thermicien = _user(db_session, "be@example.fr")
    autre = _user(db_session, "autre@example.fr")
    projet = create_project(db_session, thermicien, "Projet", None)
    planches = _planches(db_session, projet)
    niveau = thermique_metre.create_level(db_session, projet, {"nom": "RDC", "planche_id": planches[1].id})
    zone = thermique_metre.create_zone(db_session, niveau, {"type": "contour", "points": RECTANGLE})
    assert thermique_metre.get_level_for_user(db_session, autre, niveau.id) is None
    assert thermique_metre.get_zone_for_user(db_session, autre, zone.id) is None
    autre_projet = create_project(db_session, autre, "Autre", None)
    with pytest.raises(ThermiqueError, match="n'appartient pas"):
        thermique_metre.create_level(db_session, autre_projet, {"planche_id": planches[1].id})
    sans_planche = thermique_metre.create_level(db_session, projet, {"nom": "Combles"})
    with pytest.raises(ThermiqueError, match="planche"):
        thermique_metre.create_zone(db_session, sans_planche, {"type": "contour", "points": RECTANGLE})
    assert math.isclose(sans_planche.position, niveau.position + 1)
