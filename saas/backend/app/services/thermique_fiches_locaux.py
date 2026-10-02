"""Fiche par local : tour de chaque pièce, adjacence et épaisseur de chaque côté, parois déperditives (D29 à D33).

Pixels et géométrie seuls. Chaque côté du contour recalé est sondé perpendiculairement : le premier élément
rencontré de l'autre côté du mur (autre local, extérieur, terrasse, vide) donne l'adjacence, la distance donne
l'épaisseur du mur. Les éléments de l'enveloppe relevés pour ce local sont rattachés à ses côtés extérieurs.
"""
from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw
from shapely import STRtree
from shapely.geometry import LineString, Point, Polygon
from shapely.prepared import prep

from app.services import thermique_enveloppe_pieces as pieces_env
from app.services import thermique_parcours_enveloppe as env

PAS_COTE_M = 0.10
SONDE_DEBUT_CM, SONDE_PAS_CM, SONDE_MAX_CM = 5, 3, 120
COTE_MIN_M = 0.15
RATTACHEMENT_M = 0.90
LOCAUX_NON_CHAUFFES = {"non_chauffe", "gaine_technique"}
# Un local extérieur (terrasse, balcon, loggia… — D161) n'est pas chauffé : il ne déperd pas lui-même. Pour
# ses voisins, la sonde reprend sa nature comme adjacence : « exterieur », déjà déperditif.
LOCAUX_HORS_VOLUME = LOCAUX_NON_CHAUFFES | {"exterieur"}
DEPERDITIFS = {"exterieur", "vide"} | LOCAUX_NON_CHAUFFES
# Voisin d'un côté qui donne sur l'air libre, par opposition à un espace extérieur à plancher.
AIR_LIBRE = "extérieur"
TERRASSE_OBJET = "terrasse ou balcon"
ORIENTATIONS = ("N", "NE", "E", "SE", "S", "SO", "O", "NO")
# Le tracé d'un côté est réduit sous cette flèche : un côté droit de 14 m tient alors en deux points,
# au lieu des 140 sondages qui l'ont mesuré (D80).
SIMPLIFICATION_TRACE_M = 0.02


def _trace_du_cote(ligne: Any, largeur: float, hauteur: float, px_par_m: float) -> list[list[float]]:
    """Polyligne du côté dans le repère de la feuille (0 à 1000), pour dessiner sa cote sur le plan (D80).

    Un côté n'est pas une arête du contour mais un regroupement de sondages : sa position ne peut pas être
    recalculée depuis le contour, elle doit voyager avec la fiche.
    """
    if isinstance(ligne, Point):
        points = [(ligne.x, ligne.y)]
    else:
        reduite = ligne.simplify(SIMPLIFICATION_TRACE_M * px_par_m, preserve_topology=False)
        points = list(reduite.coords) or list(ligne.coords)
    return [[round(x * 1000 / largeur, 3), round(y * 1000 / hauteur, 3)] for x, y in points]


def batiment_du_manifeste(manifeste: dict[str, Any]) -> Polygon:
    """Face extérieure du bâtiment (guide de l'enveloppe), en pixels de la page."""
    if manifeste.get("batiment_px"):  # lecture par local (D44) : face extérieure trouvée par remplissage
        return Polygon(manifeste["batiment_px"]).buffer(0)
    anneau = [env._point(t, t["debut_m"], 0, manifeste["px_par_m"]) for t in manifeste["troncons"]]
    return Polygon(anneau).buffer(0)


def _formes(analyse: dict[str, Any], categories: set[str], largeur: int, hauteur: int) -> list[Polygon]:
    resultat = []
    for objet in analyse["objects"]:
        if objet["category"] in categories and len(objet["points"]) >= 3:
            forme = Polygon([(x * largeur / 1000, y * hauteur / 1000) for x, y in objet["points"]]).buffer(0)
            if forme.area > 0:
                resultat.append(forme)
    return resultat


