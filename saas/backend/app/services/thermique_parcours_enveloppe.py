"""Parcours de l'enveloppe extérieure (docs/thermique/parcours-enveloppe-decisions.md).

Une fois les pièces identifiées, elles délimitent le volume ; le remplissage de l'extérieur sur l'image donne
alors la face extérieure réelle de l'enveloppe, zigzags compris. Ce contour sert de guide :
il est découpé en tronçons de 5 m au plus, chacun rendu à 300 dpi dans une bande redressée (extérieur en haut,
intérieur en bas) et gradué en abscisse (m, le long de l'enveloppe) et en profondeur (cm, depuis la ligne
guide). L'agent lit chaque bande comme un relevé linéaire ; ses intervalles sont ensuite reprojetés sur la
feuille. Seuls des pixels sont lus : aucun vecteur PDF.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

M_PAR_POUCE = 0.0254
TRONCON_MAX_M = 5.0
RECOUVREMENT_M = 0.6
BANDE_INTERIEURE_M = 0.90
FACADE_PORTEE_M = 1.2
FACADE = {"mur_exterieur", "isolation", "menuiserie_exterieure"}
BANDE_EXTERIEURE_M = 0.40
FERMETURE_M = 0.25
SIMPLIFICATION_M = 0.10
SIMPLIFICATION_RASTER_M = 0.12
FACADE_MARGE_M = 0.9
COTE_MIN_M = 0.50
AGRANDISSEMENT = 2
BANDES_PAR_PLANCHE = 6
MARGE_GAUCHE = 150
MARGE_HAUT = 70

TYPES = (
    "paroi",
    "menuiserie",
    "poteau",
    "angle_sortant",
    "angle_rentrant",
    "about_refend",
    "about_plancher",
    "garde_corps",
    "indetermine",
)
COUCHES = ("mur", "isolant", "doublage", "lame_air", "parement", "bardage", "vitrage", "cadre", "autre")
# Catalogue appris pendant le parcours (D13) : un composant = un identifiant réutilisé à chaque occurrence.
GENRES_CATALOGUE = ("paroi", "menuiserie", "poteau", "liaison", "element_exterieur", "autre")
DECISIONS = ("integre", "exclu", "a_confirmer")
LOT_PLANCHES = 3


def _police(taille: int) -> ImageFont.ImageFont:
    for nom in ("arial.ttf", "DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nom, taille)
        except OSError:
            continue
    return ImageFont.load_default()


def rendre_page(pdf: Path, page: int, dpi: int, rotation_ccw: int) -> Image.Image:
    """Rendu en pixels de la page (pdfium), tourné comme le paquet de l'agent."""
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(str(pdf))
    try:
        image = document[page - 1].render(scale=dpi / 72).to_pil().convert("L")
    finally:
        document.close()
    return image.rotate(rotation_ccw, expand=True, fillcolor=255) if rotation_ccw else image


def contour_guide(
    analyse: dict[str, Any], largeur_px: float, hauteur_px: float, px_par_m: float, page: Image.Image | None = None
) -> dict[str, Any]:
    """Contour guide en pixels de la page haute définition.

    Sans image : contour extérieur de l'union des pièces (poussé jusqu'aux éléments de façade). Avec l'image :
    face extérieure réelle de l'enveloppe, zigzags compris, obtenue par remplissage de l'extérieur.
    """
    formes = []
    for objet in analyse["objects"]:
        if objet["category"] == "piece" and len(objet["points"]) >= 3:
            forme = Polygon([(x * largeur_px / 1000, y * hauteur_px / 1000) for x, y in objet["points"]]).buffer(0)
            if forme.area > 0:
                formes.append(forme)
    if not formes:
        raise ValueError("Aucune pièce : le parcours de l'enveloppe a besoin des pièces identifiées.")
    fermeture = FERMETURE_M * px_par_m
    union = unary_union([forme.buffer(fermeture, join_style=2) for forme in formes]).buffer(-fermeture, join_style=2)
    # Là où une pièce est approximative, le guide est poussé jusqu'aux éléments de façade vus par la passe
    # globale, limités à FACADE_PORTEE_M autour des pièces (l'escalier extérieur n'est pas absorbé).
    portee = union.buffer(FACADE_PORTEE_M * px_par_m)
    facade = []
    for objet in analyse["objects"]:
        if objet["category"] in FACADE and len(objet["points"]) >= 2:
            ligne = LineString([(x * largeur_px / 1000, y * hauteur_px / 1000) for x, y in objet["points"]])
            facade.append(ligne.intersection(portee).buffer(0.03 * px_par_m))
    if facade:
        union = unary_union([union, *facade]).buffer(fermeture, join_style=2).buffer(-fermeture, join_style=2)
    if union.geom_type == "MultiPolygon":
        union = max(union.geoms, key=lambda forme: forme.area)
    methode = "pieces"
    if page is not None:
        raster = face_exterieure(page, analyse, union, largeur_px, hauteur_px, px_par_m)
        # garde-fou : le volume trouvé doit rester comparable à celui des pièces
        if raster is not None and 0.85 <= raster.area / union.area <= 1.6:
            union, methode = raster, "remplissage_exterieur"
    union = union.simplify((SIMPLIFICATION_RASTER_M if methode != "pieces" else SIMPLIFICATION_M) * px_par_m)
    anneau = list(union.exterior.coords)[:-1]
    # sens horaire à l'écran (y vers le bas) : aire de Gauss positive
    aire = sum(anneau[k][0] * anneau[k - 1][1] - anneau[k - 1][0] * anneau[k][1] for k in range(len(anneau)))
    if aire > 0:
        anneau.reverse()
    # supprime les côtés trop courts, en gardant les angles
    propre: list[tuple[float, float]] = []
    for point in anneau:
        if propre and math.dist(propre[-1], point) < COTE_MIN_M * px_par_m:
            continue
        propre.append(point)
    depart = min(range(len(propre)), key=lambda k: propre[k][0] + propre[k][1])
    propre = propre[depart:] + propre[:depart]
    return {
        "anneau": propre,
        "polygone": union,
        "trous": [list(trou.coords)[:-1] for trou in union.interiors],
        "methode": methode,
    }


