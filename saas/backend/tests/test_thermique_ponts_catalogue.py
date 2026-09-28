"""Catalogue des ponts types de la NF EN ISO 14683 (tableau C.2), transcrit à la main : il doit rester entier."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

CATALOGUE = Path(__file__).resolve().parents[1] / "app" / "data" / "thermique_ponts_iso14683.json"


def _catalogue() -> dict:
    return json.loads(CATALOGUE.read_text(encoding="utf-8"))


def test_le_tableau_c2_est_complet_famille_par_famille():
    ponts = _catalogue()["ponts"]
    assert len(ponts) == 76
    assert len({pont["code"] for pont in ponts}) == 76
    assert Counter(pont["famille"] for pont in ponts) == {
        "R": 12, "B": 4, "C": 8, "IF": 8, "IW": 6, "GF": 16, "P": 4, "W": 18,
    }


def test_chaque_valeur_est_sur_la_grille_de_0_05_de_la_norme():
    for pont in _catalogue()["ponts"]:
        for cle in ("psi_e", "psi_oi", "psi_i"):
            assert abs(round(pont[cle] / 0.05) * 0.05 - pont[cle]) < 1e-9, (pont["code"], cle)


def test_les_angles_de_l_outil_ont_leurs_quatre_ponts_types():
    angles = [pont for pont in _catalogue()["ponts"] if pont["famille"] == "C"]
    assert [p["code"] for p in angles if p["angle"] == "sortant"] == ["C1", "C2", "C3", "C4"]
    assert [p["code"] for p in angles if p["angle"] == "rentrant"] == ["C5", "C6", "C7", "C8"]
    # En dimensions intérieures, un angle rentrant fait gagner : ψi négatif, ce qui surprend à la lecture.
    assert all(p["psi_i"] < 0 for p in angles if p["angle"] == "rentrant")
