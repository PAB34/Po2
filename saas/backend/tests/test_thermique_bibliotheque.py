"""Bibliothèque des menuiseries (lot B1) : extraction, contrôles automatiques, interpolation,
et autonomie du moteur. Voir docs/thermique/bibliotheque-composants-decisions.md."""
from __future__ import annotations

import copy
import re
from pathlib import Path

import pytest

from thermique_moteur.bibliotheque import menuiseries
from thermique_moteur.bibliotheque.menuiseries import (
    calcul_fermeture,
    charger_edition,
    controler,
    extraire_fenetres,
    extraire_fermetures,
    extraire_portes,
    interpoler,
)

MOTEUR = Path(menuiseries.__file__).resolve().parents[1]


def test_le_moteur_ne_depend_pas_de_po2():
    for fichier in MOTEUR.rglob("*.py"):
        contenu = fichier.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(from|import)\s+app\b", contenu, re.M), f"{fichier.name} importe Po2"


def test_extraction_d_un_tableau_de_fenetres():
    # Mise en page réelle : « Double avec » et « contrôle solaire » sur deux lignes, σ écrit
    # avec un point, intitulé doublé.
    pages = [
        (2, "2.1 Paroi vitrée sans protection solaire\n2.1.1 Fenêtre à un vantail, σ= 0,70 :\nUw\n"
            "Type de vitrage Sw1C Sw2C Sw3C Sw1 E Sw2 E Sw3 E TLw Tlw_dif\n"
            "Triple 2,0 0,32 0,08 0,00 0,39 0,10 0,00 0,46 0,00\n"
            "Double 2,3 0,34 0,07 0,00 0,42 0,09 0,00 0,50 0,00\n"
            "Double avec\ncontrôle solaire 2,3 0,18 0,05 0,00 0,22 0,07 0,00 0,38 0,00\n"),
        (3, "2.1.2 Porte-fenêtre à un vantail, Porte-fenêtre à un vantail, σ = 0.68 :\n"
            "Triple 1,9 0,33 0,07 0,00 0,41 0,10 0,00 0,50 0,00\n"),
    ]
    lignes, protections, anomalies = extraire_fenetres(pages)

    assert anomalies == []
    assert [l["vitrage"] for l in lignes] == ["triple", "double", "double_controle_solaire", "triple"]
    triple = lignes[0]
    assert (triple["menuiserie"], triple["vantaux"], triple["sigma"], triple["u"]) == ("fenetre", 1, 0.70, 2.0)
    assert triple["s_c"] == [0.32, 0.08, 0.0] and triple["s_e"] == [0.39, 0.10, 0.0] and triple["tl"] == 0.46
    assert lignes[2]["s_c"][0] == 0.18
    assert (lignes[3]["menuiserie"], lignes[3]["sigma"], lignes[3]["page"]) == ("porte_fenetre", 0.68, 3)
    assert protections[0]["intitule_document"].startswith("2.1 Paroi vitrée sans protection")
    assert all("correction" not in l for l in lignes)


def test_virgule_absente_dans_le_document_corrigee_et_signalee():
    # Coquille réelle du §2.5.3 : « 18 » imprimé pour un Uws de 1,8.
    pages = [(11, "2.5 AVEC protection solaire non-opaque et sombre (=0,07 et =0,77) située à\nl’extérieur\n"
                  "2.5.3 Fenêtre à deux vantaux, σ = 0,69 :\n"
                  "Triple 18 0,02 0,05 0,00 0,02 0,07 0,00 0,04 0,02\n")]
    lignes, _, anomalies = extraire_fenetres(pages)
    assert anomalies == []
    assert lignes[0]["u"] == 1.8 and lignes[0]["s_c"] == [0.02, 0.05, 0.0]
    assert "« 18 »" in lignes[0]["correction"] and "1,8" in lignes[0]["correction"]


