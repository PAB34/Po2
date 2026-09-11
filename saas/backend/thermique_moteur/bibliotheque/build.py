"""Construit les éditions de la bibliothèque à partir des documents Th-Bât.

Usage (depuis saas/backend) :
    python -m thermique_moteur.bibliotheque.build "<dossier REGLES TH BAT>"

Le dossier doit contenir :
- les applications du fascicule « parois vitrées » (archive officielle décompressée) et le
  tableau officiel de suivi des mises à jour (suivi_maj_applications_th-bat.xlsx) ;
- les fascicules « méthodes » matériaux et parois opaques ;
- les applications du fascicule « parois opaques » (murs, planchers bas, toitures, cloisons).
Écrit `donnees/menuiseries_<édition>.json`, `donnees/materiaux_<édition>.json` et
`donnees/elements_<édition>.json`.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

from .. import parois
from . import elements, materiaux, menuiseries

SOURCES_MENUISERIES = {
    "fenetres": "USTL",
    "portes": "Ud de portes",
    "ujn": "Ujour nuit",
    "uws": "Uws de fen",
    "fermetures": "sistance additionnelle",
}
MOIS = {m: i for i, m in enumerate(
    ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"], start=1
)}


def _trouver(dossier: Path, motif: str, suffixe: str = ".pdf") -> Path:
    trouves = [p for p in dossier.rglob(f"*{suffixe}") if motif.lower() in p.name.lower()]
    if len(trouves) != 1:
        raise FileNotFoundError(f"{len(trouves)} fichier(s) « {motif} » dans {dossier} (un seul attendu).")
    return trouves[0]


def _pages(chemin: Path) -> list[tuple[int, str]]:
    lecteur = PdfReader(str(chemin))
    return [(i + 1, page.extract_text() or "") for i, page in enumerate(lecteur.pages)]


def _source(chemin: Path, pages: int) -> dict:
    return {"document": chemin.name, "sha256": hashlib.sha256(chemin.read_bytes()).hexdigest(), "pages": pages}


def _edition_suivi(dossier: Path, mot: str) -> tuple[str, list[str]]:
    """Date de la dernière mise à jour officielle d'un fascicule (tableau de suivi)."""
    import openpyxl

    classeur = openpyxl.load_workbook(_trouver(dossier, "suivi_maj_applications", ".xlsx"), data_only=True)
    dates: list[dt.date] = []
    historique: list[str] = []
    for feuille in classeur.worksheets:
        for ligne in feuille.iter_rows(values_only=True):
            cellules = [c for c in ligne if c is not None]
            date = next((c for c in cellules if isinstance(c, (dt.date, dt.datetime))), None)
            texte = " ".join(str(c) for c in cellules if not isinstance(c, (dt.date, dt.datetime)))
            if date and mot in texte.lower():
                jour = date.date() if isinstance(date, dt.datetime) else date
                dates.append(jour)
                historique.append(f"{jour.isoformat()} : {texte}")
    if not dates:
        raise ValueError(f"Aucune mise à jour « {mot} » dans le tableau de suivi.")
    return max(dates).isoformat(), historique


def _date_publication(*chemins: Path) -> str:
    """« Publié le 20 décembre 2017 » en tête des fascicules méthodes."""
    for chemin in chemins:
        for _, texte in _pages(chemin)[:5]:
            trouve = re.search(r"Publi[ée] le (\d{1,2}) ([a-zéû]+) (\d{4})", texte)
            if trouve and trouve.group(2) in MOIS:
                return dt.date(int(trouve.group(3)), MOIS[trouve.group(2)], int(trouve.group(1))).isoformat()
    raise ValueError("Date de publication des fascicules méthodes introuvable.")


