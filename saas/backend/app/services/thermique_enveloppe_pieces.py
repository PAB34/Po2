"""Découpage des éléments de l'enveloppe pièce par pièce (décisions D18 à D20).

Les intervalles relevés le long de l'enveloppe sont coupés là où la pièce située derrière leur face intérieure
change ; chaque morceau est rattaché à sa pièce et mesuré sur sa face intérieure (dimensions intérieures, règle
française). Les ponts thermiques sont rattachés à la pièce qui les contient, ou partagés moitié-moitié entre
les deux pièces qu'un refend ou une cloison sépare.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw
from shapely.geometry import Point, Polygon

from app.services import thermique_parcours_enveloppe as env

PAS_M = 0.05  # pas du sondage le long de l'enveloppe
SONDES_CM = (30, 60, 15)  # profondeurs sondées derrière le nu intérieur, dans l'ordre
TOLERANCE_M = 0.8  # pièce la plus proche acceptée si aucun sondage ne tombe dans une pièce
RECALAGE_M = 0.30  # une coupe est recalée sur l'about de cloison ou de refend voisin
MORCEAU_MIN_M = 0.15  # un morceau plus court est rendu à son voisin (bruit au droit d'une cloison)
TYPES_DECOUPES = {"paroi", "menuiserie", "poteau", "garde_corps", "indetermine"}
ANGLES = {"angle_sortant", "angle_rentrant"}
ABOUTS = {"about_refend"}
SANS_PIECE = "hors pièce"


def pieces_du_plan(analyse: dict[str, Any], largeur_px: float, hauteur_px: float) -> list[tuple[str, Polygon]]:
    """Pièces de la passe globale, en pixels de la page haute définition.

    Plusieurs pièces peuvent porter le même nom (six bureaux « B.asst ») : elles restent distinctes, numérotées.
    """
    resultat = []
    for objet in analyse["objects"]:
        if objet["category"] != "piece" or len(objet["points"]) < 3:
            continue
        forme = Polygon([(x * largeur_px / 1000, y * hauteur_px / 1000) for x, y in objet["points"]]).buffer(0)
        if forme.area > 0:
            resultat.append((objet.get("subtype") or objet["id"], forme))
    homonymes = {nom for nom, _ in resultat if sum(1 for autre, _f in resultat if autre == nom) > 1}
    rangs: dict[str, int] = {}
    numerotes = []
    for nom, forme in resultat:
        if nom in homonymes:
            rangs[nom] = rangs.get(nom, 0) + 1
            nom = f"{nom} ({rangs[nom]})"
        numerotes.append((nom, forme))
    return numerotes


def natures_du_plan(analyse: dict[str, Any]) -> dict[str, str]:
    """Nature de chaque pièce (chauffe, circulation, non_chauffe ; D24), sous le même nom que pieces_du_plan."""
    objets = [o for o in analyse["objects"] if o["category"] == "piece" and len(o["points"]) >= 3]
    noms = [o.get("subtype") or o["id"] for o in objets]
    rangs: dict[str, int] = {}
    resultat = {}
    for nom, objet in zip(noms, objets):
        if noms.count(nom) > 1:
            rangs[nom] = rangs.get(nom, 0) + 1
            nom = f"{nom} ({rangs[nom]})"
        resultat[nom] = objet.get("local") or "chauffe"
    return resultat


def _interpoler(element: dict[str, Any], s: float) -> tuple[float, float]:
    """Nus extérieur et intérieur à l'abscisse s (paroi en biais : variation linéaire)."""
    ext, inte, ext_fin, inte_fin = env.nus(element)
    longueur = element["fin_m"] - element["debut_m"]
    t = 0.0 if longueur <= 0 else min(1.0, max(0.0, (s - element["debut_m"]) / longueur))
    return ext + (ext_fin - ext) * t, inte + (inte_fin - inte) * t


