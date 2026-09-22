"""Contrôle du relevé de l'enveloppe par l'image (lot A2 de chaine-analyse-plan-raster.md).

Indépendamment de l'agent, deux indices sont repérés sur les bandes redressées, tous les 5 cm le long de
l'enveloppe :

- les **alvéoles d'isolant** : petites zones blanches cernées de gris (fond de voile, traits de la hachure),
  jamais de noir (une lettre ou un meuble est cerné de noir), groupées par trois au moins ;
- le **béton** : remplissage gris plein d'au moins 10 cm d'épaisseur dans la bande.

Ils sont comparés au relevé : isolant vu et compté, vu mais non compté, compté mais non vu ; part du linéaire de
chaque composant confirmée par l'image. Pixels seuls, aucun vecteur PDF.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from app.services import thermique_parcours_enveloppe as env

PAS_M = 0.05
BLANC = 225  # une alvéole : pixels plus clairs que ce seuil
GRIS_BORD = (120, 215)  # bordure d'une alvéole : gris (fond de voile, traits de hachure)
GRIS_BETON = (138, 168)  # remplissage gris plein d'un voile
NOIR = 70
PROFONDEUR_CM = (-92, 15)  # profondeurs où une alvéole est cherchée (0 = ligne guide, + vers l'extérieur)
VOISINS_M = 0.20  # une alvéole a au moins deux voisines à cette distance
BETON_MIN_CM = 10


def profondeurs_cm(troncon: dict[str, Any] | None) -> tuple[float, float]:
    """Profondeurs où chercher le mur : sous le 0 (guide sur la face extérieure) ou au-dessus (lecture par local)."""
    if troncon and troncon.get("ligne") == "face_interieure":
        return -15.0, 85.0
    return PROFONDEUR_CM


def cellules_isolant(bande: np.ndarray, px_par_m_bande: float,
                     troncon: dict[str, Any] | None = None) -> list[tuple[float, float, int, int]]:
    """Alvéoles d'isolant d'une bande redressée : (x, y, largeur, hauteur) en pixels de la bande."""
    blanc = bande >= BLANC
    etiquettes, nombre = ndimage.label(blanc)
    if nombre == 0:
        return []
    boites = ndimage.find_objects(etiquettes)
    aires = ndimage.sum(blanc, etiquettes, index=np.arange(1, nombre + 1))
    haut_bande = (env.bande_m(troncon)[1] if troncon else env.BANDE_EXTERIEURE_M) * 100
    mini, maxi = profondeurs_cm(troncon)
    trouvees = []
    for rang, boite in enumerate(boites):
        hauteur, largeur = boite[0].stop - boite[0].start, boite[1].stop - boite[1].start
        if not (50 <= aires[rang] <= 2500 and 5 <= hauteur <= 60 and 5 <= largeur <= 70):
            continue
        masque = etiquettes[boite] == rang + 1
        y0, y1 = max(boite[0].start - 3, 0), min(boite[0].stop + 3, bande.shape[0])
        x0, x1 = max(boite[1].start - 3, 0), min(boite[1].stop + 3, bande.shape[1])
        agrandi = np.zeros((y1 - y0, x1 - x0), bool)
        agrandi[boite[0].start - y0: boite[0].stop - y0, boite[1].start - x0: boite[1].stop - x0] = masque
        bord = ndimage.binary_dilation(agrandi, iterations=3) & ~agrandi
        valeurs = bande[y0:y1, x0:x1][bord]
        if np.mean(valeurs < NOIR) > 0.15 or np.mean((valeurs > GRIS_BORD[0]) & (valeurs < GRIS_BORD[1])) < 0.5:
            continue
        cy, cx = ndimage.center_of_mass(masque)
        profondeur = haut_bande - (boite[0].start + cy) / px_par_m_bande * 100
        if not mini <= profondeur <= maxi:
            continue
        trouvees.append((boite[1].start + cx, boite[0].start + cy, largeur, hauteur))
    if not trouvees:
        return []
    points = np.array([(x, y) for x, y, _l, _h in trouvees])
    gardees = []
    for cellule in trouvees:
        distances = np.hypot(points[:, 0] - cellule[0], points[:, 1] - cellule[1])
        if ((distances > 0) & (distances < VOISINS_M * px_par_m_bande)).sum() >= 2:
            gardees.append(cellule)
    return gardees


def _element_en(elements: list[dict[str, Any]], s: float) -> dict[str, Any] | None:
    for element in elements:
        if element["debut_m"] <= s < element["fin_m"]:
            return element
    return None


def _a_isolant(element: dict[str, Any] | None) -> bool:
    return element is not None and element["type"] == "paroi" and any(
        c["nature"] == "isolant" for c in element.get("couches") or [])


def _cle(element: dict[str, Any] | None) -> str:
    if element is None:
        return "non lu"
    return element.get("composant") or element["type"]


def _suites(repere: list[tuple[str, float, str]]) -> list[dict[str, Any]]:
    """Regroupe des tranches de 5 cm contiguës (tronçon, abscisse, composant) en intervalles."""
    suites: list[dict[str, Any]] = []
    for troncon, s, cle in repere:
        if suites and suites[-1]["troncon"] == troncon and suites[-1]["composant"] == cle and s - suites[-1]["fin_m"] < PAS_M * 0.6:
            suites[-1]["fin_m"] = round(s + PAS_M / 2, 3)
        else:
            suites.append({"troncon": troncon, "debut_m": round(s - PAS_M / 2, 3), "fin_m": round(s + PAS_M / 2, 3),
                           "composant": cle})
    return [suite for suite in suites if suite["fin_m"] - suite["debut_m"] >= 0.1 - 1e-9]


def controler(page: Image.Image, manifeste: dict[str, Any], brut: dict[str, Any]) -> dict[str, Any]:
    """Bilan du contrôle par l'image d'un relevé résolu (couches des fiches reprises)."""
    brut = env.resoudre(brut)
    px_par_m = manifeste["px_par_m"]
    echelle = px_par_m * env.AGRANDISSEMENT
    par_troncon: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for element in brut["elements"]:
        par_troncon[element["troncon"]].append(element)
    decisions = {fiche["id"]: fiche.get("decision") for fiche in brut.get("catalogue", [])}
    vu_m = releve_m = commun_m = 0.0
    manques: list[tuple[str, float, str]] = []
    non_vus: list[tuple[str, float, str]] = []
    beton: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    isolant_confirme: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    cellules_par_troncon: dict[str, list[tuple[float, float, int, int]]] = {}
    for troncon in manifeste["troncons"]:
        # fenêtre du béton : de 15 cm au-dessus à 90 cm sous le 0 (guide extérieur), l'inverse en lecture par local
        exterieure = env.bande_m(troncon)[1]
        dessus, dessous = (0.85, -0.15) if troncon.get("ligne") == "face_interieure" else (0.15, -0.90)
        haut = max(0, round((exterieure - dessus) * echelle))
        bas = round((exterieure - dessous) * echelle)
        bande = np.asarray(env._bande(page, troncon, px_par_m).convert("L"))
        s0 = troncon["debut_m"] - env.RECOUVREMENT_M
        elements = sorted(par_troncon.get(troncon["id"], []), key=lambda e: e["debut_m"])
        cellules = cellules_isolant(bande, echelle, troncon)
        cellules_par_troncon[troncon["id"]] = cellules
        nombre = max(1, round((troncon["fin_m"] - troncon["debut_m"]) / PAS_M))
        vu = np.zeros(nombre, bool)
        for x, _y, largeur, _h in cellules:
            s = s0 + x / echelle
            demi = max(largeur / echelle / 2, PAS_M / 2) + 0.02
            for k in range(nombre):
                if abs(troncon["debut_m"] + (k + 0.5) * PAS_M - s) <= demi:
                    vu[k] = True
        gris = (bande > GRIS_BETON[0]) & (bande < GRIS_BETON[1])
        for k in range(nombre):
            s = troncon["debut_m"] + (k + 0.5) * PAS_M
            element = _element_en(elements, s)
            cle = _cle(element)
            compte = _a_isolant(element)
            vu_m += PAS_M * vu[k]
            releve_m += PAS_M * compte
            commun_m += PAS_M * (vu[k] and compte)
            if vu[k] and not compte:
                manques.append((troncon["id"], s, cle))
            if compte and not vu[k]:
                non_vus.append((troncon["id"], s, cle))
            if compte:
                isolant_confirme[cle][0] += PAS_M * vu[k]
                isolant_confirme[cle][1] += PAS_M
            x = int((s - s0) * echelle)
            colonne = gris[haut:bas, max(x - 3, 0): x + 4].mean(axis=1) > 0.5
            beton[cle][0] += PAS_M * (colonne.sum() / echelle * 100 >= BETON_MIN_CM)
            beton[cle][1] += PAS_M
    types = {(_cle(e)): e["type"] for e in brut["elements"]}
    composants = []
    for cle, (avec, total) in sorted(beton.items(), key=lambda item: -item[1][1]):
        genre = types.get(cle, "")
        ligne = {"composant": cle, "type": genre, "decision": decisions.get(cle, ""), "lineaire_m": round(total, 2),
                 "beton_pct": round(100 * avec / total, 1) if total else 0.0}
        if cle in isolant_confirme and isolant_confirme[cle][1]:
            ligne["isolant_pct"] = round(100 * isolant_confirme[cle][0] / isolant_confirme[cle][1], 1)
        # ce que l'image doit montrer pour confirmer : béton sous une paroi, pas de béton sous une baie
        if genre == "paroi":
            ligne["confirme_pct"] = ligne["beton_pct"]
        elif genre == "menuiserie":
            ligne["confirme_pct"] = round(100 - ligne["beton_pct"], 1)
        composants.append(ligne)
    return {
        "isolant": {"vu_m": round(vu_m, 2), "releve_m": round(releve_m, 2), "commun_m": round(commun_m, 2),
                    "taux_compte_pct": round(100 * commun_m / vu_m, 1) if vu_m else None,
                    "manques": _suites(manques), "non_vus": _suites(non_vus)},
        "composants": composants,
        "cellules": {k: [[round(x, 1), round(y, 1), w, h] for x, y, w, h in v] for k, v in cellules_par_troncon.items()},
    }


def troncons_a_montrer(bilan: dict[str, Any], nombre: int = 6) -> list[str]:
    """Tronçons où l'écart entre image et relevé est le plus grand."""
    ecarts: dict[str, float] = defaultdict(float)
    for suite in bilan["isolant"]["manques"] + bilan["isolant"]["non_vus"]:
        ecarts[suite["troncon"]] += suite["fin_m"] - suite["debut_m"]
    return [t for t, _ in sorted(ecarts.items(), key=lambda item: -item[1])[:nombre]]


