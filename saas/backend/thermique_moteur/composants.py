"""Composants de bibliothèque : catégories, codes et calcul (bibliothèque de projet, lot L1).

Un composant = une catégorie, une composition et un résultat recalculé. Le même format sert la
bibliothèque d'un projet et les modèles réutilisables d'un compte ; ce module ne dépend que du
moteur (aucun import `app.`). Voir docs/thermique/bibliotheque-projet-decisions.md.
- Parois opaques (murs, planchers, toitures) : calcul en couches de `parois.calculer_paroi`.
- Menuiseries et ponts thermiques : valeurs saisies en attendant le lot L3 (composition détaillée).
Une composition incomplète s'enregistre (brouillon) : son résultat est alors vide.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

from . import parois
from .bibliotheque.elements import premier_nombre

CATEGORIES: list[dict[str, Any]] = [
    {
        "id": "murs", "libelle": "Murs", "singulier": "mur", "nouveau": "Nouveau mur", "prefixe": "MUR", "nature": "paroi",
        "paroi": "mur", "donne_sur": "exterieur",
        "sous_categories": ["Mur extérieur", "Mur sur local non chauffé", "Mur enterré", "Refend ou cloison"],
    },
    {
        "id": "planchers_bas", "libelle": "Planchers bas", "singulier": "plancher bas", "nouveau": "Nouveau plancher bas", "prefixe": "PB", "nature": "paroi",
        "paroi": "plancher_bas", "donne_sur": "local_non_chauffe",
        "sous_categories": ["Sur vide sanitaire", "Sur local non chauffé", "Sur extérieur", "Sur terre-plein"],
    },
    {
        "id": "planchers_intermediaires", "libelle": "Planchers intermédiaires", "singulier": "plancher intermédiaire",
        "nouveau": "Nouveau plancher intermédiaire", "prefixe": "PI", "nature": "paroi", "paroi": "plancher_bas", "donne_sur": "local_non_chauffe",
        "sous_categories": ["Entre niveaux chauffés", "Sur local d'une autre zone"],
    },
    {
        "id": "planchers_hauts", "libelle": "Planchers hauts et toitures", "singulier": "plancher haut", "nouveau": "Nouveau plancher haut", "prefixe": "PH",
        "nature": "paroi", "paroi": "plancher_haut", "donne_sur": "exterieur",
        "sous_categories": ["Toiture terrasse", "Combles perdus", "Rampants", "Sous local non chauffé"],
    },
    {
        "id": "menuiseries", "libelle": "Menuiseries", "singulier": "menuiserie", "nouveau": "Nouvelle menuiserie", "prefixe": "F", "nature": "menuiserie",
        "sous_categories": ["Fenêtre", "Porte-fenêtre", "Porte", "Lanterneau"],
    },
    {
        "id": "ponts_thermiques", "libelle": "Ponts thermiques", "singulier": "pont thermique", "nouveau": "Nouveau pont thermique", "prefixe": "PT", "nature": "pont",
        "sous_categories": ["Plancher bas", "Plancher intermédiaire", "Plancher haut", "Refend", "Menuiserie", "Autre"],
    },
]
STATUTS = {"hypothese": "Hypothèse", "conforme_cctp": "Conforme CCTP"}
_PAR_ID = {c["id"]: c for c in CATEGORIES}


class ComposantError(ValueError):
    """Donnée de composant invalide ; le message est destiné à l'utilisateur."""


def categorie(identifiant: str | None) -> dict[str, Any]:
    if identifiant not in _PAR_ID:
        raise ComposantError(f"Catégorie inconnue : {identifiant}.")
    return _PAR_ID[identifiant]


def code_suivant(identifiant: str, codes: Iterable[str]) -> str:
    """« MUR 3 » si « MUR 1 » et « MUR 2 » existent déjà (les codes libres sont ignorés)."""
    prefixe = categorie(identifiant)["prefixe"]
    motif = re.compile(rf"{prefixe}\s*(\d+)", re.IGNORECASE)
    numeros = [int(m.group(1)) for code in codes if (m := motif.fullmatch((code or "").strip()))]
    return f"{prefixe} {max(numeros, default=0) + 1}"


def composition_par_defaut(identifiant: str) -> dict[str, Any]:
    cat = categorie(identifiant)
    if cat["nature"] == "paroi":
        return {"type": cat["paroi"], "donne_sur": cat["donne_sur"], "niveau_delta_u2": 1, "delta_u1": 0, "couches": []}
    if cat["nature"] == "menuiserie":
        return {"uw": None, "sw": None, "tlw": None}
    return {"psi": None}


