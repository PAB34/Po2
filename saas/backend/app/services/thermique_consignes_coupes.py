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
# L'agent voit une image réduite à environ 1 000 pixels de côté (essai du 2026-09-29 : une page entière
# rendue à 1 600 px lui est arrivée illisible, repères et graduations compris). Toute image est donc rendue
# à cette taille, et une vue d'ensemble est une mosaïque de tuiles d'environ 500 points.
COTE_IMAGE_PX = 1000
PAS_ENSEMBLE_PT = 50
TAILLE_ENSEMBLE_PT = 520
PAS_ZOOM_PT = 5
PAS_TUILE_PT = 20
TAILLE_TUILE_PT = 400
RECOUVREMENT_TUILE_PT = 40
DEMI_ZOOM_PT = 60
# Une tuile où presque rien n'est dessiné n'est pas montrée à l'agent. Mesuré le 2026-09-29 : une tuile
# blanche (graduations seules) pèse 0,6 à 1,2 ‰, la marge de PC04 qui ne porte que les drapeaux des coupes
# A et C 2,9 ‰ ; l'ancien seuil de 4 ‰ l'écartait et l'agent n'a pas vu ces drapeaux.
ENCRE_MIN = 0.002


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
        # `largeur_px` borne le plus grand côté : une tuile haute et étroite reste lisible.
        echelle = largeur_px / max(x1 - x0, y1 - y0, 1.0)
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


def encre(image_path: Path) -> float:
    """Part des pixels dessinés d'une image, hors quadrillage (bleu et orange)."""
    import numpy as np
    from PIL import Image

    pixels = np.asarray(Image.open(image_path).convert("RGB")).astype(int)
    r, g, b = pixels[..., 0], pixels[..., 1], pixels[..., 2]
    sombre = (r + g + b) < 600
    grille = ((b > 150) & (r < 120)) | ((r > 180) & (b < 90) & (g > 60))
    return float((sombre & ~grille).mean())


def rendre_ensemble(pdf: Path, page_index: int, cadre: list[float], dossier: Path, prefixe: str) -> list[Path]:
    """La vue d'ensemble d'une page en mosaïque de tuiles lisibles par l'agent ; les tuiles vides sont écartées."""
    images = []
    for rang, morceau in enumerate(tuiles(cadre, TAILLE_ENSEMBLE_PT, RECOUVREMENT_TUILE_PT)):
        image = rendre_quadrille(pdf, page_index, morceau, PAS_ENSEMBLE_PT, COTE_IMAGE_PX, dossier / f"{prefixe}-{rang:02d}.png")
        if encre(image) >= ENCRE_MIN:
            images.append(image)
        else:
            image.unlink(missing_ok=True)
    return images


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
    """L'agent ne raisonne pas sur la rotation de la vue (essai du 2026-09-29 : coupes tournées lues comme
    droites). Il donne des positions de page ; l'outil déduit le haut par les cotes de niveau."""
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
                    "required": ["nom", "cote_m", "point"],
                    "properties": {
                        "nom": {"type": "string"},
                        "cote_m": {"type": ["number", "null"]},
                        "point": _POINT,
                    },
                },
            },
            "pieces": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["nom", "cadre", "sol", "plafond", "sans_plafond", "hsp_ecrite_m", "exterieur"],
                    "properties": {
                        "nom": {"type": ["string", "null"]},
                        "cadre": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4},
                        "sol": {"type": ["string", "null"]},
                        "plafond": {"type": ["string", "null"]},
                        "sans_plafond": {"type": "boolean"},
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


def _mosaique(images: list[Path]) -> list[str]:
    return [
        f"La planche est montrée en {len(images)} tuiles qui se recouvrent, toutes dans le même repère ; lis-les "
        "toutes avant de répondre :",
        *[f"- {image}" for image in images],
    ]


