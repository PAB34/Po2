"""Lot E3 : qualification des limites, contrôle de couverture, édition des locaux et versions."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect

from app.services import thermique_calage_contours as calage
from app.services import thermique_etude_edition as edition
from app.services import thermique_etude_geometrie as geo
from app.services.thermique import ThermiqueError
from app.services.thermique_etudes import etat_editable, poser_etat_editable

# Repère de travail : page de 1000 x 1000 px, 10 px par mètre, bâtiment carré de 100 m x 100 m.
MANIFESTE = {
    "page_px": [1000, 1000],
    "px_par_m": 10,
    "batiment_px": [[0, 0], [1000, 0], [1000, 1000], [0, 1000]],
    "trous_px": [],
    "troncons": [],
}


def _piece(identifiant: str, points: list[list[float]], nom: str = "local", nature: str = "chauffe") -> dict:
    return {
        "id": identifiant,
        "category": "piece",
        "subtype": nom,
        "geometry_type": "polygon",
        "local": nature,
        "points": points,
    }


def _mur(points: list[list[float]]) -> dict:
    return {"category": "cloison", "subtype": "mur", "geometry_type": "polyline", "points": points}


def test_un_cote_sur_une_paroi_lue_se_distingue_d_une_limite_d_usage():
    # Le local occupe le quart nord-ouest : deux côtés sur l'enveloppe, un sur une cloison, un dans le vide.
    analyse = {
        "objects": [
            _piece("piece-001", [[0, 0], [500, 0], [500, 500], [0, 500]]),
            _mur([[500, 0], [500, 500]]),
        ]
    }
    limites = geo.limites_des_locaux(analyse, MANIFESTE)["piece-001"]
    assert limites[0] == "exterieur"  # côté nord, sur le bord du bâtiment
    assert limites[1] == "paroi"  # côté est, le long de la cloison
    assert limites[2] == "convention"  # côté sud, rien de dessiné
    assert limites[3] == "exterieur"  # côté ouest, sur le bord du bâtiment


def test_la_couverture_signale_le_manque_et_le_recouvrement():
    contours = {
        "piece-001": [[0, 0], [500, 0], [500, 1000], [0, 1000]],
        "piece-002": [[400, 0], [1000, 0], [1000, 1000], [400, 1000]],
    }
    controle = geo.controler_couverture(contours, MANIFESTE)
    assert controle["surface_emprise_m2"] == pytest.approx(10000, rel=1e-3)
    assert controle["surface_non_affectee_m2"] == pytest.approx(0, abs=0.5)
    # Les deux locaux se recouvrent sur une bande de 10 m sur 100 m.
    assert controle["chevauchement_m2"] == pytest.approx(1000, rel=1e-3)
    assert controle["chevauchements"][0]["locaux"] == ["piece-001", "piece-002"]
    assert geo.part_chevauchement_pct(controle) > edition.SEUIL_CHEVAUCHEMENT_PCT


def test_la_couverture_compte_l_interieur_non_affecte():
    contours = {"piece-001": [[0, 0], [500, 0], [500, 1000], [0, 1000]]}
    controle = geo.controler_couverture(contours, MANIFESTE)
    assert controle["surface_non_affectee_m2"] == pytest.approx(5000, rel=1e-3)
    assert controle["taux_couverture_pct"] == pytest.approx(50.0, abs=0.1)
    assert controle["zones_non_affectees"], "la zone à combler doit être rendue au thermicien"


def _analyse_deux_locaux() -> dict:
    return {
        "objects": [
            _piece("piece-001", [[0, 0], [1000, 0], [1000, 500], [0, 500]], "plateau"),
            _piece("piece-002", [[0, 500], [1000, 500], [1000, 1000], [0, 1000]], "annexe"),
        ]
    }


def test_couper_un_plateau_conserve_la_surface_totale():
    analyse = _analyse_deux_locaux()
    edition._couper(analyse, {"type": "couper", "id": "piece-001", "segment": [[400, -50], [400, 550]],
                              "noms": ["ouest", "est"]})
    pieces = {objet["id"]: objet for objet in analyse["objects"] if objet["category"] == "piece"}
    assert len(pieces) == 3
    contours = {identifiant: objet["points"] for identifiant, objet in pieces.items()}
    controle = geo.controler_couverture(contours, MANIFESTE)
    assert controle["chevauchement_m2"] == pytest.approx(0, abs=0.5)
    assert controle["surface_non_affectee_m2"] == pytest.approx(0, abs=0.5)
    assert sorted(objet["subtype"] for objet in pieces.values()) == ["annexe", "est", "ouest"]


def test_un_trait_court_suffit_mais_un_trait_hors_du_local_est_refuse():
    # Le trait est prolongé dans son axe : un geste court au milieu du local coupe bien de part en part.
    analyse = _analyse_deux_locaux()
    edition._couper(analyse, {"type": "couper", "id": "piece-001", "segment": [[400, 200], [400, 300]]})
    assert len([objet for objet in analyse["objects"] if objet["category"] == "piece"]) == 3

    ailleurs = _analyse_deux_locaux()
    with pytest.raises(ThermiqueError, match="de part en part"):
        edition._couper(ailleurs, {"type": "couper", "id": "piece-001", "segment": [[100, 700], [200, 700]]})


def test_fusionner_deux_locaux_mitoyens_puis_refuser_deux_locaux_distants():
    analyse = _analyse_deux_locaux()
    edition._fusionner(analyse, {"type": "fusionner", "ids": ["piece-001", "piece-002"], "nom": "plateau entier"})
    pieces = [objet for objet in analyse["objects"] if objet["category"] == "piece"]
    assert len(pieces) == 1 and pieces[0]["subtype"] == "plateau entier"
    controle = geo.controler_couverture({pieces[0]["id"]: pieces[0]["points"]}, MANIFESTE)
    assert controle["taux_couverture_pct"] == pytest.approx(100.0, abs=0.5)

    eloignes = {"objects": [_piece("piece-001", [[0, 0], [100, 0], [100, 100], [0, 100]]),
                            _piece("piece-002", [[500, 500], [600, 500], [600, 600], [500, 600]])]}
    with pytest.raises(ThermiqueError, match="ne se touchent pas"):
        edition._fusionner(eloignes, {"type": "fusionner", "ids": ["piece-001", "piece-002"]})


def test_ajouter_un_local_attribue_un_identifiant_et_conserve_sa_nature():
    analyse = _analyse_deux_locaux()
    edition._ajouter(
        analyse,
        {
            "type": "local_ajouter",
            "nom": "Gaine créée",
            "nature": "gaine_technique",
            "contour": [[100, 100], [200, 100], [200, 200], [100, 200]],
        },
    )
    nouveau = next(objet for objet in analyse["objects"] if objet["id"] == "piece-003")
    assert nouveau["subtype"] == "Gaine créée"
    assert nouveau["local"] == "gaine_technique"
    assert nouveau["evidence"] == "local tracé par le thermicien"


def test_supprimer_un_local_est_total_et_ne_touche_pas_aux_autres_objets():
    analyse = _analyse_deux_locaux()
    cloison = _mur([[0, 500], [1000, 500]])
    analyse["objects"].append(cloison)
    edition._supprimer(analyse, {"type": "local_supprimer", "id": "piece-001"})
    assert [objet["id"] for objet in analyse["objects"] if objet.get("category") == "piece"] == ["piece-002"]
    assert cloison in analyse["objects"]
    with pytest.raises(ThermiqueError, match="introuvable"):
        edition._supprimer(analyse, {"type": "local_supprimer", "id": "piece-999"})


def test_modifier_refuse_une_nature_inconnue_et_un_contour_hors_feuille():
    analyse = _analyse_deux_locaux()
    edition._modifier(analyse, {"type": "modifier", "id": "piece-001", "nature": "gaine_technique"})
    piece = next(objet for objet in analyse["objects"] if objet["id"] == "piece-001")
    assert piece["local"] == "gaine_technique"
    with pytest.raises(ThermiqueError, match="nature"):
        edition._modifier(analyse, {"type": "modifier", "id": "piece-001", "nature": "tiede"})
    with pytest.raises(ThermiqueError, match="sort de la feuille"):
        edition._modifier(analyse, {"type": "modifier", "id": "piece-001",
                                    "contour": [[0, 0], [1200, 0], [1200, 100]]})


def test_enregistrer_valide_le_local_et_fait_revoir_les_voisins():
    apres = {"locaux": [{"id": "piece-001", "nom": "Bureau"}, {"id": "piece-002", "nom": "Couloir"}]}
    etats = {
        "piece-001": {"status": "a_verifier", "motif": None},
        "piece-002": {"status": "valide", "motif": None},
        "piece-003": {"status": "valide", "motif": None},  # local disparu par fusion
    }
    resultat = edition.etats_apres_enregistrement(etats, apres, "piece-001", ["piece-002"], valider=True)
    assert resultat["piece-001"]["status"] == "valide"
    assert resultat["piece-002"]["status"] == "a_revoir"
    assert "Bureau" in resultat["piece-002"]["motif"]
    assert "piece-003" not in resultat


def test_une_version_ne_garde_que_les_pieces_et_se_repose_a_l_identique():
    contenu = {"analyse": {"objects": [_piece("piece-001", [[0, 0], [10, 0], [10, 10]]), _mur([[0, 0], [10, 0]])]}}
    pieces = etat_editable(contenu)
    assert [objet["id"] for objet in pieces] == ["piece-001"]

    modifie = copy.deepcopy(contenu)
    modifie["analyse"]["objects"][0]["points"] = [[0, 0], [20, 0], [20, 20]]
    repose = poser_etat_editable(modifie, pieces)
    formes = [objet for objet in repose["analyse"]["objects"] if objet["category"] == "piece"]
    assert formes[0]["points"] == [[0, 0], [10, 0], [10, 10]]
    # Les objets qui ne sont pas des pièces sont conservés.
    assert any(objet["category"] == "cloison" for objet in repose["analyse"]["objects"])


def test_voisins_modifies_ignore_le_local_travaille():
    avant = {"locaux": [{"id": "a", "fiche": {"x": 1}}, {"id": "b", "fiche": {"x": 1}}]}
    apres = {"locaux": [{"id": "a", "fiche": {"x": 2}}, {"id": "b", "fiche": {"x": 2}}]}
    assert edition.voisins_modifies(avant, apres, sauf="a") == ["b"]


def test_migration_0084_monte_et_redescend_isolee():
    """La chaîne complète ne tourne pas sous SQLite depuis 0007 : on teste la marche isolée."""
    moteur = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table(
        "thermique_etude_versions",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("etude_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(80), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=False),
        sa.Column("local_states_json", sa.Text(), nullable=False),
    )
    metadata.create_all(moteur)
    chemin = Path(__file__).parents[1] / "alembic" / "versions" / "0084_thermique_versions_pieces.py"
    spec = importlib.util.spec_from_file_location("migration_0084", chemin)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with moteur.begin() as connexion:
        connexion.execute(
            sa.text(
                "INSERT INTO thermique_etude_versions (etude_id, version_number, reason, content_json,"
                " local_states_json) VALUES (1, 1, 'import_initial', '{}', '{}')"
            )
        )
        migration.op = Operations(MigrationContext.configure(connexion))
        migration.upgrade()
        colonnes = {colonne["name"] for colonne in inspect(connexion).get_columns("thermique_etude_versions")}
        assert "pieces_json" in colonnes
        connexion.execute(
            sa.text(
                "INSERT INTO thermique_etude_versions (etude_id, version_number, reason, content_json,"
                " pieces_json, local_states_json) VALUES (1, 2, 'validation_local', NULL, '[]', '{}')"
            )
        )
        migration.downgrade()
        colonnes = {colonne["name"] for colonne in inspect(connexion).get_columns("thermique_etude_versions")}
        assert "pieces_json" not in colonnes
        # Une version sans contenu complet n'est pas restituable en 0083 : elle est écartée.
        restantes = connexion.execute(sa.text("SELECT version_number FROM thermique_etude_versions")).scalars().all()
        assert restantes == [1]


# --- Lot F1 : emprise intérieure et calage sur le relevé -----------------------------------------


def _releve_mur_nord() -> dict:
    """Un tronçon plein nord de 100 m, mur de 50 cm : de quoi tester l'emprise et le calage."""
    return {
        "elements": [
            {
                "troncon": "T01",
                "debut_m": 0.0,
                "fin_m": 100.0,
                "type": "paroi",
                "composant": "P1",
                "nu_exterieur_cm": 0,
                "nu_interieur_cm": -50,
                "confiance": 0.9,
                "a_verifier": False,
                "indice": "mur",
            }
        ],
        "catalogue": [],
        "observations": [],
    }