def orientation(normale: tuple[float, float], nord_deg: float | None) -> str:
    """Orientation d'une normale sortante (repère image : x à droite, y vers le bas).

    `nord_deg` : angle du nord mesuré depuis le haut de la feuille, dans le sens horaire ; None = non calé.
    """
    azimut_feuille = math.degrees(math.atan2(normale[0], -normale[1])) % 360  # 0 = haut de la feuille
    if nord_deg is None:
        return "nord à caler"
    azimut = (azimut_feuille - nord_deg) % 360
    return ORIENTATIONS[round(azimut / 45) % 8]


class Voisinage:
    """Les locaux du plan, avec un index spatial, pour répondre vite à « qu'y a-t-il en ce point ? ».

    Un sondage teste un point tous les 3 cm jusqu'à 1,20 m, et il y a un sondage tous les 10 cm sur
    chaque côté de chaque local : sans index, chacun d'eux interrogeait **les 24 locaux du niveau**, ce
    qui faisait des millions de tests et 4,8 s de recalcul sur le R+1.

    L'ordre d'origine est scrupuleusement conservé : deux locaux peuvent se recouvrir — 10,85 m² sur ce
    même R+1 — et c'est le premier de la liste qui l'emportait. Changer cet ordre changerait les fiches.
    """

    def __init__(self, formes: list[tuple[str, Any, str]]) -> None:
        self.noms = [nom for nom, _forme, _nature in formes]
        self.natures = [nature for _nom, _forme, nature in formes]
        self.prepares = [prep(forme) for _nom, forme, _nature in formes]
        self.arbre = STRtree([forme for _nom, forme, _nature in formes])

    def contenant(self, point: Any, sauf: str) -> tuple[str, str] | None:
        for rang in sorted(int(r) for r in self.arbre.query(point)):
            if self.noms[rang] != sauf and self.prepares[rang].contains(point):
                return self.natures[rang], self.noms[rang]
        return None


def _sonder(point: tuple[float, float], normale: tuple[float, float], px_par_m: float, soi: str,
            locaux: Voisinage, batiment: Any, exterieurs: list[Any], vides: list[Any]) -> tuple[str, str, float]:
    """(adjacence, voisin, épaisseur en cm) au droit d'un point du contour."""
    for cm in range(SONDE_DEBUT_CM, SONDE_MAX_CM + 1, SONDE_PAS_CM):
        q = Point(point[0] + normale[0] * cm / 100 * px_par_m, point[1] + normale[1] * cm / 100 * px_par_m)
        trouve = locaux.contenant(q, soi)
        if trouve is not None:
            return trouve[0], trouve[1], cm
        # Une terrasse ou un balcon relevé par l'agent est dehors, mais sa dalle touche le mur : on le dit, pour
        # que la liaison linéique se voie (D161). L'air libre reste « extérieur ».
        if any(forme.contains(q) for forme in exterieurs):
            return "exterieur", TERRASSE_OBJET, cm
        if not batiment.contains(q):
            return "exterieur", AIR_LIBRE, cm
        if any(forme.contains(q) for forme in vides):
            return "vide", "vide", cm
    return "inconnu", "", float(SONDE_MAX_CM)