def test_extraction_portes_et_fermetures_ignore_les_nombres_parasites():
    portes, anomalies = extraire_portes([(1, "Nature de la menuiserie Type de portes Coefficient Ud W/(m2.K)\n"
                                             "montants de 45 mm 3,5 3,3 4,0 4,5 3,3 5,8 5,8 5,5 4,8 5,8 5,8")])
    assert anomalies == [] and [p["ud"] for p in portes][:2] == [3.5, 3.3] and portes[-1]["ud"] == 5.8
    fermetures, anomalies = extraire_fermetures([(1, "Tableau 1 : Fermetures R\n0,08\n0,15\n(e ≤ 12 mm)\n0,19\n0,19\n0,25\n0,25")])
    assert anomalies == [] and [f["r"] for f in fermetures] == [0.08, 0.15, 0.19, 0.19, 0.25, 0.25]


# --- Édition publiée (construite depuis les PDF officiels) --------------------------------


@pytest.fixture(scope="module")
def edition():
    return charger_edition()


def test_edition_complete_et_sans_erreur(edition):
    controles = edition["controles"]
    assert edition["edition"] == "2021-12-16"
    # 7 cas de protection × 8 menuiseries × 3 vitrages ; 4 correctifs × 4 menuiseries.
    assert controles["comptes"] == {"fenetres": 168, "correctifs": 16, "portes": 11, "fermetures": 6, "ujn": 35, "uws": 18}
    assert controles["erreurs"] == []
    # Seule alerte : la coquille du document au §2.5.3, corrigée et signalée.
    assert len(controles["alertes"]) == 1 and "2.5.3" in controles["alertes"][0]
    assert all(l["statut"] != "erreur" for l in edition["fenetres"])


def test_valeurs_lues_dans_les_documents(edition):
    fenetre = {l["id"]: l for l in edition["fenetres"]}
    assert fenetre["2.1.1-triple"]["u"] == 2.0 and fenetre["2.1.1-triple"]["s_c"][0] == 0.32
    assert fenetre["2.1.1-double_controle_solaire"]["tl"] == 0.38
    assert fenetre["2.2.1-triple"]["u"] == 1.5  # Uws avec protection opaque claire extérieure
    corrigee = fenetre["2.5.3-triple"]
    assert corrigee["u"] == 1.8 and corrigee["statut"] == "alerte"
    assert corrigee["u"] <= fenetre["2.5.3-double"]["u"] and corrigee["u"] <= fenetre["2.1.3-triple"]["u"]
    portes = {p["id"]: p["ud"] for p in edition["portes"]}
    assert portes["bois_opaque_pleine"] == 3.5 and portes["metal_vitrage_double_30_60"] == 4.8
    fermetures = {f["id"]: f["r"] for f in edition["fermetures"]}
    assert fermetures["sans_ajours_volet_roulant_alu"] == 0.15 and fermetures["volet_roulant_pvc_epais"] == 0.25
    correctif_ete = edition["correctifs"][0]
    assert correctif_ete["code"] == "cs_ete" and correctif_ete["lignes"][0]["valeurs"][:2] == [0.56, 0.43]


def test_interpolation_ujour_nuit_et_uws(edition):
    assert calcul_fermeture(2.0, 0.14, edition)["ujn"] == 1.8
    resultat = calcul_fermeture(2.05, 0.14, edition)
    assert resultat["ujn"] == pytest.approx(1.85) and resultat["uws"] == pytest.approx(1.6)
    au_dela = calcul_fermeture(3.5, 0.14, edition)  # le tableau Uws s'arrête à 2,9
    assert au_dela["uws"] is None and "hors du tableau Uws" in au_dela["remarque"]
    with pytest.raises(ValueError, match="hors du tableau"):
        interpoler(edition["ujn"], 7.0, 0.14, "Ujour-nuit")


def test_les_controles_detectent_une_valeur_fausse(edition):
    faussee = copy.deepcopy(edition)
    lignes = {l["id"]: l for l in faussee["fenetres"]}
    lignes["2.1.1-triple"]["u"] = 9.9  # hors plage
    lignes["2.1.2-triple"]["u"] = 5.0  # triple moins bon que double
    erreurs, alertes = controler(faussee)
    assert any("2.1.1" in e and "hors de la plage" in e for e in erreurs)
    assert lignes["2.1.1-triple"]["statut"] == "erreur"
    assert any("2.1.2" in a and "triple" in a for a in alertes)
