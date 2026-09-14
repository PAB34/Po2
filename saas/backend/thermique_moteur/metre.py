"""Métré sur les plans, lot M1 : repère commun des niveaux, nord, tracés et synthèse d'un niveau.

Les tracés sont exprimés en points PDF de la planche du niveau. Le **calage** (deux points
communs A et B cliqués sur chaque plan, par exemple deux croisements d'axes) définit le
repère commun, en mètres : origine en A, axe x de A vers B. Le contour est tracé au **nu
intérieur** des parois déperditives (Th-Bât, fascicule généralités §3.5 : dimensions
intérieures). Voir docs/thermique/metre-plans-decisions.md.
"""
from __future__ import annotations

import math
import re
import unicodedata

PT_EN_MM = 25.4 / 72.0

TYPES_ZONE = {"contour": "Contour chauffé", "lnc": "Local non chauffé", "patio": "Patio ou cour"}
DONNE_SUR = {
    "exterieur": "Extérieur",
    "lnc": "Local non chauffé",
    "sol": "Sol (paroi enterrée)",
    "mitoyen": "Bâtiment chauffé mitoyen",
}
DONNE_SUR_DEFAUT = {"contour": "exterieur", "patio": "exterieur"}
TYPES_LNC = {
    "garage": "Garage, parking",
    "cave": "Cave, sous-sol",
    "vide_sanitaire": "Vide sanitaire",
    "combles": "Combles perdus",
    "circulation": "Circulation, cage d'escalier",
    "local_technique": "Local technique",
    "autre": "Autre local non chauffé",
}
# Écart toléré entre les distances A-B mesurées sur deux niveaux.
TOLERANCE_CALAGE_M = 0.05
# Un sommet à moins de 1 cm d'un bord est considéré comme posé dessus.
TOLERANCE_BORD_M = 0.01


class MetreError(ValueError):
    """Erreur de tracé dont le message est destiné à l'utilisateur."""


# --- Repère commun -------------------------------------------------------------------------------


def pt_en_m(echelle: float) -> float:
    return PT_EN_MM * echelle / 1000.0


def repere(calage: dict | None, echelle: float | None) -> dict | None:
    """Repère d'un niveau : de ses points PDF vers le repère commun (m). Sans calage, l'origine
    reste celle de la page (utile pour les surfaces, pas pour superposer les niveaux)."""
    if not echelle:
        return None
    if calage:
        (ax, ay), (bx, by) = calage["a"], calage["b"]
        angle = math.atan2(by - ay, bx - ax)
        origine = (ax, ay)
    else:
        angle, origine = 0.0, (0.0, 0.0)
    return {"ox": origine[0], "oy": origine[1], "cos": math.cos(angle), "sin": math.sin(angle), "k": pt_en_m(echelle), "cale": bool(calage)}


def vers_projet(rep: dict, point: list[float]) -> tuple[float, float]:
    dx, dy = point[0] - rep["ox"], point[1] - rep["oy"]
    return ((dx * rep["cos"] + dy * rep["sin"]) * rep["k"], (-dx * rep["sin"] + dy * rep["cos"]) * rep["k"])


def depuis_projet(rep: dict, point: tuple[float, float]) -> tuple[float, float]:
    dx, dy = point[0] / rep["k"], point[1] / rep["k"]
    return (rep["ox"] + dx * rep["cos"] - dy * rep["sin"], rep["oy"] + dx * rep["sin"] + dy * rep["cos"])


def angle_nord(rep: dict, pied: list[float], pointe: list[float]) -> float:
    """Direction du nord dans le repère commun, en degrés (sens trigonométrique, 0 = de A vers B)."""
    x1, y1 = vers_projet(rep, pied)
    x2, y2 = vers_projet(rep, pointe)
    if math.hypot(x2 - x1, y2 - y1) < 1e-6:
        raise MetreError("Le pied et la pointe de la flèche du nord sont confondus.")
    return round(math.degrees(math.atan2(y2 - y1, x2 - x1)) % 360.0, 2)


