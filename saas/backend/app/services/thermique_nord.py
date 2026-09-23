"""Nord de la planche (D85).

Le thermicien trace une flèche sur le plan : **de la base vers la pointe, la pointe du côté du nord**.
C'est le geste qu'il fait déjà au crayon sur un tirage papier, et il n'a qu'une lecture possible.

La flèche est enregistrée en **coordonnées PDF**, comme la cote de contrôle d'échelle. C'est le seul repère
qui ne bouge pas : la rotation d'affichage d'une planche peut changer, le rendu raster avec elle, mais les
points PDF restent les mêmes. Le nord posé une fois reste juste même si la planche est tournée ensuite.

L'angle utile au calcul, lui, se mesure **dans le repère de l'image** (x vers la droite, y vers le bas),
depuis le haut de la feuille et dans le sens horaire : c'est ce qu'attend
``thermique_fiches_locaux.orientation``. La conversion passe par la partie linéaire de la matrice du rendu.
"""
from __future__ import annotations

import json
import math
from typing import Any

from app.models.thermique import ThermiqueSheet

# Sous cette longueur, la flèche est un geste raté plutôt qu'une direction.
LONGUEUR_MIN_PT = 8.0
# Secteurs de lecture, pour dire le nord en français plutôt qu'en degrés.
SECTEURS = (
    "vers le haut de la planche",
    "vers le haut à droite",
    "vers la droite de la planche",
    "vers le bas à droite",
    "vers le bas de la planche",
    "vers le bas à gauche",
    "vers la gauche de la planche",
    "vers le haut à gauche",
)


def vecteur_du_nord(nord: dict[str, Any]) -> tuple[float, float]:
    """Direction du nord en coordonnées PDF, de la base vers la pointe."""
    (x1, y1), (x2, y2) = nord["p1"], nord["p2"]
    return float(x2) - float(x1), float(y2) - float(y1)


def azimut_dans_l_image(nord: dict[str, Any] | None, transform: list[Any]) -> float | None:
    """Angle du nord depuis le haut de l'image, sens horaire, tel que l'attend ``orientation``.

    ``transform`` est la matrice du rendu pdfium : ``px = a·x + c·y + e``, ``py = b·x + d·y + f``.
    Seule sa partie linéaire nous intéresse — une direction ne se translate pas.
    """
    if not nord:
        return None
    a, b, c, d = (float(valeur) for valeur in transform[:4])
    dx, dy = vecteur_du_nord(nord)
    px, py = a * dx + c * dy, b * dx + d * dy
    if math.hypot(px, py) < 1e-9:
        return None
    return math.degrees(math.atan2(px, -py)) % 360


def lecture_en_clair(azimut_deg: float) -> str:
    """« vers le haut à droite » : le thermicien contrôle d'un coup d'œil qu'il ne s'est pas trompé."""
    return SECTEURS[round(azimut_deg / 45) % 8]


def charger(sheet: ThermiqueSheet) -> dict[str, Any] | None:
    if not sheet.north_json:
        return None
    try:
        nord = json.loads(sheet.north_json)
        if not isinstance(nord, dict):
            return None
        return poser(nord["p1"], nord["p2"], float(sheet.page_width_pt), float(sheet.page_height_pt))
    except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError):
        return None


def poser(
    p1: list[float], p2: list[float], largeur_pt: float | None = None, hauteur_pt: float | None = None
) -> dict[str, Any]:
    """Valide puis prépare la flèche tracée par le thermicien.

    Quand les dimensions sont fournies, les deux clics doivent appartenir à la page. Cette vérification
    est refaite côté serveur : l'interface n'est pas la seule porte d'entrée de la route.
    """
    valeurs = [float(p1[0]), float(p1[1]), float(p2[0]), float(p2[1])]
    if not all(math.isfinite(valeur) for valeur in valeurs):
        raise ValueError("Les points de la flèche du nord sont invalides.")
    if largeur_pt is not None and hauteur_pt is not None:
        largeur, hauteur = float(largeur_pt), float(hauteur_pt)
        if largeur <= 0 or hauteur <= 0:
            raise ValueError("Les dimensions de la planche sont invalides.")
        if not all((0 <= x <= largeur and 0 <= y <= hauteur) for x, y in (valeurs[:2], valeurs[2:])):
            raise ValueError("La flèche du nord doit rester dans la planche.")
    dx, dy = valeurs[2] - valeurs[0], valeurs[3] - valeurs[1]
    longueur = math.hypot(dx, dy)
    if longueur < LONGUEUR_MIN_PT:
        raise ValueError("La flèche du nord est trop courte : repartez de sa base vers sa pointe.")
    return {
        "p1": [round(valeurs[0], 3), round(valeurs[1], 3)],
        "p2": [round(valeurs[2], 3), round(valeurs[3], 3)],
        "longueur_pt": round(longueur, 3),
    }


def adapter_a_planche(
    nord: dict[str, Any], largeur_source: float, hauteur_source: float, largeur_cible: float, hauteur_cible: float
) -> dict[str, Any]:
    """Copie une direction sur une autre page sans recopier aveuglément sa position.

    La base garde sa position relative dans la feuille ; la longueur est mise à l'échelle uniformément
    par la plus petite dimension. Une translation finale garantit que la flèche entière reste visible,
    même si les deux pages n'ont pas les mêmes proportions.
    """
    dimensions = [largeur_source, hauteur_source, largeur_cible, hauteur_cible]
    if not all(math.isfinite(float(valeur)) and float(valeur) > 0 for valeur in dimensions):
        raise ValueError("Les dimensions des planches sont invalides.")
    dx, dy = vecteur_du_nord(nord)
    longueur = math.hypot(dx, dy)
    if longueur < LONGUEUR_MIN_PT:
        raise ValueError("La flèche du nord est trop courte : repartez de sa base vers sa pointe.")

    facteur = min(float(largeur_cible), float(hauteur_cible)) / min(
        float(largeur_source), float(hauteur_source)
    )
    x1 = float(nord["p1"][0]) * float(largeur_cible) / float(largeur_source)
    y1 = float(nord["p1"][1]) * float(hauteur_cible) / float(hauteur_source)
    x2 = x1 + dx * facteur
    y2 = y1 + dy * facteur

    # Une simple translation conserve la direction. Le cas pathologique d'une flèche plus grande que
    # la page est évité en plafonnant sa longueur d'affichage — l'azimut, lui, ne change pas.
    longueur_cible = math.hypot(x2 - x1, y2 - y1)
    maximum = math.hypot(float(largeur_cible), float(hauteur_cible)) * 0.9
    if longueur_cible > maximum:
        rapport = maximum / longueur_cible
        x2, y2 = x1 + (x2 - x1) * rapport, y1 + (y2 - y1) * rapport

    min_x, max_x = min(x1, x2), max(x1, x2)
    min_y, max_y = min(y1, y2), max(y1, y2)
    decalage_x = -min_x if min_x < 0 else float(largeur_cible) - max_x if max_x > largeur_cible else 0.0
    decalage_y = -min_y if min_y < 0 else float(hauteur_cible) - max_y if max_y > hauteur_cible else 0.0
    return poser(
        [x1 + decalage_x, y1 + decalage_y],
        [x2 + decalage_x, y2 + decalage_y],
        float(largeur_cible),
        float(hauteur_cible),
    )
