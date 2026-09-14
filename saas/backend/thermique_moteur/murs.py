"""Murs par appariement de faces — jalon J3 de docs/thermique/detection-murs-strategie.md (première version).

Un mur coupé est dessiné par deux faces parallèles. Pour chaque ligne de face (lignes déjà recollées par
`vecteurs.fusionner_lignes`), on cherche les lignes parallèles situées à 5-80 cm du côté des positions
croissantes ; la portion commune aux deux lignes, **diminuée des portions où une autre face s'intercale**,
devient un segment de mur : axe, épaisseur exacte, étendue. La part de l'axe couverte par un remplissage
(aplats unis) est mesurée pour distinguer un mur d'un simple vide entre deux murs.
"""
from __future__ import annotations

import math
from collections import defaultdict

from thermique_moteur.metre import pt_en_m
from thermique_moteur.vecteurs import EPAISSEUR_MUR_MAX_M, EPAISSEUR_MUR_MIN_M

LARGEUR_FACE_MIN_PT = 0.9  # provisoire : sera tirée du dictionnaire des plumes
# Les faces de murs sont noires ; les lignes de cotes et d'annotation colorées (rouge : luminance 76) sont écartées.
LUMINANCE_FACE_MAX = 64
RECOUVREMENT_MIN_M = 0.05
TOL_DIRECTION_DEG = 0.5
PAS_REMPLISSAGE_M = 0.10
TOL_FIN_PT = 2.0
LONGUEUR_FIN_MAX_M = 0.9


def faces_de_murs(lignes: list[dict], largeur_min: float = LARGEUR_FACE_MIN_PT) -> list[dict]:
    return [
        ligne
        for ligne in lignes
        if ligne["largeur"] >= largeur_min - 1e-6 and ligne.get("luminance", 0) <= LUMINANCE_FACE_MAX
    ]


def fins_de_mur(faces: list[dict], murs: list[dict], echelle: float) -> dict[int, int]:
    """Petites faces perpendiculaires qui ferment un mur : chacune de leurs extrémités touche l'une des deux
    faces du mur (± 2 pt). Renvoie {indice de la face de fin : indice du mur}."""
    m = 1.0 / pt_en_m(echelle)
    fins: dict[int, int] = {}
    for index, face in enumerate(faces):
        if face["longueur"] > LONGUEUR_FIN_MAX_M * m:
            continue
        for numero, mur in enumerate(murs):
            if abs(face["ux"] * mur["ux"] + face["uy"] * mur["uy"]) > math.sin(math.radians(2)):
                continue
            if face["longueur"] < (mur["epaisseur_m"] - 0.02) * m or face["longueur"] > (mur["epaisseur_m"] + 0.05) * m:
                continue
            ux, uy = mur["ux"], mur["uy"]
            t_min, t_max = sorted((ux * mur["x1"] + uy * mur["y1"], ux * mur["x2"] + uy * mur["y2"]))
            extremites = []
            for x, y in ((face["x1"], face["y1"]), (face["x2"], face["y2"])):
                t = ux * x + uy * y
                n = -uy * x + ux * y
                if t_min - TOL_FIN_PT <= t <= t_max + TOL_FIN_PT:
                    extremites.append(n)
            if len(extremites) == 2:
                bas, haut = sorted(extremites)
                if abs(bas - mur["n_a"]) <= TOL_FIN_PT and abs(haut - mur["n_b"]) <= TOL_FIN_PT:
                    fins[index] = numero
                    break
    return fins


def _distance_segment(x: float, y: float, a: tuple[float, float], b: tuple[float, float]) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    carre = dx * dx + dy * dy
    t = 0.0 if carre < 1e-12 else max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / carre))
    return math.hypot(x - a[0] - t * dx, y - a[1] - t * dy)