def piece_derriere(pieces: list[tuple[str, Polygon]], troncon: dict[str, Any], element: dict[str, Any], s: float,
                   px_par_m: float) -> str:
    """Pièce située derrière la face intérieure de l'élément, à l'abscisse s."""
    _ext, inte = _interpoler(element, s)
    for sonde in SONDES_CM:
        point = Point(env._point(troncon, s, inte - sonde, px_par_m))
        for nom, forme in pieces:
            if forme.contains(point):
                return nom
    point = Point(env._point(troncon, s, inte - SONDES_CM[0], px_par_m))
    proche = min(pieces, key=lambda item: item[1].distance(point), default=None)
    if proche is not None and proche[1].distance(point) <= TOLERANCE_M * px_par_m:
        return proche[0]
    return troncon.get("piece") or SANS_PIECE


def _morceaux(etiquettes: list[str], pas: float) -> list[list[Any]]:
    """Suites d'étiquettes identiques [nom, premier, dernier+1] ; les morceaux trop courts rejoignent un voisin."""
    suites: list[list[Any]] = []
    for rang, nom in enumerate(etiquettes):
        if suites and suites[-1][0] == nom:
            suites[-1][2] = rang + 1
        else:
            suites.append([nom, rang, rang + 1])
    changement = True
    while changement and len(suites) > 1:
        changement = False
        for rang, (nom, debut, fin) in enumerate(suites):
            if (fin - debut) * pas >= MORCEAU_MIN_M:
                continue
            voisin = rang - 1 if rang > 0 else rang + 1
            suites[voisin][1] = min(suites[voisin][1], debut)
            suites[voisin][2] = max(suites[voisin][2], fin)
            del suites[rang]
            # deux voisins devenus identiques fusionnent
            fusion: list[list[Any]] = []
            for suite in suites:
                if fusion and fusion[-1][0] == suite[0]:
                    fusion[-1][2] = suite[2]
                else:
                    fusion.append(suite)
            suites = fusion
            changement = True
            break
    return suites


def _couper(element: dict[str, Any], debut: float, fin: float, piece: str) -> dict[str, Any]:
    ext_a, inte_a = _interpoler(element, debut)
    ext_b, inte_b = _interpoler(element, fin)
    return {**element, "debut_m": round(debut, 3), "fin_m": round(fin, 3), "piece": piece, "pieces": [[piece, 1.0]],
            "nu_exterieur_cm": round(ext_a, 2), "nu_interieur_cm": round(inte_a, 2),
            "nu_exterieur_fin_cm": round(ext_b, 2), "nu_interieur_fin_cm": round(inte_b, 2)}


def decouper_par_piece(brut: dict[str, Any], manifeste: dict[str, Any], analyse: dict[str, Any]) -> dict[str, Any]:
    """Relevé résolu (couches de la fiche, doublage présumé) dont chaque élément porte sa pièce."""
    brut = env.resoudre(brut)
    largeur, hauteur = manifeste["page_px"]
    px_par_m = manifeste["px_par_m"]
    pieces = pieces_du_plan(analyse, largeur, hauteur)
    par_id = {t["id"]: t for t in manifeste["troncons"]}
    abouts: dict[str, list[float]] = {}
    for element in brut["elements"]:
        if element["type"] in ABOUTS:
            abouts.setdefault(element["troncon"], []).append((element["debut_m"] + element["fin_m"]) / 2)
    elements = []
    for element in brut["elements"]:
        troncon = par_id.get(element["troncon"])
        if troncon is None or element["fin_m"] <= element["debut_m"]:
            elements.append(element)
            continue
        a, b = element["debut_m"], element["fin_m"]
        milieu = (a + b) / 2
        if element["type"] in TYPES_DECOUPES:
            nombre = max(1, round((b - a) / PAS_M))
            pas = (b - a) / nombre
            etiquettes = [piece_derriere(pieces, troncon, element, a + (k + 0.5) * pas, px_par_m) for k in range(nombre)]
            suites = _morceaux(etiquettes, pas)
            bornes = [a]
            for nom, debut, _fin in suites[1:]:
                coupe = a + debut * pas
                voisins = [x for x in abouts.get(element["troncon"], []) if abs(x - coupe) <= RECALAGE_M and a < x < b]
                bornes.append(min(voisins, key=lambda x: abs(x - coupe)) if voisins else coupe)
            bornes.append(b)
            for (nom, _debut, _fin), debut, fin in zip(suites, bornes, bornes[1:]):
                if fin > debut:
                    elements.append(_couper(element, debut, fin, nom))
        elif element["type"] in ABOUTS:
            # refend ou cloison : moitié à chaque pièce qu'il sépare
            avant = piece_derriere(pieces, troncon, element, a - RECALAGE_M, px_par_m)
            apres = piece_derriere(pieces, troncon, element, b + RECALAGE_M, px_par_m)
            partage = [[avant, 1.0]] if avant == apres else [[avant, 0.5], [apres, 0.5]]
            elements.append({**element, "piece": avant, "pieces": partage})
        else:
            nom = piece_derriere(pieces, troncon, element, milieu, px_par_m)
            elements.append({**element, "piece": nom, "pieces": [[nom, 1.0]]})
    resultat = {**brut, "elements": elements}
    resultat["raccords"] = raccorder_faces(resultat, manifeste)
    return resultat


