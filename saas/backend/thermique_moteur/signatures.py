"""Catalogue des signatures graphiques d'un plan — étape E1 de docs/thermique/refondation-parcours-decisions.md.

Les calques de l'architecte sont aplatis à l'export PDF ; chacun garde une **signature** : pour un trait, sa
largeur, sa couleur exacte et ses tirets ; pour un remplissage, sa couleur. Le catalogue regroupe les éléments
par signature, les mesure et propose un rôle (face de mur, vitrage, isolant, habillage…) que le thermicien
valide une fois par projet.

Indices mesurés sur le plan pour proposer un rôle :
- part appariée : traits qui forment des paires de faces parallèles à 5-80 cm (murs) ;
- part dans les murs : éléments situés entre les deux faces d'un mur détecté (isolant, maçonnerie) ;
- part alignée : traits dans le prolongement d'un mur, là où il s'interrompt (baies, vitrages) ;
- part courte : traits de moins de 40 cm (hachures et motifs).
"""
from __future__ import annotations

import colorsys
import math
from collections import defaultdict

from thermique_moteur import murs as moteur_murs
from thermique_moteur import vecteurs
from thermique_moteur.metre import pt_en_m

ROLES_TRAITS = {
    "face_mur": "Face de mur coupé",
    "cloison": "Cloison, doublage",
    "vitrage": "Vitrage, menuiserie",
    "isolant": "Isolant (motif dans les murs)",
    "motif": "Motif, hachure (sol, végétation)",
    "projection": "Projection, élément au-dessus",
    "habillage": "Mobilier, équipement, habillage",
    "annotation": "Cote, texte, repère",
    "trame": "Trame, axes",
    "ignorer": "À ignorer",
}
ROLES_APLATS = {
    "maconnerie": "Maçonnerie, béton (murs)",
    "isolant": "Isolant (remplissage)",
    "sol_exterieur": "Terrasse, végétation, sol extérieur",
    "autre": "Autre remplissage",
    "ignorer": "À ignorer",
}
PARTS = ("part_courte", "part_appariee", "part_dans_murs", "part_alignee")
COURT_M = 0.4
ECHANTILLON_MAX = 3000
CELLULE_M = 2.0
PORTEE_BAIE_M = 3.0
LUMINANCE_FONCEE = 64
LARGEUR_PAROI_MIN = 0.7
ECART_GRIS = 12
MAX_ELEMENTS = 20000


def _rgb(hexa: str) -> tuple[int, int, int]:
    return int(hexa[1:3], 16), int(hexa[3:5], 16), int(hexa[5:7], 16)


def est_gris(hexa: str) -> bool:
    rouge, vert, bleu = _rgb(hexa)
    return max(rouge, vert, bleu) - min(rouge, vert, bleu) <= ECART_GRIS


def _teinte_deg(hexa: str) -> float:
    rouge, vert, bleu = _rgb(hexa)
    return colorsys.rgb_to_hsv(rouge / 255, vert / 255, bleu / 255)[0] * 360


def nom_couleur(hexa: str) -> str:
    rouge, vert, bleu = _rgb(hexa)
    if est_gris(hexa):
        luminance = 0.3 * rouge + 0.59 * vert + 0.11 * bleu
        if luminance <= 40:
            return "noir"
        if luminance >= 245:
            return "blanc"
        return f"gris {round(100 - luminance / 2.55)} %"
    saturation = colorsys.rgb_to_hsv(rouge / 255, vert / 255, bleu / 255)[1]
    degres = _teinte_deg(hexa)
    noms = ((15, "rouge"), (45, "orange"), (70, "jaune"), (165, "vert"), (200, "cyan"), (255, "bleu"), (290, "violet"), (335, "magenta"), (361, "rouge"))
    nom = next(n for borne, n in noms if degres < borne)
    return f"{nom} pâle" if saturation < 0.35 else nom


def _est_vert(hexa: str) -> bool:
    return not est_gris(hexa) and 70 <= _teinte_deg(hexa) < 165


def cle_trait(largeur: float, hexa: str, tirets: str) -> str:
    return f"trait|{largeur:.2f}|{hexa}|{tirets}"


