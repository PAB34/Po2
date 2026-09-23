"""Calage des contours de locaux sur le nu intérieur relevé (lot F1, D66).

Le contour d'un local vient de ``thermicien-plan``, qui lit des pixels : il suit la façade à vue d'œil et
ignore les décrochements. Le nu intérieur, lui, a été **mesuré** bande par bande par ``thermicien-enveloppe``,
élément par élément : 45 cm au droit d'un trumeau, 26 cm au droit d'un mur-rideau.

Le calage consiste à retirer du contour la matière des murs : pour chaque élément d'enveloppe on reconstruit
le **corps de la paroi** — le quadrilatère entre son nu extérieur et son nu intérieur — et on le soustrait aux
locaux. Le contour s'arrête alors exactement au nu intérieur, décrochements compris, sans qu'aucune limite ne
soit inventée.

Le calage se fait sur le poste, à l'assemblage du fichier d'étude : le serveur ne retouche jamais une
géométrie en silence (D54).
"""
from __future__ import annotations

import copy
from typing import Any

from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.ops import unary_union

from app.services import thermique_enveloppe_pieces as pieces_env
from app.services import thermique_parcours_enveloppe as env

# Types d'éléments qui portent une face : eux seuls ont un corps de paroi.
FACES = ("paroi", "menuiserie", "poteau")
# Types d'éléments qui sont des liaisons : pas de corps, mais une position (D74).
LIAISONS = ("angle_sortant", "angle_rentrant", "about_refend")
# Le corps déborde vers l'extérieur, pour qu'aucun filet de local ne subsiste au-delà du nu extérieur.
DEBORD_EXTERIEUR_CM = 60.0
# En deçà, un déplacement n'est que du bruit de tracé et n'est pas signalé.
DEPLACEMENT_MIN_M = 0.02
# Une liaison est rattachée au local dont le contour passe à moins de cette distance.
RATTACHEMENT_LIAISON_M = 1.0


def _corps(element: dict[str, Any], troncon: dict[str, Any], px_par_m: float) -> Polygon | None:
    """Quadrilatère occupé par la paroi, du nu extérieur (débordé) au nu intérieur relevé."""
    exterieur, _interieur, exterieur_fin, _interieur_fin = env.nus(element)
    debut, fin = float(element["debut_m"]), float(element["fin_m"])
    if fin <= debut:
        return None
    interieure = pieces_env.face_interieure(element, troncon, px_par_m)
    if len(interieure) < 2:
        return None
    dehors = [
        env._point(troncon, debut, exterieur + DEBORD_EXTERIEUR_CM, px_par_m),
        env._point(troncon, fin, exterieur_fin + DEBORD_EXTERIEUR_CM, px_par_m),
    ]
    forme = Polygon([*dehors, *reversed(interieure)]).buffer(0)
    if isinstance(forme, MultiPolygon):
        forme = max(forme.geoms, key=lambda part: part.area)
    return forme if isinstance(forme, Polygon) and forme.area > 0 else None


def corps_des_parois(releve: dict[str, Any], manifeste: dict[str, Any]) -> list[Polygon]:
    """Corps de toutes les parois relevées, en pixels de la page."""
    px_par_m = float(manifeste["px_par_m"])
    par_id = {troncon["id"]: troncon for troncon in manifeste["troncons"]}
    formes = []
    for element in releve.get("elements", []):
        troncon = par_id.get(element.get("troncon"))
        if troncon is None or element.get("type") not in FACES:
            continue
        forme = _corps(element, troncon, px_par_m)
        if forme is not None:
            formes.append(forme)
    return formes


def _en_px(points: list[list[float]], largeur: float, hauteur: float) -> list[tuple[float, float]]:
    return [(x * largeur / 1000, y * hauteur / 1000) for x, y in points]


def _en_normalise(points: Any, largeur: float, hauteur: float) -> list[list[float]]:
    return [[round(x * 1000 / largeur, 3), round(y * 1000 / hauteur, 3)] for x, y in points]


