"""Locaux d'un niveau : contours de pièces recalés sur les murs et espaces libres non attribués (D26, D27).

Pixels seuls : le masque des murs vient de l'encre du plan, jamais des vecteurs du PDF. Chaque pièce vue par
l'agent part de son contour rétréci et s'étend dans l'espace libre, toutes en même temps, sans franchir un mur ni
sortir du bâtiment ; ce qui reste libre et assez grand est un local candidat (circulation ou local oublié).
"""
from __future__ import annotations

from typing import Any

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

PX_PAR_M_TRAVAIL = 59.0  # résolution de travail (~1,7 cm par pixel)
ENCRE = 170  # plus sombre : mur (remplissage gris ou trait noir)
ELEMENT_ISOLE_PX = 400  # encre isolée de moins de pixels (résolution de travail) : texte, petit mobilier, retirée
RETRAIT_M = 0.20  # le contour de l'agent est d'abord rétréci d'autant (départ sûr dans la pièce)
EXTENSION_M = 1.5  # croissance maximale d'une pièce au-delà de son départ
RATIO_SURFACE = (0.6, 1.8)
CANDIDAT_M2 = 2.0
SIMPLIFICATION_M = 0.05
NATURES = ("chauffe", "circulation", "non_chauffe", "gaine_technique")


FERMETURE_M = 0.7  # encoches de moins de 1,4 m de large (mobilier, battants de porte) refermées
EXTENSION_TRAITS_FINS_M = 1.0  # deuxième passe, à travers les traits fins
RECOIN_MIN_M = 0.40  # largeur minimale d'un recoin gagné en deuxième passe


def _disque(rayon: int) -> np.ndarray:
    y, x = np.ogrid[-rayon: rayon + 1, -rayon: rayon + 1]
    return x * x + y * y <= rayon * rayon


def _polygone_pixels(objet: dict[str, Any], largeur: int, hauteur: int) -> Polygon:
    return Polygon([(x * largeur / 1000, y * hauteur / 1000) for x, y in objet["points"]]).buffer(0)


def _vectoriser(masque: np.ndarray, echelle: float) -> Polygon | None:
    """Masque binaire -> polygone (réunion des segments de ligne), en pixels de la page."""
    rectangles = []
    for y in np.flatnonzero(masque.any(axis=1)):
        ligne = masque[y]
        bords = np.flatnonzero(np.diff(np.concatenate(([0], ligne.view(np.int8), [0]))))
        for debut, fin in zip(bords[::2], bords[1::2]):
            rectangles.append(box(debut * echelle, y * echelle, fin * echelle, (y + 1) * echelle))
    if not rectangles:
        return None
    forme = unary_union(rectangles)
    if forme.geom_type == "MultiPolygon":
        forme = max(forme.geoms, key=lambda g: g.area)
    return Polygon(forme.exterior)


