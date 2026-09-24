"""Édition pièce par pièce d'une étude importée (lot E3, D61 à D63).

Le thermicien déplace un contour, change une nature, coupe un plateau ouvert en deux ou fusionne deux
locaux. Après chaque geste, tout ce qui en découle est recalculé sans agent et sans image :
rattachement des éléments d'enveloppe aux pièces, raccords, synthèse, fiches et contrôle de couverture.

La source de vérité géométrique est ``analyse["objects"]`` : les opérations la modifient, puis
``reconstruire`` régénère la liste ``locaux`` et tout ce qui en dépend.
"""
from __future__ import annotations

import copy
import re
from typing import Any

from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import split, unary_union

from app.services import thermique_calage_contours as calage
from app.services import thermique_coherence as coherence
from app.services import thermique_elements as elements_releve
from app.services import thermique_enveloppe_pieces as pieces
from app.services import thermique_etude_geometrie as geo
from app.services import thermique_fiches_locaux as fiches_locaux
from app.services import thermique_parcours_enveloppe as enveloppe
from app.services.thermique import ThermiqueError
from app.services.thermique_etudes import LOCAL_NATURES, _noms_locaux

OPERATIONS = (
    "modifier",
    "couper",
    "fusionner",
    # Gestes sur les éléments d'enveloppe (F4). Ils passent par le même mécanisme que les contours :
    # aperçu, recalcul, enregistrement versionné — pas de second chemin d'édition.
    "element_confirmer",
    "element_corriger",
    "element_ecarter",
    "element_reactiver",
)
OPERATIONS_ELEMENT = tuple(nom for nom in OPERATIONS if nom.startswith("element_"))
# Un contour édité est simplifié sous cette tolérance, en unités du repère 0..1000 (~5 cm).
SIMPLIFICATION = 0.5
# Deux locaux à fusionner doivent se toucher ; ce jeu rattrape l'épaisseur d'un trait.
JEU_FUSION = 1.5


def _objets_pieces(analyse: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(objet.get("id") or ""): objet
        for objet in analyse.get("objects", [])
        if objet.get("category") == "piece" and str(objet.get("id") or "")
    }


def _identifiant_libre(analyse: dict[str, Any]) -> str:
    rangs = [
        int(trouve.group(1))
        for objet in analyse.get("objects", [])
        for trouve in [re.fullmatch(r"piece-(\d+)", str(objet.get("id") or ""))]
        if trouve
    ]
    return f"piece-{max(rangs, default=0) + 1:03d}"


def _polygone(points: list[list[float]]) -> Polygon:
    forme = Polygon([(float(x), float(y)) for x, y in points]).buffer(0)
    if isinstance(forme, MultiPolygon):
        forme = max(forme.geoms, key=lambda part: part.area)
    if not isinstance(forme, Polygon) or forme.area <= 0:
        raise ThermiqueError("Le contour proposé ne dessine pas une surface valide.")
    return forme


def _contour(forme: Polygon) -> list[list[float]]:
    simplifiee = forme.simplify(SIMPLIFICATION, preserve_topology=True)
    sommets = list((simplifiee if simplifiee.area > 0 else forme).exterior.coords)[:-1]
    if len(sommets) < 3:
        raise ThermiqueError("Le contour obtenu a moins de trois sommets.")
    return [[round(float(x), 3), round(float(y), 3)] for x, y in sommets]


def _controler_contour(points: Any, etiquette: str) -> list[list[float]]:
    if not isinstance(points, list) or len(points) < 3:
        raise ThermiqueError(f"Le contour de {etiquette} doit avoir au moins trois points.")
    resultat = []
    for point in points:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ThermiqueError(f"Un point de {etiquette} est invalide.")
        x, y = point
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise ThermiqueError(f"Un point de {etiquette} n'est pas numérique.")
        if not 0 <= float(x) <= 1000 or not 0 <= float(y) <= 1000:
            raise ThermiqueError(f"Le contour de {etiquette} sort de la feuille.")
        resultat.append([float(x), float(y)])
    return resultat


def _controler_segment(points: Any) -> list[list[float]]:
    resultat = []
    for point in points:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ThermiqueError("Un point de la coupe est invalide.")
        x, y = point
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise ThermiqueError("Un point de la coupe n'est pas numérique.")
        resultat.append([float(x), float(y)])
    return resultat