def faces_de_contour(faces: list[dict], anneaux: list[dict], murs: list[dict], tolerance_pt: float = 1.0) -> dict[int, int]:
    """Faces qui suivent le contour de l'aplat d'un mur détecté sans être appariées : feuillures et encoches en
    bout de mur (portes, gaines). Une face est retenue si ses extrémités et son milieu sont sur le bord d'un
    anneau (± 1 pt) qui contient le milieu d'un mur. Renvoie {indice de face : indice du mur}."""
    porteurs = []
    for anneau in anneaux:
        points = anneau["points"]
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        boite = (min(xs) - tolerance_pt, min(ys) - tolerance_pt, max(xs) + tolerance_pt, max(ys) + tolerance_pt)
        for numero, mur in enumerate(murs):
            mx, my = (mur["x1"] + mur["x2"]) / 2, (mur["y1"] + mur["y2"]) / 2
            if boite[0] <= mx <= boite[2] and boite[1] <= my <= boite[3] and _dans_anneau(mx, my, points):
                porteurs.append((boite, points, numero))
                break
    contour: dict[int, int] = {}
    for index, face in enumerate(faces):
        echantillons = ((face["x1"], face["y1"]), (face["x2"], face["y2"]), ((face["x1"] + face["x2"]) / 2, (face["y1"] + face["y2"]) / 2))
        for boite, points, numero in porteurs:
            if not all(boite[0] <= x <= boite[2] and boite[1] <= y <= boite[3] for x, y in echantillons):
                continue
            arete = len(points)
            if all(min(_distance_segment(x, y, points[k], points[(k + 1) % arete]) for k in range(arete)) <= tolerance_pt for x, y in echantillons):
                contour[index] = numero
                break
    return contour


def _intervalle(mur: dict, ux: float, uy: float) -> tuple[float, float]:
    return tuple(sorted((ux * mur["x1"] + uy * mur["y1"], ux * mur["x2"] + uy * mur["y2"])))  # type: ignore[return-value]


def parois_composees(murs: list[dict]) -> list[dict]:
    """Parois à couches (ex. maçonnerie + doublage), calculées **tronçon par tronçon**.

    Chaque mur est découpé aux extrémités des murs qui partagent ses faces ; sur chaque tronçon, la pile
    réunit de proche en proche les couches (murs partageant une face) qui couvrent **tout** le tronçon. Un
    doublage qui longe successivement un mur de 40 cm puis un mur de 20 cm donne donc deux parois (50 et
    30 cm), jamais 70 cm. Les tronçons de même composition sont regroupés, avec leur longueur."""
    par_face: dict[int, list[int]] = defaultdict(list)
    for numero, mur in enumerate(murs):
        for face in mur["faces"]:
            par_face[face].append(numero)
    piles: dict[tuple, dict] = {}
    deja: set[tuple] = set()
    for numero, mur in enumerate(murs):
        ux, uy = mur["ux"], mur["uy"]
        debut, fin = _intervalle(mur, ux, uy)
        coupures = {debut, fin}
        for face in mur["faces"]:
            for voisin in par_face[face]:
                for t in _intervalle(murs[voisin], ux, uy):
                    if debut < t < fin:
                        coupures.add(t)
        bornes = sorted(coupures)
        for t1, t2 in zip(bornes, bornes[1:]):
            if t2 - t1 <= 1e-6:
                continue
            pile, a_voir = {numero}, [numero]
            while a_voir:
                courant = murs[a_voir.pop()]
                for face in courant["faces"]:
                    for voisin in par_face[face]:
                        if voisin in pile:
                            continue
                        v1, v2 = _intervalle(murs[voisin], ux, uy)
                        if v1 <= t1 + 1e-6 and v2 >= t2 - 1e-6:
                            pile.add(voisin)
                            a_voir.append(voisin)
            couches: dict[tuple, dict] = {}
            for membre in sorted(pile, key=lambda k: murs[k]["n_a"]):
                couche = murs[membre]
                cle = (round(couche["n_a"], 1), round(couche["n_b"], 1))
                couches.setdefault(cle, {"epaisseur_m": couche["epaisseur_m"], "remplissage": couche["remplissage"]})
            signature = tuple(sorted(couches))
            paroi = piles.setdefault(
                signature,
                {
                    "murs": [],
                    "epaisseur_m": round(sum(c["epaisseur_m"] for c in couches.values()), 3),
                    "couches": list(couches.values()),
                    "longueur_pt": 0.0,
                },
            )
            if numero not in paroi["murs"]:
                paroi["murs"].append(numero)
            # Le même tronçon est vu depuis chacune de ses couches : on ne compte sa longueur qu'une fois.
            troncon = (signature, round(t1, 1), round(t2, 1))
            if troncon not in deja:
                deja.add(troncon)
                paroi["longueur_pt"] += t2 - t1
    return list(piles.values())