def controle_calages(niveaux: list[dict]) -> dict:
    """Distance A-B de chaque niveau calé, comparée à celle du premier : un écart trahit un point
    mal cliqué ou une échelle fausse."""
    par_niveau: dict = {}
    alertes: list[str] = []
    reference = None
    for niveau in niveaux:
        calage, echelle = niveau.get("calage"), niveau.get("echelle")
        if not calage or not echelle:
            continue
        (ax, ay), (bx, by) = calage["a"], calage["b"]
        ab = math.hypot(bx - ax, by - ay) * pt_en_m(echelle)
        if reference is None:
            reference = (niveau.get("nom"), ab)
            par_niveau[niveau["id"]] = {"ab_m": round(ab, 3), "ecart_m": 0.0}
            continue
        ecart = ab - reference[1]
        par_niveau[niveau["id"]] = {"ab_m": round(ab, 3), "ecart_m": round(ecart, 3)}
        if abs(ecart) > TOLERANCE_CALAGE_M:
            mesure, attendu = f"{ab:.2f}".replace(".", ","), f"{reference[1]:.2f}".replace(".", ",")
            alertes.append(
                f"Calage de « {niveau.get('nom')} » : A-B mesure {mesure} m contre {attendu} m sur "
                f"« {reference[0]} ». Vérifiez les points cliqués ou l'échelle de la planche."
            )
    return {"par_niveau": par_niveau, "alertes": alertes}


# --- Tracés --------------------------------------------------------------------------------------


def _aire_signee(points: list[list[float]]) -> float:
    total = 0.0
    for i, (x1, y1) in enumerate(points):
        x2, y2 = points[(i + 1) % len(points)]
        total += x1 * y2 - x2 * y1
    return total / 2.0


def longueurs_cotes(points: list[list[float]]) -> list[float]:
    return [math.hypot(points[(i + 1) % len(points)][0] - x, points[(i + 1) % len(points)][1] - y) for i, (x, y) in enumerate(points)]


def nettoyer_points(points) -> list[list[float]]:
    if not isinstance(points, (list, tuple)):
        raise MetreError("Tracé invalide : liste de points attendue.")
    propres: list[list[float]] = []
    for point in points:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise MetreError("Tracé invalide : chaque point doit avoir deux coordonnées.")
        x, y = float(point[0]), float(point[1])
        if not (math.isfinite(x) and math.isfinite(y)):
            raise MetreError("Tracé invalide : coordonnée non numérique.")
        if propres and math.hypot(x - propres[-1][0], y - propres[-1][1]) < 0.01:
            continue
        propres.append([round(x, 3), round(y, 3)])
    if len(propres) > 1 and math.hypot(propres[0][0] - propres[-1][0], propres[0][1] - propres[-1][1]) < 0.01:
        propres.pop()
    if len(propres) < 3:
        raise MetreError("Un tracé doit compter au moins trois sommets distincts.")
    if len(propres) > 2000:
        raise MetreError("Tracé trop détaillé (2 000 sommets au plus).")
    if abs(_aire_signee(propres)) < 1.0:
        raise MetreError("Le tracé est plat : sa surface est nulle.")
    return propres


def normaliser_cotes(cotes, nombre: int, defaut: str) -> list[dict]:
    """Une qualification par côté (côté i = du sommet i au suivant), complétée par défaut."""
    resultat = []
    for i in range(nombre):
        cote = cotes[i] if isinstance(cotes, list) and i < len(cotes) and isinstance(cotes[i], dict) else {}
        donne_sur = cote.get("donne_sur") or defaut
        if donne_sur not in DONNE_SUR:
            raise MetreError(f"« Donne sur » inconnu : {donne_sur}.")
        composant = cote.get("composant_id")
        resultat.append({"donne_sur": donne_sur, "composant_id": int(composant) if composant not in (None, "") else None})
    return resultat


