"""Bibliothèque des matériaux (lot B2a) : lecture des tableaux, édition publiée, calcul d'une
paroi avec des matériaux de la bibliothèque. Voir docs/thermique/bibliotheque-composants-decisions.md."""
from __future__ import annotations

import pytest

from thermique_moteur.bibliotheque.materiaux import (
    charger_edition,
    conductivite,
    index_materiaux,
    intervalle_masse_volumique,
)
from thermique_moteur.parois import calculer_paroi, epaisseur_isolant


def test_lecture_des_conductivites_et_appels_de_note():
    assert conductivite("2,00") == (2.0, None)
    assert conductivite("230") == (230.0, None)
    assert conductivite("0,25*") == (0.25, "*")
    assert conductivite("1,3 (*)") == (1.3, "(*)")
    assert conductivite("Voir les annexes IX") == (None, None)


def test_lecture_des_masses_volumiques():
    assert intervalle_masse_volumique("2 300 < ρ ≤ 2 600") == (2300, 2600)
    assert intervalle_masse_volumique("15 ≤ ρ < 25") == (15, 25)
    assert intervalle_masse_volumique("ρ > 2 400") == (2400, None)
    assert intervalle_masse_volumique("ρ < 750") == (None, 750)
    assert intervalle_masse_volumique("2 700") == (2700, 2700)
    assert intervalle_masse_volumique("") == (None, None)


# --- Édition publiée (construite depuis le fascicule officiel) ----------------------------


@pytest.fixture(scope="module")
def edition():
    return charger_edition()


@pytest.fixture(scope="module")
def materiaux(edition):
    return {m["id"]: m for m in edition["materiaux"]}


def test_edition_complete_et_constantes_recoupees(edition):
    controles = edition["controles"]
    assert edition["edition"] == "2017-12-20"
    assert controles["comptes"]["materiaux"] == 294 and controles["erreurs"] == []
    # 3 valeurs assorties d'une note du document + 2 μ lus « 00 » (verre cellulaire).
    assert len(controles["alertes"]) == 5
    assert edition["verification_constantes"] == {**edition["verification_constantes"], "ok": True, "manquants": []}
    assert edition["verification_constantes"]["controles"] == 14
    assert [f["section"] for f in edition["familles"]] == [f"2.{i}" for i in range(1, 10)]


def test_valeurs_lues_dans_le_fascicule(materiaux):
    assert (materiaux["2.2.1.1-1"]["lambda"], materiaux["2.2.1.1-1"]["rho_min"]) == (2.0, 2300)
    assert materiaux["2.2.1.1-2"]["lambda"] == 1.65
    laines_de_roche = [materiaux[f"2.6.2.1-{i}"]["lambda"] for i in range(1, 8)]
    assert laines_de_roche == [0.050, 0.044, 0.042, 0.044, 0.046, 0.047, 0.048]
    assert (materiaux["2.8-1"]["libelle"], materiaux["2.8-1"]["lambda"]) == ("Aluminium", 230)
    assert materiaux["2.5.1.1-1"]["lambda"] == 0.11 and "Epicéa" in materiaux["2.5.1.1-1"]["libelle"]
    gaz = {m["libelle"]: m["lambda"] for m in materiaux.values() if m["section"] == "2.9.7"}
    assert gaz["Krypton"] == 0.009 and gaz["Xénon"] == 0.0054


def test_libelle_replie_non_decoupe_et_note_rattachee(materiaux):
    # Plâtres §2.3.1 : un seul libellé replié sur 4 lignes pour 4 masses volumiques.
    libelles = {materiaux[f"2.3.1-{i}"]["libelle"] for i in range(1, 5)}
    assert len(libelles) == 1 and next(iter(libelles)).startswith("Plâtre « gaché serré » ou « très serré »")
    assert [materiaux[f"2.3.1-{i}"]["lambda"] for i in range(1, 5)] == [0.56, 0.43, 0.30, 0.18]
    plaque = materiaux["2.3.1-8"]
    assert plaque["lambda"] == 0.25 and plaque["statut"] == "alerte" and plaque["note_document"] == "*"
    assert "masse volumique" in plaque["note_texte"]


def test_paroi_composee_avec_la_bibliotheque():
    index = index_materiaux()
    paroi = {
        "type": "mur",
        "couches": [
            {"type": "materiau", "materiau_id": "2.3.1-8", "epaisseur_m": 0.013},  # plaque de plâtre, λ 0,25
            {"type": "materiau", "materiau_id": "2.6.2.2-4", "epaisseur_m": 0.10, "isolant": True},  # laine de verre, λ 0,041
            {"type": "materiau", "materiau_id": "2.2.1.1-1", "epaisseur_m": 0.20},  # béton plein, λ 2,0
        ],
    }
    resultat = calculer_paroi(paroi, index)
    attendu_rt = 0.13 + 0.013 / 0.25 + 0.10 / 0.041 + 0.20 / 2.0 + 0.04
    assert resultat["rt"] == pytest.approx(attendu_rt, abs=1e-3)
    assert resultat["couches"][1]["source"].startswith("2.6.2.2")
    epaisseur = epaisseur_isolant(paroi, 1, 0.25, index)
    assert epaisseur["up_obtenu"] <= 0.25 and epaisseur["epaisseur_arrondie_m"] >= epaisseur["epaisseur_min_m"]