def arcs_de_faces(faces: list[dict], echelle: float) -> list[dict]:
    """Recolle en arcs de cercle les chaînes de petites faces contiguës (courbes imprimées en cordes)."""
    import numpy as np

    m = 1.0 / pt_en_m(echelle)
    courtes = [i for i, face in enumerate(faces) if face["longueur"] <= 0.5 * m]

    def cle(x, y):
        return (round(x / 0.1), round(y / 0.1))

    extremites: dict[tuple, list[int]] = defaultdict(list)
    for i in courtes:
        extremites[cle(faces[i]["x1"], faces[i]["y1"])].append(i)
        extremites[cle(faces[i]["x2"], faces[i]["y2"])].append(i)
    vues: set[int] = set()
    arcs = []
    for depart in courtes:
        if depart in vues:
            continue
        chaine, pile = [], [depart]
        while pile:
            i = pile.pop()
            if i in vues:
                continue
            vues.add(i)
            chaine.append(i)
            face = faces[i]
            for point in ((face["x1"], face["y1"]), (face["x2"], face["y2"])):
                voisins = [j for j in extremites[cle(*point)] if j != i and faces[j]["largeur"] == face["largeur"]]
                if len(voisins) == 1:
                    pile.extend(voisins)
        if len(chaine) < 4:
            continue
        points = np.array([(faces[i][k], faces[i][l]) for i in chaine for k, l in (("x1", "y1"), ("x2", "y2"))])
        a = np.column_stack((points[:, 0], points[:, 1], np.ones(len(points))))
        b = -(points[:, 0] ** 2 + points[:, 1] ** 2)
        (d, e, f), *_ = np.linalg.lstsq(a, b, rcond=None)
        cx, cy = -d / 2, -e / 2
        rayon2 = cx * cx + cy * cy - f
        if rayon2 <= 0:
            continue
        rayon = float(np.sqrt(rayon2))
        ecarts = np.abs(np.hypot(points[:, 0] - cx, points[:, 1] - cy) - rayon)
        if float(ecarts.max()) > 0.3 or rayon > 30 * m:
            continue
        angles = np.unwrap(np.sort(np.arctan2(points[:, 1] - cy, points[:, 0] - cx)))
        trou = np.diff(np.concatenate((angles, [angles[0] + 2 * np.pi])))
        k = int(np.argmax(trou))
        debut = angles[(k + 1) % len(angles)]
        fin = angles[k] + (2 * np.pi if k + 1 < len(angles) else 0.0)
        if fin < debut:
            fin += 2 * np.pi
        arcs.append(
            {
                "cx": float(cx),
                "cy": float(cy),
                "rayon": rayon,
                "debut": float(debut),
                "fin": float(fin),
                "faces": sorted(chaine),
                "largeur": faces[chaine[0]]["largeur"],
                "points": [(float(x), float(y)) for x, y in points],
            }
        )
    return arcs


def apparier_arcs(arcs: list[dict], echelle: float) -> list[dict]:
    """Murs courbes : deux arcs parallèles (courbes décalées) à 5-80 cm l'un de l'autre.

    Les deux faces d'un mur courbe ne sont pas forcément concentriques à l'impression (centres ajustés à
    5,6 pt d'écart sur le projet d'essai) : on mesure la distance des points de l'arc extérieur au cercle de
    l'arc intérieur ; elle doit être constante (écart-type ≤ 1 pt) sur la partie commune."""
    import numpy as np

    m = 1.0 / pt_en_m(echelle)

    def distance_au_cercle(reference: dict, autre: dict):
        points = np.array(autre["points"])
        angles = np.arctan2(points[:, 1] - reference["cy"], points[:, 0] - reference["cx"])
        angles = reference["debut"] + np.mod(angles - reference["debut"], 2 * np.pi)
        dans = (angles >= reference["debut"]) & (angles <= reference["fin"])
        if dans.sum() < 4:
            return None, None, None
        distances = np.hypot(points[dans, 0] - reference["cx"], points[dans, 1] - reference["cy"]) - reference["rayon"]
        return float(np.median(distances)), float(distances.std()), angles[dans]

    murs = []
    for i, a in enumerate(arcs):
        for j, b in enumerate(arcs):
            if j <= i:
                continue
            interieur, exterieur = (a, b) if a["rayon"] < b["rayon"] else (b, a)
            ecart, dispersion, angles_communs = distance_au_cercle(interieur, exterieur)
            if ecart is None or not EPAISSEUR_MUR_MIN_M * m <= ecart <= EPAISSEUR_MUR_MAX_M * m or dispersion > 1.0:
                continue
            # Comme pour les murs droits : pas d'appariement par-dessus un arc intermédiaire (couche du milieu).
            entre = False
            for k, c in enumerate(arcs):
                if k in (i, j):
                    continue
                milieu, dispersion_c, _ = distance_au_cercle(interieur, c)
                if milieu is not None and dispersion_c <= 1.0 and 0.5 < milieu < ecart - 0.5:
                    entre = True
                    break
            if entre:
                continue
            dans = np.ones(len(angles_communs), dtype=bool)
            angles = angles_communs
            debut, fin = float(angles[dans].min()), float(angles[dans].max())
            rayon_axe = interieur["rayon"] + ecart / 2
            murs.append(
                {
                    "cx": interieur["cx"],
                    "cy": interieur["cy"],
                    "rayon_axe": rayon_axe,
                    "debut": debut,
                    "fin": fin,
                    "epaisseur_m": round(ecart / m, 3),
                    "longueur_m": round((fin - debut) * rayon_axe / m, 3),
                    "arcs": (i, j),
                }
            )
    return murs


