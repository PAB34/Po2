"""Reconnaissance des objets d'un plan, sans calque préalable — « Tout détecter » (docs/thermique/
refondation-parcours-decisions.md §16 et §18).

Un même trait sert à plusieurs objets (essai R+2 : le 0,24 pt fait vitrages, garde-corps et marches) : on
reconnaît donc des **formes** :

- **murs** : le trait noir le plus épais du plan (coupe des murs) ;
- **portes** : l'arc de battement, souvent dessiné en **points** (segments de 0,1 pt tous les 1 à 2 pt) ou en
  petits segments ; les points sont chaînés de proche en proche, puis un cercle est cherché par tirage aléatoire
  (rayon 0,55 à 1,4 m, balayage 45 à 110°) ; le vantail est le trait qui part du centre, de la longueur du rayon ;
- **menuiseries** : au moins deux traits fins (≤ 0,3 pt) droits, parallèles, de même longueur, écartés de 12 cm
  au plus (le vitrage), et les traits plus épais parallèles de même longueur à moins de 30 cm (le cadre) ;
- **isolant** : famille de petits traits gris (« court ») logés pour l'essentiel dans l'épaisseur des murs.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict

import numpy as np
from scipy import ndimage

from thermique_moteur.calques import TRAIT
from thermique_moteur.metre import pt_en_m

POINT_MAX_PT = 0.5
PAS_POINTS_PT = 2.5
POINTS_MIN = 8
RAYON_PORTE_M = (0.55, 1.4)
BALAYAGE_DEG = (45.0, 110.0)
ECART_CERCLE_M = 0.015
TIRAGES = 300
SEGMENT_COURT_M = 0.3
VITRAGE_LARGEUR_MAX_PT = 0.3
VITRAGE_LONGUEUR_MIN_M = 0.3
VITRAGE_ECART_MAX_M = 0.12
CADRE_DISTANCE_MAX_M = 0.3
ISOLANT_DANS_MUR = 0.6
ISOLANT_ELEMENTS_MIN = 50
MUR_VOISINAGE_M = 0.3


def _largeur(signature: str) -> float:
    return float(signature.split("|")[1]) if signature.startswith("trait|") else 0.0


def _couleur(signature: str) -> str:
    return signature.split("|")[2] if signature.startswith("trait|") else ""


def _centre(e) -> tuple[float, float]:
    return ((e[3] + e[5]) / 2, (e[4] + e[6]) / 2)


def _etendue(e) -> float:
    return max(e[5] - e[3], e[6] - e[4])


def signature_murs(donnees: dict) -> str | None:
    """Le trait noir le plus épais du plan (ou le plus épais tout court s'il n'y a pas de noir)."""
    traits = [s for s in donnees["signatures"] if s.startswith("trait|")]
    if not traits:
        return None
    noirs = [s for s in traits if _couleur(s) == "#000000"] or traits
    return max(noirs, key=_largeur)


# --- Portes -------------------------------------------------------------------------------------------------


class _Unions:
    def __init__(self, cles):
        self.parent = {c: c for c in cles}

    def trouver(self, c):
        while self.parent[c] != c:
            self.parent[c] = self.parent[self.parent[c]]
            c = self.parent[c]
        return c

    def unir(self, a, b):
        ra, rb = self.trouver(a), self.trouver(b)
        if ra != rb:
            self.parent[ra] = rb


def _chaines(donnees: dict, m: float) -> list[list[int]]:
    """Chaînes d'éléments courts d'une même signature : points proches (≤ PAS_POINTS_PT) ou segments bout à bout."""
    elements = donnees["elements"]
    points = [i for i, e in enumerate(elements) if e[0] == TRAIT and _etendue(e) < POINT_MAX_PT]
    courts = [i for i, e in enumerate(elements) if e[0] == TRAIT and POINT_MAX_PT <= _etendue(e) < SEGMENT_COURT_M * m]
    unions = _Unions(points + courts)
    grille = defaultdict(list)
    for i in points:
        x, y = _centre(elements[i])
        grille[(int(x // PAS_POINTS_PT), int(y // PAS_POINTS_PT), elements[i][1])].append(i)
    for (gx, gy, s), liste in grille.items():
        for i in liste:
            ci = _centre(elements[i])
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for j in grille.get((gx + dx, gy + dy, s), ()):
                        if j > i and math.dist(_centre(elements[j]), ci) <= PAS_POINTS_PT:
                            unions.unir(i, j)
    bouts = defaultdict(list)
    for i in courts:
        c = elements[i][7]
        for x, y in ((c[0], c[1]), (c[-2], c[-1])):
            bouts[(round(x / 0.8), round(y / 0.8), elements[i][1])].append(i)
    for (bx, by, s), liste in bouts.items():
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in bouts.get((bx + dx, by + dy, s), ()):
                    unions.unir(liste[0], j)
    groupes = defaultdict(list)
    for i in points + courts:
        groupes[unions.trouver(i)].append(i)
    return list(groupes.values())


def _points_chaine(donnees: dict, chaine: list[int]) -> list[tuple[float, float]]:
    points = []
    for i in chaine:
        e = donnees["elements"][i]
        if _etendue(e) < POINT_MAX_PT:
            points.append(_centre(e))
        else:
            c = e[7]
            points += [(c[k], c[k + 1]) for k in range(0, len(c) - 1, 2)]
    return points


def _cercle_trois(a, b, c):
    d = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
    if abs(d) < 1e-6:
        return None
    ux = ((a[0] ** 2 + a[1] ** 2) * (b[1] - c[1]) + (b[0] ** 2 + b[1] ** 2) * (c[1] - a[1]) + (c[0] ** 2 + c[1] ** 2) * (a[1] - b[1])) / d
    uy = ((a[0] ** 2 + a[1] ** 2) * (c[0] - b[0]) + (b[0] ** 2 + b[1] ** 2) * (a[0] - c[0]) + (c[0] ** 2 + c[1] ** 2) * (b[0] - a[0])) / d
    return ux, uy, math.dist(a, (ux, uy))


def _moindres_carres(points):
    p = np.asarray(points, dtype=float)
    a = np.c_[2 * p, np.ones(len(p))]
    (cx, cy, k), *_ = np.linalg.lstsq(a, (p**2).sum(1), rcond=None)
    r = math.sqrt(max(k + cx * cx + cy * cy, 0.0))
    return cx, cy, r, float(np.abs(np.hypot(p[:, 0] - cx, p[:, 1] - cy) - r).max())


def _arc(points, m: float):
    """(cx, cy, r) d'un arc de porte porté par une partie des points, ou None."""
    if len(points) < POINTS_MIN:
        return None
    alea = random.Random(len(points))
    tolerance = ECART_CERCLE_M * m
    meilleur = (0, None)
    for _ in range(TIRAGES):
        cercle = _cercle_trois(*alea.sample(points, 3))
        if cercle is None or not RAYON_PORTE_M[0] * m < cercle[2] < RAYON_PORTE_M[1] * m:
            continue
        n = sum(1 for p in points if abs(math.dist(p, cercle[:2]) - cercle[2]) < tolerance)
        if n > meilleur[0]:
            meilleur = (n, cercle)
    if meilleur[1] is None:
        return None
    cx, cy, r = meilleur[1]
    portes = [p for p in points if abs(math.dist(p, (cx, cy)) - r) < tolerance]
    if len(portes) < POINTS_MIN or len(portes) < 0.4 * len(points):
        return None
    cx, cy, r, ecart = _moindres_carres(portes)
    if not (RAYON_PORTE_M[0] * m < r < RAYON_PORTE_M[1] * m) or ecart > 2 * tolerance:
        return None
    angles = sorted(math.atan2(y - cy, x - cx) for x, y in portes)
    trous = [b - a for a, b in zip(angles, angles[1:])] + [angles[0] + 2 * math.pi - angles[-1]]
    balayage = math.degrees(2 * math.pi - max(trous))
    return (cx, cy, r) if BALAYAGE_DEG[0] <= balayage <= BALAYAGE_DEG[1] else None


