"""Coefficient de transmission surfacique d'une paroi opaque en couches (lot B2).

Méthode des règles Th-Bât, fascicule « Parois opaques » (méthodes), §3.1 :
- Up = Uc + ΔU1 + ΔU2 (ΔU3, toitures inversées : lot B2c) ; Uc = 1 / (Rsi + ΣR + Rse) ;
- couche homogène : R = e / λ ; lame d'air non ventilée : tableau V, interpolation linéaire
  autorisée par le document ; lame d'air fortement ventilée : la lame et les couches situées
  vers l'extérieur sont ignorées, et Rse prend la valeur de Rsi ;
- ΔU2 = ΔU'' × (R1 / RT,h)², ΔU'' selon trois niveaux de cavités et lames d'air parasites ;
- paroi donnant sur un local non chauffé : Rsi s'applique des deux côtés (tableau X, note 2) ;
- arrondis du document : résistances à 3 décimales, U à 2 chiffres significatifs.

Les couches sont données de l'intérieur vers l'extérieur. Les valeurs de ce module sont
recoupées automatiquement avec le texte du document à chaque construction de la
bibliothèque (voir `bibliotheque/build.py`).
"""
from __future__ import annotations

import copy
import math
from typing import Any

SOURCE = "Règles Th-Bât, fascicule Parois opaques (méthodes), §3.1"

# Tableau X : résistances superficielles (m².K/W).
RESISTANCES_SUPERFICIELLES: dict[str, dict[str, Any]] = {
    "mur": {"libelle": "Mur : paroi verticale (inclinaison ≥ 60°), flux horizontal", "flux": "horizontal", "rsi": 0.13, "rse": 0.04},
    "plancher_haut": {"libelle": "Toiture ou plancher haut : paroi horizontale, flux ascendant", "flux": "ascendant", "rsi": 0.10, "rse": 0.04},
    "plancher_bas": {"libelle": "Plancher bas sur extérieur ou local non chauffé : paroi horizontale, flux descendant", "flux": "descendant", "rsi": 0.17, "rse": 0.04},
}
DONNE_SUR = {"exterieur": "Extérieur (ou passage, local ouvert)", "local_non_chauffe": "Local non chauffé (Rsi des deux côtés)"}

# Tableau V : lames d'air non ventilées, faces d'émissivité au moins 0,8.
LAMES_AIR_MM = (0, 5, 7, 10, 15, 25, 50, 100, 300)
LAMES_AIR_R: dict[str, tuple[float, ...]] = {
    "ascendant": (0.00, 0.11, 0.13, 0.15, 0.16, 0.16, 0.16, 0.16, 0.16),
    "horizontal": (0.00, 0.11, 0.13, 0.15, 0.17, 0.18, 0.18, 0.18, 0.18),
    "descendant": (0.00, 0.11, 0.13, 0.15, 0.17, 0.19, 0.21, 0.22, 0.23),
}

# ΔU'' : cavités et lames d'air parasites dans une paroi ventilée sur l'extérieur.
NIVEAUX_DELTA_U2: dict[int, dict[str, Any]] = {
    1: {"valeur": 0.00, "libelle": "Aucune cavité ni lame d'air dans la paroi"},
    2: {"valeur": 0.01, "libelle": "Cavités ponctuelles ou linéaires traversant tout ou partie de l'isolant"},
    3: {"valeur": 0.04, "libelle": "Cavités communiquant avec des lames d'air côté chaud de l'isolant"},
}

TYPES_COUCHE = ("materiau", "lambda", "resistance", "element", "lame_air", "lame_air_ventilee")
EPAISSEUR_ISOLANT_MAX_M = 1.0


class ParoiError(ValueError):
    """Donnée de paroi invalide ; le message est destiné à l'utilisateur."""


def chiffres_significatifs(valeur: float, chiffres: int = 2) -> float:
    if valeur == 0:
        return 0.0
    return round(valeur, -int(math.floor(math.log10(abs(valeur)))) + chiffres - 1)


def resistance_lame_air(epaisseur_mm: float, flux: str) -> float:
    if flux not in LAMES_AIR_R:
        raise ParoiError(f"Sens de flux inconnu : {flux}.")
    if not 0 <= epaisseur_mm <= LAMES_AIR_MM[-1]:
        raise ParoiError(
            "Lame d'air de plus de 300 mm : le document impose un bilan thermique (coefficient b), "
            "hors du calcul en couches."
        )
    valeurs = LAMES_AIR_R[flux]
    for i in range(len(LAMES_AIR_MM) - 1):
        e0, e1 = LAMES_AIR_MM[i], LAMES_AIR_MM[i + 1]
        if e0 <= epaisseur_mm <= e1:
            return valeurs[i] + (epaisseur_mm - e0) / (e1 - e0) * (valeurs[i + 1] - valeurs[i])
    return valeurs[-1]


