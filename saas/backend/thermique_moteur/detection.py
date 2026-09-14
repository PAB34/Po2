"""Détection automatique du contour au nu intérieur d'un niveau (lot M3).

Chaîne, validée sur les plans du projet d'essai (2026-09-14) :

1. **faces de murs** = traits épais, prolongées de 1,4 m dans leur axe pour boucher portes et
   fenêtres ; les traits fins **foncés** (vitrages, menuiseries) servent aussi de barrière ;
2. **bâtiment** = la composante la plus dense de traits foncés (écarte cadre et cartouche) ;
3. **extérieur** = remplissage depuis le bord ; **emprise** = le reste ;
4. **pièces** = emprise sans murs épais ni longues lignes (≥ 2 m), sans les vides étroits entre deux
   faces ; une pièce densément **hachurée en gris** qui touche l'extérieur est dehors (terrasse,
   coursive) ;
5. union des pièces refermée de 35 cm (absorbe cloisons et refends) → bord extérieur ;
6. polygone simplifié, puis chaque côté **recalé sur la face de mur vectorielle** la plus proche.

Le résultat est une **proposition** : le thermicien la corrige avec les outils du métré.
Voir docs/thermique/agent-verification-decisions.md et metre-plans-decisions.md.
"""
from __future__ import annotations

import math

import numpy as np

from thermique_moteur.metre import pt_en_m

PX_PAR_PT = 1.5
PROLONGEMENT_M = 1.4
LARGEUR_BARRIERE_MIN = 0.24
LUMINANCE_FONCEE_MAX = 64
LONGUEUR_BARRIERE_MIN_M = 0.3
LONGUE_BARRIERE_M = 2.0
LUMINANCE_HACHURE = (64, 200)
LARGEUR_HACHURE = (0.2, 0.6)
DENSITE_HACHURE_MAX = 0.08
DEMI_VIDE_ENTRE_FACES_M = 0.30
FERMETURE_M = 0.35
SURFACE_PIECE_MIN_M2 = 1.0
TOLERANCE_SIMPLIFICATION_M = 0.12
# Distance maximale entre le contour détecté et la face intérieure du mur sur laquelle on le recale.
TOLERANCE_RECALAGE_M = 1.5
EPAISSEUR_MUR_MIN_M = 0.08
EPAISSEUR_MUR_MAX_M = 0.80


