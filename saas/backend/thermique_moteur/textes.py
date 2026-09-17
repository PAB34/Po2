"""Textes dessinés d'un plan et noms des pièces — étape E3 (docs/thermique/refondation-parcours-decisions.md §13, D29-D30).

Les PDF d'essai ne contiennent aucun caractère : les lettres sont des contours remplis. La page est donc rendue en
image puis lue par Tesseract (déjà installé sur le serveur, français). Sonde du 2026-09-17, RDC du projet de
production à 250 dpi : 37 s, « Entrée », « Escalier », « Espace », « Distributeurs », repères « 6-B14 »…

Chaque mot garde sa boîte en points PDF ; le nom d'une pièce réunit les mots dont le centre est dans son contour,
dans l'ordre de lecture.
"""
from __future__ import annotations

import math
import re
import unicodedata

from thermique_moteur.pieces import dedans

DPI = 250
PIXELS_MAX = 160_000_000
CONFIANCE_MIN = 55
REPERE = re.compile(r"^[0-9]{1,2}-[A-Z][0-9]{1,3}$")
MOT = re.compile(r"^[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’\-.]*$")
NOM_MAX = 120
# annotations de plan qui ne sont pas des noms de pièce (essai R+2 : « garde corps sol béton … nettoyage »)
ANNOTATIONS = {
    "GARDE", "CORPS", "SOL", "BETON", "BOITE", "OUVRANTS", "OUVRANT", "NETTOYAGE", "PASSERELLE", "PENTE", "NGF",
    "VIDE", "TREMIE", "FAUX", "PLAFOND", "ACIER", "BOIS", "VITRAGE", "MENUISERIE", "GAINE", "DESCENTE", "EP", "EU",
    "RIVE", "ACROTERE", "RELEVE", "COUPE", "NIVEAU", "ECHELLE", "PLAN", "INDICE", "DATE", "HSP", "HAUTEUR",
}
VOISINAGE_NOM_M = 1.2

# Mots-clés de pré-classement (en majuscules sans accents), du plus sûr au moins sûr.
EXTERIEUR = ("TERRASSE", "BALCON", "LOGGIA", "PATIO", "JARDIN", "PARVIS", "EXTERIEUR", "COURSIVE EXTERIEURE", "COUR ANGLAISE")
NON_CHAUFFE = (
    "GARAGE", "PARKING", "STATIONNEMENT", "VELO", "CHAUFFERIE", "POUBELLE", "ORDURE", "DECHET", "CAVE", "CELLIER",
    "COMBLE", "VIDE SANITAIRE", "LOCAL TECHNIQUE", "LOCAL TECH", "SOUS-STATION", "TGBT", "TRANSFO", "LOCAL ENTRETIEN", "ABRI", "CONTAINER",
)
CLASSES = {"chauffe": "Chauffé", "non_chauffe": "Non chauffé", "exterieur": "Extérieur"}


