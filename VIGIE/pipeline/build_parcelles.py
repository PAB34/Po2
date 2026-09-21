"""Étape É2 — calcul, pour chaque parcelle de Sète, du secteur PLU, du bâti et de la réserve.

Données (téléchargées une fois dans VIGIE/.cache, puis réutilisées) :
  - cadastre Etalab : parcelles + bâtiments de la commune 34301 ;
  - zonage du PLU : API Carto GPU, partition DU_34301.
Sorties (chargées par la carte) : web/data/parcelles.geojson, batiments.geojson, zonage.geojson, meta.json.

Lancer : python -m pipeline.build_parcelles [--refresh]   (depuis VIGIE/, après build_regles)
"""
from __future__ import annotations

import gzip
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

from pyproj import Transformer
from shapely import STRtree, make_valid
from shapely.geometry import mapping, shape
from shapely.ops import transform, unary_union

RACINE = Path(__file__).resolve().parents[1]
CACHE = RACINE / ".cache"
DATA = RACINE / "web" / "data"
INSEE = "34301"
URLS = {
    "parcelles": f"https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/34/{INSEE}/cadastre-{INSEE}-parcelles.json.gz",
    "batiments": f"https://cadastre.data.gouv.fr/data/etalab-cadastre/latest/geojson/communes/34/{INSEE}/cadastre-{INSEE}-batiments.json.gz",
    "zonage": f"https://apicarto.ign.fr/api/gpu/zone-urba?partition=DU_{INSEE}&_limit=1000",
}
SEUIL_PART = 1.0          # m² : en dessous, un morceau de secteur est ignoré (bruit de bordure)
SEUIL_PARTIEL = 0.05      # part non calculable au-delà de laquelle la réserve est signalée partielle
SEUIL_NU = 20.0           # m² : sous ce bâti (abri, muret), la parcelle est considérée comme nue

VERS_L93 = Transformer.from_crs(4326, 2154, always_xy=True).transform
VERS_WGS = Transformer.from_crs(2154, 4326, always_xy=True).transform


def telecharger(nom: str, refresh: bool) -> dict:
    CACHE.mkdir(exist_ok=True)
    fichier = CACHE / f"{nom}.json"
    if refresh or not fichier.exists():
        req = urllib.request.Request(URLS[nom], headers={"User-Agent": "vigie-foncier/0.1"})
        with urllib.request.urlopen(req, timeout=180) as r:
            brut = r.read()
        if brut[:2] == b"\x1f\x8b":
            brut = gzip.decompress(brut)
        fichier.write_bytes(brut)
    return json.loads(fichier.read_text(encoding="utf-8"))


def en_l93(geojson_geom):
    g = transform(VERS_L93, shape(geojson_geom))
    return g if g.is_valid else make_valid(g)


def arrondir(obj, n=6):
    if isinstance(obj, float):
        return round(obj, n)
    if isinstance(obj, (list, tuple)):
        return [arrondir(o, n) for o in obj]
    if isinstance(obj, dict):
        return {k: arrondir(v, n) for k, v in obj.items()}
    return obj


def geom_wgs(g_l93):
    return arrondir(mapping(transform(VERS_WGS, g_l93)))


def rampe(x: float, bas: float, haut: float) -> float:
    return max(0.0, min(1.0, (x - bas) / (haut - bas)))


def score_provisoire(p: dict, regle: dict) -> tuple[int | None, str]:
    """Score /100 AVANT géométrie (É4) : réserve, terrain libre, surface, priorité de zone."""
    if p["res"] is None:
        return None, "règle d'emprise non calculable"
    pts = {
        "réserve d'emprise": 40 * rampe(p["res"], 0, 250),
        "terrain libre": 25 * rampe(p["libre"], 0, 800),
        "surface": 15 * rampe(p["surf"], 350, 1500),
        "emprise peu utilisée": 10 * (1 - min(1.0, p["util"] if p["util"] is not None else 1.0)),
        "priorité de zone": 10 * ((regle.get("score_zone") or 0) / 100),
    }
    total = sum(pts.values())
    if regle["famille"] == "protege":
        total -= 30
    motif = ", ".join(k for k, v in sorted(pts.items(), key=lambda kv: -kv[1])[:2] if v > 0)
    return max(0, round(total)), motif


def classe(score: int | None) -> str:
    if score is None:
        return "-"
    return "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50 else "D"


