"""Géométrie de l'étude d'un niveau : qualification des limites et contrôle de couverture (D59, D60).

Le comparatif d'agents du 2026-09-23 a montré que 15 % de la surface des pièces change d'une lecture à
l'autre, même entre deux lectures du même agent : les contours importés sont une proposition, jamais un
relevé. La réponse (décision A6) est de séparer ce que la machine garantit de ce qu'elle propose :

* la **couverture physique** de l'intérieur est contrôlée ici, contre l'emprise ``batiment_px`` trouvée sur
  le raster par le parcours d'enveloppe ;
* les **limites fonctionnelles** — les côtés qui ne suivent aucune paroi dessinée — sont qualifiées ici pour
  que le thermicien sache lesquelles il peut déplacer librement.

Tout se calcule dans le repère de la page haute définition (``manifeste["page_px"]``), le même que
``pieces_du_plan`` : les contours des locaux y arrivent normalisés de 0 à 1000.
"""
from __future__ import annotations

from typing import Any

from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import unary_union

from app.services import thermique_enveloppe_pieces as pieces_env
from app.services import thermique_fiches_locaux as fiches_locaux

# Un côté est dit « sur paroi » si le plan montre un mur à moins de cette distance de son axe.
SEUIL_PAROI_M = 0.35
# Pas de sondage le long d'un côté ; sous cette longueur le côté est jugé d'un seul tenant.
PAS_COTE_M = 0.10
# Part des sondages qui doit trouver une paroi pour que le côté entier soit qualifié.
PART_QUALIFIEE = 0.60
# Catégories du plan qui matérialisent une séparation construite.
PAROIS = {"mur_exterieur", "refend", "cloison", "doublage", "poteau"}
BAIES = {"menuiserie_exterieure", "menuiserie_interieure"}

LIMITES = ("exterieur", "paroi", "convention")


def _echelle(manifeste: dict[str, Any]) -> tuple[float, float, float]:
    largeur, hauteur = manifeste["page_px"]
    return float(largeur), float(hauteur), float(manifeste["px_par_m"])


def _en_px(points: list[list[float]], largeur: float, hauteur: float) -> list[tuple[float, float]]:
    return [(x * largeur / 1000, y * hauteur / 1000) for x, y in points]


def _en_normalise(points: Any, largeur: float, hauteur: float) -> list[list[float]]:
    return [[round(x * 1000 / largeur, 3), round(y * 1000 / hauteur, 3)] for x, y in points]


def emprise_interieure(manifeste: dict[str, Any]) -> Polygon:
    """Intérieur du niveau tel que le raster le donne, patios et trémies déduits."""
    batiment = fiches_locaux.batiment_du_manifeste(manifeste)
    trous = [Polygon(trou).buffer(0) for trou in manifeste.get("trous_px", []) if len(trou) >= 3]
    for trou in trous:
        if trou.area > 0:
            batiment = batiment.difference(trou)
    return batiment


def _lignes_des_parois(analyse: dict[str, Any], largeur: float, hauteur: float) -> list[Any]:
    """Axes des séparations construites, baies comprises : une baie ferme bien un local."""
    lignes = []
    for objet in analyse.get("objects", []):
        if objet.get("category") not in PAROIS | BAIES:
            continue
        points = objet.get("points") or []
        if len(points) < 2:
            continue
        sommets = _en_px(points, largeur, hauteur)
        if objet.get("geometry_type") == "polygon" and len(sommets) >= 3:
            forme = Polygon(sommets).buffer(0)
            if not forme.is_empty:
                lignes.append(forme.exterior if isinstance(forme, Polygon) else forme.boundary)
                continue
        lignes.append(LineString(sommets))
    return lignes


def qualifier_limites(
    contour: list[list[float]],
    manifeste: dict[str, Any],
    lignes: list[Any],
    bord_emprise: Any,
) -> list[str]:
    """Nature de chaque côté du contour : ``exterieur``, ``paroi`` ou ``convention`` (D59).

    Le contour est fermé : le côté d'indice i va du sommet i au sommet i+1, le dernier revenant au premier.
    """
    largeur, hauteur, px_par_m = _echelle(manifeste)
    sommets = _en_px(contour, largeur, hauteur)
    seuil_px = SEUIL_PAROI_M * px_par_m
    pas_px = max(PAS_COTE_M * px_par_m, 1.0)
    resultat = []
    for rang, depart in enumerate(sommets):
        arrivee = sommets[(rang + 1) % len(sommets)]
        cote = LineString([depart, arrivee])
        nombre = max(2, int(cote.length / pas_px) + 1)
        exterieur = paroi = 0
        for indice in range(nombre):
            point = cote.interpolate(indice / (nombre - 1), normalized=True)
            if bord_emprise is not None and bord_emprise.distance(point) <= seuil_px:
                exterieur += 1
            elif any(ligne.distance(point) <= seuil_px for ligne in lignes):
                paroi += 1
        if exterieur / nombre >= PART_QUALIFIEE:
            resultat.append("exterieur")
        elif (exterieur + paroi) / nombre >= PART_QUALIFIEE:
            resultat.append("paroi")
        else:
            resultat.append("convention")
    return resultat