def _manifeste_avec_troncon() -> dict:
    manifeste = dict(MANIFESTE)
    manifeste["troncons"] = [
        {
            "id": "T01",
            "debut_m": 0.0,
            "local_debut_m": 0.0,
            "fin_m": 100.0,
            "origine_px": [0, 0],
            "direction": [1.0, 0.0],
            "normale_ext": [0.0, -1.0],
        }
    ]
    manifeste["perimetre_m"] = 100.0
    return manifeste


def test_l_emprise_interieure_retranche_l_epaisseur_des_murs():
    manifeste = _manifeste_avec_troncon()
    sans = geo.emprise_interieure(manifeste)
    avec = geo.emprise_interieure(manifeste, _releve_mur_nord())
    # Le mur fait 50 cm sur les 100 m du bord nord : 50 m² de moins.
    assert (sans.area - avec.area) / (manifeste["px_par_m"] ** 2) == pytest.approx(50, rel=0.02)


def test_une_bande_de_la_largeur_d_une_cloison_n_est_pas_un_manque():
    # Deux locaux séparés par 10 cm : le vide entre eux est une cloison, pas une surface à affecter.
    contours = {
        "piece-001": [[0, 0], [499, 0], [499, 1000], [0, 1000]],
        "piece-002": [[501, 0], [1000, 0], [1000, 1000], [501, 1000]],
    }
    controle = geo.controler_couverture(contours, MANIFESTE)
    assert controle["surface_non_affectee_m2"] == pytest.approx(0, abs=0.5)
    assert controle["zones_non_affectees"] == []