def face_interieure(element: dict[str, Any], troncon: dict[str, Any], px_par_m: float) -> list[tuple[float, float]]:
    """Segment de la face intérieure (pixels de la page) ; raccordé aux angles quand c'est fait (D21)."""
    if element.get("face_px"):
        return [tuple(point) for point in element["face_px"]]
    _e, inte = _interpoler(element, element["debut_m"])
    _e, inte_fin = _interpoler(element, element["fin_m"])
    return [env._point(troncon, element["debut_m"], inte, px_par_m), env._point(troncon, element["fin_m"], inte_fin, px_par_m)]


def longueur_interieure(element: dict[str, Any], troncon: dict[str, Any], px_par_m: float) -> float:
    """Longueur de la face intérieure, en m (dimensions intérieures ; exacte pour une paroi en biais)."""
    debut, fin = face_interieure(element, troncon, px_par_m)
    return math.dist(debut, fin) / px_par_m


FACES = {"paroi", "menuiserie", "poteau"}
RACCORD_ANGLE_MIN_DEG = 15  # en dessous, les deux faces sont dans le prolongement l'une de l'autre
RACCORD_ANGLE_MAX_DEG = 135  # au-delà, épingle due au guide ou au relevé, pas un angle de murs
RACCORD_PORTEE_M = 1.2  # le point de rencontre doit rester à cette distance des deux extrémités
RACCORD_ECART_MAX_M = 1.5  # écart d'abscisse maximal entre les deux faces (largeur de l'angle relevé)
RACCORD_TOLERANCE = 1.1  # déplacement maximal d'une face, en épaisseurs de mur (rapportées à l'angle)


def raccorder_faces(brut: dict[str, Any], manifeste: dict[str, Any]) -> list[dict[str, Any]]:
    """Prolonge les faces intérieures de part et d'autre d'un angle jusqu'à leur point de rencontre (D21).

    Le relevé suit la face extérieure : à un angle rentrant, la face intérieure est plus longue que la partie
    relevée (de l'épaisseur du mur de chaque côté) ; à un angle sortant, plus courte. En prolongeant chaque face
    jusqu'à l'intersection avec la suivante, comme on le fait à la main, les longueurs intérieures sont justes
    quelle que soit la largeur donnée à l'angle par l'agent. Un about de refend dans l'alignement n'est pas
    raccordé : l'épaisseur du refend n'appartient à aucune des deux pièces (elle est portée par le ψ).
    """
    par_id = {t["id"]: t for t in manifeste["troncons"]}
    px_par_m = manifeste["px_par_m"]
    perimetre = manifeste.get("perimetre_m") or max((t["fin_m"] for t in manifeste["troncons"]), default=0)
    decisions = {fiche["id"]: fiche.get("decision") for fiche in brut.get("catalogue", [])}
    raccords: list[dict[str, Any]] = []
    # la façade (tour fermé) et les côtés lus depuis la face intérieure des locaux (D46, sans tour fermé)
    for interieur in (False, True):
        elements = sorted((e for e in brut["elements"] if e["troncon"] in par_id
                           and (par_id[e["troncon"]].get("ligne") == "face_interieure") == interieur),
                          key=lambda e: e["debut_m"])
        raccords += _raccorder(elements, par_id, decisions, px_par_m, perimetre, boucle=not interieur)
    return raccords