def planche_controle(page: Image.Image, manifeste: dict[str, Any], brut: dict[str, Any], bilan: dict[str, Any],
                     troncons: list[str], chemin: Path) -> Path | None:
    """Bandes des tronçons choisis : alvéoles vertes si comptées, rouges sinon ; isolant compté en jaune dessous."""
    brut = env.resoudre(brut)
    px_par_m = manifeste["px_par_m"]
    echelle = px_par_m * env.AGRANDISSEMENT
    police = env._police(15)
    images = []
    for troncon in manifeste["troncons"]:
        if troncon["id"] not in troncons:
            continue
        bande = env._bande(page, troncon, px_par_m)
        image = env._graduer(bande, troncon, px_par_m).convert("RGBA")
        calque = Image.new("RGBA", image.size, (0, 0, 0, 0))
        dessin = ImageDraw.Draw(calque)
        s0 = troncon["debut_m"] - env.RECOUVREMENT_M
        elements = sorted((e for e in brut["elements"] if e["troncon"] == troncon["id"]), key=lambda e: e["debut_m"])
        bas = env.MARGE_HAUT + bande.height

        def x_de(s: float) -> float:
            return env.MARGE_GAUCHE + (s - s0) * echelle

        for element in elements:
            if _a_isolant(element):
                dessin.rectangle((x_de(element["debut_m"]), bas + 2, x_de(element["fin_m"]), bas + 12), fill=(245, 184, 0, 255))
            dessin.line((x_de(element["debut_m"]), bas, x_de(element["debut_m"]), bas + 30), fill=(23, 32, 51, 255))
            dessin.text((x_de(element["debut_m"]) + 3, bas + 14), _cle(element), fill=(23, 32, 51, 255), font=police)
        for x, y, largeur, hauteur in bilan["cellules"].get(troncon["id"], []):
            s = s0 + x / echelle
            if not troncon["debut_m"] <= s < troncon["fin_m"]:
                couleur = (150, 150, 150, 200)
            elif _a_isolant(_element_en(elements, s)):
                couleur = (43, 138, 62, 255)
            else:
                couleur = (224, 49, 49, 255)
            cx, cy = env.MARGE_GAUCHE + x, env.MARGE_HAUT + y
            dessin.rectangle((cx - largeur / 2, cy - hauteur / 2, cx + largeur / 2, cy + hauteur / 2), outline=couleur, width=3)
        images.append(Image.alpha_composite(image, calque).convert("RGB"))
    if not images:
        return None
    largeur = max(image.width for image in images)
    legende = Image.new("RGB", (largeur, 50), "white")
    dessin = ImageDraw.Draw(legende)
    grande = env._police(18)
    dessin.rectangle((10, 15, 34, 37), outline=(43, 138, 62), width=3)
    dessin.text((42, 15), "alvéole vue et comptée", fill="#172033", font=grande)
    dessin.rectangle((300, 15, 324, 37), outline=(224, 49, 49), width=3)
    dessin.text((332, 15), "alvéole vue, non comptée", fill="#172033", font=grande)
    dessin.rectangle((620, 20, 660, 30), fill=(245, 184, 0))
    dessin.text((668, 15), "isolant compté par l'agent (sous la bande)", fill="#172033", font=grande)
    planche = Image.new("RGB", (largeur, 50 + sum(image.height + 16 for image in images)), "#e9ecef")
    planche.paste(legende, (0, 0))
    y = 50
    for image in images:
        planche.paste(image, (0, y))
        y += image.height + 16
    planche.save(chemin, optimize=True)
    return chemin