def masque_murs(page: Image.Image, px_par_m_page: float) -> tuple[np.ndarray, float]:
    """Murs à la résolution de travail (True = mur) et facteur page/travail."""
    facteur = max(1, round(px_par_m_page / PX_PAR_M_TRAVAIL))
    pixels = np.asarray(page.convert("L"))
    h, w = pixels.shape[0] // facteur * facteur, pixels.shape[1] // facteur * facteur
    petit = pixels[:h, :w].reshape(h // facteur, facteur, w // facteur, facteur).min(axis=(1, 3))
    encre = petit < ENCRE
    etiquettes, nombre = ndimage.label(encre, structure=np.ones((3, 3)))
    if nombre:
        tailles = ndimage.sum(encre, etiquettes, index=np.arange(1, nombre + 1))
        gardes = np.concatenate(([False], tailles >= ELEMENT_ISOLE_PX))
        encre = gardes[etiquettes]
    return encre, facteur


def recaler_pieces(page: Image.Image, analyse: dict[str, Any], px_par_m: float,
                   batiment: Polygon | None = None) -> dict[str, Any]:
    """Contours recalés par pièce (repère 0..1000 de la feuille) et locaux candidats."""
    largeur, hauteur = page.size
    murs, facteur = masque_murs(page, px_par_m)
    ht, lt = murs.shape
    echelle = facteur  # pixels de page par pixel de travail
    ppm = px_par_m / facteur
    dedans = np.ones_like(murs)
    if batiment is not None:
        image = Image.new("1", (lt, ht), 0)
        ImageDraw.Draw(image).polygon([(x / echelle, y / echelle) for x, y in batiment.exterior.coords], fill=1)
        dedans = np.asarray(image)
    libre = ~murs & dedans
    pieces = [o for o in analyse["objects"] if o["category"] == "piece" and len(o["points"]) >= 3]
    etiquettes = np.zeros((ht, lt), np.int32)
    formes = []
    for rang, objet in enumerate(pieces, 1):
        forme = _polygone_pixels(objet, largeur, hauteur)
        formes.append(forme)
        depart = forme.buffer(-RETRAIT_M * px_par_m)
        if depart.is_empty:
            depart = forme.representative_point().buffer(0.1 * px_par_m)
        image = Image.new("1", (lt, ht), 0)
        morceaux = [depart] if depart.geom_type == "Polygon" else list(depart.geoms)
        for morceau in morceaux:
            ImageDraw.Draw(image).polygon([(x / echelle, y / echelle) for x, y in morceau.exterior.coords], fill=1)
        graine = np.asarray(image) & libre & (etiquettes == 0)
        etiquettes[graine] = rang
    # croissance simultanée dans l'espace libre, bornée à EXTENSION_M
    for _ in range(round(EXTENSION_M * ppm)):
        voisins = ndimage.grey_dilation(etiquettes, size=(3, 3))
        nouveaux = (etiquettes == 0) & libre & (voisins > 0)
        if not nouveaux.any():
            break
        etiquettes[nouveaux] = voisins[nouveaux]
    # espaces libres non attribués : locaux candidats (avant la deuxième passe, qui ne doit pas les absorber)
    reste = ndimage.binary_opening(libre & (etiquettes == 0), iterations=2)
    groupes, nombre = ndimage.label(reste)
    candidats = []
    bloque = np.zeros_like(libre)
    for rang in range(1, nombre + 1):
        region = groupes == rang
        surface = region.sum() / ppm ** 2
        if surface < CANDIDAT_M2:
            continue
        bloque |= ndimage.binary_dilation(region, iterations=2)
        forme = _vectoriser(region, echelle)
        if forme is None:
            continue
        forme = forme.simplify(SIMPLIFICATION_M * px_par_m)
        centre = forme.representative_point()
        candidats.append({
            "surface_m2": round(surface, 1),
            "centre": [round(centre.x * 1000 / largeur, 1), round(centre.y * 1000 / hauteur, 1)],
            "points": [[round(x * 1000 / largeur, 3), round(y * 1000 / hauteur, 3)] for x, y in list(forme.exterior.coords)[:-1]],
        })
    # deuxième passe : les traits fins (battants de porte, évier, contour de meuble, trait de tableau) ne bloquent
    # plus, mais seuls les recoins de plus de RECOIN_MIN_M de large sont gardés (la bande d'un mur-rideau, 25 à
    # 33 cm, reste hors de la pièce) ; les locaux candidats ne sont pas absorbés
    murs_epais = ndimage.binary_opening(murs, structure=np.ones((3, 3)))
    libre2 = ~murs_epais & dedans & ~bloque
    etendues = etiquettes.copy()
    for _ in range(round(EXTENSION_TRAITS_FINS_M * ppm)):
        voisins = ndimage.grey_dilation(etendues, size=(3, 3))
        nouveaux = (etendues == 0) & libre2 & (voisins > 0)
        if not nouveaux.any():
            break
        etendues[nouveaux] = voisins[nouveaux]
    ajouts = (etendues > 0) & (etiquettes == 0)
    demi = max(1, round(RECOIN_MIN_M / 2 * ppm))
    larges = ndimage.binary_opening(ajouts, structure=_disque(demi))
    garder = ajouts & ndimage.binary_dilation(larges, structure=_disque(demi))
    etiquettes[garder] = etendues[garder]
    # encoches restantes refermées ; seuls les murs épais restent exclus, sans empiéter sur une autre pièce
    rayon = round(FERMETURE_M * ppm)
    resultats = []
    for rang, (objet, forme) in enumerate(zip(pieces, formes), 1):
        region = etiquettes == rang
        if region.any():
            ys, xs = np.nonzero(region)
            y0, y1 = max(ys.min() - rayon - 2, 0), min(ys.max() + rayon + 3, ht)
            x0, x1 = max(xs.min() - rayon - 2, 0), min(xs.max() + rayon + 3, lt)
            local = etiquettes[y0:y1, x0:x1]
            morceau = ndimage.binary_closing(region[y0:y1, x0:x1], structure=_disque(rayon))
            morceau &= ~murs_epais[y0:y1, x0:x1] & dedans[y0:y1, x0:x1] & ((local == 0) | (local == rang))
            region = np.zeros_like(region)
            region[y0:y1, x0:x1] = ndimage.binary_fill_holes(morceau | region[y0:y1, x0:x1])
        recale = _vectoriser(region, echelle)
        rapport = recale.area / forme.area if recale is not None and forme.area else 0
        garde = recale is not None and RATIO_SURFACE[0] <= rapport <= RATIO_SURFACE[1]
        nouvelle = recale.simplify(SIMPLIFICATION_M * px_par_m) if garde else forme
        resultats.append({
            "id": objet["id"], "nom": objet.get("subtype", ""),
            "points": [[round(x * 1000 / largeur, 3), round(y * 1000 / hauteur, 3)] for x, y in list(nouvelle.exterior.coords)[:-1]],
            "surface_agent_m2": round(forme.area / px_par_m ** 2, 2),
            "surface_m2": round(nouvelle.area / px_par_m ** 2, 2),
            "recale": garde,
            "motif": "" if garde else f"surface recalée {rapport:.2f} × celle de l'agent : contour de l'agent gardé",
        })
    candidats.sort(key=lambda c: -c["surface_m2"])
    return {"pieces": resultats, "candidats": candidats}


DECISIONS_CANDIDAT = ("local", "vide", "exterieur", "mur")


def _vers_analyse(point: list[float], manifest: dict[str, Any]) -> list[float]:
    """Point de la feuille (0..1000) -> repère de l'image analysée par l'agent (0..1000 du recadrage)."""
    x = point[0] / 1000 * manifest["page_width_px"]
    y = point[1] / 1000 * manifest["page_height_px"]
    gauche, haut = manifest["crop_box_px"][0], manifest["crop_box_px"][1]
    return [round((x - gauche) * 1000 / manifest["width_px"], 1), round((y - haut) * 1000 / manifest["height_px"], 1)]


def consigne_locaux(analyse: dict[str, Any], recalage: dict[str, Any]) -> str:
    """Consigne courte pour l'agent thermicien-plan : nature des pièces, décision sur les espaces libres."""
    manifest = analyse["manifest"]
    lignes = [
        "Inventaire des locaux d'un niveau, à partir des images raster suivantes (pixels seuls).",
        f"Vue globale : {manifest['overview']}",
        "Tuiles de détail (bornes normalisées x1,y1,x2,y2 dans le repère global 0..1000) :",
    ]
    lignes += [f"- {tuile['path']} : {tuile['box_norm']}" for tuile in manifest["tiles"]]
    lignes += ["", "Pièces déjà identifiées (id, nom lu, point intérieur dans le repère global) :"]
    par_id = {o["id"]: o for o in analyse["objects"]}
    for piece in recalage["pieces"]:
        objet = par_id.get(piece["id"])
        if objet is None:
            continue
        centre = Polygon(objet["points"]).representative_point()
        lignes.append(f"- {piece['id']} « {piece['nom']} » vers {_vers_analyse([centre.x, centre.y], manifest)}")
    lignes += ["", "Espaces libres qu'aucune pièce ne couvre (repérés sur l'image entre les murs) :"]
    for rang, candidat in enumerate(recalage["candidats"], 1):
        lignes.append(f"- C{rang} : {candidat['surface_m2']} m² vers {_vers_analyse(candidat['centre'], manifest)}")
    lignes += [
        "",
        "Ta tâche, sans dessiner de contour (ils sont mesurés par ailleurs) :",
        "1. Pour chaque pièce : sa nature `local` = `chauffe` (bureau, salle, sanitaire, vestiaire…), `circulation`"
        " (couloir, hall, dégagement, palier, escalier ouvert chauffé), `gaine_technique` (gaine verticale ou"
        " horizontale) ou `non_chauffe` (autre local technique, escalier encloisonné ou local manifestement non"
        " chauffé). En cas de doute, `chauffe` et une observation.",
        "2. Pour chaque espace libre C… : `decision` = `local` (une pièce ou gaine oubliée : donne `nom` lu sur"
        " le plan ou « circulation », et sa nature `local`), `vide` (vide sur étage inférieur, trémie, patio,"
        " puits de lumière), `exterieur` (terrasse, dehors) ou `mur` (épaisseur de mur).",
        "3. Signale en observation une pièce qui contient un vide (ex. « vide sur accueil ») : sa surface n'est pas"
        " un plancher chauffé.",
        "Réponds uniquement par le JSON demandé.",
    ]
    return "\n".join(lignes)


def schema_locaux() -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "pieces": {"type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "properties": {"id": {"type": "string"}, "local": {"type": "string", "enum": list(NATURES)},
                               "indice": {"type": "string"}},
                "required": ["id", "local", "indice"]}},
            "candidats": {"type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "properties": {"id": {"type": "string"}, "decision": {"type": "string", "enum": list(DECISIONS_CANDIDAT)},
                               "nom": {"type": "string"}, "local": {"type": "string", "enum": list(NATURES)},
                               "indice": {"type": "string"}},
                "required": ["id", "decision", "nom", "local", "indice"]}},
            "observations": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["pieces", "candidats", "observations"],
    }


