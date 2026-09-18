"""Parois lues comme des paires de faces (docs/thermique/parois-et-motifs-decisions.md, D4 et D5).

Un mur n'est pas un motif recopié — chaque mur a sa longueur — mais il a toujours **deux faces
parallèles**. On n'essaie donc pas de deviner qu'un trait « est un mur » : on apparie les faces, et ce
qu'on rend est une paroi qui porte son **épaisseur**, sa **longueur** et ses **deux côtés**, c'est-à-dire
ce dont le thermicien a besoin.

Deux faces forment une paroi si elles sont parallèles (à `ANGLE_MAX_DEG` près), écartées d'une épaisseur
plausible et si elles se font face sur une longueur suffisante. Une face peut avoir plusieurs partenaires
(un mur avec son doublage) : on garde celui qui la couvre le plus.

Garde-fou (D5) : une face de mur a **un** vis-à-vis — celui d'en face — tandis qu'un trait de quadrillage
en a autant que la trame compte de lignes à portée. Mesuré sur le R+1 : 0,8 vis-à-vis par face pour la
plume des cloisons et 2,4 pour celle des murs, contre **15,1** pour la trame. Au-delà de
`VIS_A_VIS_MAX`, ces traits ne dessinent pas des parois et on refuse de les mesurer.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict

from thermique_moteur.calques import TRAIT
from thermique_moteur.metre import pt_en_m

SEGMENT_MIN_M = 0.25
LONGUEUR_MIN_M = 0.6
EPAISSEUR_M = (0.04, 0.70)
ANGLE_MAX_DEG = 2.0
COLINEAIRE_ECART_M = 0.03
BAIE_MAX_M = 6.0
RECOUVREMENT_MIN = 0.5
VIS_A_VIS_MAX = 5.0


class ParoisError(Exception):
    """Ce que le plan ne permet pas de mesurer."""


class _Unions:
    def __init__(self, n: int):
        self.p = list(range(n))

    def trouver(self, a: int) -> int:
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def unir(self, a: int, b: int) -> None:
        ra, rb = self.trouver(a), self.trouver(b)
        if ra != rb:
            self.p[ra] = rb


def _brins(donnees: dict, indices: list[int], m: float) -> list[tuple]:
    """Segments droits élémentaires, orientés dans le demi-plan des directions positives."""
    minimum = SEGMENT_MIN_M * m
    elements = donnees["elements"]
    brins = []
    for i in indices:
        e = elements[i]
        if e[0] != TRAIT:
            continue
        c = e[7]
        for k in range(0, len(c) - 3, 2):
            x1, y1, x2, y2 = c[k], c[k + 1], c[k + 2], c[k + 3]
            longueur = math.hypot(x2 - x1, y2 - y1)
            if longueur < minimum:
                continue
            ux, uy = (x2 - x1) / longueur, (y2 - y1) / longueur
            if ux < 0 or (ux == 0 and uy < 0):
                ux, uy, x1, y1, x2, y2 = -ux, -uy, x2, y2, x1, y1
            brins.append((i, x1, y1, x2, y2, longueur, ux, uy, -x1 * uy + y1 * ux))
    return brins


def faces(donnees: dict, indices: list[int]) -> list[dict]:
    """Faces candidates : les segments droits des éléments désignés.

    On ne recoud rien ici. Une façade est coupée par ses fenêtres en morceaux courts, mais chacun est
    une vraie face : c'est **après** l'appariement qu'on les recoud (`chainer`), quand on sait que le
    morceau est bien une paroi et non un trait qui traverse le vide.
    """
    m = 1 / pt_en_m(donnees["echelle"])
    return [
        {
            "element": b[0],
            "a": (b[1], b[2]),
            "b": (b[3], b[4]),
            "longueur": b[5],
            "u": (b[6], b[7]),
        }
        for b in _brins(donnees, indices, m)
    ]


def chainer(paires: list[dict], m: float) -> list[dict]:
    """Parois colinéaires de même épaisseur réunies ; les trous laissés entre elles sont les **baies**.

    Une façade percée de fenêtres donne d'abord un trumeau par plein ; recousus, ils redonnent la
    façade entière et la liste de ses baies (décision D7). Deux parois séparées de plus de
    `BAIE_MAX_M` restent deux murs distincts.
    """
    if not paires:
        return []
    pas_d = COLINEAIRE_ECART_M * m
    familles = defaultdict(list)
    for paroi in paires:
        x1, y1, x2, y2 = paroi["axe"]
        longueur = math.hypot(x2 - x1, y2 - y1) or 1.0
        ux, uy = (x2 - x1) / longueur, (y2 - y1) / longueur
        if ux < 0 or (ux == 0 and uy < 0):
            ux, uy, x1, y1, x2, y2 = -ux, -uy, x2, y2, x1, y1
        cle = (
            round(math.degrees(math.atan2(uy, ux)) / ANGLE_MAX_DEG),
            round((-x1 * uy + y1 * ux) / pas_d),
            round(paroi["epaisseur"] / m * 100),
        )
        familles[cle].append((paroi, (x1, y1), (ux, uy)))
    chainees = []
    for liste in familles.values():
        (_, origine, direction) = liste[0]
        ox, oy = origine
        ux, uy = direction
        bouts = []
        for paroi, (x1, y1), _ in liste:
            x2, y2 = paroi["axe"][2], paroi["axe"][3]
            t = sorted(((x1 - ox) * ux + (y1 - oy) * uy, (x2 - ox) * ux + (y2 - oy) * uy))
            bouts.append((t[0], t[1], paroi))
        bouts.sort(key=lambda b: (b[0], b[1]))
        courant = [bouts[0]]
        suites = [courant]
        for bout in bouts[1:]:
            if bout[0] - max(b[1] for b in courant) > BAIE_MAX_M * m:
                courant = [bout]
                suites.append(courant)
            else:
                courant.append(bout)
        for suite in suites:
            debut, fin = suite[0][0], max(b[1] for b in suite)
            baies, atteint = [], suite[0][1]
            for t0, t1, _ in suite[1:]:
                if t0 - atteint > 0:
                    baies.append(t0 - atteint)
                atteint = max(atteint, t1)
            morceaux = [b[2] for b in suite]
            chainees.append(
                {
                    "faces": tuple(sorted({f for p in morceaux for f in p["faces"]})),
                    "axe": (ox + ux * debut, oy + uy * debut, ox + ux * fin, oy + uy * fin),
                    "epaisseur": sum(p["epaisseur"] for p in morceaux) / len(morceaux),
                    "longueur": fin - debut,
                    "pleine": sum(p["longueur"] for p in morceaux),
                    "baies": sorted(baies, reverse=True),
                }
            )
    return chainees


def _vis_a_vis(face: dict, autre: dict, m: float) -> tuple[float, float, float] | None:
    """(épaisseur, début, fin) de la partie où les deux faces se font face, le long de `face`."""
    ux, uy = face["u"]
    vx, vy = autre["u"]
    if abs(ux * vx + uy * vy) < math.cos(math.radians(ANGLE_MAX_DEG)):
        return None
    ax, ay = face["a"]
    ecart = abs((autre["a"][0] - ax) * -uy + (autre["a"][1] - ay) * ux)
    if not EPAISSEUR_M[0] * m <= ecart <= EPAISSEUR_M[1] * m:
        return None
    t1 = (autre["a"][0] - ax) * ux + (autre["a"][1] - ay) * uy
    t2 = (autre["b"][0] - ax) * ux + (autre["b"][1] - ay) * uy
    debut, fin = max(min(t1, t2), 0.0), min(max(t1, t2), face["longueur"])
    commun = fin - debut
    if commun < RECOUVREMENT_MIN * min(face["longueur"], autre["longueur"]):
        return None
    return ecart, debut, fin


def apparier(donnees: dict, candidates: list[dict]) -> tuple[list[dict], int]:
    """Paires de faces en vis-à-vis, et le nombre total de vis-à-vis possibles (garde-fou D5).

    Chaque face garde le partenaire qui la couvre le plus ; le nombre de vis-à-vis rencontrés en
    chemin dit si on a affaire à des parois ou à une trame.
    """
    m = 1 / pt_en_m(donnees["echelle"])
    cases = defaultdict(list)
    for k, face in enumerate(candidates):
        for point in (face["a"], face["b"]):
            cases[(int(point[0] // m), int(point[1] // m))].append(k)
    meilleur: dict[int, tuple[float, int, tuple]] = {}
    rencontres = 0
    for k, face in enumerate(candidates):
        voisins = set()
        for point in (face["a"], face["b"]):
            cx, cy = int(point[0] // m), int(point[1] // m)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    voisins.update(cases.get((cx + dx, cy + dy), ()))
        for j in voisins:
            if j == k:
                continue
            mesure = _vis_a_vis(face, candidates[j], m)
            if mesure is None:
                continue
            rencontres += 1
            couverture = mesure[2] - mesure[1]
            if couverture > meilleur.get(k, (0.0,))[0]:
                meilleur[k] = (couverture, j, mesure)
    paires: dict[tuple[int, int], tuple[float, int, int, tuple]] = {}
    for depuis, (couverture, vers, mesure) in meilleur.items():
        cle = (min(depuis, vers), max(depuis, vers))
        if couverture > paires.get(cle, (0.0,))[0]:
            paires[cle] = (couverture, depuis, vers, mesure)
    resultat = []
    for _, (_, depuis, vers, (ecart, debut, fin)) in sorted(paires.items()):
        face, autre = candidates[depuis], candidates[vers]
        ux, uy = face["u"]
        ax, ay = face["a"]
        # l'axe de la paroi : la partie commune, décalée d'une demi-épaisseur vers l'autre face
        cote = 1.0 if (autre["a"][0] - ax) * -uy + (autre["a"][1] - ay) * ux > 0 else -1.0
        demi = cote * ecart / 2
        resultat.append(
            {
                "faces": (face["element"], autre["element"]),
                "axe": (
                    ax + ux * debut - uy * demi,
                    ay + uy * debut + ux * demi,
                    ax + ux * fin - uy * demi,
                    ay + uy * fin + ux * demi,
                ),
                "epaisseur": ecart,
                "longueur": fin - debut,
            }
        )
    return resultat, rencontres


def epaisseurs(paires: list[dict], m: float) -> list[tuple[float, int]]:
    """Épaisseurs rencontrées, au centimètre, de la plus fréquente à la moins fréquente."""
    comptes = Counter(round(p["epaisseur"] / m * 100) for p in paires)
    return [(cm / 100, n) for cm, n in comptes.most_common()]


def mesurer(donnees: dict, indices: list[int], controler: bool = True) -> dict:
    """Parois portées par les éléments désignés, avec leurs épaisseurs.

    `controler` applique le garde-fou D5 : sans lui, une trame régulière passerait pour un mur.
    """
    m = 1 / pt_en_m(donnees["echelle"])
    candidates = faces(donnees, indices)
    if not candidates:
        raise ParoisError("Aucune face assez longue : ces traits ne dessinent pas une paroi.")
    morceaux, rencontres = apparier(donnees, candidates)
    if not morceaux:
        raise ParoisError("Aucune face n'en a une autre en vis-à-vis : ces traits ne dessinent pas une paroi.")
    vis_a_vis = rencontres / len(candidates)
    if controler and vis_a_vis > VIS_A_VIS_MAX:
        raise ParoisError(
            f"Chaque trait en a {vis_a_vis:.0f} autres en vis-à-vis : c'est une trame régulière, "
            "pas des parois. Une face de mur n'en a qu'une seule en face d'elle."
        )
    paires = [p for p in chainer(morceaux, m) if p["longueur"] >= LONGUEUR_MIN_M * m]
    if not paires:
        raise ParoisError("Les parois trouvées sont trop courtes pour être mesurées.")
    par_m = pt_en_m(donnees["echelle"])
    baies = [b * par_m for p in paires for b in p["baies"]]
    return {
        "parois": paires,
        "epaisseurs": epaisseurs(paires, m),
        "vis_a_vis_par_face": vis_a_vis,
        "faces_appariees": len({f for p in paires for f in p["faces"]}),
        "faces_vues": len({f["element"] for f in candidates}),
        "longueur_m": sum(p["longueur"] for p in paires) * par_m,
        "pleine_m": sum(p["pleine"] for p in paires) * par_m,
        "baies": len(baies),
        "baies_m": sum(baies),
    }
