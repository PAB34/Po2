"""Bibliothèque des matériaux (lot B2a) : conductivités utiles par défaut.

Les tableaux du fascicule « Matériaux » des règles Th-Bât (méthodes) sont lus d'après la
géométrie de la page : les cellules sont délimitées par les bordures des tableaux (pdfplumber),
si bien qu'une conductivité ne peut pas glisser sur la ligne voisine (décision B2-D1).
Contrôles automatiques : structure des tableaux, plages de valeurs par famille, valeurs
assorties d'une note du document signalées.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

DONNEES_DIR = Path(__file__).resolve().parent.parent / "donnees"

# Caractères de la police Symbol, placés dans la zone privée d'Unicode par le PDF.
SYMBOLES = {
    "": "ρ",
    "": "λ",
    "": "μ",
    "": "≤",
    "": "≥",
    "": "∞",
    "": "<",
    "": ">",
}
TITRE = re.compile(r"^(2\.\d+(?:\.\d+){0,2})$")
NOMBRE = re.compile(r"\d{1,3}(?: \d{3})+(?:,\d+)?|\d+(?:,\d+)?")
# Conductivité éventuellement suivie d'un appel de note du document : « 0,25* », « 1,3 (*) ».
CONDUCTIVITE = re.compile(r"^(\d{1,3}(?: \d{3})+(?:,\d+)?|\d+(?:,\d+)?)\s*(\(?\*+\)?|\(\d\))?$")
# Colonnes qu'une cellule fusionnée peut couvrir sur plusieurs lignes (jamais λ ni ρ).
COLONNES_FUSIONNABLES = ("cp", "mu_sec", "mu_humide")
COLONNES_VALEURS = ("rho", "lambda", "cp", "mu_sec", "mu_humide")

REGLES_USAGE = {
    "valeurs": (
        "Valeurs utiles par défaut, à retenir à défaut de valeur justifiée (certificat, Avis technique, "
        "valeur déclarée convertie selon le fascicule)."
    ),
    "masse_volumique_inconnue": (
        "Quand la masse volumique d'un matériau est inconnue, retenir la conductivité la plus élevée "
        "indiquée pour sa famille."
    ),
}


def propre(texte: str | None) -> str:
    texte = texte or ""
    for code, symbole in SYMBOLES.items():
        texte = texte.replace(code, symbole)
    return "\n".join(" ".join(ligne.split()) for ligne in texte.splitlines()).strip()


def _nombre(texte: str) -> float:
    return float(texte.replace(" ", "").replace(",", "."))


def conductivite(texte: str) -> tuple[float | None, str | None]:
    trouve = CONDUCTIVITE.match(texte.strip())
    if not trouve:
        return None, None
    return _nombre(trouve.group(1)), trouve.group(2)


def intervalle_masse_volumique(texte: str) -> tuple[float | None, float | None]:
    t = propre(texte).replace("kg/m3", "").replace("\n", " ")
    if not NOMBRE.search(t):
        return None, None
    if "ρ" not in t:
        nombres = [_nombre(n) for n in NOMBRE.findall(t)]
        return min(nombres), max(nombres)
    avant, _, apres = t.partition("ρ")
    n_avant, n_apres = NOMBRE.findall(avant), NOMBRE.findall(apres)
    minimum = _nombre(n_avant[-1]) if n_avant else None
    maximum = _nombre(n_apres[0]) if n_apres else None
    if not n_avant and n_apres and (">" in apres or "≥" in apres):  # « ρ > a »
        minimum, maximum = maximum, None
    return minimum, maximum


def _titres(page: Any) -> list[tuple[float, str, str]]:
    """Intitulés de paragraphes (« 2.6.2.1 Laines de roches ») avec leur ordonnée."""
    mots = page.extract_words(x_tolerance=1.5)
    lignes: list[list[dict]] = []
    for mot in sorted(mots, key=lambda m: (m["top"], m["x0"])):
        if lignes and abs(lignes[-1][0]["top"] - mot["top"]) <= 3:
            lignes[-1].append(mot)
        else:
            lignes.append([mot])
    titres = []
    for ligne in lignes:
        ligne.sort(key=lambda m: m["x0"])
        if TITRE.match(ligne[0]["text"]) and ligne[0]["x0"] < 110 and len(ligne) > 1:
            titres.append((ligne[0]["top"], ligne[0]["text"], propre(" ".join(m["text"] for m in ligne[1:]))))
    return titres


def _colonnes(entete: list[str], sous_entete: list[str]) -> dict[str, int]:
    colonnes: dict[str, int] = {"libelle": 0}
    for i, cellule in enumerate(entete):
        c = propre(cellule).replace("\n", " ")
        if "kg/m3" in c:
            colonnes["rho"] = i
        elif "W/(m.K" in c:
            colonnes["lambda"] = i
        elif "J/(" in c:
            colonnes["cp"] = i
    for i, cellule in enumerate(sous_entete):
        c = propre(cellule)
        if c == "Sec":
            colonnes["mu_sec"] = i
        elif c == "Humide":
            colonnes["mu_humide"] = i
    return colonnes


def _cellule(ligne: list[str | None], colonnes: dict[str, int], cle: str) -> str:
    i = colonnes.get(cle)
    return propre(ligne[i]) if i is not None and i < len(ligne) else ""


def _lignes_materiau(cellules: dict[str, str], section: str, numero: int, anomalies: list[str]) -> list[dict[str, str]]:
    """Une ligne de tableau peut regrouper plusieurs matériaux dans ses cellules (une valeur par
    ligne de texte). Le libellé, lui, n'est jamais découpé : c'est un seul texte replié sur
    plusieurs lignes, commun à toutes les valeurs (constaté pour les plâtres, §2.3.1)."""
    valeurs_lambda = [v for v in cellules["lambda"].split("\n") if v]
    n = len(valeurs_lambda)
    libelle = cellules["libelle"].replace("\n", " ")
    if n <= 1:
        return [{**{cle: texte.replace("\n", " ") for cle, texte in cellules.items()}, "libelle": libelle}]
    decoupe = {cle: [v for v in cellules[cle].split("\n") if v] for cle in COLONNES_VALEURS}
    incoherentes = {
        cle: len(v) for cle, v in decoupe.items() if v and len(v) != n and not (len(v) == 1 and cle in COLONNES_FUSIONNABLES)
    }
    if incoherentes:
        anomalies.append(f"§{section} p. {numero} : colonnes groupées de longueurs différentes de {n} : {incoherentes}")
        return []
    return [
        {"libelle": libelle, **{cle: (decoupe[cle][k] if len(decoupe[cle]) == n else cellules[cle]) for cle in COLONNES_VALEURS}}
        for k in range(n)
    ]


def extraire_materiaux(pdf: Any) -> tuple[list[dict], list[dict], list[dict], list[dict], list[str]]:
    """Retourne (matériaux, renvois sans valeur, sections, familles, anomalies)."""
    materiaux: list[dict] = []
    renvois: list[dict] = []
    sections: dict[str, dict] = {}
    familles: dict[str, str] = {}
    anomalies: list[str] = []
    section, titre, famille = None, "", None
    compteur: dict[str, int] = {}
    tableaux = 0
    for numero, page in enumerate(pdf.pages, start=1):
        evenements = [("titre", top, (ident, texte)) for top, ident, texte in _titres(page)]
        evenements += [("tableau", t.bbox[1], t) for t in page.find_tables()]
        for genre, _top, objet in sorted(evenements, key=lambda e: e[1]):
            if genre == "titre":
                section, titre = objet
                if section.count(".") == 1:
                    famille = section
                    familles[section] = titre
                sections.setdefault(section, {"section": section, "titre": titre, "famille": famille, "page": numero})
                continue
            lignes = objet.extract()
            if section is None or not lignes or not any("W/(m.K" in propre(c) for c in lignes[0]):
                continue  # avant le chapitre 2, ou tableau sans conductivité
            tableaux += 1
            colonnes = _colonnes(lignes[0], lignes[1] if len(lignes) > 1 else [])
            if "lambda" not in colonnes:
                anomalies.append(f"§{section} p. {numero} : colonne λ introuvable")
                continue
            debut_tableau = len(materiaux)
            note_tableau = ""
            for ligne in lignes[1:]:
                cellules = {cle: _cellule(ligne, colonnes, cle) for cle in ("libelle",) + COLONNES_VALEURS}
                if cellules["mu_sec"] == "Sec" or not any(cellules.values()):
                    continue  # sous-en-tête ou ligne vide
                if cellules["libelle"].startswith(("(*", "*")) and not any(cellules[c] for c in COLONNES_VALEURS):
                    note_tableau = cellules["libelle"].replace("\n", " ")  # note de bas de tableau
                    continue
                valeurs_lambda = [v for v in cellules["lambda"].split("\n") if v]
                if not any(conductivite(v)[0] is not None for v in valeurs_lambda):
                    if cellules["libelle"] or cellules["lambda"]:
                        renvois.append({"section": section, "texte": " ".join(v for v in cellules.values() if v).replace("\n", " "), "page": numero})
                    continue
                for valeurs in _lignes_materiau(cellules, section, numero, anomalies):
                    valeur, note = conductivite(valeurs["lambda"])
                    if valeur is None:
                        anomalies.append(f"§{section} p. {numero} : conductivité illisible « {valeurs['lambda']} »")
                        continue
                    compteur[section] = compteur.get(section, 0) + 1
                    rho_min, rho_max = intervalle_masse_volumique(valeurs["rho"])
                    materiau = {
                        "id": f"{section}-{compteur[section]}",
                        "section": section,
                        "section_titre": titre,
                        "famille": famille,
                        "libelle": valeurs["libelle"] or titre,
                        "rho_texte": valeurs["rho"],
                        "rho_min": rho_min,
                        "rho_max": rho_max,
                        "lambda": valeur,
                        "cp_texte": valeurs["cp"],
                        "mu_sec": valeurs["mu_sec"],
                        "mu_humide": valeurs["mu_humide"],
                        "page": numero,
                        "statut": "valide",
                    }
                    if note:
                        materiau["note_document"] = note
                    materiaux.append(materiau)
            if note_tableau:
                for materiau in materiaux[debut_tableau:]:
                    if materiau.get("note_document"):
                        materiau["note_texte"] = note_tableau
    anomalies_structure = [] if tableaux else ["Aucun tableau de conductivités reconnu."]
    return materiaux, renvois, list(sections.values()), [{"section": s, "titre": t} for s, t in familles.items()], anomalies_structure + anomalies


def controler(materiaux: list[dict]) -> tuple[list[str], list[str]]:
    erreurs: list[str] = []
    alertes: list[str] = []
    identifiants = [m["id"] for m in materiaux]
    if len(identifiants) != len(set(identifiants)):
        erreurs.append("Identifiants de matériaux en double.")
    for m in materiaux:
        source = f"§{m['section']} {m['libelle']} (p. {m['page']})"
        valeur = m["lambda"]
        if not 0.001 <= valeur <= 400:  # des gaz (krypton, xénon) aux métaux
            erreurs.append(f"{source} : λ = {valeur} hors de 0,001 à 400")
            m["statut"] = "erreur"
            continue
        if m["famille"] == "2.8":
            plausible = valeur >= 10
        elif m["famille"] == "2.6":
            plausible = valeur <= 0.12
        else:
            plausible = valeur <= 5
        if not plausible:
            alertes.append(f"{source} : λ = {valeur} inhabituel pour cette famille")
            m["statut"] = "alerte"
        if m.get("note_document"):
            texte = f" : « {m['note_texte']} »" if m.get("note_texte") else f", à lire à la page {m['page']}"
            alertes.append(f"{source} : valeur assortie d'une note du document ({m['note_document']}){texte}")
            m["statut"] = "alerte"
        for cle in ("mu_sec", "mu_humide"):
            if m[cle] and set(m[cle]) <= {"0"}:
                alertes.append(f"{source} : μ lu « {m[cle]} » (probablement ∞ dans le document, sans effet sur U)")
                break
        if m["rho_min"] is not None and m["rho_max"] is not None and m["rho_min"] > m["rho_max"]:
            erreurs.append(f"{source} : masse volumique mini supérieure à la maxi")
            m["statut"] = "erreur"
    return erreurs, alertes


def assembler_edition(pdf: Any, sources: dict, edition: str, extrait_le: str, verification: dict) -> dict[str, Any]:
    materiaux, renvois, sections, familles, anomalies = extraire_materiaux(pdf)
    erreurs, alertes = controler(materiaux)
    if not verification.get("ok"):
        erreurs.append("Constantes du calcul de paroi non retrouvées dans le fascicule méthodes : " + ", ".join(verification.get("manquants", [])))
    return {
        "bibliotheque": "materiaux",
        "regles": "Règles Th-Bât, fascicule Matériaux (méthodes)",
        "edition": edition,
        "extrait_le": extrait_le,
        "sources": sources,
        "regles_usage": REGLES_USAGE,
        "familles": familles,
        "sections": sections,
        "materiaux": materiaux,
        "renvois": renvois,
        "verification_constantes": verification,
        "controles": {
            "methode": "Contrôles automatiques : structure des tableaux, plages de conductivité par famille, recoupement des constantes de calcul.",
            "erreurs": anomalies + erreurs,
            "alertes": alertes,
            "comptes": {"materiaux": len(materiaux), "sections": len(sections), "renvois": len(renvois)},
        },
    }


@lru_cache(maxsize=1)
def charger_edition() -> dict[str, Any]:
    fichiers = sorted(DONNEES_DIR.glob("materiaux_*.json"))
    if not fichiers:
        raise FileNotFoundError("Aucune édition de la bibliothèque des matériaux.")
    return json.loads(fichiers[-1].read_text(encoding="utf-8"))


def index_materiaux() -> dict[str, dict]:
    """Matériaux utilisables dans un calcul (hors valeurs en erreur), par identifiant."""
    return {m["id"]: m for m in charger_edition()["materiaux"] if m["statut"] != "erreur"}
