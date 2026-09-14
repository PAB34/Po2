"""Deux lignes d'un niveau — nu extérieur et nu intérieur — déduites des murs vectoriels (lot G1).

Voir docs/thermique/detection-guidee-decisions.md §6 (D4, D5). Entrée : les murs de `murs.detecter_murs`
(polygones en points PDF ; un mur droit a ses deux faces sur les arêtes 0-1 et 2-3).

1. **Emprise** : murs dessinés en masque, refermés de 1,6 m (baies jusqu'à 3,2 m), trous remplis, plus grande
   composante. Le masque ne sert qu'à trouver la forme ; il n'en sort aucune position.
2. **Nu extérieur** : bord de l'emprise simplifié, puis chaque côté **posé sur la face de mur vectorielle**
   parallèle qui le couvre le mieux ; les sommets sont les intersections exactes des faces consécutives.
3. **Nu intérieur** : pour chaque côté du nu extérieur, empilement des murs parallèles collés à la face
   extérieure (mur, puis doublage…) ; la profondeur de la pile donne la face intérieure, tronçon par tronçon.
   Aux baies (pas de mur), la profondeur des tronçons voisins est reprise.

Limite connue : un mur courbe est approché par les côtés du nu extérieur ; son épaisseur y est celle des
tronçons voisins.
"""
from __future__ import annotations

import math

import numpy as np

from thermique_moteur.detection import _bord_exterieur, _cross, _dilater, _eroder, _simplifier_ferme
from thermique_moteur.metre import pt_en_m

PX_PAR_PT = 1.5
FERMETURE_BAIES_M = 1.6
TOLERANCE_SIMPLIFICATION_M = 0.08
# Écart maximal entre un côté de l'emprise et la face de mur sur laquelle on le pose.
TOLERANCE_CALAGE_M = 0.15
# Un côté sans face plus court que ceci est un pan coupé du masque : ses voisins se prolongent.
PAN_SANS_FACE_MAX_M = 1.5
TOL_PARALLELE_DEG = 3.0
TOL_PILE_M = 0.04
PROFONDEUR_MAX_M = 1.2
TRONCON_MIN_M = 0.10


def _aire(points) -> float:
    return sum(points[i - 1][0] * points[i][1] - points[i][0] * points[i - 1][1] for i in range(len(points))) / 2


def _intersection(a1, d1, a2, d2, repli):
    denominateur = float(_cross(d1, d2))
    if abs(denominateur) < 1e-9:
        return repli
    return a1 + float(_cross(a2 - a1, d2)) / denominateur * d1


def _nettoyer(sommets: list, m: float) -> list:
    propres: list = []
    for s in sommets:
        if not propres or math.hypot(s[0] - propres[-1][0], s[1] - propres[-1][1]) >= 0.01 * m:
            propres.append(s)
    if len(propres) > 1 and math.hypot(propres[0][0] - propres[-1][0], propres[0][1] - propres[-1][1]) < 0.01 * m:
        propres.pop()
    change = True
    while change and len(propres) > 3:
        change = False
        for i in range(len(propres)):
            a, b, c = np.array(propres[i - 1]), np.array(propres[i]), np.array(propres[(i + 1) % len(propres)])
            if abs(float(_cross(b - a, c - b))) / (float(np.hypot(*(c - a))) or 1.0) < 0.01 * m:
                propres.pop(i)
                change = True
                break
    return propres