def portes(donnees: dict) -> list[dict]:
    """Portes : éléments de l'arc et du vantail, centre et rayon (points PDF)."""
    m = 1 / pt_en_m(donnees["echelle"])
    elements = donnees["elements"]
    trouvees = []
    for chaine in _chaines(donnees, m):
        if len(chaine) < 3:
            continue
        arc = _arc(_points_chaine(donnees, chaine), m)
        if arc is None:
            continue
        cx, cy, r = arc
        vantail = []
        for j, e in enumerate(elements):
            if e[0] != TRAIT or e[5] < cx - r * 1.2 or e[3] > cx + r * 1.2 or e[6] < cy - r * 1.2 or e[4] > cy + r * 1.2:
                continue
            if _etendue(e) < POINT_MAX_PT:
                continue
            c = e[7]
            a, b = (c[0], c[1]), (c[-2], c[-1])
            if min(math.dist(a, (cx, cy)), math.dist(b, (cx, cy))) < 0.06 * m and abs(math.dist(a, b) - r) < 0.15 * r:
                vantail.append(j)
        trouvees.append({"elements": sorted(set(chaine) | set(vantail)), "centre": [cx, cy], "rayon": r})
    return trouvees


# --- Menuiseries --------------------------------------------------------------------------------------------


def _droite(c):
    x1, y1, x2, y2 = c[:4]
    longueur = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / longueur, (y2 - y1) / longueur
    if ux < 0 or (ux == 0 and uy < 0):
        ux, uy = -ux, -uy
    return ((x1 + x2) / 2, (y1 + y2) / 2, longueur, ux, uy)


