"""Types de murs le long du contour (lot M4a) : épaisseur et position de l'isolant, côté par côté.

Méthode validée sur le projet d'essai (2026-09-14, voir docs/thermique/parois-menuiseries-pt-decisions.md) :

1. **corps de mur** = aplats gris (maçonnerie) + traits épais (faces) + zones denses en petits traits
   (motif d'isolant), refermés de 2 cm ; les vides étroits entre deux faces (murs dessinés en simple
   contour) sont comblés ;
2. tous les 5 cm le long d'un côté, un **rayon perpendiculaire** traverse le corps de mur le plus proche
   du contour (±50 cm) : épaisseur = longueur traversée − largeur d'un trait de bordure ;
3. l'isolant est situé par la position moyenne du motif d'isolant dans l'épaisseur ;
4. les mesures sont **lissées** en tronçons homogènes (± 4 cm, tronçons de moins de 50 cm absorbés) ;
5. chaque côté reçoit son épaisseur dominante ; les côtés d'épaisseur voisine (± 3 cm) forment un
   **type de mur**, proposé au thermicien.

Projet d'essai : niveau −1 un seul type (32 cm sur 119 m) ; niveau 2 mur de 42 cm à isolant réparti sur
35 m ; les parties vitrées restent « non lues ».
"""
from __future__ import annotations

import math
from collections import Counter

import numpy as np

from thermique_moteur.metre import pt_en_m

PX_PAR_PT = 3.0
PAS_M = 0.05
PORTEE_RAYON_M = 1.2
ECART_CONTOUR_M = 0.5
TROU_DANS_MUR_M = 0.08
EPAISSEUR_MIN_M = 0.05
# Au-delà, ce sont des couches accolées à autre chose (profondeur de redents, jardinières) : non lu.
EPAISSEUR_MAX_M = 0.6
TRONCON_MIN_M = 0.5
TOLERANCE_TRONCON_M = 0.04
TOLERANCE_TYPE_M = 0.03
LUMINANCE_PLEIN = (96, 176)
LUMINANCE_HACHURE = (64, 220)
DENSITE_ISOLANT = 0.08
ISOLANTS = {"interieur": "isolant intérieur", "exterieur": "isolant extérieur", "reparti": "isolant réparti"}


def _masques(traits: list, aplats: list, cadre: tuple, seuil: float, m: float):
    from PIL import Image, ImageDraw
    from scipy import ndimage

    x0, y0, x1, y1 = cadre
    largeur = int((x1 - x0) * PX_PAR_PT) + 1
    hauteur = int((y1 - y0) * PX_PAR_PT) + 1

    def px(x, y):
        return ((x - x0) * PX_PAR_PT, (y1 - y) * PX_PAR_PT)

    def dedans(x, y):
        return x0 <= x <= x1 and y0 <= y <= y1

    image_plein = Image.new("1", (largeur, hauteur), 0)
    image_bords = Image.new("1", (largeur, hauteur), 0)
    image_hachures = Image.new("1", (largeur, hauteur), 0)
    d_plein, d_bords, d_hachures = ImageDraw.Draw(image_plein), ImageDraw.Draw(image_bords), ImageDraw.Draw(image_hachures)
    for contour, luminance in aplats:
        if len(contour) >= 3 and LUMINANCE_PLEIN[0] <= luminance <= LUMINANCE_PLEIN[1] and dedans(*contour[0]):
            d_plein.polygon([px(*q) for q in contour], fill=1)
    for t in traits:
        xa, ya, xb, yb, epaisseur = t[:5]
        luminance = t[5] if len(t) > 5 else 0
        if not (dedans(xa, ya) or dedans(xb, yb)):
            continue
        if epaisseur >= seuil - 1e-6:
            d_bords.line([px(xa, ya), px(xb, yb)], fill=1, width=max(2, int(round(epaisseur * PX_PAR_PT))))
        elif LUMINANCE_HACHURE[0] < luminance <= LUMINANCE_HACHURE[1] and epaisseur <= 0.6 and math.hypot(xb - xa, yb - ya) <= 0.4 * m:
            d_hachures.line([px(xa, ya), px(xb, yb)], fill=1, width=1)

    plein = np.array(image_plein, dtype=bool)
    bords = np.array(image_bords, dtype=bool)
    hachures = np.array(image_hachures, dtype=bool)
    r = m * PX_PAR_PT
    densite = ndimage.uniform_filter(hachures.astype(np.float32), size=max(3, int(0.06 * r)))
    isolant = densite > DENSITE_ISOLANT
    corps = ndimage.binary_closing(plein | bords | isolant, structure=np.ones((3, 3), dtype=bool), iterations=max(1, int(0.02 * r)))
    trous, nombre = ndimage.label(ndimage.binary_fill_holes(corps) & ~corps)
    if nombre:
        aires = np.bincount(trous.ravel(), minlength=nombre + 1)[1:]
        contact = trous * (ndimage.binary_dilation(corps) & (trous > 0))
        perimetres = np.bincount(contact.ravel(), minlength=nombre + 1)[1:]
        largeurs = 2 * aires / np.maximum(perimetres, 1) / r
        etroits = np.nonzero((largeurs < 0.6) & (aires < 60 * r * r))[0] + 1
        corps |= np.isin(trous, etroits)
    return corps, plein, isolant, (x0, y1, largeur, hauteur)


