"""Extraction des DPE de l'ADEME sur les 14 communes de l'agglo.

Jeu de données `meg-83tjwtg8dyz4vv7h1dqe` — « DPE Logements existants depuis
juillet 2021 », 15,5 millions de lignes en France, **34 156 sur le périmètre**.
API ouverte : aucune clé, aucune inscription. Rien n'est envoyé à l'ADEME que le
code INSEE de la commune demandée.

Le DPE apporte ce que le cadastre ne donne pas — étiquette énergie, **surface
habitable**, coût annuel de chauffage, type d'installation — mais il ne porte
**aucune référence cadastrale** : ni parcelle, ni section, ni invariant. Les 230
champs ont été passés en revue. Le rattachement se fera donc par l'adresse puis
par les coordonnées (Lambert-93, le même système que les parcelles projetées),
et **à la maille parcelle**, jamais au logement : rien ne permet de dire lequel
des 200 appartements d'un immeuble porte le DPE relevé.

Usage :
    python scripts/sig_agglo_dpe.py
    python scripts/sig_agglo_dpe.py --commune 34301
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sig_agglo_classeur import COMMUNES_AGGLO  # noqa: E402
from sig_agglo_extract import proteger_dossier  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

JEU = "meg-83tjwtg8dyz4vv7h1dqe"
JEU_TERTIAIRE = "j9ol0fwjqckyf49vr29nknbu"
PAGE = 5000
TIMEOUT = 120

# Agde n'est pas dans l'agglo, mais elle est dans le périmètre commercial du
# tertiaire (cf. cibles-tertiaires-decisions.md) : le DPE, lui, la couvre.
AGDE = "34003"

# Le jeu tertiaire a son propre schéma : surfaces, secteur d'activité et
# catégorie ERP à la place des caractéristiques de logement.
CHAMPS_TERTIAIRE = [
    "numero_dpe", "date_etablissement_dpe",
    "identifiant_ban", "adresse_ban", "numero_voie_ban", "nom_rue_ban",
    "code_postal_ban", "code_insee_ban", "statut_geocodage",
    "coordonnee_cartographique_x_ban", "coordonnee_cartographique_y_ban",
    "etiquette_dpe", "etiquette_ges",
    "surface_shon", "surface_utile", "secteur_activite", "categorie_erp",
    "annee_construction", "conso_kwhep_m2_an", "conso_ep_energie_n1",
    "annee_releve_conso_energie_n1", "type_energie_principale_chauffage",
    "complement_adresse_batiment", "numero_immatriculation_copropriete",
]

# Sur 230 champs, ceux qui décrivent le logement ou permettent de le situer.
CHAMPS = [
    "numero_dpe", "date_etablissement_dpe",
    "identifiant_ban", "adresse_ban", "numero_voie_ban", "nom_rue_ban",
    "code_postal_ban", "code_insee_ban", "statut_geocodage",
    "coordonnee_cartographique_x_ban", "coordonnee_cartographique_y_ban",
    "etiquette_dpe", "etiquette_ges",
    "type_batiment", "annee_construction", "periode_construction",
    "surface_habitable_logement", "complement_adresse_batiment",
    "conso_5_usages_par_m2_ep", "emission_ges_5_usages_par_m2",
    "cout_total_5_usages", "type_installation_chauffage",
    "type_energie_principale_chauffage", "nombre_niveau_logement",
]


def extraire_commune(
    session: requests.Session, insee: str, writer, champs: list[str], base: str
) -> int:
    """Pagine les DPE d'une commune. data-fair fournit le lien suivant lui-même."""

    params = {
        "qs": f"code_insee_ban:{insee}",
        "size": PAGE,
        "select": ",".join(champs),
    }
    url, ecrites = base, 0
    while url:
        for tentative in range(4):
            try:
                reponse = session.get(url, params=params if url == base else None, timeout=TIMEOUT)
                break
            except requests.RequestException:
                time.sleep(1 + tentative * 2)
        else:
            print(f"    [!] {insee} : abandon après 4 tentatives")
            break
        if reponse.status_code != 200:
            print(f"    [!] {insee} : HTTP {reponse.status_code}")
            break
        charge = reponse.json()
        lignes = charge.get("results") or []
        if not lignes:
            break
        for ligne in lignes:
            writer.writerow({c: ligne.get(c, "") for c in champs})
        ecrites += len(lignes)
        url = charge.get("next")
        print(f"    {insee} : {ecrites:>6}", end="\r")
    return ecrites


def main() -> int:
    parser = argparse.ArgumentParser(description="Extraction des DPE ADEME sur l'agglo.")
    parser.add_argument("--out", default="sig_agglo_data", help="dossier de sortie")
    parser.add_argument("--commune", help="un seul code INSEE (défaut : les 14)")
    parser.add_argument(
        "--tertiaire", action="store_true",
        help="jeu DPE Tertiaire au lieu des logements, et Agde en plus",
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    proteger_dossier(out_dir)
    session = requests.Session()

    jeu = JEU_TERTIAIRE if args.tertiaire else JEU
    voulus = CHAMPS_TERTIAIRE if args.tertiaire else CHAMPS
    base = f"https://data.ademe.fr/data-fair/api/v1/datasets/{jeu}/lines"

    # Le schéma évolue : ne demander que les champs réellement servis, sinon
    # l'API rejette la requête entière pour un seul nom inconnu.
    schema = session.get(
        f"https://data.ademe.fr/data-fair/api/v1/datasets/{jeu}/schema", timeout=TIMEOUT
    )
    disponibles = {c.get("key") for c in schema.json()} if schema.status_code == 200 else set()
    champs = [c for c in voulus if c in disponibles] or voulus
    manquants = [c for c in voulus if c not in disponibles]
    if manquants:
        print(f"[schema] champs absents du jeu, ignorés : {', '.join(manquants)}")

    if args.commune:
        communes = [args.commune]
    else:
        communes = sorted(COMMUNES_AGGLO) + ([AGDE] if args.tertiaire else [])
    cible = out_dir / ("dpe_tertiaire.csv" if args.tertiaire else "dpe_ademe.csv")
    total = 0
    with cible.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=champs, extrasaction="ignore")
        writer.writeheader()
        for insee in communes:
            total += extraire_commune(session, insee, writer, champs, base)
            print(f"    {insee} : {total:>6} au total")

    print(f"\n{total} DPE écrits dans {cible.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