def test_le_calage_retire_du_local_ce_qui_mord_dans_le_mur():
    manifeste = _manifeste_avec_troncon()
    # Le local monte jusqu'à y = 0 : il mord donc dans les 50 cm de mur.
    analyse = {"objects": [_piece("piece-001", [[0, 0], [1000, 0], [1000, 500], [0, 500]])]}
    cale, rapport = calage.caler_locaux(analyse, manifeste, _releve_mur_nord())
    assert len(rapport) == 1
    assert rapport[0]["surface_retiree_m2"] == pytest.approx(50, rel=0.05)
    assert rapport[0]["deplacement_max_m"] == pytest.approx(0.5, abs=0.05)
    # Le contour commence maintenant au nu intérieur, soit 50 cm plus bas.
    y_min = min(point[1] for point in cale["objects"][0]["points"])
    assert y_min * manifeste["page_px"][1] / 1000 / manifeste["px_par_m"] == pytest.approx(0.5, abs=0.05)


def test_le_calage_ne_touche_pas_un_local_deja_bien_pose():
    manifeste = _manifeste_avec_troncon()
    analyse = {"objects": [_piece("piece-001", [[0, 60], [1000, 60], [1000, 500], [0, 500]])]}
    _cale, rapport = calage.caler_locaux(analyse, manifeste, _releve_mur_nord())
    assert rapport == []


