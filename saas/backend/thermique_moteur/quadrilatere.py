"""Un local est un quadrilatère — règle des 98 % (docs/thermique/parois-et-motifs-decisions.md §0.6).

Un local courant a quatre côtés, et il est rectangulaire la plupart du temps. Un contour relevé sur le
dessin, lui, arrive avec des dizaines de sommets : les tableaux des portes, les redans du mobilier, et
les zigzags laissés là où le tracé s'est échappé par une baie.

On ne retient donc que les **grandes droites** du contour : les côtés sont regroupés par droite support,
les quatre groupes les plus longs sont conservés, et leurs intersections donnent les quatre coins. Le
détail disparaît, la géométrie utile reste — et les côtés obtenus sont portés par de vrais traits du plan,
pas par une moyenne.

Le contour d'origine n'est jamais perdu : un local en L ou en U se rend tel quel (`simplifier` refuse
quand les quatre droites ne décrivent pas l'essentiel du périmètre).
"""
from __future__ import annotations

import math

TOLERANCE_ANGLE_DEG = 10.0
TOLERANCE_ECART_M = 0.35
TOLERANCE_ZIGZAG_M = 0.15
PART_PERIMETRE_MIN = 0.55
ECART_SURFACE_MAX = 0.18
ECART_SURFACE_NETTOYAGE_MAX = 0.08


class QuadrilatereError(Exception):
    """Ce contour ne se ramène pas à quatre côtés."""


def _cotes(contour: list[float]) -> list[tuple]:
    points = _points(contour)
    return list(zip(points, points[1:] + points[:1]))


def _points(contour: list[float]) -> list[tuple[float, float]]:
    if len(contour) % 2:
        raise QuadrilatereError("Le contour contient une coordonnée incomplète.")
    points = [(float(contour[k]), float(contour[k + 1])) for k in range(0, len(contour), 2)]
    while len(points) > 1 and points[-1] == points[0]:
        points.pop()
    return points


def aire(points: list[tuple]) -> float:
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))) / 2


def _orientation(a: tuple, b: tuple, c: tuple) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _sur_segment(a: tuple, b: tuple, p: tuple, epsilon: float = 1e-7) -> bool:
    return (
        abs(_orientation(a, b, p)) <= epsilon
        and min(a[0], b[0]) - epsilon <= p[0] <= max(a[0], b[0]) + epsilon
        and min(a[1], b[1]) - epsilon <= p[1] <= max(a[1], b[1]) + epsilon
    )


def _segments_se_coupent(a: tuple, b: tuple, c: tuple, d: tuple) -> bool:
    o1, o2 = _orientation(a, b, c), _orientation(a, b, d)
    o3, o4 = _orientation(c, d, a), _orientation(c, d, b)
    if (o1 > 0 > o2 or o2 > 0 > o1) and (o3 > 0 > o4 or o4 > 0 > o3):
        return True
    return any((_sur_segment(a, b, c), _sur_segment(a, b, d), _sur_segment(c, d, a), _sur_segment(c, d, b)))


def _est_simple(points: list[tuple]) -> bool:
    cotes = list(zip(points, points[1:] + points[:1]))
    for i, (a, b) in enumerate(cotes):
        for j in range(i + 1, len(cotes)):
            if j in {i, i + 1} or (i == 0 and j == len(cotes) - 1):
                continue
            if _segments_se_coupent(a, b, *cotes[j]):
                return False
    return True


def _droites(contour: list[float], m: float) -> list[dict]:
    """Côtés regroupés par droite support, du groupe le plus long au plus court."""
    groupes: list[dict] = []
    for a, b in _cotes(contour):
        longueur = math.dist(a, b)
        if longueur <= 0:
            continue
        ux, uy = (b[0] - a[0]) / longueur, (b[1] - a[1]) / longueur
        if ux < 0 or (ux == 0 and uy < 0):
            ux, uy = -ux, -uy
        place = None
        for groupe in groupes:
            vx, vy = groupe["u"]
            if abs(ux * vx + uy * vy) < math.cos(math.radians(TOLERANCE_ANGLE_DEG)):
                continue
            # même droite : l'écart perpendiculaire au milieu du côté reste faible
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            if abs((mx - groupe["point"][0]) * -vy + (my - groupe["point"][1]) * vx) <= TOLERANCE_ECART_M * m:
                place = groupe
                break
        if place is None:
            groupes.append(
                {
                    "u": (ux, uy),
                    "point": ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2),
                    "longueur": longueur,
                    "max_longueur": longueur,
                }
            )
        else:
            # la droite du groupe suit le côté le plus long qu'il contient
            if longueur > place["max_longueur"]:
                place["u"] = (ux, uy)
                place["point"] = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                place["max_longueur"] = longueur
            place["longueur"] += longueur
    groupes.sort(key=lambda g: -g["longueur"])
    return groupes


def _intersection(d1: dict, d2: dict) -> tuple | None:
    (x1, y1), (ux, uy) = d1["point"], d1["u"]
    (x2, y2), (vx, vy) = d2["point"], d2["u"]
    det = ux * vy - uy * vx
    if abs(det) < 1e-9:
        return None
    t = ((x2 - x1) * vy - (y2 - y1) * vx) / det
    return (x1 + ux * t, y1 + uy * t)


