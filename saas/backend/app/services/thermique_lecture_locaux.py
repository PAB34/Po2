"""Lecture de l'enveloppe local par local (essai D42 à D45, docs/thermique/piece-par-piece-decisions.md § 8).

Au lieu de longer la face extérieure du bâtiment, l'agent lit les côtés de chaque local chauffé qui donnent sur
l'extérieur, un local non chauffé, un vide, ou derrière lesquels le sondage n'a rien trouvé. La ligne 0 de chaque
bande est la face intérieure du local : les longueurs intérieures sont lues directement et une façade en dents
de scie est suivie comme le contour du local. Le reste de la chaîne (lots, catalogue, restitution, fiches) est
inchangé. Pixels seuls, aucun vecteur PDF.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw
from shapely.geometry import Point, Polygon
from shapely.prepared import prep

from app.services import thermique_enveloppe_pieces as pieces_env
from app.services import thermique_fiches_locaux as fiches_locaux
from app.services import thermique_parcours_enveloppe as env

LOCAUX_LUS = {"chauffe", "circulation"}
ADJACENCES_LUES = {"exterieur", "non_chauffe", "vide", "inconnu"}
BANDE = {"interieure": 0.40, "exterieure": 0.90}
PAS_M = 0.10
MORCEAU_MIN_M = 0.30  # une suite de sondages plus courte rejoint ses voisins
COTE_MIN_M = 0.30
SIMPLIFICATION_M = 0.04
SAUT_M = 100.0  # écart d'abscisse entre deux locaux : aucun raccord d'angle d'un local à l'autre


def _anneau_horaire(forme: Polygon) -> list[tuple[float, float]]:
    """Contour dont la normale (-uy, ux) de chaque côté pointe hors du local (même sens que le guide)."""
    anneau = list(forme.exterior.coords)[:-1]
    # repère image (y vers le bas) : aire de Gauss négative = sens horaire à l'écran, comme contour_guide
    aire = sum(anneau[k][0] * anneau[k - 1][1] - anneau[k - 1][0] * anneau[k][1] for k in range(len(anneau)))
    if aire > 0:
        anneau.reverse()
    a, b = max(zip(anneau, anneau[1:] + anneau[:1]), key=lambda c: math.dist(*c))
    longueur = math.dist(a, b)
    ux, uy = (b[0] - a[0]) / longueur, (b[1] - a[1]) / longueur
    if forme.contains(Point((a[0] + b[0]) / 2 - uy * 3, (a[1] + b[1]) / 2 + ux * 3)):
        anneau.reverse()
    return anneau


def _suites(etiquettes: list[bool], pas: float) -> list[tuple[int, int]]:
    """Suites de sondages à lire [premier, dernier+1] ; les trous et morceaux trop courts sont absorbés."""
    suites: list[list[Any]] = []
    for rang, lu in enumerate(etiquettes):
        if suites and suites[-1][0] == lu:
            suites[-1][2] = rang + 1
        else:
            suites.append([lu, rang, rang + 1])
    change = True
    while change and len(suites) > 1:
        change = False
        for rang, (lu, debut, fin) in enumerate(suites):
            if (fin - debut) * pas >= MORCEAU_MIN_M:
                continue
            suites[rang][0] = not lu
            fusion: list[list[Any]] = []
            for suite in suites:
                if fusion and fusion[-1][0] == suite[0]:
                    fusion[-1][2] = suite[2]
                else:
                    fusion.append(suite)
            suites = fusion
            change = True
            break
    return [(debut, fin) for lu, debut, fin in suites if lu]


def troncons_par_local(analyse: dict[str, Any], largeur: float, hauteur: float, px_par_m: float,
                       batiment: Polygon, adjacences: set[str] = ADJACENCES_LUES, prefixe: str = "T",
                       depart_m: float = 0.0, longueur_min_m: float = 0.0,
                       exiges: set[str] | None = None) -> list[dict[str, Any]]:
    """Un tronçon par côté de local chauffé dont les sondages trouvent `adjacences` derrière le mur.

    `exiges` : une suite n'est gardée que si au moins PART_EXIGEE de ses sondages trouvent l'une de ces adjacences
    (le sondage alterne souvent entre « vide » et « rien trouvé » le long d'un vide mal délimité) ; son adjacence
    est alors la plus fréquente d'entre elles.
    """
    natures = pieces_env.natures_du_plan(analyse)
    formes = pieces_env.pieces_du_plan(analyse, largeur, hauteur)
    locaux = [(nom, prep(forme), natures.get(nom, "chauffe")) for nom, forme in formes]
    exterieurs = [prep(f) for f in fiches_locaux._formes(analyse, {"terrasse", "balcon"}, int(largeur), int(hauteur))]
    vides = [prep(Polygon([(x * largeur / 1000, y * hauteur / 1000) for x, y in e["points"]]).buffer(0))
             for e in analyse.get("locaux_ecartes", []) if e.get("decision") == "vide" and e.get("points")]
    batiment_p = prep(batiment)
    resultat: list[dict[str, Any]] = []
    abscisse = depart_m
    for nom, forme in formes:
        if natures.get(nom, "chauffe") not in LOCAUX_LUS:
            continue
        anneau = _anneau_horaire(forme.simplify(SIMPLIFICATION_M * px_par_m))
        tour = 0.0
        for cote, (a, b) in enumerate(zip(anneau, anneau[1:] + anneau[:1]), 1):
            longueur_m = math.dist(a, b) / px_par_m
            if longueur_m < COTE_MIN_M:
                tour += longueur_m
                continue
            ux, uy = (b[0] - a[0]) / (longueur_m * px_par_m), (b[1] - a[1]) / (longueur_m * px_par_m)
            normale = (-uy, ux)
            nombre = max(1, round(longueur_m / PAS_M))
            pas = longueur_m / nombre
            sondes = []
            for k in range(nombre):
                s = (k + 0.5) * pas
                p = (a[0] + ux * s * px_par_m, a[1] + uy * s * px_par_m)
                sondes.append(fiches_locaux._sonder(p, normale, px_par_m, nom, locaux, batiment_p, exterieurs, vides)[0])
            for debut, fin in _suites([adj in adjacences for adj in sondes], pas):
                d0, d1 = debut * pas, fin * pas
                if d1 - d0 < longueur_min_m:
                    continue
                vues = sondes[debut:fin]
                if exiges:
                    retenues = [a for a in vues if a in exiges]
                    if len(retenues) < PART_EXIGEE * len(vues):
                        continue
                    vues = retenues
                majoritaire = max(set(vues), key=vues.count)
                parts = max(1, math.ceil((d1 - d0) / env.TRONCON_MAX_M - 1e-9))
                for k in range(parts):
                    local_debut = d0 + (d1 - d0) * k / parts
                    local_fin = d0 + (d1 - d0) * (k + 1) / parts
                    resultat.append({
                        "id": f"{prefixe}{len(resultat) + 1:02d}",
                        "cote": cote,
                        "origine_px": [a[0], a[1]],
                        "direction": [ux, uy],
                        "normale_ext": [normale[0], normale[1]],
                        "local_debut_m": round(local_debut, 3),
                        "local_fin_m": round(local_fin, 3),
                        "debut_m": round(abscisse + tour + local_debut, 3),
                        "fin_m": round(abscisse + tour + local_fin, 3),
                        "piece": nom,
                        "adjacence": majoritaire,
                        "ligne": "face_interieure",
                        "bande_m": dict(BANDE),
                    })
            tour += longueur_m
        abscisse += tour + SAUT_M
    return resultat


ADJACENCES_COMPLEMENT = {"non_chauffe", "vide"}
PART_EXIGEE = 0.30
COMPLEMENT_MIN_M = 0.5
COMPLEMENT_DEPART_M = 10000.0  # loin du périmètre de la façade : aucun raccord d'angle avec les tronçons T


def complement(analyse: dict[str, Any], largeur: float, hauteur: float, px_par_m: float,
               batiment: Polygon) -> list[dict[str, Any]]:
    """D46 : côtés des locaux chauffés sur un local non chauffé ou un vide, lus en plus du parcours de la façade."""
    return troncons_par_local(analyse, largeur, hauteur, px_par_m, batiment, ADJACENCES_COMPLEMENT | {"inconnu"}, "U",
                              COMPLEMENT_DEPART_M, COMPLEMENT_MIN_M, exiges=ADJACENCES_COMPLEMENT)


def _plan_guide(page: Image.Image, batiment: Polygon, liste: list[dict[str, Any]], chemin: Path, px_par_m: float) -> Path:
    x0, y0, x1, y1 = batiment.bounds
    marge = 400
    boite = (max(0, int(x0) - marge), max(0, int(y0) - marge), min(page.width, int(x1) + marge), min(page.height, int(y1) + marge))
    image = page.crop(boite).convert("RGB")
    dessin = ImageDraw.Draw(image)
    police = env._police(40)
    for troncon in liste:
        debut = env._point(troncon, troncon["debut_m"], 0, px_par_m)
        fin = env._point(troncon, troncon["fin_m"], 0, px_par_m)
        dessin.line([(debut[0] - boite[0], debut[1] - boite[1]), (fin[0] - boite[0], fin[1] - boite[1])], fill="#d6336c", width=8)
        x, y = env._point(troncon, (troncon["debut_m"] + troncon["fin_m"]) / 2, -45, px_par_m)
        dessin.text((x - boite[0] - 25, y - boite[1] - 20), troncon["id"], fill="#0b3d91", font=police)
    image.thumbnail((2400, 2400))
    image.save(chemin, quality=90)
    return chemin


def preparer(pdf: Path, analyse: dict[str, Any], dossier: Path, page: int = 1, dpi: int = 300,
             echelle: float = 100) -> dict[str, Any]:
    """Comme env.preparer, avec un tronçon par côté déperditif de chaque local."""
    rotation = int(analyse["manifest"]["rotation_deg_ccw"])
    page_image = env.rendre_page(pdf, page, dpi, rotation)
    largeur, hauteur = page_image.size
    px_par_m = dpi / env.M_PAR_POUCE / echelle
    batiment = env.contour_guide(analyse, largeur, hauteur, px_par_m, page_image)["polygone"]
    liste = troncons_par_local(analyse, largeur, hauteur, px_par_m, batiment)
    dossier.mkdir(parents=True, exist_ok=True)
    planches: list[dict[str, Any]] = []
    graduees = [env._graduer(env._bande(page_image, t, px_par_m), t, px_par_m) for t in liste]
    for debut in range(0, len(graduees), env.BANDES_PAR_PLANCHE):
        groupe = graduees[debut: debut + env.BANDES_PAR_PLANCHE]
        planche = Image.new("RGB", (max(i.width for i in groupe), sum(i.height + 24 for i in groupe)), "#e9ecef")
        y = 0
        for image in groupe:
            planche.paste(image, (0, y))
            y += image.height + 24
        chemin = dossier / f"enveloppe-{len(planches) + 1:02d}.png"
        planche.save(chemin, optimize=True)
        planches.append({"chemin": str(chemin.resolve()), "troncons": [t["id"] for t in liste[debut: debut + env.BANDES_PAR_PLANCHE]]})
    plan = _plan_guide(page_image, batiment, liste, dossier / "enveloppe-guide.jpg", px_par_m)
    manifeste = {
        "version": 1,
        "methode": "parcours_enveloppe_raster",
        "mode": "par_local",
        "uses_pdf_vectors": False,
        "dpi": dpi,
        "echelle": echelle,
        "px_par_m": px_par_m,
        "page_px": [largeur, hauteur],
        "bande_m": {**BANDE, "recouvrement": env.RECOUVREMENT_M},
        "perimetre_m": round(sum(t["fin_m"] - t["debut_m"] for t in liste), 2),
        "troncons": liste,
        "batiment_px": [list(p) for p in batiment.exterior.coords],
        "trous_px": [],
        "guide": "cotes_des_locaux",
        "planches": planches,
        "plan_guide": str(plan.resolve()),
    }
    (dossier / "enveloppe-manifeste.json").write_text(json.dumps(manifeste, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifeste
