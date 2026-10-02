#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export CSV, statistiques par commune, rapport de collecte.

Produit aussi la **préparation** du rapprochement cadastral — et rien de plus :
sans numéro d'enregistrement exposé par Airbnb (mesuré : absent), et sans accès
au fichier des déclarations de meublés ou de la taxe de séjour, une annonce
n'est pas rattachable à un logement précis. On prépare donc les clés et les
coordonnées projetées, et le rapprochement lui-même fera l'objet d'une note
séparée, à la maille parcelle ou secteur.

Le rapport écrit le taux de remplissage de chaque colonne : une colonne à 4 %
ne doit pas être découverte trois semaines plus tard dans une analyse.

Usage :
    python airbnb_lcd_export.py --sortie sig_agglo_data/airbnb
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from shapely.geometry import Point

import airbnb_lcd_communes as communes_mod
import airbnb_lcd_equipements as equip

# Lambert-93 : la projection légale en France métropolitaine. Les distances en
# degrés sont trompeuses (à 43,4° de latitude, un degré de longitude vaut ~27 %
# de moins qu'un degré de latitude) ; toute distance doit passer par là.
LAMBERT93_EPSG = 2154


def _projeter_l93(lon: float, lat: float) -> tuple[float, float]:
    """
    WGS84 -> Lambert-93, sans dépendance à pyproj.

    Formules IGN (projection conique conforme de Lambert sécante).
    Précision largement suffisante ici : les coordonnées Airbnb sont floutées de
    plusieurs dizaines de mètres, l'erreur de projection est négligeable devant.
    """
    a = 6378137.0
    e = 0.0818191910428158
    n = 0.7256077650532670
    c = 11754255.4261000
    xs = 700000.0
    ys = 12655612.0499000

    lon_r = math.radians(lon)
    lat_r = math.radians(lat)
    lon0 = math.radians(3.0)

    lat_iso = math.log(math.tan(math.pi / 4 + lat_r / 2) *
                       ((1 - e * math.sin(lat_r)) /
                        (1 + e * math.sin(lat_r))) ** (e / 2))
    x = xs + c * math.exp(-n * lat_iso) * math.sin(n * (lon_r - lon0))
    y = ys - c * math.exp(-n * lat_iso) * math.cos(n * (lon_r - lon0))
    return x, y


def charger_lignes(sortie: Path) -> list[dict]:
    chemin = sortie / "passage2" / "annonces_details.jsonl"
    if not chemin.exists():
        raise SystemExit(f"{chemin} introuvable. Lancer airbnb_lcd_details.py.")
    with chemin.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def localiser(lignes: list[dict], sortie: Path) -> list[dict]:
    """
    Ajoute la commune réelle (par le contour), les coordonnées Lambert-93 et le
    statut de localisation.

    Rappel du piège déjà payé sur le SIG : on ne juge JAMAIS l'appartenance au
    territoire sur un code postal. Ici on la juge sur le contour administratif.
    """
    communes = communes_mod.charger_communes(sortie)
    geoms = [(c["nom"], c["code"], communes_mod.geometrie(c)) for c in communes]

    for ligne in lignes:
        lat = ligne.get("latitude_airbnb")
        lon = ligne.get("longitude_airbnb")
        ligne["commune_contour"] = ""
        ligne["code_insee_contour"] = ""
        ligne["x_l93"] = None
        ligne["y_l93"] = None
        ligne["localisation_statut"] = "sans_coordonnees"

        if lat is None or lon is None:
            continue
        try:
            pt = Point(float(lon), float(lat))
        except (TypeError, ValueError):
            continue

        x, y = _projeter_l93(float(lon), float(lat))
        ligne["x_l93"] = round(x, 2)
        ligne["y_l93"] = round(y, 2)
        ligne["localisation_statut"] = "hors_agglo"

        for nom, insee, geom in geoms:
            if geom.contains(pt):
                ligne["commune_contour"] = nom
                ligne["code_insee_contour"] = insee
                ligne["localisation_statut"] = "dans_commune"
                break
    return lignes


def ecrire_csv(chemin: Path, lignes: list[dict],
               colonnes: list[str] | None = None) -> None:
    if not lignes:
        chemin.write_text("", encoding="utf-8")
        return
    if colonnes is None:
        vues: list[str] = []
        for l in lignes:
            for k in l:
                if k not in vues:
                    vues.append(k)
        colonnes = vues
    with chemin.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colonnes, extrasaction="ignore")
        w.writeheader()
        w.writerows(lignes)