def _raccorder(elements: list[dict[str, Any]], par_id: dict[str, Any], decisions: dict[str, Any], px_par_m: float,
               perimetre: float, boucle: bool) -> list[dict[str, Any]]:
    faces = [e for e in elements if e["type"] in FACES and decisions.get(e.get("composant") or "") != "exclu"]
    for element in faces:
        element["face_px"] = [list(p) for p in face_interieure(element, par_id[element["troncon"]], px_par_m)]
    raccords = []
    for rang, avant in enumerate(faces):
        if not boucle and rang == len(faces) - 1:
            break
        apres = faces[(rang + 1) % len(faces)]
        if apres is avant:
            break
        # mur contre mur, ou angle tout vitré ; un mur contre une baie s'arrête au tableau (déjà relevé),
        # un poteau n'a pas de face à prolonger
        if avant["type"] != apres["type"] or avant["type"] == "poteau":
            continue
        ecart = apres["debut_m"] - avant["fin_m"]
        if rang == len(faces) - 1:
            ecart += perimetre
        if ecart < -0.01 or ecart > RACCORD_ECART_MAX_M:
            continue
        entre = [e for e in elements if avant["fin_m"] - 0.01 <= e["debut_m"] < avant["fin_m"] + ecart - 0.01
                 and e is not avant and e is not apres]
        if any(e["type"] not in ANGLES | ABOUTS for e in entre):
            continue  # un autre élément (claustra, indéterminé) s'intercale : pas de raccord
        p1, q1 = avant["face_px"]
        p2, q2 = apres["face_px"]
        d1 = _direction(p1, q1, par_id[avant["troncon"]], px_par_m)
        d2 = _direction(p2, q2, par_id[apres["troncon"]], px_par_m)
        croix = d1[0] * d2[1] - d1[1] * d2[0]
        angle = math.degrees(math.atan2(abs(croix), d1[0] * d2[0] + d1[1] * d2[1]))
        if angle < RACCORD_ANGLE_MIN_DEG or angle > RACCORD_ANGLE_MAX_DEG:
            continue
        # q1 + t d1 = p2 + u d2
        t = ((p2[0] - q1[0]) * d2[1] - (p2[1] - q1[1]) * d2[0]) / croix
        point = (q1[0] + t * d1[0], q1[1] + t * d1[1])
        portee = RACCORD_PORTEE_M * px_par_m
        if math.dist(point, q1) > portee or math.dist(point, p2) > portee:
            continue
        avant_m = (math.dist(p1, q1) + math.dist(p2, q2)) / px_par_m
        genre = next((e["type"] for e in entre if e["type"] in ANGLES), "angle sans relevé")
        # garde-fou : de chaque côté, la face ne bouge pas plus que l'épaisseur du mur rapportée à l'angle
        # (au-delà, c'est le relevé qui est approximatif : le raccord est refusé et signalé)
        ext1, int1 = _interpoler(avant, avant["fin_m"])
        ext2, int2 = _interpoler(apres, apres["debut_m"])
        epaisseur = max(min(abs(ext1 - int1), abs(ext2 - int2)), 10) / 100 * px_par_m
        limite = RACCORD_TOLERANCE * epaisseur / max(math.sin(math.radians(angle)), 0.5)
        if abs(math.dist(p1, point) - math.dist(p1, q1)) > limite or abs(math.dist(point, q2) - math.dist(p2, q2)) > limite:
            raccords.append({"troncon": avant["troncon"], "abscisse_m": round(avant["fin_m"], 2), "angle_deg": round(angle),
                             "nature": "refusé", "liaison": genre, "allongement_m": 0.0,
                             "pieces": sorted({avant.get("piece", ""), apres.get("piece", "")})})
            continue
        avant["face_px"][1] = list(point)
        apres["face_px"][0] = list(point)
        apres_m = (math.dist(*avant["face_px"]) + math.dist(*apres["face_px"])) / px_par_m
        raccords.append({"troncon": avant["troncon"], "abscisse_m": round(avant["fin_m"], 2), "angle_deg": round(angle),
                         # parcours horaire à l'écran (y vers le bas) : produit vectoriel positif = angle sortant
                         "nature": "sortant" if croix > 0 else "rentrant", "liaison": genre,
                         "allongement_m": round(apres_m - avant_m, 3),
                         "pieces": sorted({avant.get("piece", ""), apres.get("piece", "")})})
    return raccords