def _poser_sur_faces(polygone: list, faces: list, m: float) -> list:
    """Chaque côté prend la droite de la face parallèle qui le couvre le mieux (± 15 cm)."""
    n = len(polygone)
    droites, appuis, longueurs = [], [], []
    for i in range(n):
        p, q = np.array(polygone[i], float), np.array(polygone[(i + 1) % n], float)
        longueur = float(np.hypot(*(q - p)))
        longueurs.append(longueur)
        if longueur < 1e-9:
            droites.append((p, np.array([1.0, 0.0])))
            appuis.append(False)
            continue
        u = (q - p) / longueur
        normale = np.array([-u[1], u[0]])
        groupes: dict[int, dict] = {}
        for a, b in faces:
            w = b - a
            lw = float(np.hypot(*w))
            if lw < 0.05 * m or abs(float(_cross(u, w / lw))) > math.sin(math.radians(TOL_PARALLELE_DEG)):
                continue
            decalage = float(np.dot((a + b) / 2 - p, normale))
            if abs(decalage) > TOLERANCE_CALAGE_M * m:
                continue
            ta, tb = sorted((float(np.dot(a - p, u)), float(np.dot(b - p, u))))
            recouvrement = min(tb, longueur) - max(ta, 0.0)
            if recouvrement <= 0:
                continue
            groupe = groupes.setdefault(round(decalage / (0.02 * m)), {"recouvrement": 0.0, "appui": None, "lw": 0.0})
            groupe["recouvrement"] += recouvrement
            if lw > groupe["lw"]:
                groupe["appui"], groupe["lw"] = (a, w / lw), lw
        candidats = [g for g in groupes.values() if g["recouvrement"] >= 0.3 * longueur]
        if candidats:
            point, direction = max(candidats, key=lambda g: g["recouvrement"])["appui"]
            droites.append((point, direction if float(np.dot(direction, u)) >= 0 else -direction))
            appuis.append(True)
        else:
            droites.append((p, u))
            appuis.append(False)
    gardes = [i for i in range(n) if appuis[i] or longueurs[i] >= PAN_SANS_FACE_MAX_M * m]
    if len(gardes) < 3:
        gardes = list(range(n))
    sommets = []
    for j, i in enumerate(gardes):
        (a1, d1), (a2, d2) = droites[gardes[j - 1]], droites[i]
        repli = np.array(polygone[i], float)
        if abs(float(_cross(d1, d2))) < 1e-6:
            # Deux côtés posés sur des droites parallèles : même face (sommet inutile) ou marche d'équerre.
            if abs(float(_cross(d1, a2 - a1))) < 0.01 * m:
                continue
            for a, d in ((a1, d1), (a2, d2)):
                projete = a + float(np.dot(repli - a, d)) * d
                sommets.append((float(projete[0]), float(projete[1])))
            continue
        point = _intersection(a1, d1, a2, d2, repli)
        if float(np.hypot(*(point - repli))) > (PAN_SANS_FACE_MAX_M + 0.5) * m:
            point = repli
        sommets.append((float(point[0]), float(point[1])))
    return _nettoyer(sommets, m)


def _nu_interieur(exterieur: list, droits: list[np.ndarray], m: float) -> tuple[list, float | None]:
    n = len(exterieur)
    sens = 1.0 if _aire(exterieur) > 0 else -1.0  # sens trigonométrique : l'intérieur est à gauche
    cotes = []
    for i in range(n):
        p, q = np.array(exterieur[i], float), np.array(exterieur[(i + 1) % n], float)
        longueur = float(np.hypot(*(q - p)))
        u = (q - p) / (longueur or 1.0)
        vers_interieur = np.array([-u[1], u[0]]) * sens
        intervalles = []
        for points in droits:
            direction = points[1] - points[0]
            ld = float(np.hypot(*direction))
            if ld < 1e-9 or abs(float(_cross(u, direction / ld))) > math.sin(math.radians(TOL_PARALLELE_DEG)):
                continue
            o = (points - p) @ vers_interieur
            t = (points - p) @ u
            o1, o2 = float(o.min()), float(o.max())
            if o2 < -TOL_PILE_M * m or o1 > PROFONDEUR_MAX_M * m:
                continue
            t1, t2 = max(float(t.min()), 0.0), min(float(t.max()), longueur)
            if t2 - t1 >= 0.02 * m:
                intervalles.append((t1, t2, o1, o2))
        bornes = sorted({0.0, longueur, *[v for t1, t2, _, _ in intervalles for v in (t1, t2)]})
        troncons = []
        for a, b in zip(bornes, bornes[1:]):
            if b - a < 1e-6:
                continue
            milieu = (a + b) / 2
            couvrants = [(o1, o2) for t1, t2, o1, o2 in intervalles if t1 <= milieu <= t2]
            profondeur, trouve = 0.0, False
            for _ in range(6):
                suivants = [o2 for o1, o2 in couvrants if abs(o1 - profondeur) <= TOL_PILE_M * m and o2 > profondeur + 0.02 * m]
                if not suivants:
                    break
                profondeur, trouve = max(suivants), True
            troncons.append([a, b, profondeur if trouve else None])
        cotes.append((p, u, vers_interieur, troncons))

    connues = [(b - a, d) for _, _, _, troncons in cotes for a, b, d in troncons if d is not None]
    if not connues:
        return [], None
    connues.sort(key=lambda item: item[1])
    cumul, typique = 0.0, connues[0][1]
    for poids, valeur in connues:
        cumul += poids
        if cumul >= sum(poids for poids, _ in connues) / 2:
            typique = valeur
            break

    for _, _, _, troncons in cotes:
        # baies : profondeur du tronçon précédent, sinon du suivant, sinon profondeur typique du niveau
        for k, troncon in enumerate(troncons):
            if troncon[2] is None:
                avant = next((troncons[j][2] for j in range(k - 1, -1, -1) if troncons[j][2] is not None), None)
                apres = next((troncons[j][2] for j in range(k + 1, len(troncons)) if troncons[j][2] is not None), None)
                troncon[2] = avant if avant is not None else apres if apres is not None else typique
        # petits tronçons (artefacts de jonction) absorbés par leur voisin
        for k, troncon in enumerate(troncons):
            if troncon[1] - troncon[0] < TRONCON_MIN_M * m and len(troncons) > 1:
                troncon[2] = troncons[k - 1][2] if k > 0 else troncons[k + 1][2]
        fusion: list = []
        for troncon in troncons:
            if fusion and abs(fusion[-1][2] - troncon[2]) <= 0.01 * m:
                fusion[-1][1] = troncon[1]
            else:
                fusion.append(list(troncon))
        troncons[:] = fusion

    sommets = []
    for i, (p, u, vers_interieur, troncons) in enumerate(cotes):
        pp, pu, pv, ptroncons = cotes[i - 1]
        dernier = ptroncons[-1][2]
        premier = troncons[0][2]
        repli = p + vers_interieur * premier
        point = _intersection(pp + pv * dernier, pu, p + vers_interieur * premier, u, repli)
        if float(np.hypot(*(point - repli))) > 2 * PROFONDEUR_MAX_M * m:
            point = repli
        sommets.append((float(point[0]), float(point[1])))
        for k in range(1, len(troncons)):
            t = troncons[k][0]
            for profondeur in (troncons[k - 1][2], troncons[k][2]):
                s = p + u * t + vers_interieur * profondeur
                sommets.append((float(s[0]), float(s[1])))
    return _nettoyer(sommets, m), typique / m


