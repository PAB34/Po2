"""Éléments dessinés d'une planche et désignation des calques par l'exemple.

Étape E1 révisée (docs/thermique/refondation-parcours-decisions.md §10, décisions Q66 à Q69). Un **élément** est
un tracé continu du PDF, d'un « moveto » au suivant : polyligne, contour fermé, arc ou remplissage. Sa
**famille** réunit sa signature (trait : largeur, couleur exacte, tirets ; remplissage : couleur) et, pour un
trait, sa **forme**. Le thermicien clique un élément et donne sa nature ; la règle vaut pour tous les éléments de
la même famille, sur tous les plans du projet. Ce qui n'est pas désigné est ignoré.

Constaté au niveau 0 du projet d'essai : la plume 0,36 pt noire compte 2 834 éléments (1 856 traits courts,
400 polylignes, 354 traits droits, 224 contours fermés) ; la forme sépare marches, mobilier et cloisons.
"""
from __future__ import annotations

import ctypes
import math
from pathlib import Path

import numpy as np

from thermique_moteur.metre import pt_en_m
from thermique_moteur.signatures import cle_aplat, cle_trait, nom_couleur
from thermique_moteur.traits import PROFONDEUR_MAX, VERROU_PDFIUM, _composer

# Un élément est une liste compacte : [genre, n° de signature, forme, x min, y min, x max, y max, coordonnées].
TRAIT, REMPLISSAGE = 0, 1
TOUTES_FORMES = "*"
FORME_REMPLISSAGE = "remplissage"
FORMES = {
    "droit": "trait droit",
    "polyligne": "polyligne",
    "court": "trait court (< 40 cm)",
    "petit_ferme": "petit contour fermé (< 1,5 m)",
    "grand_ferme": "grand contour fermé",
    "courbe": "arc ou courbe",
    FORME_REMPLISSAGE: "remplissage",
}
NATURES = {
    "mur": "Mur (maçonnerie, béton)",
    "isolant": "Isolant",
    "cloison": "Cloison, doublage",
    "menuiserie": "Menuiserie (fenêtre, baie, vitrage)",
    # à forcer seulement : l'intérieur / extérieur se déduit des pièces de part et d'autre (D31)
    "menuiserie_interieure": "Menuiserie intérieure (forcée)",
    "porte": "Porte",
    "garde_corps": "Garde-corps, limite de terrasse",
    "plancher": "Plancher, dalle (coupes)",
    "toiture": "Toiture (coupes)",
}
PARTOUT = "partout"
COURT_M = 0.4
PETIT_FERME_M = 1.5
TOL_FERMETURE_PT = 0.05
SUPERPOSITION_PT = 0.5


def forme_trait(points: list, ferme: bool, courbe: bool, echelle: float) -> str:
    m = 1.0 / pt_en_m(echelle)
    if courbe:
        return "courbe"
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    if ferme:
        return "petit_ferme" if max(max(xs) - min(xs), max(ys) - min(ys)) < PETIT_FERME_M * m else "grand_ferme"
    longueur = sum(math.hypot(points[k + 1][0] - points[k][0], points[k + 1][1] - points[k][1]) for k in range(len(points) - 1))
    if longueur < COURT_M * m:
        return "court"
    return "droit" if len(points) == 2 else "polyligne"


def libelle_signature(signature: str) -> str:
    morceaux = signature.split("|")
    if morceaux[0] == "aplat":
        return f"Remplissage {nom_couleur(morceaux[1])}"
    texte = f"{float(morceaux[1]):.2f} pt · {nom_couleur(morceaux[2])}".replace(".", ",")
    return texte + (" · tirets" if len(morceaux) > 3 and morceaux[3] else "")


def libelle_forme(forme: str) -> str:
    return "toutes formes" if forme == TOUTES_FORMES else FORMES.get(forme, forme)


def assembler(elements: list[tuple], echelle: float) -> dict:
    """Éléments (genre, signature, forme, coordonnées à plat) → données compactes, avec les comptes par famille."""
    signatures: dict[str, int] = {}
    liste, comptes = [], {}
    for genre, signature, forme, coords in elements:
        numero = signatures.setdefault(signature, len(signatures))
        xs, ys = coords[0::2], coords[1::2]
        liste.append([genre, numero, forme, min(xs), min(ys), max(xs), max(ys), coords])
        cle = f"{signature}#{forme}"
        comptes[cle] = comptes.get(cle, 0) + 1
    return {"echelle": echelle, "signatures": list(signatures), "elements": liste, "comptes": comptes}