def agreger_hotes(lignes: list[dict]) -> list[dict]:
    """
    Un hôte par ligne, avec son nombre d'annonces sur le territoire.

    `get_listings_from_user()` de pyairbnb renvoie une liste vide : on ne peut
    pas demander à Airbnb les autres annonces d'un hôte. On les regroupe donc
    depuis notre propre collecte — ce qui répond de toute façon mieux à la
    question posée, qui porte sur ce territoire.
    """
    par_hote: dict[str, list[dict]] = defaultdict(list)
    for l in lignes:
        if l.get("host_id"):
            par_hote[l["host_id"]].append(l)

    out = []
    for hid, ann in sorted(par_hote.items(), key=lambda kv: -len(kv[1])):
        communes = sorted({a.get("commune_contour") or
                           a.get("commune_recherche", "") for a in ann})
        out.append({
            "host_id": hid,
            "host_nom": ann[0].get("host_nom", ""),
            "nb_annonces": len(ann),
            "communes": " | ".join(c for c in communes if c),
            "capacite_totale": sum(a.get("capacite") or 0 for a in ann),
            "superhost": any(a.get("superhost") for a in ann),
            "nb_avis_cumules": sum(a.get("nb_avis") or 0 for a in ann),
            "room_ids": " | ".join(a["room_id"] for a in ann),
        })
    return out


def stats_communes(lignes: list[dict]) -> list[dict]:
    par_commune: dict[str, list[dict]] = defaultdict(list)
    for l in lignes:
        cle = l.get("commune_contour") or "(hors contour)"
        par_commune[cle].append(l)

    out = []
    for nom, ann in sorted(par_commune.items(), key=lambda kv: -len(kv[1])):
        def taux(cat: str) -> str:
            vrais = sum(1 for a in ann if a.get(f"eq_{cat}") is True)
            return f"{vrais / len(ann):.0%}" if ann else "-"

        capacites = [a["capacite"] for a in ann if a.get("capacite")]
        prix = [a["prix_nuit_eur"] for a in ann if a.get("prix_nuit_eur")]
        out.append({
            "commune": nom,
            "nb_annonces": len(ann),
            "nb_hotes": len({a["host_id"] for a in ann if a.get("host_id")}),
            "capacite_mediane": _mediane(capacites),
            "prix_nuit_median": _mediane(prix),
            "pct_clim": taux("clim"),
            "pct_piscine": taux("piscine"),
            "pct_jacuzzi": taux("jacuzzi"),
            "pct_parking": taux("parking"),
            "pct_superhost": f"{sum(1 for a in ann if a.get('superhost')) / len(ann):.0%}",
        })
    return out


def _mediane(valeurs: list) -> float | None:
    v = sorted(x for x in valeurs if x is not None)
    if not v:
        return None
    m = len(v) // 2
    return float(v[m]) if len(v) % 2 else round((v[m - 1] + v[m]) / 2, 2)


def taux_remplissage(lignes: list[dict]) -> list[tuple[str, float]]:
    if not lignes:
        return []
    colonnes: list[str] = []
    for l in lignes:
        for k in l:
            if k not in colonnes:
                colonnes.append(k)
    res = []
    for c in colonnes:
        rempli = sum(1 for l in lignes
                     if l.get(c) not in (None, "", [], {}))
        res.append((c, rempli / len(lignes)))
    return res


