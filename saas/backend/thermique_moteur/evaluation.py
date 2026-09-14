"""Mesure de la détection des murs contre une vérité terrain — §5 de docs/thermique/detection-murs-strategie.md.

Référence et détection sont des segments d'axe de mur (points PDF) avec leur épaisseur. Un mur de référence
est « retrouvé » sur la portion couverte par des murs détectés parallèles (± 2°) dont l'axe passe à moins
de 2 cm ; symétriquement, un linéaire détecté non couvert par la référence est un faux mur.
"""
from __future__ import annotations

import math

from thermique_moteur.metre import pt_en_m

TOL_AXE_M = 0.02
TOL_ANGLE_DEG = 2.0
TOL_EPAISSEUR_M = 0.01
LONGUEUR_SIGNIFICATIVE_M = 0.5


def _couverture(cible: dict, candidats: list[dict], m: float) -> tuple[float, list[tuple[float, float, float]]]:
    """Longueur de `cible` couverte par les `candidats` compatibles, et portions (t1, t2, épaisseur candidate)."""
    longueur = math.hypot(cible["x2"] - cible["x1"], cible["y2"] - cible["y1"])
    if longueur < 1e-9:
        return 0.0, []
    ux, uy = (cible["x2"] - cible["x1"]) / longueur, (cible["y2"] - cible["y1"]) / longueur
    portions = []
    for autre in candidats:
        lo = math.hypot(autre["x2"] - autre["x1"], autre["y2"] - autre["y1"])
        if lo < 1e-9:
            continue
        vx, vy = (autre["x2"] - autre["x1"]) / lo, (autre["y2"] - autre["y1"]) / lo
        if abs(ux * vy - uy * vx) > math.sin(math.radians(TOL_ANGLE_DEG)):
            continue
        distances = [abs(-uy * (x - cible["x1"]) + ux * (y - cible["y1"])) for x, y in ((autre["x1"], autre["y1"]), (autre["x2"], autre["y2"]))]
        if max(distances) > TOL_AXE_M * m:
            continue
        t1, t2 = sorted(((autre["x1"] - cible["x1"]) * ux + (autre["y1"] - cible["y1"]) * uy, (autre["x2"] - cible["x1"]) * ux + (autre["y2"] - cible["y1"]) * uy))
        t1, t2 = max(t1, 0.0), min(t2, longueur)
        if t2 > t1:
            portions.append((t1, t2, autre["epaisseur_m"]))
    portions.sort()
    couvert, courant = 0.0, None
    for t1, t2, _ in portions:
        if courant is None or t1 > courant[1]:
            if courant is not None:
                couvert += courant[1] - courant[0]
            courant = [t1, t2]
        else:
            courant[1] = max(courant[1], t2)
    if courant is not None:
        couvert += courant[1] - courant[0]
    return couvert, portions


def evaluer_murs(detectes: list[dict], reference: list[dict], echelle: float) -> dict:
    m = 1.0 / pt_en_m(echelle)
    total_reference = total_couvert = 0.0
    manques, ecarts_epaisseur = [], []
    for index, mur in enumerate(reference):
        longueur = math.hypot(mur["x2"] - mur["x1"], mur["y2"] - mur["y1"])
        couvert, portions = _couverture(mur, detectes, m)
        total_reference += longueur
        total_couvert += couvert
        if longueur - couvert > LONGUEUR_SIGNIFICATIVE_M * m * 0.1:
            manques.append({"reference": index, "manque_m": round((longueur - couvert) / m, 3), "longueur_m": round(longueur / m, 3)})
        for t1, t2, epaisseur in portions:
            ecarts_epaisseur.append((abs(epaisseur - mur["epaisseur_m"]), (t2 - t1) / m, index))
    total_detecte = total_juste = 0.0
    faux = []
    for index, mur in enumerate(detectes):
        longueur = math.hypot(mur["x2"] - mur["x1"], mur["y2"] - mur["y1"])
        couvert, _ = _couverture(mur, reference, m)
        total_detecte += longueur
        total_juste += couvert
        if (longueur - couvert) / m >= LONGUEUR_SIGNIFICATIVE_M:
            faux.append({"detecte": index, "exces_m": round((longueur - couvert) / m, 3), "epaisseur_m": mur["epaisseur_m"]})
    longueur_mesuree = sum(l for _, l, _ in ecarts_epaisseur)
    return {
        "lineaire_reference_m": round(total_reference / m, 2),
        "lineaire_detecte_m": round(total_detecte / m, 2),
        "rappel": round(total_couvert / total_reference, 4) if total_reference else None,
        "precision": round(total_juste / total_detecte, 4) if total_detecte else None,
        "part_epaisseur_a_1cm": round(sum(l for e, l, _ in ecarts_epaisseur if e <= TOL_EPAISSEUR_M + 1e-9) / longueur_mesuree, 4)
        if longueur_mesuree
        else None,
        "ecart_epaisseur_max_m": round(max((e for e, _, _ in ecarts_epaisseur), default=0.0), 3),
        "murs_manques": manques,
        "faux_murs": faux,
    }