def _nombre(couche: dict, cle: str, nom: str, minimum: float = 0.0, strict: bool = True) -> float:
    try:
        valeur = float(couche[cle])
    except (KeyError, TypeError, ValueError):
        raise ParoiError(f"{nom} manquant ou invalide.") from None
    if valeur < minimum or (strict and valeur == minimum):
        raise ParoiError(f"{nom} doit être {'strictement ' if strict else ''}supérieur à {minimum:g}.")
    return valeur


def _resistance_element(couche: dict, index: int, elements: dict[str, dict] | None, ligne: dict, remarques: list[str]) -> float:
    """R lue dans une case d'un tableau d'applications (lot B2b, décision B2b-D2)."""
    tableau = (elements or {}).get(couche.get("tableau_id"))
    if tableau is None:
        raise ParoiError(f"Couche {index + 1} : tableau d'éléments inconnu ({couche.get('tableau_id')}).")
    try:
        i, j = int(couche.get("ligne", -1)), int(couche.get("colonne", 0))
    except (TypeError, ValueError):
        raise ParoiError(f"Couche {index + 1} : ligne ou colonne du tableau invalide.") from None
    if not (0 <= i < len(tableau["lignes"]) and 0 <= j < len(tableau["colonnes"])):
        raise ParoiError(f"Couche {index + 1} : case hors du tableau.")
    rangee = tableau["lignes"][i]
    variante = couche.get("variante") or None
    valeurs = rangee["variantes"].get(variante) if variante else rangee["valeurs"]
    if valeurs is None or valeurs[j] is None:
        raise ParoiError(f"Couche {index + 1} : pas de valeur dans cette case du tableau.")
    colonne = f", {tableau['axe_colonnes'].lower()} {tableau['colonnes'][j]}" if len(tableau["colonnes"]) > 1 else ""
    libelle = f"{tableau['titre']} : {rangee['libelle']}{colonne}"
    if variante:
        libelle += f" — {tableau['variantes'].get(variante, variante)}"
    ligne["libelle"] = ligne["libelle"] or libelle
    numero = f"T{tableau['numero']}" if tableau.get("numero") else "figure"
    lecture = ", lu sur image" if tableau.get("lecture") == "image" else ""
    ligne["source"] = f"Th-Bât {tableau['fascicule']} {numero} p. {tableau['page']}{lecture}"
    ligne["tabule"] = True
    if "isolant" not in couche:
        ligne["isolant"] = bool(tableau.get("isolant"))
    for signalement in tableau.get("signalements", []):
        if signalement["ligne"] == i and signalement.get("colonne") in (None, j):
            remarques.append(f"Couche {index + 1} : {signalement['message']}")
    return float(valeurs[j])


