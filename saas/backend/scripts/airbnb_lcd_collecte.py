#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Passage 1 — inventaire des annonces par tuilage récursif adaptatif.

Pourquoi récursif : une recherche Airbnb rend au plus 40 résultats, quelle que
soit la taille de l'emprise (mesuré sur trois emprises, du centre-ville à la
commune entière). Une grille fixe plafonne donc à 40 × nombre de tuiles et
tronque en silence les zones denses.

Ici, toute tuile qui atteint le plafond est réputée **saturée** et redécoupée en
quatre, jusqu'à descendre sous le plafond ou atteindre la taille plancher. Les
tuiles encore saturées à la taille plancher sont journalisées : on saura où
l'inventaire reste incertain plutôt que de l'ignorer.

Deux économies d'appels :
- une sous-tuile qui n'intersecte pas la commune (tampon compris) n'est pas
  interrogée ;
- l'état est persisté, donc une reprise ne réinterroge pas les tuiles faites.

Usage :
    python airbnb_lcd_collecte.py --communes Sète
    python airbnb_lcd_collecte.py --toutes --sortie ../../../sig_agglo_data/airbnb
"""

from __future__ import annotations

import argparse
import json
import math
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from shapely.geometry import box

import airbnb_lcd_communes as communes_mod
from airbnb_lcd_client import PLAFOND_RESULTATS, ClientAirbnb

# Côté minimal d'une tuile. En deçà, on cesse de subdiviser : on est descendu
# sous la maille de l'îlot et le flou des coordonnées Airbnb rend la précision
# supplémentaire illusoire.
COTE_MINIMAL_M = 150.0

# Les coordonnées Airbnb sont approximatives : on interroge un peu au-delà du
# contour communal pour ne pas perdre les annonces déportées hors limite.
TAMPON_COMMUNE_M = 400.0


def _m_par_degre(lat: float) -> tuple[float, float]:
    """Mètres par degré de longitude et de latitude à cette latitude."""
    lat_rad = math.radians(lat)
    m_lon = 111_320.0 * math.cos(lat_rad)
    m_lat = 110_574.0
    return m_lon, m_lat


def _cote_m(t: dict) -> float:
    """Plus petit côté de la tuile, en mètres."""
    lat_moy = (t["sw_lat"] + t["ne_lat"]) / 2
    m_lon, m_lat = _m_par_degre(lat_moy)
    largeur = (t["ne_lon"] - t["sw_lon"]) * m_lon
    hauteur = (t["ne_lat"] - t["sw_lat"]) * m_lat
    return min(largeur, hauteur)


def _cle(t: dict) -> str:
    return (f"{t['sw_lat']:.6f},{t['sw_lon']:.6f},"
            f"{t['ne_lat']:.6f},{t['ne_lon']:.6f}")


def _quatre(t: dict) -> list[dict]:
    """Découpe une tuile en quatre quadrants."""
    mid_lat = (t["sw_lat"] + t["ne_lat"]) / 2
    mid_lon = (t["sw_lon"] + t["ne_lon"]) / 2
    return [
        {"sw_lat": t["sw_lat"], "sw_lon": t["sw_lon"],
         "ne_lat": mid_lat, "ne_lon": mid_lon},
        {"sw_lat": t["sw_lat"], "sw_lon": mid_lon,
         "ne_lat": mid_lat, "ne_lon": t["ne_lon"]},
        {"sw_lat": mid_lat, "sw_lon": t["sw_lon"],
         "ne_lat": t["ne_lat"], "ne_lon": mid_lon},
        {"sw_lat": mid_lat, "sw_lon": mid_lon,
         "ne_lat": t["ne_lat"], "ne_lon": t["ne_lon"]},
    ]


def _tampon_deg(geom, metres: float):
    """Tampon approché en degrés, corrigé de la latitude."""
    lat = geom.centroid.y
    m_lon, m_lat = _m_par_degre(lat)
    # On prend le pas le plus fin des deux axes : tampon jamais sous-dimensionné.
    return geom.buffer(metres / min(m_lon, m_lat))


def _sans_accent(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def _slug(nom: str) -> str:
    return _sans_accent(nom).lower().replace(" ", "-").replace("'", "-")


def collecter_commune(commune: dict, client: ClientAirbnb,
                      sortie: Path, reprendre: bool = True,
                      cote_minimal_m: float = COTE_MINIMAL_M) -> dict:
    """
    Inventorie une commune. Rend un dict de bilan.

    L'état (file de tuiles, tuiles faites, annonces trouvées) est écrit sur
    disque au fil de l'eau : une interruption se reprend sans perte.
    """
    nom = commune["nom"]
    insee = commune["code"]
    dossier = sortie / "passage1"
    dossier.mkdir(parents=True, exist_ok=True)
    chemin_etat = dossier / f"etat_{insee}_{_slug(nom)}.json"

    geom = communes_mod.geometrie(commune)
    geom_tamponnee = _tampon_deg(geom, TAMPON_COMMUNE_M)
    w, s, e, n = geom_tamponnee.bounds

    if chemin_etat.exists() and reprendre:
        etat = json.loads(chemin_etat.read_text(encoding="utf-8"))
        print(f"  reprise : {len(etat['faites'])} tuiles déjà faites, "
              f"{len(etat['annonces'])} annonces déjà vues")

        # Si on repasse avec un plancher plus fin qu'à l'exécution précédente,
        # les zones abandonnées comme saturées redeviennent subdivisibles :
        # on les réinjecte, sans quoi l'affinage progressif serait sans effet.
        reprises = [z for z in etat.get("tuiles_saturees", [])
                    if z["cote_m"] / 2 >= cote_minimal_m]
        if reprises:
            print(f"  plancher affiné : {len(reprises)} zones saturées "
                  f"réinjectées pour subdivision")
            for z in reprises:
                etat["file"].extend(_quatre(z["tuile"]))
            etat["tuiles_saturees"] = [
                z for z in etat["tuiles_saturees"]
                if z["cote_m"] / 2 < cote_minimal_m
            ]
    else:
        etat = {
            "commune": nom,
            "code_insee": insee,
            "debut_utc": datetime.now(timezone.utc).isoformat(),
            "file": [{"sw_lat": s, "sw_lon": w, "ne_lat": n, "ne_lon": e}],
            "faites": [],
            "annonces": {},        # room_id -> annonce brute
            "tuiles_saturees": [],  # tuiles plancher encore tronquées
            "tuiles_interrogees": 0,
            "tuiles_ignorees_hors_contour": 0,
        }

    faites = set(etat["faites"])

    while etat["file"]:
        tuile = etat["file"].pop(0)
        cle = _cle(tuile)
        if cle in faites:
            continue

        rect = box(tuile["sw_lon"], tuile["sw_lat"],
                   tuile["ne_lon"], tuile["ne_lat"])
        if not geom_tamponnee.intersects(rect):
            faites.add(cle)
            etat["faites"].append(cle)
            etat["tuiles_ignorees_hors_contour"] += 1
            continue

        cote = _cote_m(tuile)
        try:
            res = client.rechercher(tuile["sw_lat"], tuile["sw_lon"],
                                    tuile["ne_lat"], tuile["ne_lon"])
        except RuntimeError as exc:
            # Tuile perdue : on la journalise et on continue, elle restera
            # dans la file pour une prochaine exécution.
            print(f"    tuile {cle} abandonnée : {exc}")
            etat["file"].append(tuile)
            _ecrire_etat(chemin_etat, etat, faites)
            break

        etat["tuiles_interrogees"] += 1
        nouvelles = 0
        for item in res:
            rid = item.get("room_id")
            if not rid:
                continue
            rid = str(rid)
            if rid not in etat["annonces"]:
                nouvelles += 1
                item["_commune_recherche"] = nom
                item["_code_insee_recherche"] = insee
                item["_tuile"] = cle
                etat["annonces"][rid] = item

        sature = len(res) >= PLAFOND_RESULTATS
        marque = "SATURÉE" if sature else "        "
        print(f"    [{cote:6.0f} m] {marque} {len(res):3d} résultats "
              f"(+{nouvelles:3d} nouvelles) — total {len(etat['annonces'])}")

        if sature:
            if cote / 2 >= cote_minimal_m:
                etat["file"].extend(_quatre(tuile))
            else:
                etat["tuiles_saturees"].append({"tuile": tuile, "cote_m": cote})

        faites.add(cle)
        etat["faites"].append(cle)

        if etat["tuiles_interrogees"] % 10 == 0:
            _ecrire_etat(chemin_etat, etat, faites)

    etat["fin_utc"] = datetime.now(timezone.utc).isoformat()
    _ecrire_etat(chemin_etat, etat, faites)

    # Sortie exploitable : les annonces de la commune, dédupliquées.
    chemin_annonces = dossier / f"annonces_{insee}_{_slug(nom)}.json"
    chemin_annonces.write_text(
        json.dumps(list(etat["annonces"].values()), ensure_ascii=False),
        encoding="utf-8")

    bilan = {
        "commune": nom,
        "code_insee": insee,
        "annonces": len(etat["annonces"]),
        "tuiles_interrogees": etat["tuiles_interrogees"],
        "tuiles_ignorees_hors_contour": etat["tuiles_ignorees_hors_contour"],
        "tuiles_saturees_residuelles": len(etat["tuiles_saturees"]),
        "file_restante": len(etat["file"]),
        "fichier": str(chemin_annonces),
    }
    return bilan


def _ecrire_etat(chemin: Path, etat: dict, faites: set) -> None:
    etat["faites"] = sorted(faites)
    chemin.write_text(json.dumps(etat, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sortie", default="sig_agglo_data/airbnb",
                   help="Dossier de sortie (hors git).")
    p.add_argument("--communes", nargs="*",
                   help="Noms de communes à traiter (défaut : Sète seule).")
    p.add_argument("--toutes", action="store_true",
                   help="Traiter les 14 communes.")
    p.add_argument("--pause", type=float, default=1.0)
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--pas-de-reprise", action="store_true",
                   help="Ignorer l'état existant et repartir de zéro.")
    p.add_argument("--cote-min", type=float, default=COTE_MINIMAL_M,
                   help=f"Côté plancher d'une tuile, en mètres "
                        f"(défaut {COTE_MINIMAL_M:.0f}). Une valeur élevée "
                        f"écourte la collecte mais laisse des zones saturées.")
    args = p.parse_args()

    sortie = Path(args.sortie)
    sortie.mkdir(parents=True, exist_ok=True)

    toutes = communes_mod.charger_communes(sortie)
    if args.toutes:
        cibles = sorted(toutes, key=lambda c: -c.get("population", 0))
    elif args.communes:
        voulues = {_sans_accent(x).lower() for x in args.communes}
        cibles = [c for c in toutes
                  if _sans_accent(c["nom"]).lower() in voulues]
        introuvables = voulues - {_sans_accent(c["nom"]).lower() for c in cibles}
        if introuvables:
            raise SystemExit(f"Communes inconnues : {sorted(introuvables)}")
    else:
        cibles = [c for c in toutes if c["nom"] == "Sète"]

    client = ClientAirbnb(cache_dir=sortie / "cache_details",
                          pause=args.pause, timeout=args.timeout)

    bilans = []
    for i, c in enumerate(cibles, 1):
        print(f"\n[{i}/{len(cibles)}] {c['nom']} ({c['code']}) "
              f"— {c.get('population', 0)} hab.")
        bilans.append(collecter_commune(c, client, sortie,
                                        reprendre=not args.pas_de_reprise,
                                        cote_minimal_m=args.cote_min))

    chemin_bilan = sortie / "passage1" / "bilan_collecte.json"
    chemin_bilan.write_text(json.dumps(
        {"genere_utc": datetime.now(timezone.utc).isoformat(),
         "plafond_par_recherche": PLAFOND_RESULTATS,
         "cote_minimal_m": COTE_MINIMAL_M,
         "stats_client": client.stats,
         "communes": bilans}, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 66)
    total = sum(b["annonces"] for b in bilans)
    for b in bilans:
        alerte = ""
        if b["tuiles_saturees_residuelles"]:
            alerte = f"  ⚠ {b['tuiles_saturees_residuelles']} zones encore saturées"
        if b["file_restante"]:
            alerte += f"  ⚠ {b['file_restante']} tuiles non traitées (relancer)"
        print(f"  {b['commune']:<20} {b['annonces']:>5} annonces  "
              f"({b['tuiles_interrogees']} tuiles){alerte}")
    print(f"  {'TOTAL':<20} {total:>5} annonces")
    print(f"\n  appels recherche : {client.stats['recherches']}, "
          f"échecs : {client.stats['echecs']}")
    print(f"  bilan -> {chemin_bilan}")


if __name__ == "__main__":
    main()
