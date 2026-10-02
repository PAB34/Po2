"""Collecte des établissements tertiaires — 14 communes de l'agglo + Agde.

Source : **API Recherche d'entreprises** de data.gouv.fr, ouverte et sans clé.
Elle remplace la couche SIG 60 `economie.vmp_etab_eco`, qui s'arrête à l'agglo
(une seule ligne à Agde), laisse 4 560 établissements sans commune et ne porte
ni coordonnées ni état administratif. Décisions et périmètre :
`docs/refonte-v1/cibles-tertiaires-decisions.md`.

Agde pèse lourd dans ce périmètre — 109 hôtels et 65 campings contre 91 et 51
sur toute l'agglo — mais le cadastre y est muet côté propriétaires : le fichier
le dira colonne par colonne plutôt que de laisser croire à un trou de données.

L'API plafonne à 25 résultats par page ; la collecte est donc paginée par couple
(commune, code d'activité), avec une temporisation volontaire.

Usage :
    python scripts/sig_agglo_tertiaire.py
    python scripts/sig_agglo_tertiaire.py --commune 34003
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sig_agglo_extract import proteger_dossier  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

API = "https://recherche-entreprises.api.gouv.fr/search"
PAGE = 25
PAUSE = 0.18  # ~5 requêtes/s : l'API en encaisse 6, on reste en deçà.
TIMEOUT = 60

COMMUNES = {
    "34003": "Agde",
    "34023": "Balaruc-les-Bains", "34024": "Balaruc-le-Vieux", "34039": "Bouzigues",
    "34108": "Frontignan", "34113": "Gigean", "34143": "Loupian", "34150": "Marseillan",
    "34157": "Mèze", "34159": "Mireval", "34165": "Montbazin", "34213": "Poussan",
    "34301": "Sète", "34333": "Vic-la-Gardiole", "34341": "Villeveyrac",
}

# Les 12 segments du business model, traduits en codes d'activité, avec le rang
# de priorité commerciale. Le rang suit la logique de ciblage du modèle :
# plusieurs bâtiments, CVC lourd, factures fortes, pas de technicien interne.
SEGMENTS: list[tuple[int, str, list[str]]] = [
    (1, "Hôtellerie de plein air et hébergement touristique",
     ["55.10Z", "55.20Z", "55.30Z", "55.90Z"]),
    (2, "Administrateurs de biens, syndics, agences",
     ["68.32A", "68.32B", "68.31Z"]),
    (3, "Santé et hébergement médico-social",
     ["86.10Z", "87.10A", "87.10B", "87.10C", "87.20A", "87.20B", "87.30A", "87.30B"]),
    (3, "Grandes et moyennes surfaces",
     ["47.11B", "47.11C", "47.11D", "47.11E", "47.11F", "47.19A", "47.19B",
      "47.30Z", "47.52B", "47.54Z"]),
    (4, "Concessions et garages",
     ["45.11Z", "45.19Z", "45.20A", "45.20B"]),
    (4, "Foncières, SCI et marchands de biens",
     ["68.20A", "68.20B", "68.10Z", "64.20Z"]),
    (5, "Industrie et agroalimentaire",
     ["10.11Z", "10.12Z", "10.13A", "10.13B", "10.20Z", "10.31Z", "10.32Z", "10.39A",
      "10.39B", "10.51A", "10.51B", "10.71A", "10.71B", "10.71C", "10.71D", "10.72Z",
      "10.73Z", "10.85Z", "10.89Z", "11.02A", "11.02B", "11.05Z", "11.07A", "11.07B",
      "20.14Z", "20.30Z", "20.41Z", "22.21Z", "22.22Z", "22.29A", "22.29B",
      "23.61Z", "23.63Z", "23.70Z", "25.11Z", "25.12Z", "25.61Z", "25.62A", "25.62B"]),
    (5, "Équipements sportifs et de loisirs", ["93.11Z", "93.21Z"]),
    (6, "Restauration", ["56.10A", "56.10C", "56.21Z", "56.29A", "56.29B", "56.30Z"]),
]

COLONNES = [
    "siret", "siren", "nom_entreprise", "enseigne", "nom_commercial",
    "segment", "priorite", "naf", "libelle_naf",
    "adresse", "code_postal", "commune", "code_commune", "latitude", "longitude",
    "tranche_effectif", "caractere_employeur", "categorie_entreprise",
    "etat_administratif", "est_siege", "nombre_etablissements",
    "date_creation", "qualifications_rge",
]


def collecter(
    session: requests.Session, insee: str, naf: str | None = None, rge: bool = False
) -> list[dict]:
    """Pagine une recherche (commune, activité ou RGE). L'API plafonne à 25/page."""

    resultats, page = [], 1
    while True:
        for tentative in range(4):
            try:
                criteres: dict[str, object] = {
                    "code_commune": insee,
                    "per_page": PAGE,
                    "page": page,
                }
                if naf:
                    criteres["activite_principale"] = naf
                if rge:
                    criteres["est_rge"] = "true"
                reponse = session.get(API, params=criteres, timeout=TIMEOUT)
                break
            except requests.RequestException:
                time.sleep(1 + tentative * 2)
        else:
            print(f"    [!] {insee}/{naf} : abandon")
            return resultats
        if reponse.status_code == 429:
            time.sleep(2)
            continue
        if reponse.status_code != 200:
            print(f"    [!] {insee}/{naf} : HTTP {reponse.status_code}")
            return resultats
        lignes = reponse.json().get("results") or []
        if not lignes:
            return resultats
        resultats.extend(lignes)
        page += 1
        time.sleep(PAUSE)


