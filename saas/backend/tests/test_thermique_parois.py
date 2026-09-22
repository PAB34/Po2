"""Calcul d'une paroi opaque en couches (lot B2) : cas calculés à la main.
Voir thermique_moteur/parois.py et docs/thermique/bibliotheque-composants-decisions.md."""
from __future__ import annotations

import pytest

from thermique_moteur.parois import (
    ParoiError,
    calculer_paroi,
    chiffres_significatifs,
    epaisseur_isolant,
    resistance_lame_air,
)

# Mur, de l'intérieur vers l'extérieur : plâtre 13 mm, isolant 12 cm, béton 20 cm.
MUR = {
    "type": "mur",
    "couches": [
        {"type": "lambda", "libelle": "Plâtre", "lambda": 0.25, "epaisseur_m": 0.013},
        {"type": "lambda", "libelle": "Isolant", "lambda": 0.032, "epaisseur_m": 0.12, "isolant": True},
        {"type": "lambda", "libelle": "Béton", "lambda": 2.0, "epaisseur_m": 0.20},
    ],
}


def test_mur_isole_calcule_a_la_main():
    resultat = calculer_paroi(MUR)
    # ΣR = 0,052 + 3,75 + 0,10 = 3,902 ; RT = 0,13 + 3,902 + 0,04 = 4,072 ; U = 1 / 4,072
    assert (resultat["rsi"], resultat["rse"]) == (0.13, 0.04)
    assert resultat["r_couches"] == pytest.approx(3.902)
    assert resultat["rt"] == pytest.approx(4.072)
    assert resultat["up"] == pytest.approx(1 / 4.072, abs=1e-4)
    assert resultat["up_arrondi"] == 0.25  # deux chiffres significatifs


def test_resistances_superficielles_selon_la_paroi():
    plancher_haut = calculer_paroi({**MUR, "type": "plancher_haut"})
    plancher_bas = calculer_paroi({**MUR, "type": "plancher_bas"})
    sur_local = calculer_paroi({**MUR, "donne_sur": "local_non_chauffe"})
    assert (plancher_haut["rsi"], plancher_haut["rse"]) == (0.10, 0.04)
    assert (plancher_bas["rsi"], plancher_bas["rse"]) == (0.17, 0.04)
    assert (sur_local["rsi"], sur_local["rse"]) == (0.13, 0.13)  # Rsi des deux côtés


def test_lames_d_air_interpolees_et_plafonnees():
    assert resistance_lame_air(20, "horizontal") == pytest.approx(0.175)
    assert resistance_lame_air(75, "descendant") == pytest.approx(0.215)
    assert resistance_lame_air(300, "ascendant") == pytest.approx(0.16)
    with pytest.raises(ParoiError, match="300 mm"):
        resistance_lame_air(350, "horizontal")


def test_lame_d_air_fortement_ventilee():
    paroi = {
        "type": "mur",
        "couches": [
            {"type": "lambda", "lambda": 0.032, "epaisseur_m": 0.10, "isolant": True},
            {"type": "lame_air_ventilee"},
            {"type": "lambda", "libelle": "Bardage", "lambda": 0.13, "epaisseur_m": 0.02},
        ],
    }
    resultat = calculer_paroi(paroi)
    assert resultat["rse"] == 0.13 and resultat["couches"][2]["ignoree"]
    assert resultat["rt"] == pytest.approx(0.13 + 0.10 / 0.032 + 0.13, abs=1e-3)


def test_correction_delta_u2_et_ponts_integres():
    resultat = calculer_paroi({**MUR, "niveau_delta_u2": 3, "delta_u1": 0.02})
    attendu_du2 = 0.04 * (3.75 / 4.072) ** 2
    assert resultat["delta_u2"] == pytest.approx(attendu_du2, abs=1e-4)
    assert resultat["up"] == pytest.approx(1 / 4.072 + 0.02 + attendu_du2, abs=1e-4)
    with pytest.raises(ParoiError, match="couche isolante"):
        calculer_paroi({"type": "mur", "niveau_delta_u2": 2, "couches": [{"type": "lambda", "lambda": 2.0, "epaisseur_m": 0.2}]})


def test_epaisseur_d_isolant_pour_un_u_cible():
    # U 0,20 → RT 5 ; R isolant = 5 − (0,13 + 0,04 + 0,052 + 0,10) = 4,678 ; e = 4,678 × 0,032 = 0,1497 m
    resultat = epaisseur_isolant(MUR, 1, 0.20)
    assert resultat["epaisseur_min_m"] == pytest.approx(0.1497, abs=1e-4)
    assert resultat["epaisseur_arrondie_m"] == 0.15
    assert resultat["up_obtenu"] <= 0.20
    with pytest.raises(ParoiError, match="inatteignable"):
        epaisseur_isolant(MUR, 1, 0.02)


def test_arrondi_a_deux_chiffres_significatifs():
    assert chiffres_significatifs(0.24558) == 0.25
    assert chiffres_significatifs(1.234) == 1.2
    assert chiffres_significatifs(0.1996) == 0.2