def caler_locaux(
    analyse: dict[str, Any], manifeste: dict[str, Any], releve: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Retire la matière des murs aux contours des locaux ; renvoie l'analyse calée et le rapport.

    Le contour ne peut que **reculer** : on enlève ce qui mordait dans la paroi. Un local tracé trop petit
    n'est pas agrandi ici — c'est le travail de l'étape « Contours », que le thermicien mène à la main.
    """
    largeur, hauteur = (float(valeur) for valeur in manifeste["page_px"])
    px_par_m = float(manifeste["px_par_m"])
    m2 = px_par_m * px_par_m
    murs = corps_des_parois(releve, manifeste)
    resultat = copy.deepcopy(analyse)
    rapport: list[dict[str, Any]] = []
    if not murs:
        return resultat, rapport
    matiere = unary_union(murs)

    for objet in resultat.get("objects", []):
        if objet.get("category") != "piece" or len(objet.get("points", [])) < 3:
            continue
        avant = Polygon(_en_px(objet["points"], largeur, hauteur)).buffer(0)
        if isinstance(avant, MultiPolygon):
            avant = max(avant.geoms, key=lambda part: part.area)
        if not isinstance(avant, Polygon) or avant.area <= 0:
            continue
        apres = avant.difference(matiere)
        if isinstance(apres, MultiPolygon):
            apres = max(apres.geoms, key=lambda part: part.area)
        if not isinstance(apres, Polygon) or apres.area <= 0:
            continue
        # Un sommet de plus n'apporte rien sous le centimètre : on nettoie le feston du calcul booléen.
        simplifie = apres.simplify(0.01 * px_par_m, preserve_topology=True)
        if simplifie.area > 0:
            apres = simplifie
        deplacement = max(
            (apres.exterior.distance(avant.exterior.interpolate(rang / 200, normalized=True)) for rang in range(201)),
            default=0.0,
        ) / px_par_m
        retire = (avant.area - apres.area) / m2
        if retire <= 0.01 and deplacement < DEPLACEMENT_MIN_M:
            continue
        objet["points"] = _en_normalise(list(apres.exterior.coords)[:-1], largeur, hauteur)
        rapport.append(
            {
                "id": objet.get("id"),
                "nom": objet.get("subtype"),
                "surface_retiree_m2": round(retire, 2),
                "deplacement_max_m": round(deplacement, 3),
            }
        )
    return resultat, rapport


def liaisons_localisees(
    releve: dict[str, Any], manifeste: dict[str, Any], analyse: dict[str, Any]
) -> list[dict[str, Any]]:
    """Position de chaque liaison relevée et local auquel elle se rattache (D74).

    Sans cela, les ponts thermiques sont comptés mais introuvables sur le plan.
    """
    largeur, hauteur = (float(valeur) for valeur in manifeste["page_px"])
    px_par_m = float(manifeste["px_par_m"])
    par_id = {troncon["id"]: troncon for troncon in manifeste["troncons"]}
    locaux = pieces_env.pieces_du_plan(analyse, largeur, hauteur)
    resultat = []
    for element in releve.get("elements", []):
        troncon = par_id.get(element.get("troncon"))
        if troncon is None or element.get("type") not in LIAISONS:
            continue
        debut, fin = float(element["debut_m"]), float(element["fin_m"])
        _exterieur, interieur, _exterieur_fin, interieur_fin = env.nus(element)
        point = env._point(troncon, (debut + fin) / 2, (interieur + interieur_fin) / 2, px_par_m)
        repere = Point(point)
        proche, ecart = None, RATTACHEMENT_LIAISON_M * px_par_m
        for nom, forme in locaux:
            distance = forme.exterior.distance(repere)
            if distance <= ecart:
                proche, ecart = nom, distance
        resultat.append(
            {
                "type": element["type"],
                "troncon": element["troncon"],
                "abscisse_m": round((debut + fin) / 2, 3),
                "longueur_m": round(fin - debut, 3),
                "point": _en_normalise([point], largeur, hauteur)[0],
                "piece": proche,
                "composant": element.get("composant") or None,
            }
        )
    return resultat
