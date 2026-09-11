"""Construit une édition de la bibliothèque des menuiseries à partir des PDF Th-Bât.

Usage (depuis saas/backend) :
    python -m thermique_moteur.bibliotheque.build "<dossier REGLES TH BAT>" [sortie.json]

Le dossier doit contenir les applications du fascicule « parois vitrées » (archive officielle
décompressée) et le tableau officiel de suivi des mises à jour (suivi_maj_applications_th-bat.xlsx),
qui date l'édition.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

from pypdf import PdfReader

from . import menuiseries

SOURCES = {
    "fenetres": "USTL",
    "portes": "Ud de portes",
    "ujn": "Ujour nuit",
    "uws": "Uws de fen",
    "fermetures": "sistance additionnelle",
}


def _trouver(dossier: Path, motif: str, suffixe: str = ".pdf") -> Path:
    trouves = [p for p in dossier.rglob(f"*{suffixe}") if motif.lower() in p.name.lower()]
    if len(trouves) != 1:
        raise FileNotFoundError(f"{len(trouves)} fichier(s) « {motif} » dans {dossier} (un seul attendu).")
    return trouves[0]


def _pages(chemin: Path) -> list[tuple[int, str]]:
    lecteur = PdfReader(str(chemin))
    return [(i + 1, page.extract_text() or "") for i, page in enumerate(lecteur.pages)]


def _edition(dossier: Path) -> tuple[str, list[str]]:
    """Date de la dernière mise à jour officielle concernant les parois vitrées."""
    import openpyxl

    classeur = openpyxl.load_workbook(_trouver(dossier, "suivi_maj_applications", ".xlsx"), data_only=True)
    dates: list[dt.date] = []
    historique: list[str] = []
    for feuille in classeur.worksheets:
        for ligne in feuille.iter_rows(values_only=True):
            cellules = [c for c in ligne if c is not None]
            date = next((c for c in cellules if isinstance(c, (dt.date, dt.datetime))), None)
            texte = " ".join(str(c) for c in cellules if not isinstance(c, (dt.date, dt.datetime)))
            if date and "vitr" in texte.lower():
                jour = date.date() if isinstance(date, dt.datetime) else date
                dates.append(jour)
                historique.append(f"{jour.isoformat()} : {texte}")
    if not dates:
        raise ValueError("Aucune mise à jour « parois vitrées » dans le tableau de suivi.")
    return max(dates).isoformat(), historique


def construire(dossier: Path) -> dict:
    pages: dict[str, list[tuple[int, str]]] = {}
    sources: dict[str, dict] = {}
    for cle, motif in SOURCES.items():
        chemin = _trouver(dossier, motif)
        pages[cle] = _pages(chemin)
        sources[cle] = {
            "document": chemin.name,
            "sha256": hashlib.sha256(chemin.read_bytes()).hexdigest(),
            "pages": len(pages[cle]),
        }
    edition, historique = _edition(dossier)
    return menuiseries.assembler_edition(pages, sources, edition, historique, dt.date.today().isoformat())


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parseur.add_argument("dossier", type=Path)
    parseur.add_argument("sortie", type=Path, nargs="?")
    arguments = parseur.parse_args(argv)
    resultat = construire(arguments.dossier)
    sortie = arguments.sortie or menuiseries.DONNEES_DIR / f"menuiseries_{resultat['edition']}.json"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps(resultat, ensure_ascii=False, indent=1), encoding="utf-8")
    controles = resultat["controles"]
    print(f"Édition {resultat['edition']} écrite dans {sortie}")
    print("Comptes :", controles["comptes"])
    print(f"Erreurs : {len(controles['erreurs'])} · alertes : {len(controles['alertes'])}")
    for message in controles["erreurs"] + controles["alertes"]:
        print("  -", message)
    return 1 if controles["erreurs"] else 0


if __name__ == "__main__":
    sys.exit(main())
