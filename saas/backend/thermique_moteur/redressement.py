"""Redressement des lignes calculées sur image : chaque côté est reposé sur la face vectorielle du PDF qui le
porte (docs/thermique/refondation-parcours-decisions.md §17).

Les contours des pièces et de l'enveloppe suivent l'escalier des pixels (5 cm) : après simplification, les
côtés « hésitent » autour des vraies faces (retour de l'utilisateur sur l'essai R+2). Ici :

1. le contour est simplifié plus franchement (`TOLERANCE_SIMPLIFICATION_M`) pour garder les vrais côtés ;
2. chaque côté est accroché à la droite du segment-limite parallèle (± `ANGLE_MAX_DEG`) le plus proche
   (≤ `DISTANCE_MAX_M`) qui le recouvre assez ;
3. les côtés consécutifs accrochés à la même droite sont fusionnés ;
4. les sommets sont les intersections des côtés voisins ;
5. si la surface change de plus de `ECART_SURFACE_MAX`, le contour d'origine est gardé.
"""
from __future__ import annotations

import math

import numpy as np

TOLERANCE_SIMPLIFICATION_M = 0.08
# là où aucune face ne porte la ligne (éléments répétés, pointillés, bord de terrasse) : côtés droits à 25 cm près
TOLERANCE_SANS_FACE_M = 0.25
DISTANCE_MAX_M = 0.12
ANGLE_MAX_DEG = 6.0
RECOUVREMENT_MIN = 0.3
LONGUEUR_SEGMENT_MIN_M = 0.15
ECART_SURFACE_MAX = 0.05


def segments_des_elements(donnees: dict, indices: list[int], m_par_pt: float) -> np.ndarray:
    """Segments droits (x1, y1, x2, y2) des éléments-limites, d'au moins `LONGUEUR_SEGMENT_MIN_M`."""
    minimum = LONGUEUR_SEGMENT_MIN_M / m_par_pt
    lignes = []
    for index in indices:
        c = donnees["elements"][index][7]
        for k in range(0, len(c) - 3, 2):
            if math.hypot(c[k + 2] - c[k], c[k + 3] - c[k + 1]) >= minimum:
                lignes.append(c[k : k + 4])
    return np.asarray(lignes, dtype=float).reshape(-1, 4)


def _aire(points) -> float:
    return abs(sum(points[k - 1][0] * points[k][1] - points[k][0] * points[k - 1][1] for k in range(len(points)))) / 2