def _parcourir(brut, objets: list, parent: tuple, echelle: float, sortie: list, profondeur: int) -> None:
    matrice = brut.FS_MATRIX()
    x, y = ctypes.c_float(), ctypes.c_float()
    largeur = ctypes.c_float()
    remplissage, trace = ctypes.c_int(), ctypes.c_int()
    rouge, vert, bleu, alpha = (ctypes.c_uint() for _ in range(4))
    for objet in objets:
        genre = brut.FPDFPageObj_GetType(objet)
        if not brut.FPDFPageObj_GetMatrix(objet, ctypes.byref(matrice)):
            continue
        m = _composer((matrice.a, matrice.b, matrice.c, matrice.d, matrice.e, matrice.f), parent)
        if genre == brut.FPDF_PAGEOBJ_FORM:
            if profondeur < PROFONDEUR_MAX:
                enfants = [brut.FPDFFormObj_GetObject(objet, i) for i in range(brut.FPDFFormObj_CountObjects(objet))]
                _parcourir(brut, enfants, m, echelle, sortie, profondeur + 1)
            continue
        if genre != brut.FPDF_PAGEOBJ_PATH or not brut.FPDFPath_GetDrawMode(objet, ctypes.byref(remplissage), ctypes.byref(trace)):
            continue
        if not (remplissage.value or trace.value):
            continue
        a, b, c, d, e, f = m
        signatures = []
        if trace.value:
            brut.FPDFPageObj_GetStrokeWidth(objet, ctypes.byref(largeur))
            brut.FPDFPageObj_GetStrokeColor(objet, ctypes.byref(rouge), ctypes.byref(vert), ctypes.byref(bleu), ctypes.byref(alpha))
            facteur = math.sqrt(abs(a * d - b * c))
            tirets = ""
            nombre = brut.FPDFPageObj_GetDashCount(objet)
            if nombre > 0:
                motif = (ctypes.c_float * nombre)()
                brut.FPDFPageObj_GetDashArray(objet, motif, nombre)
                tirets = "-".join(f"{valeur * facteur:.1f}" for valeur in motif)
            couleur = f"#{rouge.value:02x}{vert.value:02x}{bleu.value:02x}"
            signatures.append((TRAIT, cle_trait(round(largeur.value * facteur, 2), couleur, tirets)))
        if remplissage.value:
            brut.FPDFPageObj_GetFillColor(objet, ctypes.byref(rouge), ctypes.byref(vert), ctypes.byref(bleu), ctypes.byref(alpha))
            signatures.append((REMPLISSAGE, cle_aplat(f"#{rouge.value:02x}{vert.value:02x}{bleu.value:02x}")))

        chemins = []
        points: list = []
        ferme = courbe = False
        bezier = 0
        for i in range(brut.FPDFPath_CountSegments(objet)):
            segment = brut.FPDFPath_GetPathSegment(objet, i)
            brut.FPDFPathSegment_GetPoint(segment, ctypes.byref(x), ctypes.byref(y))
            point = (a * x.value + c * y.value + e, b * x.value + d * y.value + f)
            nature = brut.FPDFPathSegment_GetType(segment)
            if nature == brut.FPDF_SEGMENT_MOVETO:
                if len(points) >= 2:
                    chemins.append((points, ferme, courbe))
                points, ferme, courbe, bezier = [point], False, False, 0
            else:
                ajouter = True
                if nature == brut.FPDF_SEGMENT_BEZIERTO:
                    # Courbe : trois points par morceau, on garde l'extrémité.
                    courbe = True
                    bezier += 1
                    ajouter = bezier % 3 == 0
                if ajouter:
                    points.append(point)
            if brut.FPDFPathSegment_GetClose(segment):
                ferme = True
        if len(points) >= 2:
            chemins.append((points, ferme, courbe))

        for genre_element, signature in signatures:
            for points, ferme, courbe in chemins:
                if genre_element == REMPLISSAGE and len(points) < 3:
                    continue
                boucle = ferme or (len(points) >= 4 and math.hypot(points[0][0] - points[-1][0], points[0][1] - points[-1][1]) <= TOL_FERMETURE_PT)
                if genre_element == TRAIT:
                    if sum(math.hypot(points[k + 1][0] - points[k][0], points[k + 1][1] - points[k][1]) for k in range(len(points) - 1)) <= 0:
                        continue
                    forme = forme_trait(points, boucle, courbe, echelle)
                    if ferme and points[0] != points[-1]:
                        points = [*points, points[0]]
                else:
                    forme = FORME_REMPLISSAGE
                sortie.append((genre_element, signature, forme, [round(v, 2) for p in points for v in p]))