def menuiseries(donnees: dict, exclus: set[int] = frozenset()) -> list[list[int]]:
    """Groupes d'éléments (vitrage + cadre), un groupe par menuiserie."""
    m = 1 / pt_en_m(donnees["echelle"])
    signatures, elements = donnees["signatures"], donnees["elements"]

    def droit(i, minimum):
        e = elements[i]
        return e[0] == TRAIT and e[2] == "droit" and i not in exclus and math.dist(e[7][:2], e[7][2:4]) >= minimum

    fins = [i for i in range(len(elements)) if droit(i, VITRAGE_LONGUEUR_MIN_M * m) and _largeur(signatures[elements[i][1]]) <= VITRAGE_LARGEUR_MAX_PT]
    geo = {i: _droite(elements[i][7]) for i in fins}
    # voisinage par cases d'un mètre pour éviter de tout comparer à tout
    cases = defaultdict(list)
    for i in fins:
        cases[(int(geo[i][0] // m), int(geo[i][1] // m))].append(i)
    vus, groupes = set(), []
    for i in fins:
        if i in vus:
            continue
        mx, my, longueur, ux, uy = geo[i]
        groupe = [i]
        cx, cy = int(mx // m), int(my // m)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in cases.get((cx + dx, cy + dy), ()):
                    if j == i or j in vus:
                        continue
                    nx, ny, lj, vx, vy = geo[j]
                    if abs(ux * vy - uy * vx) > 0.01 or abs(longueur - lj) > 0.05 * longueur:
                        continue
                    ecart = abs((nx - mx) * -uy + (ny - my) * ux)
                    if ecart <= VITRAGE_ECART_MAX_M * m and math.dist((nx, ny), (mx, my)) <= ecart + 0.05 * m:
                        groupe.append(j)
        if len(groupe) >= 2:
            vus.update(groupe)
            groupes.append(groupe)
    # cadres
    epais = [i for i in range(len(elements)) if droit(i, VITRAGE_LONGUEUR_MIN_M * m) and 0.3 < _largeur(signatures[elements[i][1]]) < 1.0]
    geo_epais = {i: _droite(elements[i][7]) for i in epais}
    cases_epais = defaultdict(list)
    for i in epais:
        cases_epais[(int(geo_epais[i][0] // m), int(geo_epais[i][1] // m))].append(i)
    resultat = []
    for groupe in groupes:
        mx, my, longueur, ux, uy = geo[groupe[0]]
        cadre = []
        cx, cy = int(mx // m), int(my // m)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in cases_epais.get((cx + dx, cy + dy), ()):
                    nx, ny, lj, vx, vy = geo_epais[j]
                    if abs(ux * vy - uy * vx) < 0.01 and abs(longueur - lj) < 0.08 * longueur and math.dist((nx, ny), (mx, my)) < CADRE_DISTANCE_MAX_M * m:
                        cadre.append(j)
        resultat.append(sorted(set(groupe) | set(cadre)))
    return resultat


# --- Isolant ------------------------------------------------------------------------------------------------


def _part_parallele(donnees: dict, indices: list[int]) -> float:
    """Part des éléments dont la direction est celle de la majorité (une hachure est tous ses traits parallèles,
    un isolant fait des zigzags)."""
    angles = []
    for i in indices:
        c = donnees["elements"][i][7]
        if len(c) >= 4:
            angles.append(math.degrees(math.atan2(c[-1] - c[1], c[-2] - c[0])) % 180)
    if not angles:
        return 0.0
    paquets = defaultdict(int)
    for angle in angles:
        paquets[round(angle / 8)] += 1
    return max(paquets.values()) / len(angles)


PART_PARALLELE_HACHURE = 0.75


def familles_isolant(donnees: dict, murs: list[int]) -> tuple[list[str], list[str]]:
    """(isolants, hachures) : familles de petits traits gris logées dans les murs, séparées par leur direction —
    une hachure de mur est faite de traits parallèles, un isolant de zigzags."""
    if not murs:
        return [], []
    from thermique_moteur.pieces import grille_des_elements, image_limites

    grille = grille_des_elements(donnees, murs)
    voisinage = ndimage.binary_dilation(
        image_limites(donnees, murs, grille), iterations=max(1, int(round(MUR_VOISINAGE_M / 0.05)))
    )
    par_signature = defaultdict(list)
    for i, e in enumerate(donnees["elements"]):
        s = donnees["signatures"][e[1]]
        if e[0] == TRAIT and e[2] == "court" and _couleur(s) not in ("#000000", ""):
            par_signature[s].append(i)
    isolants, hachures = [], []
    for s, indices in par_signature.items():
        if len(indices) < ISOLANT_ELEMENTS_MIN:
            continue
        dedans = 0
        for i in indices:
            c, l = (int(v) for v in grille.pixel(*_centre(donnees["elements"][i])))
            if 0 <= l < voisinage.shape[0] and 0 <= c < voisinage.shape[1] and voisinage[l, c]:
                dedans += 1
        if dedans < ISOLANT_DANS_MUR * len(indices):
            continue
        (hachures if _part_parallele(donnees, indices) >= PART_PARALLELE_HACHURE else isolants).append(s)
    return isolants, hachures
