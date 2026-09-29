"""Lecture des coupes par l'agent `thermicien-coupe` : images quadrillées, consignes, schémas, conversions.

S5 (`docs/thermique/coupes-elevations-S5-decisions.md`, D181, D185). L'agent lit des **images** ; pour qu'il
rende des positions exploitables sans conversion de pixels, chaque image est **quadrillée en points PDF
de la page** (origine en bas à gauche, y vers le haut), graduations écrites sur la grille. C'est ainsi que la
vérité terrain a été relevée à la main (`verite-terrain-coupes.md`).

Deux travaux :
- **traits** (un plan) : repérage des traits de coupe sur une vue d'ensemble, puis précision de chaque
  extrémité sur un zoom ;
- **coupes** (une planche) : repérage des vues sur une vue d'ensemble, puis lecture de chaque coupe en tuiles.

L'agent donne des coordonnées de page ; `lecture_de_vue` les remet dans le repère de la vue (droite, haut)
qu'attend `thermique_coupes.py`.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

SENS = {"haut": (0.0, 1.0), "bas": (0.0, -1.0), "gauche": (-1.0, 0.0), "droite": (1.0, 0.0)}
PAS_ENSEMBLE_PT = 100
PAS_ZOOM_PT = 5
PAS_TUILE_PT = 20
TAILLE_TUILE_PT = 400
RECOUVREMENT_TUILE_PT = 40
DEMI_ZOOM_PT = 60


# --- Images quadrillées -----------------------------------------------------------------------------------


def rendre_quadrille(pdf: Path, page_index: int, cadre: list[float], pas: float, largeur_px: int, sortie: Path) -> Path:
    """Rend `cadre` = [x0, y0, x1, y1] (points PDF) de la page, quadrillé tous les `pas` points, graduations
    écrites. Même repère que le reste de l'application : celui de pdfium, origine en bas à gauche."""
    import pypdfium2 as pdfium
    from PIL import ImageDraw, ImageFont

    document = pdfium.PdfDocument(str(pdf))
    try:
        page = document[page_index]
        gauche, bas, droite, haut = page.get_mediabox()
        largeur_page, hauteur_page = droite - gauche, haut - bas
        x0, x1 = sorted((float(cadre[0]), float(cadre[2])))
        y0, y1 = sorted((float(cadre[1]), float(cadre[3])))
        x0, y0 = max(x0, 0.0), max(y0, 0.0)
        x1, y1 = min(x1, largeur_page), min(y1, hauteur_page)
        echelle = largeur_px / max(x1 - x0, 1.0)
        image = page.render(scale=echelle, crop=(x0, y0, largeur_page - x1, hauteur_page - y1)).to_pil().convert("RGB")
    finally:
        document.close()
    dessin = ImageDraw.Draw(image)
    try:
        police = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        police = ImageFont.load_default()

    def ecran(x: float, y: float) -> tuple[float, float]:
        return (x - x0) * echelle, (y1 - y) * echelle

    gx = math.ceil(x0 / pas) * pas
    while gx <= x1:
        dessin.line([ecran(gx, y0), ecran(gx, y1)], fill=(0, 160, 255), width=1)
        dessin.text((ecran(gx, y0)[0] + 2, 2), f"x{gx:g}", fill=(0, 90, 200), font=police)
        gx += pas
    gy = math.ceil(y0 / pas) * pas
    while gy <= y1:
        dessin.line([ecran(x0, gy), ecran(x1, gy)], fill=(255, 120, 0), width=1)
        dessin.text((2, ecran(x0, gy)[1] + 2), f"y{gy:g}", fill=(200, 80, 0), font=police)
        gy += pas
    sortie.parent.mkdir(parents=True, exist_ok=True)
    image.save(sortie)
    return sortie