def majuscules(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn").upper()


def lire_mots(pdf_path, page_index: int) -> list[dict]:
    """Mots lus sur la page : texte, confiance et boîte [xmin, ymin, xmax, ymax] en points PDF."""
    import ctypes

    import pypdfium2 as pdfium
    import pypdfium2.raw as pdfium_c
    import pytesseract

    from thermique_moteur.traits import VERROU_PDFIUM

    with VERROU_PDFIUM:
        document = pdfium.PdfDocument(str(pdf_path))
        try:
            page = document[page_index]
            largeur, hauteur = page.get_size()
            echelle = DPI / 72
            if largeur * hauteur * echelle * echelle > PIXELS_MAX:
                echelle = (PIXELS_MAX / (largeur * hauteur)) ** 0.5
            image = page.render(scale=echelle).to_pil().convert("L")
            w, h = image.size
            # pixel → point PDF : inverse de la transformation calculée par pdfium (rotation de page comprise)
            sortie_x, sortie_y = ctypes.c_double(), ctypes.c_double()

            def vers_pdf(px: float, py: float) -> tuple[float, float]:
                pdfium_c.FPDF_DeviceToPage(page.raw, 0, 0, w, h, 0, int(px), int(py), ctypes.byref(sortie_x), ctypes.byref(sortie_y))
                return sortie_x.value, sortie_y.value

            donnees = pytesseract.image_to_data(image, lang="fra", config="--psm 11", output_type=pytesseract.Output.DICT)
            mots = []
            for k, texte in enumerate(donnees["text"]):
                texte = texte.strip()
                confiance = float(donnees["conf"][k])
                if not texte or confiance < CONFIANCE_MIN:
                    continue
                x, y, lw, lh = donnees["left"][k], donnees["top"][k], donnees["width"][k], donnees["height"][k]
                coins = [vers_pdf(x, y), vers_pdf(x + lw, y + lh)]
                mots.append(
                    {
                        "texte": texte,
                        "confiance": round(confiance),
                        "boite": [
                            round(min(c[0] for c in coins), 2),
                            round(min(c[1] for c in coins), 2),
                            round(max(c[0] for c in coins), 2),
                            round(max(c[1] for c in coins), 2),
                        ],
                        # position dans l'image rendue (sens de lecture, même sur une page tournée)
                        "image": [x, y, lh],
                    }
                )
            page.close()
        finally:
            document.close()
    return mots


def _propre(texte: str) -> str:
    return texte.strip(" .,;:()[]{}\"'«»")


def _vrai_mot(texte: str) -> bool:
    """Écarte les lectures parasites (traits d'escalier ou hachures lus « LL », « Ti ») : au moins trois lettres,
    une voyelle et deux lettres différentes."""
    lettres = majuscules(texte).replace("'", "").replace("-", "").replace(".", "")
    return (
        len(lettres) >= 3 and bool(MOT.match(texte)) and any(v in lettres for v in "AEIOUY") and len(set(lettres)) >= 2
    )


def nom_de_piece(
    mots: list[dict], polygone: list[float], centre: list[float] | None = None, voisinage_pt: float | None = None
) -> tuple[str, str | None]:
    """(nom, repère) d'une pièce : mots de lettres dont le centre est dans le contour, lus de haut en bas puis de
    gauche à droite ; le repère est un code du type « 6-B14 ». Avec `centre` et `voisinage_pt` : seulement le mot
    le plus proche du point d'étiquette et ses voisins (un grand plateau contient bien d'autres annotations)."""
    retenus, repere = [], None
    for mot in mots:
        x0, y0, x1, y1 = mot["boite"]
        if not dedans((x0 + x1) / 2, (y0 + y1) / 2, polygone):
            continue
        texte = _propre(mot["texte"])
        if REPERE.match(texte.upper()):
            repere = repere or texte.upper()
        elif _vrai_mot(texte) and majuscules(texte).strip(".-'") not in ANNOTATIONS:
            retenus.append((mot, texte))
    if retenus and centre is not None and voisinage_pt:
        milieu = lambda m: ((m["boite"][0] + m["boite"][2]) / 2, (m["boite"][1] + m["boite"][3]) / 2)
        proche = min(retenus, key=lambda r: math.dist(milieu(r[0]), centre))
        retenus = [r for r in retenus if math.dist(milieu(r[0]), milieu(proche[0])) <= voisinage_pt]
    # sens de lecture de l'image rendue : lignes de haut en bas, puis de gauche à droite
    if all("image" in m for m, _ in retenus):
        hauteur = max((m["image"][2] for m, _ in retenus), default=1) or 1
        retenus.sort(key=lambda m: (round(m[0]["image"][1] / hauteur), m[0]["image"][0]))
    else:
        retenus.sort(key=lambda m: (-m[0]["boite"][3], m[0]["boite"][0]))
    return " ".join(t for _, t in retenus)[:NOM_MAX], repere


def classer(nom: str) -> str:
    texte = majuscules(nom)
    if any(cle in texte for cle in EXTERIEUR):
        return "exterieur"
    if any(cle in texte for cle in NON_CHAUFFE):
        return "non_chauffe"
    return "chauffe"
