"""Option C (D255 à D262) : les parois des locaux portent la composition ; le mur n'est plus un tracé à part."""
from __future__ import annotations

import copy

import pytest

from app.services import thermique_etude_edition as edition
from app.services import thermique_parois_locaux as parois_locaux
from app.services.thermique import ThermiqueError

# Page de 1000 x 1000 px, 10 px par mètre (repère de la feuille = pixels). Façade nord le long de y = 0 ;
# mur P1 de 50 cm dont la face intérieure est à y = 5. Le Bureau touche cette face sur 50 m.
MANIFESTE = {
    "page_px": [1000, 1000],
    "px_par_m": 10,
    "batiment_px": [[0, 0], [1000, 0], [1000, 1000], [0, 1000]],
    "trous_px": [],
    "perimetre_m": 100.0,
    "troncons": [
        {"id": "T01", "debut_m": 0.0, "local_debut_m": 0.0, "fin_m": 100.0, "origine_px": [0, 0],
         "direction": [1.0, 0.0], "normale_ext": [0.0, -1.0]},
    ],
}


def _etude() -> dict:
    mur = {
        "troncon": "T01", "debut_m": 0.0, "fin_m": 50.0, "type": "paroi", "composant": "P1",
        "couches": [{"nature": "mur", "epaisseur_cm": 20}, {"nature": "isolant", "epaisseur_cm": 12},
                    {"nature": "mur", "epaisseur_cm": 18}],
        "nu_exterieur_cm": 0, "nu_interieur_cm": -50, "confiance": 0.9, "a_verifier": False, "indice": "mur",
    }
    piece = {"id": "piece-001", "category": "piece", "subtype": "Bureau", "geometry_type": "polygon", "local": "chauffe",
             "points": [[0, 5], [500, 5], [500, 300], [0, 300]]}
    return {
        "niveau": "R1",
        "analyse": {"objects": [piece], "manifest": {"page_width_px": 1000, "page_height_px": 1000,
                                                     "crop_box_px": [0, 0, 1000, 1000], "width_px": 1000, "height_px": 1000}},
        "enveloppe": {"manifeste": copy.deepcopy(MANIFESTE),
                      "releve_brut": {"elements": [mur], "catalogue": [], "observations": []}},
        "locaux": [],
    }


def _paroi_nord(contenu: dict) -> dict:
    bureau = next(local for local in contenu["locaux"] if local["nom"] == "Bureau")
    return next(p for p in bureau["fiche"]["parois"] if abs(p["trace"][0][1] - 5) < 1 and abs(p["trace"][1][1] - 5) < 1)


def test_chaque_arete_du_local_donne_une_paroi_avec_la_proposition_du_releve():
    resultat = edition.reconstruire(_etude())
    bureau = next(local for local in resultat["locaux"] if local["nom"] == "Bureau")
    parois = bureau["fiche"]["parois"]
    # Quatre arêtes, quatre parois au moins (une arête dont ce qui est derrière change en donne plusieurs).
    assert len(parois) >= 4
    nord = _paroi_nord(resultat)
    assert nord["adjacence"] == "exterieur" and nord["deperditif"] is True
    assert nord["longueur_m"] == pytest.approx(50.0, abs=0.01)
    # Proposition tirée du mur relevé par l'IA, à valider : sa composition et son épaisseur.
    assert nord["proposition"]["composant"] == "P1" and nord["proposition"]["epaisseur_cm"] == 50
    # Le doublage BA13 présumé (D17) fait partie de la proposition : le thermicien le garde ou le retire.
    assert [c["epaisseur_cm"] for c in nord["proposition"]["couches"]] == [20, 12, 18, 1.3]
    assert nord["composition"] is None


def test_la_composition_validee_passe_le_schema_et_suit_un_contour_retouche():
    from app.schemas.thermique import EtudeEnregistrement

    nord = _paroi_nord(edition.reconstruire(_etude()))
    corps = {"operations": [{"type": "paroi_composer", "local": "piece-001", "trace": nord["trace"], "composant": "P1",
                             "couches": [{"nature": "mur", "epaisseur_cm": 20}, {"nature": "isolant", "epaisseur_cm": 16}]}],
             "motif": "elements", "valider": False}
    gestes = [op.model_dump(exclude_none=True) for op in EtudeEnregistrement.model_validate(corps).operations]
    resultat = edition.appliquer(_etude(), gestes)
    assert _paroi_nord(resultat)["composition"]["epaisseur_cm"] == 36
    assert len(resultat["compositions_parois"]) == 1

    # Le contour est retouché de 10 cm (1 unité de feuille) : la composition reste sur la même paroi.
    retouche = copy.deepcopy(resultat)
    retouche["analyse"]["objects"][0]["points"] = [[0, 6], [500, 6], [500, 300], [0, 300]]
    assert _paroi_nord_proche(edition.reconstruire(retouche))["composition"]["composant"] == "P1"

    # Valider à nouveau la même paroi remplace la composition au lieu d'en ajouter une.
    encore = edition.appliquer(resultat, [{**gestes[0], "couches": [{"nature": "mur", "epaisseur_cm": 25}]}])
    assert len(encore["compositions_parois"]) == 1 and _paroi_nord(encore)["composition"]["epaisseur_cm"] == 25


