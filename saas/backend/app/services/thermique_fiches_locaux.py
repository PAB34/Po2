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
from shapely.geometry import LineString, Point, Polygon
from shapely.prepared import prep

from app.services import thermique_enveloppe_pieces as pieces_env
from app.services import thermique_parcours_enveloppe as env

PAS_COTE_M = 0.10
SONDE_DEBUT_CM, SONDE_PAS_CM, SONDE_MAX_CM = 5, 3, 120
COTE_MIN_M = 0.15
RATTACHEMENT_M = 0.90
DEPERDITIFS = {"exterieur", "non_chauffe", "vide"}
ORIENTATIONS = ("N", "NE", "E", "SE", "S", "SO", "O", "NO")


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


def _sonder(point: tuple[float, float], normale: tuple[float, float], px_par_m: float, soi: str,
            locaux: list[tuple[str, Any, str]], batiment: Any, exterieurs: list[Any], vides: list[Any]) -> tuple[str, str, float]:
    """(adjacence, voisin, épaisseur en cm) au droit d'un point du contour."""
    for cm in range(SONDE_DEBUT_CM, SONDE_MAX_CM + 1, SONDE_PAS_CM):
        q = Point(point[0] + normale[0] * cm / 100 * px_par_m, point[1] + normale[1] * cm / 100 * px_par_m)
        for nom, forme, nature in locaux:
            if nom != soi and forme.contains(q):
                return nature, nom, cm
        if any(forme.contains(q) for forme in exterieurs) or not batiment.contains(q):
            return "exterieur", "extérieur", cm
        if any(forme.contains(q) for forme in vides):
            return "vide", "vide", cm
    return "inconnu", "", float(SONDE_MAX_CM)


def fiches(analyse: dict[str, Any], manifeste: dict[str, Any], brut: dict[str, Any] | None = None,
           synthese: list[dict[str, Any]] | None = None, nord_deg: float | None = None) -> list[dict[str, Any]]:
    """Une fiche par local : côtés (adjacence, épaisseur, orientation, déperditif), enveloppe rattachée."""
    largeur, hauteur = manifeste["page_px"]
    px_par_m = manifeste["px_par_m"]
    batiment = prep(batiment_du_manifeste(manifeste))
    natures = pieces_env.natures_du_plan(analyse)
    locaux_formes = [(nom, forme, natures.get(nom, "chauffe")) for nom, forme in pieces_env.pieces_du_plan(analyse, largeur, hauteur)]
    locaux = [(nom, prep(forme), nature) for nom, forme, nature in locaux_formes]
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
        for a, b in zip(coords, coords[1:]):
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
                                 "epaisseur": epaisseur, "normale": normale})
        cotes = _regrouper(sondages)
        lignes_cotes = [LineString([s["p"] for s in c["sondages"]]) if len(c["sondages"]) > 1 else Point(c["sondages"][0]["p"])
                        for c in cotes]
        # chaque élément d'enveloppe va au seul côté extérieur le plus proche (à moins de RATTACHEMENT_M)
        affectation: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for element in enveloppe_par_local.get(nom, []):
            milieu = element["_face"].interpolate(0.5, normalized=True)
            candidats = [(lignes_cotes[r].distance(milieu), r) for r, c in enumerate(cotes) if c["adjacence"] == "exterieur"]
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
                "deperditif": cote["adjacence"] in DEPERDITIFS and nature != "non_chauffe",
                "enveloppe": [],
            }
            if cote["adjacence"] == "exterieur":
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
            alertes.append(f"{len(orphelins)} élément(s) d'enveloppe relevé(s) sans côté extérieur correspondant "
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
            "par_adjacence": {a: round(sum(c["longueur_m"] for c in details if c["adjacence"] == a), 2)
                              for a in sorted({c["adjacence"] for c in details})},
            "baies": synthese_local.get("menuiseries", []),
            "ponts": synthese_local.get("ponts", {}),
            "liaison_plancher_m": synthese_local.get("liaison_plancher_m", 0.0),
            "a_completer": ["plancher bas", "plancher haut", "hauteur sous plafond (coupes)"],
            "alertes": alertes,
        })
    return resultat


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


COULEURS = {"exterieur": (214, 40, 40), "non_chauffe": (240, 140, 0), "vide": (156, 54, 181),
            "circulation": (25, 113, 194), "chauffe": (120, 130, 140), "inconnu": (0, 0, 0)}
LIBELLES = {"exterieur": "extérieur", "non_chauffe": "local non chauffé", "vide": "vide / patio",
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
    locaux = [(nom, prep(forme), natures.get(nom, "chauffe")) for nom, forme in formes]
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
                deperditif = adjacence in DEPERDITIFS and natures.get(nom, "chauffe") != "non_chauffe"
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
    for cle in ("exterieur", "non_chauffe", "vide", "circulation", "chauffe", "inconnu"):
        legende.line((x, 38, x + 50, 38), fill=COULEURS[cle], width=12 if cle in DEPERDITIFS else 5)
        legende.text((x + 60, 20), LIBELLES[cle], fill=(20, 20, 20), font=police)
        x += 90 + legende.textlength(LIBELLES[cle], font=police)
    legende.text((20, 70), "trait épais = côté déperditif", fill=(20, 20, 20), font=police)
    recadre.thumbnail((2400, 2400))
    recadre.save(chemin, optimize=True)
    return chemin