def _manifeste_troncon_interieur() -> dict:
    """Un tronçon parcouru par sa face intérieure, en plein milieu du plan (patio, atrium, mitoyenneté).

    Sa normale pointe vers le haut : le « nu extérieur » de la paroi est à l'intérieur du bâtiment, avec
    un vrai local de l'autre côté. C'est le cas qui a fait manger des locaux entiers le 2026-09-23.
    """
    manifeste = dict(MANIFESTE)
    manifeste["troncons"] = [
        {
            "id": "U01",
            "debut_m": 0.0,
            "fin_m": 100.0,
            "local_debut_m": 0.0,
            "origine_px": [0, 300],
            "direction": [1.0, 0.0],
            "normale_ext": [0.0, -1.0],
            "ligne": "face_interieure",
        }
    ]
    manifeste["perimetre_m"] = 100.0
    return manifeste


def _releve_paroi_interieure() -> dict:
    """Paroi de 30 cm : le corps va de y = 300 px (nu intérieur) à y = 297 px (nu extérieur)."""
    return {
        "elements": [
            {
                "troncon": "U01",
                "debut_m": 0.0,
                "fin_m": 100.0,
                "type": "paroi",
                "composant": "P1",
                "nu_exterieur_cm": 30,
                "nu_interieur_cm": 0,
                "confiance": 0.9,
                "a_verifier": False,
                "indice": "refend",
            }
        ],
        "catalogue": [],
        "observations": [],
    }


def test_une_paroi_interieure_ne_deborde_pas_dans_le_local_d_en_face():
    # Le local s'arrête juste avant la paroi (y = 296 px, la paroi commence à 297).
    manifeste = _manifeste_troncon_interieur()
    analyse = {"objects": [_piece("piece-001", [[0, 100], [1000, 100], [1000, 296], [0, 296]])]}
    _cale, rapport = calage.caler_locaux(analyse, manifeste, _releve_paroi_interieure())
    # Sur une façade le corps déborde de 60 cm vers l'extérieur, où il n'y a rien. Ici l'extérieur du
    # tronçon est un local : déborder lui mangerait une bande de 60 cm sur toute sa longueur.
    assert rapport == []


def test_un_calage_qui_couperait_le_local_en_deux_est_refuse():
    manifeste = _manifeste_troncon_interieur()
    # Le local traverse la paroi de part en part : le retrait le couperait en deux morceaux.
    analyse = {"objects": [_piece("piece-001", [[0, 100], [1000, 100], [1000, 500], [0, 500]])]}
    avant = [list(point) for point in analyse["objects"][0]["points"]]
    cale, rapport = calage.caler_locaux(analyse, manifeste, _releve_paroi_interieure())
    assert len(rapport) == 1 and rapport[0]["applique"] is False
    assert "morceaux" in rapport[0]["motif"]
    # Refusé veut dire refusé : le contour n'a pas bougé d'un pixel.
    assert cale["objects"][0]["points"] == avant


def test_le_recalcul_redonne_le_trace_des_elements_les_liaisons_et_le_controle():
    """Version 3 : sans ces trois blocs, rien n'est dessinable et la chaîne ne se relit pas (D74, D75, D77)."""
    contenu = {
        "niveau": "R1",
        "analyse": {
            "objects": [_piece("piece-001", [[0, 60], [1000, 60], [1000, 500], [0, 500]], "Bureau")],
            "manifest": {"page_width_px": 1000, "page_height_px": 1000, "crop_box_px": [0, 0, 1000, 1000],
                         "width_px": 1000, "height_px": 1000},
        },
        "enveloppe": {"manifeste": _manifeste_avec_troncon(), "releve_brut": _releve_mur_nord()},
        "locaux": [],
    }
    contenu["enveloppe"]["releve_brut"]["elements"].append(
        {"troncon": "T01", "debut_m": 100.0, "fin_m": 100.0, "type": "angle_sortant", "composant": None,
         "nu_exterieur_cm": 0, "nu_interieur_cm": -50, "confiance": 0.9, "a_verifier": False, "indice": "angle"}
    )
    resultat = edition.reconstruire(contenu)
    assert resultat["enveloppe"]["objets"], "le tracé reprojeté des éléments doit revenir dans le fichier"
    assert [liaison["type"] for liaison in resultat["enveloppe"]["liaisons"]] == ["angle_sortant"]
    assert len(resultat["coherence"]["controles"]) == 6


# --- Gestes sur les éléments d'enveloppe (F4, D99 et D100) ----------------------


