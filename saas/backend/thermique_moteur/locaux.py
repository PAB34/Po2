"""Locaux délimités par les traits réels du plan (docs/thermique/parois-et-motifs-decisions.md, D8 et §0.6).

On abandonne le calcul par pixels : il produisait des contours en étoile (sur le R+1, deux locaux ratés
pesaient 544 m² sur 841). Ici, le contour d'un local est une **boucle du dessin lui-même**.

1. les traits des limites sont **découpés à leurs intersections** ;
2. les **passages** (portes, ouvertures) sont refermés en reliant deux bouts libres proches, sans jamais
   traverser un trait existant ;
3. le plan devient un graphe dont les **faces** sont les locaux : on rend celle qui contient le point
   cliqué, avec ses sommets exacts.

Aucun sommet n'est inventé : chaque coin est une vraie intersection de deux traits, ou une fermeture de
passage que l'on sait nommer.
"""
from __future__ import annotations

import math
from collections import defaultdict

from thermique_moteur.calques import TRAIT
from thermique_moteur.metre import pt_en_m

SNAP_M = 0.02
PROLONGE_M = 0.3
SOUDURE_M = 0.15
PASSAGE_MAX_M = 2.5
ALIGNEMENT_MAX_DEG = 12.0
ANGLE_MAX_DEG_COTE = 8.0
SEGMENT_MIN_M = 0.05
SURFACE_MIN_M2 = 0.5
CASE_M = 1.0


class LocauxError(Exception):
    """Ce que le plan ne permet pas de délimiter."""


def _segments(donnees: dict, indices: list[int], m: float) -> list[tuple]:
    minimum = SEGMENT_MIN_M * m
    elements = donnees["elements"]
    out = []
    for i in indices:
        e = elements[i]
        if e[0] != TRAIT:
            continue
        c = e[7]
        for k in range(0, len(c) - 3, 2):
            a, b = (c[k], c[k + 1]), (c[k + 2], c[k + 3])
            if math.dist(a, b) >= minimum:
                out.append((a, b))
    return out


