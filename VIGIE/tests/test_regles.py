"""Garde-fous de la matrice PLU (étape É1) : lancer `python -m pytest tests` depuis VIGIE/."""
import json
from pathlib import Path

from pipeline.build_regles import construire

DATA = Path(__file__).resolve().parents[1] / "web" / "data"


def test_xml_et_excel_concordent():
    matrice = construire()
    assert matrice["controle"]["ecarts_xml_excel"] == []
    assert matrice["controle"]["secteurs_sans_excel"] == []


def test_chaque_secteur_a_une_famille_et_des_taux_coherents():
    for code, s in construire()["secteurs"].items():
        assert s["famille"] != "non_classe", code
        taux = s["emprise"]["taux"]
        assert (taux is None) != s["emprise"]["calculable"], code
        if taux is not None:
            assert 0 < taux <= 1, code
        if code.endswith("v"):
            assert s["famille"] == "protege", code


def test_valeurs_de_reference_du_cadrage():
    s = construire()["secteurs"]
    attendus = {"UD1": 0.11, "UD1a": 0.20, "UD2": 0.20, "UD3": 0.30, "UD4": 0.50, "UD1v": 0.08,
                "UD2v": 0.10, "UC3": 0.85, "UC4a": 0.50, "UC4d": 0.75, "3UB1": 0.75, "3UB4": 0.50}
    for code, taux in attendus.items():
        assert s[code]["emprise"]["taux"] == taux, code
    assert s["3UB7"]["emprise"]["calculable"] is False  # formule bande de 16 m


def test_regles_publiees_a_jour():
    """web/data/regles.json doit être régénéré après toute modification des sources."""
    publie = json.loads((DATA / "regles.json").read_text(encoding="utf-8"))
    assert publie["secteurs"] == json.loads(json.dumps(construire()["secteurs"]))
