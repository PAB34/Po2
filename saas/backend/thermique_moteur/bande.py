"""Enveloppe thermique d'un niveau : nu extérieur, nu intérieur et bande entre les deux (docs/thermique/
refondation-parcours-decisions.md §15, D34 à D36).

Proposition des deux lignes à partir des calques désignés (mêmes limites que les pièces) :

1. limites épaissies de la moitié de `fermeture_m` ; ce qui communique avec le bord du plan est l'**extérieur** ;
2. le reste est le bâtiment ; le bord de chaque bâtiment est son **nu extérieur** ;
3. les espaces libres du bâtiment, réunis à travers les parois intérieures (fermeture de `paroi_max_m`) et
   bouchés, donnent l'intérieur ; son bord est le **nu intérieur**.

La bande sert ensuite de filtre aux calques : un élément est « dans l'enveloppe » si tous ses points sont dans le
nu extérieur (à `TOLERANCE_M` près) et aucun à plus de `TOLERANCE_M` à l'intérieur du nu intérieur ; il est « à
l'intérieur » si tous ses points sont dans le nu intérieur (à la même tolérance).
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

from thermique_moteur.pieces import (
    RESOLUTION_M,
    Grille,
    PiecesError,
    _disque,
    _espaces,
    _rayon,
    contour,
    grille_des_elements,
    image_limites,
    simplifier,
)

FERMETURE_M = 1.0
PAROI_MAX_M = 0.6
SURFACE_MIN_M2 = 10.0
TOLERANCE_M = 0.10
PARTOUT, ENVELOPPE, INTERIEUR = "partout", "enveloppe", "interieur"
PERIMETRES = {PARTOUT: "partout", ENVELOPPE: "dans l'enveloppe", INTERIEUR: "à l'intérieur"}


def decaler(points: list[tuple[float, float]], distance: float) -> list[tuple[float, float]]:
    """Décale un contour fermé de `distance` vers l'extérieur (négatif : vers l'intérieur), angles en onglet."""
    n = len(points)
    if n < 3 or not distance:
        return points
    sens = 1.0 if _aire_signee(points) > 0 else -1.0
    resultat = []
    for k in range(n):
        (ax, ay), (bx, by), (cx, cy) = points[k - 1], points[k], points[(k + 1) % n]
        normales = []
        for (px, py), (qx, qy) in (((ax, ay), (bx, by)), ((bx, by), (cx, cy))):
            longueur = math.hypot(qx - px, qy - py) or 1.0
            # normale sortante d'un contour parcouru dans le sens `sens`
            normales.append((sens * (qy - py) / longueur, -sens * (qx - px) / longueur))
        mx, my = normales[0][0] + normales[1][0], normales[0][1] + normales[1][1]
        norme = math.hypot(mx, my)
        if norme < 1e-9:
            resultat.append((bx + normales[1][0] * distance, by + normales[1][1] * distance))
            continue
        mx, my = mx / norme, my / norme
        cosinus = max(mx * normales[1][0] + my * normales[1][1], 0.3)
        resultat.append((bx + mx * distance / cosinus, by + my * distance / cosinus))
    return resultat


def _aire_signee(points) -> float:
    return sum(points[k - 1][0] * points[k][1] - points[k][0] * points[k - 1][1] for k in range(len(points))) / 2


def _polygone(masque: np.ndarray, grille: Grille, decalage: tuple[int, int], vers_dehors: float) -> list[list[float]]:
    """Contour du masque en points PDF, décalé de `vers_dehors` pixels (le bord des pixels est à un demi-pixel de
    l'axe du trait-limite)."""
    sommets = decaler(simplifier(contour(masque), 1.0), vers_dehors)
    return [[round(v, 3) for v in grille.point(c + decalage[0], l + decalage[1])] for c, l in sommets]


def _aire(points: list[list[float]]) -> float:
    return abs(sum(points[k - 1][0] * points[k][1] - points[k][0] * points[k - 1][1] for k in range(len(points)))) / 2


def proposer(
    donnees: dict,
    indices: list[int],
    fermeture_m: float = FERMETURE_M,
    paroi_max_m: float = PAROI_MAX_M,
    surface_min: float = SURFACE_MIN_M2,
) -> list[dict]:
    """Un couple (nu extérieur, nu intérieur) par bâtiment du plan, du plus grand au plus petit."""
    grille = grille_des_elements(donnees, indices)
    etiquettes, _nombre, bord = _espaces(image_limites(donnees, indices, grille), fermeture_m)
    exterieur = np.isin(etiquettes, list(bord)) if bord else np.zeros(etiquettes.shape, dtype=bool)
    batiments, nombre = ndimage.label(~exterieur)
    marge = _rayon(paroi_max_m) + 2
    resultats = []
    for numero, (lignes, colonnes) in enumerate(ndimage.find_objects(batiments), start=1):
        # recadrage avec une marge, pour que la fermeture ne bute pas sur le bord
        l0, l1 = max(lignes.start - marge, 0), min(lignes.stop + marge, etiquettes.shape[0])
        c0, c1 = max(colonnes.start - marge, 0), min(colonnes.stop + marge, etiquettes.shape[1])
        batiment = batiments[l0:l1, c0:c1] == numero
        if batiment.sum() * grille.m2_par_pixel < surface_min:
            continue
        libre = batiment & (etiquettes[l0:l1, c0:c1] > 0)
        if not libre.any():
            continue
        interieur = ndimage.binary_fill_holes(ndimage.binary_closing(libre, structure=_disque(_rayon(paroi_max_m))))
        # le plus grand morceau d'intérieur : un bâtiment, un nu intérieur
        morceaux, n = ndimage.label(interieur)
        if n > 1:
            tailles = np.bincount(morceaux.ravel())
            tailles[0] = 0
            interieur = morceaux == int(np.argmax(tailles))
        nu_ext = _polygone(batiment, grille, (c0, l0), -0.5)
        nu_int = _polygone(interieur, grille, (c0, l0), 0.5)
        k2 = (RESOLUTION_M / grille.pas) ** 2
        resultats.append(
            {
                "nu_exterieur": nu_ext,
                "nu_interieur": nu_int,
                "aire_exterieur_m2": round(_aire(nu_ext) * k2, 2),
                "aire_interieur_m2": round(_aire(nu_int) * k2, 2),
            }
        )
    if not resultats:
        raise PiecesError(
            "Aucun bâtiment fermé : désignez les murs et les menuiseries de façade, ou augmentez la fermeture des ouvertures."
        )
    return sorted(resultats, key=lambda r: -r["aire_exterieur_m2"])


class Bande:
    """Filtre des éléments selon leur position par rapport aux deux lignes d'un niveau (points PDF)."""

    def __init__(self, nu_exterieurs: list[list[list[float]]], nu_interieurs: list[list[list[float]]], echelle: float):
        polygones = [p for p in nu_exterieurs + nu_interieurs if len(p) >= 3]
        self.vide = not nu_exterieurs or not nu_interieurs
        if self.vide:
            return
        xs = [pt[0] for p in polygones for pt in p]
        ys = [pt[1] for p in polygones for pt in p]
        self.grille = Grille(min(xs), min(ys), max(xs), max(ys), echelle)
        tolerance = max(1, int(round(TOLERANCE_M / RESOLUTION_M)))
        exterieur = self._remplir(nu_exterieurs)
        interieur = self._remplir(nu_interieurs)
        disque = _disque(tolerance)
        self.dans_exterieur = ndimage.binary_dilation(exterieur, structure=disque)
        self.coeur = ndimage.binary_erosion(interieur, structure=disque)
        self.dans_interieur = ndimage.binary_dilation(interieur, structure=disque)

    def _remplir(self, polygones: list[list[list[float]]]) -> np.ndarray:
        image, dessin = self.grille.image()
        for polygone in polygones:
            if len(polygone) >= 3:
                dessin.polygon([self.grille.pixel(x, y) for x, y in polygone], fill=1, outline=1)
        return np.array(image, dtype=bool)

    def _lire(self, masque: np.ndarray, colonnes: np.ndarray, lignes: np.ndarray) -> np.ndarray:
        dedans = (colonnes >= 0) & (colonnes < masque.shape[1]) & (lignes >= 0) & (lignes < masque.shape[0])
        valeurs = np.zeros(len(colonnes), dtype=bool)
        valeurs[dedans] = masque[lignes[dedans], colonnes[dedans]]
        return valeurs

    def filtrer(self, donnees: dict, indices: list[int], perimetre: str) -> list[int]:
        """Éléments d'`indices` situés dans le périmètre (tous si « partout », aucun sans lignes tracées)."""
        if perimetre == PARTOUT:
            return list(indices)
        if self.vide or not indices:
            return []
        elements = donnees["elements"]
        longueurs = np.array([len(elements[i][7]) // 2 for i in indices])
        coords = np.fromiter((v for i in indices for v in elements[i][7][: 2 * (len(elements[i][7]) // 2)]), dtype=float).reshape(-1, 2)
        colonnes = ((coords[:, 0] - self.grille.ox) / self.grille.pas).astype(np.int64)
        lignes = ((coords[:, 1] - self.grille.oy) / self.grille.pas).astype(np.int64)
        debuts = np.concatenate(([0], np.cumsum(longueurs)[:-1]))
        if perimetre == ENVELOPPE:
            dans_ext = np.logical_and.reduceat(self._lire(self.dans_exterieur, colonnes, lignes), debuts)
            au_coeur = np.logical_or.reduceat(self._lire(self.coeur, colonnes, lignes), debuts)
            garde = dans_ext & ~au_coeur
        elif perimetre == INTERIEUR:
            garde = np.logical_and.reduceat(self._lire(self.dans_interieur, colonnes, lignes), debuts)
        else:
            raise PiecesError("Portée inconnue.")
        return [i for i, ok in zip(indices, garde) if ok]

    def positions(self, donnees: dict, index: int) -> list[str]:
        """Portées qui s'appliquent à un élément."""
        return [PARTOUT] + [p for p in (ENVELOPPE, INTERIEUR) if self.filtrer(donnees, [index], p)]