def consigne_traits_ensemble(images: list[Path], titre: str = "") -> str:
    return "\n".join(
        [
            f"Plan de niveau{f' « {titre} »' if titre else ''}.",
            *_mosaique(images),
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


def consigne_vues_ensemble(images: list[Path], titre: str = "", nature_planche: str = "coupe") -> str:
    classement = "coupes" if nature_planche == "coupe" else "façades"
    return "\n".join(
        [
            f"Planche classée « {classement} » par le thermicien{f', intitulée « {titre} »' if titre else ''}. "
            f"Ses vues sont des {classement}, sauf un détail ou un zoom clairement annoncé comme tel.",
            *_mosaique(images),
            REPERE,
            "Liste chaque vue dessinée sur la planche : `nom` tel qu'écrit près de la vue ou dans le cartouche "
            "(« COUPE AA », « Coupe B », « Façade Est »…) ; `nature` : coupe, facade, ou detail (un zoom, un "
            "détail constructif, une vue partielle annotée « détail » ou « zoom ») ; `cadre` = [x0, y0, x1, y1] "
            "en points PDF lus sur la grille, qui englobe la vue (bâtiment, cotes de niveau, axes), sans le "
            "cartouche ; `haut` = le côté de la page vers lequel est le haut du bâtiment.",
            "Une coupe peut être **tournée d'un quart de tour** et ressembler alors à un plan : ce qui la trahit, ce "
            "sont les repères de niveau (±0,00, +4,16, H10, NGF) alignés le long d'un bord, le sol naturel ou la "
            "rue d'un côté, la toiture de l'autre, des textes écrits dans le même sens. Le haut est du côté de la "
            "toiture et des cotes de niveau les plus élevées.",
        ]
    )


def consigne_lecture_vue(vue: dict[str, Any], images: list[Path]) -> str:
    return "\n".join(
        [
            f"Coupe « {vue['nom']} », en {len(images)} tuiles qui se recouvrent :",
            *[f"- {image}" for image in images],
            REPERE,
            "La coupe peut être dessinée tournée d'un quart de tour : ne t'en occupe pas, donne seulement des "
            "positions de page (x, y) lues sur la grille. L'outil déduira le sens de la coupe.",
            "1. `niveaux` : chaque repère ou ligne de niveau (« ±0,00 », « +4,16 », « H10 », « +7,05 NGF »…). "
            "`nom` tel qu'écrit ; `cote_m` sa cote en mètres si elle est écrite, ou déductible d'une chaîne de "
            "cotes écrite (H10 → H11 = 2,88 donne H11 = H10 + 2,88), sinon null ; `point` = [x, y] de la pointe "
            "du repère ou d'un point de la ligne, là où elle marque le niveau.",
            "2. `pieces` : chaque pièce COUPÉE (volume traversé par le plan de coupe, souvent grisé, borné par des "
            "murs et planchers coupés, hachurés ou noircis), à chaque étage. `nom` tel qu'écrit, numéro de programme "
            "compris (« 6.1.2 Bur.1 »), null s'il n'y en a pas ; `cadre` = [x0, y0, x1, y1] le rectangle de la "
            "pièce, de mur à mur et du sol fini au plafond fini (sous le faux plafond) ; `sol`, `plafond` = le nom "
            "de la ligne de niveau sur laquelle tombe son sol, son plafond, si elle en porte une (sinon null : le "
            "cadre fait foi) ; `sans_plafond` vrai si le volume monte sans plafond à cet étage (double hauteur, "
            "trémie, atrium) ; `hsp_ecrite_m` = hauteur sous plafond écrite pour cette pièce, sinon null ; "
            "`exterieur` vrai pour une terrasse, un balcon, une coursive, un parking ouvert.",
            "Une pièce dont tu ne vois pas les bornes n'est pas listée : dis-le dans `observations`. N'invente rien. "
            "Ignore le mobilier, les personnages, la végétation et ce qui est vu au-delà du plan de coupe.",
        ]
    )


# --- Conversions vers le format du serveur ------------------------------------------------------------------


def liste_rendue(reponse: dict[str, Any], cle: str) -> list[Any] | None:
    """La liste attendue sous `cle` ; l'agent la range parfois sous un autre nom (« coupes » pour « traits ») :
    une seule liste dans la réponse, hors observations, vaut réponse."""
    if isinstance(reponse.get(cle), list):
        return reponse[cle]
    autres = [v for k, v in reponse.items() if k != "observations" and isinstance(v, list)]
    return autres[0] if len(autres) == 1 else None


def point_lu(valeur: Any) -> list[float] | None:
    """Un point rendu par l'agent : [x, y] ou {"x": …, "y": …} (le schéma de réponse n'est pas toujours
    respecté : essai du 2026-09-29 sur PC04)."""
    if isinstance(valeur, dict):
        valeur = [valeur.get("x"), valeur.get("y")]
    if isinstance(valeur, (list, tuple)) and len(valeur) == 2 and all(isinstance(v, (int, float)) for v in valeur):
        return [float(valeur[0]), float(valeur[1])]
    return None


def traits_de_lecture(bruts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Les traits exploitables, et ce qui a été écarté en clair. Un sens illisible n'écarte pas le trait : la
    coupe le tranchera (`thermique_coupes.rattacher` essaie les deux sens)."""
    traits, ecartes = [], []
    for brut in bruts:
        nom = str(brut.get("nom") or "").strip()
        points = [p for p in (point_lu(p) for p in brut.get("points") or []) if p is not None]
        if not nom or len(points) < 2:
            ecartes.append(f"trait « {nom or '?'} » écarté : une seule extrémité lue")
            continue
        sens = SENS.get(brut.get("sens") or "", (0.0, 1.0))
        traits.append({"nom": nom, "points": [[float(x), float(y)] for x, y in points], "sens": list(sens)})
    return traits, ecartes


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
    lus = {
        str(e.get("image")): point_lu(e.get("point"))
        for e in (liste_rendue(reponse, "extremites") or [])
        if isinstance(e, dict) and point_lu(e.get("point")) is not None
    }
    par_nom = {t["nom"]: [list(p) for p in t["points"]] for t in traits}
    for zoom in zooms:
        point = lus.get(str(zoom["image"])) or lus.get(Path(str(zoom["image"])).name)
        if point is None:
            continue
        x0, y0, x1, y1 = zoom["cadre"]
        if x0 <= point[0] <= x1 and y0 <= point[1] <= y1:
            par_nom[zoom["trait"]][zoom["rang"]] = [float(point[0]), float(point[1])]
    return [{**t, "points": par_nom[t["nom"]]} for t in traits]


def _correlation(a: list[float], b: list[float]) -> float:
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = sum((x - ma) ** 2 for x in a) ** 0.5
    vb = sum((y - mb) ** 2 for y in b) ** 0.5
    return cov / (va * vb) if va > 0 and vb > 0 else 0.0


def haut_par_les_cotes(niveaux: list[dict[str, Any]]) -> tuple[float, float] | None:
    """Le haut de la vue, déduit de la direction dans laquelle les cotes de niveau montent sur la page.

    C'est ce que l'agent ne savait pas faire (2026-09-29) : il notait lui-même que les repères de niveau
    étaient « alignés selon x » sans en conclure que la coupe était tournée. Il faut au moins deux cotes
    distantes d'un mètre ; sinon, rien n'est déduit.
    """
    points = [(n["point"], float(n["cote_m"])) for n in niveaux if n.get("cote_m") is not None and n.get("point")]
    cotes = [c for _, c in points]
    if len(points) < 2 or max(cotes) - min(cotes) < 1.0:
        return None
    rx = _correlation([float(p[0]) for p, _ in points], cotes)
    ry = _correlation([float(p[1]) for p, _ in points], cotes)
    if max(abs(rx), abs(ry)) < 0.8:
        return None
    return ((1.0 if rx > 0 else -1.0), 0.0) if abs(rx) > abs(ry) else (0.0, (1.0 if ry > 0 else -1.0))


def lecture_de_vue(vue: dict[str, Any], brut: dict[str, Any]) -> dict[str, Any]:
    """Positions de page lues par l'agent → repère de la vue attendu par `thermique_coupes.rattacher`.

    Le haut vient des cotes de niveau (`haut_par_les_cotes`), à défaut du repérage d'ensemble. La droite de la
    vue est le haut tourné d'un quart de tour dans le sens horaire : (hy, −hx). Les bornes d'une pièce sont
    la projection de son cadre sur la droite, son sol et son plafond la projection sur le haut, sauf quand ils
    tombent sur une ligne de niveau cotée : la cote écrite fait foi.
    """
    niveaux_bruts = [
        {**n, "point": point_lu(n.get("point"))} for n in brut.get("niveaux", []) if isinstance(n, dict) and n.get("nom")
    ]
    deduit = haut_par_les_cotes(niveaux_bruts)
    hx, hy = deduit or SENS.get(vue.get("haut") or "haut", (0.0, 1.0))
    dx, dy = hy, -hx

    def sur_le_haut(point: Any) -> float:
        return float(point[0]) * hx + float(point[1]) * hy

    niveaux = [
        {"nom": str(n["nom"]), "cote_m": n.get("cote_m"), "position": sur_le_haut(n["point"]) if n.get("point") else None}
        for n in niveaux_bruts
    ]
    cotes = {n["nom"] for n in niveaux if n["cote_m"] is not None}

    pieces = []
    for piece in brut.get("pieces", []):
        cadre = piece.get("cadre") if isinstance(piece, dict) else None
        if not isinstance(cadre, list) or len(cadre) != 4 or any(not isinstance(v, (int, float)) for v in cadre):
            continue
        coins = [(cadre[0], cadre[1]), (cadre[2], cadre[3]), (cadre[0], cadre[3]), (cadre[2], cadre[1])]
        largeur = [x * dx + y * dy for x, y in coins]
        hauteur = [x * hx + y * hy for x, y in coins]
        sol = piece.get("sol") if piece.get("sol") in cotes else min(hauteur)
        if piece.get("sans_plafond"):
            plafond = None
        else:
            plafond = piece.get("plafond") if piece.get("plafond") in cotes else max(hauteur)
        pieces.append(
            {
                "nom": piece.get("nom"),
                "debut": min(largeur),
                "fin": max(largeur),
                "sol": sol,
                "plafond": plafond,
                "hsp_ecrite_m": piece.get("hsp_ecrite_m"),
                "exterieur": bool(piece.get("exterieur")),
            }
        )
    return {
        "nom": vue["nom"],
        "nature": vue["nature"],
        "cadre": [float(v) for v in vue["cadre"]],
        "haut": [hx, hy],
        "haut_par": "cotes" if deduit else "reperage",
        "niveaux": [n for n in niveaux if n["cote_m"] is not None or n["position"] is not None],
        "pieces": pieces,
    }