def _direction(debut: Any, fin: Any, troncon: dict[str, Any], px_par_m: float) -> tuple[float, float]:
    longueur = math.dist(debut, fin)
    if longueur < 0.2 * px_par_m:  # face trop courte : direction du tronçon
        return tuple(troncon["direction"])
    return ((fin[0] - debut[0]) / longueur, (fin[1] - debut[1]) / longueur)


def synthese_pieces(brut: dict[str, Any], manifeste: dict[str, Any]) -> list[dict[str, Any]]:
    """Par pièce : parois et baies par composant, poteaux, ponts thermiques, linéaire de façade."""
    decisions = {fiche["id"]: fiche.get("decision") for fiche in brut.get("catalogue", [])}
    compositions = {fiche["id"]: env.composition_libelle(fiche.get("couches") or []) for fiche in brut.get("catalogue", [])}
    par_id = {t["id"]: t for t in manifeste["troncons"]}
    px_par_m = manifeste["px_par_m"]
    fiches: dict[str, dict[str, Any]] = {}

    def fiche_de(nom: str) -> dict[str, Any]:
        return fiches.setdefault(nom, {"piece": nom, "parois": {}, "menuiseries": {}, "poteaux": 0,
                                       "ponts": {"angle_sortant": 0.0, "angle_rentrant": 0.0, "about_refend": 0.0},
                                       "facade_m": 0.0, "sur_non_chauffe_m": 0.0})

    for element in brut["elements"]:
        troncon = par_id.get(element["troncon"])
        composant = element.get("composant") or ""
        if troncon is None or "piece" not in element or decisions.get(composant) == "exclu":
            continue
        genre = element["type"]
        if genre in ANGLES | ABOUTS:
            for nom, part in element["pieces"]:
                fiche_de(nom)["ponts"][genre] += part
            continue
        fiche = fiche_de(element["piece"])
        longueur = longueur_interieure(element, troncon, px_par_m)
        # D46 : paroi ou baie sur local non chauffé ou vide, lue depuis la face intérieure : hors façade
        cle_longueur = "sur_non_chauffe_m" if troncon.get("ligne") == "face_interieure" else "facade_m"
        if genre in ("paroi", "menuiserie", "poteau") and cle_longueur == "sur_non_chauffe_m":
            fiche[cle_longueur] += longueur
            if genre == "poteau":
                continue
            ligne = fiche["parois" if genre == "paroi" else "menuiseries"].setdefault(
                composant or genre, {"composant": composant, "composition": compositions.get(composant, ""),
                                     "type": element.get("menuiserie_type", ""), "largeurs_cm": [], "lineaire_m": 0.0,
                                     "sur_non_chauffe": True})
            ligne["lineaire_m"] += longueur
            continue
        if genre == "paroi":
            cle = composant or env.composition_libelle(element["couches"])
            ligne = fiche["parois"].setdefault(cle, {
                "composant": composant, "composition": compositions.get(composant) or env.composition_libelle(element["couches"]),
                "lineaire_m": 0.0})
            ligne["lineaire_m"] += longueur
            fiche["facade_m"] += longueur
        elif genre == "menuiserie":
            cle = composant or element.get("menuiserie_type") or "menuiserie"
            ligne = fiche["menuiseries"].setdefault(cle, {"composant": composant, "type": element.get("menuiserie_type", ""),
                                                          "largeurs_cm": [], "lineaire_m": 0.0})
            ligne["largeurs_cm"].append(round(longueur * 100))
            ligne["lineaire_m"] += longueur
            fiche["facade_m"] += longueur
        elif genre == "poteau":
            fiche["poteaux"] += 1
            fiche["facade_m"] += longueur
    resultat = []
    for fiche in fiches.values():
        resultat.append({
            "piece": fiche["piece"],
            "parois": [{**v, "lineaire_m": round(v["lineaire_m"], 2)} for v in fiche["parois"].values()],
            "menuiseries": [{**v, "lineaire_m": round(v["lineaire_m"], 2)} for v in fiche["menuiseries"].values()],
            "poteaux": fiche["poteaux"],
            "ponts": {k: round(v, 2) for k, v in fiche["ponts"].items()},
            "facade_m": round(fiche["facade_m"], 2),
            "sur_non_chauffe_m": round(fiche["sur_non_chauffe_m"], 2),
            # la liaison avec les planchers court sur toute la façade de la pièce (D20)
            "liaison_plancher_m": round(fiche["facade_m"], 2),
        })
    return resultat