def integrer_locaux(analyse: dict[str, Any], recalage: dict[str, Any], reponse: dict[str, Any]) -> dict[str, Any]:
    """Nature de chaque pièce ; les espaces libres reconnus comme locaux deviennent des pièces (contour mesuré)."""
    natures = {p["id"]: p for p in reponse.get("pieces", [])}
    objets = []
    for objet in analyse["objects"]:
        if objet["category"] == "piece":
            fiche = natures.get(objet.get("id"))
            objet = {**objet, "local": fiche["local"] if fiche else "chauffe"}
        objets.append(objet)
    decisions = {c["id"]: c for c in reponse.get("candidats", [])}
    compteur = sum(1 for o in objets if o["category"] == "piece")
    ecartes = []
    for rang, candidat in enumerate(recalage["candidats"], 1):
        fiche = decisions.get(f"C{rang}")
        if not fiche or fiche["decision"] != "local":
            ecartes.append({"id": f"C{rang}", "surface_m2": candidat["surface_m2"], "points": candidat["points"],
                            "decision": fiche["decision"] if fiche else "sans réponse",
                            "nom": fiche["nom"] if fiche else ""})
            continue
        compteur += 1
        objets.append({"id": f"piece-{compteur:03d}", "category": "piece", "subtype": fiche["nom"] or "circulation",
                       "geometry_type": "polygon", "points": candidat["points"], "confidence": 0.7,
                       "evidence": f"espace libre entre les murs ({candidat['surface_m2']} m²) : {fiche['indice']}",
                       "review_required": True, "local": fiche["local"], "contour": "espace_libre_mesure"})
    return {**analyse, "objects": objets, "locaux_ecartes": ecartes,
            "observations": analyse.get("observations", []) + reponse.get("observations", [])}


def appliquer(analyse: dict[str, Any], recalage: dict[str, Any]) -> dict[str, Any]:
    """Analyse dont les pièces prennent le contour recalé (le contour de l'agent est conservé à côté)."""
    par_id = {p["id"]: p for p in recalage["pieces"]}
    objets = []
    for objet in analyse["objects"]:
        fiche = par_id.get(objet.get("id"))
        if fiche and fiche["recale"]:
            objet = {**objet, "points_contour_agent": objet["points"], "points": fiche["points"], "contour": "recale_sur_murs"}
        objets.append(objet)
    return {**analyse, "objects": objets, "locaux_candidats": recalage["candidats"]}