def limites_des_locaux(analyse: dict[str, Any], manifeste: dict[str, Any]) -> dict[str, list[str]]:
    """Qualification des côtés de chaque local, indexée par son identifiant d'analyse."""
    largeur, hauteur, _ = _echelle(manifeste)
    lignes = _lignes_des_parois(analyse, largeur, hauteur)
    emprise = emprise_interieure(manifeste)
    bord = emprise.boundary if not emprise.is_empty else None
    resultat = {}
    for objet in analyse.get("objects", []):
        if objet.get("category") != "piece" or len(objet.get("points", [])) < 3:
            continue
        identifiant = str(objet.get("id") or "").strip()
        if identifiant:
            resultat[identifiant] = qualifier_limites(objet["points"], manifeste, lignes, bord)
    return resultat


def _polygone(contour: list[list[float]], largeur: float, hauteur: float) -> Polygon:
    return Polygon(_en_px(contour, largeur, hauteur)).buffer(0)


def _morceaux(forme: Any) -> list[Polygon]:
    if forme.is_empty:
        return []
    if isinstance(forme, MultiPolygon):
        return [part for part in forme.geoms if isinstance(part, Polygon) and part.area > 0]
    return [forme] if isinstance(forme, Polygon) and forme.area > 0 else []


# Sous cette surface, un écart de couverture n'est que du bruit de tracé (un demi-mètre carré).
BRUIT_M2 = 0.5


def controler_couverture(
    contours: dict[str, list[list[float]]],
    manifeste: dict[str, Any],
) -> dict[str, Any]:
    """Confronte l'union des locaux à l'emprise intérieure du raster (D60).

    ``contours`` associe l'identifiant d'un local à son contour normalisé de 0 à 1000.
    """
    largeur, hauteur, px_par_m = _echelle(manifeste)
    m2 = px_par_m * px_par_m
    bruit_px = BRUIT_M2 * m2
    emprise = emprise_interieure(manifeste)
    formes = {identifiant: _polygone(contour, largeur, hauteur) for identifiant, contour in contours.items()}
    union = unary_union([forme for forme in formes.values() if forme.area > 0]) if formes else Polygon()

    manque = emprise.difference(union) if not emprise.is_empty else Polygon()
    debord = union.difference(emprise) if not emprise.is_empty else Polygon()
    zones = sorted(_morceaux(manque), key=lambda part: part.area, reverse=True)
    zones = [part for part in zones if part.area > bruit_px]

    chevauchements = []
    identifiants = sorted(formes)
    for rang, gauche in enumerate(identifiants):
        for droite in identifiants[rang + 1 :]:
            commun = formes[gauche].intersection(formes[droite])
            if commun.area > bruit_px:
                chevauchements.append(
                    {"locaux": [gauche, droite], "surface_m2": round(commun.area / m2, 2)}
                )

    surface_emprise = emprise.area / m2 if not emprise.is_empty else 0.0
    non_affectee = sum(part.area for part in zones) / m2
    return {
        "surface_emprise_m2": round(surface_emprise, 2),
        "surface_affectee_m2": round(union.area / m2, 2),
        "surface_non_affectee_m2": round(non_affectee, 2),
        "surface_hors_emprise_m2": round(debord.area / m2, 2),
        "chevauchement_m2": round(sum(part["surface_m2"] for part in chevauchements), 2),
        "chevauchements": chevauchements,
        "taux_couverture_pct": round(100 * union.intersection(emprise).area / emprise.area, 1)
        if surface_emprise > 0
        else 0.0,
        "zones_non_affectees": [
            _en_normalise(part.exterior.coords, largeur, hauteur) for part in zones[:20]
        ],
    }


def part_chevauchement_pct(controle: dict[str, Any]) -> float:
    """Chevauchement rapporté à la surface affectée : c'est lui qui fausse les surfaces (Q2)."""
    affectee = float(controle.get("surface_affectee_m2") or 0.0)
    if affectee <= 0:
        return 0.0
    return 100 * float(controle.get("chevauchement_m2") or 0.0) / affectee


def pieces_du_plan(analyse: dict[str, Any], manifeste: dict[str, Any]) -> list[tuple[str, Polygon]]:
    """Raccourci vers la fonction historique, pour garder un seul repère dans tout le lot."""
    largeur, hauteur, _ = _echelle(manifeste)
    return pieces_env.pieces_du_plan(analyse, largeur, hauteur)
