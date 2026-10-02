#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Passage 2 — fiche détaillée de chaque annonce.

Poste le plus coûteux du projet : un appel réseau par annonce. Tout est donc
construit autour du cache : une fiche déjà téléchargée n'est jamais redemandée,
et une interruption se reprend sans perte.

Deux extractions non triviales :

* **host_id** — `details["host"]["id"]` est vide et `get_host_details()` renvoie
  une erreur GraphQL (mesuré sur 6/6 fiches). L'identifiant de l'hôte est en
  revanche présent dans le profil du `reviewee` des avis, qui est l'hôte de
  l'annonce : `reviews[].reviewee…onPressAction.url` = `/users/profile/<id>`.
  Récupéré ainsi sur 8/8 annonces testées — mais seulement si l'annonce a au
  moins un avis.

* **calendrier** — 12 mois jour par jour, ~200 ko par annonce. On en tire un
  résumé d'occupation. Attention à l'interprétation : Airbnb dit `available:
  false` aussi bien pour une nuit réservée que pour une nuit bloquée par
  l'hôte. Le taux calculé est donc un taux d'**indisponibilité**, pas un taux
  d'occupation commerciale. Ne pas le vendre pour ce qu'il n'est pas.

Usage :
    python airbnb_lcd_details.py --communes Sète
    python airbnb_lcd_details.py --toutes --limite 500
