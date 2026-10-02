"""Compositions des parois des locaux (option C, D255, D261).

Un mur n'est plus un tracé à part : c'est la composition affectée à une paroi d'un local (une portion droite de
son contour). Les parois se recalculent à chaque recalcul depuis les contours ; la composition validée par le
thermicien est donc rangée à part, avec le local et le tracé de la paroi, et se raccroche à chaque recalcul à la
paroi du même local qui tombe au même endroit (milieu à moins de 30 cm, direction parallèle).
"""
from __future__ import annotations

import math
import uuid
from typing import Any

from app.services import thermique_elements as elements_releve
from app.services.thermique import ThermiqueError

CORRESPONDANCE_M = 0.30
PARALLELE_COS = 0.95


def _metres(manifeste: dict[str, Any]) -> tuple[float, float]:
    """Mètres par unité de feuille (0 à 1000), en x et en y."""
    largeur, hauteur = manifeste["page_px"]
    return largeur / 1000 / manifeste["px_par_m"], hauteur / 1000 / manifeste["px_par_m"]


def _segment_m(trace: list[list[float]], manifeste: dict[str, Any]) -> tuple[tuple[float, float], tuple[float, float]]:
    mx, my = _metres(manifeste)
    (x0, y0), (x1, y1) = trace[0], trace[-1]
    return (x0 * mx, y0 * my), (x1 * mx, y1 * my)


def correspond(trace_a: list[list[float]], trace_b: list[list[float]], manifeste: dict[str, Any]) -> bool:
    """Deux tracés de paroi désignent-ils la même paroi : milieux proches et directions parallèles ?"""
    (a0, a1), (b0, b1) = _segment_m(trace_a, manifeste), _segment_m(trace_b, manifeste)
    milieu_a = ((a0[0] + a1[0]) / 2, (a0[1] + a1[1]) / 2)
    milieu_b = ((b0[0] + b1[0]) / 2, (b0[1] + b1[1]) / 2)
    if math.dist(milieu_a, milieu_b) > CORRESPONDANCE_M:
        return False
    ua, ub = (a1[0] - a0[0], a1[1] - a0[1]), (b1[0] - b0[0], b1[1] - b0[1])
    na, nb = math.hypot(*ua), math.hypot(*ub)
    if na == 0 or nb == 0:
        return False
    return abs(ua[0] * ub[0] + ua[1] * ub[1]) / (na * nb) >= PARALLELE_COS


def _trace(valeur: Any) -> list[list[float]]:
    if not isinstance(valeur, list) or len(valeur) != 2:
        raise ThermiqueError("La paroi se désigne par son tracé : deux points.")
    points = []
    for point in valeur:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ThermiqueError("Un point du tracé de la paroi est invalide.")
        x, y = float(point[0]), float(point[1])
        if not 0 <= x <= 1000 or not 0 <= y <= 1000:
            raise ThermiqueError("Le tracé de la paroi sort de la feuille.")
        points.append([round(x, 3), round(y, 3)])
    return points


def composer(contenu: dict[str, Any], operation: dict[str, Any]) -> dict[str, Any]:
    """Valide la composition d'une paroi d'un local (D261) ; remplace celle déjà donnée à cette paroi."""
    local = str(operation.get("local") or "")
    if not any(objet.get("id") == local and objet.get("category") == "piece" for objet in contenu["analyse"].get("objects", [])):
        raise ThermiqueError("Le local de cette paroi est introuvable.")
    trace = _trace(operation.get("trace"))
    couches = [{"nature": c["nature"], "epaisseur_cm": c["epaisseur_cm"]} for c in elements_releve._couches(operation.get("couches"))]
    manifeste = contenu["enveloppe"]["manifeste"]
    compositions = contenu.setdefault("compositions_parois", [])
    gardees = [c for c in compositions if not (c.get("local") == local and correspond(c["trace"], trace, manifeste))]
    entree = {
        "id": uuid.uuid4().hex[:12],
        "local": local,
        "trace": trace,
        "composant": (str(operation.get("composant") or "").strip() or None),
        "couches": couches,
        "epaisseur_cm": round(sum(c["epaisseur_cm"] for c in couches), 1),
    }
    contenu["compositions_parois"] = gardees + [entree]
    return entree


def affecter(locaux: list[dict[str, Any]], compositions: list[dict[str, Any]], manifeste: dict[str, Any]) -> None:
    """Pose sur chaque paroi la composition validée qui lui correspond (D261)."""
    par_local: dict[str, list[dict[str, Any]]] = {}
    for composition in compositions:
        par_local.setdefault(composition.get("local"), []).append(composition)
    for local in locaux:
        candidates = par_local.get(local.get("id"), [])
        for paroi in (local.get("fiche") or {}).get("parois", []):
            trouvee = next((c for c in candidates if correspond(c["trace"], paroi["trace"], manifeste)), None)
            paroi["composition"] = (
                {k: trouvee[k] for k in ("id", "composant", "couches", "epaisseur_cm")} if trouvee else None
            )
