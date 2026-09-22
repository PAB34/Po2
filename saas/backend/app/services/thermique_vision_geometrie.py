"""Mise au propre géométrique des objets proposés par l'IA visuelle, par algorithmes classiques.

Tout se calcule en pixels de l'image analysée (repère isotrope) et à partir du seul raster :
1. simplification Douglas-Peucker, qui supprime les zigzags de quelques pixels ;
2. redressement de chaque segment sur les directions dominantes du plan (orthogonales et façades en
   biais), en recalculant les sommets par intersection pour garder le tracé connecté ;
3. recalage des murs, refends, cloisons et isolants sur la bande d'encre la plus proche, perpendiculairement
   à chaque segment, lorsque le raster le justifie nettement.
Aucune primitive vectorielle du PDF n'est lue.
"""
from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np

Point = tuple[float, float]

# Tolérances exprimées en pixels de l'image analysée (≈ 150 dpi, soit 1,7 cm par pixel au 1/100).
SIMPLIFICATION_PX = 6.0
ANGLE_ACCROCHE_DEG = 6.0
FUSION_COLINEAIRE_PX = 8.0
DIRECTION_LONGUEUR_MIN_PX = 80.0
# Demi-largeur de recherche et largeur de bande d'encre par nature de paroi.
RECALAGE_RAYON_PX = 22
BANDES_PX = {"mur_exterieur": 17, "refend": 13, "cloison": 5, "isolation": 7}
RECALAGE_GAIN_MIN = 1.25
LINEAIRES = {"mur_exterieur", "refend", "cloison", "isolation", "garde_corps",
             "menuiserie_exterieure", "menuiserie_interieure"}


def _distance_segment(p: Point, a: Point, b: Point) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    longueur2 = dx * dx + dy * dy
    if longueur2 == 0:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / longueur2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def simplifier(points: Sequence[Point], tolerance: float = SIMPLIFICATION_PX, ferme: bool = False) -> list[Point]:
    """Douglas-Peucker ; un contour fermé est coupé à son sommet le plus éloigné du premier."""
    pts = [tuple(map(float, p)) for p in points]
    dedoublonnes = [pts[0]] if pts else []
    for p in pts[1:]:
        if math.hypot(p[0] - dedoublonnes[-1][0], p[1] - dedoublonnes[-1][1]) > 0.5:
            dedoublonnes.append(p)
    pts = dedoublonnes
    if ferme and len(pts) > 1 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) <= 0.5:
        pts = pts[:-1]
    if len(pts) <= 2:
        return pts

    def dp(chaine: list[Point]) -> list[Point]:
        if len(chaine) <= 2:
            return chaine
        distances = [_distance_segment(p, chaine[0], chaine[-1]) for p in chaine[1:-1]]
        k = int(np.argmax(distances)) + 1
        if distances[k - 1] <= tolerance:
            return [chaine[0], chaine[-1]]
        return dp(chaine[: k + 1])[:-1] + dp(chaine[k:])

    if not ferme:
        return dp(pts)
    loin = max(range(len(pts)), key=lambda k: math.hypot(pts[k][0] - pts[0][0], pts[k][1] - pts[0][1]))
    resultat = dp(pts[: loin + 1])[:-1] + dp(pts[loin:] + [pts[0]])[:-1]
    return resultat if len(resultat) >= 3 else pts


def _angle(a: Point, b: Point) -> float:
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0


def _ecart_angle(a: float, b: float) -> float:
    ecart = abs(a - b) % 180.0
    return min(ecart, 180.0 - ecart)


