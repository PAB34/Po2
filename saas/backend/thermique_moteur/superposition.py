"""Superposition des niveaux — étape E2 (docs/thermique/refondation-parcours-decisions.md §12).

Les plans d'un même projet sont souvent exportés depuis la même maquette : ils tombent déjà l'un sur l'autre dans
le cadre du PDF, ou à une translation près. On cherche cette translation en comparant **tout le dessin** des deux
planches (sonde du 2026-09-17 : plus fiable que les seuls murs désignés, qui sont des hachures, et que la toiture,
faite surtout de textures) :

1. chaque planche devient une image de ses traits, au point PDF près ;
2. la corrélation des deux images (transformée de Fourier) propose quelques translations ;
3. chacune est notée par la part des traits du niveau qui retombent sur un trait de la référence (à 1 pt près),
   la translation nulle comprise, puis la meilleure est affinée à ±3 pt.

Projet de production : R+1, R+2, R-1 et TOITURE à 0 pt du RDC ; R+3 à (74, −40) pt, vérifié à l'œil.
"""
from __future__ import annotations

import numpy as np
from scipy import fft, ndimage

from thermique_moteur.calques import TRAIT

# Part des traits retrouvés en dessous de laquelle la superposition est douteuse.
SCORE_MIN = 0.2
# Gain minimal sur la translation nulle pour proposer un décalage.
GAIN_MIN = 0.05
PICS = 20
AFFINAGE_PT = 3
TAILLE_MAX_PT = 6000


def image_traits(donnees: dict, largeur: int, hauteur: int) -> np.ndarray:
    """Image booléenne (une case par point PDF) des traits d'une planche."""
    segments = []
    for element in donnees["elements"]:
        if element[0] != TRAIT:
            continue
        coords = element[7]
        for k in range(0, len(coords) - 2, 2):
            segments.append(coords[k : k + 4])
    image = np.zeros((hauteur, largeur), dtype=bool)
    if not segments:
        return image
    s = np.asarray(segments, dtype=np.float64)
    pas = (np.maximum(np.abs(s[:, 2] - s[:, 0]), np.abs(s[:, 3] - s[:, 1])) + 1).astype(np.int64)
    rang = np.repeat(np.arange(len(s)), pas)
    debut = np.repeat(np.cumsum(pas) - pas, pas)
    t = (np.arange(len(rang)) - debut) / np.maximum(pas[rang] - 1, 1)
    x = (s[rang, 0] + (s[rang, 2] - s[rang, 0]) * t).astype(np.int64)
    y = (s[rang, 1] + (s[rang, 3] - s[rang, 1]) * t).astype(np.int64)
    garde = (x >= 0) & (x < largeur) & (y >= 0) & (y < hauteur)
    image[y[garde], x[garde]] = True
    return image


def _score(points: tuple[np.ndarray, np.ndarray], reference: np.ndarray, dx: int, dy: int) -> float:
    ys, xs = points
    if len(ys) == 0:
        return 0.0
    y, x = ys + dy, xs + dx
    garde = (y >= 0) & (y < reference.shape[0]) & (x >= 0) & (x < reference.shape[1])
    return float(reference[y[garde], x[garde]].sum()) / len(ys)


def recaler(image: np.ndarray, reference: np.ndarray) -> dict:
    """Translation (dx, dy), en points, qui pose `image` sur `reference` : point du niveau + (dx, dy) = point de la
    référence. Les deux images ont la même taille."""
    hauteur, largeur = image.shape
    a = fft.rfft2(image.astype(np.float32), workers=-1)
    b = fft.rfft2(reference.astype(np.float32), workers=-1)
    correlation = fft.irfft2(b * np.conj(a), s=image.shape, workers=-1)
    candidats = {(0, 0)}
    for indice in np.argpartition(correlation.ravel(), -PICS)[-PICS:]:
        dy, dx = np.unravel_index(indice, correlation.shape)
        candidats.add((int(dx - largeur if dx > largeur // 2 else dx), int(dy - hauteur if dy > hauteur // 2 else dy)))
    dilatee = ndimage.binary_dilation(reference, iterations=1)
    points = np.nonzero(image)
    meilleur = max(sorted(candidats), key=lambda d: _score(points, dilatee, *d))
    voisins = [
        (meilleur[0] + i, meilleur[1] + j) for i in range(-AFFINAGE_PT, AFFINAGE_PT + 1) for j in range(-AFFINAGE_PT, AFFINAGE_PT + 1)
    ]
    # à score égal (tolérance de 1 pt), le recouvrement exact départage, puis le plus petit déplacement
    meilleur = max(
        voisins,
        key=lambda d: (round(_score(points, dilatee, *d), 3), round(_score(points, reference, *d), 3), -abs(d[0]) - abs(d[1])),
    )
    score = _score(points, dilatee, *meilleur)
    score_zero = _score(points, dilatee, 0, 0)
    if score < SCORE_MIN:
        etat = "incertain"
    elif abs(meilleur[0]) <= 1 and abs(meilleur[1]) <= 1:
        etat = "superpose"
    elif score - score_zero >= GAIN_MIN:
        etat = "decale"
    else:
        etat = "incertain"
    return {"dx": meilleur[0], "dy": meilleur[1], "score": round(score, 3), "score_zero": round(score_zero, 3), "etat": etat}