def _lisser(echantillons: list[tuple[float, float | None, str | None]], longueur: float, m: float) -> list[dict]:
    """Tronçons homogènes à partir des mesures (position, épaisseur, isolant)."""
    groupes: list[list] = []
    for mesure in echantillons:
        if groupes:
            dernier = groupes[-1]
            meme_nature = (mesure[1] is None) == (dernier[0][1] is None)
            if meme_nature and (mesure[1] is None or abs(mesure[1] - float(np.median([x[1] for x in dernier]))) <= TOLERANCE_TRONCON_M):
                dernier.append(mesure)
                continue
        groupes.append([mesure])
    pas = longueur / max(1, len(echantillons))
    fusionnes: list[list] = []
    for groupe in groupes:
        if fusionnes and len(groupe) * pas < TRONCON_MIN_M * m:
            fusionnes[-1].extend(groupe)
        else:
            fusionnes.append(groupe)
    if len(fusionnes) > 1 and len(fusionnes[0]) * pas < TRONCON_MIN_M * m:
        fusionnes[1] = fusionnes[0] + fusionnes[1]
        fusionnes.pop(0)
    troncons: list[dict] = []
    for groupe in fusionnes:
        lues = [x for x in groupe if x[1] is not None]
        if len(lues) >= 0.5 * len(groupe):
            epaisseur = round(float(np.median([x[1] for x in lues])) * 50) / 50
            isolants = Counter(x[2] for x in lues if x[2])
            isolant = isolants.most_common(1)[0][0] if isolants and isolants.most_common(1)[0][1] >= 0.5 * len(lues) else None
        else:
            epaisseur, isolant = None, None
        debut, fin = max(0.0, groupe[0][0] - pas / 2) / m, min(longueur, groupe[-1][0] + pas / 2) / m
        if troncons and troncons[-1]["epaisseur_m"] == epaisseur and troncons[-1]["isolant"] == isolant:
            troncons[-1]["fin_m"] = round(fin, 3)
        else:
            troncons.append({"debut_m": round(debut, 3), "fin_m": round(fin, 3), "epaisseur_m": epaisseur, "isolant": isolant})
    return troncons