def directions_dominantes(objets: Sequence[dict[str, Any]], pas_deg: float = 1.0) -> list[float]:
    """Directions des parois (modulo 180°), pondérées par la longueur ; 0° et 90° toujours retenus."""
    histogramme = np.zeros(int(180 / pas_deg))
    mesures: list[tuple[float, float]] = []
    for objet in objets:
        if objet["category"] not in {"mur_exterieur", "refend", "cloison", "isolation", "piece"}:
            continue
        pts = objet["points_px"]
        segments = list(zip(pts, pts[1:] + (pts[:1] if objet.get("geometry_type") == "polygon" else [])))
        for a, b in segments:
            longueur = math.hypot(b[0] - a[0], b[1] - a[1])
            if longueur >= DIRECTION_LONGUEUR_MIN_PX:
                histogramme[int(round(_angle(a, b) / pas_deg)) % len(histogramme)] += longueur
                mesures.append((_angle(a, b), longueur))
    directions = [0.0, 90.0]
    lisse = sum(np.roll(histogramme, k) for k in (-2, -1, 0, 1, 2))
    total = float(histogramme.sum()) or 1.0
    for k in np.argsort(lisse)[::-1]:
        angle = float(k * pas_deg)
        if lisse[k] / total < 0.04:
            break
        if all(_ecart_angle(angle, d) > 2 * ANGLE_ACCROCHE_DEG for d in directions):
            # direction fine : moyenne des angles exacts proches du pic, pondérée par la longueur
            proches = [(a, l) for a, l in mesures if _ecart_angle(a, angle) <= 3 * pas_deg]
            if proches:
                somme = sum(l for _, l in proches)
                angle = sum((angle + ((a - angle + 90) % 180 - 90)) * l for a, l in proches) / somme % 180.0
            directions.append(angle)
    return directions


def _droite(a: Point, b: Point, directions: Sequence[float]) -> tuple[Point, Point]:
    """Droite support (point, vecteur unitaire), accrochée à une direction dominante si proche."""
    angle = _angle(a, b)
    proche = min(directions, key=lambda d: _ecart_angle(angle, d))
    if _ecart_angle(angle, proche) <= ANGLE_ACCROCHE_DEG:
        angle = proche
    rad = math.radians(angle)
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), (math.cos(rad), math.sin(rad))


def _projeter(p: Point, droite: tuple[Point, Point]) -> Point:
    (ox, oy), (ux, uy) = droite
    t = (p[0] - ox) * ux + (p[1] - oy) * uy
    return (ox + t * ux, oy + t * uy)


def _decalage(p: Point, droite: tuple[Point, Point]) -> float:
    (ox, oy), (ux, uy) = droite
    return (p[0] - ox) * -uy + (p[1] - oy) * ux


def _intersection(d1: tuple[Point, Point], d2: tuple[Point, Point]) -> Point | None:
    (x1, y1), (u1, v1) = d1
    (x2, y2), (u2, v2) = d2
    det = u1 * v2 - v1 * u2
    if abs(det) < math.sin(math.radians(10)):
        return None
    t = ((x2 - x1) * v2 - (y2 - y1) * u2) / det
    return (x1 + t * u1, y1 + t * v1)


def redresser(points: Sequence[Point], directions: Sequence[float], ferme: bool = False) -> list[Point]:
    """Accroche chaque segment à une direction dominante puis recalcule les sommets par intersection."""
    pts = list(points)
    if len(pts) < 2:
        return pts
    paires = list(zip(pts, pts[1:] + (pts[:1] if ferme else [])))
    droites: list[tuple[tuple[Point, Point], float, Point, Point]] = []
    for a, b in paires:
        longueur = math.hypot(b[0] - a[0], b[1] - a[1])
        if longueur < 0.5:
            continue
        droite = _droite(a, b, directions)
        if droites:
            precedente, poids, debut, _ = droites[-1]
            if (precedente[1] == droite[1] or _ecart_angle(_angle((0, 0), precedente[1]), _angle((0, 0), droite[1])) < 0.5) \
                    and abs(_decalage(droite[0], precedente)) <= FUSION_COLINEAIRE_PX:
                # deux segments colinéaires : une seule droite, moyenne pondérée par la longueur
                decalage = _decalage(droite[0], precedente) * longueur / (poids + longueur)
                (ox, oy), (ux, uy) = precedente
                droites[-1] = (((ox - uy * decalage, oy + ux * decalage), (ux, uy)), poids + longueur, debut, b)
                continue
        droites.append((droite, longueur, a, b))
    if ferme and len(droites) > 2:
        premiere, derniere = droites[0], droites[-1]
        if _ecart_angle(_angle((0, 0), premiere[0][1]), _angle((0, 0), derniere[0][1])) < 0.5 \
                and abs(_decalage(derniere[0][0], premiere[0])) <= FUSION_COLINEAIRE_PX:
            droites = [(premiere[0], premiere[1] + derniere[1], derniere[2], premiere[3])] + droites[1:-1]
    if not droites:
        return pts
    if len(droites) == 1:
        droite, _, a, b = droites[0]
        return [_projeter(a, droite), _projeter(b, droite)]
    sommets: list[Point] = []
    if not ferme:
        sommets.append(_projeter(droites[0][2], droites[0][0]))
    enchainement = list(zip(droites, droites[1:] + (droites[:1] if ferme else [])))
    for (d1, _, _, fin), (d2, _, _, _) in enchainement:
        croisement = _intersection(d1, d2)
        if croisement is None or math.hypot(croisement[0] - fin[0], croisement[1] - fin[1]) > 4 * FUSION_COLINEAIRE_PX:
            # droites parallèles décalées (redan) : un court retour perpendiculaire
            sommets.extend([_projeter(fin, d1), _projeter(fin, d2)])
        else:
            sommets.append(croisement)
    if not ferme:
        sommets.append(_projeter(droites[-1][3], droites[-1][0]))
    return sommets