def _etude_avec_deux_elements() -> dict:
    """Un mur nord relevé en deux morceaux : de quoi en écarter un et voir le dessin changer."""
    releve = _releve_mur_nord()
    releve["elements"][0]["fin_m"] = 50.0
    releve["elements"].append(
        {
            "troncon": "T01",
            "debut_m": 50.0,
            "fin_m": 100.0,
            "type": "menuiserie",
            "composant": "M1",
            "nu_exterieur_cm": 0,
            "nu_interieur_cm": -20,
            "nu_exterieur_fin_cm": 0,
            "nu_interieur_fin_cm": -20,
            # Le relevé réel porte toujours ces champs, même vides : la chaîne les lit sans garde.
            "couches": [],
            "menuiserie_type": "fenetre",
            "cadre_cm": -4,
            "confiance": 0.5,
            "a_verifier": True,
            "indice": "double trait",
        }
    )
    return {
        "niveau": "R1",
        "analyse": {
            "objects": [_piece("piece-001", [[0, 60], [1000, 60], [1000, 500], [0, 500]], "Bureau")],
            "manifest": {"page_width_px": 1000, "page_height_px": 1000, "crop_box_px": [0, 0, 1000, 1000],
                         "width_px": 1000, "height_px": 1000},
        },
        "enveloppe": {"manifeste": _manifeste_avec_troncon(), "releve_brut": releve},
        "locaux": [],
    }


def test_une_correction_d_element_survit_au_recalcul():
    """Le point qui gouverne tout le lot (D99) : le dessin est régénéré, le relevé fait foi."""
    contenu = _etude_avec_deux_elements()
    resultat = edition.appliquer(
        contenu,
        [
            {
                "type": "element_corriger",
                "element": {"troncon": "T01", "debut_m": 50.0, "fin_m": 100.0},
                "changes": {"nu_interieur_cm": -35.0},
            }
        ],
    )
    corrige = resultat["enveloppe"]["releve_brut"]["elements"][1]
    assert corrige["nu_interieur_cm"] == -35.0
    assert corrige["releve_origine"]["nu_interieur_cm"] == -20
    assert corrige["a_verifier"] is False
    # Le tracé a été refait depuis le relevé corrigé, il n'a pas été laissé tel quel.
    assert resultat["enveloppe"]["objets"]


def test_un_element_ecarte_sort_du_dessin_mais_reste_dans_l_etude():
    contenu = _etude_avec_deux_elements()
    avant = len(edition.reconstruire(contenu)["enveloppe"]["objets"])

    resultat = edition.appliquer(
        contenu,
        [
            {
                "type": "element_ecarter",
                "element": {"troncon": "T01", "debut_m": 50.0, "fin_m": 100.0},
                "motif": "double trait de cotation pris pour une menuiserie",
            }
        ],
    )
    # Il n'est plus dessiné…
    assert len(resultat["enveloppe"]["objets"]) < avant
    # …mais il est toujours là, avec sa raison, donc réactivable (D100).
    ecarte = resultat["enveloppe"]["releve_brut"]["elements"][1]
    assert ecarte["exclu"] is True and "cotation" in ecarte["motif_exclusion"]

    revenu = edition.appliquer(
        resultat,
        [{"type": "element_reactiver", "element": {"troncon": "T01", "debut_m": 50.0, "fin_m": 100.0}}],
    )
    assert len(revenu["enveloppe"]["objets"]) == avant


def test_un_pont_ecarte_reste_dessine_mais_marque_ecarte():
    """D113 : l'invisible ne se corrige pas.

    Une liaison écartée disparaissait complètement du plan, puisque `liaisons` était calculée sur le
    seul relevé actif. Le thermicien ne pouvait donc plus la remettre dans le calcul : le geste était
    irréversible à l'œil. Elle reste maintenant dessinée, avec son drapeau — et aucun métré ne lit
    `liaisons`, donc rien n'est compté en trop.
    """
    contenu = _etude_avec_deux_elements()
    contenu["enveloppe"]["releve_brut"]["elements"].append(
        {"troncon": "T01", "debut_m": 100.0, "fin_m": 100.0, "type": "angle_sortant", "composant": None,
         "nu_exterieur_cm": 0, "nu_interieur_cm": -50, "confiance": 0.9, "a_verifier": True, "indice": "angle"}
    )
    ref = {"troncon": "T01", "debut_m": 100.0, "fin_m": 100.0}
    avant = edition.reconstruire(contenu)["enveloppe"]["liaisons"]
    assert [liaison["exclu"] for liaison in avant] == [False]

    apres = edition.appliquer(contenu, [{"type": "element_ecarter", "element": ref, "motif": "angle du tracé"}])
    liaisons = apres["enveloppe"]["liaisons"]
    assert len(liaisons) == 1, "la liaison écartée doit rester dessinable"
    assert liaisons[0]["exclu"] is True

    revenu = edition.appliquer(apres, [{"type": "element_reactiver", "element": ref}])
    assert revenu["enveloppe"]["liaisons"][0]["exclu"] is False