def _soustraire(intervalles: list[tuple[float, float]], a: float, b: float) -> list[tuple[float, float]]:
    resultat = []
    for debut, fin in intervalles:
        if b <= debut or a >= fin:
            resultat.append((debut, fin))
            continue
        if a > debut:
            resultat.append((debut, a))
        if b < fin:
            resultat.append((b, fin))
    return resultat


def _dans_anneau(x: float, y: float, points: list[tuple[float, float]]) -> bool:
    dedans = False
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            dedans = not dedans
    return dedans


def _retirer_vides_entre_murs(murs: list[dict], motifs: list[dict] | None) -> list[dict]:
    """Écarte les « murs » vides (sans remplissage ni motif d'isolant) dont les deux faces bordent déjà un autre
    mur de part et d'autre : c'est le vide entre deux murs (couloir étroit, gaine, joint), pas un mur."""

    def recouvre(a: dict, b: dict) -> bool:
        ux, uy = a["ux"], a["uy"]
        a1, a2 = _intervalle(a, ux, uy)
        b1, b2 = _intervalle(b, ux, uy)
        return min(a2, b2) - max(a1, b1) >= 0.5 * (a2 - a1)

    dessous: dict[int, list[int]] = defaultdict(list)  # face → murs dont elle est la face haute
    dessus: dict[int, list[int]] = defaultdict(list)  # face → murs dont elle est la face basse
    for numero, mur in enumerate(murs):
        dessous[mur["faces"][1]].append(numero)
        dessus[mur["faces"][0]].append(numero)

    def motif_dans(mur: dict) -> bool:
        if not motifs:
            return False
        ux, uy = mur["ux"], mur["uy"]
        t1, t2 = _intervalle(mur, ux, uy)
        compte = 0
        for ligne in motifs:
            x, y = (ligne["x1"] + ligne["x2"]) / 2, (ligne["y1"] + ligne["y2"]) / 2
            t, n = ux * x + uy * y, -uy * x + ux * y
            if t1 <= t <= t2 and mur["n_a"] < n < mur["n_b"]:
                compte += 1
                if compte >= 3:
                    return True
        return False

    gardes = []
    for numero, mur in enumerate(murs):
        vide = mur["remplissage"] is None or mur["remplissage"] < 0.5
        borde_bas = any(k != numero and recouvre(mur, murs[k]) for k in dessous[mur["faces"][0]])
        borde_haut = any(k != numero and recouvre(mur, murs[k]) for k in dessus[mur["faces"][1]])
        if vide and borde_bas and borde_haut and not motif_dans(mur):
            continue
        gardes.append(mur)
    return gardes