def _paroi_nord_proche(contenu: dict) -> dict:
    bureau = next(local for local in contenu["locaux"] if local["nom"] == "Bureau")
    return min(bureau["fiche"]["parois"], key=lambda p: abs(p["trace"][0][1] - 5) + abs(p["trace"][1][1] - 5))


def test_une_paroi_trop_eloignee_ne_recoit_pas_la_composition_d_une_autre():
    trace = [[0.0, 5.0], [500.0, 5.0]]
    assert parois_locaux.correspond(trace, [[0.0, 7.0], [500.0, 7.0]], MANIFESTE)  # 20 cm : même paroi
    assert not parois_locaux.correspond(trace, [[0.0, 15.0], [500.0, 15.0]], MANIFESTE)  # 1 m : autre paroi
    assert not parois_locaux.correspond(trace, [[250.0, 0.0], [250.0, 10.0]], MANIFESTE)  # perpendiculaire


def test_une_composition_sur_un_local_inconnu_ou_sans_couche_est_refusee():
    with pytest.raises(ThermiqueError, match="introuvable"):
        edition.appliquer(_etude(), [{"type": "paroi_composer", "local": "piece-999", "trace": [[0, 5], [500, 5]],
                                      "couches": [{"nature": "mur", "epaisseur_cm": 20}]}])
    with pytest.raises(ThermiqueError, match="au moins une couche"):
        edition.appliquer(_etude(), [{"type": "paroi_composer", "local": "piece-001", "trace": [[0, 5], [500, 5]], "couches": []}])


def test_migration_0089_garde_une_copie_complete_de_chaque_etude():
    """D259 : avant le métré par les côtés, chaque étude reçoit une version avec tout son contenu."""
    import importlib.util
    import json
    from pathlib import Path

    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    moteur = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table("thermique_etudes", metadata, sa.Column("id", sa.Integer(), primary_key=True),
             sa.Column("content_json", sa.Text()), sa.Column("local_states_json", sa.Text()))
    sa.Table("thermique_etude_versions", metadata, sa.Column("id", sa.Integer(), primary_key=True),
             sa.Column("etude_id", sa.Integer(), nullable=False), sa.Column("version_number", sa.Integer(), nullable=False),
             sa.Column("reason", sa.String(80), nullable=False), sa.Column("content_json", sa.Text()),
             sa.Column("pieces_json", sa.Text()), sa.Column("local_states_json", sa.Text(), nullable=False))
    metadata.create_all(moteur)
    chemin = Path(__file__).parents[1] / "alembic" / "versions" / "0089_thermique_sauvegarde_avant_parois_locaux.py"
    spec = importlib.util.spec_from_file_location("migration_0089", chemin)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    contenu = json.dumps(_etude())
    with moteur.begin() as connexion:
        connexion.execute(sa.text("INSERT INTO thermique_etudes (id, content_json, local_states_json) VALUES (1, :c, '{}')"),
                          {"c": contenu})
        connexion.execute(sa.text("INSERT INTO thermique_etude_versions (etude_id, version_number, reason, local_states_json)"
                                  " VALUES (1, 7, 'elements', '{}')"))
        migration.op = Operations(MigrationContext.configure(connexion))
        migration.upgrade()
        numero, motif, copie, pieces = connexion.execute(sa.text(
            "SELECT version_number, reason, content_json, pieces_json FROM thermique_etude_versions WHERE version_number = 8"
        )).one()
        assert motif == "sauvegarde_avant_metre_par_cotes" and copie == contenu
        assert [p["id"] for p in json.loads(pieces)] == ["piece-001"]
        migration.downgrade()
        assert connexion.execute(sa.text("SELECT COUNT(*) FROM thermique_etude_versions")).scalar() == 1


def test_une_paroi_devant_une_menuiserie_sans_mur_est_vitree():
    """Sur le R+1, 33 parois (75 m) longent un vitrage et aucun mur : elles vont à l'étape Menuiseries."""
    contenu = _etude()
    contenu["enveloppe"]["releve_brut"]["elements"][0].update({"type": "menuiserie", "couches": [], "menuiserie_type": "mur_rideau", "cadre_cm": -4})
    nord = _paroi_nord(edition.reconstruire(contenu))
    assert nord["vitree"] is True and nord["proposition"] is None
    assert _paroi_nord(edition.reconstruire(_etude()))["vitree"] is False


def _parois_nord(contenu: dict) -> list[dict]:
    bureau = next(local for local in contenu["locaux"] if local["nom"] == "Bureau")
    return sorted((p for p in bureau["fiche"]["parois"] if abs(p["trace"][0][1] - 5) < 1 and abs(p["trace"][1][1] - 5) < 1),
                  key=lambda p: min(p["trace"][0][0], p["trace"][1][0]))