def _etude_avec_un_angle() -> tuple[dict, dict]:
    contenu = _etude_avec_deux_elements()
    contenu["enveloppe"]["releve_brut"]["elements"].append(
        {"troncon": "T01", "debut_m": 100.0, "fin_m": 100.0, "type": "angle_sortant", "composant": None,
         "nu_exterieur_cm": 0, "nu_interieur_cm": -50, "confiance": 0.9, "a_verifier": True, "indice": "angle"}
    )
    return contenu, {"troncon": "T01", "debut_m": 100.0, "fin_m": 100.0}


def test_reattribuer_un_pont_a_un_pont_type_survit_au_recalcul():
    """D : un pont mal reconnu change de type et reçoit son pont type NF EN ISO 14683, jugé du même geste."""
    contenu, ref = _etude_avec_un_angle()
    apres = edition.appliquer(
        contenu,
        [{"type": "element_corriger", "element": ref,
          "changes": {"type": "about_refend", "reference_pont": "IW3"}}],
    )
    pont = next(e for e in apres["enveloppe"]["releve_brut"]["elements"] if e["debut_m"] == 100.0)
    assert (pont["type"], pont["reference_pont"], pont["corrige"]) == ("about_refend", "IW3", True)
    assert pont["releve_origine"] == {"type": "angle_sortant", "reference_pont": None}
    # Et le recalcul suivant ne l'efface pas : le relevé fait foi (D99).
    pont = next(e for e in edition.reconstruire(apres)["enveloppe"]["releve_brut"]["elements"] if e["debut_m"] == 100.0)
    assert pont["reference_pont"] == "IW3"


def test_un_pont_absent_du_catalogue_est_a_modeliser_et_un_code_invente_est_refuse():
    contenu, ref = _etude_avec_un_angle()
    geste = {"type": "element_corriger", "element": ref, "changes": {"reference_pont": "a_modeliser"}}
    assert next(
        e for e in edition.appliquer(contenu, [geste])["enveloppe"]["releve_brut"]["elements"] if e["debut_m"] == 100.0
    )["reference_pont"] == "a_modeliser"
    with pytest.raises(ThermiqueError, match="inconnu du catalogue"):
        edition.appliquer(contenu, [{**geste, "changes": {"reference_pont": "C9"}}])


def test_un_mur_ne_porte_pas_de_pont_type():
    contenu, _ = _etude_avec_un_angle()
    with pytest.raises(ThermiqueError, match="Seul un pont thermique"):
        edition.appliquer(
            contenu,
            [{"type": "element_corriger", "element": {"troncon": "T01", "debut_m": 50.0, "fin_m": 100.0},
              "changes": {"reference_pont": "C1"}}],
        )


def _ajout(x: float, y: float, **reste) -> dict:
    return {"type": "pont_ajouter", "type_pont": "angle_sortant", "point": [x, y], **reste}


def test_un_pont_ajoute_garde_son_point_et_prend_le_local_qui_le_contient():
    """Remarque C, D157 : le point posé fait foi ; le tronçon ne donne que l'identité dans le relevé."""
    contenu = _etude_avec_deux_elements()
    apres = edition.appliquer(contenu, [_ajout(420.0, 200.0, reference_pont="C1")])
    ajoute = next(e for e in apres["enveloppe"]["releve_brut"]["elements"] if e.get("ajoute"))
    # Projeté sur T01 (100 m sur 1000 px) : 420 px donnent l'abscisse 42 m.
    assert (ajoute["troncon"], ajoute["debut_m"], ajoute["fin_m"]) == ("T01", 42.0, 42.0)
    assert ajoute["point_feuille"] == [420.0, 200.0]
    assert (ajoute["confirme"], ajoute["a_verifier"], ajoute["reference_pont"]) == (True, False, "C1")
    liaison = next(l for l in apres["enveloppe"]["liaisons"] if l["ajoute"])
    assert liaison["point"] == [420.0, 200.0], "le pont se dessine là où il a été posé, pas sur le tronçon"
    assert liaison["piece"] == "Bureau"
    # Et il compte dans la synthèse du local, comme un angle relevé par l'agent.
    synthese = next(s for s in apres["enveloppe"]["synthese_pieces"] if s["piece"] == "Bureau")
    assert synthese["ponts"]["angle_sortant"] == 1.0


def test_deux_ponts_poses_au_meme_endroit_restent_deux_elements():
    contenu = _etude_avec_deux_elements()
    apres = edition.appliquer(contenu, [_ajout(420.0, 200.0), _ajout(420.0, 200.0)])
    ajoutes = [e for e in apres["enveloppe"]["releve_brut"]["elements"] if e.get("ajoute")]
    assert [e["debut_m"] for e in ajoutes] == [42.0, 42.001]


def test_un_pont_ajoute_se_reattribue_et_s_ecarte_comme_les_autres():
    contenu = _etude_avec_deux_elements()
    ref = {"troncon": "T01", "debut_m": 42.0, "fin_m": 42.0}
    apres = edition.appliquer(
        contenu,
        [_ajout(420.0, 200.0),
         {"type": "element_corriger", "element": ref, "changes": {"type": "about_refend", "reference_pont": "IW1"}},
         {"type": "element_ecarter", "element": ref, "motif": "posé par erreur"}],
    )
    ajoute = next(e for e in apres["enveloppe"]["releve_brut"]["elements"] if e.get("ajoute"))
    assert (ajoute["type"], ajoute["reference_pont"], ajoute["exclu"]) == ("about_refend", "IW1", True)


