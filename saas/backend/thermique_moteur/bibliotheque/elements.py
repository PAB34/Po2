"""Bibliothèque des éléments à résistance tabulée (lot B2b-1).

Résistances thermiques R des fascicules « applications » des règles Th-Bât (parois opaques) :
briques et blocs, béton cellulaire, planchers à entrevous et dalles alvéolées, isolants en vrac,
cloisons. Les tableaux en texte sont lus dans la grille du PDF d'après leurs descripteurs
(`elements_descripteurs.py`, décision B2b-D1) ; les tableaux imprimés en image sont transcrits
(`elements_transcrits.py`, Q32). Une valeur tabulée devient une couche « élément » du calcul de
paroi (B2b-D2). Contrôles automatiques (B2b-D4) : nombre de valeurs par tableau, plages,
monotonie, recoupement des notes avec le texte des pages.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from .elements_descripteurs import DESCRIPTEURS
from .elements_transcrits import TRANSCRITS
from .materiaux import DONNEES_DIR, propre

FASCICULES: dict[str, dict[str, str]] = {
    "murs": {"document": "Murs.pdf", "libelle": "Murs"},
    "planchers": {"document": "Planchers bas_EXT_LNC.pdf", "libelle": "Planchers bas sur extérieur ou local non chauffé"},
    "toitures": {"document": "Toitures_rampants_plafonds.pdf", "libelle": "Toitures, rampants et plafonds"},
    "cloisons": {"document": "Cloisons.pdf", "libelle": "Cloisons"},
}
FAMILLES = [
    {"id": "terre_cuite", "libelle": "Briques et blocs de terre cuite"},
    {"id": "beton", "libelle": "Blocs en béton"},
    {"id": "beton_cellulaire", "libelle": "Béton cellulaire"},
    {"id": "plancher_entrevous", "libelle": "Planchers à entrevous"},
    {"id": "plancher_beton", "libelle": "Dalles alvéolées"},
    {"id": "isolant_vrac", "libelle": "Isolants en vrac et projetés"},
    {"id": "cloison", "libelle": "Cloisons et contre-murs"},
]
REGLES_USAGE = {
    "valeurs": (
        "Valeurs par défaut des règles Th-Bât : les valeurs des Avis Techniques, DTA et certificats "
        "(CSTBât, NF…) priment sur elles."
    ),
    "interpolation": (
        "Pas d'interpolation entre les cases, sauf quand le document l'autorise (signalé sur le tableau) : "
        "sinon, saisir la résistance à la main."
    ),
    "variantes": "Valeur entre parenthèses dans le document : variante du même élément (joint rempli de mortier, application parasismique).",
}
R_MIN, R_MAX = 0.01, 12.0
VALEUR = re.compile(r"^(\d+(?:[,.]\d+)?)\s*(?:\(\s*(\d+(?:[,.]\d+)?)\s*\))?\s*(\(?\*\)?)?$")
SANS_VALEUR = {"", "-", "–", "—"}
PARENTHESES = "parentheses"
SENS = {"croissant": "croissante", "decroissant": "décroissante"}


class LectureError(ValueError):
    """Tableau ou cellule illisible : message du rapport de construction."""


def lire_valeur(texte: str | None) -> tuple[float | None, float | None]:
    """« 0,51 (0,47) » → (0.51, 0.47) ; « – » ou case vide → (None, None)."""
    t = " ".join((texte or "").split())
    if t in SANS_VALEUR:
        return None, None
    trouve = VALEUR.match(t)
    if not trouve:
        raise LectureError(f"valeur illisible « {t} »")
    variante = trouve.group(2)
    return float(trouve.group(1).replace(",", ".")), float(variante.replace(",", ".")) if variante else None


def premier_nombre(texte: str | None) -> float | None:
    trouve = re.search(r"\d+(?:,\d+)?", texte or "")
    return float(trouve.group(0).replace(",", ".")) if trouve else None


def lignes_cellule(texte: str | None) -> list[str]:
    """Lignes d'une cellule ; un indice isolé (« o » de lo) est rattaché à la ligne précédente."""
    lignes: list[str] = []
    for ligne in propre(texte).split("\n"):
        ligne = ligne.strip()
        if not ligne:
            continue
        if re.fullmatch(r"[a-zA-Z]", ligne) and lignes:
            lignes[-1] = re.sub(r"(?<![A-Za-z])l(?![A-Za-z])", "l" + ligne, lignes[-1], count=1)
            continue
        lignes.append(re.sub(r"(?<![A-Za-z])l ([oe])(?![A-Za-z])", r"l\1", ligne))
    return lignes


