"""Angle réel des angles sortants et rentrants, et minoration de leur ψ (remarque E, D160).

Le catalogue NF EN ISO 14683 ne donne que des angles droits, et aucune norme du dossier ne traite d'un
autre angle. Règle retenue par l'utilisateur : proportionnalité au changement de direction,
ψ(θ) = ψ₉₀ × θ / 90 — un angle à 90° garde sa valeur, un pan coupé à 45° en perd la moitié.

L'angle se lit entre le tronçon qui porte l'angle et celui qui le prolonge, à l'extrémité la plus proche.
Sur le R+1, les 72 tronçons de façade forment une boucle fermée ; les 17 tronçons lus depuis la face
intérieure sont des morceaux, qui ne se prolongent que là où ils se touchent.
"""
from __future__ import annotations

import math
from typing import Any

ANGLES = ("angle_sortant", "angle_rentrant")
# Un angle plus loin que cela de l'extrémité de son tronçon n'est pas à une jonction : on ne devine pas.
PORTEE_JONCTION_M = 1.0
# Deux tronçons se prolongent quand la fin de l'un est le début de l'autre, à cette tolérance près.
JOINT_M = 0.05
# En deçà, le tracé ne tourne presque pas : ce n'est sans doute pas un angle (5 cas sur 64 au R+1).
ANGLE_PLAT_DEG = 15
# Au-delà, l'angle est plus fermé qu'un pan coupé ordinaire : épingle du tracé plus souvent qu'un mur.
ANGLE_FERME_DEG = 135


def _voisin(troncons: list[dict[str, Any]], rang: int, cote: str, perimetre: float) -> dict[str, Any] | None:
    troncon = troncons[rang]
    exterieur = troncon.get("ligne") != "face_interieure"
    for autre in troncons:
        if autre is troncon or (autre.get("ligne") != "face_interieure") != exterieur:
            continue
        if cote == "fin":
            ecart = autre["debut_m"] - troncon["fin_m"]
        else:
            ecart = troncon["debut_m"] - autre["fin_m"]
        # La façade est une boucle : le dernier tronçon rejoint le premier, un périmètre plus loin.
        if exterieur and perimetre:
            ecart = min(abs(ecart), abs(abs(ecart) - perimetre))
        if abs(ecart) <= JOINT_M:
            return autre
    return None


def angle_mesure(element: dict[str, Any], manifeste: dict[str, Any]) -> float | None:
    """Changement de direction à l'angle, en degrés (90 = angle droit), ou None s'il ne se lit pas.

    Un pont posé à la main n'est pas à une jonction de tronçons : son angle ne se mesure pas, il se saisit.
    """
    if element.get("type") not in ANGLES or element.get("point_feuille"):
        return None
    troncons = manifeste.get("troncons") or []
    rang = next((i for i, t in enumerate(troncons) if t.get("id") == element.get("troncon")), None)
    if rang is None:
        return None
    troncon = troncons[rang]
    milieu = (float(element["debut_m"]) + float(element["fin_m"])) / 2
    vers_debut, vers_fin = milieu - troncon["debut_m"], troncon["fin_m"] - milieu
    cote = "debut" if vers_debut <= vers_fin else "fin"
    if min(vers_debut, vers_fin) > PORTEE_JONCTION_M:
        return None
    perimetre = float(manifeste.get("perimetre_m") or 0)
    voisin = _voisin(troncons, rang, cote, perimetre)
    if voisin is None:
        return None
    (ux, uy), (vx, vy) = troncon["direction"], voisin["direction"]
    return round(math.degrees(math.atan2(abs(ux * vy - uy * vx), ux * vx + uy * vy)), 1)


def angle_retenu(element: dict[str, Any], manifeste: dict[str, Any]) -> float | None:
    """L'angle saisi par le thermicien l'emporte sur la mesure du tracé."""
    saisi = element.get("angle_deg")
    return float(saisi) if isinstance(saisi, (int, float)) else angle_mesure(element, manifeste)


def coefficient(angle_deg: float | None) -> float:
    """Minoration proportionnelle (D160) ; sans angle connu, on garde l'angle droit du catalogue."""
    return 1.0 if angle_deg is None else round(angle_deg / 90, 3)