def tuiles(cadre: list[float], taille: float = TAILLE_TUILE_PT, recouvrement: float = RECOUVREMENT_TUILE_PT) -> list[list[float]]:
    """Découpe un cadre en tuiles carrées qui se recouvrent, pour lire une coupe à la bonne finesse."""
    x0, x1 = sorted((float(cadre[0]), float(cadre[2])))
    y0, y1 = sorted((float(cadre[1]), float(cadre[3])))
    pas = taille - recouvrement

    def bornes(debut: float, fin: float) -> list[tuple[float, float]]:
        if fin - debut <= taille:
            return [(debut, fin)]
        nombre = math.ceil((fin - debut - recouvrement) / pas)
        return [(debut + i * pas, min(debut + i * pas + taille, fin)) for i in range(nombre)]

    # De haut en bas puis de gauche à droite : l'ordre de lecture d'une planche.
    return [[a, b, c, d] for b, d in reversed(bornes(y0, y1)) for a, c in bornes(x0, x1)]


# --- Schémas de réponse -------------------------------------------------------------------------------------

_POINT = {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2}
_OBS = {"type": "array", "items": {"type": "string"}}


def schema_traits_ensemble() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["traits", "observations"],
        "properties": {
            "traits": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["nom", "points", "sens", "dessin"],
                    "properties": {
                        "nom": {"type": "string"},
                        "points": {"type": "array", "items": _POINT, "minItems": 2},
                        "sens": {"type": "string", "enum": list(SENS)},
                        "dessin": {"type": "string", "enum": ["trait_continu", "reperes_aux_extremites"]},
                    },
                },
            },
            "observations": _OBS,
        },
    }


def schema_traits_precis() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["extremites", "observations"],
        "properties": {
            "extremites": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["image", "point"],
                    "properties": {"image": {"type": "string"}, "point": _POINT},
                },
            },
            "observations": _OBS,
        },
    }


def schema_vues_ensemble() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["vues", "observations"],
        "properties": {
            "vues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["nom", "nature", "cadre", "haut"],
                    "properties": {
                        "nom": {"type": "string"},
                        "nature": {"type": "string", "enum": ["coupe", "facade", "detail"]},
                        "cadre": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4},
                        "haut": {"type": "string", "enum": list(SENS)},
                    },
                },
            },
            "observations": _OBS,
        },
    }


def schema_lecture_vue() -> dict[str, Any]:
    borne = {"anyOf": [{"type": "number"}, {"type": "string"}, {"type": "null"}]}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["niveaux", "pieces", "observations"],
        "properties": {
            "niveaux": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["nom", "cote_m", "position"],
                    "properties": {
                        "nom": {"type": "string"},
                        "cote_m": {"type": ["number", "null"]},
                        "position": {"type": ["number", "null"]},
                    },
                },
            },
            "pieces": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["nom", "gauche", "droite", "sol", "plafond", "hsp_ecrite_m", "exterieur"],
                    "properties": {
                        "nom": {"type": ["string", "null"]},
                        "gauche": {"type": "number"},
                        "droite": {"type": "number"},
                        "sol": {"anyOf": [{"type": "number"}, {"type": "string"}]},
                        "plafond": borne,
                        "hsp_ecrite_m": {"type": ["number", "null"]},
                        "exterieur": {"type": "boolean"},
                    },
                },
            },
            "observations": _OBS,
        },
    }


# --- Consignes ----------------------------------------------------------------------------------------------

REPERE = (
    "Les images sont quadrillées en points PDF de la page : traits bleus verticaux gradués « x… », traits orange "
    "horizontaux gradués « y… ». y croît VERS LE HAUT de la page. Lis chaque position sur la grille, en "
    "interpolant entre deux graduations ; ne donne jamais de pixels."
)


def consigne_traits_ensemble(image: Path) -> str:
    return "\n".join(
        [
            f"Plan de niveau : {image}",
            REPERE,
            "Repère chaque trait de coupe du plan (lettre ou chiffre : A, B, 1…). Il est marqué soit par un trait "
            "continu ou mixte (souvent rouge) terminé par des flèches, soit seulement par deux repères à ses "
            "extrémités (drapeaux, triangles), sans trait entre eux.",
            "Pour chacun : `nom` tel qu'écrit ; `points` = ses sommets dans l'ordre, extrémités comprises (un trait "
            "avec décrochés est une ligne brisée : donne chaque coude) ; `sens` = côté vers lequel pointent les "
            "flèches ou le drapeau, c'est-à-dire ce que l'on regarde (haut, bas, gauche ou droite de la page).",
            "Ignore les axes de trame, les cotes, les limites de propriété et les flèches du nord.",
        ]
    )


