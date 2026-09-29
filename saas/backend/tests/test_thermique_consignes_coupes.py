"""Lecture des coupes par l'agent : images quadrillées, conversions, chaîne rejouée sans agent (S5, D181)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.services import thermique_consignes_coupes as consignes
from app.services import thermique_coupes as coupes
from app.services import thermique_lecture_coupes as lecture

BACKEND = Path(__file__).resolve().parents[1]


def test_une_vue_tournee_se_remet_dans_le_repere_de_la_coupe():
    """PC10 : le haut de la coupe A est la droite de la page ; sa droite est donc le bas (−y)."""
    vue = {"nom": "COUPE A", "nature": "coupe", "cadre": [882, 978, 1573, 2003], "haut": "droite"}
    brut = {
        "niveaux": [{"nom": "H10", "cote_m": 4.16, "position": 1252.0}, {"nom": "H11", "cote_m": 7.04, "position": 1335.0}],
        "pieces": [
            {"nom": "6.1.2 - Bur.1", "gauche": 1255.7, "droite": 1170.5, "sol": "H10", "plafond": "H11", "hsp_ecrite_m": None, "exterieur": False},
            {"nom": None, "gauche": 1339.1, "droite": 1562.8, "sol": 1252.0, "plafond": None, "hsp_ecrite_m": None, "exterieur": False},
        ],
    }
    lu = consignes.lecture_de_vue(vue, brut)
    assert lu["haut"] == [1.0, 0.0]
    bur = lu["pieces"][0]
    assert sorted((bur["debut"], bur["fin"])) == [-1255.7, -1170.5]
    assert (bur["sol"], bur["plafond"]) == ("H10", "H11")
    assert lu["pieces"][1]["sol"] == 1252.0 and lu["pieces"][1]["plafond"] is None
    [piece, vide] = coupes.pieces_de_la_vue(lu, 100)
    assert piece["plafond_m"] - piece["sol_m"] == pytest.approx(2.88)
    # Position calée sur les deux lignes de niveau (lues à 83 pt l'une de l'autre pour 2,88 m écrits) : à
    # quelques centimètres de H10, assez pour reconnaître l'étage.
    assert vide["sol_m"] == pytest.approx(4.16, abs=0.05)


def test_une_vue_droite_garde_ses_coordonnees():
    vue = {"nom": "COUPE CC", "nature": "coupe", "cadre": [0, 0, 100, 100], "haut": "haut"}
    lu = consignes.lecture_de_vue(vue, {"niveaux": [], "pieces": [
        {"nom": "Salle", "gauche": 10, "droite": 40, "sol": 20, "plafond": 70, "hsp_ecrite_m": 2.7, "exterieur": False}]})
    assert lu["pieces"][0] | {} == {"nom": "Salle", "debut": 10.0, "fin": 40.0, "sol": 20.0, "plafond": 70.0, "hsp_ecrite_m": 2.7, "exterieur": False}


def test_un_niveau_sans_cote_se_remplace_par_sa_position():
    vue = {"nom": "B", "nature": "coupe", "cadre": [0, 0, 1, 1], "haut": "haut"}
    lu = consignes.lecture_de_vue(vue, {"niveaux": [{"nom": "N1", "cote_m": None, "position": 300.0}], "pieces": [
        {"nom": None, "gauche": 0, "droite": 1, "sol": "N1", "plafond": None, "hsp_ecrite_m": None, "exterieur": False}]})
    assert lu["pieces"][0]["sol"] == 300.0
    lecture.valider_vues([lu])


def test_les_tuiles_couvrent_la_vue_en_se_recouvrant():
    cadres = consignes.tuiles([0, 0, 1000, 500])
    assert len(cadres) == 3 * 2
    assert min(c[0] for c in cadres) == 0 and max(c[2] for c in cadres) == 1000
    assert min(c[1] for c in cadres) == 0 and max(c[3] for c in cadres) == 500
    assert all(c[2] - c[0] <= consignes.TAILLE_TUILE_PT for c in cadres)
    assert consignes.tuiles([0, 0, 100, 100]) == [[0.0, 0.0, 100.0, 100.0]]


def test_un_zoom_precise_un_sommet_mais_pas_hors_de_son_cadre():
    traits = [consignes.trait_de_lecture({"nom": "A", "points": [[1140, 760], [1140, 1900]], "sens": "gauche"})]
    assert traits[0]["sens"] == [-1.0, 0.0]
    zooms = consignes.points_a_preciser(traits)
    for rang, zoom in enumerate(zooms):
        zoom["image"] = f"zoom-{rang}.png"
    reponse = {"extremites": [{"image": "zoom-0.png", "point": [1144.5, 763.0]}, {"image": "zoom-1.png", "point": [5000, 5000]}]}
    [precis] = consignes.appliquer_precisions(traits, zooms, reponse)
    assert precis["points"] == [[1144.5, 763.0], [1140.0, 1900.0]]


def _pdf(chemin: Path) -> Path:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument.new()
    document.new_page(1684, 2384)
    document.save(str(chemin))
    document.close()
    return chemin


def test_l_image_quadrillee_a_la_taille_demandee(tmp_path):
    from PIL import Image

    image = consignes.rendre_quadrille(_pdf(tmp_path / "p.pdf"), 0, [100, 200, 500, 400], 20, 800, tmp_path / "q.png")
    largeur, hauteur = Image.open(image).size
    assert largeur == pytest.approx(800, abs=2) and hauteur == pytest.approx(400, abs=2)


def test_la_reponse_reelle_de_l_agent_sur_pc04_se_recupere():
    """Réponse de l'essai du 2026-09-29 : clé « coupes » au lieu de « traits », trait C à une seule extrémité et
    sans sens. Les trois autres traits sont gardés, C est écarté et dit."""
    reponse = {
        "coupes": [
            {"nom": "A", "points": [[1148, 770], [1148, 1875]], "sens": "gauche"},
            {"nom": "B", "points": [[272, 1250], [1310, 1250]], "sens": "haut"},
            {"nom": "C", "points": [[770, 785]], "sens": None},
            {"nom": "D", "points": [[520, 915], [1405, 915]], "sens": "haut"},
        ],
        "observations": "…",
    }
    traits, ecartes = consignes.traits_de_lecture(consignes.liste_rendue(reponse, "traits"))
    assert [t["nom"] for t in traits] == ["A", "B", "D"]
    assert ecartes == ["trait « C » écarté : une seule extrémité lue"]
    assert consignes.liste_rendue({"a": [], "b": [], "observations": []}, "traits") is None


def test_la_reponse_de_l_agent_se_lit_meme_glissee_dans_du_texte():
    sys.path.insert(0, str(BACKEND / "scripts"))
    import run_lecture_coupes as chaine

    from app.services.thermique import ThermiqueError

    assert chaine.reponse_de_l_agent(json.dumps({"structured_output": {"vues": []}}), "x") == {"vues": []}
    texte = 'Voici la lecture : {"vues": [], "observations": []} — fin.'
    assert chaine.reponse_de_l_agent(json.dumps({"result": texte}), "x") == {"vues": [], "observations": []}
    with pytest.raises(ThermiqueError, match="error_max_turns"):
        chaine.reponse_de_l_agent(json.dumps({"subtype": "error_max_turns", "result": "J'ai lu 12 tuiles."}), "x")
    with pytest.raises(ThermiqueError, match="enveloppe JSON"):
        chaine.reponse_de_l_agent("pas du json", "x")


def test_une_page_blanche_ne_donne_aucune_tuile_a_lire(tmp_path):
    """Le quadrillage seul n'est pas du dessin : l'agent ne reçoit que des tuiles où quelque chose est dessiné."""
    assert consignes.rendre_ensemble(_pdf(tmp_path / "p.pdf"), 0, [0, 0, 1684, 2384], tmp_path, "ensemble") == []
    assert list(tmp_path.glob("ensemble-*.png")) == []


def test_la_chaine_rejouee_ecrit_une_lecture_que_le_site_accepte(tmp_path):
    """Réponses d'agent enregistrées : aucun appel à Claude Code, la chaîne entière tourne."""
    reponses = tmp_path / "reponses"
    reponses.mkdir()
    (reponses / "vues-ensemble.json").write_text(json.dumps({"vues": [
        {"nom": "COUPE A", "nature": "coupe", "cadre": [882, 978, 1573, 2003], "haut": "droite"},
        {"nom": "Zoom sur menuiserie", "nature": "detail", "cadre": [100, 100, 300, 300], "haut": "haut"},
    ], "observations": []}), encoding="utf-8")
    (reponses / "vue-00.json").write_text(json.dumps({"niveaux": [
        {"nom": "H10", "cote_m": 4.16, "position": 1252}, {"nom": "H11", "cote_m": 7.04, "position": 1335}],
        "pieces": [{"nom": "6.1.2 - Bur.1", "gauche": 1255.7, "droite": 1170.5, "sol": "H10", "plafond": "H11", "hsp_ecrite_m": None, "exterieur": False}],
        "observations": []}), encoding="utf-8")
    sortie = tmp_path / "travail"
    fini = subprocess.run(
        [sys.executable, str(BACKEND / "scripts" / "run_lecture_coupes.py"), str(_pdf(tmp_path / "coupes.pdf")),
         "--type", "coupes", "--sorties", str(sortie), "--reponses", str(reponses)],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert fini.returncode == 0, fini.stderr
    resultat = json.loads((sortie / "lecture.json").read_text(encoding="utf-8"))
    assert [v["nom"] for v in resultat["vues"]] == ["COUPE A", "Zoom sur menuiserie"]
    assert resultat["vues"][1]["nature"] == "detail" and resultat["vues"][1]["pieces"] == []
    assert len(list(sortie.glob("vue-00-tuile-*.png"))) == 6
    lecture.valider_vues(resultat["vues"])