def apparier_faces(faces: list[dict], echelle: float, anneaux: list[dict] | None = None, motifs: list[dict] | None = None) -> list[dict]:
    """Segments de mur (axe, épaisseur, étendue, part remplie) à partir des lignes de faces.

    `motifs` : petites lignes de hachure (isolant), qui attestent qu'une bande sans remplissage est une couche."""
    m = 1.0 / pt_en_m(echelle)
    par_direction: dict[int, list[int]] = defaultdict(list)
    for index, face in enumerate(faces):
        par_direction[round(math.degrees(math.atan2(face["uy"], face["ux"])) / TOL_DIRECTION_DEG)].append(index)

    boites = []
    for anneau in anneaux or []:
        xs = [p[0] for p in anneau["points"]]
        ys = [p[1] for p in anneau["points"]]
        boites.append((min(xs), min(ys), max(xs), max(ys), anneau["points"]))

    def rempli(x: float, y: float) -> bool:
        return any(x0 <= x <= x1 and y0 <= y <= y1 and _dans_anneau(x, y, pts) for x0, y0, x1, y1, pts in boites)

    murs: list[dict] = []
    for cle, indices in par_direction.items():
        voisins = sorted(set(indices + par_direction.get(cle - 1, []) + par_direction.get(cle + 1, [])))
        ux = sum(faces[i]["ux"] for i in indices) / len(indices)
        uy = sum(faces[i]["uy"] for i in indices) / len(indices)
        norme = math.hypot(ux, uy)
        ux, uy = ux / norme, uy / norme

        def projeter(face):
            n = ((-uy * face["x1"] + ux * face["y1"]) + (-uy * face["x2"] + ux * face["y2"])) / 2
            t1, t2 = sorted((ux * face["x1"] + uy * face["y1"], ux * face["x2"] + uy * face["y2"]))
            return n, t1, t2

        projetes = {i: projeter(faces[i]) for i in voisins}
        ordre = sorted(voisins, key=lambda i: projetes[i][0])
        for i in indices:
            n_a, a1, a2 = projetes[i]
            for j in ordre:
                n_b, b1, b2 = projetes[j]
                ecart = n_b - n_a
                if j == i or ecart < EPAISSEUR_MUR_MIN_M * m:
                    continue
                if ecart > EPAISSEUR_MUR_MAX_M * m:
                    break
                debut, fin = max(a1, b1), min(a2, b2)
                if fin - debut < RECOUVREMENT_MIN_M * m:
                    continue
                libres = [(debut, fin)]
                for k in ordre:
                    n_c, c1, c2 = projetes[k]
                    if k in (i, j) or not (n_a + 0.5 < n_c < n_b - 0.5):
                        continue
                    libres = _soustraire(libres, c1, c2)
                    if not libres:
                        break
                # Une face non parallèle qui traverse la bande entre les deux faces (mur perpendiculaire, angle,
                # retour de gaine) coupe le mur : pas d'appariement à travers une jonction.
                if libres:
                    for face in faces:
                        if abs(face["ux"] * uy - face["uy"] * ux) < math.sin(math.radians(5)):
                            continue
                        ta = ux * face["x1"] + uy * face["y1"]
                        na = -uy * face["x1"] + ux * face["y1"]
                        tb = ux * face["x2"] + uy * face["y2"]
                        nb = -uy * face["x2"] + ux * face["y2"]
                        bas, haut = sorted((na, nb))
                        if haut <= n_a + 0.5 or bas >= n_b - 0.5 or abs(nb - na) < 1e-9:
                            continue
                        entree, sortie = max(bas, n_a), min(haut, n_b)
                        te = ta + (tb - ta) * (entree - na) / (nb - na)
                        ts = ta + (tb - ta) * (sortie - na) / (nb - na)
                        marge = face["largeur"] / 2 + 0.5
                        zone_bas, zone_haut = min(te, ts) - marge, max(te, ts) + marge
                        # Au bout du mur, la traversée est sa fermeture (trait de fin, angle) : elle ne retire rien.
                        if zone_bas <= debut or zone_haut >= fin:
                            continue
                        libres = _soustraire(libres, zone_bas, zone_haut)
                        if not libres:
                            break
                for t1, t2 in libres:
                    # Un mur est plus long qu'épais : un bloc de 36 × 72 cm n'est gardé que dans le sens où il
                    # mesure 36 cm d'épaisseur ; les reliquats de jonction plus courts que l'épaisseur disparaissent.
                    if t2 - t1 < max(RECOUVREMENT_MIN_M * m, ecart * 0.999):
                        continue
                    axe = (n_a + n_b) / 2
                    x1, y1 = t1 * ux - axe * uy, t1 * uy + axe * ux
                    x2, y2 = t2 * ux - axe * uy, t2 * uy + axe * ux
                    echantillons = max(1, int((t2 - t1) / (PAS_REMPLISSAGE_M * m)))
                    remplis = sum(
                        1
                        for k in range(echantillons)
                        if rempli(x1 + (x2 - x1) * (k + 0.5) / echantillons, y1 + (y2 - y1) * (k + 0.5) / echantillons)
                    ) if boites else 0
                    murs.append(
                        {
                            "x1": x1,
                            "y1": y1,
                            "x2": x2,
                            "y2": y2,
                            "epaisseur_m": round(ecart / m, 3),
                            "longueur_m": round((t2 - t1) / m, 3),
                            "faces": (i, j),
                            "ux": ux,
                            "uy": uy,
                            "n_a": n_a,
                            "n_b": n_b,
                            "remplissage": round(remplis / echantillons, 2) if boites else None,
                        }
                    )
    return _retirer_vides_entre_murs(murs, motifs)