def consigne_traits_precis(zooms: list[dict[str, Any]]) -> str:
    lignes = [REPERE, "Chaque image est un zoom sur une extrémité ou un coude d'un trait de coupe."]
    for zoom in zooms:
        lignes.append(f"- {zoom['image']} : trait « {zoom['trait']} », point attendu vers {zoom['approche']}")
    lignes.append(
        "Pour chaque image, donne `point` : l'extrémité exacte du trait (là où il s'arrête, ou le bord du drapeau "
        "d'où part la ligne), ou le coude exact, lu sur la grille fine."
    )
    return "\n".join(lignes)


def consigne_vues_ensemble(image: Path) -> str:
    return "\n".join(
        [
            f"Planche de coupes ou de façades : {image}",
            REPERE,
            "Liste chaque vue dessinée sur la planche : `nom` tel qu'écrit (« COUPE AA », « Coupe B », « Façade "
            "Est »…) ; `nature` : coupe, facade, ou detail (un zoom, un détail constructif, une vue partielle "
            "annotée « détail » ou « zoom ») ; `cadre` = [x0, y0, x1, y1] qui englobe la vue (bâtiment, cotes de "
            "niveau, axes), sans le cartouche ; `haut` = le côté de la page vers lequel est le haut du bâtiment "
            "(le ciel, la toiture) : une vue peut être tournée d'un quart de tour.",
        ]
    )


def consigne_lecture_vue(vue: dict[str, Any], images: list[Path]) -> str:
    axe_horizontal = "x" if vue["haut"] in ("haut", "bas") else "y"
    axe_vertical = "y" if axe_horizontal == "x" else "x"
    return "\n".join(
        [
            f"Coupe « {vue['nom']} », en {len(images)} tuiles qui se recouvrent :",
            *[f"- {image}" for image in images],
            REPERE,
            f"Dans cette vue, le haut du bâtiment est vers le {vue['haut']} de la page : l'horizontale de la coupe "
            f"se lit sur l'axe {axe_horizontal} de la page, la verticale sur l'axe {axe_vertical}.",
            "1. `niveaux` : chaque ligne ou repère de niveau (sol fini, plafond fini, dalle : « H10 », « ±0,00 », "
            "« +7,05 NGF »…). `nom` tel qu'écrit, `cote_m` sa cote en mètres si elle est écrite ou déductible d'une "
            f"chaîne de cotes écrite, sinon null ; `position` sa coordonnée {axe_vertical} sur la grille.",
            "2. `pieces` : chaque pièce COUPÉE (volume traversé par le plan de coupe, souvent grisé ou limité par "
            "des murs et planchers coupés, hachurés ou noircis), à chaque étage. `nom` tel qu'écrit (numéro de "
            f"programme compris : « 6.1.2 Bur.1 »), null s'il n'y en a pas ; `gauche`, `droite` = ses bornes, "
            f"coordonnées {axe_horizontal} de ses deux murs ou cloisons ; `sol` = nom de la ligne de niveau de son "
            f"sol fini si elle en porte une, sinon sa coordonnée {axe_vertical} ; `plafond` = de même pour son "
            "plafond fini (sous le faux plafond s'il y en a un), null si le volume monte sans plafond à cet étage "
            "(double hauteur, trémie, atrium) ; `hsp_ecrite_m` = hauteur sous plafond si elle est écrite pour cette "
            "pièce, sinon null ; `exterieur` vrai pour une terrasse, un balcon, une coursive, un parking ouvert.",
            "N'invente rien : une borne illisible se signale dans `observations`. Ignore le mobilier, les personnages, "
            "la végétation et ce qui est vu au-delà du plan de coupe.",
        ]
    )


# --- Conversions vers le format du serveur ------------------------------------------------------------------