def normaliser(texte: str) -> str:
    return " ".join(propre(texte).replace("’", "'").split())


def reference(tableau: dict) -> str:
    numero = f"T{tableau['numero']}" if tableau.get("numero") else "figure"
    return f"{FASCICULES[tableau['fascicule']]['libelle']} {numero} p. {tableau['page']}"


def identifiant(descripteur: dict) -> str:
    return descripteur.get("id") or f"{descripteur['fascicule']}-T{descripteur['numero']}"


# --- Lecture des tableaux en texte -------------------------------------------------------------


def _trouver_tableau(page: Any, numero: int) -> Any:
    """Le tableau dont la bande de 45 pt au-dessus porte « Tableau N »."""
    motif = re.compile(rf"T\s?a\s?bleau\s*{numero}(?!\d)")
    candidats = []
    for table in page.find_tables():
        haut = table.bbox[1]
        bande = page.crop((0, max(0, haut - 45), page.width, haut)).extract_text() or ""
        if len(table.rows) >= 2 and motif.search(bande):
            candidats.append(table)
    if len(candidats) != 1:
        raise LectureError(f"{len(candidats)} grille(s) sous « Tableau {numero} » au lieu d'une")
    return candidats[0]


def _colonnes(grille: list[list], descripteur: dict) -> list[str]:
    if descripteur.get("colonnes"):
        return list(descripteur["colonnes"])
    debut = descripteur["debut"]
    niveaux = []
    for rang in descripteur.get("niveaux", [descripteur["entete"] - 1]):
        remplies, dernier = [], ""
        for cellule in grille[rang][debut:]:
            dernier = " ".join(lignes_cellule(cellule)) or dernier  # cellule fusionnée sur plusieurs colonnes
            remplies.append(dernier)
        niveaux.append(remplies)
    return [descripteur.get("format_colonne", "{0}").format(*parties) for parties in zip(*niveaux)]


def lire_tableau_texte(page: Any, descripteur: dict) -> tuple[list[str], list[dict], list[str], list[str]]:
    """Colonnes, lignes, remarques lues et anomalies d'un tableau décrit par son descripteur."""
    table = _trouver_tableau(page, descripteur["numero"])
    grille = [list(ligne) for ligne in table.extract()]
    boites = [rangee.bbox for rangee in table.rows]
    if descripteur.get("transposer"):
        grille = [list(colonne) for colonne in zip(*grille)]
        boites = [None] * len(grille)
    largeur = max(len(ligne) for ligne in grille)
    grille = [ligne + [None] * (largeur - len(ligne)) for ligne in grille]
    colonnes = _colonnes(grille, descripteur)
    debut, n_colonnes = descripteur["debut"], len(colonnes)
    cles_colonnes: dict[int, str] = descripteur["cles"]
    premiere_cle = min(cles_colonnes)
    diviser = descripteur.get("diviser_selon") or list(range(debut, debut + n_colonnes))
    noms = descripteur.get("noms_lignes") or []

    lignes: list[dict] = []
    remarques: list[str] = []
    anomalies: list[str] = []
    precedent: dict[str, str] = {}
    groupe: str | None = None
    rang_donnee = 0
    for rang in range(descripteur["entete"], len(grille)):
        cellules = grille[rang]
        valeurs_brutes = cellules[debut:debut + n_colonnes]
        if descripteur.get("groupes") and propre(cellules[0]) and not any(propre(c) for c in cellules[1:]):
            groupe = " ".join(lignes_cellule(cellules[0]))
            continue
        if not any(propre(c) for c in valeurs_brutes):
            texte = " ".join(lignes_cellule(cellules[0]))
            if len(texte) > 20:  # note sous le tableau
                remarques.append(texte)
            continue
        k = max((len(lignes_cellule(cellules[j])) for j in diviser), default=1) or 1

        def morceau(cellule: str | None, s: int) -> str:
            parties = lignes_cellule(cellule)
            return parties[s] if len(parties) == k else " ".join(parties)

        nom = None
        if noms:
            if rang_donnee >= len(noms):
                anomalies.append(f"ligne {rang + 1} en trop par rapport aux libellés des schémas")
            else:
                nom = noms[rang_donnee]
        rang_donnee += 1
        gauche = None
        if descripteur.get("colonne_gauche") and boites[rang]:
            _, haut, _, bas = boites[rang]
            gauche = " ".join((page.crop((0, haut, table.bbox[0], bas)).extract_text() or "").split())

        for s in range(k):
            cles: dict[str, str] = {}
            if descripteur.get("colonne_gauche"):
                cles[descripteur["colonne_gauche"]] = gauche or precedent.get(descripteur["colonne_gauche"], "")
            if groupe:
                cles[descripteur["groupes"]] = groupe
            for j, nom_cle in cles_colonnes.items():
                texte = nom if (nom is not None and j == premiere_cle) else morceau(cellules[j], s)
                cles[nom_cle] = texte or precedent.get(nom_cle, "")  # cellule fusionnée sur plusieurs lignes
            precedent.update(cles)
            corrections = []
            for cle, lu, corrige, message in descripteur.get("corrections", []):
                if cles.get(cle) == lu:
                    cles[cle] = corrige
                    corrections.append(message)
            for nom_cle, calcul in descripteur.get("cles_calculees", {}).items():
                cles[nom_cle] = calcul(cles)
            valeurs, variantes = [], []
            for j in range(n_colonnes):
                try:
                    valeur, variante = lire_valeur(morceau(valeurs_brutes[j], s))
                except LectureError as exc:
                    anomalies.append(f"ligne {rang + 1}, colonne « {colonnes[j]} » : {exc}")
                    valeur = variante = None
                valeurs.append(valeur)
                variantes.append(variante)
            libelle = descripteur["libelle"](cles) if descripteur.get("libelle") else " · ".join(v for v in cles.values() if v)
            ligne = {"libelle": libelle, "cles": cles, "valeurs": valeurs, "variantes": {}}
            if any(v is not None for v in variantes):
                ligne["variantes"][PARENTHESES] = variantes
            if corrections:
                ligne["corrections"] = corrections
            lignes.append(ligne)
    if noms and rang_donnee != len(noms):
        anomalies.append(f"{rang_donnee} lignes de valeurs pour {len(noms)} libellés de schémas")
    return colonnes, lignes, remarques, anomalies


