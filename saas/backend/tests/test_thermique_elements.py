"""Éléments à résistance tabulée (lot B2b-1) : lecture des cellules, édition publiée, contrôles,
couche « élément » du calcul de paroi. Voir docs/thermique/bibliotheque-composants-decisions.md §10."""
from __future__ import annotations

import pytest

from thermique_moteur.bibliotheque.elements import (
    charger_edition,
    controler_monotonie,
    index_elements,
    lignes_cellule,
    lire_valeur,
)
from thermique_moteur.bibliotheque.materiaux import index_materiaux
from thermique_moteur.parois import ParoiError, calculer_paroi, epaisseur_isolant


def test_lecture_des_cellules():
    assert lire_valeur("0,51 (0,47)") == (0.51, 0.47)
    assert lire_valeur("0,5\n(0,45)") == (0.5, 0.45)
    assert lire_valeur("11,85") == (11.85, None)
    assert lire_valeur("–") == (None, None) and lire_valeur(None) == (None, None)
    # Indices du document (lo, le) rattachés à leur lettre, symboles de la zone privée d'Unicode.
    assert lignes_cellule("95  l  125\no") == ["95 ≤ lo ≤ 125"]
    assert lignes_cellule("125 < l o  140") == ["125 < lo ≤ 140"]
    assert lignes_cellule("0,16\n0,17") == ["0,16", "0,17"]


def test_monotonie_signale_la_case_fautive():
    tableau = {
        "axe_lignes": "Ligne",
        "axe_colonnes": "Épaisseur",
        "colonnes": ["10", "20", "30"],
        "lignes": [{"libelle": "A", "cles": {}, "valeurs": [0.1, 0.3, 0.2]}],
    }
    constats = controler_monotonie(tableau, {"colonnes": "croissant"})
    assert {(i, j) for i, j, _ in constats} == {(0, 1), (0, 2)}
    assert "0,2 après 0,3" in constats[0][2]


# --- Édition publiée (construite depuis les fascicules officiels) ------------------------------


@pytest.fixture(scope="module")
def edition():
    return charger_edition()


@pytest.fixture(scope="module")
def tableaux(edition):
    return {t["id"]: t for t in edition["tableaux"]}


def _ligne(tableau: dict, debut: str) -> tuple[int, dict]:
    return next((i, l) for i, l in enumerate(tableau["lignes"]) if l["libelle"].startswith(debut))


def test_edition_complete_et_controlee(edition):
    controles = edition["controles"]
    assert edition["edition"] == "2022-01-20"
    assert controles["comptes"] == {"tableaux": 40, "tableaux_image": 7, "valeurs": 1074}
    assert controles["erreurs"] == []
    # 4 valeurs non monotones du document (planchers T2 et T6) + l'épaisseur « 20,5 » des fibragglo.
    assert len(controles["alertes"]) == 5


def test_valeurs_lues_dans_les_grilles(tableaux):
    assert tableaux["murs-T14"]["lignes"][0]["valeurs"][:3] == [1.28, 1.5, 1.71]
    _, entrevous = _ligne(tableaux["planchers-T6"], "languette 30 mm, entrevous 120 mm, talon 95 ≤ lo ≤ 125")
    assert entrevous["valeurs"] == [1.84, 1.91, 1.96]
    _, laine = _ligne(tableaux["toitures-T1"], "Laines minérales")
    assert laine["valeurs"][-1] == 11.85
    _, languette = _ligne(tableaux["planchers-T14"], "languette 45 à 60 mm")  # lue à gauche de la grille
    assert languette["valeurs"][0] == 1.38
    t1 = tableaux["planchers-T1"]
    assert t1["lignes"][0]["valeurs"][:2] == [0.16, 0.19]
    assert t1["lignes"][0]["variantes"]["dalle_argile_expansee"][:2] == [0.19, 0.22]


def test_tableaux_transcrits_et_corrections_signales(tableaux):
    parpaing = tableaux["murs-T8"]
    assert parpaing["lecture"] == "image"
    _, bloc = _ligne(parpaing, "20 × 20 × 50, deux rangées")
    assert bloc["valeurs"] == [0.23] and bloc["variantes"]["parentheses"] == [0.21]
    fibragglo = tableaux["cloisons-T6"]
    assert fibragglo["statut"] == "alerte"
    assert [l["cles"]["Épaisseur (cm)"] for l in fibragglo["lignes"]][:3] == ["1,5", "2,0", "2,5"]
    assert any(s["message"].startswith("Correction") for s in fibragglo["signalements"])


def test_couche_element_dans_le_calcul_de_paroi(tableaux):
    materiaux, elements = index_materiaux(), index_elements()
    i, _ = _ligne(tableaux["murs-T8"], "20 × 20 × 50, deux rangées")
    paroi = {
        "type": "mur",
        "couches": [
            {"type": "materiau", "materiau_id": "2.3.1-8", "epaisseur_m": 0.013},
            {"type": "materiau", "materiau_id": "2.6.2.2-4", "epaisseur_m": 0.10, "isolant": True},
            {"type": "element", "tableau_id": "murs-T8", "ligne": i, "colonne": 0},
        ],
    }
    resultat = calculer_paroi(paroi, materiaux, elements)
    assert resultat["rt"] == pytest.approx(0.13 + 0.013 / 0.25 + 0.10 / 0.041 + 0.23 + 0.04, abs=1e-3)
    assert resultat["couches"][2]["source"] == "Th-Bât murs T8 p. 9, lu sur image"
    parasismique = {**paroi, "couches": [*paroi["couches"][:2], {**paroi["couches"][2], "variante": "parentheses"}]}
    assert calculer_paroi(parasismique, materiaux, elements)["couches"][2]["r"] == 0.21
    epaisseur = epaisseur_isolant(paroi, 1, 0.25, materiaux, elements=elements)
    assert epaisseur["up_obtenu"] <= 0.25


def test_case_signalee_ou_vide(tableaux):
    elements = index_elements()
    i, ligne = _ligne(tableaux["planchers-T6"], "languette 50 mm, entrevous 200 et + mm, talon 95 ≤ lo ≤ 125")
    plancher = {"type": "plancher_bas", "couches": [{"type": "element", "tableau_id": "planchers-T6", "ligne": i, "colonne": 1}]}
    resultat = calculer_paroi(plancher, None, elements)
    assert resultat["couches"][0]["r"] == ligne["valeurs"][1] == 2.65
    assert any("Valeur à vérifier" in r for r in resultat["remarques"])
    vide = {"type": "mur", "couches": [{"type": "element", "tableau_id": "murs-T1", "ligne": 0, "colonne": 4}]}
    with pytest.raises(ParoiError, match="pas de valeur"):
        calculer_paroi(vide, None, elements)