def _encre(image: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    hauteur, largeur = image.shape
    xi = np.clip(np.round(x).astype(int), 0, largeur - 1)
    yi = np.clip(np.round(y).astype(int), 0, hauteur - 1)
    return image[yi, xi]


def recaler(points: list[Point], encre: np.ndarray, bande_px: int, ferme: bool = False) -> list[Point]:
    """Déplace chaque segment perpendiculairement vers la bande d'encre la plus dense, puis reconnecte."""
    if len(points) < 2:
        return points
    paires = list(zip(points, points[1:] + (points[:1] if ferme else [])))
    droites: list[tuple[Point, Point]] = []
    for a, b in paires:
        longueur = math.hypot(b[0] - a[0], b[1] - a[1])
        if longueur < 1:
            droites.append(((a[0], a[1]), (1.0, 0.0)))
            continue
        ux, uy = (b[0] - a[0]) / longueur, (b[1] - a[1]) / longueur
        t = np.linspace(0.1, 0.9, max(8, int(longueur / 4)))
        base_x = a[0] + t * (b[0] - a[0])
        base_y = a[1] + t * (b[1] - a[1])
        decalages = np.arange(-RECALAGE_RAYON_PX - bande_px, RECALAGE_RAYON_PX + bande_px + 1)
        profil = np.array([_encre(encre, base_x - uy * o, base_y + ux * o).mean() for o in decalages])
        noyau = np.ones(bande_px) / bande_px
        lisse = np.convolve(profil, noyau, mode="same")
        centre = len(decalages) // 2
        zone = slice(centre - RECALAGE_RAYON_PX, centre + RECALAGE_RAYON_PX + 1)
        meilleur = int(np.argmax(lisse[zone])) + centre - RECALAGE_RAYON_PX
        decalage = 0.0
        if lisse[meilleur] >= RECALAGE_GAIN_MIN * max(lisse[centre], 0.02) and lisse[meilleur] > 0.15:
            decalage = float(decalages[meilleur])
        droites.append(((a[0] + (b[0] - a[0]) / 2 - uy * decalage, a[1] + (b[1] - a[1]) / 2 + ux * decalage), (ux, uy)))
    sommets: list[Point] = []
    if not ferme:
        sommets.append(_projeter(points[0], droites[0]))
    enchainement = list(zip(droites, droites[1:] + (droites[:1] if ferme else [])))
    fins = points[1:] + (points[:1] if ferme else [])
    for (d1, d2), fin in zip(enchainement, fins):
        croisement = _intersection(d1, d2)
        if croisement is None:
            sommets.extend([_projeter(fin, d1), _projeter(fin, d2)])
        else:
            sommets.append(croisement)
    if not ferme:
        sommets.append(_projeter(points[-1], droites[-1]))
    return sommets


ESPACES = {"piece", "terrasse", "balcon", "indetermine"}
RECOUVREMENT_MIN = 0.02


def separer_espaces(objets: list[dict[str, Any]], sx: float = 1.0, sy: float = 1.0) -> int:
    """Deux espaces d'un même niveau ne se recouvrent pas : le plus grand est amputé des plus petits.

    Seules les pièces sont amputées ; les vides, terrasses et objets à déterminer restent tels quels. Si la
    découpe produit plusieurs morceaux ou un trou, l'espace est gardé tel quel et signalé pour revue.
    Retourne le nombre de pièces modifiées.
    """
    from shapely.geometry import Polygon

    formes = []
    for objet in objets:
        if objet.get("category") in ESPACES and objet.get("geometry_type") == "polygon" and len(objet["points"]) >= 3:
            forme = Polygon([(float(x) * sx, float(y) * sy) for x, y in objet["points"]]).buffer(0)
            if forme.is_valid and forme.area > 0:
                formes.append((objet, forme))
    modifiees = 0
    for objet, forme in sorted(formes, key=lambda item: -item[1].area):
        if objet["category"] != "piece":
            continue
        reste = forme
        for autre, autre_forme in formes:
            if autre is objet or autre_forme.area >= forme.area:
                continue
            if reste.intersection(autre_forme).area <= RECOUVREMENT_MIN * autre_forme.area:
                continue
            candidat = reste.difference(autre_forme)
            if candidat.geom_type == "MultiPolygon":
                # éclats de quelques pixels laissés par des bords presque confondus
                morceaux = [m for m in candidat.geoms if m.area > 0.01 * forme.area]
                candidat = morceaux[0] if len(morceaux) == 1 else candidat
            if candidat.geom_type == "Polygon" and len(candidat.interiors) > len(getattr(reste, "interiors", [])):
                # espace enclavé (gaine, trémie au milieu) : pas de trou dans un contour éditable, il est
                # rattaché à la pièce pour être déduit de sa surface au calcul
                if autre.get("id"):
                    objet.setdefault("enclaves", []).append(autre["id"])
                continue
            reste = candidat
        if reste.equals(forme):
            continue
        reste = reste.simplify(0.5)
        if reste.geom_type != "Polygon" or len(reste.interiors):
            objet["review_required"] = True
            objet["evidence"] = (objet.get("evidence", "") + " ; chevauche un autre espace").strip(" ;")
            continue
        objet["points"] = [
            [round(x / sx, 3), round(y / sy, 3)] for x, y in list(reste.exterior.coords)[:-1]
        ]
        modifiees += 1
    return modifiees


def mettre_au_propre(
    objets: list[dict[str, Any]],
    largeur_px: float,
    hauteur_px: float,
    encre: np.ndarray | None = None,
) -> dict[str, Any]:
    """Nettoie ``points`` (repère 0..1000 de l'image analysée) de chaque objet, en place.

    ``encre`` est l'image en niveaux d'encre (0 = blanc, 1 = noir) à la taille ``largeur_px`` × ``hauteur_px``.
    Retourne un petit bilan (directions retenues, nombre de sommets avant/après, objets recalés).
    """
    sx, sy = largeur_px / 1000, hauteur_px / 1000
    for objet in objets:
        objet["points_px"] = [(float(x) * sx, float(y) * sy) for x, y in objet["points"]]
    directions = directions_dominantes(objets)
    avant = apres = recales = 0
    for objet in objets:
        ferme = objet.get("geometry_type") in {"polygon", "bbox"}
        pts = objet.pop("points_px")
        avant += len(pts)
        if objet.get("geometry_type") == "bbox" or len(pts) < 2:
            apres += len(pts)
            continue
        nets = redresser(simplifier(pts, ferme=ferme), directions, ferme=ferme)
        bande = BANDES_PX.get(objet["category"])
        if encre is not None and bande:
            recales_pts = recaler(nets, encre, bande, ferme=ferme)
            if max(math.hypot(p[0] - q[0], p[1] - q[1]) for p, q in zip(nets, recales_pts)) > 0.5 \
                    if len(recales_pts) == len(nets) else True:
                recales += 1
            nets = recales_pts
        if len(nets) < (3 if ferme else 2):
            apres += len(pts)
            continue
        apres += len(nets)
        objet["points"] = [
            [round(min(1000.0, max(0.0, x / sx)), 3), round(min(1000.0, max(0.0, y / sy)), 3)] for x, y in nets
        ]
    separees = separer_espaces(objets, sx, sy)
    return {
        "pieces_separees": separees,
        "directions_deg": [round(d, 2) for d in directions],
        "sommets_avant": avant,
        "sommets_apres": apres,
        "objets_recales": recales,
    }