def test_un_pont_ajoute_hors_feuille_ou_de_type_inconnu_est_refuse():
    contenu = _etude_avec_deux_elements()
    with pytest.raises(ThermiqueError, match="hors de la feuille"):
        edition.appliquer(contenu, [_ajout(1200.0, 200.0)])
    with pytest.raises(ThermiqueError, match="type du pont"):
        edition.appliquer(contenu, [_ajout(420.0, 200.0, type_pont="balcon")])
    with pytest.raises(ThermiqueError, match="inconnu du catalogue"):
        edition.appliquer(contenu, [_ajout(420.0, 200.0, reference_pont="Z9")])


def test_la_position_calculee_par_l_ecran_est_reprise_telle_quelle():
    """P5, D164 : l'écran situe le pont pour le poser sans attendre ; le serveur vérifie, il ne recalcule pas."""
    contenu = _etude_avec_deux_elements()
    apres = edition.appliquer(contenu, [_ajout(420.0, 200.0, troncon="T01", abscisse_m=41.999)])
    ajoute = next(e for e in apres["enveloppe"]["releve_brut"]["elements"] if e.get("ajoute"))
    assert (ajoute["troncon"], ajoute["debut_m"]) == ("T01", 41.999), "l'identité vue par l'écran est gardée"


def test_une_position_d_ecran_impossible_est_refusee():
    contenu = _etude_avec_deux_elements()
    with pytest.raises(ThermiqueError, match="n'existe pas"):
        edition.appliquer(contenu, [_ajout(420.0, 200.0, troncon="T99", abscisse_m=42.0)])
    with pytest.raises(ThermiqueError, match="sort de son tronçon"):
        edition.appliquer(contenu, [_ajout(420.0, 200.0, troncon="T01", abscisse_m=150.0)])
    with pytest.raises(ThermiqueError, match="occupe déjà"):
        edition.appliquer(
            contenu,
            [_ajout(420.0, 200.0, troncon="T01", abscisse_m=42.0), _ajout(420.0, 200.0, troncon="T01", abscisse_m=42.0)],
        )


def test_le_point_pdf_d_un_pont_ajoute_passe_en_repere_de_feuille():
    """L'écran n'envoie que des points PDF : la conversion se fait une fois, comme pour les contours."""
    converti = edition._operations_en_feuille(
        [{"type": "pont_ajouter", "type_pont": "angle_sortant", "point_pdf": [100.0, 50.0]}],
        [2, 0, 0, 2, 0, 0], 1000.0, 1000.0,
    )
    assert converti == [{"type": "pont_ajouter", "type_pont": "angle_sortant", "point": [200.0, 100.0]}]


def test_confirmer_un_element_ne_change_aucune_mesure():
    contenu = _etude_avec_deux_elements()
    avant = edition.reconstruire(contenu)
    apres = edition.appliquer(
        contenu,
        [{"type": "element_confirmer", "element": {"troncon": "T01", "debut_m": 50.0, "fin_m": 100.0}}],
    )
    assert apres["couverture"] == avant["couverture"]
    assert apres["enveloppe"]["releve_brut"]["elements"][1]["a_verifier"] is False


def test_un_geste_sans_element_designe_est_refuse():
    contenu = _etude_avec_deux_elements()
    with pytest.raises(ThermiqueError, match="n'est pas désigné"):
        edition.appliquer(contenu, [{"type": "element_confirmer"}])


def test_une_passe_sur_les_77_ponts_s_enregistre_en_un_seul_lot():
    """Erreur 422 du 2026-09-28 : 61 ponts jugés d'un coup dépassaient le plafond de 50 gestes."""
    from app.schemas.thermique import EtudeEnregistrement

    geste = {"type": "element_confirmer", "element": {"troncon": "T01", "debut_m": 1.0, "fin_m": 1.0}}
    assert len(EtudeEnregistrement(operations=[geste] * 227).operations) == 227


def _etude_a_valider(**drapeaux_mur) -> dict:
    """Un bureau, un mur douteux dessiné chez lui, un angle douteux, et un mur douteux chez le voisin."""
    element = lambda troncon, debut, fin, type_, **reste: {  # noqa: E731
        "troncon": troncon, "debut_m": debut, "fin_m": fin, "type": type_, "a_verifier": True, **reste
    }
    forme = lambda troncon, debut, fin, piece: {  # noqa: E731
        "source_parcours": {"troncon": troncon, "debut_m": debut, "fin_m": fin, "piece": piece}
    }
    return {
        "locaux": [{"id": "L1", "nom": "Bureau"}, {"id": "L2", "nom": "Salle"}],
        "enveloppe": {
            "releve_brut": {
                "elements": [
                    element("T01", 0.0, 3.0, "paroi", **drapeaux_mur),
                    element("T01", 3.0, 3.0, "angle_sortant"),
                    element("T02", 0.0, 4.0, "paroi"),
                ]
            },
            "objets": [forme("T01", 0.0, 3.0, "Bureau"), forme("T02", 0.0, 4.0, "Salle")],
            "liaisons": [{"type": "angle_sortant", "troncon": "T01", "abscisse_m": 3.0, "piece": "Bureau"}],
        },
    }


