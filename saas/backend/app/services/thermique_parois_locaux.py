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


def _parallele(a0: tuple[float, float], a1: tuple[float, float], b0: tuple[float, float], b1: tuple[float, float]) -> bool:
    ua, ub = (a1[0] - a0[0], a1[1] - a0[1]), (b1[0] - b0[0], b1[1] - b0[1])
    na, nb = math.hypot(*ua), math.hypot(*ub)
    if na == 0 or nb == 0:
        return False
    return abs(ua[0] * ub[0] + ua[1] * ub[1]) / (na * nb) >= PARALLELE_COS


def _distance_au_segment(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    longueur2 = dx * dx + dy * dy
    t = 0.0 if longueur2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / longueur2))
    return math.dist(p, (a[0] + t * dx, a[1] + t * dy))


def correspond(trace_a: list[list[float]], trace_b: list[list[float]], manifeste: dict[str, Any]) -> bool:
    """Deux tracés de paroi désignent-ils la même paroi : milieux proches et directions parallèles ?"""
    (a0, a1), (b0, b1) = _segment_m(trace_a, manifeste), _segment_m(trace_b, manifeste)
    milieu_a = ((a0[0] + a1[0]) / 2, (a0[1] + a1[1]) / 2)
    milieu_b = ((b0[0] + b1[0]) / 2, (b0[1] + b1[1]) / 2)
    return math.dist(milieu_a, milieu_b) <= CORRESPONDANCE_M and _parallele(a0, a1, b0, b1)


def couverture(trace_composition: list[list[float]], trace_paroi: list[list[float]], manifeste: dict[str, Any]) -> float | None:
    """D265 : la composition couvre-t-elle cette paroi ? Oui si le milieu de la paroi est à moins de 30 cm de son
    tracé, parallèle. Rend l'écart entre les deux milieux (la plus proche l'emporte), sinon None."""
    (c0, c1), (p0, p1) = _segment_m(trace_composition, manifeste), _segment_m(trace_paroi, manifeste)
    milieu = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
    if _distance_au_segment(milieu, c0, c1) > CORRESPONDANCE_M or not _parallele(c0, c1, p0, p1):
        return None
    return math.dist(milieu, ((c0[0] + c1[0]) / 2, (c0[1] + c1[1]) / 2))


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
            couvrantes = [(ecart, rang) for rang, c in enumerate(candidates)
                          if (ecart := couverture(c["trace"], paroi["trace"], manifeste)) is not None]
            trouvee = candidates[min(couvrantes)[1]] if couvrantes else None
            proposition = paroi.get("proposition") or {}
            if trouvee:
                paroi["composition"] = {k: trouvee[k] for k in ("id", "composant", "couches", "epaisseur_cm")}
            elif proposition.get("validee") and proposition.get("couches"):
                # Le travail déjà fait sur les murs du relevé n'est pas perdu : une composition validée là y est
                # reprise comme validée (option C, « rien n'est perdu »). La valider ici la remplace.
                paroi["composition"] = {"id": "releve", "reprise": True,
                                        **{k: proposition[k] for k in ("composant", "couches", "epaisseur_cm")}}
            else:
                paroi["composition"] = None


# ---------------------------------------------------------------------------------------------------------
# D264 : couper une paroi par des points, quand sa composition change en cours de côté.

COUPURE_DOUBLON_M = 0.10


def _local_existe(contenu: dict[str, Any], local: str) -> None:
    if not any(o.get("id") == local and o.get("category") == "piece" for o in contenu["analyse"].get("objects", [])):
        raise ThermiqueError("Le local de cette paroi est introuvable.")


def _point(valeur: Any) -> list[float]:
    if not isinstance(valeur, (list, tuple)) or len(valeur) != 2:
        raise ThermiqueError("Le point de coupure est invalide.")
    x, y = float(valeur[0]), float(valeur[1])
    if not 0 <= x <= 1000 or not 0 <= y <= 1000:
        raise ThermiqueError("Le point de coupure sort de la feuille.")
    return [round(x, 3), round(y, 3)]


def _ecart_m(a: list[float], b: list[float], manifeste: dict[str, Any]) -> float:
    mx, my = _metres(manifeste)
    return math.hypot((a[0] - b[0]) * mx, (a[1] - b[1]) * my)


def couper(contenu: dict[str, Any], operation: dict[str, Any]) -> dict[str, Any]:
    """Pose une coupure sur une paroi d'un local (D264) ; la paroi se coupe au recalcul."""
    local = str(operation.get("local") or "")
    _local_existe(contenu, local)
    point = _point(operation.get("point"))
    manifeste = contenu["enveloppe"]["manifeste"]
    coupures = contenu.setdefault("coupures_parois", [])
    existante = next((c for c in coupures if c["local"] == local and _ecart_m(c["point"], point, manifeste) <= COUPURE_DOUBLON_M), None)
    if existante:
        return existante
    coupure = {"id": uuid.uuid4().hex[:12], "local": local, "point": point}
    coupures.append(coupure)
    return coupure


def recoller(contenu: dict[str, Any], operation: dict[str, Any]) -> None:
    """Retire la coupure la plus proche du point, à moins de 30 cm (D264)."""
    local = str(operation.get("local") or "")
    point = _point(operation.get("point"))
    manifeste = contenu["enveloppe"]["manifeste"]
    coupures = contenu.get("coupures_parois", [])
    proches = sorted((_ecart_m(c["point"], point, manifeste), rang) for rang, c in enumerate(coupures) if c["local"] == local)
    if not proches or proches[0][0] > CORRESPONDANCE_M:
        raise ThermiqueError("Aucune coupure de paroi à cet endroit.")
    del coupures[proches[0][1]]