def _modifier(analyse: dict[str, Any], operation: dict[str, Any]) -> None:
    objets = _objets_pieces(analyse)
    objet = objets.get(str(operation.get("id") or ""))
    if objet is None:
        raise ThermiqueError("Le local à modifier est introuvable.")
    if "contour" in operation:
        points = _controler_contour(operation["contour"], f"« {objet.get('subtype')} »")
        objet["points"] = _contour(_polygone(points))
    if "nature" in operation:
        if operation["nature"] not in LOCAL_NATURES:
            raise ThermiqueError("La nature proposée est inconnue.")
        objet["local"] = operation["nature"]
    if "nom" in operation:
        nom = str(operation["nom"] or "").strip()
        if not nom:
            raise ThermiqueError("Le nom d'un local ne peut pas être vide.")
        objet["subtype"] = nom


def _couper(analyse: dict[str, Any], operation: dict[str, Any]) -> None:
    """Coupe un local en deux le long d'un segment tracé d'un bord à l'autre (D61)."""
    objets = _objets_pieces(analyse)
    objet = objets.get(str(operation.get("id") or ""))
    if objet is None:
        raise ThermiqueError("Le local à couper est introuvable.")
    segment = operation.get("segment")
    if not isinstance(segment, list) or len(segment) < 2:
        raise ThermiqueError("La coupe demande au moins deux points.")
    points = [(float(x), float(y)) for x, y in _controler_segment(segment)]
    forme = _polygone(objet["points"])
    # Le trait est prolongé à ses deux bouts pour traverser franchement le local.
    longueur = max(forme.bounds[2] - forme.bounds[0], forme.bounds[3] - forme.bounds[1]) or 1.0

    def prolonger(point: tuple[float, float], voisin: tuple[float, float]) -> tuple[float, float]:
        dx, dy = point[0] - voisin[0], point[1] - voisin[1]
        norme = (dx * dx + dy * dy) ** 0.5 or 1.0
        return (point[0] + dx / norme * longueur, point[1] + dy / norme * longueur)

    trace = LineString(
        [prolonger(points[0], points[1]), *points, prolonger(points[-1], points[-2])]
    )
    morceaux = [
        part
        for part in getattr(split(forme, trace), "geoms", [])
        if isinstance(part, Polygon) and part.area > 0
    ]
    if len(morceaux) < 2:
        raise ThermiqueError("La coupe ne traverse pas le local de part en part.")
    morceaux.sort(key=lambda part: part.area, reverse=True)
    garde, *restes = morceaux
    reste = unary_union(restes)
    if isinstance(reste, MultiPolygon):
        reste = max(reste.geoms, key=lambda part: part.area)

    noms = operation.get("noms") or []
    base = str(objet.get("subtype") or "local")
    objet["points"] = _contour(garde)
    objet["subtype"] = str(noms[0]).strip() if len(noms) > 0 and str(noms[0]).strip() else f"{base} (1)"
    nouveau = copy.deepcopy(objet)
    nouveau["id"] = _identifiant_libre(analyse)
    nouveau["points"] = _contour(reste)
    nouveau["subtype"] = str(noms[1]).strip() if len(noms) > 1 and str(noms[1]).strip() else f"{base} (2)"
    nouveau["review_required"] = True
    nouveau["evidence"] = "limite d'usage tracée par le thermicien"
    analyse["objects"].append(nouveau)


def _fusionner(analyse: dict[str, Any], operation: dict[str, Any]) -> None:
    identifiants = operation.get("ids")
    if not isinstance(identifiants, list) or len(identifiants) != 2 or identifiants[0] == identifiants[1]:
        raise ThermiqueError("La fusion demande deux locaux distincts.")
    objets = _objets_pieces(analyse)
    gauche, droite = (objets.get(str(identifiant)) for identifiant in identifiants)
    if gauche is None or droite is None:
        raise ThermiqueError("Un des locaux à fusionner est introuvable.")
    formes = [_polygone(gauche["points"]), _polygone(droite["points"])]
    if formes[0].distance(formes[1]) > JEU_FUSION:
        raise ThermiqueError("Ces deux locaux ne se touchent pas.")
    union = unary_union([forme.buffer(JEU_FUSION / 2) for forme in formes]).buffer(-JEU_FUSION / 2)
    if isinstance(union, MultiPolygon):
        union = max(union.geoms, key=lambda part: part.area)
    gauche["points"] = _contour(union)
    nom = str(operation.get("nom") or "").strip()
    if nom:
        gauche["subtype"] = nom
    analyse["objects"] = [objet for objet in analyse["objects"] if objet is not droite]