def aplatir(entreprise: dict, etablissement: dict, segment: str, priorite: int) -> dict:
    """Une ligne par établissement, en gardant ce qui sert à qualifier la cible."""

    enseignes = etablissement.get("liste_enseignes") or []
    rge = etablissement.get("liste_rge") or []
    return {
        "siret": etablissement.get("siret", ""),
        "siren": entreprise.get("siren", ""),
        "nom_entreprise": entreprise.get("nom_complet", ""),
        "enseigne": " / ".join(enseignes),
        "nom_commercial": etablissement.get("nom_commercial") or "",
        "segment": segment,
        "priorite": priorite,
        "naf": etablissement.get("activite_principale", ""),
        "libelle_naf": entreprise.get("activite_principale_naf25", "") or "",
        "adresse": etablissement.get("adresse", ""),
        "code_postal": etablissement.get("code_postal", ""),
        "commune": etablissement.get("libelle_commune", ""),
        # `commune` porte le code INSEE, `libelle_commune` le nom ; `geo_id` est
        # un identifiant d'adresse et ne commence pas par le code commune.
        "code_commune": etablissement.get("commune", ""),
        "latitude": etablissement.get("latitude") or "",
        "longitude": etablissement.get("longitude") or "",
        "tranche_effectif": etablissement.get("tranche_effectif_salarie") or "",
        "caractere_employeur": etablissement.get("caractere_employeur") or "",
        "categorie_entreprise": entreprise.get("categorie_entreprise") or "",
        "etat_administratif": etablissement.get("etat_administratif", ""),
        "est_siege": etablissement.get("est_siege", ""),
        "nombre_etablissements": entreprise.get("nombre_etablissements", ""),
        "date_creation": etablissement.get("date_creation") or "",
        "qualifications_rge": " / ".join(rge),
    }


def collecter_rge(session: requests.Session, communes: dict[str, str], out_dir: Path) -> int:
    """Entreprises qualifiées RGE du territoire — le vivier de partenaires.

    §6 du business model : la société garde la relation client et confie
    l'exécution à des spécialistes qualifiés et assurés. L'API expose le
    marqueur RGE, ce qui donne cette liste sans la constituer à la main. Ici on
    ne filtre pas sur l'activité : un RGE est par construction une entreprise du
    bâtiment ou de l'étude.
    """

    cible = out_dir / "tertiaire_partenaires_rge.csv"
    vus: set[str] = set()
    total = 0
    with cible.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLONNES, extrasaction="ignore")
        writer.writeheader()
        for insee, nom in communes.items():
            for entreprise in collecter(session, insee, rge=True):
                for etablissement in entreprise.get("matching_etablissements") or []:
                    siret = etablissement.get("siret", "")
                    if not siret or siret in vus:
                        continue
                    vus.add(siret)
                    writer.writerow(aplatir(entreprise, etablissement, "Partenaire RGE", 0))
                    total += 1
            print(f"    {nom:22} {total:>5} au total")
    print(f"\n{total} entreprises RGE écrites dans {cible.resolve()}")
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="Collecte des cibles tertiaires.")
    parser.add_argument("--out", default="sig_agglo_data")
    parser.add_argument("--commune", help="un seul code INSEE")
    parser.add_argument(
        "--rge", action="store_true",
        help="collecte les entreprises qualifiées RGE (vivier de partenaires)",
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    proteger_dossier(out_dir)
    session = requests.Session()
    communes = {args.commune: COMMUNES.get(args.commune, args.commune)} if args.commune else COMMUNES

    if args.rge:
        return 0 if collecter_rge(session, communes, out_dir) >= 0 else 1

    cible = out_dir / "tertiaire_etablissements.csv"
    vus: set[tuple[str, str]] = set()
    total = 0
    with cible.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLONNES, extrasaction="ignore")
        writer.writeheader()
        for insee, nom in communes.items():
            avant = total
            for priorite, segment, codes in SEGMENTS:
                for naf in codes:
                    for entreprise in collecter(session, insee, naf):
                        etablissements = entreprise.get("matching_etablissements") or []
                        for etablissement in etablissements:
                            siret = etablissement.get("siret", "")
                            # Un établissement peut ressortir sur deux codes
                            # proches : la clé (siret, commune) tranche.
                            cle = (siret, insee)
                            if not siret or cle in vus:
                                continue
                            vus.add(cle)
                            writer.writerow(aplatir(entreprise, etablissement, segment, priorite))
                            total += 1
            print(f"    {nom:22} {total - avant:>6} établissements  (total {total})")

    print(f"\n{total} établissements écrits dans {cible.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