def face_exterieure(
    page: Image.Image, analyse: dict[str, Any], guide: Polygon, largeur_px: float, hauteur_px: float, px_par_m: float
) -> Polygon | None:
    """Volume du bâtiment = ce que le remplissage de l'extérieur n'atteint pas (pixels seuls).

    Deux remplissages : A arrêté par tous les traits (juste là où un vitrage n'est qu'un trait simple), B qui
    ignore les traits simples et fins (rive de dalle, axes, arcs) mais ne pénètre pas à plus de 30 cm dans les
    pièces. Les poches que B voit extérieures hors des pièces (dents de scie fermées par une rive) sont retirées
    de A. Les terrasses, balcons et espaces extérieurs à déterminer de la passe globale sont exclus.
    """
    reduction = 2
    zone = guide.buffer(3.0 * px_par_m, join_style=2)
    x0, y0 = max(0, int(zone.bounds[0])), max(0, int(zone.bounds[1]))
    x1, y1 = min(page.width, int(zone.bounds[2])), min(page.height, int(zone.bounds[3]))
    pixels = np.asarray(page.convert("L"))[y0:y1, x0:x1]
    h, w = pixels.shape[0] // reduction * reduction, pixels.shape[1] // reduction * reduction
    petit = pixels[:h, :w].reshape(h // reduction, reduction, w // reduction, reduction).min(axis=(1, 3))
    encre = petit < 200

    def masque(forme: Any) -> np.ndarray:
        image = Image.new("1", (petit.shape[1], petit.shape[0]), 0)
        dessin = ImageDraw.Draw(image)
        for morceau in ([forme] if forme.geom_type == "Polygon" else list(getattr(forme, "geoms", []))):
            if morceau.is_empty:
                continue
            dessin.polygon([((x - x0) / reduction, (y - y0) / reduction) for x, y in morceau.exterior.coords], fill=1)
            for trou in morceau.interiors:
                dessin.polygon([((x - x0) / reduction, (y - y0) / reduction) for x, y in trou.coords], fill=0)
        return np.asarray(image)

    def exterieur(barriere: np.ndarray, interdit: np.ndarray | None = None) -> np.ndarray:
        libre = ~barriere if interdit is None else ~barriere & ~interdit
        libre[0, :] = libre[-1, :] = True
        libre[:, 0] = libre[:, -1] = True
        etiquettes, _ = ndimage.label(libre)
        return etiquettes == etiquettes[0, 0]

    ext_a = exterieur(ndimage.binary_dilation(encre, iterations=2))
    fusion = ndimage.binary_closing(encre, iterations=3)
    barriere_b = ndimage.binary_dilation(ndimage.binary_opening(fusion, iterations=2), iterations=1)
    ext_b = exterieur(barriere_b, masque(guide.buffer(-0.3 * px_par_m, join_style=2)))
    masse = ~ext_a & ~(ext_b & ~masque(guide))
    exclus = []
    coeur = guide.buffer(-0.5 * px_par_m)
    for objet in analyse["objects"]:
        exterieur_connu = objet["category"] in ("terrasse", "balcon")
        indetermine = objet["category"] == "indetermine" and objet.get("geometry_type") == "polygon"
        if (exterieur_connu or indetermine) and len(objet["points"]) >= 3:
            forme = Polygon([(x * largeur_px / 1000, y * hauteur_px / 1000) for x, y in objet["points"]]).buffer(0)
            if exterieur_connu or not coeur.contains(forme.centroid):
                exclus.append(forme)
    limite = guide.buffer(FACADE_MARGE_M * px_par_m, join_style=2)
    if exclus:
        limite = limite.difference(unary_union(exclus).buffer(0.02 * px_par_m))
    region = masse & masque(limite)
    region = ndimage.binary_opening(region, iterations=2)
    etiquettes, nombre = ndimage.label(region)
    if nombre == 0:
        return None
    tailles = ndimage.sum(region, etiquettes, range(1, nombre + 1))
    region = ndimage.binary_fill_holes(etiquettes == int(np.argmax(tailles)) + 1)
    # vectorisation par maille de 4 cm (sans dépendance d'imagerie supplémentaire)
    maille = max(1, int(0.04 * px_par_m / reduction))
    hh, ww = region.shape[0] // maille * maille, region.shape[1] // maille * maille
    cellules = region[:hh, :ww].reshape(hh // maille, maille, ww // maille, maille).mean(axis=(1, 3)) > 0.5
    pas = maille * reduction
    boites = []
    for j, ligne in enumerate(cellules):
        colonnes = np.flatnonzero(np.diff(np.concatenate(([0], ligne.astype(np.int8), [0]))))
        for debut, fin in zip(colonnes[::2], colonnes[1::2]):
            boites.append(box(x0 + debut * pas, y0 + j * pas, x0 + fin * pas, y0 + (j + 1) * pas))
    forme = unary_union(boites)
    if forme.geom_type == "MultiPolygon":
        forme = max(forme.geoms, key=lambda morceau: morceau.area)
    return Polygon(forme.exterior)


def _piece_interieure(analyse: dict[str, Any], point: tuple[float, float], largeur_px: float, hauteur_px: float) -> str:
    meilleure, distance = "", math.inf
    for objet in analyse["objects"]:
        if objet["category"] != "piece" or len(objet["points"]) < 3:
            continue
        forme = Polygon([(x * largeur_px / 1000, y * hauteur_px / 1000) for x, y in objet["points"]])
        d = forme.distance(Point(point))
        if d < distance:
            meilleure, distance = objet.get("subtype") or objet["id"], d
    return meilleure


def troncons(guide: dict[str, Any], analyse: dict[str, Any], largeur_px: float, hauteur_px: float, px_par_m: float) -> list[dict[str, Any]]:
    anneau = guide["anneau"]
    polygone = guide["polygone"]
    resultat: list[dict[str, Any]] = []
    abscisse = 0.0
    for cote, (a, b) in enumerate(zip(anneau, anneau[1:] + anneau[:1]), 1):
        longueur_m = math.dist(a, b) / px_par_m
        ux, uy = (b[0] - a[0]) / (longueur_m * px_par_m), (b[1] - a[1]) / (longueur_m * px_par_m)
        nx, ny = -uy, ux
        milieu = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if polygone.contains(Point(milieu[0] + nx * 5, milieu[1] + ny * 5)):
            nx, ny = -nx, -ny  # la normale pointe vers l'extérieur
        parts = max(1, math.ceil(longueur_m / TRONCON_MAX_M))
        for k in range(parts):
            debut = longueur_m * k / parts
            fin = longueur_m * (k + 1) / parts
            centre = (a[0] + ux * (debut + fin) / 2 * px_par_m, a[1] + uy * (debut + fin) / 2 * px_par_m)
            interieur = (centre[0] - nx * 0.6 * px_par_m, centre[1] - ny * 0.6 * px_par_m)
            resultat.append(
                {
                    "id": f"T{len(resultat) + 1:02d}",
                    "cote": cote,
                    "origine_px": [a[0], a[1]],
                    "direction": [ux, uy],
                    "normale_ext": [nx, ny],
                    "local_debut_m": debut,
                    "local_fin_m": fin,
                    "debut_m": round(abscisse + debut, 3),
                    "fin_m": round(abscisse + fin, 3),
                    "piece": _piece_interieure(analyse, interieur, largeur_px, hauteur_px),
                }
            )
        abscisse += longueur_m
    return resultat


def bande_m(troncon: dict[str, Any]) -> tuple[float, float]:
    """(profondeur côté intérieur, hauteur côté extérieur) de la bande, en m.

    Guide sur la face extérieure : le mur est sous le 0. Lecture par local (D43) : la ligne 0 est la face
    intérieure du local, le mur est au-dessus.
    """
    bande = troncon.get("bande_m") or {}
    return bande.get("interieure", BANDE_INTERIEURE_M), bande.get("exterieure", BANDE_EXTERIEURE_M)


def _bande(page: Image.Image, troncon: dict[str, Any], px_par_m: float) -> Image.Image:
    """Bande redressée : abscisse vers la droite, extérieur en haut."""
    (ox, oy), (ux, uy), (nx, ny) = troncon["origine_px"], troncon["direction"], troncon["normale_ext"]
    s0 = (troncon["local_debut_m"] - RECOUVREMENT_M) * px_par_m
    longueur = (troncon["local_fin_m"] - troncon["local_debut_m"] + 2 * RECOUVREMENT_M) * px_par_m
    interieure, exterieure = bande_m(troncon)
    haut = exterieure * px_par_m
    profondeur = (interieure + exterieure) * px_par_m
    k = 1 / AGRANDISSEMENT
    taille = (round(longueur * AGRANDISSEMENT), round(profondeur * AGRANDISSEMENT))
    # pixel (x, y) de la bande -> origine + u (s0 + x k) + n (haut - y k)
    donnees = (ux * k, -nx * k, ox + ux * s0 + nx * haut, uy * k, -ny * k, oy + uy * s0 + ny * haut)
    return page.transform(taille, Image.AFFINE, donnees, resample=Image.BICUBIC, fillcolor=255)


def _graduer(bande: Image.Image, troncon: dict[str, Any], px_par_m: float) -> Image.Image:
    echelle = px_par_m * AGRANDISSEMENT
    police, petite = _police(22), _police(16)
    image = Image.new("RGB", (bande.width + MARGE_GAUCHE + 20, bande.height + MARGE_HAUT + 46), "white")
    image.paste(bande.convert("RGB"), (MARGE_GAUCHE, MARGE_HAUT))
    dessin = ImageDraw.Draw(image)
    dessin.text(
        (8, 6),
        f"{troncon['id']} · côté {troncon['cote']} · {troncon['debut_m']:.2f} → {troncon['fin_m']:.2f} m · pièce : {troncon['piece']}",
        fill="#0b3d91",
        font=police,
    )
    # règle d'abscisse (m, le long de l'enveloppe)
    s_image0 = troncon["debut_m"] - RECOUVREMENT_M
    premier = math.ceil(s_image0 * 10) / 10
    s = premier
    while s <= troncon["fin_m"] + RECOUVREMENT_M + 1e-9:
        x = MARGE_GAUCHE + (s - s_image0) * echelle
        metre = abs(s - round(s)) < 1e-6
        demi = abs(s * 2 - round(s * 2)) < 1e-6
        longueur = 22 if metre else 14 if demi else 7
        dessin.line((x, MARGE_HAUT - longueur, x, MARGE_HAUT), fill="#0b3d91", width=2 if metre else 1)
        if metre:
            dessin.text((x + 3, MARGE_HAUT - 44), f"{s:.0f} m", fill="#0b3d91", font=petite)
        s = round(s + 0.1, 6)
    # limites du tronçon (hors recouvrement)
    for s_lim in (troncon["debut_m"], troncon["fin_m"]):
        x = MARGE_GAUCHE + (s_lim - s_image0) * echelle
        dessin.line((x, MARGE_HAUT - 30, x, MARGE_HAUT + bande.height + 12), fill="#d6336c", width=1)
    # règle de profondeur (cm, + vers l'extérieur, 0 = ligne guide)
    interieure, exterieure = bande_m(troncon)
    for cm in range(-round(interieure * 100), round(exterieure * 100) + 1, 5):
        y = MARGE_HAUT + (exterieure - cm / 100) * echelle
        longueur = 26 if cm % 50 == 0 else 16 if cm % 10 == 0 else 8
        dessin.line((MARGE_GAUCHE - longueur, y, MARGE_GAUCHE, y), fill="#2b8a3e", width=2 if cm == 0 else 1)
        if cm % 10 == 0:
            dessin.text((MARGE_GAUCHE - 100, y - 9), f"{cm:+d} cm", fill="#2b8a3e", font=petite)
    y0 = MARGE_HAUT + exterieure * echelle
    dessin.line((image.width - 18, y0, image.width - 2, y0), fill="#2b8a3e", width=3)
    dessin.text((8, MARGE_HAUT - 2), "EXT ↑", fill="#2b8a3e", font=petite)
    dessin.text((8, image.height - 30), "INT ↓", fill="#2b8a3e", font=petite)
    return image


def preparer(
    pdf: Path,
    analyse: dict[str, Any],
    dossier: Path,
    page: int = 1,
    dpi: int = 300,
    echelle: float = 100,
    complement: Any = None,
) -> dict[str, Any]:
    """Rend la page, trace le guide, découpe et gradue les bandes, puis les regroupe en planches.

    `complement(analyse, largeur, hauteur, px_par_m, batiment)` ajoute des tronçons lus depuis la face intérieure
    des locaux (D46 : côtés sur local non chauffé ou vide), sur des planches et dans des lots à part.
    """
    manifeste_analyse = analyse["manifest"]
    rotation = int(manifeste_analyse["rotation_deg_ccw"])
    page_image = rendre_page(pdf, page, dpi, rotation)
    largeur, hauteur = page_image.size
    px_par_m = dpi / M_PAR_POUCE / echelle
    guide = contour_guide(analyse, largeur, hauteur, px_par_m, page_image)
    liste = troncons(guide, analyse, largeur, hauteur, px_par_m)
    supplement = complement(analyse, largeur, hauteur, px_par_m, guide["polygone"]) if complement else []
    dossier.mkdir(parents=True, exist_ok=True)
    planches: list[dict[str, Any]] = []
    for groupe_troncons, est_complement in ((liste, False), (supplement, True)):
        graduees = [_graduer(_bande(page_image, t, px_par_m), t, px_par_m) for t in groupe_troncons]
        for debut in range(0, len(graduees), BANDES_PAR_PLANCHE):
            groupe = graduees[debut : debut + BANDES_PAR_PLANCHE]
            largeur_planche = max(image.width for image in groupe)
            planche = Image.new("RGB", (largeur_planche, sum(image.height + 24 for image in groupe)), "#e9ecef")
            y = 0
            for image in groupe:
                planche.paste(image, (0, y))
                y += image.height + 24
            chemin = dossier / f"enveloppe-{len(planches) + 1:02d}.png"
            planche.save(chemin, optimize=True)
            planches.append({"chemin": str(chemin.resolve()), "complement": est_complement,
                             "troncons": [t["id"] for t in groupe_troncons[debut : debut + BANDES_PAR_PLANCHE]]})
    plan = _plan_guide(page_image, guide, liste + supplement, dossier / "enveloppe-guide.jpg", px_par_m)
    manifeste = {
        "version": 1,
        "methode": "parcours_enveloppe_raster",
        "uses_pdf_vectors": False,
        "dpi": dpi,
        "echelle": echelle,
        "px_par_m": px_par_m,
        "page_px": [largeur, hauteur],
        "bande_m": {"interieure": BANDE_INTERIEURE_M, "exterieure": BANDE_EXTERIEURE_M, "recouvrement": RECOUVREMENT_M},
        "perimetre_m": round(sum(t["fin_m"] - t["debut_m"] for t in liste), 2),
        "troncons": liste + supplement,
        "batiment_px": [list(p) for p in guide["polygone"].exterior.coords],
        "trous_px": guide["trous"],
        "guide": guide["methode"],
        "planches": planches,
        "plan_guide": str(plan.resolve()),
    }
    (dossier / "enveloppe-manifeste.json").write_text(json.dumps(manifeste, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifeste


def _plan_guide(page: Image.Image, guide: dict[str, Any], liste: list[dict[str, Any]], chemin: Path, px_par_m: float) -> Path:
    xs = [x for x, _ in guide["anneau"]]
    ys = [y for _, y in guide["anneau"]]
    marge = 400
    boite = (max(0, min(xs) - marge), max(0, min(ys) - marge), min(page.width, max(xs) + marge), min(page.height, max(ys) + marge))
    image = page.crop(boite).convert("RGB")
    dessin = ImageDraw.Draw(image)
    anneau = [(x - boite[0], y - boite[1]) for x, y in guide["anneau"]]
    dessin.line(anneau + anneau[:1], fill="#d6336c", width=8)
    police = _police(48)
    for troncon in liste:
        if troncon.get("ligne") == "face_interieure":  # D46 : côté de local, tracé en orange
            a = _point(troncon, troncon["debut_m"], 0, px_par_m)
            b = _point(troncon, troncon["fin_m"], 0, px_par_m)
            dessin.line([(a[0] - boite[0], a[1] - boite[1]), (b[0] - boite[0], b[1] - boite[1])], fill="#e8590c", width=8)
        x, y = _point(troncon, (troncon["debut_m"] + troncon["fin_m"]) / 2, -60, px_par_m)
        dessin.text((x - boite[0] - 30, y - boite[1] - 24), troncon["id"], fill="#0b3d91", font=police)
    dessin.ellipse((anneau[0][0] - 25, anneau[0][1] - 25, anneau[0][0] + 25, anneau[0][1] + 25), fill="#2b8a3e")
    image.thumbnail((2400, 2400))
    image.save(chemin, quality=90)
    return chemin


def consigne(
    manifeste: dict[str, Any],
    planches: list[dict[str, Any]] | None = None,
    catalogue: list[dict[str, Any]] | None = None,
    image_catalogue: str | None = None,
) -> str:
    planches = manifeste["planches"] if planches is None else planches
    troncons_lot = {t for planche in planches for t in planche["troncons"]}
    par_id = {t["id"]: t for t in manifeste["troncons"]}
    par_local = manifeste.get("mode") == "par_local" or (troncons_lot and all(
        par_id.get(t, {}).get("ligne") == "face_interieure" for t in troncons_lot))
    if par_local:
        # lecture par local (D42, D43) : un tronçon = un côté déperditif d'un local, 0 = face intérieure du local
        lignes = [
            "Tu fais le tour des locaux chauffés d'un étage, local par local. Pour chaque local, on ne te montre que "
            "ses côtés qui donnent sur l'extérieur, un local non chauffé, un vide, ou derrière lesquels le plan n'a "
            "rien trouvé.",
            f"Plan guide (côtés numérotés en rose, un tronçon par côté) : {manifeste['plan_guide']}",
            "La ligne guide (0) est la FACE INTÉRIEURE du local : le mur, l'isolant et le doublage sont AU-DESSUS du 0 "
            "(profondeurs positives), la pièce est sous le 0. Le nu intérieur est donc proche de 0 cm.",
            "Chaque planche empile des bandes redressées rendues à 300 dpi (1/100) : EXTÉRIEUR EN HAUT, PIÈCE EN BAS. "
            "Le titre de chaque bande donne le local et le côté.",
            "Règle du haut : abscisse le long du tour du local en mètres (graduée tous les 10 cm). Traits roses : limites "
            "du tronçon ; au-delà, 60 cm de recouvrement pour voir les angles.",
            f"Règle de gauche : profondeur en cm depuis la ligne guide (0), positive vers l'extérieur "
            f"(bande de -{manifeste['bande_m']['interieure'] * 100:.0f} à +{manifeste['bande_m']['exterieure'] * 100:.0f} cm).",
            "Si le côté donne sur un local non chauffé ou une gaine, relève la paroi telle qu'elle est dessinée. S'il n'y "
            "a pas de paroi (ouverture sur une circulation, local voisin chauffé), relève un intervalle « indetermine » "
            "avec un indice qui dit ce que tu vois.",
        ]
    else:
        lignes = [
            "Tu longes l'enveloppe extérieure d'un étage, dans le sens horaire, depuis le point vert du plan guide.",
            f"Plan guide (contour rose = ligne guide, tronçons numérotés, point vert = départ) : {manifeste['plan_guide']}",
            "La ligne guide suit la face extérieure de l'enveloppe (zigzags compris) : le mur est surtout SOUS le 0.",
            "Chaque planche empile des bandes redressées rendues à 300 dpi (1/100) : EXTÉRIEUR EN HAUT, INTÉRIEUR EN BAS.",
            "Règle du haut : abscisse le long de l'enveloppe en mètres (graduée tous les 10 cm). Traits roses : limites "
            "du tronçon ; au-delà, 60 cm de recouvrement pour voir les angles.",
            f"Règle de gauche : profondeur en cm depuis la ligne guide (0), positive vers l'extérieur "
            f"(bande de -{manifeste['bande_m']['interieure'] * 100:.0f} à +{manifeste['bande_m']['exterieure'] * 100:.0f} cm).",
        ]
    for planche in planches:
        lignes.append(f"Planche : {planche['chemin']} (tronçons {', '.join(planche['troncons'])})")
    lignes.append("Bornes des tronçons (m) : " + "; ".join(
        f"{t['id']} {t['debut_m']:.2f}-{t['fin_m']:.2f}" for t in manifeste["troncons"] if t["id"] in troncons_lot))
    lignes += ["", "CATALOGUE DES COMPOSANTS (tu apprends en avançant) :"]
    if catalogue:
        lignes.append("Composants déjà identifiés lors des lots précédents"
                      + (f" ; vignettes : {image_catalogue}" if image_catalogue else "") + " :")
        for fiche in catalogue:
            lignes.append(f"- {fiche['id']} « {fiche['nom']} » ({fiche['genre']}, {fiche['decision']}) : "
                          f"{composition_libelle(fiche['couches'])} ; reconnaissance : {fiche['regle']}")
        lignes.append(
            "Lis d'abord la planche des vignettes. Quand tu revois un composant du catalogue, réutilise son "
            "identifiant et sa composition (mêmes couches, mêmes noms de couches) ; ne crée un nouveau composant "
            "que s'il est réellement différent (en poursuivant la numérotation), et dis pourquoi dans sa règle de "
            "reconnaissance.")
    else:
        lignes.append("Le catalogue est vide : tu le crées.")
    lignes += [
        "Quand un intervalle est un composant du catalogue (déjà connu ou créé dans ce lot) avec la même "
        "composition, laisse son champ couches VIDE : la composition de la fiche s'applique. Ne détaille les "
        "couches que dans la fiche du catalogue.",
        "Chaque intervalle porte l'identifiant de son composant (champ composant) : P1, P2… parois ; M1… "
        "menuiseries ; PO1… poteaux ; L1… liaisons (angles, abouts) ; X1… éléments extérieurs (brise-soleil, "
        "claustra, garde-corps, potelets, escalier extérieur). Décision : integre (fait partie de l'enveloppe "
        "thermique), exclu (hors enveloppe), a_confirmer.",
        "Dans ta réponse, le champ catalogue contient UNIQUEMENT les composants NOUVEAUX de ce lot et ceux dont tu corriges la "
        "fiche ; premiere_vue = l'endroit le plus lisible où tu l'as vu.",
        "Nomme les couches de façon stable : un voile béton est toujours « mur », même mince ou dessiné par un trait "
        "noir épais ; « parement » est réservé à un revêtement rapporté distinct d'un voile.",
        "Si la ligne guide passe sur un élément extérieur (claustra, potelets, rive de terrasse) au lieu de la paroi "
        "chauffée, rattache l'intervalle à cet élément extérieur (X…, exclu) et indique en observation où se trouve "
        "la vraie paroi.",
        "",
        "PAROI EN BIAIS : si la paroi n'est pas parallèle à la ligne guide, donne les nus au DÉBUT "
        "(nu_exterieur_cm, nu_interieur_cm) et à la FIN de l'intervalle (nu_exterieur_fin_cm, nu_interieur_fin_cm). "
        "Sinon, recopie les mêmes valeurs. Les couches gardent leur épaisseur.",
        "",
        "Lis le plan guide, puis les vignettes du catalogue s'il y en a, puis chaque planche avec l'outil Read, dans "
        "l'ordre. Pour chaque tronçon, découpe l'abscisse en intervalles successifs SANS TROU entre ses bornes.",
    ]
    return "\n".join(lignes)


def lots(manifeste: dict[str, Any]) -> list[list[dict[str, Any]]]:
    """Planches regroupées en lots successifs : le catalogue passe d'un lot au suivant."""
    resultat = []
    for complement in (False, True):  # les côtés sur local non chauffé (D46) forment leurs propres lots
        planches = [p for p in manifeste["planches"] if bool(p.get("complement")) == complement]
        resultat += [planches[k : k + LOT_PLANCHES] for k in range(0, len(planches), LOT_PLANCHES)]
    return resultat


def schema() -> dict[str, Any]:
    couche = {
        "type": "object",
        "properties": {
            "nature": {"type": "string", "enum": list(COUCHES)},
            "epaisseur_cm": {"type": "number"},
            "indice": {"type": "string"},
        },
        "required": ["nature", "epaisseur_cm", "indice"],
    }
    element = {
        "type": "object",
        "properties": {
            "troncon": {"type": "string"},
            "debut_m": {"type": "number"},
            "fin_m": {"type": "number"},
            "type": {"type": "string", "enum": list(TYPES)},
            "composant": {"type": "string"},
            "nu_exterieur_cm": {"type": "number"},
            "nu_interieur_cm": {"type": "number"},
            "nu_exterieur_fin_cm": {"type": "number"},
            "nu_interieur_fin_cm": {"type": "number"},
            "couches": {"type": "array", "items": couche},
            "menuiserie_type": {"type": "string"},
            "cadre_cm": {"type": "number"},
            "confiance": {"type": "number", "minimum": 0, "maximum": 1},
            "indice": {"type": "string"},
            "a_verifier": {"type": "boolean"},
        },
        "required": ["troncon", "debut_m", "fin_m", "type", "composant", "nu_exterieur_cm", "nu_interieur_cm",
                     "nu_exterieur_fin_cm", "nu_interieur_fin_cm", "couches", "menuiserie_type", "cadre_cm",
                     "confiance", "indice", "a_verifier"],
    }
    fiche = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "nom": {"type": "string"},
            "genre": {"type": "string", "enum": list(GENRES_CATALOGUE)},
            "decision": {"type": "string", "enum": list(DECISIONS)},
            "couches": {"type": "array", "items": couche},
            "regle": {"type": "string"},
            "premiere_vue": {
                "type": "object",
                "properties": {"troncon": {"type": "string"}, "debut_m": {"type": "number"}, "fin_m": {"type": "number"}},
                "required": ["troncon", "debut_m", "fin_m"],
            },
        },
        "required": ["id", "nom", "genre", "decision", "couches", "regle", "premiere_vue"],
    }
    return {
        "type": "object",
        "properties": {
            "catalogue": {"type": "array", "items": fiche},
            "elements": {"type": "array", "items": element},
            "observations": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["catalogue", "elements", "observations"],
    }


def _point(troncon: dict[str, Any], abscisse_m: float, profondeur_cm: float, px_par_m: float) -> tuple[float, float]:
    (ox, oy), (ux, uy), (nx, ny) = troncon["origine_px"], troncon["direction"], troncon["normale_ext"]
    local = troncon["local_debut_m"] + (abscisse_m - troncon["debut_m"])
    t = profondeur_cm / 100
    return (ox + (ux * local + nx * t) * px_par_m, oy + (uy * local + ny * t) * px_par_m)


def nus(element: dict[str, Any]) -> tuple[float, float, float, float]:
    """Nus extérieur et intérieur au début puis à la fin de l'intervalle (paroi en biais)."""
    ext, inte = element["nu_exterieur_cm"], element["nu_interieur_cm"]
    return ext, inte, element.get("nu_exterieur_fin_cm", ext), element.get("nu_interieur_fin_cm", inte)


def couches_positionnees(element: dict[str, Any]) -> list[tuple[dict[str, Any], float, float, float, float]]:
    """Chaque couche avec ses profondeurs (haut, bas) au début puis à la fin de l'intervalle.

    Épaisseur constante : couches empilées depuis le nu extérieur (paroi droite ou en biais). Épaisseur variable
    (massif triangulaire) : couches calées sur le nu intérieur, la première couche absorbe la variation.
    """
    ext, inte, ext_fin, inte_fin = nus(element)
    toutes = element.get("couches") or []
    # couches présumées (doublage non dessiné, D17) : posées côté pièce, contre le nu intérieur dessiné
    couches = [c for c in toutes if not c.get("presume")]
    presumees = [c for c in toutes if c.get("presume")]
    if not couches:
        return []
    resultat = _couches_dessinees(couches, ext, inte, ext_fin, inte_fin)
    haut, haut_fin = inte, inte_fin
    for couche in presumees:
        bas, bas_fin = haut - couche["epaisseur_cm"], haut_fin - couche["epaisseur_cm"]
        resultat.append((couche, haut, bas, haut_fin, bas_fin))
        haut, haut_fin = bas, bas_fin
    return resultat


def _couches_dessinees(couches: list[dict[str, Any]], ext: float, inte: float, ext_fin: float,
                       inte_fin: float) -> list[tuple[dict[str, Any], float, float, float, float]]:
    variable = abs((ext - inte) - (ext_fin - inte_fin)) > 3
    resultat = []
    if not variable:
        decalage = ext_fin - ext
        haut = ext
        for couche in couches:
            bas = haut - couche["epaisseur_cm"]
            resultat.append((couche, haut, bas, haut + decalage, bas + decalage))
            haut = bas
        return resultat
    # couches fixes (toutes sauf la première) ; si l'épaisseur disponible ne suffit pas, elles sont comprimées
    fixes = sum(couche["epaisseur_cm"] for couche in couches[1:])
    facteur = min(1.0, (ext - inte) / fixes) if fixes > 0 else 1.0
    facteur_fin = min(1.0, (ext_fin - inte_fin) / fixes) if fixes > 0 else 1.0
    bas, bas_fin = inte, inte_fin
    for rang in range(len(couches) - 1, -1, -1):
        couche = couches[rang]
        if rang == 0:
            haut, haut_fin = ext, ext_fin
        else:
            haut = bas + couche["epaisseur_cm"] * max(facteur, 0.0)
            haut_fin = bas_fin + couche["epaisseur_cm"] * max(facteur_fin, 0.0)
        resultat.append((couche, haut, bas, haut_fin, bas_fin))
        bas, bas_fin = haut, haut_fin
    return list(reversed(resultat))


def composition_libelle(couches: list[dict[str, Any]]) -> str:
    return " + ".join(f"{c['nature']} {c['epaisseur_cm']:g}{' présumé' if c.get('presume') else ''}"
                      for c in couches) or "non lue"


# Doublage présumé (D17) : plaque de plâtre BA13 rarement dessinée au 1/100, présente dans la très grande
# majorité des parois ; à confirmer par composant dans le catalogue.
DOUBLAGE_PRESUME = {"nature": "doublage", "epaisseur_cm": 1.3, "indice": "BA13 présumé (non dessiné au 1/100)",
                    "presume": True}


def avec_doublage_presume(couches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ajoute le BA13 présumé à une paroi dont la face côté pièce est un voile nu."""
    if not couches or couches[-1]["nature"] != "mur" or any(c["nature"] == "doublage" for c in couches):
        return couches
    return [*couches, DOUBLAGE_PRESUME]


def role_couche(couches: list[dict[str, Any]], rang: int) -> str:
    """Nom de la couche dans le rendu : voile extérieur / intérieur (double peau), isolant, doublage (D16)."""
    couche = couches[rang]
    nature = couche["nature"]
    if nature == "doublage":
        return "doublage BA13 présumé" if couche.get("presume") else "doublage"
    if nature != "mur":
        return nature.replace("_", " ")
    isolants = [i for i, c in enumerate(couches) if c["nature"] == "isolant"]
    if not isolants:
        return "voile"
    if rang < isolants[0]:
        return "voile extérieur"
    if rang > isolants[-1]:
        return "voile intérieur"
    return "voile"


def _mediane_ponderee(valeurs: list[tuple[float, float]]) -> float:
    valeurs = sorted(valeurs)
    total = sum(poids for _, poids in valeurs)
    cumul = 0.0
    for valeur, poids in valeurs:
        cumul += poids
        if cumul >= total / 2:
            return valeur
    return valeurs[-1][0]


# Épaisseurs commerciales usuelles par nature de couche, en cm (voiles béton, isolants en panneaux, doublages
# collés isolant + plaque, parements). L'épaisseur lue sur plan est ramenée à la plus proche (décision
# utilisateur 2026-09-21) ; l'épaisseur lue reste affichée à côté.
EPAISSEURS_COMMERCIALES = {
    "mur": (10, 12, 15, 16, 18, 20, 22, 25, 30, 35, 40),
    "isolant": (4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30),
    "doublage": (1.3, 2.6, 5.3, 6.3, 7.3, 8.3, 9.3, 10.3, 11.3, 12.3, 13.3, 14.3, 16.3),
    "parement": (1, 2, 3, 4, 5),
    "bardage": (2, 3, 4, 5),
}


def epaisseur_commerciale(nature: str, epaisseur_cm: float) -> float:
    gamme = EPAISSEURS_COMMERCIALES.get(nature)
    if not gamme:
        return epaisseur_cm
    return min(gamme, key=lambda valeur: (abs(valeur - epaisseur_cm), valeur))


def familles_de_parois(parois: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Regroupe les compositions lues par suite de couches : une famille = un composant candidat.

    Les épaisseurs lues varient de quelques centimètres d'un tronçon à l'autre ; la famille retient la médiane
    pondérée par le linéaire et la fourchette observée, à valider par le thermicien (coupe, CCTP).
    """
    groupes: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for fiche in parois.values():
        cle = tuple(couche["nature"] for couche in fiche["composition"])
        groupes.setdefault(cle, []).append(fiche)
    familles = []
    for natures, fiches in groupes.items():
        lineaire = sum(f["lineaire_m"] for f in fiches)
        couches = []
        for rang, nature in enumerate(natures):
            mesures = [(f["composition"][rang]["epaisseur_cm"], f["lineaire_m"]) for f in fiches]
            mediane = _mediane_ponderee(mesures)
            couches.append({
                "nature": nature,
                "epaisseur_cm": mediane,
                "epaisseur_retenue_cm": epaisseur_commerciale(nature, mediane),
                "min_cm": min(m for m, _ in mesures),
                "max_cm": max(m for m, _ in mesures),
            })
        familles.append({
            "famille": " + ".join(c["nature"] for c in couches) or "non lue",
            "composition_type": " + ".join(f"{c['nature']} {c['epaisseur_cm']:g}" for c in couches),
            "composition_retenue": " + ".join(f"{c['nature']} {c['epaisseur_retenue_cm']:g}" for c in couches),
            "couches": couches,
            "lineaire_m": round(lineaire, 2),
            "variantes": len(fiches),
            "pieces": sorted({p for f in fiches for p in f["pieces"]}),
        })
    return sorted(familles, key=lambda famille: -famille["lineaire_m"])


def fusionner_catalogue(ancien: list[dict[str, Any]], nouveau: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ajoute les fiches nouvelles et remplace celles que le lot a corrigées (même identifiant)."""
    par_id = {fiche["id"]: fiche for fiche in ancien}
    ordre = [fiche["id"] for fiche in ancien]
    for fiche in nouveau:
        if fiche["id"] not in par_id:
            ordre.append(fiche["id"])
        par_id[fiche["id"]] = fiche
    return [par_id[identifiant] for identifiant in ordre]


def synthese_catalogue(brut: dict[str, Any]) -> list[dict[str, Any]]:
    """Linéaire et occurrences par composant du catalogue, composition ramenée aux épaisseurs commerciales."""
    resultat = []
    for fiche in brut.get("catalogue", []):
        occurrences = [e for e in brut["elements"] if e.get("composant") == fiche["id"]]
        resultat.append({
            **fiche,
            "composition": composition_libelle(fiche["couches"]),
            "composition_retenue": " + ".join(
                f"{c['nature']} {epaisseur_commerciale(c['nature'], c['epaisseur_cm']):g}{' présumé' if c.get('presume') else ''}"
                for c in fiche["couches"]),
            "occurrences": len(occurrences),
            "lineaire_m": round(sum(e["fin_m"] - e["debut_m"] for e in occurrences), 2),
            "troncons": sorted({e["troncon"] for e in occurrences}),
        })
    return resultat


def resoudre(brut: dict[str, Any]) -> dict[str, Any]:
    """Un intervalle qui renvoie à un composant du catalogue sans détailler ses couches prend celles de la fiche.

    Les parois de l'enveloppe (non exclues) dont la face côté pièce est un voile nu reçoivent le doublage présumé.
    """
    catalogue = []
    for fiche in brut.get("catalogue", []):
        if fiche.get("genre") == "paroi" and fiche.get("decision") != "exclu":
            fiche = {**fiche, "couches": avec_doublage_presume(fiche.get("couches") or [])}
        catalogue.append(fiche)
    par_id = {fiche["id"]: fiche for fiche in catalogue}
    elements = []
    for element in brut["elements"]:
        fiche = par_id.get(element.get("composant") or "")
        if fiche and not element.get("couches") and fiche.get("couches"):
            element = {**element, "couches": fiche["couches"]}
        elif element.get("type") == "paroi" and (fiche is None or fiche.get("decision") != "exclu"):
            element = {**element, "couches": avec_doublage_presume(element.get("couches") or [])}
        elements.append(element)
    resultat = {**brut, "elements": elements}
    if "catalogue" in brut:
        resultat["catalogue"] = catalogue
    return resultat


def reprojeter(brut: dict[str, Any], manifeste: dict[str, Any], analyse: dict[str, Any]) -> dict[str, Any]:
    """Intervalles lus -> objets éditables (repère feuille 0..1000) + synthèse pour la bibliothèque."""
    brut = resoudre(brut)
    px_par_m = manifeste["px_par_m"]
    largeur, hauteur = manifeste["page_px"]
    par_id = {t["id"]: t for t in manifeste["troncons"]}
    ma = analyse["manifest"]

    def feuille(point: tuple[float, float]) -> list[float]:
        return [round(point[0] * 1000 / largeur, 3), round(point[1] * 1000 / hauteur, 3)]

    def analyse_norm(point: tuple[float, float]) -> list[float]:
        # repère de l'image recadrée de la première passe (pour la projection PNG)
        x150 = point[0] * ma["page_width_px"] / largeur
        y150 = point[1] * ma["page_height_px"] / hauteur
        return [round((x150 - ma["crop_box_px"][0]) * 1000 / ma["width_px"], 3),
                round((y150 - ma["crop_box_px"][1]) * 1000 / ma["height_px"], 3)]

    objets: list[dict[str, Any]] = []
    compteurs: dict[str, int] = {}
    parois: dict[str, dict[str, Any]] = {}
    menuiseries: dict[str, dict[str, Any]] = {}
    liaisons: list[dict[str, Any]] = []

    def ajouter(categorie: str, geometrie: str, points: list[tuple[float, float]], element: dict[str, Any], sous_type: str) -> None:
        compteurs[categorie] = compteurs.get(categorie, 0) + 1
        objets.append(
            {
                "id": f"env-{categorie}-{compteurs[categorie]:03d}",
                "category": categorie,
                "subtype": sous_type,
                "geometry_type": geometrie,
                "points": [feuille(p) for p in points],
                "points_analysis_norm": [analyse_norm(p) for p in points],
                "confidence": element["confiance"],
                "evidence": f"{element['troncon']} {element['debut_m']:.2f}-{element['fin_m']:.2f} m : {element['indice']}",
                "review_required": bool(element["a_verifier"]) or element["confiance"] < 0.5,
                "source_parcours": {k: element.get(k) for k in ("troncon", "debut_m", "fin_m", "type", "composant", "piece")},
            }
        )

    for element in brut["elements"]:
        troncon = par_id.get(element["troncon"])
        if troncon is None or element["fin_m"] <= element["debut_m"]:
            continue
        a, b = element["debut_m"], element["fin_m"]
        ext, inte, ext_fin, inte_fin = nus(element)
        decalage = ext_fin - ext
        longueur = b - a
        bande = [_point(troncon, a, ext, px_par_m), _point(troncon, b, ext_fin, px_par_m),
                 _point(troncon, b, inte_fin, px_par_m), _point(troncon, a, inte, px_par_m)]
        genre = element["type"]
        if genre == "paroi":
            libelle = composition_libelle(element["couches"])
            composant = element.get("composant") or ""
            positions = couches_positionnees(element)
            if not positions:
                ajouter("mur_exterieur", "polygon", bande, element, f"{composant} {libelle}".strip())
            # une couche = un objet (D16) : voile extérieur, isolant, voile intérieur, doublage
            couches = [p[0] for p in positions]
            for rang, (couche, haut, bas, haut_fin, bas_fin) in enumerate(positions):
                categorie = CATEGORIE_COUCHE.get(couche["nature"], "mur_exterieur")
                ajouter(categorie, "polygon", [
                    _point(troncon, a, haut, px_par_m), _point(troncon, b, haut_fin, px_par_m),
                    _point(troncon, b, bas_fin, px_par_m), _point(troncon, a, bas, px_par_m)],
                    element, f"{composant} · {role_couche(couches, rang)} {couche['epaisseur_cm']:g} cm".strip(" ·"))
                if couche.get("presume"):
                    objets[-1]["review_required"] = True
            fiche = parois.setdefault(libelle, {"composition": element["couches"], "epaisseur_cm": round(ext - inte, 1),
                                                "lineaire_m": 0.0, "troncons": set(), "pieces": set()})
            fiche["lineaire_m"] += longueur
            fiche["troncons"].add(element["troncon"])
            fiche["pieces"].add(element.get("piece") or troncon["piece"])
        elif genre == "menuiserie":
            cadre = element["cadre_cm"]
            ajouter("menuiserie_exterieure", "polyline",
                    [_point(troncon, a, cadre, px_par_m), _point(troncon, b, cadre + decalage, px_par_m)], element,
                    f"{element['menuiserie_type']} {longueur * 100:.0f} cm, cadre à {cadre:+g} cm")
            cle = f"{element['menuiserie_type']} · cadre à {cadre - inte:.0f} cm du nu intérieur"
            fiche = menuiseries.setdefault(cle, {"type": element["menuiserie_type"], "largeurs_cm": [], "pieces": set()})
            fiche["largeurs_cm"].append(round(longueur * 100))
            fiche["pieces"].add(element.get("piece") or troncon["piece"])
        elif genre == "poteau":
            ajouter("poteau", "polygon", bande, element, f"poteau {longueur * 100:.0f} × {ext - inte:.0f} cm")
        elif genre == "garde_corps":
            ajouter("garde_corps", "polyline", [_point(troncon, a, ext, px_par_m), _point(troncon, b, ext, px_par_m)], element, "garde-corps")
        elif genre == "indetermine":
            ajouter("indetermine", "polygon", bande, element, element["indice"][:60])
        else:
            liaisons.append({"type": genre, "troncon": element["troncon"], "abscisse_m": round((a + b) / 2, 2),
                             "piece": element.get("piece") or troncon["piece"], "indice": element["indice"], "confiance": element["confiance"]})
    bibliotheque = {
        "composants": synthese_catalogue(brut),
        "familles": familles_de_parois(parois),
        "parois": [
            {"composition": cle, "couches": v["composition"], "epaisseur_cm": v["epaisseur_cm"],
             "lineaire_m": round(v["lineaire_m"], 2), "troncons": sorted(v["troncons"]), "pieces": sorted(v["pieces"])}
            for cle, v in sorted(parois.items(), key=lambda item: -item[1]["lineaire_m"])
        ],
        "menuiseries": [
            {"famille": cle, "type": v["type"], "nombre": len(v["largeurs_cm"]), "largeurs_cm": sorted(v["largeurs_cm"]),
             "pieces": sorted(v["pieces"])}
            for cle, v in sorted(menuiseries.items(), key=lambda item: -len(item[1]["largeurs_cm"]))
        ],
        "liaisons": liaisons,
    }
    return {"objets": objets, "bibliotheque": bibliotheque, "observations": brut.get("observations", [])}


CATEGORIES_REMPLACEES = {"mur_exterieur", "isolation", "doublage", "menuiserie_exterieure"}
# nature de couche -> catégorie d'objet éditable
CATEGORIE_COUCHE = {"mur": "mur_exterieur", "isolant": "isolation", "doublage": "doublage"}


def fusionner(analyse: dict[str, Any], enveloppe: dict[str, Any], manifeste: dict[str, Any]) -> dict[str, Any]:
    """Résultat importable : passe globale sans ses objets d'enveloppe, plus les objets du parcours."""
    largeur, hauteur = manifeste["page_px"]
    bande = manifeste["bande_m"]
    px_par_m = manifeste["px_par_m"]
    anneau = []
    for troncon in manifeste["troncons"]:
        anneau.append(_point(troncon, troncon["debut_m"], 0, px_par_m))
    zone = Polygon(anneau).exterior.buffer(max(bande["interieure"], bande["exterieure"]) * px_par_m)

    def dans_bande(objet: dict[str, Any]) -> bool:
        points = [(x * largeur / 1000, y * hauteur / 1000) for x, y in objet["points"]]
        return all(zone.contains(Point(p)) for p in points)

    gardes = [o for o in analyse["objects"]
              if o["category"] not in CATEGORIES_REMPLACEES and not (o["category"] == "poteau" and dans_bande(o))]
    return {**analyse, "objects": gardes + enveloppe["objets"], "enveloppe": {
        "perimetre_m": manifeste["perimetre_m"], "bibliotheque": enveloppe["bibliotheque"],
        "observations": enveloppe["observations"]}}


COULEURS_COUCHES = {
    "mur": (90, 104, 120),
    "isolant": (245, 184, 0),
    "doublage": (155, 89, 182),
    "lame_air": (116, 192, 252),
    "parement": (141, 110, 99),
    "bardage": (141, 110, 99),
    "vitrage": (0, 166, 214),
    "cadre": (0, 120, 160),
    "autre": (160, 160, 160),
}
ABREVIATIONS = {"mur": "M", "isolant": "I", "doublage": "D", "lame_air": "A", "parement": "P", "bardage": "B",
                "vitrage": "V", "cadre": "C", "autre": "?"}
# rôles des couches (D16) : deux voiles d'une double peau de teintes distinctes, doublage violet
COULEURS_ROLES = {
    "voile extérieur": (52, 58, 64),
    "voile intérieur": (134, 142, 150),
    "voile": (90, 104, 120),
    "doublage": (156, 54, 181),
    "doublage BA13 présumé": (156, 54, 181),
}
ABREVIATIONS_ROLES = {"voile extérieur": "Ve", "voile intérieur": "Vi", "voile": "Vo", "isolant": "I",
                      "doublage": "D", "doublage BA13 présumé": "D"}
LIBELLES_LIAISONS = {"angle_sortant": "angle ext", "angle_rentrant": "angle int", "about_refend": "about refend",
                     "about_plancher": "about plancher"}


def _legende(largeur: int) -> Image.Image:
    image = Image.new("RGB", (largeur, 64), "white")
    dessin = ImageDraw.Draw(image)
    police = _police(18)
    x = 10
    for libelle, couleur, contour in (("voile ext. (Ve)", COULEURS_ROLES["voile extérieur"], False),
                                      ("isolant (I)", COULEURS_COUCHES["isolant"], False),
                                      ("voile int. (Vi)", COULEURS_ROLES["voile intérieur"], False),
                                      ("BA13 présumé (D*)", COULEURS_ROLES["doublage"], True)):
        if contour:
            dessin.rectangle((x, 20, x + 26, 42), outline=couleur, width=3)
        else:
            dessin.rectangle((x, 20, x + 26, 42), fill=couleur)
        dessin.text((x + 32, 20), libelle, fill="#172033", font=police)
        x += 200 if contour else 175
    dessin.line((x, 31, x + 40, 31), fill=(0, 166, 214), width=8)
    dessin.text((x + 48, 20), "menuiserie", fill="#172033", font=police)
    x += 170
    dessin.rectangle((x, 18, x + 26, 44), outline=(20, 20, 20), width=4)
    dessin.text((x + 32, 20), "poteau", fill="#172033", font=police)
    x += 120
    dessin.line((x + 10, 12, x + 10, 50), fill=(214, 51, 108), width=4)
    dessin.text((x + 20, 20), "angle / about", fill="#172033", font=police)
    x += 170
    dessin.rectangle((x, 20, x + 26, 42), fill=(231, 41, 138))
    dessin.text((x + 32, 20), "à déterminer", fill="#172033", font=police)
    return image


def annoter(page_image: Image.Image, manifeste: dict[str, Any], brut: dict[str, Any], dossier: Path) -> list[Path]:
    """Planches de relevé : les intervalles lus par l'agent dessinés sur les bandes redressées."""
    images = [image for _troncon, image in bandes_annotees(page_image, manifeste, brut)]
    chemins: list[Path] = []
    for debut in range(0, len(images), BANDES_PAR_PLANCHE):
        groupe = images[debut : debut + BANDES_PAR_PLANCHE]
        largeur = max(max(image.width for image in groupe), 1400)
        legende = _legende(largeur)
        planche = Image.new("RGB", (largeur, legende.height + sum(image.height + 24 for image in groupe)), "#e9ecef")
        planche.paste(legende, (0, 0))
        y = legende.height
        for image in groupe:
            planche.paste(image, (0, y))
            y += image.height + 24
        chemin = dossier / f"releve-{len(chemins) + 1:02d}.png"
        planche.save(chemin, optimize=True)
        chemins.append(chemin)
    return chemins


def bandes_annotees(page_image: Image.Image, manifeste: dict[str, Any], brut: dict[str, Any]) -> list[tuple[dict[str, Any], Image.Image]]:
    """Chaque bande redressée et graduée, avec les intervalles lus par l'agent dessinés dessus."""
    px_par_m = manifeste["px_par_m"]
    echelle = px_par_m * AGRANDISSEMENT
    par_troncon: dict[str, list[dict[str, Any]]] = {}
    for element in resoudre(brut)["elements"]:
        par_troncon.setdefault(element["troncon"], []).append(element)
    petite = _police(15)
    images: list[Image.Image] = []
    for troncon in manifeste["troncons"]:
        image = _graduer(_bande(page_image, troncon, px_par_m), troncon, px_par_m).convert("RGBA")
        calque = Image.new("RGBA", image.size, (0, 0, 0, 0))
        dessin = ImageDraw.Draw(calque)
        s0 = troncon["debut_m"] - RECOUVREMENT_M
        interieure, exterieure = bande_m(troncon)

        def x_de(s: float) -> float:
            return MARGE_GAUCHE + (s - s0) * echelle

        def y_de(cm: float, exterieure: float = exterieure) -> float:
            return MARGE_HAUT + (exterieure - cm / 100) * echelle

        bas = MARGE_HAUT + (exterieure + interieure) * echelle
        elements = sorted(par_troncon.get(troncon["id"], []), key=lambda e: e["debut_m"])
        fin_etiquette = [0.0, 0.0]
        if not elements:
            dessin.rectangle((MARGE_GAUCHE, MARGE_HAUT, image.width - 20, bas), outline=(231, 41, 138, 255), width=4)
            dessin.text((MARGE_GAUCHE + 10, MARGE_HAUT + 10), "NON LU", fill=(231, 41, 138, 255), font=_police(28))
        for element in elements:
            xa, xb = x_de(element["debut_m"]), x_de(element["fin_m"])
            n_ext, n_int, n_ext_fin, n_int_fin = nus(element)
            decalage = n_ext_fin - n_ext
            ext, inte = y_de(n_ext), y_de(n_int)
            genre = element["type"]

            def quadrilatere(haut_cm: float, bas_cm: float, haut_fin_cm: float, bas_fin_cm: float) -> list[tuple[float, float]]:
                return [(xa, y_de(haut_cm)), (xb, y_de(haut_fin_cm)), (xb, y_de(bas_fin_cm)), (xa, y_de(bas_cm))]

            if genre == "paroi":
                positions = couches_positionnees(element)
                natures = [p[0] for p in positions]
                for rang, (couche, c_haut, c_bas, c_haut_fin, c_bas_fin) in enumerate(positions):
                    role = role_couche(natures, rang)
                    rouge, vert, bleu = COULEURS_ROLES.get(role) or COULEURS_COUCHES.get(couche["nature"], COULEURS_COUCHES["autre"])
                    forme = quadrilatere(c_haut, c_bas, c_haut_fin, c_bas_fin)
                    if couche.get("presume"):
                        # présumé : contour seul, épais, sans remplissage plein
                        dessin.polygon(forme, fill=(rouge, vert, bleu, 60), outline=(rouge, vert, bleu, 255), width=3)
                    else:
                        dessin.polygon(forme, fill=(rouge, vert, bleu, 120), outline=(rouge, vert, bleu, 255), width=2)
            elif genre == "menuiserie":
                y = y_de(element["cadre_cm"])
                dessin.rectangle((xa, min(ext, inte), xb, max(ext, inte)), outline=(0, 166, 214, 255), width=2)
                dessin.rectangle((xa, y - 6, xb, y + 6), fill=(0, 166, 214, 200))
            elif genre == "poteau":
                dessin.rectangle((xa, min(ext, inte), xb, max(ext, inte)), outline=(20, 20, 20, 255), width=4)
            elif genre == "indetermine":
                dessin.polygon(quadrilatere(n_ext, n_int, n_ext_fin, n_int_fin), fill=(231, 41, 138, 70),
                               outline=(231, 41, 138, 255), width=3)
            elif genre == "garde_corps":
                dessin.line((xa, ext, xb, ext), fill=(99, 99, 99, 255), width=6)
            else:
                xm = (xa + xb) / 2
                dessin.line((xm, MARGE_HAUT, xm, bas), fill=(214, 51, 108, 255), width=4)
            # étiquette de l'intervalle, sous la bande
            if genre == "paroi":
                couches = element["couches"]
                texte = "|".join(f"{ABREVIATIONS_ROLES.get(role_couche(couches, rang)) or ABREVIATIONS.get(c['nature'], '?')}"
                                 f"{c['epaisseur_cm']:g}{'*' if c.get('presume') else ''}" for rang, c in enumerate(couches))
            elif genre == "menuiserie":
                texte = f"{element['menuiserie_type']} {round((element['fin_m'] - element['debut_m']) * 100)}"
            else:
                texte = LIBELLES_LIAISONS.get(genre, genre)
            if element.get("composant"):
                texte = f"{element['composant']} {texte}"
            if element.get("a_verifier"):
                texte += " ?"
            # étiquettes étagées sur deux lignes quand les intervalles sont courts
            largeur_texte = dessin.textlength(texte, font=petite)
            rang = 0 if xa + 3 >= fin_etiquette[0] else 1
            if rang == 1 and xa + 3 < fin_etiquette[1]:
                rang = 0
            y_texte = bas + 3 + rang * 18
            dessin.line((xa, bas + 2, xa, y_texte + 12), fill=(23, 32, 51, 255), width=1)
            dessin.text((xa + 3, y_texte), texte, fill=(23, 32, 51, 255), font=petite)
            fin_etiquette[rang] = xa + 3 + largeur_texte + 6
        images.append((troncon, Image.alpha_composite(image, calque).convert("RGB")))
    return images


def planche_catalogue(page_image: Image.Image, manifeste: dict[str, Any], catalogue: list[dict[str, Any]], chemin: Path) -> Path:
    """Vignettes des composants appris : l'image où chacun a été vu, son identifiant, sa décision, sa règle."""
    px_par_m = manifeste["px_par_m"]
    echelle = px_par_m * AGRANDISSEMENT
    par_id = {t["id"]: t for t in manifeste["troncons"]}
    police, petite = _police(22), _police(16)
    cartes: list[Image.Image] = []
    for fiche in catalogue:
        vue = fiche.get("premiere_vue") or {}
        troncon = par_id.get(vue.get("troncon"))
        carte = Image.new("RGB", (760, 420), "white")
        dessin = ImageDraw.Draw(carte)
        couleur = {"integre": "#2b8a3e", "exclu": "#868e96", "a_confirmer": "#e8590c"}.get(fiche["decision"], "#172033")
        dessin.rectangle((0, 0, 759, 419), outline=couleur, width=4)
        dessin.text((12, 8), f"{fiche['id']} · {fiche['nom']}"[:60], fill="#0b3d91", font=police)
        dessin.text((12, 38), f"{fiche['genre']} · {fiche['decision'].upper()} · {composition_libelle(fiche['couches'])}"[:90],
                    fill=couleur, font=petite)
        if troncon is not None:
            bande = _bande(page_image, troncon, px_par_m).convert("RGB")
            s0 = troncon["debut_m"] - RECOUVREMENT_M
            milieu = (vue["debut_m"] + vue["fin_m"]) / 2
            x_milieu = (milieu - s0) * echelle
            demi = min(max((vue["fin_m"] - vue["debut_m"]) / 2 + 0.3, 0.6), 1.2) * echelle
            extrait = bande.crop((max(0, round(x_milieu - demi)), 0, min(bande.width, round(x_milieu + demi)), bande.height))
            extrait.thumbnail((736, 300))
            carte.paste(extrait, (12, 66))
        regle = fiche.get("regle", "")
        for rang, debut_ligne in enumerate(range(0, min(len(regle), 190), 95)):
            dessin.text((12, 372 + rang * 20), regle[debut_ligne : debut_ligne + 95], fill="#172033", font=petite)
        cartes.append(carte)
    colonnes = 2
    lignes = max(1, math.ceil(len(cartes) / colonnes))
    planche = Image.new("RGB", (colonnes * 780 + 20, lignes * 440 + 20), "#e9ecef")
    for rang, carte in enumerate(cartes):
        planche.paste(carte, (20 + (rang % colonnes) * 780, 20 + (rang // colonnes) * 440))
    planche.save(chemin, optimize=True)
    return chemin