def _cases(a: tuple, b: tuple, pas: float):
    x0, x1 = sorted((a[0], b[0]))
    y0, y1 = sorted((a[1], b[1]))
    for cx in range(int(x0 // pas), int(x1 // pas) + 1):
        for cy in range(int(y0 // pas), int(y1 // pas) + 1):
            yield (cx, cy)


def _projete(point: tuple, a: tuple, b: tuple) -> tuple[float, tuple]:
    """(distance, pied) du point sur le segment [a, b]."""
    vx, vy = b[0] - a[0], b[1] - a[1]
    carre = vx * vx + vy * vy
    t = 0.0 if carre == 0 else max(0.0, min(1.0, ((point[0] - a[0]) * vx + (point[1] - a[1]) * vy) / carre))
    pied = (a[0] + vx * t, a[1] + vy * t)
    return math.dist(point, pied), pied


def souder(segments: list[tuple], m: float) -> list[tuple]:
    """Soude au trait voisin les bouts qui s'arrêtent **juste à côté**, sans être dans son axe.

    Sur un plan réel, une cloison s'arrête souvent à quelques centimètres du mur qu'elle rejoint, ou
    légèrement décalée : l'œil ne le voit pas, mais le local reste ouvert et son contour s'échappe.
    Mesuré sur le R+1 avant ce rattrapage : 509 bouts libres sur 1 769 sommets, et seulement 43 locaux
    fermés. Allonger le trait dans son axe ne suffit pas — il faut le raccorder au plus proche.

    La soudure est un trait très court (au plus `SOUDURE_M`), donc sans effet sur les surfaces.
    """
    portee = SOUDURE_M * m
    pas = max(portee, CASE_M * m)
    grille = defaultdict(list)
    for k, (a, b) in enumerate(segments):
        for case in _cases(a, b, pas):
            grille[case].append(k)
    liaisons = []
    for k, (a, b) in enumerate(segments):
        for bout in (a, b):
            meilleure = None
            cx, cy = int(bout[0] // pas), int(bout[1] // pas)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for j in grille.get((cx + dx, cy + dy), ()):
                        if j == k:
                            continue
                        distance, pied = _projete(bout, *segments[j])
                        if distance <= portee and (meilleure is None or distance < meilleure[0]):
                            meilleure = (distance, pied)
            # rien à faire si le bout touche déjà le trait voisin, ou si aucun n'est à portée
            if meilleure is not None and meilleure[0] > SNAP_M * m:
                liaisons.append((bout, meilleure[1]))
    return segments + liaisons


def _croisement(p1, p2, p3, p4):
    """Paramètres (t, s) du croisement de deux segments, ou None s'ils sont parallèles."""
    d1x, d1y = p2[0] - p1[0], p2[1] - p1[1]
    d2x, d2y = p4[0] - p3[0], p4[1] - p3[1]
    det = d1x * d2y - d1y * d2x
    if abs(det) < 1e-9:
        return None
    t = ((p3[0] - p1[0]) * d2y - (p3[1] - p1[1]) * d2x) / det
    s = ((p3[0] - p1[0]) * d1y - (p3[1] - p1[1]) * d1x) / det
    return t, s


def decouper(segments: list[tuple], m: float) -> list[tuple]:
    """Découpe les traits à leurs croisements, chaque trait étant **allongé jusqu'à sa rencontre**.

    Sur un vrai plan, les deux faces d'un mur s'arrêtent au coin sans rejoindre celles du mur voisin :
    sans rattrapage, presque aucun trait n'en croise un autre et le plan n'a aucune boucle fermée
    (mesuré sur le R+1 : 774 traits, 170 croisements seulement). On cherche donc les croisements sur
    un trait allongé de `PROLONGE_M`, mais on ne garde l'allonge que **là où elle rencontre vraiment
    quelque chose** — comme le fait un CAO. Ailleurs, le trait garde sa longueur d'origine : pas de
    barbes qui pendent dans le vide et fausseraient les contours.
    """
    marge = PROLONGE_M * m
    allonges, bornes_vraies = [], []
    for a, b in segments:
        longueur = math.dist(a, b) or 1.0
        ux, uy = (b[0] - a[0]) / longueur, (b[1] - a[1]) / longueur
        allonges.append(((a[0] - ux * marge, a[1] - uy * marge), (b[0] + ux * marge, b[1] + uy * marge)))
        entier = longueur + 2 * marge
        bornes_vraies.append((marge / entier, (marge + longueur) / entier))

    pas = CASE_M * m
    grille = defaultdict(list)
    for k, (a, b) in enumerate(allonges):
        for case in _cases(a, b, pas):
            grille[case].append(k)
    coupures = [set() for _ in allonges]
    for liste in grille.values():
        for indice, k in enumerate(liste):
            a, b = allonges[k]
            for j in liste[indice + 1 :]:
                c, d = allonges[j]
                croise = _croisement(a, b, c, d)
                if croise is None:
                    continue
                t, s = croise
                if 0.0 <= t <= 1.0 and 0.0 <= s <= 1.0:
                    coupures[k].add(t)
                    coupures[j].add(s)

    morceaux = []
    for k, (a, b) in enumerate(allonges):
        debut, fin = bornes_vraies[k]
        avant = [t for t in coupures[k] if t < debut]
        apres = [t for t in coupures[k] if t > fin]
        debut = min(avant) if avant else debut
        fin = max(apres) if apres else fin
        retenues = sorted({debut, fin} | {t for t in coupures[k] if debut < t < fin})
        for t0, t1 in zip(retenues, retenues[1:]):
            p = (a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0)
            q = (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)
            if math.dist(p, q) >= SEGMENT_MIN_M * m:
                morceaux.append((p, q))
    return morceaux


def _graphe(morceaux: list[tuple], m: float) -> tuple[list[tuple], dict]:
    """Sommets fusionnés à SNAP_M près, arêtes sans doublon."""
    pas = SNAP_M * m
    noeuds: dict[tuple, int] = {}
    points: list[tuple] = []

    def sommet(p):
        cle = (round(p[0] / pas), round(p[1] / pas))
        if cle not in noeuds:
            noeuds[cle] = len(points)
            points.append((cle[0] * pas, cle[1] * pas))
        return noeuds[cle]

    aretes = set()
    for a, b in morceaux:
        u, v = sommet(a), sommet(b)
        if u != v:
            aretes.add((min(u, v), max(u, v)))
    return points, aretes


def _refermer(points: list[tuple], aretes: set, m: float) -> set:
    """Referme les passages : deux bouts libres **alignés** sont reliés, si rien ne s'interpose.

    Une porte perce une cloison : les deux tronçons de part et d'autre sont dans le prolongement l'un
    de l'autre, et c'est ce qui distingue une ouverture d'un simple débord de dessin à un angle. Sans ce
    raccord, le local « fuit » par l'ouverture et son contour part en étoile ; sans la condition
    d'alignement, on relierait deux bouts de murs perpendiculaires et on couperait les coins.
    """
    degres = defaultdict(int)
    voisin = {}
    for u, v in aretes:
        degres[u] += 1
        degres[v] += 1
        voisin.setdefault(u, v)
        voisin.setdefault(v, u)
    libres = [k for k, d in degres.items() if d == 1]
    if not libres:
        return aretes
    portee = PASSAGE_MAX_M * m
    grille = defaultdict(list)
    for k in libres:
        grille[(int(points[k][0] // portee), int(points[k][1] // portee))].append(k)
    existantes = [(points[u], points[v]) for u, v in aretes]
    case_aretes = defaultdict(list)
    for indice, (a, b) in enumerate(existantes):
        for case in _cases(a, b, CASE_M * m):
            case_aretes[case].append(indice)

    def traverse(a, b):
        vus = set()
        for case in _cases(a, b, CASE_M * m):
            for indice in case_aretes.get(case, ()):
                if indice in vus:
                    continue
                vus.add(indice)
                c, d = existantes[indice]
                croise = _croisement(a, b, c, d)
                if croise and 0.01 < croise[0] < 0.99 and 0.01 < croise[1] < 0.99:
                    return True
        return False

    def sortante(k):
        """Direction du trait qui arrive sur ce bout libre, pointée vers le vide."""
        px, py = points[k]
        qx, qy = points[voisin[k]]
        longueur = math.hypot(px - qx, py - qy) or 1.0
        return ((px - qx) / longueur, (py - qy) / longueur)

    cos_max = math.cos(math.radians(ALIGNEMENT_MAX_DEG))
    candidats = []
    for k in libres:
        px, py = points[k]
        ux, uy = sortante(k)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grille.get((int(px // portee) + dx, int(py // portee) + dy), ()):
                    if j <= k:
                        continue
                    d = math.dist(points[k], points[j])
                    if d > portee or d == 0:
                        continue
                    vx, vy = sortante(j)
                    # les deux traits doivent être dans le prolongement l'un de l'autre…
                    if -(ux * vx + uy * vy) < cos_max:
                        continue
                    # … et le raccord doit partir vers le vide, pas revenir en arrière
                    wx, wy = (points[j][0] - px) / d, (points[j][1] - py) / d
                    if ux * wx + uy * wy < cos_max:
                        continue
                    candidats.append((d, k, j))
    candidats.sort()
    pris = set()
    ajoutees = set(aretes)
    for d, k, j in candidats:
        if k in pris or j in pris or (min(k, j), max(k, j)) in ajoutees:
            continue
        if traverse(points[k], points[j]):
            continue
        ajoutees.add((min(k, j), max(k, j)))
        pris.add(k)
        pris.add(j)
    return ajoutees


def _sans_aller_retour(boucle: list[int]) -> list[int]:
    """Retire du contour les traits parcourus à l'aller et au retour.

    Une cloison dont un bout reste libre — elle s'arrête sur un passage large, ou c'est une amorce — est
    longée deux fois par le parcours. On ne peut pas l'élaguer du graphe : la supprimer rouvrirait le
    local qu'elle sépare. On la retire seulement du **contour**, où elle ne décrit rien (son aire est
    nulle) mais ajouterait des pics.
    """
    propre = list(boucle)
    change = True
    while change and len(propre) > 3:
        change = False
        n = len(propre)
        for k in range(n):
            if propre[(k - 1) % len(propre)] == propre[(k + 1) % len(propre)]:
                del propre[k % len(propre)]
                del propre[k % len(propre)]
                change = True
                break
    return propre


def _faces(points: list[tuple], aretes: set) -> list[list[int]]:
    """Toutes les boucles fermées du graphe, parcourues par la demi-arête la plus à droite."""
    sortantes = defaultdict(list)
    for u, v in aretes:
        sortantes[u].append(v)
        sortantes[v].append(u)
    ordre = {}
    for u, voisins in sortantes.items():
        voisins.sort(key=lambda v: math.atan2(points[v][1] - points[u][1], points[v][0] - points[u][0]))
        ordre[u] = {v: k for k, v in enumerate(voisins)}
    vues = set()
    boucles = []
    for depart, voisins in sortantes.items():
        for premier in voisins:
            if (depart, premier) in vues:
                continue
            boucle = []
            u, v = depart, premier
            while (u, v) not in vues:
                vues.add((u, v))
                boucle.append(u)
                liste = sortantes[v]
                suivant = liste[(ordre[v][u] - 1) % len(liste)]
                u, v = v, suivant
                if len(boucle) > len(aretes) * 2 + 4:
                    break
            if len(boucle) >= 3:
                boucles.append(boucle)
    return boucles


def _aire(points: list[tuple], boucle: list[int]) -> float:
    total = 0.0
    for a, b in zip(boucle, boucle[1:] + boucle[:1]):
        total += points[a][0] * points[b][1] - points[b][0] * points[a][1]
    return total / 2


def _dedans(points: list[tuple], boucle: list[int], point: tuple) -> bool:
    x, y = point
    dedans = False
    for a, b in zip(boucle, boucle[1:] + boucle[:1]):
        (x1, y1), (x2, y2) = points[a], points[b]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            dedans = not dedans
    return dedans


def decouper_le_plan(donnees: dict, indices: list[int]) -> dict:
    """Prépare une fois le graphe du plan : à réutiliser pour tous les clics du même plan."""
    m = 1 / pt_en_m(donnees["echelle"])
    segments = _segments(donnees, indices, m)
    if not segments:
        raise LocauxError("Aucun trait de limite sur ce plan : désignez d'abord les murs et les cloisons.")
    return _preparer(segments, m, pt_en_m(donnees["echelle"]))


def _preparer(segments: list[tuple], m: float, par_m: float) -> dict:
    points, aretes = _graphe(decouper(souder(segments, m), m), m)
    aretes = _refermer(points, aretes, m)
    boucles = []
    mini = SURFACE_MIN_M2 / par_m**2
    for brute in _faces(points, aretes):
        boucle = _sans_aller_retour(brute)
        if len(boucle) < 3:
            continue
        aire = _aire(points, boucle)
        # le sens de parcours dépend de la composante du dessin (un îlot au milieu d'un plateau tourne
        # à l'envers) : on ne s'y fie pas, on remet chaque contour dans le sens direct. Les tours
        # extérieurs sont éliminés au clic, puisqu'on rend la **plus petite** face qui contient le point.
        if abs(aire) > mini:
            boucles.append((abs(aire), boucle if aire > 0 else boucle[::-1]))
    boucles.sort(key=lambda t: t[0])
    return {"points": points, "boucles": boucles, "m": m}


def _epaisseur_du_cote(a: tuple, b: tuple, murs: list[dict], m: float) -> float:
    """Épaisseur de la paroi qui porte ce côté du contour, ou 0 si c'est un raccord."""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    longueur = math.dist(a, b) or 1.0
    ux, uy = (b[0] - a[0]) / longueur, (b[1] - a[1]) / longueur
    meilleure = (SOUDURE_M * m, 0.0)
    for paroi in murs:
        x1, y1, x2, y2 = paroi["axe"]
        lp = math.hypot(x2 - x1, y2 - y1) or 1.0
        vx, vy = (x2 - x1) / lp, (y2 - y1) / lp
        if abs(ux * vx + uy * vy) < math.cos(math.radians(ANGLE_MAX_DEG_COTE)):
            continue
        distance, _ = _projete((mx, my), (x1, y1), (x2, y2))
        if distance < meilleure[0]:
            meilleure = (distance, paroi["epaisseur"])
    return meilleure[1]


def _retrecir(contour: list[tuple], epaisseurs: list[float]) -> list[tuple]:
    """Rentre chaque côté d'une demi-épaisseur : du contour entre axes au **nu intérieur** du local."""
    n = len(contour)
    droites = []
    for k in range(n):
        a, b = contour[k], contour[(k + 1) % n]
        longueur = math.dist(a, b) or 1.0
        ux, uy = (b[0] - a[0]) / longueur, (b[1] - a[1]) / longueur
        d = epaisseurs[k] / 2
        droites.append(((a[0] - uy * d, a[1] + ux * d), (ux, uy)))  # contour direct : intérieur à gauche
    rentre = []
    for k in range(n):
        (p1, u1), (p2, u2) = droites[(k - 1) % n], droites[k]
        det = u1[0] * u2[1] - u1[1] * u2[0]
        if abs(det) < 1e-9:  # côtés parallèles : on garde le point décalé
            rentre.append(p2)
            continue
        t = ((p2[0] - p1[0]) * u2[1] - (p2[1] - p1[1]) * u2[0]) / det
        rentre.append((p1[0] + u1[0] * t, p1[1] + u1[1] * t))
    return rentre


def depuis_parois(donnees: dict, murs: list[dict]) -> dict:
    """Prépare le plan à partir des **axes de parois**, et non des traits bruts.

    Un trait n'est pas un mur : c'est un côté de mur. En travaillant sur les traits, les boucles fermées
    du dessin sont les rubans entre les deux faces — autrement dit les murs eux-mêmes, pas les pièces
    (mesuré sur le R+1 : un ruban unique de 156 m² faisant le tour de toutes les cloisons). Sur les
    axes, les faces sont les pièces, comme dans un logiciel de thermique : on pose des axes, et on
    retranche les demi-épaisseurs pour obtenir la surface intérieure.
    """
    m = 1 / pt_en_m(donnees["echelle"])
    if not murs:
        raise LocauxError("Aucune paroi mesurée sur ce plan : désignez d'abord les murs et les cloisons.")
    segments = [((p["axe"][0], p["axe"][1]), (p["axe"][2], p["axe"][3])) for p in murs]
    plan = _preparer(segments, m, pt_en_m(donnees["echelle"]))
    plan["murs"] = murs
    return plan


def local_au_point(plan: dict, point: tuple[float, float]) -> dict:
    """Le plus petit local qui contient le point, avec son contour exact et sa compacité."""
    points = plan["points"]
    murs = plan.get("murs")
    for aire, boucle in plan["boucles"]:
        if _dedans(points, boucle, point):
            contour = [points[k] for k in boucle]
            perimetre = sum(math.dist(a, b) for a, b in zip(contour, contour[1:] + contour[:1]))
            par_m = 1 / plan["m"]
            local = {
                "contour": [c for p in contour for c in p],
                "surface_m2": aire * par_m * par_m,
                "perimetre_m": perimetre * par_m,
                "compacite": 4 * math.pi * aire / perimetre**2 if perimetre else 0.0,
                "sommets": len(contour),
            }
            if murs:
                # sur les axes, le contour passe au milieu des parois : on rentre d'une demi-épaisseur
                epaisseurs = [
                    _epaisseur_du_cote(a, b, murs, plan["m"])
                    for a, b in zip(contour, contour[1:] + contour[:1])
                ]
                dedans = _retrecir(contour, epaisseurs)
                local["contour_interieur"] = [c for p in dedans for c in p]
                local["surface_interieure_m2"] = abs(_aire(dedans, list(range(len(dedans))))) * par_m * par_m
                local["epaisseurs_m"] = [round(e * par_m, 3) for e in epaisseurs]
            return local
    raise LocauxError("Ce point n'est dans aucun local fermé : il manque une limite, ou le passage est trop large.")