def lire_elements(pdf_path: Path | str, page_index: int, echelle: float) -> dict:
    """Tous les éléments tracés ou remplis d'une page, rangés par famille (signature + forme)."""
    import pypdfium2 as pdfium
    import pypdfium2.raw as brut

    sortie: list = []
    with VERROU_PDFIUM:
        document = pdfium.PdfDocument(str(pdf_path))
        try:
            page = document[page_index]
            objets = [brut.FPDFPage_GetObject(page.raw, i) for i in range(brut.FPDFPage_CountObjects(page.raw))]
            _parcourir(brut, objets, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), echelle, sortie, 0)
            page.close()
        finally:
            document.close()
    return assembler(sortie, echelle)


def _distance_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    dx, dy = bx - ax, by - ay
    carre = dx * dx + dy * dy
    t = 0.0 if carre == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / carre))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def _dedans(px: float, py: float, coords: list) -> bool:
    dedans = False
    n = len(coords) // 2
    for k in range(n):
        x1, y1 = coords[2 * k], coords[2 * k + 1]
        x2, y2 = coords[2 * ((k + 1) % n)], coords[2 * ((k + 1) % n) + 1]
        if (y1 > py) != (y2 > py) and px < x1 + (py - y1) * (x2 - x1) / (y2 - y1):
            dedans = not dedans
    return dedans


def element_sous_point(donnees: dict, x: float, y: float, tolerance: float) -> int | None:
    """Trait le plus proche du point (à `tolerance` près) ; à défaut, le plus petit remplissage qui le contient.

    Des traits superposés (à 0,5 pt près) : le plus épais l'emporte (constaté au niveau 3 du projet d'essai, où un
    trait fin de 0,36 pt double la face d'un mur de 1,56 pt), puis le dernier dessiné."""
    traits: list[tuple[float, int]] = []
    remplis = []
    for index, element in enumerate(donnees["elements"]):
        if x < element[3] - tolerance or x > element[5] + tolerance or y < element[4] - tolerance or y > element[6] + tolerance:
            continue
        coords = element[7]
        if element[0] == TRAIT:
            distance = min(
                _distance_segment(x, y, coords[k], coords[k + 1], coords[k + 2], coords[k + 3]) for k in range(0, len(coords) - 2, 2)
            )
            if distance <= tolerance:
                traits.append((distance, index))
        elif _dedans(x, y, coords):
            remplis.append(((element[5] - element[3]) * (element[6] - element[4]), index))
    if traits:
        plus_proche = min(distance for distance, _ in traits)
        signatures = donnees["signatures"]
        voisins = [index for distance, index in traits if distance <= plus_proche + SUPERPOSITION_PT]
        return max(voisins, key=lambda i: (float(signatures[donnees["elements"][i][1]].split("|")[1]), i))
    return min(remplis)[1] if remplis else None


def nombre_famille(donnees: dict, signature: str, forme: str) -> int:
    comptes = donnees["comptes"]
    if forme == TOUTES_FORMES:
        return sum(nombre for cle, nombre in comptes.items() if cle.rsplit("#", 1)[0] == signature)
    return comptes.get(f"{signature}#{forme}", 0)


def famille(donnees: dict, signature: str, forme: str) -> list[int]:
    try:
        numero = donnees["signatures"].index(signature)
    except ValueError:
        return []
    return [i for i, e in enumerate(donnees["elements"]) if e[1] == numero and (forme == TOUTES_FORMES or e[2] == forme)]


def perimetre(regle: dict) -> str:
    """Portée d'une règle (§15, D36) : « partout » par défaut."""
    return regle.get("perimetre") or PARTOUT


def _priorite(regle: dict) -> tuple[bool, bool]:
    # une forme précise l'emporte sur « toutes formes », une portée restreinte sur « partout »
    return (regle["forme"] != TOUTES_FORMES, perimetre(regle) != PARTOUT)


def regle_applicable(regles: list[dict], signature: str, forme: str, perimetres: list[str] | tuple[str, ...] = (PARTOUT,)) -> dict | None:
    """Règle qui s'applique à un élément de cette signature et de cette forme, situé dans ces portées."""
    candidates = [
        r for r in regles if r["signature"] == signature and r["forme"] in (forme, TOUTES_FORMES) and perimetre(r) in perimetres
    ]
    return max(candidates, key=_priorite) if candidates else None