# Aplats gris des murs coupés (luminance 118 à 153 sur le projet d'essai) ; le blanc et le noir sont écartés.
LUMINANCE_REMPLISSAGE = (96, 176)
LONGUEUR_MOTIF_MAX_M = 0.4
POINTS_PAR_ARC = 24


def detecter_murs(lignes: list[dict], aplats: list, echelle: float) -> dict:
    """Chaîne complète pour l'affichage : murs droits et courbes en polygones (points PDF), types par
    épaisseur et parois composées. `lignes` sort de `vecteurs.fusionner_lignes`, `aplats` de `traits.lire_aplats`."""
    from thermique_moteur import vecteurs

    m = 1.0 / pt_en_m(echelle)
    anneaux = vecteurs.unir_aplats([a for a in aplats if LUMINANCE_REMPLISSAGE[0] <= a[1] <= LUMINANCE_REMPLISSAGE[1]])
    toutes = faces_de_murs(lignes)
    arcs = arcs_de_faces(toutes, echelle)
    faces_arcs = {i for arc in arcs for i in arc["faces"]}
    faces = [face for i, face in enumerate(toutes) if i not in faces_arcs]
    motifs = [l for l in lignes if l.get("luminance", 0) > LUMINANCE_FACE_MAX and l["longueur"] <= LONGUEUR_MOTIF_MAX_M * m]
    droits = apparier_faces(faces, echelle, anneaux, motifs)
    courbes = apparier_arcs(arcs, echelle)

    def arrondi(points):
        return [[round(x, 2), round(y, 2)] for x, y in points]

    murs = []
    for mur in droits:
        demi = (mur["n_b"] - mur["n_a"]) / 2
        nx, ny = -mur["uy"] * demi, mur["ux"] * demi
        coins = [(mur["x1"] + nx, mur["y1"] + ny), (mur["x2"] + nx, mur["y2"] + ny), (mur["x2"] - nx, mur["y2"] - ny), (mur["x1"] - nx, mur["y1"] - ny)]
        murs.append(
            {"points": arrondi(coins), "epaisseur_m": mur["epaisseur_m"], "longueur_m": mur["longueur_m"], "rempli": (mur["remplissage"] or 0) >= 0.5}
        )
    for courbe in courbes:
        demi = courbe["epaisseur_m"] * m / 2
        angles = [courbe["debut"] + (courbe["fin"] - courbe["debut"]) * k / POINTS_PAR_ARC for k in range(POINTS_PAR_ARC + 1)]
        exterieur = [(courbe["cx"] + (courbe["rayon_axe"] + demi) * math.cos(a), courbe["cy"] + (courbe["rayon_axe"] + demi) * math.sin(a)) for a in angles]
        interieur = [(courbe["cx"] + (courbe["rayon_axe"] - demi) * math.cos(a), courbe["cy"] + (courbe["rayon_axe"] - demi) * math.sin(a)) for a in reversed(angles)]
        murs.append({"points": arrondi(exterieur + interieur), "epaisseur_m": courbe["epaisseur_m"], "longueur_m": courbe["longueur_m"], "rempli": True, "courbe": True})

    types: dict[int, dict] = {}
    for mur in murs:
        cm = round(mur["epaisseur_m"] * 100)
        entree = types.setdefault(cm, {"epaisseur_m": cm / 100, "longueur_m": 0.0, "nombre": 0})
        entree["longueur_m"] += mur["longueur_m"]
        entree["nombre"] += 1
    composees = [
        {
            "epaisseur_m": round(paroi["epaisseur_m"], 3),
            "couches_m": [round(couche["epaisseur_m"], 3) for couche in paroi["couches"]],
            "longueur_m": round(paroi["longueur_pt"] / m, 2),
        }
        for paroi in parois_composees(droits)
        if len(paroi["couches"]) > 1
    ]
    return {
        "echelle": echelle,
        "murs": murs,
        "types": sorted(({**t, "longueur_m": round(t["longueur_m"], 2)} for t in types.values()), key=lambda t: -t["longueur_m"]),
        "parois_composees": composees,
        "lineaire_m": round(sum(mur["longueur_m"] for mur in murs), 2),
    }