def _cross(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def _dilater(ndimage, masque, rayon_px):
    return ndimage.distance_transform_edt(~masque) <= rayon_px


def _eroder(ndimage, masque, rayon_px):
    return ndimage.distance_transform_edt(masque) > rayon_px


def _bord_exterieur(ndimage, masque) -> list[tuple[int, int]]:
    """Suivi de Moore du bord de la plus grande composante (trous remplis)."""
    etiquettes, n = ndimage.label(masque)
    if n == 0:
        return []
    tailles = ndimage.sum(masque, etiquettes, range(1, n + 1))
    garde = ndimage.binary_fill_holes(etiquettes == int(np.argmax(tailles)) + 1)
    ys, xs = np.nonzero(garde)
    i = int(np.argmin(ys * garde.shape[1] + xs))
    depart = (int(xs[i]), int(ys[i]))
    voisins = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
    hauteur, largeur = garde.shape
    chemin = [depart]
    courant, direction = depart, 7
    for _ in range(8 * (hauteur + largeur) * 10):
        suivant = None
        for k in range(8):
            d = (direction + 6 + k) % 8
            nx, ny = courant[0] + voisins[d][0], courant[1] + voisins[d][1]
            if 0 <= nx < largeur and 0 <= ny < hauteur and garde[ny, nx]:
                suivant = ((nx, ny), d)
                break
        if suivant is None:
            break
        courant, direction = suivant
        if courant == depart:
            break
        chemin.append(courant)
    return chemin


def _douglas_peucker(points: list, tolerance: float) -> list:
    pile, garder = [(0, len(points) - 1)], {0, len(points) - 1}
    tableau = np.asarray(points, float)
    while pile:
        debut, fin = pile.pop()
        if fin - debut < 2:
            continue
        a, b = tableau[debut], tableau[fin]
        norme = float(np.hypot(*(b - a))) or 1.0
        distances = np.abs(_cross(b - a, tableau[debut + 1 : fin] - a)) / norme
        k = int(np.argmax(distances))
        if distances[k] > tolerance:
            milieu = debut + 1 + k
            garder.add(milieu)
            pile.extend([(debut, milieu), (milieu, fin)])
    return [points[i] for i in sorted(garder)]


def _simplifier_ferme(points: list, tolerance: float) -> list:
    loin = max(range(len(points)), key=lambda i: math.hypot(points[i][0] - points[0][0], points[i][1] - points[0][1]))
    aller = _douglas_peucker(points[: loin + 1], tolerance)
    retour = _douglas_peucker(points[loin:] + [points[0]], tolerance)
    return aller[:-1] + retour[:-1]


def _recaler(polygone: list, faces: list, m: float) -> list:
    """Remplace chaque côté par la ligne de face de mur parallèle qui le recouvre le mieux ; les sommets
    deviennent les intersections des droites consécutives.

    Une face est souvent dessinée en nombreux petits morceaux : les morceaux alignés (même décalage à
    1 cm près) sont additionnés. Le côté reste en place s'il repose déjà sur une face ; sinon il est
    poussé sur la ligne de face la mieux couverte à moins de `TOLERANCE_RECALAGE_M` (constaté au
    niveau 2 du projet d'essai : contour arrêté sur un trait fin 60 cm avant le mur)."""
    droites = []
    appuis: list[bool] = []
    longueurs: list[float] = []
    n = len(polygone)
    aire_signee = sum(polygone[i - 1][0] * polygone[i][1] - polygone[i][0] * polygone[i - 1][1] for i in range(n))
    # Normale à gauche du côté : l'intérieur si le polygone tourne dans le sens trigonométrique.
    vers_exterieur = -1.0 if aire_signee > 0 else 1.0
    for i in range(n):
        p, q = np.array(polygone[i]), np.array(polygone[(i + 1) % n])
        longueur = float(np.hypot(*(q - p)))
        longueurs.append(longueur)
        if longueur == 0:
            droites.append((p, np.array([1.0, 0.0])))
            appuis.append(False)
            continue
        u = (q - p) / longueur
        normale = np.array([-u[1], u[0]])
        lignes: dict[int, dict] = {}
        portee = (TOLERANCE_RECALAGE_M + EPAISSEUR_MUR_MAX_M) * m
        for x1, y1, x2, y2 in faces:
            a, w = np.array([x1, y1]), np.array([x2 - x1, y2 - y1])
            lw = float(np.hypot(*w))
            if lw < 0.05 * m or abs(_cross(u, w / lw)) > math.sin(math.radians(6)):
                continue
            # Décalage compté positivement vers l'extérieur du bâtiment.
            decalage = float(np.dot(a + w / 2 - p, normale)) * vers_exterieur
            if abs(decalage) > portee:
                continue
            ta, tb = sorted((float(np.dot(a - p, u)), float(np.dot(a + w - p, u))))
            recouvrement = min(tb, longueur) - max(ta, 0.0)
            if recouvrement <= 0:
                continue
            ligne = lignes.setdefault(
                round(decalage / (0.01 * m)), {"recouvrement": 0.0, "decalage": 0.0, "poids": 0.0, "appui": None, "lw": 0.0}
            )
            ligne["recouvrement"] += recouvrement
            ligne["decalage"] += decalage * recouvrement
            ligne["poids"] += recouvrement
            if lw > ligne["lw"]:
                ligne["appui"], ligne["lw"] = (a, w / lw), lw
        # regroupe les classes voisines (± 1 cm) avant de comparer
        fusion: list[dict] = []
        for cle in sorted(lignes):
            ligne = lignes[cle]
            if fusion and cle - fusion[-1]["cle"] <= 1:
                cible = fusion[-1]
                cible["recouvrement"] += ligne["recouvrement"]
                cible["decalage"] += ligne["decalage"]
                cible["poids"] += ligne["poids"]
                if ligne["lw"] > cible["lw"]:
                    cible["appui"], cible["lw"] = ligne["appui"], ligne["lw"]
                cible["cle"] = cle
            else:
                fusion.append({**ligne, "cle": cle})
        # Au moins 30 % du côté : un bout de mur de 4 m sur une façade de 26 m ne suffit pas à le retenir.
        suffisant = [ligne for ligne in fusion if ligne["recouvrement"] >= 0.3 * longueur]
        for ligne in suffisant:
            ligne["d"] = ligne["decalage"] / ligne["poids"]
        # Face intérieure d'un mur = ligne bien couverte qui a, côté extérieur, sa face extérieure parallèle
        # à 8-80 cm. On retient la plus proche, vers l'intérieur comme vers l'extérieur : le contour
        # détecté peut s'arrêter avant le mur (trait fin, niveau 2) ou le dépasser (bande plantée, niveau 0).
        faces_interieures = [
            ligne
            for ligne in suffisant
            if abs(ligne["d"]) <= TOLERANCE_RECALAGE_M * m
            and any(EPAISSEUR_MUR_MIN_M * m <= autre["d"] - ligne["d"] <= EPAISSEUR_MUR_MAX_M * m for autre in suffisant)
        ]
        if faces_interieures:
            choix = min(faces_interieures, key=lambda ligne: abs(ligne["d"]))
        else:
            en_place = [ligne for ligne in suffisant if abs(ligne["d"]) <= 0.05 * m]
            dehors = [ligne for ligne in suffisant if 0.03 * m < ligne["d"] <= TOLERANCE_RECALAGE_M * m]
            choix = en_place[0] if en_place else (min(dehors, key=lambda ligne: ligne["d"]) if dehors else None)
        if choix is not None:
            point, direction = choix["appui"]
            if float(np.dot(direction, u)) < 0:
                direction = -direction
            droites.append((point, direction))
            appuis.append(True)
        else:
            droites.append((p, u))
            appuis.append(False)
    # Les petits pans sans face (angles coupés par le tracé en pixels) disparaissent : les côtés appuyés
    # voisins se prolongent jusqu'à leur intersection.
    gardes = [i for i in range(n) if appuis[i] or longueurs[i] >= 0.3 * m]
    if len(gardes) < 3:
        gardes = list(range(n))
    sommets = []
    for j, i in enumerate(gardes):
        (a1, d1), (a2, d2) = droites[gardes[j - 1]], droites[i]
        denominateur = float(_cross(d1, d2))
        if abs(denominateur) < 1e-6:
            sommets.append((float(polygone[i][0]), float(polygone[i][1])))
            continue
        intersection = a1 + float(_cross(a2 - a1, d2)) / denominateur * d1
        if float(np.hypot(*(intersection - np.array(polygone[i])))) > 1.5 * m:
            sommets.append((float(polygone[i][0]), float(polygone[i][1])))
        else:
            sommets.append((float(intersection[0]), float(intersection[1])))
    propres: list = []
    for s in sommets:
        if not propres or math.hypot(s[0] - propres[-1][0], s[1] - propres[-1][1]) >= 0.02 * m:
            propres.append(s)
    change = True
    while change and len(propres) > 3:
        change = False
        for i in range(len(propres)):
            a, b, c = (np.array(propres[i - 1]), np.array(propres[i]), np.array(propres[(i + 1) % len(propres)]))
            if abs(float(_cross(b - a, c - b))) / (float(np.hypot(*(c - a))) or 1.0) < 0.02 * m:
                propres.pop(i)
                change = True
                break
    return propres


def detecter_contour(traits: list, seuil: float, echelle: float) -> dict | None:
    """Contour au nu intérieur proposé pour un plan de niveau.

    `traits` : segments (x1, y1, x2, y2, largeur, luminance) en points PDF, `seuil` : épaisseur
    minimale des faces de murs, `echelle` : dénominateur (100 pour 1/100).
    """
    from PIL import Image, ImageDraw
    from scipy import ndimage

    m = 1.0 / pt_en_m(echelle)  # points PDF par mètre
    faces = [t for t in traits if t[4] >= seuil - 1e-6 and math.hypot(t[2] - t[0], t[3] - t[1]) >= 0.5]
    if len(faces) < 4:
        return None
    xs = [v for t in faces for v in (t[0], t[2])]
    ys = [v for t in faces for v in (t[1], t[3])]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    marge = 3 * m
    largeur_px = int((x1 - x0 + 2 * marge) * PX_PAR_PT) + 1
    hauteur_px = int((y1 - y0 + 2 * marge) * PX_PAR_PT) + 1

    def px(x, y):
        return ((x - x0 + marge) * PX_PAR_PT, (y1 + marge - y) * PX_PAR_PT)

    def dans_cadre(t):
        return x0 - marge <= t[0] <= x1 + marge and y0 - marge <= t[1] <= y1 + marge

    image_murs = Image.new("1", (largeur_px, hauteur_px), 0)
    image_faces = Image.new("1", (largeur_px, hauteur_px), 0)
    image_fonces = Image.new("1", (largeur_px, hauteur_px), 0)
    image_hachures = Image.new("1", (largeur_px, hauteur_px), 0)
    d_murs, d_faces = ImageDraw.Draw(image_murs), ImageDraw.Draw(image_faces)
    d_fonces, d_hachures = ImageDraw.Draw(image_fonces), ImageDraw.Draw(image_hachures)

    for xa, ya, xb, yb, *_ in faces:
        longueur = math.hypot(xb - xa, yb - ya)
        ux, uy = (xb - xa) / longueur, (yb - ya) / longueur
        e = PROLONGEMENT_M * m if longueur >= 0.15 * m else 0.0
        d_murs.line([px(xa - ux * e, ya - uy * e), px(xb + ux * e, yb + uy * e)], fill=1, width=2)
        d_faces.line([px(xa, ya), px(xb, yb)], fill=1, width=2)
        d_fonces.line([px(xa, ya), px(xb, yb)], fill=1, width=2)
    for t in traits:
        if len(t) < 6 or not dans_cadre(t):
            continue
        xa, ya, xb, yb, largeur, luminance = t[:6]
        longueur = math.hypot(xb - xa, yb - ya)
        if luminance <= LUMINANCE_FONCEE_MAX and largeur >= LARGEUR_BARRIERE_MIN - 1e-6 and longueur >= LONGUEUR_BARRIERE_MIN_M * m:
            d_murs.line([px(xa, ya), px(xb, yb)], fill=1, width=2)
            d_fonces.line([px(xa, ya), px(xb, yb)], fill=1, width=2)
            if longueur >= LONGUE_BARRIERE_M * m:
                d_faces.line([px(xa, ya), px(xb, yb)], fill=1, width=2)
        elif (
            LUMINANCE_HACHURE[0] < luminance <= LUMINANCE_HACHURE[1]
            and LARGEUR_HACHURE[0] - 1e-6 <= largeur <= LARGEUR_HACHURE[1] + 1e-6
            and longueur >= 0.05 * m
        ):
            d_hachures.line([px(xa, ya), px(xb, yb)], fill=1, width=1)

    murs = np.array(image_murs, dtype=bool)
    murs_epais = np.array(image_faces, dtype=bool)
    fonces = np.array(image_fonces, dtype=bool)
    hachures = np.array(image_hachures, dtype=bool)
    r = m * PX_PAR_PT  # pixels par mètre

    groupes, n = ndimage.label(_dilater(ndimage, fonces, 0.5 * r))
    if n == 0:
        return None
    poids = ndimage.sum(fonces, groupes, range(1, n + 1))
    scores = []
    for k, (tranche, p) in enumerate(zip(ndimage.find_objects(groupes), poids), 1):
        surface = (tranche[0].stop - tranche[0].start) * (tranche[1].stop - tranche[1].start)
        scores.append((p * p / surface, k))
    batiment = groupes == max(scores)[1]
    murs &= _dilater(ndimage, batiment, 2 * r)

    libres, _ = ndimage.label(~_dilater(ndimage, murs, 1))
    exterieur = libres == libres[0, 0]
    emprise = ~exterieur

    pieces = emprise & ~_dilater(ndimage, murs_epais, 1)
    pieces = _dilater(ndimage, _eroder(ndimage, pieces, DEMI_VIDE_ENTRE_FACES_M * r), DEMI_VIDE_ENTRE_FACES_M * r)
    etiquettes, n = ndimage.label(pieces)
    ecartees = 0
    if n:
        index = range(1, n + 1)
        tailles = ndimage.sum(pieces, etiquettes, index)
        densites = ndimage.sum(hachures, etiquettes, index) / np.maximum(tailles, 1)
        contacts = ndimage.sum(_dilater(ndimage, exterieur, 0.6 * r), etiquettes, index)
        assez_grandes = tailles >= SURFACE_PIECE_MIN_M2 * r * r
        dehors = (densites >= DENSITE_HACHURE_MAX) & (contacts >= 0.6 * r * r)
        ecartees = int((assez_grandes & dehors).sum())
        pieces = np.isin(etiquettes, 1 + np.nonzero(assez_grandes & ~dehors)[0])

    union = _eroder(ndimage, _dilater(ndimage, pieces, FERMETURE_M * r), FERMETURE_M * r) & emprise
    chemin = _bord_exterieur(ndimage, union)
    if len(chemin) < 8:
        return None
    polygone_px = _simplifier_ferme(chemin, TOLERANCE_SIMPLIFICATION_M * r)
    polygone = [(x / PX_PAR_PT + x0 - marge, y1 + marge - y / PX_PAR_PT) for x, y in polygone_px]
    points = _recaler(polygone, [t[:4] for t in faces], m)
    if len(points) < 3:
        return None
    aire = abs(sum(points[i][0] * points[i - 1][1] - points[i - 1][0] * points[i][1] for i in range(len(points)))) / 2
    perimetre = sum(math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]) for i in range(len(points)))
    return {
        "points": [[round(x, 3), round(y, 3)] for x, y in points],
        "aire_m2": round(aire / m / m, 2),
        "perimetre_m": round(perimetre / m, 2),
        "zones_exterieures_ecartees": ecartees,
    }