def membres(donnees: dict, regle: dict, planche: int, bande=None) -> list[int]:
    """Éléments d'une règle sur une planche : sa famille, dans sa portée, sans les éléments retirés. Une règle
    restreinte à l'enveloppe ou à l'intérieur ne s'applique pas sur un plan sans lignes tracées."""
    indices = famille(donnees, regle["signature"], regle["forme"])
    if perimetre(regle) != PARTOUT:
        indices = bande.filtrer(donnees, indices, perimetre(regle)) if bande is not None else []
    exclus = {e["element"] for e in regle.get("exclusions", []) if e["planche"] == planche}
    return [i for i in indices if i not in exclus]


def attribuer(donnees: dict, regles: list[dict], planche: int, ponctuels: list[dict] = (), bande=None) -> dict[int, dict]:
    """Élément → règle sur une planche ; une forme précise l'emporte sur « toutes formes », une portée restreinte
    sur « partout » ; un élément retiré d'une règle n'en reçoit pas la nature ; une désignation ponctuelle (un
    élément seul) prime sur tout."""
    resultat: dict[int, dict] = {}
    for regle in sorted(regles, key=_priorite):
        for index in membres(donnees, regle, planche, bande):
            resultat[index] = regle
    nombre = len(donnees["elements"])
    for ponctuel in ponctuels:
        if ponctuel["planche"] == planche and 0 <= ponctuel["element"] < nombre:
            resultat[ponctuel["element"]] = {"id": None, "nature": ponctuel["nature"], "ponctuel": True}
    return resultat


def familles_de(donnees: dict, indices: list[int]) -> list[tuple[str, str, int]]:
    """(signature, forme, nombre) des familles présentes parmi les éléments, de la plus nombreuse à la moindre ;
    un remplissage compte pour toutes ses formes."""
    comptes: dict[tuple[str, str], int] = {}
    for index in indices:
        element = donnees["elements"][index]
        forme = element[2] if element[0] == TRAIT else TOUTES_FORMES
        cle = (donnees["signatures"][element[1]], forme)
        comptes[cle] = comptes.get(cle, 0) + 1
    return sorted(((s, f, n) for (s, f), n in comptes.items()), key=lambda t: -t[2])


def dans_zone(donnees: dict, contour: list[float]) -> list[int]:
    """Éléments dont tous les points sont dans le contour (lasso : x1, y1, x2, y2…)."""
    xs, ys = contour[0::2], contour[1::2]
    gauche, droite, bas, haut = min(xs), max(xs), min(ys), max(ys)
    candidats = [
        i for i, e in enumerate(donnees["elements"]) if e[3] >= gauche and e[5] <= droite and e[4] >= bas and e[6] <= haut
    ]
    if not candidats:
        return []
    # tous les points des candidats d'un coup (lancer de rayon vectorisé : une plume de toiture en compte des centaines de milliers)
    points = [donnees["elements"][i][7] for i in candidats]
    longueurs = np.array([len(p) // 2 for p in points])
    plat = np.fromiter((v for p in points for v in p[: 2 * (len(p) // 2)]), dtype=float).reshape(-1, 2)
    px, py = plat[:, 0], plat[:, 1]
    dedans = np.zeros(len(plat), dtype=bool)
    ax, ay = np.array(xs, dtype=float), np.array(ys, dtype=float)
    bx, by = np.roll(ax, -1), np.roll(ay, -1)
    for x1, y1, x2, y2 in zip(ax, ay, bx, by):
        if y1 == y2:
            continue
        croise = (y1 > py) != (y2 > py)
        dedans ^= croise & (px < x1 + (py - y1) * (x2 - x1) / (y2 - y1))
    tous = np.logical_and.reduceat(dedans, np.concatenate(([0], np.cumsum(longueurs)[:-1])))
    return [i for i, ok in zip(candidats, tous) if ok]


def coordonnees(donnees: dict, indices: list[int], maximum: int) -> dict:
    """Coordonnées des éléments à montrer (les plus grands d'abord au-delà de `maximum`)."""
    tronque = len(indices) > maximum
    if tronque:
        elements = donnees["elements"]
        indices = sorted(indices, key=lambda i: -((elements[i][5] - elements[i][3]) + (elements[i][6] - elements[i][4])))[:maximum]
    traits, remplissages = [], []
    for index in indices:
        element = donnees["elements"][index]
        (traits if element[0] == TRAIT else remplissages).append(element[7])
    return {"traits": traits, "remplissages": remplissages, "tronque": tronque}