def test_couper_une_paroi_composee_garde_la_composition_sur_ses_deux_morceaux():
    """D264, D265 : la coupure fait deux parois ; la composition de la paroi entière les couvre toutes les deux,
    puis valider un morceau ne change que lui ; retirer la coupure redonne une seule paroi."""
    nord = _paroi_nord(edition.reconstruire(_etude()))
    compose = edition.appliquer(_etude(), [{"type": "paroi_composer", "local": "piece-001", "trace": nord["trace"],
                                            "composant": "P1", "couches": [{"nature": "mur", "epaisseur_cm": 20}]}])
    coupe = edition.appliquer(compose, [{"type": "cote_couper", "local": "piece-001", "point": [250.0, 5.3]}])
    morceaux = _parois_nord(coupe)
    assert [m["longueur_m"] for m in morceaux] == [pytest.approx(25.0, abs=0.01)] * 2
    assert all(m["composition"]["epaisseur_cm"] == 20 for m in morceaux)

    vitrage = edition.appliquer(coupe, [{"type": "paroi_composer", "local": "piece-001", "trace": morceaux[1]["trace"],
                                         "composant": "M-rideau", "couches": [{"nature": "autre", "epaisseur_cm": 6}]}])
    gauche, droite = _parois_nord(vitrage)
    assert (gauche["composition"]["epaisseur_cm"], droite["composition"]["epaisseur_cm"]) == (20, 6)

    recolle = edition.appliquer(coupe, [{"type": "cote_recoller", "local": "piece-001", "point": [251.0, 5.0]}])
    assert len(_parois_nord(recolle)) == 1
    with pytest.raises(ThermiqueError, match="Aucune coupure"):
        edition.appliquer(recolle, [{"type": "cote_recoller", "local": "piece-001", "point": [251.0, 5.0]}])


def test_la_coupure_passe_le_schema_et_un_point_loin_de_la_paroi_ne_coupe_rien():
    from app.schemas.thermique import EtudeEnregistrement

    corps = {"operations": [{"type": "cote_couper", "local": "piece-001", "point_pdf": [10.0, 20.0]}], "motif": "elements", "valider": False}
    geste = EtudeEnregistrement.model_validate(corps).operations[0].model_dump(exclude_none=True)
    assert geste["point_pdf"] == [10.0, 20.0] and geste["local"] == "piece-001"
    loin = edition.appliquer(_etude(), [{"type": "cote_couper", "local": "piece-001", "point": [250.0, 60.0]}])
    assert len(_parois_nord(loin)) == 1


def test_une_menuiserie_est_posee_sur_la_paroi_qu_elle_longe():
    """D267, D268 : la baie relevée de 10 m sur les 50 m du mur nord se pose sur la paroi nord, à sa position ;
    une paroi couverte à 90 % par ses baies devient vitrée."""
    contenu = _etude()
    mur = contenu["enveloppe"]["releve_brut"]["elements"][0]
    mur["fin_m"] = 40.0
    contenu["enveloppe"]["releve_brut"]["elements"].append({
        **mur, "debut_m": 40.0, "fin_m": 50.0, "type": "menuiserie", "composant": "M1", "modele": "F1",
        "couches": [], "menuiserie_type": "fenetre", "cadre_cm": -4,
    })
    resultat = edition.reconstruire(contenu)
    nord = _paroi_nord(resultat)
    assert [(m["composant"], m["modele"], m["largeur_m"]) for m in nord["menuiseries"]] == [("M1", "F1", 10.0)]
    # Sa position est mesurée depuis le début de la ligne de la paroi ; sur le plan, elle va de x = 400 à 500.
    assert sorted(x for x, _ in nord["menuiseries"][0]["trace"]) == [pytest.approx(400.0), pytest.approx(500.0)]
    assert nord["vitree"] is False  # 20 % de baies : la paroi reste opaque

    tout_vitre = edition.appliquer(resultat, [{"type": "cote_couper", "local": "piece-001", "point": [400.0, 5.0]}])
    droite = _parois_nord(tout_vitre)[1]
    assert droite["longueur_m"] == pytest.approx(10.0, abs=0.01) and droite["vitree"] is True
    assert droite["menuiseries"][0]["largeur_m"] == pytest.approx(10.0, abs=0.01)


def test_une_composition_deja_validee_sur_le_mur_du_releve_est_reprise_comme_validee():
    """Le travail fait avant l'option C (D243 : composition validée mur par mur) n'est pas perdu."""
    contenu = _etude()
    contenu["enveloppe"]["releve_brut"]["elements"][0]["corrige"] = True
    nord = _paroi_nord(edition.reconstruire(contenu))
    assert nord["composition"]["reprise"] is True and nord["composition"]["composant"] == "P1"
    assert _paroi_nord(edition.reconstruire(_etude()))["composition"] is None  # simple lecture de l'IA : proposition