def test_valider_un_local_est_refuse_tant_qu_un_mur_douteux_n_est_pas_tranche():
    with pytest.raises(ThermiqueError, match="Il reste 1 mur ou menuiserie"):
        edition.valider_local(_etude_a_valider(), {}, "L1")


@pytest.mark.parametrize("drapeau", ["confirme", "corrige", "exclu"])
def test_un_mur_tranche_libere_la_validation_et_les_ponts_ne_la_bloquent_pas(drapeau):
    """Q7 : uniquement les côtés. L'angle douteux du bureau et le mur du voisin ne comptent pas."""
    etats = edition.valider_local(_etude_a_valider(**{drapeau: True}), {"L2": {"status": "a_verifier"}}, "L1")
    assert etats["L1"] == {"status": "valide", "motif": None}
    assert etats["L2"] == {"status": "a_verifier"}


def test_un_mur_douteux_qui_longe_deux_locaux_bloque_les_deux():
    """M2 : dessiné en deux morceaux, un par local ; chacun le rattache à son local."""
    contenu = _etude_a_valider()
    contenu["enveloppe"]["objets"] = [
        {"source_parcours": {"troncon": "T01", "debut_m": 0.0, "fin_m": 1.2, "piece": "Bureau"}},
        {"source_parcours": {"troncon": "T01", "debut_m": 1.2, "fin_m": 3.0, "piece": "Salle"}},
    ]
    assert len(edition.parois_a_trancher(contenu, "L1")) == 1
    assert len(edition.parois_a_trancher(contenu, "L2")) == 1


def test_un_mur_que_l_agent_n_a_pas_mis_en_doute_est_tenu_pour_acquis():
    assert edition.parois_a_trancher(_etude_a_valider(a_verifier=False), "L1") == []


def test_valider_un_local_inconnu_est_refuse():
    with pytest.raises(ThermiqueError, match="introuvable"):
        edition.valider_local(_etude_a_valider(), {}, "L9")


def test_une_extremite_de_mur_se_deplace_librement_et_passe_la_porte_du_serveur():
    """D249 : le point lâché donne la borne et la face intérieure à ce bout ; l'épaisseur est gardée, l'autre
    bout ne bouge pas. Le geste passe par le même chemin que le site (schéma, puis exclude_none)."""
    from app.schemas.thermique import EtudeEnregistrement

    corps = {
        "operations": [
            {"type": "paroi_extremite", "element": {"troncon": "T01", "debut_m": 0.0, "fin_m": 50.0},
             "extremite": "fin", "abscisse_m": 42.5, "nu_interieur_cm": -80.0},
        ],
        "motif": "elements",
        "valider": False,
    }
    gestes = [op.model_dump(exclude_none=True) for op in EtudeEnregistrement.model_validate(corps).operations]
    resultat = edition.appliquer(_etude_avec_deux_elements(), gestes)
    mur = resultat["enveloppe"]["releve_brut"]["elements"][0]
    assert (mur["debut_m"], mur["fin_m"]) == (0.0, 42.5)
    # Le bout déplacé : face intérieure à -80 cm, épaisseur de 50 cm gardée ; le début n'a pas bougé.
    assert (mur["nu_interieur_fin_cm"], mur["nu_exterieur_fin_cm"]) == (-80.0, -30.0)
    assert (mur["nu_interieur_cm"], mur["nu_exterieur_cm"]) == (-50, 0)
    assert mur["corrige"] is True and mur["releve_origine"]["bornes"] == [0.0, 50.0]
    # La ligne de métré suit : 42,5 m le long de la façade, 30 cm plus à l'intérieur au bout, donc en biais.
    ligne = next(l for l in resultat["enveloppe"]["lignes_metre"] if l["source_parcours"]["fin_m"] == 42.5)
    assert ligne["epaisseur_cm"] == 50 and ligne["longueur_m"] == pytest.approx(42.501, abs=0.001)


def test_une_extremite_ne_peut_pas_croiser_l_autre_ni_viser_autre_chose_qu_un_mur():
    contenu = _etude_avec_deux_elements()
    with pytest.raises(ThermiqueError, match="trop court"):
        edition.appliquer(contenu, [{"type": "paroi_extremite", "element": {"troncon": "T01", "debut_m": 0.0, "fin_m": 50.0},
                                     "extremite": "debut", "abscisse_m": 60.0, "nu_interieur_cm": -50.0}])
    with pytest.raises(ThermiqueError, match="mur actif"):
        edition.appliquer(contenu, [{"type": "paroi_extremite", "element": {"troncon": "T01", "debut_m": 50.0, "fin_m": 100.0},
                                     "extremite": "fin", "abscisse_m": 90.0, "nu_interieur_cm": -20.0}])