def simplifier(contour: list[float], m: float) -> list[float]:
    """Contour ramené à quatre côtés, portés par ses quatre droites les plus longues.

    Lève `QuadrilatereError` quand le local n'en est pas un : moins de quatre directions franches, des
    droites qui ne se coupent pas, ou une surface trop éloignée de celle du contour d'origine (un local
    en L, par exemple, que l'on garde alors tel quel).
    """
    points = _points(contour)
    if len(points) < 3:
        raise QuadrilatereError("Ce contour n'a pas assez de points.")
    if not _est_simple(points):
        raise QuadrilatereError("Ce contour se croise lui-même.")
    groupes = _droites(contour, m)
    if len(groupes) < 4:
        raise QuadrilatereError("Ce contour n'a pas quatre directions franches.")
    retenues = groupes[:4]
    perimetre = sum(math.dist(a, b) for a, b in _cotes(contour))
    if sum(g["longueur"] for g in retenues) < PART_PERIMETRE_MIN * perimetre:
        raise QuadrilatereError("Les quatre plus grands côtés ne font pas le tour de ce local.")

    centre = (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))
    # on ordonne les droites autour du centre, par l'angle du pied de la perpendiculaire
    def angle(groupe):
        ux, uy = groupe["u"]
        px, py = groupe["point"]
        ecart = (px - centre[0]) * -uy + (py - centre[1]) * ux
        return math.atan2(-uy * ecart, ux * ecart) if ecart else math.atan2(uy, ux)

    retenues.sort(key=angle)
    coins = []
    for k in range(4):
        point = _intersection(retenues[k], retenues[(k + 1) % 4])
        if point is None:
            raise QuadrilatereError("Deux côtés de ce local sont parallèles : il n'a pas quatre coins.")
        coins.append(point)
    if len({(round(p[0], 3), round(p[1], 3)) for p in coins}) < 4:
        raise QuadrilatereError("Les quatre côtés ne donnent pas quatre coins distincts.")
    if not _est_simple(coins):
        raise QuadrilatereError("Les quatre côtés donnent un contour croisé.")
    marge = max(m, TOLERANCE_ECART_M * m)
    min_x, max_x = min(p[0] for p in points) - marge, max(p[0] for p in points) + marge
    min_y, max_y = min(p[1] for p in points) - marge, max(p[1] for p in points) + marge
    if any(not (min_x <= x <= max_x and min_y <= y <= max_y) for x, y in coins):
        raise QuadrilatereError("Les quatre côtés se rencontrent trop loin du contour relevé.")
    surface = aire(coins)
    depart = aire(points)
    if depart <= 0:
        raise QuadrilatereError("Ce contour est dégénéré.")
    if abs(surface - depart) > ECART_SURFACE_MAX * depart:
        raise QuadrilatereError("Ce local n'est pas un quadrilatère : sa forme s'en écarte trop.")
    return [c for point in coins for c in point]


def _distance_segment(point: tuple, a: tuple, b: tuple) -> float:
    longueur2 = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2
    if longueur2 == 0:
        return math.dist(point, a)
    t = max(0.0, min(1.0, ((point[0] - a[0]) * (b[0] - a[0]) + (point[1] - a[1]) * (b[1] - a[1])) / longueur2))
    projection = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
    return math.dist(point, projection)


def _rdp(points: list[tuple], tolerance: float) -> list[tuple]:
    if len(points) <= 2:
        return points
    distances = [_distance_segment(point, points[0], points[-1]) for point in points[1:-1]]
    maximum = max(distances, default=0.0)
    if maximum <= tolerance:
        return [points[0], points[-1]]
    index = distances.index(maximum) + 1
    return _rdp(points[: index + 1], tolerance)[:-1] + _rdp(points[index:], tolerance)


def _nettoyer_points(points: list[tuple], tolerance: float) -> list[tuple]:
    """Douglas-Peucker sur un anneau, coupé entre ses deux sommets les plus éloignés."""
    sans_doublons: list[tuple] = []
    for point in points:
        if not sans_doublons or math.dist(point, sans_doublons[-1]) > tolerance / 5:
            sans_doublons.append(point)
    if len(sans_doublons) > 1 and math.dist(sans_doublons[0], sans_doublons[-1]) <= tolerance / 5:
        sans_doublons.pop()
    if len(sans_doublons) <= 3:
        return sans_doublons
    i, j = max(
        ((i, j) for i in range(len(sans_doublons)) for j in range(i + 1, len(sans_doublons))),
        key=lambda pair: math.dist(sans_doublons[pair[0]], sans_doublons[pair[1]]),
    )
    arc1 = sans_doublons[i : j + 1]
    arc2 = sans_doublons[j:] + sans_doublons[: i + 1]
    return _rdp(arc1, tolerance)[:-1] + _rdp(arc2, tolerance)[:-1]


def simplifier_adaptatif(contour: list[float], m: float) -> list[float]:
    """Quadrilatère si la preuve est solide, sinon simple retrait des petits zigzags.

    La seconde voie conserve les vrais changements de direction d'un grand espace en L ou en U.
    Si les garde-fous échouent, le contour détaillé d'origine est renvoyé sans modification.
    """
    points = _points(contour)
    if len(points) < 3 or not _est_simple(points) or aire(points) <= 0:
        raise QuadrilatereError("Ce contour est invalide.")
    try:
        return simplifier(contour, m)
    except QuadrilatereError:
        pass
    nettoyes = _nettoyer_points(points, TOLERANCE_ZIGZAG_M * m)
    if len(nettoyes) < 3 or len(nettoyes) >= len(points) or not _est_simple(nettoyes):
        return list(contour)
    depart, arrivee = aire(points), aire(nettoyes)
    if abs(arrivee - depart) > ECART_SURFACE_NETTOYAGE_MAX * depart:
        return list(contour)
    return [c for point in nettoyes for c in point]