REGROUPEMENT_FACADE_M = 30.0  # une pièce avec plus de façade que cela regroupe vraisemblablement plusieurs locaux


def demandes_etude(synthese: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Informations à demander à l'architecte ou au maître d'ouvrage (apport de l'étude, décision 2026-09-22).

    Un espace ouvert qui regroupe plusieurs locaux (« inclut », « et », très grande façade) est laissé d'un seul
    tenant ; l'étude demande son découpage précis en zones.
    """
    demandes = []
    for fiche in synthese:
        nom = fiche["piece"]
        motifs = []
        if "inclut" in nom.lower():
            motifs.append("le nom regroupe plusieurs locaux")
        elif " et " in nom:
            motifs.append("deux locaux sous un même nom")
        if fiche["facade_m"] > REGROUPEMENT_FACADE_M:
            motifs.append(f"{_nombre(fiche['facade_m'])} m de façade")
        if motifs:
            demandes.append({"piece": nom, "objet": "Découpage précis des zones",
                             "motif": " ; ".join(motifs),
                             "consequence": "façade, baies et ponts thermiques comptés sur l'espace entier en attendant"})
    return demandes


PALETTE = [(230, 119, 0), (47, 158, 68), (25, 113, 194), (174, 62, 201), (224, 49, 49), (12, 166, 120),
           (240, 140, 0), (102, 70, 200), (194, 37, 92), (8, 127, 140), (92, 148, 13), (201, 42, 42)]


def _nombre(valeur: float) -> str:
    return f"{valeur:g}".replace(".", ",")


def planche_pieces(page_image: Image.Image, manifeste: dict[str, Any], analyse: dict[str, Any], brut: dict[str, Any],
                   synthese: list[dict[str, Any]], chemin: Path, reduction: float = 0.4) -> Path:
    """Plan des pièces : chaque pièce et sa façade de la même couleur, baies en bleu, ponts thermiques marqués."""
    largeur, hauteur = manifeste["page_px"]
    px_par_m = manifeste["px_par_m"]
    par_id = {t["id"]: t for t in manifeste["troncons"]}
    fond = page_image.convert("RGB").resize((round(page_image.width * reduction), round(page_image.height * reduction)))
    calque = Image.new("RGBA", fond.size, (0, 0, 0, 0))
    dessin = ImageDraw.Draw(calque)
    couleurs = {fiche["piece"]: PALETTE[rang % len(PALETTE)] for rang, fiche in enumerate(synthese)}
    formes = dict(pieces_du_plan(analyse, largeur, hauteur))

    def r(point: tuple[float, float]) -> tuple[float, float]:
        return (point[0] * reduction, point[1] * reduction)

    for nom, forme in formes.items():
        if nom in couleurs and forme.geom_type == "Polygon":
            rouge, vert, bleu = couleurs[nom]
            dessin.polygon([r(p) for p in forme.exterior.coords], fill=(rouge, vert, bleu, 45))
    decisions = {fiche["id"]: fiche.get("decision") for fiche in brut.get("catalogue", [])}
    for element in brut["elements"]:
        troncon = par_id.get(element["troncon"])
        if troncon is None or "piece" not in element or decisions.get(element.get("composant") or "") == "exclu":
            continue
        genre = element["type"]
        _e, inte = _interpoler(element, element["debut_m"])
        _e, inte_fin = _interpoler(element, element["fin_m"])
        debut, fin = (r(p) for p in face_interieure(element, troncon, px_par_m))
        if genre == "paroi":
            dessin.line((debut, fin), fill=(*couleurs.get(element["piece"], (90, 90, 90)), 255), width=7)
        elif genre == "menuiserie":
            dessin.line((debut, fin), fill=(0, 150, 200, 255), width=7)
            for point in (debut, fin):  # coupe au droit de la baie
                dessin.ellipse((point[0] - 3, point[1] - 3, point[0] + 3, point[1] + 3), fill=(0, 90, 130, 255))
        elif genre == "poteau":
            dessin.line((debut, fin), fill=(40, 40, 40, 255), width=9)
        elif genre in ANGLES:
            x, y = r(env._point(troncon, (element["debut_m"] + element["fin_m"]) / 2, inte - 10, px_par_m))
            dessin.ellipse((x - 7, y - 7, x + 7, y + 7), outline=(214, 51, 108, 255), width=3)
        elif genre in ABOUTS:
            x, y = r(env._point(troncon, (element["debut_m"] + element["fin_m"]) / 2, inte - 10, px_par_m))
            partage = len(element["pieces"]) > 1
            dessin.rectangle((x - 6, y - 6, x + 6, y + 6), outline=(214, 51, 108, 255), width=3,
                             fill=(214, 51, 108, 120) if partage else None)
    image = Image.alpha_composite(fond.convert("RGBA"), calque).convert("RGB")
    # étiquettes : nom, façade, composants, ponts
    dessin = ImageDraw.Draw(image)
    police, petite = env._police(20), env._police(16)
    for fiche in synthese:
        forme = formes.get(fiche["piece"])
        if forme is None:
            continue
        x, y = r(forme.representative_point().coords[0])
        lignes = [f"façade {_nombre(fiche['facade_m'])} m"]
        lignes += [f"{p['composant'] or 'paroi'} {_nombre(p['lineaire_m'])} m" for p in fiche["parois"]]
        lignes += [f"{m['composant'] or m['type']} {_nombre(m['lineaire_m'])} m" for m in fiche["menuiseries"]]
        ponts = fiche["ponts"]
        if any(ponts.values()):
            lignes.append(f"ψ angles {_nombre(ponts['angle_sortant'] + ponts['angle_rentrant'])} · refends {_nombre(ponts['about_refend'])}")
        titre = fiche["piece"][:34]
        hauteur_bloc = 24 + 19 * len(lignes)
        largeur_bloc = max([dessin.textlength(titre, font=police)] + [dessin.textlength(l, font=petite) for l in lignes]) + 14
        rouge, vert, bleu = couleurs[fiche["piece"]]
        dessin.rectangle((x - largeur_bloc / 2, y - hauteur_bloc / 2, x + largeur_bloc / 2, y + hauteur_bloc / 2),
                         fill="white", outline=(rouge, vert, bleu), width=3)
        dessin.text((x - largeur_bloc / 2 + 7, y - hauteur_bloc / 2 + 3), titre, fill=(rouge, vert, bleu), font=police)
        for rang, ligne in enumerate(lignes):
            dessin.text((x - largeur_bloc / 2 + 7, y - hauteur_bloc / 2 + 26 + 19 * rang), ligne, fill="#172033", font=petite)
    image.save(chemin, optimize=True)
    return chemin
