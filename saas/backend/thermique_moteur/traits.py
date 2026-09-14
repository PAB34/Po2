"""Traits vectoriels d'une planche PDF, pour aimanter le tracé du métré (lot M1).

Lecture par pdfium des chemins **tracés** (les remplissages — hachures pleines, textes
vectorisés — sont ignorés), transformations comprises, y compris dans les objets de
formulaire imbriqués. Mesuré sur le niveau 0 du projet d'essai (2026-09-14) : 224 015
segments lus en 0,9 s ; les faces de murs sont tracées en 0,96 et 1,56 pt, le reste en
0,48 pt ou moins. Voir docs/thermique/metre-plans-decisions.md.
"""
from __future__ import annotations

import ctypes
import math
from collections import defaultdict
from pathlib import Path

# Segments plus courts ignorés (points, pointillés serrés).
LONGUEUR_MIN_PT = 0.5
# Au-delà, on garde les plus longs : l'aimantation reste fluide dans le navigateur.
MAX_SEGMENTS = 30000
PROFONDEUR_MAX = 15

Trait = tuple[float, float, float, float, float]  # x1, y1, x2, y2, largeur (pt)
Matrice = tuple[float, float, float, float, float, float]


def _composer(enfant: Matrice, parent: Matrice) -> Matrice:
    """Applique `enfant` puis `parent` (convention PDF : x' = a·x + c·y + e)."""
    a, b, c, d, e, f = enfant
    pa, pb, pc, pd, pe, pf = parent
    return (
        a * pa + b * pc,
        a * pb + b * pd,
        c * pa + d * pc,
        c * pb + d * pd,
        e * pa + f * pc + pe,
        e * pb + f * pd + pf,
    )


def _parcourir(brut, objets: list, parent: Matrice, sortie: list[Trait], profondeur: int) -> None:
    matrice = brut.FS_MATRIX()
    x, y = ctypes.c_float(), ctypes.c_float()
    largeur = ctypes.c_float()
    remplissage, trace = ctypes.c_int(), ctypes.c_int()
    for objet in objets:
        genre = brut.FPDFPageObj_GetType(objet)
        if not brut.FPDFPageObj_GetMatrix(objet, ctypes.byref(matrice)):
            continue
        m = _composer((matrice.a, matrice.b, matrice.c, matrice.d, matrice.e, matrice.f), parent)
        if genre == brut.FPDF_PAGEOBJ_FORM:
            if profondeur < PROFONDEUR_MAX:
                enfants = [brut.FPDFFormObj_GetObject(objet, i) for i in range(brut.FPDFFormObj_CountObjects(objet))]
                _parcourir(brut, enfants, m, sortie, profondeur + 1)
            continue
        if genre != brut.FPDF_PAGEOBJ_PATH:
            continue
        if not brut.FPDFPath_GetDrawMode(objet, ctypes.byref(remplissage), ctypes.byref(trace)) or not trace.value:
            continue
        brut.FPDFPageObj_GetStrokeWidth(objet, ctypes.byref(largeur))
        a, b, c, d, e, f = m
        epaisseur = round(largeur.value * math.sqrt(abs(a * d - b * c)), 2)
        precedent = depart = None
        bezier = 0
        for i in range(brut.FPDFPath_CountSegments(objet)):
            segment = brut.FPDFPath_GetPathSegment(objet, i)
            brut.FPDFPathSegment_GetPoint(segment, ctypes.byref(x), ctypes.byref(y))
            point = (a * x.value + c * y.value + e, b * x.value + d * y.value + f)
            nature = brut.FPDFPathSegment_GetType(segment)
            if nature == brut.FPDF_SEGMENT_MOVETO:
                precedent = depart = point
                bezier = 0
            else:
                if nature == brut.FPDF_SEGMENT_BEZIERTO:
                    # Courbe (arc de porte…) : trois points par morceau, on garde la corde.
                    bezier += 1
                    if bezier % 3:
                        continue
                if precedent is not None:
                    sortie.append((*precedent, *point, epaisseur))
                precedent = point
            if brut.FPDFPathSegment_GetClose(segment) and depart is not None and precedent not in (None, depart):
                sortie.append((*precedent, *depart, epaisseur))
                precedent = depart


def lire_traits(pdf_path: Path | str, page_index: int) -> list[Trait]:
    import pypdfium2 as pdfium
    import pypdfium2.raw as brut

    document = pdfium.PdfDocument(str(pdf_path))
    try:
        page = document[page_index]
        objets = [brut.FPDFPage_GetObject(page.raw, i) for i in range(brut.FPDFPage_CountObjects(page.raw))]
        sortie: list[Trait] = []
        _parcourir(brut, objets, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), sortie, 0)
        page.close()
    finally:
        document.close()
    return sortie


def classes_epaisseur(traits: list[Trait]) -> list[dict]:
    """Nombre et longueur cumulée des traits par épaisseur, de la plus épaisse à la plus fine."""
    classes: dict[float, list[float]] = defaultdict(lambda: [0, 0.0])
    for x1, y1, x2, y2, largeur in traits:
        classe = classes[largeur]
        classe[0] += 1
        classe[1] += math.hypot(x2 - x1, y2 - y1)
    return [
        {"largeur": largeur, "nombre": int(nombre), "longueur_pt": round(longueur, 1)}
        for largeur, (nombre, longueur) in sorted(classes.items(), reverse=True)
    ]


def seuil_propose(classes: list[dict]) -> float | None:
    """Épaisseur minimale des traits d'aimantation : les classes nettement plus épaisses que la
    plume médiane (pondérée par la longueur) — les faces de murs coupés sur un plan d'architecte."""
    if not classes:
        return None
    croissantes = sorted(classes, key=lambda classe: classe["largeur"])
    total = sum(classe["longueur_pt"] for classe in croissantes)
    mediane = croissantes[-1]["largeur"]
    cumul = 0.0
    for classe in croissantes:
        cumul += classe["longueur_pt"]
        if cumul >= total / 2:
            mediane = classe["largeur"]
            break
    epaisses = [classe["largeur"] for classe in croissantes if classe["largeur"] >= 1.9 * max(mediane, 0.05)]
    return epaisses[0] if epaisses else croissantes[-1]["largeur"]


def extraire_aimantation(pdf_path: Path | str, page_index: int, seuil: float | None = None) -> dict:
    traits = lire_traits(pdf_path, page_index)
    classes = classes_epaisseur(traits)
    propose = seuil_propose(classes)
    retenu = propose if seuil is None else seuil
    retenus = [
        trait
        for trait in traits
        if retenu is not None
        and trait[4] >= retenu - 1e-6
        and math.hypot(trait[2] - trait[0], trait[3] - trait[1]) >= LONGUEUR_MIN_PT
    ]
    tronque = len(retenus) > MAX_SEGMENTS
    if tronque:
        retenus.sort(key=lambda trait: math.hypot(trait[2] - trait[0], trait[3] - trait[1]), reverse=True)
        retenus = retenus[:MAX_SEGMENTS]
    return {
        "classes": classes,
        "seuil_propose": propose,
        "seuil": retenu,
        "segments": [[round(v, 2) for v in trait[:4]] for trait in retenus],
        "tronque": tronque,
        "nombre_total": len(traits),
    }