def appliquer(contenu: dict[str, Any], operations: list[dict[str, Any]]) -> dict[str, Any]:
    """Applique les gestes du thermicien à l'analyse, puis reconstruit tout ce qui en découle."""
    if not isinstance(operations, list) or not operations:
        raise ThermiqueError("Aucune modification n'a été transmise.")
    resultat = copy.deepcopy(contenu)
    for operation in operations:
        if not isinstance(operation, dict) or operation.get("type") not in OPERATIONS:
            raise ThermiqueError("Type de modification inconnu.")
        if operation["type"] in OPERATIONS_ELEMENT:
            _element(resultat, operation)
        elif operation["type"] == "modifier":
            _modifier(resultat["analyse"], operation)
        elif operation["type"] == "couper":
            _couper(resultat["analyse"], operation)
        else:
            _fusionner(resultat["analyse"], operation)
    return reconstruire(resultat)


def _element(contenu: dict[str, Any], operation: dict[str, Any]) -> None:
    """Un geste sur un élément relevé (F4). Il écrit dans le relevé brut, jamais dans le dessin (D99)."""
    ref = operation.get("element")
    if not isinstance(ref, dict):
        raise ThermiqueError("L'élément visé n'est pas désigné.")
    geste = operation["type"]
    if geste == "element_confirmer":
        elements_releve.confirmer(contenu, ref)
    elif geste == "element_corriger":
        elements_releve.corriger(
            contenu,
            ref,
            operation.get("changes") or {},
            operation.get("portee", elements_releve.PORTEE_CET_ELEMENT),
        )
    elif geste == "element_ecarter":
        elements_releve.ecarter(contenu, ref, operation.get("motif", ""))
    else:
        elements_releve.reactiver(contenu, ref)


def reconstruire(contenu: dict[str, Any]) -> dict[str, Any]:
    """Recalcule le rattachement, les raccords, la synthèse, les fiches et la couverture (D62).

    Aucun agent, aucune image : uniquement les fonctions de mesure classiques déjà en place.
    """
    resultat = copy.deepcopy(contenu)
    analyse = resultat["analyse"]
    manifeste = resultat["enveloppe"]["manifeste"]
    # Les éléments écartés par le thermicien restent dans l'étude, avec leur motif, mais sortent de tout
    # ce qui se mesure (D100). Une seule copie filtrée sert à toute la chaîne, pour que le dessin, les
    # fiches, les liaisons et la couverture racontent la même chose.
    brut = elements_releve.releve_actif(resultat["enveloppe"]["releve_brut"])

    coupe = pieces.decouper_par_piece(brut, manifeste, analyse)
    releve = enveloppe.reprojeter(coupe, manifeste, analyse)
    bibliotheque = releve.get("bibliotheque", {})
    natures = pieces.natures_du_plan(analyse)
    syntheses = [
        {**fiche, "local": natures.get(fiche["piece"], "chauffe")}
        for fiche in pieces.synthese_pieces(coupe, manifeste)
    ]
    # Le nord vient de la planche, posé par le thermicien (D85). Absent, les orientations restent « à caler ».
    fiches = fiches_locaux.fiches(analyse, manifeste, coupe, syntheses, resultat.get("nord_deg"))
    demandes = pieces.demandes_etude(syntheses)
    limites = geo.limites_des_locaux(analyse, manifeste)

    par_nom_fiche = {fiche.get("piece"): fiche for fiche in fiches}
    par_nom_synthese = {fiche.get("piece"): fiche for fiche in syntheses}
    locaux = []
    for objet, nom in _noms_locaux(analyse):
        identifiant = str(objet.get("id") or "").strip()
        fiche = par_nom_fiche.get(nom, {"piece": nom, "cotes": [], "alertes": []})
        locaux.append(
            {
                "id": identifiant,
                "nom": nom,
                "nature": objet.get("local") or "chauffe",
                "contour": copy.deepcopy(objet["points"]),
                "limites": limites.get(identifiant, []),
                "surface_m2": fiche.get("surface_m2"),
                "fiche": copy.deepcopy(fiche),
                "synthese": copy.deepcopy(par_nom_synthese.get(nom, {})),
                "demandes": [demande for demande in demandes if demande.get("piece") == nom],
            }
        )

    resultat["locaux"] = locaux
    resultat["enveloppe"]["catalogue"] = copy.deepcopy(bibliotheque.get("composants", []))
    resultat["enveloppe"]["synthese_pieces"] = syntheses
    resultat["enveloppe"]["fiches_locaux"] = fiches
    resultat["enveloppe"]["raccords"] = copy.deepcopy(coupe.get("raccords", []))
    resultat["enveloppe"]["demandes"] = demandes
    # Le tracé des éléments revient dans le fichier (D75) : sans lui, rien n'est dessinable sur le plan.
    resultat["enveloppe"]["objets"] = copy.deepcopy(releve.get("objets", []))
    # Les ponts thermiques portent leur position, pour être montrés là où ils sont (D74).
    resultat["enveloppe"]["liaisons"] = calage.liaisons_localisees(brut, manifeste, analyse)
    resultat["couverture"] = geo.controler_couverture(
        {local["id"]: local["contour"] for local in locaux}, manifeste, brut
    )
    # La chaîne se relit elle-même : le rapport voyage avec l'étude et s'affiche à l'import (D77).
    resultat["coherence"] = coherence.controler_niveau(resultat)
    return resultat