def cle_aplat(hexa: str) -> str:
    return f"aplat|{hexa}"


def libelle(signature: dict) -> str:
    couleur = nom_couleur(signature["couleur"])
    if signature["genre"] == "aplat":
        return f"Remplissage {couleur}"
    texte = f"{signature['largeur']:.2f} pt · {couleur}".replace(".", ",")
    return texte + (" · tirets" if signature["tirets"] else "")


class _IndexMurs:
    """Murs détectés rangés par cellules de 2 m, pour tester vite « dans un mur » et « dans une baie »."""

    def __init__(self, murs: list[dict], m: float):
        self.m = m
        self.cellule = CELLULE_M * m
        self.murs: list[tuple] = []
        self.grille: dict[tuple[int, int], list[int]] = defaultdict(list)
        portee = PORTEE_BAIE_M * m
        for mur in murs:
            points = mur["points"]
            xs, ys = [p[0] for p in points], [p[1] for p in points]
            axe = None
            if not mur.get("courbe") and len(points) == 4:
                (x0, y0), (x1, y1), (x2, y2), (x3, y3) = points
                ax, ay, bx, by = (x0 + x3) / 2, (y0 + y3) / 2, (x1 + x2) / 2, (y1 + y2) / 2
                longueur = math.hypot(bx - ax, by - ay)
                if longueur > 0:
                    axe = (ax, ay, (bx - ax) / longueur, (by - ay) / longueur, longueur, math.hypot(x3 - x0, y3 - y0) / 2)
            numero = len(self.murs)
            self.murs.append((points, (min(xs), min(ys), max(xs), max(ys)), axe))
            for cx in range(int((min(xs) - portee) // self.cellule), int((max(xs) + portee) // self.cellule) + 1):
                for cy in range(int((min(ys) - portee) // self.cellule), int((max(ys) + portee) // self.cellule) + 1):
                    self.grille[(cx, cy)].append(numero)

    def _proches(self, x: float, y: float):
        return self.grille.get((int(x // self.cellule), int(y // self.cellule)), ())

    def dans_un_mur(self, x: float, y: float) -> bool:
        for numero in self._proches(x, y):
            points, (x0, y0, x1, y1), _ = self.murs[numero]
            if x0 <= x <= x1 and y0 <= y <= y1 and moteur_murs._dans_anneau(x, y, points):
                return True
        return False

    def dans_une_baie(self, x: float, y: float, ux: float, uy: float) -> bool:
        for numero in self._proches(x, y):
            axe = self.murs[numero][2]
            if axe is None:
                continue
            ax, ay, wx, wy, longueur, demi = axe
            if abs(ux * wy - uy * wx) > math.sin(math.radians(3)):
                continue
            dx, dy = x - ax, y - ay
            if abs(-wy * dx + wx * dy) > demi + 0.02 * self.m:
                continue
            t = wx * dx + wy * dy
            if -PORTEE_BAIE_M * self.m <= t < 0 or longueur < t <= longueur + PORTEE_BAIE_M * self.m:
                return True
        return False


def _aire(points) -> float:
    return abs(sum(points[i - 1][0] * points[i][1] - points[i][0] * points[i - 1][1] for i in range(len(points)))) / 2


def catalogue_planche(traits: list, aplats: list, echelle: float) -> dict:
    """Signatures d'une planche. `traits` : sortie de `traits.lire_traits(..., detail=True)` ;
    `aplats` : sortie de `traits.lire_aplats(..., detail=True)`."""
    m = 1.0 / pt_en_m(echelle)
    lignes = vecteurs.fusionner_lignes([t[:6] for t in traits])
    # Paires mesurées sur les traits foncés et épais seulement (faces de murs, cloisons) : les textures grises
    # (végétation d'une toiture : 60 000 traits au niveau 3 du projet d'essai) et les rayures fines (terrasses,
    # marches) rendaient la mesure très lente (3 min) et ne servent à aucun rôle de paroi.
    foncees = [ligne for ligne in lignes if ligne["luminance"] <= LUMINANCE_FONCEE and ligne["largeur"] >= LARGEUR_PAROI_MIN]
    appariement = {(p["largeur"], p["luminance"]): p["part_appariee"] for p in vecteurs.dictionnaire_plumes(foncees, echelle)} if foncees else {}
    detection = moteur_murs.detecter_murs(lignes, [a[:2] for a in aplats], echelle) if lignes else {"murs": []}
    index = _IndexMurs(detection["murs"], m)
    signatures = []

    groupes: dict[str, list] = defaultdict(list)
    for trait in traits:
        groupes[cle_trait(trait[4], trait[6], trait[7])].append(trait)
    for cle, segments in groupes.items():
        premier = segments[0]
        longueurs = [math.hypot(s[2] - s[0], s[3] - s[1]) for s in segments]
        total = sum(longueurs)
        if total <= 0:
            continue
        pas = max(1, len(segments) // ECHANTILLON_MAX)
        poids = dans = alignes = 0.0
        for segment, longueur in zip(segments[::pas], longueurs[::pas]):
            if longueur <= 0:
                continue
            x, y = (segment[0] + segment[2]) / 2, (segment[1] + segment[3]) / 2
            poids += longueur
            if index.dans_un_mur(x, y):
                dans += longueur
            elif index.dans_une_baie(x, y, (segment[2] - segment[0]) / longueur, (segment[3] - segment[1]) / longueur):
                alignes += longueur
        signatures.append(
            {
                "cle": cle,
                "genre": "trait",
                "largeur": premier[4],
                "couleur": premier[6],
                "tirets": premier[7],
                "luminance": premier[5],
                "nombre": len(segments),
                "longueur_m": round(total / m, 2),
                "part_courte": round(sum(l for l in longueurs if l <= COURT_M * m) / total, 3),
                "part_appariee": round(appariement.get((premier[4], premier[5]), 0.0), 3),
                "part_dans_murs": round(dans / poids, 3) if poids else 0.0,
                "part_alignee": round(alignes / poids, 3) if poids else 0.0,
            }
        )

    par_couleur: dict[str, list] = defaultdict(list)
    for aplat in aplats:
        par_couleur[aplat[2]].append(aplat)
    for hexa, facettes in par_couleur.items():
        aires = [_aire(f[0]) for f in facettes]
        total = sum(aires)
        if total <= 0:
            continue
        pas = max(1, len(facettes) // ECHANTILLON_MAX)
        poids = dans = 0.0
        for facette, aire in zip(facettes[::pas], aires[::pas]):
            if aire <= 0:
                continue
            x = sum(p[0] for p in facette[0]) / len(facette[0])
            y = sum(p[1] for p in facette[0]) / len(facette[0])
            poids += aire
            if index.dans_un_mur(x, y):
                dans += aire
        signatures.append(
            {
                "cle": cle_aplat(hexa),
                "genre": "aplat",
                "couleur": hexa,
                "luminance": facettes[0][1],
                "nombre": len(facettes),
                "aire_m2": round(total / m / m, 2),
                "part_dans_murs": round(dans / poids, 3) if poids else 0.0,
            }
        )
    return {"echelle": echelle, "murs": len(detection["murs"]), "signatures": signatures}


def proposer_role(signature: dict) -> tuple[str, str]:
    """Rôle proposé et raison lisible, à partir des mesures de la signature."""

    def pct(valeur: float) -> str:
        return f"{round(valeur * 100)} %"

    couleur = signature["couleur"]
    if signature["genre"] == "aplat":
        if signature["part_dans_murs"] >= 0.5:
            return "maconnerie", f"{pct(signature['part_dans_murs'])} de sa surface est dans les murs détectés"
        if est_gris(couleur) and signature["luminance"] >= 245:
            return "ignorer", "remplissage blanc (masque sous les textes et symboles)"
        if _est_vert(couleur):
            return "sol_exterieur", "remplissage vert (végétation)"
        return "autre", "remplissage hors des murs"
    if not est_gris(couleur):
        if _est_vert(couleur):
            return "motif", "trait vert (végétation)"
        return "annotation", f"trait {nom_couleur(couleur)} (cotes, repères)"
    if signature["tirets"]:
        return "projection", "trait en tirets"
    if signature["part_appariee"] >= 0.5 and signature["largeur"] >= 0.9:
        return "face_mur", f"{pct(signature['part_appariee'])} de ses traits forment des paires de faces à 5-80 cm"
    if signature["part_dans_murs"] >= 0.3 and signature["part_courte"] >= 0.5:
        return "isolant", f"petits traits entre les faces des murs ({pct(signature['part_dans_murs'])})"
    fonce = signature["luminance"] <= LUMINANCE_FONCEE
    if fonce and signature["part_alignee"] >= 0.2:
        return "vitrage", f"{pct(signature['part_alignee'])} de ses traits prolongent un mur là où il s'interrompt"
    # Les traits fins foncés forment aussi des paires (mobilier, portes) : seuls les traits épais sont proposés en cloison.
    if fonce and signature["largeur"] >= LARGEUR_PAROI_MIN:
        return "cloison", f"trait foncé épais, {pct(signature['part_appariee'])} en paires"
    if signature["part_courte"] >= 0.6:
        return "motif", f"{pct(signature['part_courte'])} de traits courts (hachures)"
    if signature["luminance"] >= 150 and signature["largeur"] <= 0.2:
        return "trame", "trait fin et clair"
    return "habillage", "trait sans rôle de paroi reconnu"


def fusionner_catalogues(catalogues: list[tuple[int, dict]]) -> list[dict]:
    """Signatures du projet : catalogues des planches réunis par clé, parts pondérées par longueur ou surface."""
    fusion: dict[str, dict] = {}
    for planche, catalogue in catalogues:
        for signature in catalogue["signatures"]:
            mesure = "longueur_m" if signature["genre"] == "trait" else "aire_m2"
            poids = signature[mesure]
            entree = fusion.get(signature["cle"])
            if entree is None:
                entree = fusion[signature["cle"]] = {**signature, "nombre": 0, mesure: 0.0, "planches": [], "_poids": 0.0, "_sommes": defaultdict(float)}
            entree["nombre"] += signature["nombre"]
            entree[mesure] += poids
            entree["planches"].append(planche)
            entree["_poids"] += poids
            for part in PARTS:
                if part in signature:
                    entree["_sommes"][part] += signature[part] * poids
    resultat = []
    for entree in fusion.values():
        sommes, poids = entree.pop("_sommes"), entree.pop("_poids")
        for part in PARTS:
            if part in entree:
                entree[part] = round(sommes[part] / poids, 3) if poids else 0.0
        mesure = "longueur_m" if entree["genre"] == "trait" else "aire_m2"
        entree[mesure] = round(entree[mesure], 2)
        entree["libelle"] = libelle(entree)
        entree["role_propose"], entree["raison"] = proposer_role(entree)
        resultat.append(entree)
    resultat.sort(key=lambda e: (e["genre"] != "trait", -e.get("longueur_m", e.get("aire_m2", 0.0))))
    return resultat


def elements_de_signature(traits: list, aplats: list, cle: str, maximum: int = MAX_ELEMENTS) -> dict:
    """Éléments d'une signature sur une planche, pour les montrer sur le plan (points PDF)."""
    if cle.startswith("trait|"):
        segments = [t for t in traits if cle_trait(t[4], t[6], t[7]) == cle]
        tronque = len(segments) > maximum
        if tronque:
            segments = sorted(segments, key=lambda s: -math.hypot(s[2] - s[0], s[3] - s[1]))[:maximum]
        return {"segments": [[round(v, 2) for v in s[:4]] for s in segments], "tronque": tronque}
    facettes = [(a[0], a[1]) for a in aplats if cle_aplat(a[2]) == cle]
    anneaux = vecteurs.unir_aplats(facettes)
    return {
        "polygones": [[[round(x, 2), round(y, 2)] for x, y in anneau["points"]] for anneau in anneaux[:maximum]],
        "tronque": len(anneaux) > maximum,
    }