def fiches(analyse: dict[str, Any], manifeste: dict[str, Any], brut: dict[str, Any] | None = None,
           synthese: list[dict[str, Any]] | None = None, nord_deg: float | None = None,
           coupures: dict[str, list[list[float]]] | None = None) -> list[dict[str, Any]]:
    """Une fiche par local : côtés (adjacence, épaisseur, orientation, déperditif), enveloppe rattachée."""
    largeur, hauteur = manifeste["page_px"]
    px_par_m = manifeste["px_par_m"]
    batiment = prep(batiment_du_manifeste(manifeste))
    natures = pieces_env.natures_du_plan(analyse)
    locaux_formes = [(nom, forme, natures.get(nom, "chauffe")) for nom, forme in pieces_env.pieces_du_plan(analyse, largeur, hauteur)]
    locaux = Voisinage(locaux_formes)
    exterieurs = [prep(f) for f in _formes(analyse, {"terrasse", "balcon"}, largeur, hauteur)]
    vides = [prep(Polygon([(x * largeur / 1000, y * hauteur / 1000) for x, y in e["points"]]).buffer(0))
             for e in analyse.get("locaux_ecartes", []) if e.get("decision") == "vide" and e.get("points")]
    par_troncon = {t["id"]: t for t in manifeste["troncons"]}
    enveloppe_par_local: dict[str, list[dict[str, Any]]] = defaultdict(list)
    decisions = {f["id"]: f.get("decision") for f in (brut or {}).get("catalogue", [])}
    for element in (brut or {}).get("elements", []):
        if element.get("piece") and element["type"] in ("paroi", "menuiserie", "poteau") and element["troncon"] in par_troncon \
                and decisions.get(element.get("composant") or "") != "exclu":
            face = pieces_env.face_interieure(element, par_troncon[element["troncon"]], px_par_m)
            enveloppe_par_local[element["piece"]].append({**element, "_face": LineString(face)})
    synthese_par_local = {s["piece"]: s for s in (synthese or [])}
    resultat = []
    for nom, forme, nature in locaux_formes:
        anneau = forme.exterior
        sondages = []
        coords = list(anneau.coords)
        for arete, (a, b) in enumerate(zip(coords, coords[1:])):
            longueur = math.dist(a, b)
            if longueur < 1:
                continue
            ux, uy = (b[0] - a[0]) / longueur, (b[1] - a[1]) / longueur
            normale = (uy, -ux) if anneau.is_ccw else (-uy, ux)
            test = Point(a[0] + ux * longueur / 2 + normale[0] * 3, a[1] + uy * longueur / 2 + normale[1] * 3)
            if forme.contains(test):
                normale = (-normale[0], -normale[1])
            nombre = max(1, round(longueur / (PAS_COTE_M * px_par_m)))
            for k in range(nombre):
                t = (k + 0.5) / nombre
                p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                adjacence, voisin, epaisseur = _sonder(p, normale, px_par_m, nom, locaux, batiment, exterieurs, vides)
                sondages.append({"p": p, "longueur": longueur / nombre / px_par_m, "adjacence": adjacence, "voisin": voisin,
                                 "epaisseur": epaisseur, "normale": normale,
                                 # D260 : l'arête du contour et la part qu'en couvre ce sondage, pour les parois.
                                 "arete": arete, "a": a, "b": b, "t0": k / nombre, "t1": (k + 1) / nombre})
        cotes = _regrouper(sondages)
        lignes_cotes = [LineString([s["p"] for s in c["sondages"]]) if len(c["sondages"]) > 1 else Point(c["sondages"][0]["p"])
                        for c in cotes]
        # chaque élément d'enveloppe va au seul côté déperditif le plus proche (à moins de RATTACHEMENT_M) : extérieur
        # pour la façade, local non chauffé ou vide pour les côtés lus depuis la face intérieure (D46)
        affectation: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for element in enveloppe_par_local.get(nom, []):
            milieu = element["_face"].interpolate(0.5, normalized=True)
            vises = LOCAUX_NON_CHAUFFES | {"vide"} if par_troncon[element["troncon"]].get("ligne") == "face_interieure" else {"exterieur"}
            candidats = [(lignes_cotes[r].distance(milieu), r) for r, c in enumerate(cotes) if c["adjacence"] in vises]
            if candidats:
                distance, rang_cote = min(candidats)
                if distance <= RATTACHEMENT_M * px_par_m:
                    affectation[rang_cote].append(element)
                    element["_rattache"] = True
        details = []
        for rang_cote, cote in enumerate(cotes):
            fiche_cote = {
                "adjacence": cote["adjacence"], "voisin": cote["voisin"],
                "longueur_m": round(cote["longueur"], 2),
                "epaisseur_cm": round(sorted(s["epaisseur"] for s in cote["sondages"])[len(cote["sondages"]) // 2]),
                "orientation": orientation(cote["sondages"][len(cote["sondages"]) // 2]["normale"], nord_deg),
                "deperditif": cote["adjacence"] in DEPERDITIFS and nature not in LOCAUX_HORS_VOLUME,
                # Remarque F (D161) : un local chauffé contre un espace extérieur à plancher (terrasse, balcon,
                # loggia…) porte une liaison linéique le long de ce côté, créée d'office.
                "liaison_exterieur": cote["adjacence"] == "exterieur" and cote["voisin"] != AIR_LIBRE
                and nature not in LOCAUX_HORS_VOLUME,
                "trace": _trace_du_cote(lignes_cotes[rang_cote], largeur, hauteur, px_par_m),
                "enveloppe": [],
            }
            if cote["adjacence"] in DEPERDITIFS:
                composants: dict[str, float] = defaultdict(float)
                for element in affectation.get(rang_cote, []):
                    composants[element.get("composant") or element["type"]] += element["_face"].length / px_par_m
                fiche_cote["enveloppe"] = [{"composant": k, "lineaire_m": round(v, 2)} for k, v in composants.items()]
            details.append(fiche_cote)
        alertes = []
        for cote in details:
            if cote["adjacence"] == "exterieur" and not cote["enveloppe"] and cote["longueur_m"] >= 0.5:
                alertes.append(f"côté extérieur de {cote['longueur_m']:.2f} m sans élément d'enveloppe relevé")
            if cote["adjacence"] == "inconnu" and cote["longueur_m"] >= 0.5:
                alertes.append(f"côté de {cote['longueur_m']:.2f} m : rien trouvé derrière le mur à moins de 1,2 m")
        orphelins = [e for e in enveloppe_par_local.get(nom, []) if not e.get("_rattache")]
        if orphelins:
            alertes.append(f"{len(orphelins)} élément(s) d'enveloppe relevé(s) sans côté déperditif correspondant "
                           f"({sum(e['_face'].length for e in orphelins) / px_par_m:.2f} m)")
        synthese_local = synthese_par_local.get(nom, {})
        # contrôle croisé : longueur des côtés extérieurs (tour du local) contre façade relevée sur l'enveloppe
        exterieur_m = sum(c["longueur_m"] for c in details if c["adjacence"] == "exterieur")
        facade_m = synthese_local.get("facade_m", 0.0)
        if facade_m and abs(exterieur_m - facade_m) > max(0.15 * facade_m, 0.3):
            alertes.append(f"côtés extérieurs {exterieur_m:.2f} m contre {facade_m:.2f} m de façade relevée sur l'enveloppe")
        resultat.append({
            "piece": nom, "local": nature,
            "surface_m2": round(forme.area / px_par_m ** 2, 2),
            "perimetre_m": round(anneau.length / px_par_m, 2),
            "cotes": details,
            "deperditif_m": round(sum(c["longueur_m"] for c in details if c["deperditif"]), 2),
            "liaison_exterieur_m": round(sum(c["longueur_m"] for c in details if c["liaison_exterieur"]), 2),
            "par_adjacence": {a: round(sum(c["longueur_m"] for c in details if c["adjacence"] == a), 2)
                              for a in sorted({c["adjacence"] for c in details})},
            "baies": synthese_local.get("menuiseries", []),
            "ponts": synthese_local.get("ponts", {}),
            "liaison_plancher_m": synthese_local.get("liaison_plancher_m", 0.0),
            "a_completer": ["plancher bas", "plancher haut", "hauteur sous plafond (coupes)"],
            "alertes": alertes,
            "parois": _parois(sondages, enveloppe_par_local.get(nom, []), nature, largeur, hauteur, px_par_m, nord_deg,
                              (coupures or {}).get(nom)),
        })
    return resultat


COUPURE_M = 0.30


def _decouper(p0: tuple[float, float], p1: tuple[float, float], coupures: list[tuple[float, float]],
              px_par_m: float) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """D264 : la portion p0-p1 coupée aux points posés par le thermicien (à moins de 30 cm de la portion)."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    longueur2 = dx * dx + dy * dy
    if longueur2 == 0:
        return [(p0, p1)]
    pas_min = COTE_MIN_M * px_par_m / math.sqrt(longueur2)
    parts = []
    for cx, cy in coupures:
        t = ((cx - p0[0]) * dx + (cy - p0[1]) * dy) / longueur2
        pied = (p0[0] + t * dx, p0[1] + t * dy)
        if pas_min <= t <= 1 - pas_min and math.dist(pied, (cx, cy)) <= COUPURE_M * px_par_m:
            parts.append(t)
    bornes = [0.0] + sorted(set(round(t, 6) for t in parts)) + [1.0]
    morceaux = []
    for t0, t1 in zip(bornes, bornes[1:]):
        if t1 - t0 >= pas_min / 2:
            morceaux.append(((p0[0] + t0 * dx, p0[1] + t0 * dy), (p0[0] + t1 * dx, p0[1] + t1 * dy)))
    return morceaux or [(p0, p1)]


def _parois(sondages: list[dict[str, Any]], releve: list[dict[str, Any]], nature: str, largeur: float, hauteur: float,
            px_par_m: float, nord_deg: float | None, coupures: list[list[float]] | None = None) -> list[dict[str, Any]]:
    """Les parois d'un local (D260) : une par arête du contour et par nature de ce qu'il y a derrière, coupées aux
    points posés par le thermicien (D264).

    Le tracé est la portion droite de l'arête (face intérieure, dimensions intérieures). La proposition vient du
    mur relevé par l'IA le plus proche (moins de 90 cm) : sa composition, à valider par le thermicien.
    """
    points_coupure = [(x * largeur / 1000, y * hauteur / 1000) for x, y in (coupures or [])]
    groupes: list[list[dict[str, Any]]] = []
    for s in sondages:
        dernier = groupes[-1][-1] if groupes else None
        if dernier and dernier["arete"] == s["arete"] and dernier["adjacence"] == s["adjacence"] and dernier["voisin"] == s["voisin"]:
            groupes[-1].append(s)
        else:
            groupes.append([s])
    murs = [e for e in releve if e.get("type") == "paroi"]
    parois = []
    for groupe in groupes:
        premier, dernier = groupe[0], groupe[-1]
        a, b = premier["a"], premier["b"]
        debut = (a[0] + (b[0] - a[0]) * premier["t0"], a[1] + (b[1] - a[1]) * premier["t0"])
        fin = (a[0] + (b[0] - a[0]) * dernier["t1"], a[1] + (b[1] - a[1]) * dernier["t1"])
        for p0, p1 in _decouper(debut, fin, points_coupure, px_par_m):
            paroi = _paroi(p0, p1, groupe, murs, releve, nature, largeur, hauteur, px_par_m, nord_deg)
            if paroi:
                parois.append({**paroi, "rang": len(parois)})
    return parois


def _paroi(p0: tuple[float, float], p1: tuple[float, float], groupe: list[dict[str, Any]], murs: list[dict[str, Any]],
           releve: list[dict[str, Any]], nature: str, largeur: float, hauteur: float, px_par_m: float,
           nord_deg: float | None) -> dict[str, Any] | None:
    """Une paroi : son tracé, ce qu'il y a derrière, et la proposition du relevé le plus proche de son milieu."""
    premier = groupe[0]
    longueur = math.dist(p0, p1) / px_par_m
    if longueur < COTE_MIN_M:
        return None
    milieu = Point((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
    proches = sorted((m["_face"].distance(milieu), rang) for rang, m in enumerate(murs))
    proposition = None
    # Sans mur relevé à moins de 90 cm mais devant une menuiserie : la paroi est vitrée, elle se traite à
    # l'étape Menuiseries (R+1 : 33 parois, 75 m de murs-rideaux et baies).
    vitres = sorted(e["_face"].distance(milieu) for e in releve if e.get("type") == "menuiserie")
    vitree = (not proches or proches[0][0] > RATTACHEMENT_M * px_par_m) and bool(vitres) and vitres[0] <= RATTACHEMENT_M * px_par_m
    if proches and proches[0][0] <= RATTACHEMENT_M * px_par_m:
        mur = murs[proches[0][1]]
        proposition = {
            "composant": mur.get("composant") or None,
            "couches": [{"nature": c.get("nature"), "epaisseur_cm": c.get("epaisseur_cm")} for c in (mur.get("couches") or [])
                        if c.get("nature") and c.get("epaisseur_cm")],
            "epaisseur_cm": round(float(mur["nu_exterieur_cm"]) - float(mur["nu_interieur_cm"]), 1),
        }
    epaisseurs = sorted(s["epaisseur"] for s in groupe)
    # D267, D268 : les menuiseries qui longent la paroi ; couverte à 90 % ou plus, la paroi est vitrée.
    menuiseries = _menuiseries_sur(p0, p1, releve, largeur, hauteur, px_par_m)
    if longueur > 0 and sum(m["largeur_m"] for m in menuiseries) >= COUVERTURE_VITREE * longueur:
        vitree = True
    return {
        "adjacence": premier["adjacence"],
        "voisin": premier["voisin"],
        "deperditif": premier["adjacence"] in DEPERDITIFS and nature not in LOCAUX_HORS_VOLUME,
        "longueur_m": round(longueur, 2),
        "epaisseur_cm": round(epaisseurs[len(epaisseurs) // 2]),
        "orientation": orientation(groupe[len(groupe) // 2]["normale"], nord_deg),
        "trace": [[round(x * 1000 / largeur, 3), round(y * 1000 / hauteur, 3)] for x, y in (p0, p1)],
        "proposition": proposition,
        "vitree": vitree,
        "menuiseries": menuiseries,
    }


COUVERTURE_VITREE = 0.90
MENUISERIE_MIN_M = 0.05
PARALLELE_COS = 0.95


def _menuiseries_sur(p0: tuple[float, float], p1: tuple[float, float], releve: list[dict[str, Any]], largeur: float,
                     hauteur: float, px_par_m: float) -> list[dict[str, Any]]:
    """D267 : les menuiseries du relevé posées sur cette paroi (face intérieure parallèle, à moins de 90 cm), avec la
    portion qui la recouvre. Une baie à cheval sur deux parois se partage entre elles."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    longueur = math.hypot(dx, dy)
    if longueur == 0:
        return []
    ux, uy = dx / longueur, dy / longueur
    poses = []
    for element in releve:
        if element.get("type") != "menuiserie":
            continue
        (ax, ay), (bx, by) = element["_face"].coords[0], element["_face"].coords[-1]
        fx, fy = bx - ax, by - ay
        lf = math.hypot(fx, fy)
        if lf == 0 or abs(fx * ux + fy * uy) / lf < PARALLELE_COS:
            continue
        # position le long de la paroi (0 à longueur) et écart perpendiculaire du milieu de la face
        t0 = (ax - p0[0]) * ux + (ay - p0[1]) * uy
        t1 = (bx - p0[0]) * ux + (by - p0[1]) * uy
        mx, my = (ax + bx) / 2 - p0[0], (ay + by) / 2 - p0[1]
        if abs(mx * -uy + my * ux) > RATTACHEMENT_M * px_par_m:
            continue
        debut, fin = max(0.0, min(t0, t1)), min(longueur, max(t0, t1))
        if (fin - debut) / px_par_m < MENUISERIE_MIN_M:
            continue
        q0 = (p0[0] + ux * debut, p0[1] + uy * debut)
        q1 = (p0[0] + ux * fin, p0[1] + uy * fin)
        poses.append({
            "ref": {"troncon": element["troncon"], "debut_m": element["debut_m"], "fin_m": element["fin_m"]},
            "composant": element.get("composant") or None,
            "modele": element.get("modele") or None,
            "menuiserie_type": element.get("menuiserie_type") or None,
            "largeur_m": round((fin - debut) / px_par_m, 2),
            "debut_m": round(debut / px_par_m, 2),
            "fin_m": round(fin / px_par_m, 2),
            "trace": [[round(x * 1000 / largeur, 3), round(y * 1000 / hauteur, 3)] for x, y in (q0, q1)],
        })
    return sorted(poses, key=lambda pose: pose["debut_m"])


def _regrouper(sondages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sondages contigus de même adjacence et même voisin -> côtés ; les côtés trop courts rejoignent un voisin."""
    cotes: list[dict[str, Any]] = []
    for s in sondages:
        if cotes and cotes[-1]["adjacence"] == s["adjacence"] and cotes[-1]["voisin"] == s["voisin"]:
            cotes[-1]["sondages"].append(s)
            cotes[-1]["longueur"] += s["longueur"]
        else:
            cotes.append({"adjacence": s["adjacence"], "voisin": s["voisin"], "sondages": [s], "longueur": s["longueur"]})
    # le contour est fermé : le dernier côté rejoint le premier s'ils sont de même nature
    if len(cotes) > 1 and cotes[0]["adjacence"] == cotes[-1]["adjacence"] and cotes[0]["voisin"] == cotes[-1]["voisin"]:
        dernier = cotes.pop()
        cotes[0]["sondages"] = dernier["sondages"] + cotes[0]["sondages"]
        cotes[0]["longueur"] += dernier["longueur"]
    change = True
    while change and len(cotes) > 1:
        change = False
        for rang, cote in enumerate(cotes):
            if cote["longueur"] >= COTE_MIN_M:
                continue
            voisin = cotes[rang - 1] if rang > 0 else cotes[rang + 1]
            voisin["sondages"] += cote["sondages"]
            voisin["longueur"] += cote["longueur"]
            del cotes[rang]
            change = True
            break
    # deux côtés devenus voisins sur le même local fusionnent
    fusion: list[dict[str, Any]] = []
    for cote in cotes:
        if fusion and fusion[-1]["adjacence"] == cote["adjacence"] and fusion[-1]["voisin"] == cote["voisin"]:
            fusion[-1]["sondages"] += cote["sondages"]
            fusion[-1]["longueur"] += cote["longueur"]
        else:
            fusion.append(cote)
    return fusion


COULEURS = {"exterieur": (214, 40, 40), "non_chauffe": (240, 140, 0),
            "gaine_technique": (124, 58, 237), "vide": (156, 54, 181),
            "circulation": (25, 113, 194), "chauffe": (120, 130, 140), "inconnu": (0, 0, 0)}
LIBELLES = {"exterieur": "extérieur", "non_chauffe": "local non chauffé",
            "gaine_technique": "gaine technique", "vide": "vide / patio",
            "circulation": "circulation", "chauffe": "local chauffé", "inconnu": "rien trouvé"}


def planche_adjacences(page: Image.Image, analyse: dict[str, Any], manifeste: dict[str, Any],
                       fiches_locaux: list[dict[str, Any]], chemin: Path, nord_deg: float | None = None) -> Path:
    """Plan des locaux : chaque côté coloré selon ce qu'il y a derrière ; déperditif en trait épais."""
    largeur, hauteur = manifeste["page_px"]
    px_par_m = manifeste["px_par_m"]
    image = page.convert("RGB")
    dessin = ImageDraw.Draw(image, "RGBA")
    batiment = prep(batiment_du_manifeste(manifeste))
    natures = pieces_env.natures_du_plan(analyse)
    formes = pieces_env.pieces_du_plan(analyse, largeur, hauteur)
    locaux = Voisinage([(nom, forme, natures.get(nom, "chauffe")) for nom, forme in formes])
    exterieurs = [prep(f) for f in _formes(analyse, {"terrasse", "balcon"}, largeur, hauteur)]
    vides = [prep(Polygon([(x * largeur / 1000, y * hauteur / 1000) for x, y in e["points"]]).buffer(0))
             for e in analyse.get("locaux_ecartes", []) if e.get("decision") == "vide" and e.get("points")]
    for nom, forme in formes:
        coords = list(forme.exterior.coords)
        for a, b in zip(coords, coords[1:]):
            longueur = math.dist(a, b)
            if longueur < 1:
                continue
            ux, uy = (b[0] - a[0]) / longueur, (b[1] - a[1]) / longueur
            normale = (uy, -ux)
            if forme.contains(Point(a[0] + ux * longueur / 2 + normale[0] * 3, a[1] + uy * longueur / 2 + normale[1] * 3)):
                normale = (-normale[0], -normale[1])
            nombre = max(1, round(longueur / (PAS_COTE_M * px_par_m)))
            for k in range(nombre):
                t0, t1 = k / nombre, (k + 1) / nombre
                p = (a[0] + (b[0] - a[0]) * (t0 + t1) / 2, a[1] + (b[1] - a[1]) * (t0 + t1) / 2)
                adjacence, _voisin, _e = _sonder(p, normale, px_par_m, nom, locaux, batiment, exterieurs, vides)
                deperditif = adjacence in DEPERDITIFS and natures.get(nom, "chauffe") not in LOCAUX_NON_CHAUFFES
                decale = 7 if deperditif else 4
                q0 = (a[0] + (b[0] - a[0]) * t0 - normale[0] * decale, a[1] + (b[1] - a[1]) * t0 - normale[1] * decale)
                q1 = (a[0] + (b[0] - a[0]) * t1 - normale[0] * decale, a[1] + (b[1] - a[1]) * t1 - normale[1] * decale)
                dessin.line((q0, q1), fill=COULEURS[adjacence] + (255,), width=12 if deperditif else 5)
    police, petite = env._police(34), env._police(26)
    for fiche, (nom, forme) in zip(fiches_locaux, formes):
        pt = forme.representative_point()
        lignes = [nom[:30], f"{fiche['local'].replace('_', ' ')} · {fiche['surface_m2']:.1f} m²",
                  f"déperditif {fiche['deperditif_m']:.2f} m"]
        largeur_bloc = max(dessin.textlength(l, font=petite) for l in lignes) + 14
        dessin.rectangle((pt.x - largeur_bloc / 2, pt.y - 44, pt.x + largeur_bloc / 2, pt.y + 44), fill=(255, 255, 255, 225))
        for rang, ligne in enumerate(lignes):
            dessin.text((pt.x - largeur_bloc / 2 + 7, pt.y - 42 + rang * 29), ligne,
                        fill=(214, 40, 40) if rang == 2 and fiche["deperditif_m"] else (20, 20, 20), font=petite)
    xs = [x for _n, f in formes for x, _y in f.exterior.coords]
    ys = [y for _n, f in formes for _x, y in f.exterior.coords]
    recadre = image.crop((int(min(xs)) - 120, int(min(ys)) - 170, int(max(xs)) + 120, int(max(ys)) + 120))
    legende = ImageDraw.Draw(recadre)
    x = 20
    for cle in ("exterieur", "non_chauffe", "gaine_technique", "vide", "circulation", "chauffe", "inconnu"):
        legende.line((x, 38, x + 50, 38), fill=COULEURS[cle], width=12 if cle in DEPERDITIFS else 5)
        legende.text((x + 60, 20), LIBELLES[cle], fill=(20, 20, 20), font=police)
        x += 90 + legende.textlength(LIBELLES[cle], font=police)
    legende.text((20, 70), "trait épais = côté déperditif", fill=(20, 20, 20), font=police)
    recadre.thumbnail((2400, 2400))
    recadre.save(chemin, optimize=True)
    return chemin
