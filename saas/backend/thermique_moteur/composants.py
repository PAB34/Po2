"""Ce qui borde un local — étape 3 du parcours (docs/thermique/parois-et-motifs-decisions.md §0.6).

Pour calculer les déperditions d'un local, on n'a pas besoin de reconnaître tout le plan : il faut savoir,
**côté par côté**, ce qui borde ce local-là et ce qu'il y a derrière. C'est une question locale, et c'est
pour cela qu'elle se règle sans détection parfaite en amont.

On relève donc les éléments du dessin **collés au contour** (à `CONTACT_M` près), regroupés par famille
graphique, avec la **longueur de contact** de chacune. L'utilisateur nomme une famille une fois — mur
extérieur, menuiserie, cloison vers un local non chauffé — et la réponse vaut pour tous ses exemplaires,
ici et dans les locaux jumeaux.
"""
from __future__ import annotations

import math
from collections import defaultdict

from thermique_moteur.calques import TRAIT
from thermique_moteur.metre import pt_en_m

CONTACT_M = 0.35
PAS_ECHANTILLON_M = 0.05
PART_LONGEE_MIN = 0.4
PART_COTE_MIN = 0.25


def _cotes(contour: list[float]) -> list[tuple]:
    points = [(contour[k], contour[k + 1]) for k in range(0, len(contour) - 1, 2)]
    return list(zip(points, points[1:] + points[:1]))


def _distance_au_cote(point: tuple, a: tuple, b: tuple) -> float:
    vx, vy = b[0] - a[0], b[1] - a[1]
    carre = vx * vx + vy * vy
    t = 0.0 if carre == 0 else max(0.0, min(1.0, ((point[0] - a[0]) * vx + (point[1] - a[1]) * vy) / carre))
    return math.dist(point, (a[0] + vx * t, a[1] + vy * t))


def _echantillons(element, pas: float) -> list[tuple]:
    """Points régulièrement espacés le long d'un trait, pour mesurer sa longueur de contact."""
    c = element[7]
    points = []
    for k in range(0, len(c) - 3, 2):
        a, b = (c[k], c[k + 1]), (c[k + 2], c[k + 3])
        longueur = math.dist(a, b)
        n = max(1, int(longueur / pas))
        for j in range(n + 1):
            t = j / n
            points.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return points


def bordant(donnees: dict, contour: list[float], natures: dict[int, str] | None = None) -> list[dict]:
    """Familles d'éléments collées au contour, avec leur longueur de contact et leur côté.

    `natures` donne, pour les éléments déjà rangés dans un calque, la nature connue — elle est rendue
    telle quelle, pour que l'utilisateur n'ait à se prononcer que sur ce qui reste.
    """
    m = 1 / pt_en_m(donnees["echelle"])
    contact = CONTACT_M * m
    pas = PAS_ECHANTILLON_M * m
    cotes = _cotes(contour)
    if not cotes:
        return []
    xs = [p[0] for cote in cotes for p in cote]
    ys = [p[1] for cote in cotes for p in cote]
    boite = (min(xs) - contact, min(ys) - contact, max(xs) + contact, max(ys) + contact)

    familles: dict[tuple, dict] = defaultdict(
        lambda: {"elements": [], "longueur": 0.0, "cotes": set(), "natures": set()}
    )
    for i, e in enumerate(donnees["elements"]):
        if e[0] != TRAIT or e[5] < boite[0] or e[3] > boite[2] or e[6] < boite[1] or e[4] > boite[3]:
            continue
        points = _echantillons(e, pas)
        if not points:
            continue
        longes, par_cote = 0, defaultdict(int)
        for point in points:
            for rang, (a, b) in enumerate(cotes):
                if _distance_au_cote(point, a, b) <= contact:
                    longes += 1
                    par_cote[rang] += 1
                    break
        # un élément qui ne fait qu'effleurer le contour n'est pas une paroi de ce local
        if longes < PART_LONGEE_MIN * len(points):
            continue
        # un côté n'est retenu que s'il est vraiment longé : sinon, tous les voisins d'un coin
        # compteraient pour les deux côtés qui s'y rejoignent
        touches = {rang for rang, n in par_cote.items() if n >= PART_COTE_MIN * longes}
        cle = (donnees["signatures"][e[1]], e[2])
        famille = familles[cle]
        famille["elements"].append(i)
        famille["longueur"] += longes / len(points) * sum(
            math.dist((e[7][k], e[7][k + 1]), (e[7][k + 2], e[7][k + 3])) for k in range(0, len(e[7]) - 3, 2)
        )
        famille["cotes"].update(touches)
        if natures and i in natures:
            famille["natures"].add(natures[i])

    par_m = pt_en_m(donnees["echelle"])
    resultat = []
    for (signature, forme), famille in familles.items():
        resultat.append(
            {
                "signature": signature,
                "forme": forme,
                "elements": sorted(famille["elements"]),
                "nombre": len(famille["elements"]),
                "longueur_m": round(famille["longueur"] * par_m, 2),
                "cotes": sorted(famille["cotes"]),
                "nature": sorted(famille["natures"])[0] if len(famille["natures"]) == 1 else None,
            }
        )
    resultat.sort(key=lambda f: -f["longueur_m"])
    return resultat


def longueurs_des_cotes(donnees: dict, contour: list[float]) -> list[float]:
    """Longueur de chaque côté du local, en mètres — la base du métré des parois."""
    par_m = pt_en_m(donnees["echelle"])
    return [round(math.dist(a, b) * par_m, 2) for a, b in _cotes(contour)]