def trait_de_lecture(brut: dict[str, Any]) -> dict[str, Any]:
    return {"nom": str(brut["nom"]).strip(), "points": [[float(x), float(y)] for x, y in brut["points"]], "sens": list(SENS[brut["sens"]])}


def points_a_preciser(traits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Chaque sommet de chaque trait, avec le cadre de son zoom."""
    zooms = []
    for trait in traits:
        for rang, (x, y) in enumerate(trait["points"]):
            zooms.append(
                {
                    "trait": trait["nom"],
                    "rang": rang,
                    "approche": f"x{x:.0f}, y{y:.0f}",
                    "cadre": [x - DEMI_ZOOM_PT, y - DEMI_ZOOM_PT, x + DEMI_ZOOM_PT, y + DEMI_ZOOM_PT],
                }
            )
    return zooms


def appliquer_precisions(traits: list[dict[str, Any]], zooms: list[dict[str, Any]], reponse: dict[str, Any]) -> list[dict[str, Any]]:
    """Remplace chaque sommet approché par le point lu sur son zoom, s'il reste dans le zoom."""
    lus = {str(e["image"]): e["point"] for e in reponse.get("extremites", [])}
    par_nom = {t["nom"]: [list(p) for p in t["points"]] for t in traits}
    for zoom in zooms:
        point = lus.get(str(zoom["image"])) or lus.get(Path(str(zoom["image"])).name)
        if point is None:
            continue
        x0, y0, x1, y1 = zoom["cadre"]
        if x0 <= point[0] <= x1 and y0 <= point[1] <= y1:
            par_nom[zoom["trait"]][zoom["rang"]] = [float(point[0]), float(point[1])]
    return [{**t, "points": par_nom[t["nom"]]} for t in traits]


def lecture_de_vue(vue: dict[str, Any], brut: dict[str, Any]) -> dict[str, Any]:
    """Coordonnées de page lues par l'agent → repère de la vue attendu par `thermique_coupes.rattacher`.

    La droite de la vue est le haut tourné d'un quart de tour dans le sens horaire : (hy, −hx). Une borne se
    projette sur la droite, une altitude sur le haut ; comme la vue n'est tournée que par quarts de tour, une
    seule coordonnée de page porte chaque projection.
    """
    hx, hy = SENS[vue["haut"]]
    dx, dy = hy, -hx

    def le_long_de_la_droite(valeur: float) -> float:
        return float(valeur) * (dx if dx else dy)

    def le_long_du_haut(valeur: Any) -> Any:
        if valeur is None or isinstance(valeur, str):
            return valeur
        return float(valeur) * (hx if hx else hy)

    niveaux = [
        {"nom": n["nom"], "cote_m": n.get("cote_m"), "position": le_long_du_haut(n.get("position"))}
        for n in brut.get("niveaux", [])
    ]
    # Un nom de niveau sans cote ne peut pas servir de sol ou de plafond : on revient à sa position.
    sans_cote = {n["nom"]: n["position"] for n in niveaux if n.get("cote_m") is None}

    def altitude(valeur: Any) -> Any:
        if isinstance(valeur, str) and valeur in sans_cote:
            return sans_cote[valeur]
        return le_long_du_haut(valeur)

    pieces = []
    for piece in brut.get("pieces", []):
        sol = altitude(piece["sol"])
        if sol is None:
            continue
        pieces.append(
            {
                "nom": piece.get("nom"),
                "debut": le_long_de_la_droite(piece["gauche"]),
                "fin": le_long_de_la_droite(piece["droite"]),
                "sol": sol,
                "plafond": altitude(piece.get("plafond")),
                "hsp_ecrite_m": piece.get("hsp_ecrite_m"),
                "exterieur": bool(piece.get("exterieur")),
            }
        )
    return {
        "nom": vue["nom"],
        "nature": vue["nature"],
        "cadre": [float(v) for v in vue["cadre"]],
        "haut": [hx, hy],
        "niveaux": [n for n in niveaux if n.get("cote_m") is not None or n.get("position") is not None],
        "pieces": pieces,
    }