def calculer_paroi(
    paroi: dict[str, Any], materiaux: dict[str, dict] | None = None, elements: dict[str, dict] | None = None
) -> dict[str, Any]:
    """Résistance et coefficient Up d'une paroi, avec le détail couche par couche."""
    type_paroi = paroi.get("type")
    if type_paroi not in RESISTANCES_SUPERFICIELLES:
        raise ParoiError("Type de paroi inconnu (mur, plancher_haut ou plancher_bas).")
    donne_sur = paroi.get("donne_sur", "exterieur")
    if donne_sur not in DONNE_SUR:
        raise ParoiError("La paroi donne sur l'extérieur ou sur un local non chauffé.")
    couches = paroi.get("couches") or []
    if not couches:
        raise ParoiError("Ajoutez au moins une couche.")
    reference = RESISTANCES_SUPERFICIELLES[type_paroi]
    flux = reference["flux"]
    rsi = reference["rsi"]
    rse = rsi if donne_sur == "local_non_chauffe" else reference["rse"]
    remarques: list[str] = []
    if donne_sur == "local_non_chauffe":
        remarques.append("Paroi sur local non chauffé : Rsi appliquée des deux côtés.")

    details: list[dict[str, Any]] = []
    somme_r = 0.0
    r_isolant = 0.0
    ventilee = False
    for index, couche in enumerate(couches):
        genre = couche.get("type")
        if genre not in TYPES_COUCHE:
            raise ParoiError(f"Couche {index + 1} : type inconnu.")
        ligne: dict[str, Any] = {"index": index, "type": genre, "libelle": couche.get("libelle") or "", "isolant": bool(couche.get("isolant"))}
        if ventilee:
            ligne.update({"r": 0.0, "ignoree": True})
            details.append(ligne)
            continue
        if genre in ("materiau", "lambda"):
            epaisseur = _nombre(couche, "epaisseur_m", f"Couche {index + 1} : épaisseur", strict=False)
            if genre == "materiau":
                identifiant = couche.get("materiau_id")
                materiau = (materiaux or {}).get(identifiant)
                if materiau is None:
                    raise ParoiError(f"Couche {index + 1} : matériau inconnu ({identifiant}).")
                conductivite = float(materiau["lambda"])
                ligne["libelle"] = ligne["libelle"] or materiau.get("libelle", identifiant)
                ligne["source"] = f"{materiau.get('section', '')} p. {materiau.get('page', '?')}"
            else:
                conductivite = _nombre(couche, "lambda", f"Couche {index + 1} : conductivité λ")
            r = epaisseur / conductivite
            ligne.update({"epaisseur_m": epaisseur, "lambda": conductivite})
        elif genre == "resistance":
            r = _nombre(couche, "r", f"Couche {index + 1} : résistance R", strict=False)
        elif genre == "element":
            r = _resistance_element(couche, index, elements, ligne, remarques)
        elif genre == "lame_air":
            epaisseur_mm = _nombre(couche, "epaisseur_mm", f"Couche {index + 1} : épaisseur de la lame d'air", strict=False)
            r = resistance_lame_air(epaisseur_mm, flux)
            ligne.update({"epaisseur_mm": epaisseur_mm, "flux": flux})
        else:  # lame d'air fortement ventilée
            ventilee = True
            r = 0.0
            rse = rsi
            remarques.append("Lame d'air fortement ventilée : elle et les couches extérieures sont ignorées, Rse = Rsi.")
        ligne["r"] = round(r, 3)
        details.append(ligne)
        somme_r += r
        if ligne["isolant"]:
            r_isolant += r

    rt = rsi + somme_r + rse
    uc = 1 / rt
    niveau = int(paroi.get("niveau_delta_u2", 1) or 1)
    if niveau not in NIVEAUX_DELTA_U2:
        raise ParoiError("Niveau de correction ΔU2 : 1, 2 ou 3.")
    if niveau > 1 and r_isolant == 0:
        raise ParoiError("Indiquez la couche isolante pour appliquer la correction ΔU2.")
    delta_u2 = NIVEAUX_DELTA_U2[niveau]["valeur"] * (r_isolant / rt) ** 2
    delta_u1 = float(paroi.get("delta_u1", 0) or 0)
    if delta_u1 < 0:
        raise ParoiError("ΔU1 (ponts thermiques intégrés) ne peut pas être négatif.")
    up = uc + delta_u1 + delta_u2
    return {
        "type": type_paroi,
        "libelle_type": reference["libelle"],
        "donne_sur": donne_sur,
        "flux": flux,
        "couches": details,
        "rsi": rsi,
        "rse": rse,
        "r_couches": round(somme_r, 3),
        "rt": round(rt, 3),
        "uc": round(uc, 4),
        "delta_u1": round(delta_u1, 4),
        "niveau_delta_u2": niveau,
        "delta_u2": round(delta_u2, 4),
        "up": round(up, 4),
        "up_arrondi": chiffres_significatifs(up, 2),
        "remarques": remarques,
        "source": SOURCE,
    }


def epaisseur_isolant(
    paroi: dict[str, Any],
    index_isolant: int,
    u_cible: float,
    materiaux: dict[str, dict] | None = None,
    epaisseur_max_m: float = EPAISSEUR_ISOLANT_MAX_M,
    elements: dict[str, dict] | None = None,
) -> dict[str, Any]:
    """Épaisseur minimale de la couche isolante pour que Up ne dépasse pas la cible."""
    couches = paroi.get("couches") or []
    if not 0 <= index_isolant < len(couches):
        raise ParoiError("Choisissez la couche isolante à dimensionner.")
    couche = couches[index_isolant]
    if couche.get("type") not in ("materiau", "lambda"):
        raise ParoiError("La couche à dimensionner doit être un matériau ou une conductivité λ.")
    if u_cible <= 0:
        raise ParoiError("Le U cible doit être positif.")

    def up_pour(epaisseur: float) -> float:
        essai = copy.deepcopy(paroi)
        essai["couches"][index_isolant] = {**couche, "epaisseur_m": epaisseur, "isolant": True}
        return calculer_paroi(essai, materiaux, elements)["up"]

    if up_pour(epaisseur_max_m) > u_cible:
        raise ParoiError(f"U cible {u_cible:g} inatteignable avec {epaisseur_max_m * 100:.0f} cm d'isolant ou moins.")
    if up_pour(0.0) <= u_cible:
        minimum = 0.0
    else:
        bas, haut = 0.0, epaisseur_max_m
        for _ in range(60):  # Up décroît avec l'épaisseur : dichotomie
            milieu = (bas + haut) / 2
            if up_pour(milieu) > u_cible:
                bas = milieu
            else:
                haut = milieu
        minimum = haut
    arrondie = math.ceil(round(minimum * 100, 6)) / 100
    up_obtenu = up_pour(arrondie)
    return {
        "u_cible": u_cible,
        "epaisseur_min_m": round(minimum, 4),
        "epaisseur_arrondie_m": arrondie,
        "up_obtenu": round(up_obtenu, 4),
        "up_obtenu_arrondi": chiffres_significatifs(up_obtenu, 2),
        "source": SOURCE,
    }