def ecrire_rapport(chemin: Path, lignes: list[dict], hotes: list[dict],
                   stats: list[dict], sortie: Path) -> None:
    bilan_p1 = {}
    chemin_bilan = sortie / "passage1" / "bilan_collecte.json"
    if chemin_bilan.exists():
        bilan_p1 = json.loads(chemin_bilan.read_text(encoding="utf-8"))

    L: list[str] = []
    L.append("# Rapport de collecte Airbnb — Sète Agglopôle Méditerranée\n")
    L.append(f"Généré le {datetime.now(timezone.utc).isoformat()} (UTC).\n")

    L.append("\n## 1. Volumes\n")
    L.append(f"- annonces exploitées : **{len(lignes)}**")
    L.append(f"- hôtes distincts : **{len(hotes)}**")
    multi = [h for h in hotes if h["nb_annonces"] > 1]
    L.append(f"- hôtes multi-annonces : **{len(multi)}** "
             f"({sum(h['nb_annonces'] for h in multi)} annonces)")
    sans_host = sum(1 for l in lignes if not l.get("host_id"))
    L.append(f"- annonces sans host_id identifiable : {sans_host} "
             f"({sans_host / len(lignes):.1%} — annonces sans avis)"
             if lignes else "")

    if bilan_p1:
        L.append("\n## 2. Exhaustivité de la collecte\n")
        L.append(f"Plafond mesuré par recherche : "
                 f"**{bilan_p1.get('plafond_par_recherche')}** résultats.")
        L.append("Le tuilage récursif subdivise toute tuile saturée ; "
                 "les tuiles ci-dessous sont restées saturées à la taille "
                 "plancher, l'inventaire y est donc **possiblement incomplet**.\n")
        L.append("| Commune | Annonces | Tuiles interrogées | Zones encore saturées |")
        L.append("|---|---:|---:|---:|")
        for c in bilan_p1.get("communes", []):
            L.append(f"| {c['commune']} | {c['annonces']} | "
                     f"{c['tuiles_interrogees']} | "
                     f"{c['tuiles_saturees_residuelles']} |")
        total_sat = sum(c["tuiles_saturees_residuelles"]
                        for c in bilan_p1.get("communes", []))
        if total_sat:
            L.append(f"\n⚠️ **{total_sat} zones encore saturées** : le nombre "
                     "d'annonces y est un plancher, pas un comptage.")
        else:
            L.append("\n✅ Aucune zone résiduellement saturée : sous réserve du "
                     "comportement d'Airbnb, la couverture géographique est "
                     "complète à la maille interrogée.")

    L.append("\n## 3. Par commune\n")
    L.append("| Commune | Annonces | Hôtes | Capacité méd. | Prix méd. | "
             "Clim | Piscine | Jacuzzi | Parking | Superhost |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for s in stats:
        L.append(f"| {s['commune']} | {s['nb_annonces']} | {s['nb_hotes']} | "
                 f"{s['capacite_mediane']} | {s['prix_nuit_median']} | "
                 f"{s['pct_clim']} | {s['pct_piscine']} | {s['pct_jacuzzi']} | "
                 f"{s['pct_parking']} | {s['pct_superhost']} |")

    L.append("\n## 4. Taux de remplissage des colonnes\n")
    L.append("Une colonne peu remplie n'est pas une colonne fausse, mais elle "
             "ne peut pas porter une analyse. À lire avant toute exploitation.\n")
    L.append("| Colonne | Rempli |")
    L.append("|---|---:|")
    for col, t in sorted(taux_remplissage(lignes), key=lambda kv: -kv[1]):
        L.append(f"| `{col}` | {t:.0%} |")

    L.append("\n## 5. Limites à connaître\n")
    L.append("1. **Coordonnées floutées.** Airbnb déplace la position publique "
             "des annonces. Aucune annonce n'est rattachable à un logement "
             "précis sur cette seule base.")
    L.append("2. **Pas de numéro d'enregistrement.** Mesuré absent des fiches "
             "pyairbnb : la clé exacte vers une adresse n'existe pas ici.")
    L.append("3. **Taux d'indisponibilité ≠ taux d'occupation.** Airbnb ne "
             "distingue pas une nuit réservée d'une nuit bloquée par l'hôte.")
    L.append("4. **host_id absent des annonces sans avis** (extrait via le "
             "profil du reviewee).")
    L.append("5. **Photographie à une date.** Le parc Airbnb bouge en continu ; "
             "ces chiffres valent pour la date de collecte indiquée en tête.")
    L.append("6. **`prix_nuit_eur` n'est pas exploitable tel quel.** Valeurs "
             "aberrantes observées dès le premier lot (972 € et 1,00 € la nuit "
             "sur des T2) : selon les annonces, Airbnb renvoie un prix nuitée, "
             "un total de séjour ou un prix promotionnel, sans le dire. "
             "Ne pas construire d'analyse de revenus dessus sans requalifier "
             "ce champ.")

    chemin.write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sortie", default="sig_agglo_data/airbnb")
    args = p.parse_args()

    sortie = Path(args.sortie)
    dossier = sortie / "export"
    dossier.mkdir(parents=True, exist_ok=True)

    lignes = charger_lignes(sortie)
    lignes = localiser(lignes, sortie)

    # Colonnes prioritaires en tête, pour un CSV lisible à l'ouverture.
    tete = ["room_id", "url", "commune_contour", "code_insee_contour",
            "localisation_statut", "nom", "type_logement", "capacite",
            "prix_nuit_eur", "note", "nb_avis", "superhost", "host_id",
            "host_nom", "latitude_airbnb", "longitude_airbnb", "x_l93", "y_l93"]
    tete += [f"eq_{c}" for c in equip.COLONNES_PRIORITAIRES]
    reste = [k for k in (lignes[0].keys() if lignes else []) if k not in tete]

    ecrire_csv(dossier / "annonces.csv", lignes, tete + reste)

    hotes = agreger_hotes(lignes)
    ecrire_csv(dossier / "hotes.csv", hotes)

    chemin_eq = sortie / "passage2" / "equipements_long.json"
    if chemin_eq.exists():
        ecrire_csv(dossier / "equipements.csv",
                   json.loads(chemin_eq.read_text(encoding="utf-8")))

    stats = stats_communes(lignes)
    ecrire_csv(dossier / "stats_communes.csv", stats)

    ecrire_rapport(dossier / "rapport-collecte.md", lignes, hotes, stats, sortie)

    print(f"{len(lignes)} annonces, {len(hotes)} hôtes")
    print(f"  -> {dossier / 'annonces.csv'}")
    print(f"  -> {dossier / 'hotes.csv'}")
    print(f"  -> {dossier / 'equipements.csv'}")
    print(f"  -> {dossier / 'stats_communes.csv'}")
    print(f"  -> {dossier / 'rapport-collecte.md'}")

    hors = Counter(l["localisation_statut"] for l in lignes)
    print("\n  localisation :", dict(hors))
    multi = [h for h in hotes if h["nb_annonces"] > 1]
    if multi:
        print(f"\n  {len(multi)} hôtes multi-annonces ; top 5 :")
        for h in multi[:5]:
            print(f"    {h['nb_annonces']:3d} annonces — {h['host_nom']} "
                  f"({h['communes']})")


if __name__ == "__main__":
    main()