def analyser_murs(traits: list, aplats: list, points: list, seuil: float, echelle: float) -> dict:
    """Épaisseur de mur et position de l'isolant pour chaque côté du contour (points en pt PDF)."""
    m = 1.0 / pt_en_m(echelle)
    n = len(points)
    if n < 3:
        return {"cotes": []}
    aire = sum(points[i - 1][0] * points[i][1] - points[i][0] * points[i - 1][1] for i in range(n))
    marge = (PORTEE_RAYON_M + 0.5) * m
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    corps, plein, isolant, (x0, y1, largeur, hauteur) = _masques(
        traits, aplats, (min(xs) - marge, min(ys) - marge, max(xs) + marge, max(ys) + marge), seuil, m
    )
    # Largeur du trait de bordure tel qu'il est dessiné dans le masque (arrondi au pixel).
    trait_bordure_m = max(2, int(round(seuil * PX_PAR_PT))) / PX_PAR_PT * pt_en_m(echelle)
    pas_rayon = 1.0 / PX_PAR_PT
    distances = np.arange(-PORTEE_RAYON_M * m, PORTEE_RAYON_M * m, pas_rayon)
    zero = int(np.searchsorted(distances, 0.0))
    trou = TROU_DANS_MUR_M * m / pas_rayon
    ecart = ECART_CONTOUR_M * m / pas_rayon

    cotes = []
    for i in range(n):
        p, q = points[i], points[(i + 1) % n]
        longueur = math.hypot(q[0] - p[0], q[1] - p[1])
        if longueur < 0.05 * m:
            cotes.append({"troncons": [], "epaisseur_m": None, "isolant": None, "part_lue": 0.0})
            continue
        ux, uy = (q[0] - p[0]) / longueur, (q[1] - p[1]) / longueur
        ex, ey = (uy, -ux) if aire > 0 else (-uy, ux)  # vers l'extérieur
        nombre = max(1, int(longueur / (PAS_M * m)))
        mesures = []
        for k in range(nombre):
            s = (k + 0.5) * longueur / nombre
            bx, by = p[0] + ux * s, p[1] + uy * s
            X = ((bx + ex * distances - x0) * PX_PAR_PT).astype(int)
            Y = ((y1 - (by + ey * distances)) * PX_PAR_PT).astype(int)
            valides = (X >= 0) & (X < largeur) & (Y >= 0) & (Y < hauteur)
            dans_corps = np.zeros(len(distances), dtype=bool)
            dans_corps[valides] = corps[Y[valides], X[valides]]
            indices = np.nonzero(dans_corps)[0]
            if len(indices) == 0:
                mesures.append((s, None, None))
                continue
            coupures = np.nonzero(np.diff(indices) > trou + 1)[0]
            debuts = np.concatenate(([indices[0]], indices[coupures + 1]))
            fins = np.concatenate((indices[coupures], [indices[-1]]))
            proches = [(d, f) for d, f in zip(debuts, fins) if d <= zero <= f or min(abs(d - zero), abs(f - zero)) <= ecart]
            if not proches:
                mesures.append((s, None, None))
                continue
            debut, fin = min(proches, key=lambda plage: 0 if plage[0] <= zero <= plage[1] else min(abs(plage[0] - zero), abs(plage[1] - zero)))
            epaisseur = (fin - debut + 1) * pas_rayon / m - trait_bordure_m  # pixels extrêmes compris
            if not EPAISSEUR_MIN_M <= epaisseur <= EPAISSEUR_MAX_M:
                mesures.append((s, None, None))
                continue
            tranche = slice(debut, fin + 1)
            iso = np.zeros(len(distances), dtype=bool)
            iso[valides] = isolant[Y[valides], X[valides]] & ~plein[Y[valides], X[valides]]
            positions = np.nonzero(iso[tranche])[0]
            if len(positions) < 0.1 * (fin - debut + 1):
                position = None
            else:
                relatif = float(positions.mean()) / max(1, fin - debut)  # 0 = côté intérieur, 1 = côté extérieur
                position = "interieur" if relatif < 0.4 else ("exterieur" if relatif > 0.6 else "reparti")
            mesures.append((s, epaisseur, position))
        troncons = _lisser(mesures, longueur, m)
        lus = [t for t in troncons if t["epaisseur_m"] is not None]
        longueur_m = longueur / m
        if lus:
            par_epaisseur = Counter()
            for t in lus:
                par_epaisseur[t["epaisseur_m"]] += t["fin_m"] - t["debut_m"]
            dominante = par_epaisseur.most_common(1)[0][0]
            voisins = [t for t in lus if abs(t["epaisseur_m"] - dominante) <= TOLERANCE_TYPE_M]
            isolants = Counter()
            for t in voisins:
                isolants[t["isolant"]] += t["fin_m"] - t["debut_m"]
            isolant_dominant, part = isolants.most_common(1)[0]
            total_voisins = sum(isolants.values())
            cotes.append(
                {
                    "troncons": troncons,
                    "epaisseur_m": dominante,
                    "isolant": isolant_dominant if isolant_dominant and part >= 0.6 * total_voisins else None,
                    "part_lue": round(min(1.0, sum(t["fin_m"] - t["debut_m"] for t in lus) / longueur_m), 2),
                }
            )
        else:
            cotes.append({"troncons": troncons, "epaisseur_m": None, "isolant": None, "part_lue": 0.0})
    return {"cotes": cotes}


def types_de_murs(cotes: list[dict], longueurs_m: list[float]) -> list[dict]:
    """Regroupe les côtés par épaisseur de mur lue (± 3 cm) : un type proposé par groupe."""
    items = []
    for index, cote in enumerate(cotes):
        mur = cote.get("mur") or {}
        if mur.get("epaisseur_m") and index < len(longueurs_m):
            items.append((mur["epaisseur_m"], index, mur.get("isolant"), longueurs_m[index] * (mur.get("part_lue") or 1.0)))
    items.sort()
    groupes: list[list] = []
    for item in items:
        if groupes and item[0] - groupes[-1][0][0] <= TOLERANCE_TYPE_M + 1e-9:
            groupes[-1].append(item)
        else:
            groupes.append([item])
    types = []
    for groupe in groupes:
        longueur = sum(item[3] for item in groupe)
        epaisseur = sum(item[0] * item[3] for item in groupe) / longueur if longueur else groupe[0][0]
        isolants = Counter()
        for item in groupe:
            isolants[item[2]] += item[3]
        isolant, part = isolants.most_common(1)[0]
        types.append(
            {
                "epaisseur_m": round(epaisseur, 2),
                "isolant": isolant if isolant and part >= 0.6 * longueur else None,
                "longueur_m": round(longueur, 2),
                "cotes": [item[1] for item in groupe],
                "composants": sorted({cotes[item[1]].get("composant_id") for item in groupe if cotes[item[1]].get("composant_id")}),
            }
        )
    return sorted(types, key=lambda t: -t["longueur_m"])
