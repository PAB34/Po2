"""Lecture vectorielle exacte d'une planche — jalon J1 de docs/thermique/detection-murs-strategie.md.

Aucun pixel : on travaille sur les coordonnées du PDF.

- **Fusion des lignes** : les faces de murs sont imprimées en morceaux (médiane 0,35 m sur le projet
  d'essai) ; les morceaux colinéaires d'une même plume (largeur, teinte) sont recollés.
- **Union des aplats** : les remplissages sont imprimés en triangles ; les arêtes communes à deux
  facettes s'annulent, les arêtes restantes forment le bord exact du remplissage.
- **Dictionnaire des plumes** : rôle probable de chaque plume d'après ses lignes (longueur, présence d'une
  ligne parallèle partenaire à 5-80 cm, signe d'une paire de faces de mur).
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict

from thermique_moteur.metre import pt_en_m

TOL_ANGLE_DEG = 0.1
TOL_DECALAGE_PT = 0.05
TOL_JOINTURE_PT = 0.1
TOL_SOMMET_PT = 0.01
EPAISSEUR_MUR_MIN_M = 0.05
EPAISSEUR_MUR_MAX_M = 0.80


def _orientation(x1: float, y1: float, x2: float, y2: float) -> tuple[float, float, float] | None:
    """Direction unitaire normalisée (demi-plan ux > 0, ou ux = 0 et uy > 0) et angle en degrés."""
    longueur = math.hypot(x2 - x1, y2 - y1)
    if longueur < 1e-9:
        return None
    ux, uy = (x2 - x1) / longueur, (y2 - y1) / longueur
    if ux < -1e-12 or (abs(ux) <= 1e-12 and uy < 0):
        ux, uy = -ux, -uy
    return ux, uy, math.degrees(math.atan2(uy, ux))


def fusionner_lignes(traits: list) -> list[dict]:
    """Recolle les morceaux colinéaires d'une même plume.

    `traits` : (x1, y1, x2, y2, largeur[, luminance]) en points PDF. Deux morceaux sont fusionnés s'ils ont
    la même plume, la même direction (± 0,1°), la même droite (± 0,05 pt) et se touchent (± 0,1 pt)."""
    par_direction: dict[tuple, list] = defaultdict(list)
    for t in traits:
        x1, y1, x2, y2, largeur = t[:5]
        luminance = t[5] if len(t) > 5 else 0
        orientation = _orientation(x1, y1, x2, y2)
        if orientation is None:
            continue
        ux, uy, angle = orientation
        par_direction[(largeur, luminance, round(angle / TOL_ANGLE_DEG))].append((x1, y1, x2, y2, ux, uy))

    lignes: list[dict] = []
    for (largeur, luminance, _), morceaux in par_direction.items():
        # direction moyenne du groupe, puis décalage de chaque morceau par rapport à l'origine
        ux = sum(m[4] for m in morceaux) / len(morceaux)
        uy = sum(m[5] for m in morceaux) / len(morceaux)
        norme = math.hypot(ux, uy)
        ux, uy = ux / norme, uy / norme
        projetes = []
        for x1, y1, x2, y2, _, _ in morceaux:
            n = ((-uy * x1 + ux * y1) + (-uy * x2 + ux * y2)) / 2
            t1, t2 = sorted((ux * x1 + uy * y1, ux * x2 + uy * y2))
            projetes.append((n, t1, t2))
        projetes.sort()
        droites: list[list] = []
        for item in projetes:
            if droites and item[0] - droites[-1][-1][0] <= TOL_DECALAGE_PT:
                droites[-1].append(item)
            else:
                droites.append([item])
        for droite in droites:
            n_moyen = sum(item[0] * (item[2] - item[1]) for item in droite) / max(1e-9, sum(item[2] - item[1] for item in droite))
            intervalles = sorted((item[1], item[2]) for item in droite)
            courant: list | None = None
            for t1, t2 in intervalles:
                if courant is not None and t1 <= courant[1] + TOL_JOINTURE_PT:
                    courant[1] = max(courant[1], t2)
                    courant[2] += 1
                else:
                    if courant is not None:
                        lignes.append(_ligne(courant, ux, uy, n_moyen, largeur, luminance))
                    courant = [t1, t2, 1]
            if courant is not None:
                lignes.append(_ligne(courant, ux, uy, n_moyen, largeur, luminance))
    return lignes


def _ligne(intervalle: list, ux: float, uy: float, n: float, largeur: float, luminance: int) -> dict:
    t1, t2, morceaux = intervalle
    return {
        "x1": t1 * ux - n * uy,
        "y1": t1 * uy + n * ux,
        "x2": t2 * ux - n * uy,
        "y2": t2 * uy + n * ux,
        "ux": ux,
        "uy": uy,
        "n": n,
        "t1": t1,
        "t2": t2,
        "longueur": t2 - t1,
        "largeur": largeur,
        "luminance": luminance,
        "morceaux": morceaux,
    }


def unir_aplats(aplats: list) -> list[dict]:
    """Union exacte des facettes de même teinte : anneaux de bord (points PDF), aire signée, nombre de facettes."""
    par_teinte: dict[int, list] = defaultdict(list)
    for contour, luminance in aplats:
        par_teinte[luminance].append(contour)

    def cle(point):
        return (round(point[0] / TOL_SOMMET_PT), round(point[1] / TOL_SOMMET_PT))

    resultat: list[dict] = []
    for luminance, contours in par_teinte.items():
        comptes: Counter = Counter()
        aretes: list[tuple] = []
        for contour in contours:
            sommets = []
            for point in contour:
                k = cle(point)
                if not sommets or sommets[-1] != k:
                    sommets.append(k)
            if len(sommets) > 1 and sommets[0] == sommets[-1]:
                sommets.pop()
            for i, a in enumerate(sommets):
                b = sommets[(i + 1) % len(sommets)]
                if a != b:
                    k = (min(a, b), max(a, b))
                    comptes[k] += 1
                    aretes.append(k)
        bord = [k for k in dict.fromkeys(aretes) if comptes[k] % 2 == 1]
        voisins: dict[tuple, list] = defaultdict(list)
        for a, b in bord:
            voisins[a].append(b)
            voisins[b].append(a)
        utilisees: set = set()
        for a, b in bord:
            if (a, b) in utilisees:
                continue
            utilisees.add((a, b))
            anneau, precedent, courant = [a, b], a, b
            while True:
                suivant = next((c for c in voisins[courant] if (min(courant, c), max(courant, c)) not in utilisees), None)
                if suivant is None:
                    break
                utilisees.add((min(courant, suivant), max(courant, suivant)))
                if suivant == anneau[0]:
                    break
                anneau.append(suivant)
                precedent, courant = courant, suivant
            points = [(x * TOL_SOMMET_PT, y * TOL_SOMMET_PT) for x, y in anneau]
            aire = sum(points[i - 1][0] * points[i][1] - points[i][0] * points[i - 1][1] for i in range(len(points))) / 2
            resultat.append({"luminance": luminance, "points": points, "aire_pt2": aire, "facettes": len(contours)})
    return resultat


def _apparier(lignes: list[dict], m: float) -> set[int]:
    """Indices des lignes qui ont une ligne parallèle à 5-80 cm les recouvrant sur au moins la moitié de la plus courte."""
    appariees: set[int] = set()
    par_direction: dict[int, list] = defaultdict(list)
    for index, ligne in enumerate(lignes):
        angle = math.degrees(math.atan2(ligne["uy"], ligne["ux"]))
        par_direction[round(angle / 0.5)].append((ligne["n"], index))
    for cle, items in par_direction.items():
        voisins = items + par_direction.get(cle - 1, []) + par_direction.get(cle + 1, [])
        voisins.sort()
        positions = [n for n, _ in voisins]
        for n, i in items:
            a = lignes[i]
            debut = _bisect(positions, n + EPAISSEUR_MUR_MIN_M * m)
            for k in range(debut, len(voisins)):
                n_autre, j = voisins[k]
                if n_autre - n > EPAISSEUR_MUR_MAX_M * m:
                    break
                b = lignes[j]
                if abs(a["ux"] * b["uy"] - a["uy"] * b["ux"]) > math.sin(math.radians(0.5)):
                    continue
                tb1, tb2 = sorted((a["ux"] * b["x1"] + a["uy"] * b["y1"], a["ux"] * b["x2"] + a["uy"] * b["y2"]))
                recouvrement = min(a["t2"], tb2) - max(a["t1"], tb1)
                if recouvrement >= 0.5 * min(a["longueur"], b["longueur"]) and recouvrement > 0:
                    appariees.update((i, j))
    return appariees


def _bisect(valeurs: list[float], cible: float) -> int:
    bas, haut = 0, len(valeurs)
    while bas < haut:
        milieu = (bas + haut) // 2
        if valeurs[milieu] < cible:
            bas = milieu + 1
        else:
            haut = milieu
    return bas


def dictionnaire_plumes(lignes: list[dict], echelle: float) -> list[dict]:
    """Plumes de la planche (largeur, teinte) avec leurs statistiques et leur rôle probable."""
    m = 1.0 / pt_en_m(echelle)
    appariees = _apparier([ligne for ligne in lignes], m)
    par_plume: dict[tuple, list] = defaultdict(list)
    for index, ligne in enumerate(lignes):
        par_plume[(ligne["largeur"], ligne["luminance"])].append(index)
    largeur_max = max((ligne["largeur"] for ligne in lignes), default=0.0)
    plumes = []
    for (largeur, luminance), indices in par_plume.items():
        longueurs = sorted(lignes[i]["longueur"] / m for i in indices)
        total = sum(longueurs)
        part_appariee = sum(lignes[i]["longueur"] / m for i in indices if i in appariees) / total if total else 0.0
        mediane = longueurs[len(longueurs) // 2]
        if part_appariee >= 0.5 and largeur >= 0.5 * largeur_max:
            role = "faces de murs"
        elif part_appariee >= 0.3 and luminance <= 64:
            role = "faces fines (cloisons, menuiseries)"
        elif mediane < 0.15 and luminance > 64:
            role = "hachures et motifs"
        else:
            role = "autres (cotes, axes, mobilier, cadre)"
        plumes.append(
            {
                "largeur": largeur,
                "luminance": luminance,
                "lignes": len(indices),
                "longueur_m": round(total, 1),
                "mediane_m": round(mediane, 3),
                "part_appariee": round(part_appariee, 3),
                "role": role,
            }
        )
    return sorted(plumes, key=lambda plume: (-plume["largeur"], plume["luminance"]))
