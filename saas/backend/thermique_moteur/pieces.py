"""Pièces d'un plan — étape E3 (docs/thermique/refondation-parcours-decisions.md §13, D28).

Une pièce est un espace **fermé par les calques désignés** (murs, cloisons, menuiseries, portes, garde-corps) :

1. les éléments-limites sont dessinés dans une image à 5 cm le pixel ;
2. les limites sont **épaissies** de `fermeture_m / 2` de chaque côté, ce qui referme les ouvertures plus étroites
   que `fermeture_m` (baies, passages) ; une fermeture morphologique ne suffit pas (elle laisse ouvert l'espace
   entre deux bouts de cloison alignés) ;
3. chaque espace libre qui ne touche pas le bord de l'image est une pièce candidate ; elle récupère ensuite les
   pixels libres pris par l'épaississement (au plus proche), puis est gardée entre `surface_min` et `surface_max` ;
4. son contour suit les bords des pixels, puis il est simplifié (Douglas-Peucker, 1 pixel).

Constat du 2026-09-17 (RDC du projet de production) : avec les seuls calques « mur » (hachure) et « isolant »,
1 à 2 espaces clos ; les portes (arc 0,36 pt, vantail 0,48 pt) et les vitrages doivent être désignés.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from thermique_moteur.calques import TRAIT
from thermique_moteur.metre import pt_en_m

NATURES_LIMITES = ("mur", "isolant", "cloison", "menuiserie", "menuiserie_interieure", "porte", "garde_corps")
RESOLUTION_M = 0.05
MARGE_M = 1.0
FERMETURE_M = 0.4
SURFACE_MIN_M2 = 1.0
# un plateau ouvert de médiathèque dépasse 800 m² (essai R+2 du 2026-09-17)
SURFACE_MAX_M2 = 3000.0
PIXELS_MAX = 40_000_000


class PiecesError(ValueError):
    pass


class Grille:
    """Image de la planche : pixel (colonne, ligne) ↔ point PDF."""

    def __init__(self, xmin: float, ymin: float, xmax: float, ymax: float, echelle: float, marge_m: float = MARGE_M):
        self.pas = RESOLUTION_M / pt_en_m(echelle)
        marge = marge_m / pt_en_m(echelle)
        self.ox, self.oy = xmin - marge, ymin - marge
        self.largeur = int((xmax - xmin + 2 * marge) / self.pas) + 1
        self.hauteur = int((ymax - ymin + 2 * marge) / self.pas) + 1
        if self.largeur * self.hauteur > PIXELS_MAX:
            raise PiecesError("Plan trop étendu pour la détection des pièces.")
        self.m2_par_pixel = RESOLUTION_M * RESOLUTION_M

    def pixel(self, x: float, y: float) -> tuple[float, float]:
        return (x - self.ox) / self.pas, (y - self.oy) / self.pas

    def point(self, colonne: float, ligne: float) -> tuple[float, float]:
        return self.ox + colonne * self.pas, self.oy + ligne * self.pas

    def image(self) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        image = Image.new("1", (self.largeur, self.hauteur), 0)
        return image, ImageDraw.Draw(image)


def marge_pour(fermeture_m: float) -> float:
    """Marge autour du dessin : plus large que l'épaississement, sinon des limites épaissies touchent le bord et
    l'extérieur est coupé en morceaux (constaté sur le R+2 à 2 m de fermeture)."""
    return max(MARGE_M, fermeture_m / 2 + 0.5)


def grille_des_elements(donnees: dict, indices: list[int], marge_m: float = MARGE_M) -> Grille:
    elements = [donnees["elements"][i] for i in indices]
    if not elements:
        raise PiecesError("Aucun calque de limite désigné sur ce plan : désignez murs, cloisons, portes et menuiseries.")
    return Grille(
        min(e[3] for e in elements), min(e[4] for e in elements), max(e[5] for e in elements), max(e[6] for e in elements), donnees["echelle"],
        marge_m,
    )


def image_limites(donnees: dict, indices: list[int], grille: Grille) -> np.ndarray:
    image, dessin = grille.image()
    for index in indices:
        element = donnees["elements"][index]
        coords = element[7]
        points = [grille.pixel(coords[k], coords[k + 1]) for k in range(0, len(coords) - 1, 2)]
        if element[0] == TRAIT:
            if len(points) >= 2:
                dessin.line(points, fill=1, width=1)
        elif len(points) >= 3:
            dessin.polygon(points, fill=1, outline=1)
    return np.array(image, dtype=bool)