def main(refresh: bool = False) -> None:
    matrice = json.loads((DATA / "regles.json").read_text(encoding="utf-8"))
    regles = matrice["secteurs"]
    familles_notees = {k for k, v in matrice["familles"].items() if v.get("score")}
    parcelles = telecharger("parcelles", refresh)["features"]
    batiments = telecharger("batiments", refresh)["features"]
    zonage = telecharger("zonage", refresh)["features"]

    zones_g = [en_l93(f["geometry"]) for f in zonage]
    zones_code = [f["properties"]["libelle"] for f in zonage]
    inconnus = sorted(set(zones_code) - set(regles))
    if inconnus:
        raise SystemExit(f"Codes du zonage sans règle : {inconnus}")
    arbre_zones = STRtree(zones_g)

    bat_g = [en_l93(f["geometry"]) for f in batiments]
    bat_type = [f["properties"].get("type") for f in batiments]
    arbre_bat = STRtree(bat_g)

    sorties, bat_utiles = [], set()
    for f in parcelles:
        pr = f["properties"]
        g = en_l93(f["geometry"])
        surf = g.area
        if surf < 1:
            continue
        # Secteurs PLU
        parts: dict[str, float] = {}
        for i in arbre_zones.query(g, predicate="intersects"):
            a = g.intersection(zones_g[i]).area
            if a >= SEUIL_PART:
                parts[zones_code[i]] = parts.get(zones_code[i], 0) + a
        if not parts:
            continue  # parcelle hors zonage (domaine public maritime, etc.)
        principal = max(parts, key=parts.get)
        emprise_max, part_nc = 0.0, 0.0
        for code, a in parts.items():
            t = regles[code]["emprise"]["taux"]
            if t is None:
                part_nc += a
            else:
                emprise_max += a * t
        tout_nc = part_nc >= sum(parts.values()) - 1e-6
        # Bâti
        idx = arbre_bat.query(g, predicate="intersects")
        morceaux = [g.intersection(bat_g[i]) for i in idx]
        morceaux = [(i, m) for i, m in zip(idx, morceaux) if m.area >= 1]
        bati = unary_union([m for _, m in morceaux]).area if morceaux else 0.0
        bati_leger = sum(m.area for i, m in morceaux if bat_type[i] == "02")
        bat_utiles.update(int(i) for i, _ in morceaux)

        res = None if tout_nc else round(emprise_max - bati)
        p = {
            "id": pr["id"],
            "sec": pr["section"],
            "num": pr["numero"],
            "surf": round(surf),
            "cont": pr.get("contenance"),
            "z": principal,
            "zs": {k: round(v) for k, v in sorted(parts.items(), key=lambda kv: -kv[1])},
            "fam": regles[principal]["famille"],
            "bati": round(bati),
            "leger": round(bati_leger),
            "nbat": len(morceaux),
            "libre": round(surf - bati),
            "emax": None if tout_nc else round(emprise_max),
            "res": res,
            "util": None if tout_nc or emprise_max <= 0 else round(bati / emprise_max, 3),
            "partiel": (not tout_nc) and part_nc / surf > SEUIL_PARTIEL,
            "nu": bati < SEUIL_NU,
        }
        if regles[principal]["famille"] not in familles_notees:
            p["score"], p["motif"] = None, "famille non notée"
        else:
            p["score"], p["motif"] = score_provisoire(p, regles[principal])
        p["cl"] = classe(p["score"])
        sorties.append({"type": "Feature", "geometry": geom_wgs(g), "properties": p})

    DATA.mkdir(parents=True, exist_ok=True)
    ecrire(DATA / "parcelles.geojson", sorties)
    ecrire(DATA / "batiments.geojson", [
        {"type": "Feature", "geometry": geom_wgs(bat_g[i]), "properties": {"t": bat_type[i]}}
        for i in sorted(bat_utiles)
    ])
    ecrire(DATA / "zonage.geojson", [
        {"type": "Feature", "geometry": geom_wgs(g), "properties": {"z": c}}
        for g, c in zip(zones_g, zones_code)
    ])
    meta = {
        "genere_le": date.today().isoformat(),
        "parcelles": len(sorties),
        "batiments": len(bat_utiles),
        "zones": len(zonage),
        "sources": URLS,
    }
    (DATA / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))


def ecrire(chemin: Path, features: list) -> None:
    """Écrit le GeoJSON (servi en local) et sa version .gz (versionnée, servie par nginx gzip_static)."""
    brut = json.dumps({"type": "FeatureCollection", "features": features},
                      ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    chemin.write_bytes(brut)
    Path(f"{chemin}.gz").write_bytes(gzip.compress(brut, compresslevel=9, mtime=0))


if __name__ == "__main__":
    main(refresh="--refresh" in sys.argv)