# Q2 : un trou de couverture n'est qu'un avertissement, un recouvrement fausse les surfaces.
SEUIL_CHEVAUCHEMENT_PCT = 2.0


def _vers_feuille(transform: list[Any], largeur: float, hauteur: float, point: Any) -> list[float]:
    """Point PDF -> repère normalisé 0..1000 de la feuille, par la matrice du rendu pdfium."""
    if not isinstance(point, (list, tuple)) or len(point) != 2:
        raise ThermiqueError("Un point PDF est invalide.")
    a, b, c, d, e, f = (float(valeur) for valeur in transform)
    x, y = float(point[0]), float(point[1])
    px, py = a * x + c * y + e, b * x + d * y + f
    return [round(px * 1000 / largeur, 3), round(py * 1000 / hauteur, 3)]


def _operations_en_feuille(
    operations: list[dict[str, Any]], transform: list[Any], largeur: float, hauteur: float
) -> list[dict[str, Any]]:
    """L'interface ne manipule que des points PDF : la conversion se fait ici, une seule fois."""
    resultat = []
    for operation in operations:
        converti = dict(operation)
        if isinstance(converti.get("contour_pdf"), list):
            converti["contour"] = [
                _vers_feuille(transform, largeur, hauteur, point) for point in converti.pop("contour_pdf")
            ]
        if isinstance(converti.get("segment_pdf"), list):
            converti["segment"] = [
                _vers_feuille(transform, largeur, hauteur, point) for point in converti.pop("segment_pdf")
            ]
        resultat.append(converti)
    return resultat


def remodeler(
    contenu: dict[str, Any],
    operations: list[dict[str, Any]],
    transform: list[Any],
    largeur: float,
    hauteur: float,
    local_id: str | None = None,
) -> dict[str, Any]:
    """Calcule sans rien écrire : contenu recalculé, couverture, voisins touchés, motif de blocage."""
    from app.services import thermique_etudes as etudes  # import tardif : évite une boucle d'imports

    gestes = _operations_en_feuille(operations, transform, largeur, hauteur)
    apres = appliquer(contenu, gestes) if gestes else reconstruire(contenu)
    etudes.convertir_contours(apres, transform, largeur, hauteur)
    couverture = apres["couverture"]
    bloquant = None
    if geo.part_chevauchement_pct(couverture) > SEUIL_CHEVAUCHEMENT_PCT:
        bloquant = (
            f"Les locaux se recouvrent sur {couverture['chevauchement_m2']} m² : "
            "les surfaces seraient comptées deux fois. Corrigez les contours avant d'enregistrer."
        )
    return {
        "content": apres,
        "couverture": couverture,
        "voisins_modifies": voisins_modifies(contenu, apres, local_id),
        "bloquant": bloquant,
    }


def etats_apres_enregistrement(
    etats: dict[str, Any],
    apres: dict[str, Any],
    local_id: str | None,
    voisins: list[str],
    valider: bool,
) -> dict[str, Any]:
    """État de chaque local après un « Enregistrer et suivant » (D63)."""
    presents = {local["id"]: local["nom"] for local in apres.get("locaux", [])}
    resultat = {identifiant: dict(etat) for identifiant, etat in etats.items() if identifiant in presents}
    for identifiant in presents:
        resultat.setdefault(identifiant, {"status": "a_verifier", "motif": None})
    if local_id and valider and local_id in resultat:
        resultat[local_id] = {"status": "valide", "motif": None}
    nom = presents.get(local_id or "", "voisin")
    for voisin in voisins:
        if voisin in resultat and resultat[voisin].get("status") == "valide":
            resultat[voisin] = {"status": "a_revoir", "motif": f"le local « {nom} » a changé à côté"}
    return resultat


def voisins_modifies(avant: dict[str, Any], apres: dict[str, Any], sauf: str | None = None) -> list[str]:
    """Locaux dont la fiche a changé, hors celui que le thermicien vient de travailler (D63)."""
    anciennes = {local["id"]: local.get("fiche") for local in avant.get("locaux", [])}
    changes = []
    for local in apres.get("locaux", []):
        if local["id"] == sauf:
            continue
        if local["id"] not in anciennes or anciennes[local["id"]] != local.get("fiche"):
            changes.append(local["id"])
    return changes