def _simplifier(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    from thermique_moteur.pieces import simplifier

    return simplifier(points, tolerance)


def _accrocher(a, b, segments: np.ndarray, distance_max: float):
    """Droite (point, direction unitaire) du segment qui porte le côté a-b, ou None."""
    if len(segments) == 0:
        return None
    ax, ay = a
    bx, by = b
    longueur = math.hypot(bx - ax, by - ay)
    if longueur <= 0:
        return None
    ux, uy = (bx - ax) / longueur, (by - ay) / longueur
    sx1, sy1, sx2, sy2 = segments.T
    sl = np.hypot(sx2 - sx1, sy2 - sy1)
    vx, vy = (sx2 - sx1) / sl, (sy2 - sy1) / sl
    parallele = np.abs(ux * vy - uy * vx) <= math.sin(math.radians(ANGLE_MAX_DEG))
    # distance du milieu du côté à la droite du segment
    mx, my = (ax + bx) / 2, (ay + by) / 2
    distance = np.abs((mx - sx1) * vy - (my - sy1) * vx)
    proche = parallele & (distance <= distance_max)
    if not proche.any():
        return None
    # recouvrement le long du côté
    t1 = (sx1 - ax) * ux + (sy1 - ay) * uy
    t2 = (sx2 - ax) * ux + (sy2 - ay) * uy
    recouvrement = np.clip(np.minimum(np.maximum(t1, t2), longueur) - np.maximum(np.minimum(t1, t2), 0), 0, None)
    # le segment le plus proche parmi ceux qui recouvrent assez le côté (ou qu'il recouvre en entier)
    assez = proche & ((recouvrement >= RECOUVREMENT_MIN * longueur) | (recouvrement >= 0.9 * sl))
    if not assez.any():
        return None
    # à distance quasi égale, le plus long recouvrement l'emporte
    score = np.where(assez, distance - 1e-3 * recouvrement, np.inf)
    k = int(np.argmin(score))
    # direction du segment, orientée comme le côté
    dx, dy = vx[k], vy[k]
    if dx * ux + dy * uy < 0:
        dx, dy = -dx, -dy
    # la droite passe par le segment, on la repère par son point le plus proche du côté
    px = sx1[k] + ((mx - sx1[k]) * dx + (my - sy1[k]) * dy) * dx
    py = sy1[k] + ((mx - sx1[k]) * dx + (my - sy1[k]) * dy) * dy
    return (px, py, dx, dy)


def _intersection(d1, d2):
    px, py, ux, uy = d1
    qx, qy, vx, vy = d2
    det = ux * vy - uy * vx
    if abs(det) < math.sin(math.radians(ANGLE_MAX_DEG)):
        return None
    t = ((qx - px) * vy - (qy - py) * vx) / det
    return (px + t * ux, py + t * uy)


def _lisser_sans_face(base: list, segments: np.ndarray, m_par_pt: float) -> list:
    """Simplifie plus franchement les suites de côtés qu'aucune face ne porte (les côtés accrochés restent)."""
    from thermique_moteur.pieces import _dp

    n = len(base)
    distance = DISTANCE_MAX_M / m_par_pt
    porte = [_accrocher(base[k], base[(k + 1) % n], segments, distance) is not None for k in range(n)]
    if all(porte):
        return base
    if not any(porte):
        return _simplifier(base, TOLERANCE_SANS_FACE_M / m_par_pt)
    # on commence juste après un côté accroché : le dernier côté parcouru est donc accroché, et chaque suite de
    # sommets se termine au départ d'un côté accroché
    depart = (porte.index(True) + 1) % n
    ordre = base[depart:] + base[:depart]
    drapeaux = porte[depart:] + porte[:depart]
    tolerance = TOLERANCE_SANS_FACE_M / m_par_pt
    resultat, suite = [], [ordre[0]]
    for k in range(n):
        if drapeaux[k]:
            resultat += _dp(suite, tolerance) if len(suite) >= 2 else suite
            suite = [ordre[(k + 1) % n]]
        else:
            suite.append(ordre[(k + 1) % n])
    return resultat


def redresser(points: list[tuple[float, float]], segments: np.ndarray, m_par_pt: float) -> list[tuple[float, float]]:
    """Contour fermé redressé sur les segments (points PDF) ; le contour simplifié s'il n'y a rien à accrocher."""
    base = _simplifier([(float(x), float(y)) for x, y in points], TOLERANCE_SIMPLIFICATION_M / m_par_pt)
    if len(base) >= 3:
        lisse = _lisser_sans_face(base, segments, m_par_pt)
        if len(lisse) >= 3:
            base = lisse
    n = len(base)
    if n < 3:
        return list(points)
    droites = []
    for k in range(n):
        a, b = base[k], base[(k + 1) % n]
        droite = _accrocher(a, b, segments, DISTANCE_MAX_M / m_par_pt)
        if droite is None:
            longueur = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
            droite = (a[0], a[1], (b[0] - a[0]) / longueur, (b[1] - a[1]) / longueur)
            accroche = False
        else:
            accroche = True
        droites.append((droite, accroche, a, b))
    # fusion des côtés consécutifs portés par la même droite
    fusion = []
    for droite, accroche, a, b in droites:
        if fusion and accroche and fusion[-1][1]:
            px, py, ux, uy = fusion[-1][0]
            qx, qy, vx, vy = droite
            if abs(ux * vy - uy * vx) < 1e-6 and abs((qx - px) * uy - (qy - py) * ux) < 0.5:
                fusion[-1] = (fusion[-1][0], True, fusion[-1][2], b)
                continue
        fusion.append((droite, accroche, a, b))
    if len(fusion) > 1 and fusion[0][1] and fusion[-1][1]:
        px, py, ux, uy = fusion[-1][0]
        qx, qy, vx, vy = fusion[0][0]
        if abs(ux * vy - uy * vx) < 1e-6 and abs((qx - px) * uy - (qy - py) * ux) < 0.5:
            fusion[0] = (fusion[0][0], True, fusion[-1][2], fusion[0][3])
            fusion.pop()
    m = len(fusion)
    if m < 3:
        return base
    sommets = []
    for k in range(m):
        precedente, suivante = fusion[k - 1][0], fusion[k][0]
        point = _intersection(precedente, suivante)
        if point is None:
            # deux côtés quasi alignés mais décalés : on garde le sommet d'origine, projeté sur le côté suivant
            ax, ay = fusion[k][2]
            px, py, ux, uy = suivante
            t = (ax - px) * ux + (ay - py) * uy
            point = (px + t * ux, py + t * uy)
        sommets.append(point)
    # garde-fous : un angle qui s'envole (intersection lointaine) ou une surface qui change trop → contour simplifié
    etendue = max(max(p[0] for p in base) - min(p[0] for p in base), max(p[1] for p in base) - min(p[1] for p in base))
    xmin, ymin = min(p[0] for p in base) - 0.1 * etendue, min(p[1] for p in base) - 0.1 * etendue
    xmax, ymax = max(p[0] for p in base) + 0.1 * etendue, max(p[1] for p in base) + 0.1 * etendue
    if any(not (xmin <= x <= xmax and ymin <= y <= ymax) for x, y in sommets):
        return base
    aire = _aire(base)
    if aire <= 0 or abs(_aire(sommets) - aire) / aire > ECART_SURFACE_MAX:
        return base
    return [(float(x), float(y)) for x, y in sommets]