def _nombre(composition: dict, cle: str, nom: str, minimum: float, maximum: float) -> float | None:
    valeur = composition.get(cle)
    if valeur is None or valeur == "":
        return None
    try:
        valeur = float(valeur)
    except (TypeError, ValueError):
        raise ComposantError(f"{nom} invalide.") from None
    if not minimum <= valeur <= maximum:
        raise ComposantError(f"{nom} doit être compris entre {minimum:g} et {maximum:g}.".replace(".", ","))
    return valeur


def _epaisseur_element(couche: dict, elements: dict[str, dict] | None) -> float | None:
    """Épaisseur d'un élément tabulé quand le tableau la donne (colonne ou clé « Épaisseur (cm) »)."""
    tableau = (elements or {}).get(couche.get("tableau_id"))
    if tableau is None:
        return None
    ligne = tableau["lignes"][int(couche.get("ligne", 0))]
    if "Épaisseur (cm)" in ligne["cles"]:
        valeur = premier_nombre(ligne["cles"]["Épaisseur (cm)"])
        return valeur / 100 if valeur else None
    axe = tableau["axe_colonnes"].lower()
    if "paisseur" in axe and "(cm)" in axe:
        valeur = premier_nombre(tableau["colonnes"][int(couche.get("colonne", 0))])
        return valeur / 100 if valeur else None
    return None


def _epaisseur(couches: list[dict], detail: dict, elements: dict[str, dict] | None) -> tuple[float, bool]:
    total, complete = 0.0, True
    for couche, ligne in zip(couches, detail["couches"]):
        if ligne.get("epaisseur_m") is not None:
            total += ligne["epaisseur_m"]
        elif ligne.get("epaisseur_mm") is not None:
            total += ligne["epaisseur_mm"] / 1000
        elif couche.get("type") == "element" and (e := _epaisseur_element(couche, elements)) is not None:
            total += e
        else:
            complete = False
    return round(total, 3), complete


def _resume(detail: dict) -> str:
    parties = []
    for ligne in detail["couches"]:
        if ligne.get("ignoree"):
            continue
        libelle = ligne.get("libelle") or {"lame_air": "Lame d'air", "lame_air_ventilee": "Lame d'air ventilée", "resistance": "Élément"}.get(ligne["type"], "Couche")
        if ligne["type"] == "element":
            libelle = libelle.split(" : ", 1)[-1]
        libelle = libelle if len(libelle) <= 34 else libelle[:33] + "…"
        if ligne.get("epaisseur_m") is not None:
            libelle += f" {ligne['epaisseur_m'] * 100:g} cm".replace(".", ",")
        elif ligne.get("epaisseur_mm") is not None:
            libelle += f" {ligne['epaisseur_mm']:g} mm".replace(".", ",")
        parties.append(libelle)
    return " + ".join(parties)


def evaluer(identifiant: str, composition: dict[str, Any], materiaux: dict | None = None, elements: dict | None = None) -> dict[str, Any]:
    """Résultat d'un composant ; `valeur` vaut None tant que la composition est incomplète."""
    cat = categorie(identifiant)
    if not isinstance(composition, dict):
        raise ComposantError("Composition invalide.")
    if cat["nature"] == "paroi":
        if not composition.get("couches"):
            return {"grandeur": "Up", "unite": "W/(m²·K)", "valeur": None, "resume": "Aucune couche", "epaisseur_m": None, "epaisseur_complete": False, "detail": None}
        paroi = {**composition_par_defaut(identifiant), **composition}
        try:
            detail = parois.calculer_paroi(paroi, materiaux, elements)
        except parois.ParoiError as exc:
            raise ComposantError(str(exc)) from exc
        epaisseur, complete = _epaisseur(paroi["couches"], detail, elements)
        return {
            "grandeur": "Up", "unite": "W/(m²·K)", "valeur": detail["up_arrondi"], "resume": _resume(detail),
            "epaisseur_m": epaisseur, "epaisseur_complete": complete, "detail": detail,
        }
    if cat["nature"] == "menuiserie":
        uw = _nombre(composition, "uw", "Uw", 0.1, 7)
        sw = _nombre(composition, "sw", "Sw", 0, 1)
        tlw = _nombre(composition, "tlw", "TLw", 0, 1)
        extras = ", ".join(f"{nom} {v:g}".replace(".", ",") for nom, v in (("Sw", sw), ("TLw", tlw)) if v is not None)
        return {"grandeur": "Uw", "unite": "W/(m²·K)", "valeur": uw, "sw": sw, "tlw": tlw, "resume": extras or "Valeurs saisies", "detail": None}
    psi = _nombre(composition, "psi", "ψ", -1, 5)
    return {"grandeur": "ψ", "unite": "W/(m·K)", "valeur": psi, "resume": "Valeur saisie", "detail": None}