def lire_tableau_transcrit(descripteur: dict) -> tuple[list[dict], list[str]]:
    anomalies: list[str] = []
    noms_cles = descripteur.get("cles") or []
    lignes: list[dict] = []
    for entree in descripteur["lignes"]:
        libelle, cellules = entree[0], entree[1]
        if len(cellules) != len(descripteur["colonnes"]):
            anomalies.append(f"« {libelle} » : {len(cellules)} cellules pour {len(descripteur['colonnes'])} colonnes")
            continue
        cles = dict(zip(noms_cles, entree[2])) if noms_cles else {descripteur["axe_lignes"]: libelle}
        valeurs, variantes = [], []
        for cellule in cellules:
            try:
                valeur, variante = lire_valeur(cellule)
            except LectureError as exc:
                anomalies.append(f"« {libelle} » : {exc}")
                valeur = variante = None
            valeurs.append(valeur)
            variantes.append(variante)
        ligne = {"libelle": libelle, "cles": cles, "valeurs": valeurs, "variantes": {}}
        if any(v is not None for v in variantes):
            ligne["variantes"][PARENTHESES] = variantes
        lignes.append(ligne)
    return lignes, anomalies


# --- Contrôles automatiques (B2b-D4) ------------------------------------------------------------


def _fmt(valeur: float) -> str:
    return f"{valeur:g}".replace(".", ",")


