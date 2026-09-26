#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Territoire : les 14 communes de Sète Agglopôle Méditerranée.

Les codes INSEE ne sont pas écrits en dur : ils sont résolus par l'API officielle
geo.api.gouv.fr à partir de l'EPCI, puis confrontés à la liste attendue. Écrire
14 codes de mémoire produit des erreurs silencieuses (mesuré : 5 codes faux sur
14 lors d'une première rédaction).

Les contours sont mis en cache sur disque : ils ne changent pas d'une exécution
à l'autre, inutile de rappeler l'API.
"""

from __future__ import annotations

import json
from pathlib import Path

import requests
from shapely.geometry import shape

GEO_API = "https://geo.api.gouv.fr"

# CA Sète Agglopôle Méditerranée
EPCI_SIREN = "200066355"

# Garde-fou : la liste attendue, telle que définie par le périmètre du projet.
# Si l'API et cette liste divergent, on veut le savoir bruyamment.
COMMUNES_ATTENDUES = {
    "Sète", "Frontignan", "Marseillan", "Mèze", "Bouzigues",
    "Balaruc-les-Bains", "Balaruc-le-Vieux", "Gigean", "Poussan",
    "Villeveyrac", "Mireval", "Vic-la-Gardiole", "Loupian", "Montbazin",
}


def _cache_path(base_dir: Path) -> Path:
    return Path(base_dir) / "communes_agglo.json"


def charger_communes(base_dir: Path, force: bool = False) -> list[dict]:
    """
    Rend la liste des 14 communes : code INSEE, nom, population, contour GeoJSON.

    Lève RuntimeError si le périmètre renvoyé par l'API ne correspond pas à
    COMMUNES_ATTENDUES — mieux vaut s'arrêter que collecter le mauvais territoire.
    """
    cache = _cache_path(base_dir)
    if cache.exists() and not force:
        return json.loads(cache.read_text(encoding="utf-8"))

    r = requests.get(
        f"{GEO_API}/epcis/{EPCI_SIREN}/communes",
        params={"fields": "nom,code,population,surface"},
        timeout=30,
    )
    r.raise_for_status()
    communes = r.json()

    noms = {c["nom"] for c in communes}
    if noms != COMMUNES_ATTENDUES:
        manquantes = sorted(COMMUNES_ATTENDUES - noms)
        en_trop = sorted(noms - COMMUNES_ATTENDUES)
        raise RuntimeError(
            "Périmètre EPCI inattendu. "
            f"Attendues absentes : {manquantes} ; en trop : {en_trop}"
        )

    for c in communes:
        c["contour"] = _charger_contour(c["code"])

    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(
        json.dumps(communes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return communes


def _charger_contour(code_insee: str) -> dict:
    """Contour administratif officiel d'une commune, en GeoJSON."""
    r = requests.get(
        f"{GEO_API}/communes/{code_insee}",
        params={"fields": "nom,code,contour", "format": "geojson",
                "geometry": "contour"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()

    # L'API a plusieurs formes de réponse selon les versions.
    if data.get("type") == "Feature":
        return data["geometry"]
    if data.get("type") == "FeatureCollection":
        features = data.get("features") or []
        if not features:
            raise RuntimeError(f"Contour introuvable pour {code_insee}")
        return features[0]["geometry"]
    if "geometry" in data:
        return data["geometry"]
    raise RuntimeError(f"GeoJSON inattendu pour {code_insee} : {data.get('type')}")


def geometrie(commune: dict):
    """Objet shapely du contour d'une commune."""
    return shape(commune["contour"])


def bbox(commune: dict) -> tuple[float, float, float, float]:
    """Emprise (west, south, east, north) du contour."""
    minx, miny, maxx, maxy = geometrie(commune).bounds
    return (minx, miny, maxx, maxy)


if __name__ == "__main__":
    import sys

    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    for c in sorted(charger_communes(base), key=lambda x: -x.get("population", 0)):
        w, s, e, n = bbox(c)
        print(f"{c['code']}  {c['nom']:<20} pop={c.get('population', 0):>6}  "
              f"bbox=({w:.4f},{s:.4f},{e:.4f},{n:.4f})")