"""

from __future__ import annotations

import argparse
import json
import os
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import airbnb_lcd_equipements as equip
from airbnb_lcd_client import ClientAirbnb


def _sans_accent(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn")


def extraire_host(fiche: dict) -> tuple[str | None, str | None, bool]:
    """
    Rend (host_id, nom_hote, trouve_via_avis).

    Cherche d'abord le champ direct (vide en pratique aujourd'hui, mais si
    Airbnb le remplit à nouveau, autant le préférer), puis le contournement
    par le profil du reviewee.
    """
    direct = (fiche.get("host") or {}).get("id")
    if direct:
        return str(direct), (fiche.get("host") or {}).get("name") or None, False

    for avis in fiche.get("reviews") or []:
        reviewee = avis.get("reviewee") or {}
        action = ((reviewee.get("userProfilePicture") or {})
                  .get("onPressAction") or {})
        url = action.get("url") or ""
        if "/users/profile/" in url:
            return url.rsplit("/", 1)[-1], reviewee.get("hostName"), True
    return None, None, False


def resumer_calendrier(fiche: dict) -> dict:
    """
    Résume les 12 mois de calendrier en quelques indicateurs.

    `indispo` agrège nuits réservées ET nuits bloquées par l'hôte : Airbnb ne
    les distingue pas publiquement.
    """
    jours = 0
    indispo = 0
    mois_vus = []
    for mois in fiche.get("calendar") or []:
        libelle = f"{mois.get('year')}-{mois.get('month'):02d}" \
            if mois.get("month") else None
        n_mois = n_indispo_mois = 0
        for jour in mois.get("days") or []:
            n_mois += 1
            if jour.get("available") is False:
                n_indispo_mois += 1
        jours += n_mois
        indispo += n_indispo_mois
        if libelle and n_mois:
            mois_vus.append({"mois": libelle, "jours": n_mois,
                             "indisponibles": n_indispo_mois})

    return {
        "calendrier_jours_publies": jours,
        "calendrier_jours_indisponibles": indispo,
        "calendrier_taux_indisponibilite": round(indispo / jours, 4) if jours else None,
        "calendrier_mois": mois_vus,
    }


def aplatir(annonce: dict, fiche: dict) -> dict:
    """Une ligne exploitable par annonce, à partir de la recherche + la fiche."""
    rid = str(annonce.get("room_id"))
    coords_fiche = fiche.get("coordinates") or {}
    coords_rech = annonce.get("coordinates") or {}

    # pyairbnb écrit "longitud" dans les résultats de recherche (typo amont).
    lon_rech = coords_rech.get("longitude", coords_rech.get("longitud"))
    lat_rech = coords_rech.get("latitude")

    host_id, host_nom, via_avis = extraire_host(fiche)
    rating = annonce.get("rating") or {}
    prix = annonce.get("price") or {}
    unite = prix.get("unit") or {}

    ligne = {
        "room_id": rid,
        "url": f"https://www.airbnb.fr/rooms/{rid}",
        "commune_recherche": annonce.get("_commune_recherche", ""),
        "code_insee_recherche": annonce.get("_code_insee_recherche", ""),
        "nom": annonce.get("name", ""),
        "type_logement": fiche.get("room_type", ""),
        "capacite": fiche.get("person_capacity"),
        "note": rating.get("value"),
        "nb_avis": rating.get("reviewCount"),
        "prix_nuit_eur": unite.get("amount"),
        "superhost": fiche.get("is_super_host"),
        "coup_de_coeur_voyageurs": fiche.get("is_guest_favorite"),
        # Coordonnées : celles de la fiche font foi, celles de la recherche
        # servent de recours. Dans les deux cas, Airbnb les floute.
        "latitude_airbnb": coords_fiche.get("latitude", lat_rech),
        "longitude_airbnb": coords_fiche.get("longitude", lon_rech),
        "host_id": host_id or "",
        "host_nom": host_nom or "",
        "host_id_via_avis": via_avis,
        "nb_equipements_listes": len(equip.lister_equipements(fiche)),
        "collecte_utc": datetime.now(timezone.utc).isoformat(),
    }

    ligne.update(resumer_calendrier(fiche))
    ligne.pop("calendrier_mois", None)  # détail mensuel : fichier séparé

    for cat, val in equip.drapeaux(fiche).items():
        ligne[f"eq_{cat}"] = val

    return ligne


def traiter(sortie: Path, communes: list[str] | None, toutes: bool,
            limite: int | None, pause: float, timeout: int,
            alleger_calendrier: bool, echantillon_brut: int) -> None:
    dossier1 = sortie / "passage1"
    fichiers = sorted(dossier1.glob("annonces_*.json"))
    if not fichiers:
        raise SystemExit(f"Aucun résultat de passage 1 dans {dossier1}. "
                         "Lancer airbnb_lcd_collecte.py d'abord.")

    if not toutes and communes:
        voulues = {_sans_accent(c).lower() for c in communes}
        fichiers = [f for f in fichiers
                    if any(v.replace(" ", "-") in _sans_accent(f.stem).lower()
                           for v in voulues)]
    if not fichiers:
        raise SystemExit("Aucun fichier de passage 1 ne correspond aux communes.")

    client = ClientAirbnb(cache_dir=sortie / "cache_details",
                          pause=pause, timeout=timeout)

    dossier2 = sortie / "passage2"
    dossier2.mkdir(parents=True, exist_ok=True)

    annonces: list[dict] = []
    for f in fichiers:
        annonces.extend(json.loads(f.read_text(encoding="utf-8")))
    # Une annonce peut être vue depuis deux communes voisines (tampon) :
    # on dédoublonne une dernière fois.
    par_id = {str(a.get("room_id")): a for a in annonces if a.get("room_id")}
    a_traiter = list(par_id.values())
    if limite:
        a_traiter = a_traiter[:limite]

    print(f"{len(par_id)} annonces uniques ; {len(a_traiter)} à traiter")
    deja = sum(1 for a in a_traiter if client.en_cache(str(a["room_id"])))
    print(f"{deja} déjà en cache, {len(a_traiter) - deja} à télécharger\n")

    lignes: list[dict] = []
    equipements_longs: list[dict] = []
    calendriers: list[dict] = []
    orphelins: dict[str, int] = {}
    echecs: list[dict] = []

    chemin_lignes = dossier2 / "annonces_details.jsonl"
    # On écrit dans un fichier temporaire renommé à la fin : sans quoi le
    # fichier de sortie reste tronqué pendant toute la durée du passage, et
    # une analyse lancée en parallèle lit un jeu partiel sans s'en douter.
    chemin_tmp = dossier2 / "annonces_details.jsonl.tmp"
    debut = datetime.now(timezone.utc)

    with chemin_tmp.open("w", encoding="utf-8") as sortie_jsonl:
        for i, annonce in enumerate(a_traiter, 1):
            rid = str(annonce["room_id"])
            try:
                fiche = client.details(rid)
            except RuntimeError as exc:
                echecs.append({"room_id": rid, "erreur": str(exc)})
                print(f"  [{i}/{len(a_traiter)}] {rid} ÉCHEC")
                continue

            ligne = aplatir(annonce, fiche)
            lignes.append(ligne)
            sortie_jsonl.write(json.dumps(ligne, ensure_ascii=False) + "\n")

            for e in equip.lister_equipements(fiche):
                equipements_longs.append({"room_id": rid, **e})
            for m in resumer_calendrier(fiche)["calendrier_mois"]:
                calendriers.append({"room_id": rid, **m})
            for lib in equip.libelles_non_classes(fiche):
                orphelins[lib] = orphelins.get(lib, 0) + 1

            if alleger_calendrier and i > echantillon_brut:
                _alleger(client, rid)

            if i % 25 == 0 or i == len(a_traiter):
                ecoule = (datetime.now(timezone.utc) - debut).total_seconds()
                reste = (ecoule / i) * (len(a_traiter) - i)
                print(f"  [{i}/{len(a_traiter)}] {ecoule / 60:.1f} min écoulées, "
                      f"~{reste / 60:.1f} min restantes "
                      f"(cache {client.stats['cache_hits']}, "
                      f"réseau {client.stats['details']})")

    os.replace(chemin_tmp, chemin_lignes)

    _ecrire_json(dossier2 / "equipements_long.json", equipements_longs)
    _ecrire_json(dossier2 / "calendrier_mensuel.json", calendriers)
    _ecrire_json(dossier2 / "equipements_non_classes.json",
                 sorted(({"libelle": k, "occurrences": v}
                         for k, v in orphelins.items()),
                        key=lambda x: -x["occurrences"]))
    _ecrire_json(dossier2 / "echecs_details.json", echecs)

    print(f"\n{len(lignes)} fiches exploitées, {len(echecs)} échecs")
    print(f"  appels réseau : {client.stats['details']}, "
          f"servis par le cache : {client.stats['cache_hits']}")
    sans_host = sum(1 for x in lignes if not x["host_id"])
    print(f"  host_id manquant : {sans_host}/{len(lignes)} "
          f"({sans_host / len(lignes):.1%})" if lignes else "")
    print(f"  -> {chemin_lignes}")
    if orphelins:
        top = sorted(orphelins.items(), key=lambda kv: -kv[1])[:8]
        print("\n  équipements fréquents non classés (à verser au lexique) :")
        for lib, n in top:
            print(f"    {n:5d}  {lib}")


def _alleger(client: ClientAirbnb, room_id: str) -> None:
    """Retire le calendrier du cache : ~200 ko par annonce économisés."""
    chemin = client._chemin_cache(room_id)  # noqa: SLF001
    try:
        fiche = json.loads(chemin.read_text(encoding="utf-8"))
        if "calendar" in fiche:
            fiche["calendar"] = None
            fiche["_calendrier_purge"] = True
            chemin.write_text(json.dumps(fiche, ensure_ascii=False),
                              encoding="utf-8")
    except Exception:  # noqa: BLE001 - l'allègement ne doit jamais bloquer
        pass


def _ecrire_json(chemin: Path, donnees) -> None:
    chemin.write_text(json.dumps(donnees, ensure_ascii=False),
                      encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sortie", default="sig_agglo_data/airbnb")
    p.add_argument("--communes", nargs="*")
    p.add_argument("--toutes", action="store_true")
    p.add_argument("--limite", type=int,
                   help="Ne traiter que les N premières annonces (test).")
    p.add_argument("--pause", type=float, default=1.0)
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--garder-calendriers", action="store_true",
                   help="Conserver le calendrier brut de TOUTES les fiches "
                        "(~200 ko/annonce). Par défaut on n'en garde qu'un "
                        "échantillon et le résumé.")
    p.add_argument("--echantillon-brut", type=int, default=200,
                   help="Nombre de fiches dont le calendrier brut est conservé.")
    args = p.parse_args()

    traiter(Path(args.sortie), args.communes, args.toutes, args.limite,
            args.pause, args.timeout,
            alleger_calendrier=not args.garder_calendriers,
            echantillon_brut=args.echantillon_brut)


if __name__ == "__main__":
    main()