def controler_monotonie(tableau: dict, regles: dict) -> list[tuple[int, int | None, str]]:
    """Cellules qui contredisent le sens de variation attendu : (ligne, colonne, message)."""
    lignes, colonnes = tableau["lignes"], tableau["colonnes"]
    constats: list[tuple[int, int | None, str]] = []
    respecte = lambda a, b, sens: b >= a if sens == "croissant" else b <= a  # noqa: E731

    def comparer(i1: int, i2: int, j1: int, j2: int, sens: str, sur: str) -> None:
        a, b = lignes[i1]["valeurs"][j1], lignes[i2]["valeurs"][j2]
        if a is None or b is None or respecte(a, b, sens):
            return
        message = (
            f"{lignes[i2]['libelle']} ({colonnes[j2]}) : {_fmt(b)} après {_fmt(a)} "
            f"({lignes[i1]['libelle']}, {colonnes[j1]}), R devrait être {SENS[sens]} selon {sur[:1].lower()}{sur[1:]}"
        )
        constats.extend([(i1, j1, message), (i2, j2, message)])

    if regles.get("colonnes"):
        pas = regles.get("pas", 1)
        for i in range(len(lignes)):
            for j in range(len(colonnes) - pas):
                comparer(i, i, j, j + pas, regles["colonnes"], tableau["axe_colonnes"])
    if regles.get("lignes"):
        for i in range(len(lignes) - 1):
            for j in range(len(colonnes)):
                comparer(i, i + 1, j, j, regles["lignes"], tableau["axe_lignes"])
    for cle, sens in regles.get("lignes_cles", []):
        groupes: dict[tuple, list[int]] = {}
        for i, ligne in enumerate(lignes):
            autres = tuple((k, v) for k, v in ligne["cles"].items() if k != cle)
            groupes.setdefault(autres, []).append(i)
        for rangs in groupes.values():
            for i1, i2 in zip(rangs, rangs[1:]):
                for j in range(len(colonnes)):
                    comparer(i1, i2, j, j, sens, cle)
    if regles.get("epaisseur"):
        cle = regles["epaisseur"]
        groupes = {}
        for i, ligne in enumerate(lignes):
            groupes.setdefault(tuple(ligne["cles"].get(g) for g in regles.get("groupes", [])), []).append(i)
        for rangs in groupes.values():
            rangs = sorted(rangs, key=lambda i: premier_nombre(lignes[i]["cles"].get(cle)) or 0)
            for i1, i2 in zip(rangs, rangs[1:]):
                e1, e2 = (premier_nombre(lignes[i]["cles"].get(cle)) for i in (i1, i2))
                if e1 is not None and e2 is not None and e2 > e1:
                    comparer(i1, i2, 0, 0, "croissant", "l'épaisseur")
    return constats


def controler(tableaux: list[dict], attendus: dict[str, int], monotonies: dict[str, dict]) -> tuple[list[str], list[str]]:
    erreurs: list[str] = []
    alertes: list[str] = []
    identifiants = [t["id"] for t in tableaux]
    if len(identifiants) != len(set(identifiants)):
        erreurs.append("Identifiants de tableaux en double.")
    for tableau in tableaux:
        ref = reference(tableau)
        n = sum(v is not None for ligne in tableau["lignes"] for v in ligne["valeurs"])
        tableau["nombre_valeurs"] = n
        attendu = attendus.get(tableau["id"])
        if attendu is not None and n != attendu:
            erreurs.append(f"{ref} : {n} valeurs lues pour {attendu} attendues")
            tableau["statut"] = "erreur"
        for i, ligne in enumerate(tableau["lignes"]):
            for j, valeur in enumerate(ligne["valeurs"]):
                if valeur is not None and not R_MIN <= valeur <= R_MAX:
                    erreurs.append(f"{ref} : {ligne['libelle']} ({tableau['colonnes'][j]}) R = {_fmt(valeur)} hors de 0,01 à 12")
                    tableau["statut"] = "erreur"
                variante = ligne["variantes"].get(PARENTHESES, [None] * (j + 1))[j]
                if valeur is not None and variante is not None and variante > valeur:
                    message = f"{ligne['libelle']} ({tableau['colonnes'][j]}) : variante {_fmt(variante)} supérieure à la valeur {_fmt(valeur)}"
                    alertes.append(f"{ref} : {message}")
                    tableau["signalements"].append({"ligne": i, "colonne": j, "message": message})
            for message in ligne.get("corrections", []):
                alertes.append(f"{ref} : {message}")
                tableau["signalements"].append({"ligne": i, "colonne": None, "message": f"Correction : {message}"})
        vus = set()
        for i, j, message in controler_monotonie(tableau, monotonies.get(tableau["id"]) or {}):
            tableau["signalements"].append({"ligne": i, "colonne": j, "message": f"Valeur à vérifier : {message}"})
            if message not in vus:
                vus.add(message)
                alertes.append(f"{ref} : {message}")
        if tableau["signalements"] and tableau["statut"] == "valide":
            tableau["statut"] = "alerte"
    return erreurs, alertes


# --- Édition --------------------------------------------------------------------------------------


def _tableau(descripteur: dict, colonnes: list[str], lignes: list[dict], lecture: str, remarques: list[str]) -> dict:
    variantes = {PARENTHESES: descripteur.get("variante") or "Valeur entre parenthèses du document"} if any(
        PARENTHESES in ligne["variantes"] for ligne in lignes
    ) else {}
    return {
        "id": identifiant(descripteur),
        "fascicule": descripteur["fascicule"],
        "numero": descripteur["numero"],
        "page": descripteur["page"],
        "section": descripteur["section"],
        "titre": descripteur["titre"],
        "famille": descripteur["famille"],
        "isolant": bool(descripteur.get("isolant")),
        "lecture": lecture,
        "axe_lignes": descripteur["axe_lignes"],
        "axe_colonnes": descripteur["axe_colonnes"],
        "colonnes": colonnes,
        "variantes": variantes,
        "lignes": lignes,
        "remarques": list(descripteur.get("remarques", [])) + remarques,
        "signalements": [],
        "statut": "valide",
    }