def _disque(rayon: int) -> np.ndarray:
    y, x = np.ogrid[-rayon : rayon + 1, -rayon : rayon + 1]
    return x * x + y * y <= rayon * rayon


def _rayon(largeur_m: float) -> int:
    return int(round(largeur_m / RESOLUTION_M / 2))


def epaissir(limites: np.ndarray, fermeture_m: float) -> np.ndarray:
    rayon = _rayon(fermeture_m)
    return ndimage.binary_dilation(limites, structure=_disque(rayon)) if rayon > 0 else limites


def _espaces(limites: np.ndarray, fermeture_m: float) -> tuple[np.ndarray, int, set[int]]:
    """Espaces libres numérotés, limites épaissies ; chaque pixel libre pris par l'épaississement est ensuite rendu
    à l'espace le plus proche (angles et bords des pièces restitués)."""
    etiquettes, nombre = ndimage.label(~epaissir(limites, fermeture_m))
    rayon = _rayon(fermeture_m)
    if nombre and rayon > 0:
        # croissance pas à pas, sans jamais franchir une limite (une pièce ne gagne pas les pixels d'un mur creux
        # ou de la pièce voisine à travers un trait) ; jusqu'à la diagonale du rayon pour restituer les angles
        libres = ~limites
        # croissance en croix : un coin en diagonale est à 2 × rayon pas (constaté sur le R+2 : pointes en V)
        for _ in range(2 * rayon + 2):
            candidats = (etiquettes == 0) & libres
            if not candidats.any():
                break
            voisins = ndimage.grey_dilation(etiquettes, footprint=np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool))
            etiquettes = np.where(candidats & (voisins > 0), voisins, etiquettes)
    bord = set(np.unique(np.concatenate([etiquettes[0], etiquettes[-1], etiquettes[:, 0], etiquettes[:, -1]]))) - {0}
    return etiquettes, nombre, bord


def contour(masque: np.ndarray) -> list[tuple[int, int]]:
    """Contour extérieur d'un masque (sommets de pixels, colonne puis ligne), en suivant les bords des pixels."""
    m = np.pad(masque, 1)
    lignes, colonnes = np.nonzero(m & ~ndimage.binary_erosion(m))
    suivants: dict[tuple[int, int], list[tuple[int, int]]] = {}

    def ajouter(depart, arrivee):
        suivants.setdefault(depart, []).append(arrivee)

    for l, c in zip(lignes.tolist(), colonnes.tolist()):
        if not m[l - 1, c]:
            ajouter((c + 1, l), (c, l))
        if not m[l + 1, c]:
            ajouter((c, l + 1), (c + 1, l + 1))
        if not m[l, c - 1]:
            ajouter((c, l), (c, l + 1))
        if not m[l, c + 1]:
            ajouter((c + 1, l + 1), (c + 1, l))
    boucles = []
    while suivants:
        depart = next(iter(suivants))
        boucle = [depart]
        courant = depart
        while True:
            options = suivants.get(courant)
            if not options:
                break
            prochain = options.pop()
            if not options:
                del suivants[courant]
            if prochain == depart:
                break
            boucle.append(prochain)
            courant = prochain
        boucles.append(boucle)
    exterieure = max(boucles, key=lambda b: abs(_aire(b)))
    return [(c - 1, l - 1) for c, l in exterieure]


def _aire(points: list[tuple[float, float]]) -> float:
    return 0.5 * sum(points[k][0] * points[k - 1][1] - points[k - 1][0] * points[k][1] for k in range(len(points)))