def verifier_constantes(chemin_parois_opaques: Path) -> dict:
    """Recoupe les constantes de `parois.py` avec le texte du fascicule méthodes (B2-D3)."""
    texte = " ".join(t for _, t in _pages(chemin_parois_opaques))
    texte = " ".join(texte.replace("’", "'").split())
    virgule = lambda v: f"{v:.2f}".replace(".", ",")  # noqa: E731
    attendus: list[str] = []
    for i, epaisseur in enumerate(parois.LAMES_AIR_MM):
        ligne = [parois.LAMES_AIR_R[f][i] for f in ("ascendant", "horizontal", "descendant")]
        attendus.append(f"{epaisseur} " + " ".join(virgule(v) for v in ligne))
    mur = parois.RESISTANCES_SUPERFICIELLES["mur"]
    attendus.append(f"{virgule(mur['rsi'])} {virgule(mur['rse'])} {virgule(mur['rsi'] + mur['rse'])}")
    haut, bas = parois.RESISTANCES_SUPERFICIELLES["plancher_haut"], parois.RESISTANCES_SUPERFICIELLES["plancher_bas"]
    attendus.append(
        f"{virgule(haut['rsi'])} {virgule(bas['rsi'])} {virgule(haut['rse'])} {virgule(bas['rse'])} "
        f"{virgule(haut['rsi'] + haut['rse'])} {virgule(bas['rsi'] + bas['rse'])}"
    )
    for niveau, suite in ((1, "paroi"), (2, "paroi"), (3, "isolation")):
        attendus.append(f"{suite} {virgule(parois.NIVEAUX_DELTA_U2[niveau]['valeur'])}")
    manquants = [a for a in attendus if a not in texte]
    return {"ok": not manquants, "controles": len(attendus), "manquants": manquants, "document": chemin_parois_opaques.name}


def construire_menuiseries(dossier: Path) -> dict:
    pages: dict[str, list[tuple[int, str]]] = {}
    sources: dict[str, dict] = {}
    for cle, motif in SOURCES_MENUISERIES.items():
        chemin = _trouver(dossier, motif)
        pages[cle] = _pages(chemin)
        sources[cle] = _source(chemin, len(pages[cle]))
    edition, historique = _edition_suivi(dossier, "vitr")
    return menuiseries.assembler_edition(pages, sources, edition, historique, dt.date.today().isoformat())


def construire_materiaux(dossier: Path) -> dict:
    import pdfplumber

    chemin_materiaux = _trouver(dossier, "fascicule_materiaux")
    chemin_parois = _trouver(dossier, "fascicule_parois_opaques_methodes")
    verification = verifier_constantes(chemin_parois)
    with pdfplumber.open(str(chemin_materiaux)) as pdf:
        sources = {
            "materiaux": _source(chemin_materiaux, len(pdf.pages)),
            "parois_opaques_methodes": _source(chemin_parois, len(PdfReader(str(chemin_parois)).pages)),
        }
        edition = _date_publication(chemin_materiaux, *[p for p in dossier.rglob("*generalites*.pdf")])
        return materiaux.assembler_edition(pdf, sources, edition, dt.date.today().isoformat(), verification)


def construire_elements(dossier: Path) -> dict:
    import pdfplumber

    pdfs: dict = {}
    sources: dict[str, dict] = {}
    try:
        for cle, fascicule in elements.FASCICULES.items():
            chemin = _trouver(dossier, fascicule["document"])
            pdfs[cle] = pdfplumber.open(str(chemin))
            sources[cle] = _source(chemin, len(pdfs[cle].pages))
        edition, historique = _edition_suivi(dossier, "opaques")
        resultat = elements.assembler_edition(pdfs, sources, edition, dt.date.today().isoformat())
        resultat["historique"] = historique
        return resultat
    finally:
        for pdf in pdfs.values():
            pdf.close()


def _ecrire(resultat: dict, prefixe: str) -> int:
    sortie = menuiseries.DONNEES_DIR / f"{prefixe}_{resultat['edition']}.json"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps(resultat, ensure_ascii=False, indent=1), encoding="utf-8")
    controles = resultat["controles"]
    print(f"\n{prefixe} : édition {resultat['edition']} écrite dans {sortie}")
    print("Comptes :", controles["comptes"])
    print(f"Erreurs : {len(controles['erreurs'])} · alertes : {len(controles['alertes'])}")
    for message in controles["erreurs"] + controles["alertes"]:
        print("  -", message)
    return len(controles["erreurs"])


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parseur.add_argument("dossier", type=Path)
    parseur.add_argument("--lot", choices=("tout", "menuiseries", "materiaux", "elements"), default="tout")
    arguments = parseur.parse_args(argv)
    erreurs = 0
    if arguments.lot in ("tout", "menuiseries"):
        erreurs += _ecrire(construire_menuiseries(arguments.dossier), "menuiseries")
    if arguments.lot in ("tout", "materiaux"):
        erreurs += _ecrire(construire_materiaux(arguments.dossier), "materiaux")
    if arguments.lot in ("tout", "elements"):
        erreurs += _ecrire(construire_elements(arguments.dossier), "elements")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