def assembler_edition(pdfs: dict[str, Any], sources: dict, edition: str, extrait_le: str) -> dict[str, Any]:
    """`pdfs` : fascicule → document pdfplumber ouvert."""
    textes: dict[tuple[str, int], str] = {}

    def texte_page(fascicule: str, page: int) -> str:
        if (fascicule, page) not in textes:
            textes[(fascicule, page)] = normaliser(pdfs[fascicule].pages[page - 1].extract_text() or "")
        return textes[(fascicule, page)]

    tableaux: list[dict] = []
    erreurs: list[str] = []
    for descripteur in DESCRIPTEURS:
        ref = reference(descripteur)
        try:
            colonnes, lignes, remarques, anomalies = lire_tableau_texte(pdfs[descripteur["fascicule"]].pages[descripteur["page"] - 1], descripteur)
        except LectureError as exc:
            erreurs.append(f"{ref} : {exc}")
            continue
        erreurs.extend(f"{ref} : {a}" for a in anomalies)
        tableau = _tableau(descripteur, colonnes, lignes, "texte", remarques)
        for nom, calcul in descripteur.get("variantes_calculees", {}).items():
            if normaliser(calcul["verifier"]) not in texte_page(descripteur["fascicule"], calcul["page"]):
                erreurs.append(f"{ref} : règle « {calcul['verifier']} » introuvable p. {calcul['page']}")
                continue
            tableau["variantes"][nom] = calcul["libelle"]
            for ligne in tableau["lignes"]:
                ligne["variantes"][nom] = [None if v is None else round(v + calcul["ajout"], 3) for v in ligne["valeurs"]]
        tableaux.append(tableau)
    for descripteur in TRANSCRITS:
        ref = reference(descripteur)
        lignes, anomalies = lire_tableau_transcrit(descripteur)
        erreurs.extend(f"{ref} : {a}" for a in anomalies)
        for attendu in descripteur.get("verifier_texte", []):
            if normaliser(attendu) not in texte_page(descripteur["fascicule"], descripteur["page"]):
                erreurs.append(f"{ref} : texte « {attendu} » introuvable sur la page")
        lecture = descripteur.get("lecture", "image")
        tableaux.append(_tableau(descripteur, list(descripteur["colonnes"]), lignes, lecture, []))

    ordre = list(FASCICULES)
    tableaux.sort(key=lambda t: (ordre.index(t["fascicule"]), t["page"], t["numero"] or 0))
    attendus = {identifiant(d): d["attendu"] for d in DESCRIPTEURS if "attendu" in d}
    monotonies = {identifiant(d): d.get("monotonie") or {} for d in (*DESCRIPTEURS, *TRANSCRITS)}
    erreurs_controles, alertes = controler(tableaux, attendus, monotonies)
    return {
        "bibliotheque": "elements",
        "regles": "Règles Th-Bât, fascicules « applications » parois opaques",
        "edition": edition,
        "extrait_le": extrait_le,
        "sources": sources,
        "regles_usage": REGLES_USAGE,
        "fascicules": {cle: valeur["libelle"] for cle, valeur in FASCICULES.items()},
        "familles": FAMILLES,
        "tableaux": tableaux,
        "controles": {
            "methode": (
                "Contrôles automatiques : nombre de valeurs par tableau, plages de R, sens de variation "
                "(épaisseur, entraxe, masse volumique…), recoupement des notes transcrites avec le texte des pages."
            ),
            "erreurs": erreurs + erreurs_controles,
            "alertes": alertes,
            "comptes": {
                "tableaux": len(tableaux),
                "tableaux_image": sum(t["lecture"] == "image" for t in tableaux),
                "valeurs": sum(t["nombre_valeurs"] for t in tableaux),
            },
        },
    }


@lru_cache(maxsize=1)
def charger_edition() -> dict[str, Any]:
    fichiers = sorted(DONNEES_DIR.glob("elements_*.json"))
    if not fichiers:
        raise FileNotFoundError("Aucune édition de la bibliothèque des éléments.")
    return json.loads(fichiers[-1].read_text(encoding="utf-8"))


def index_elements() -> dict[str, dict]:
    """Tableaux utilisables dans un calcul (hors tableaux en erreur), par identifiant."""
    return {t["id"]: t for t in charger_edition()["tableaux"] if t["statut"] != "erreur"}