def simplifier(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    """Douglas-Peucker sur un contour fermé."""
    if len(points) <= 4:
        return points
    # coupe en deux au point le plus éloigné du premier
    loin = max(range(len(points)), key=lambda k: math.dist(points[0], points[k]))
    return _dp(points[: loin + 1], tolerance)[:-1] + _dp(points[loin:] + [points[0]], tolerance)[:-1]


def _dp(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    garder = [False] * len(points)
    garder[0] = garder[-1] = True
    pile = [(0, len(points) - 1)]
    while pile:
        debut, fin = pile.pop()
        (ax, ay), (bx, by) = points[debut], points[fin]
        longueur = math.hypot(bx - ax, by - ay)
        pire, indice = 0.0, None
        for k in range(debut + 1, fin):
            px, py = points[k]
            d = abs((bx - ax) * (ay - py) - (ax - px) * (by - ay)) / longueur if longueur else math.hypot(px - ax, py - ay)
            if d > pire:
                pire, indice = d, k
        if indice is not None and pire > tolerance:
            garder[indice] = True
            pile += [(debut, indice), (indice, fin)]
    return [p for p, g in zip(points, garder) if g]


def _piece(masque: np.ndarray, grille: Grille, decalage: tuple[int, int] = (0, 0), segments=None) -> dict:
    """Pièce d'un masque (éventuellement recadré : `decalage` = colonne et ligne de son coin). Avec `segments`,
    le contour est redressé sur les faces vectorielles et la surface est celle du contour redressé."""
    sommets = simplifier(contour(masque), 1.0)
    points = [grille.point(c + decalage[0], l + decalage[1]) for c, l in sommets]
    m_par_pt = RESOLUTION_M / grille.pas
    redresse = None
    if segments is not None and len(segments):
        from thermique_moteur.redressement import redresser

        redresse = redresser(points, segments, m_par_pt)
    # point d'étiquette : le plus loin des bords, donc à l'intérieur même d'une pièce en L
    distances = ndimage.distance_transform_edt(np.pad(masque, 1))[1:-1, 1:-1]
    cy, cx = np.unravel_index(int(np.argmax(distances)), distances.shape)
    cx, cy = cx + 0.5 + decalage[0], cy + 0.5 + decalage[1]
    # les traits-limites occupent un pixel : la moitié revient à la pièce, tout le long du contour
    perimetre_m = sum(math.dist(sommets[k - 1], sommets[k]) for k in range(len(sommets))) * RESOLUTION_M
    return {
        "contour": [round(v, 2) for p in (redresse or points) for v in p],
        "surface_m2": round(
            _aire_pt(redresse) * m_par_pt * m_par_pt
            if redresse
            else float(masque.sum()) * grille.m2_par_pixel + perimetre_m * RESOLUTION_M / 2,
            2,
        ),
        "centre": [round(v, 2) for v in grille.point(cx, cy)],
    }


def _aire_pt(points) -> float:
    return abs(sum(points[k - 1][0] * points[k][1] - points[k][0] * points[k - 1][1] for k in range(len(points)))) / 2


def _segments(donnees: dict, indices: list[int], grille: Grille):
    from thermique_moteur.redressement import segments_des_elements

    return segments_des_elements(donnees, indices, RESOLUTION_M / grille.pas)


def detecter(
    donnees: dict,
    indices: list[int],
    fermeture_m: float = FERMETURE_M,
    surface_min: float = SURFACE_MIN_M2,
    surface_max: float = SURFACE_MAX_M2,
) -> list[dict]:
    """Pièces candidates d'une planche, de la plus grande à la plus petite."""
    grille = grille_des_elements(donnees, indices, marge_pour(fermeture_m))
    etiquettes, nombre, bord = _espaces(image_limites(donnees, indices, grille), fermeture_m)
    if nombre == 0:
        return []
    tailles = np.bincount(etiquettes.ravel(), minlength=nombre + 1) * grille.m2_par_pixel
    objets = ndimage.find_objects(etiquettes)
    segments = _segments(donnees, indices, grille)
    pieces = []
    for numero in range(1, nombre + 1):
        if numero in bord or not surface_min <= tailles[numero] <= surface_max:
            continue
        lignes, colonnes = objets[numero - 1]
        masque = etiquettes[lignes, colonnes] == numero
        pieces.append(_piece(masque, grille, (colonnes.start, lignes.start), segments))
    return sorted(pieces, key=lambda p: -p["surface_m2"])


def piece_au_point(donnees: dict, indices: list[int], x: float, y: float, fermeture_m: float = FERMETURE_M) -> dict:
    """Espace fermé qui contient le point cliqué."""
    grille = grille_des_elements(donnees, indices, marge_pour(fermeture_m))
    colonne, ligne = (int(v) for v in grille.pixel(x, y))
    if not (0 <= ligne < grille.hauteur and 0 <= colonne < grille.largeur):
        raise PiecesError("Le point cliqué est hors des limites dessinées.")
    etiquettes, _nombre, bord = _espaces(image_limites(donnees, indices, grille), fermeture_m)
    numero = int(etiquettes[ligne, colonne])
    if numero == 0:
        raise PiecesError("Le point cliqué tombe sur une limite : cliquez à l'intérieur de la pièce.")
    if numero in bord:
        raise PiecesError(
            "Cet espace n'est pas fermé : désignez les limites manquantes (portes, vitrages) ou augmentez la fermeture des ouvertures."
        )
    lignes, colonnes = ndimage.find_objects((etiquettes == numero).astype(np.int32))[0]
    return _piece(etiquettes[lignes, colonnes] == numero, grille, (colonnes.start, lignes.start), _segments(donnees, indices, grille))


def _grille_polygones(polygones: list[list[float]], echelle: float) -> Grille:
    xs = [v for p in polygones for v in p[0::2]]
    ys = [v for p in polygones for v in p[1::2]]
    return Grille(min(xs), min(ys), max(xs), max(ys), echelle)


def _remplir(polygones: list[list[float]], grille: Grille) -> np.ndarray:
    image, dessin = grille.image()
    for polygone in polygones:
        dessin.polygon([grille.pixel(polygone[k], polygone[k + 1]) for k in range(0, len(polygone) - 1, 2)], fill=1, outline=1)
    return np.array(image, dtype=bool)


def _cotes(polygones: list[list[float]]) -> np.ndarray:
    """Côtés de contours fermés (x1, y1, x2, y2), pour redresser une fusion ou une découpe."""
    lignes = []
    for polygone in polygones:
        n = len(polygone) // 2
        for k in range(n):
            j = (k + 1) % n if n > 2 else k + 1
            if j < n:
                lignes.append([polygone[2 * k], polygone[2 * k + 1], polygone[2 * j], polygone[2 * j + 1]])
    return np.asarray(lignes, dtype=float).reshape(-1, 4)


def fusionner(polygones: list[list[float]], echelle: float, epaisseur_max_m: float = 0.6) -> dict:
    """Une pièce à partir de pièces voisines (séparées au plus par une paroi de `epaisseur_max_m`)."""
    if len(polygones) < 2:
        raise PiecesError("Choisissez au moins deux pièces à fusionner.")
    grille = _grille_polygones(polygones, echelle)
    # deux pièces séparées par une paroi : une fermeture comble la bande entre elles
    union = ndimage.binary_closing(_remplir(polygones, grille), structure=_disque(_rayon(epaisseur_max_m)))
    etiquettes, nombre = ndimage.label(union)
    if nombre != 1:
        raise PiecesError("Ces pièces ne sont pas voisines : fusionnez des pièces qui se touchent.")
    return _piece(union, grille, segments=_cotes(polygones))


def decouper(polygone: list[float], p1: list[float], p2: list[float], echelle: float) -> list[dict]:
    """Coupe une pièce le long du trait p1-p2 (qui doit la traverser)."""
    grille = _grille_polygones([polygone, [p1[0], p1[1], p2[0], p2[1]]], echelle)
    masque = _remplir([polygone], grille)
    image = Image.fromarray(masque)
    ImageDraw.Draw(image).line([grille.pixel(*p1), grille.pixel(*p2)], fill=0, width=1)
    coupe = np.array(image, dtype=bool)
    etiquettes, nombre = ndimage.label(coupe)
    tailles = np.bincount(etiquettes.ravel(), minlength=nombre + 1) * grille.m2_par_pixel
    morceaux = [n for n in range(1, nombre + 1) if tailles[n] >= 0.5]
    if len(morceaux) < 2:
        raise PiecesError("Le trait ne coupe pas la pièce en deux : tracez-le d'un bord à l'autre.")
    cotes = _cotes([polygone, [p1[0], p1[1], p2[0], p2[1]]])
    return sorted((_piece(etiquettes == n, grille, segments=cotes) for n in morceaux), key=lambda p: -p["surface_m2"])


def dedans(x: float, y: float, polygone: list[float]) -> bool:
    resultat = False
    n = len(polygone) // 2
    for k in range(n):
        x1, y1 = polygone[2 * k], polygone[2 * k + 1]
        x2, y2 = polygone[2 * ((k + 1) % n)], polygone[2 * ((k + 1) % n) + 1]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            resultat = not resultat
    return resultat