def _resume(points: list, m: float) -> dict:
    perimetre = sum(math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]) for i in range(len(points)))
    return {
        "points": [[round(x, 3), round(y, 3)] for x, y in points],
        "aire_m2": round(abs(_aire(points)) / m / m, 2),
        "perimetre_m": round(perimetre / m, 2),
    }


def detecter_deux_lignes(murs: list[dict], echelle: float) -> dict | None:
    """Nu extérieur et nu intérieur proposés à partir des murs d'un plan de niveau."""
    from PIL import Image, ImageDraw
    from scipy import ndimage

    if len(murs) < 3:
        return None
    m = 1.0 / pt_en_m(echelle)
    xs = [p[0] for mur in murs for p in mur["points"]]
    ys = [p[1] for mur in murs for p in mur["points"]]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    marge = (FERMETURE_BAIES_M + 1.0) * m
    largeur_px = int((x1 - x0 + 2 * marge) * PX_PAR_PT) + 1
    hauteur_px = int((y1 - y0 + 2 * marge) * PX_PAR_PT) + 1

    image = Image.new("1", (largeur_px, hauteur_px), 0)
    dessin = ImageDraw.Draw(image)
    for mur in murs:
        dessin.polygon([((x - x0 + marge) * PX_PAR_PT, (y1 + marge - y) * PX_PAR_PT) for x, y in mur["points"]], fill=1, outline=1)
    masque = np.array(image, dtype=bool)
    r = m * PX_PAR_PT
    ferme = _eroder(ndimage, _dilater(ndimage, masque, FERMETURE_BAIES_M * r), FERMETURE_BAIES_M * r)
    plein = ndimage.binary_fill_holes(ferme | masque)
    etiquettes, nombre = ndimage.label(plein)
    if nombre == 0:
        return None
    tailles = ndimage.sum(plein, etiquettes, range(1, nombre + 1))
    emprise = etiquettes == int(np.argmax(tailles)) + 1
    chemin = _bord_exterieur(ndimage, emprise)
    if len(chemin) < 8:
        return None
    polygone = [(x / PX_PAR_PT + x0 - marge, y1 + marge - y / PX_PAR_PT) for x, y in _simplifier_ferme(chemin, TOLERANCE_SIMPLIFICATION_M * r)]

    droits = [np.array(mur["points"], float) for mur in murs if not mur.get("courbe") and len(mur["points"]) == 4]
    faces = [(points[a], points[b]) for points in droits for a, b in ((0, 1), (2, 3))]
    exterieur = _poser_sur_faces(polygone, faces, m)
    if len(exterieur) < 3:
        return None
    interieur, epaisseur = _nu_interieur(exterieur, droits, m)
    if len(interieur) < 3:
        return None
    return {
        "nu_exterieur": _resume(exterieur, m),
        "nu_interieur": _resume(interieur, m),
        "epaisseur_typique_m": round(epaisseur, 3) if epaisseur is not None else None,
    }