def _orientation(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def auto_intersections(points: list[list[float]]) -> list[tuple[int, int]]:
    """Paires de côtés non voisins qui se croisent."""
    n = len(points)
    croisements = []
    for i in range(n):
        a, b = points[i], points[(i + 1) % n]
        for j in range(i + 2, n):
            if (j + 1) % n == i:
                continue
            c, d = points[j], points[(j + 1) % n]
            o1, o2, o3, o4 = _orientation(a, b, c), _orientation(a, b, d), _orientation(c, d, a), _orientation(c, d, b)
            if o1 * o2 < 0 and o3 * o4 < 0:
                croisements.append((i, j))
    return croisements


def dans_polygone(point, points: list[list[float]]) -> bool:
    x, y = point
    dedans = False
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            dedans = not dedans
    return dedans


def _distance_bord(point, points: list[list[float]]) -> float:
    meilleure = math.inf
    for i, a in enumerate(points):
        b = points[(i + 1) % len(points)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        longueur2 = dx * dx + dy * dy
        t = 0.0 if longueur2 == 0 else max(0.0, min(1.0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / longueur2))
        meilleure = min(meilleure, math.hypot(point[0] - a[0] - t * dx, point[1] - a[1] - t * dy))
    return meilleure


def _echantillons(points: list[list[float]]) -> list[tuple[float, float]]:
    """Points juste à l'intérieur du tracé, au quart, à la moitié et aux trois quarts de chaque
    côté : servent à situer un local par rapport au contour, même quand il en partage les bords."""
    signe = 1.0 if _aire_signee(points) > 0 else -1.0
    decalage = 0.05
    resultat = []
    for i, (x1, y1) in enumerate(points):
        x2, y2 = points[(i + 1) % len(points)]
        longueur = math.hypot(x2 - x1, y2 - y1)
        if longueur == 0:
            continue
        nx, ny = -(y2 - y1) / longueur * decalage * signe, (x2 - x1) / longueur * decalage * signe
        for t in (0.25, 0.5, 0.75):
            resultat.append((x1 + t * (x2 - x1) + nx, y1 + t * (y2 - y1) + ny))
    return resultat


def _position_dans_contours(points: list[list[float]], contours: list[dict], tolerance: float) -> tuple[bool, bool]:
    """(dedans, déborde) : un local est dans un contour si une partie de ses échantillons y est ;
    il déborde si d'autres sont franchement dehors. Les échantillons posés sur un bord ne comptent pas."""
    dedans = dehors = 0
    for echantillon in _echantillons(points):
        if any(_distance_bord(echantillon, contour["points"]) <= tolerance for contour in contours):
            continue
        if any(dans_polygone(echantillon, contour["points"]) for contour in contours):
            dedans += 1
        else:
            dehors += 1
    return dedans > 0, dedans > 0 and dehors > 0


def synthese_niveau(
    echelle: float | None,
    hauteur_etage_m: float | None,
    epaisseur_plancher_m: float | None,
    zones: list[dict],
    hauteur_sous_plafond_m: float | None = None,
) -> dict:
    """Surfaces et linéaires d'un niveau. Les locaux non chauffés et patios situés dans un contour
    en sont déduits ; ceux qui le jouxtent restent à part (le contour s'arrête alors à leur mur)."""
    alertes: list[str] = []
    k = pt_en_m(echelle) if echelle else None
    if zones and k is None:
        alertes.append("Échelle de la planche non définie : surfaces et longueurs indisponibles.")
    contours = [zone for zone in zones if zone["type"] == "contour"]
    if zones and not contours:
        alertes.append("Aucun contour chauffé sur ce niveau.")
    tolerance = TOLERANCE_BORD_M / k if k else 0.3

    totaux = {cle: 0.0 for cle in TYPES_ZONE}
    deduit = 0.0
    lineaires = {cle: 0.0 for cle in DONNE_SUR}
    resumes = []
    for zone in zones:
        points = zone["points"]
        alertes_zone: list[str] = []
        croisements = auto_intersections(points)
        if croisements:
            alertes_zone.append(f"Le tracé se recoupe ({len(croisements)} croisement{'s' if len(croisements) > 1 else ''}) : déplacez les sommets.")
        incluse = None
        if zone["type"] != "contour":
            incluse, deborde = _position_dans_contours(points, contours, tolerance)
            if deborde:
                alertes_zone.append("Déborde du contour : la surface déduite est approchée (calcul exact au lot M2).")
            if zone["type"] == "patio" and not incluse:
                alertes_zone.append("Patio hors de tout contour : il n'est pas pris en compte.")
        aire = perimetre = None
        cotes_m = None
        if k:
            longueurs = longueurs_cotes(points)
            aire = abs(_aire_signee(points)) * k * k
            perimetre = sum(longueurs) * k
            cotes_m = [round(longueur * k, 3) for longueur in longueurs]
            totaux[zone["type"]] += aire
            if incluse:
                deduit += aire
            if zone["type"] == "contour" or (zone["type"] == "patio" and incluse):
                for longueur, cote in zip(longueurs, zone.get("cotes") or []):
                    lineaires[cote["donne_sur"]] += longueur * k
        resumes.append(
            {
                "id": zone.get("id"),
                "aire_m2": round(aire, 2) if aire is not None else None,
                "perimetre_m": round(perimetre, 2) if perimetre is not None else None,
                "cotes_m": cotes_m,
                "incluse_dans_contour": incluse,
                "alertes": alertes_zone,
            }
        )

    hauteur = None
    if hauteur_sous_plafond_m is not None:
        hauteur = round(hauteur_sous_plafond_m, 3)
        if hauteur_etage_m is not None and hauteur_sous_plafond_m > hauteur_etage_m:
            alertes.append("La hauteur sous plafond dépasse la hauteur d'étage.")
    elif hauteur_etage_m is not None and epaisseur_plancher_m is not None:
        if hauteur_etage_m > epaisseur_plancher_m:
            hauteur = round(hauteur_etage_m - epaisseur_plancher_m, 3)
        else:
            alertes.append("L'épaisseur du plancher dépasse la hauteur d'étage.")
    return {
        "zones": resumes,
        "surface_contour_m2": round(totaux["contour"], 2) if k else None,
        "surface_lnc_m2": round(totaux["lnc"], 2) if k else None,
        "surface_patio_m2": round(totaux["patio"], 2) if k else None,
        "surface_chauffee_m2": round(totaux["contour"] - deduit, 2) if k and contours else None,
        "lineaires_m": {cle: round(valeur, 2) for cle, valeur in lineaires.items()} if k else None,
        # Hauteur intérieure = hauteur d'étage − épaisseur du plancher (dimensions intérieures).
        "hauteur_interieure_m": hauteur,
        "surfaces_murs_m2": {cle: round(valeur * hauteur, 2) for cle, valeur in lineaires.items()} if k and hauteur else None,
        "alertes": alertes,
    }


# --- Niveaux proposés depuis les planches --------------------------------------------------------


def _majuscules(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in decompose if not unicodedata.combining(c)).upper()


def ordre_niveau(libelle: str | None) -> int | None:
    """Rang d'un niveau d'après son libellé : « Niveau -1 » → -1, « RDC » → 0, « R+2 » → 2.
    La toiture n'est pas un niveau chauffé : pas de rang."""
    if not libelle:
        return None
    texte = _majuscules(libelle)
    if "TOITURE" in texte or "TERRASSE" in texte:
        return None
    trouve = re.search(r"(?:NIVEAU|ETAGE)\s*_?\s*(-?\d+)", texte)
    if trouve:
        return int(trouve.group(1))
    trouve = re.search(r"(?<![A-Z])R\s*([+-])\s*(\d+)", texte)
    if trouve:
        return int(trouve.group(2)) * (1 if trouve.group(1) == "+" else -1)
    if re.search(r"(?<![A-Z])(RDC|REZ)", texte):
        return 0
    if re.search(r"SOUS[\s_-]?SOL", texte):
        return -1
    return None


def suggestion_niveaux(planches: list[dict]) -> list[dict]:
    """Un niveau par planche de plan dont le libellé de niveau est reconnu, du plus bas au plus haut."""
    retenus: dict[int, dict] = {}
    for planche in planches:
        if planche.get("nature") != "plan":
            continue
        rang = ordre_niveau(planche.get("niveau"))
        if rang is None or rang in retenus:
            continue
        retenus[rang] = {"nom": planche["niveau"], "ordre": rang, "planche_id": planche["id"]}
    return [retenus[rang] for rang in sorted(retenus)]
