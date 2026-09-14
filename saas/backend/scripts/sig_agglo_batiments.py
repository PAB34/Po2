"""Bâtiments d'activité de la BD TOPO — surface de plancher estimée.

Le classeur tertiaire ne connaissait la surface que par le DPE tertiaire : 1 480
diagnostics sur tout le territoire, d'où **168 présomptions** d'assujettissement
au décret tertiaire seulement. La surface de parcelle ne peut pas y suppléer —
c'est celle du terrain, et un camping de trois hectares n'a que quelques
centaines de mètres carrés bâtis.

La BD TOPO de l'IGN publie en revanche chaque bâtiment avec son **usage**, sa
**hauteur**, son **nombre d'étages** et son emprise au sol. Sur le bassin de Thau
et Agde : 5 090 bâtiments commerciaux, 1 489 industriels, 980 agricoles, 136
sportifs. Croisés avec le nombre d'étages, ils donnent une surface de plancher
estimée sur un parc cinq fois plus large que les DPE.

⚠️ **Ce n'est pas une surface au sens du décret tertiaire.** Le seuil des
1 000 m² s'apprécie par site en cumulant les activités, un bâtiment peut mêler
logement et activité, et le nombre d'étages est parfois absent. La sortie est
une **présomption élargie destinée à trier des appels**, jamais une affirmation
opposable à un prospect.

API Géoplateforme (WFS 2.0), ouverte et sans clé. Les coordonnées sont demandées
en Lambert-93 pour que les aires se calculent directement en mètres carrés.

Usage :
    python scripts/sig_agglo_batiments.py
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sig_agglo_extract import proteger_dossier  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

WFS = "https://data.geopf.fr/wfs/ows"
COUCHE = "BDTOPO_V3:batiment"
PAGE = 1000
TIMEOUT = 240

# Emprise du bassin de Thau élargie à Agde, en latitude/longitude.
BBOX = "BBOX(geometrie,43.25,3.28,43.55,3.90)"
USAGES = ["Commercial et services", "Industriel", "Sportif", "Agricole",
          "Religieux", "Sanitaire", "Enseignement", "Administratif"]

COLONNES = [
    "cleabs", "usage_1", "usage_2", "nature", "hauteur", "nombre_d_etages",
    "nombre_de_logements", "construction_legere", "etat_de_l_objet",
    "date_d_apparition", "emprise_m2", "x_l93", "y_l93",
]


def aire_et_centre(coordonnees: list) -> tuple[float, float, float]:
    """Aire et centre d'un polygone, par la formule du lacet.

    Les coordonnées arrivent déjà en Lambert-93 : l'aire sort en mètres carrés
    sans conversion. Seul l'anneau extérieur est pris en compte — les cours
    intérieures sont trop rares sur du bâti d'activité pour justifier le reste.
    """

    anneau = coordonnees[0] if coordonnees and isinstance(coordonnees[0][0], (list, tuple)) else []
    if len(anneau) < 3:
        return 0.0, 0.0, 0.0
    aire = 0.0
    for index in range(len(anneau) - 1):
        x1, y1 = anneau[index][0], anneau[index][1]
        x2, y2 = anneau[index + 1][0], anneau[index + 1][1]
        aire += x1 * y2 - x2 * y1
    xs = [point[0] for point in anneau]
    ys = [point[1] for point in anneau]
    return abs(aire) / 2.0, sum(xs) / len(xs), sum(ys) / len(ys)


def geometries(forme: dict) -> list:
    """Un bâtiment est un Polygon ou un MultiPolygon ; on rend la liste des anneaux."""

    if not forme:
        return []
    if forme.get("type") == "Polygon":
        return [forme.get("coordinates") or []]
    if forme.get("type") == "MultiPolygon":
        return list(forme.get("coordinates") or [])
    return []


def extraire_usage(session: requests.Session, usage: str, writer) -> int:
    """Pagine un usage. Le filtre et l'emprise passent tous deux par le CQL :
    combiner BBOX et CQL_FILTER en paramètres séparés fait échouer la requête."""

    ecrits, depart = 0, 0
    while True:
        parametres = {
            "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
            "TYPENAMES": COUCHE, "OUTPUTFORMAT": "application/json",
            "SRSNAME": "EPSG:2154", "COUNT": PAGE, "STARTINDEX": depart,
            "CQL_FILTER": f"{BBOX} AND usage_1='{usage}'",
        }
        for tentative in range(4):
            try:
                reponse = session.get(WFS, params=parametres, timeout=TIMEOUT)
                break
            except requests.RequestException:
                time.sleep(2 + tentative * 3)
        else:
            print(f"    [!] {usage} : abandon à l'index {depart}")
            return ecrits
        if reponse.status_code != 200 or "json" not in (reponse.headers.get("content-type") or ""):
            message = re.sub(r"\s+", " ", reponse.text[:120])
            print(f"    [!] {usage} : HTTP {reponse.status_code} {message}")
            return ecrits
        lots = reponse.json().get("features") or []
        if not lots:
            return ecrits
        for forme in lots:
            proprietes = forme.get("properties") or {}
            aire = centre_x = centre_y = 0.0
            for polygone in geometries(forme.get("geometry")):
                a, cx, cy = aire_et_centre(polygone)
                if a > aire:
                    aire, centre_x, centre_y = a, cx, cy
            ligne = {c: proprietes.get(c, "") for c in COLONNES}
            ligne["emprise_m2"] = round(aire)
            ligne["x_l93"] = round(centre_x, 1)
            ligne["y_l93"] = round(centre_y, 1)
            writer.writerow(ligne)
            ecrits += 1
        depart += len(lots)
        print(f"    {usage} : {ecrits}", end="\r")
        if len(lots) < PAGE:
            return ecrits


def main() -> int:
    parser = argparse.ArgumentParser(description="Bâtiments d'activité de la BD TOPO.")
    parser.add_argument("--out", default="sig_agglo_data")
    args = parser.parse_args()

    out_dir = Path(args.out)
    proteger_dossier(out_dir)
    session = requests.Session()
    cible = out_dir / "batiments_activite.csv"

    total = 0
    with cible.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLONNES, extrasaction="ignore")
        writer.writeheader()
        for usage in USAGES:
            compte = extraire_usage(session, usage, writer)
            total += compte
            print(f"    {usage:26} {compte:>6}   (total {total})")

    print(f"\n{total} bâtiments d'activité écrits dans {cible.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
