"""Extraction des données foncières du SIG de Sète Agglopôle Méditerranée.

Suite de `sig_agglo_recon.py` : la reconnaissance a dit *ce qui existe*, ce script
*récupère*. Périmètre décidé le 2026-09-03 (cf.
`docs/refonte-v1/sig-agglo-proprietaires-decisions.md` §8) : **toute l'agglo,
propriétaires personnes physiques comprises**.

⚠️ **Ce script écrit des données à caractère personnel sur le disque** (nom, prénom,
civilité et adresse des propriétaires, issus des fichiers fonciers DGFiP/MAJIC).
Trois protections sont câblées et ne dépendent pas de la vigilance de l'opérateur :

  1. le dossier de sortie reçoit un `.gitignore` contenant `*` dès sa création :
     rien de ce qui est extrait ne peut partir dans git, même par `git add -A` ;
  2. un `MANIFESTE.md` daté est écrit à côté des données : origine, finalité,
     volumétrie, date d'extraction — de quoi répondre à la question « d'où vient
     ce fichier et pourquoi » six mois plus tard ;
  3. la géométrie (colonne `geom`, l'essentiel du volume) est écartée par défaut :
     `--avec-geom` pour la conserver.

Usage :
    python scripts/sig_agglo_extract.py                    # tout le périmètre décidé
    python scripts/sig_agglo_extract.py --commune 34301    # Sète seule
    python scripts/sig_agglo_extract.py --couches 474,317  # une sélection
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

import requests

# Console Windows en cp1252 : ne pas planter sur un caractere non encodable.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sig_agglo_recon import DEFAULT_BASE_URL, TIMEOUT, fetch, load_env, login, rows_of  # noqa: E402

# Les couches du périmètre, relevées par la reconnaissance du 2026-09-03.
# `personnel` marque celles qui portent des données nominatives de particuliers.
COUCHES = {
    474: {
        "table": "agglo_s_cadastre.vmp_uf_proprietaire",
        "libelle": "Propriétaire parcelle (nom d'usage)",
        "attendu": 63809,
        "personnel": True,
    },
    317: {
        "table": "foncier.vmp_foncier_public",
        "libelle": "Foncier présumé public (DGFP 2025)",
        "attendu": 17040,
        "personnel": False,
    },
    532: {
        "table": "s_cadastre.v_vmap_unite_fonciere",
        "libelle": "Unité foncière",
        "attendu": 63811,
        "personnel": False,
    },
    943: {
        "table": "agglo_s_cadastre.vmap_fond_cadastral_parcelle",
        "libelle": "Parcelle",
        "attendu": 173365,
        "personnel": False,
    },
    455: {
        "table": "s_cadastre.v_vmap_batiment",
        "libelle": "Bâtiment cadastral",
        "attendu": 100722,
        "personnel": False,
    },
    604: {
        "table": "foncier.vmp_cadhist",
        "libelle": "Historique parcelle",
        "attendu": 91537,
        "personnel": False,
    },
    # Adresse des BIENS (à ne pas confondre avec l'adresse du propriétaire, qui
    # est dans la couche 474). 226 porte section/parcelle : rattachement exact,
    # mais Sète seule. 397 (BAN) couvre tout le territoire, en géométrie seule :
    # le rattachement y est géographique, donc approché.
    226: {
        "table": "adresse.v_sete_adresse",
        "libelle": "Sète — gestion adresse (n° + voie + parcelle)",
        "attendu": 9974,
        "personnel": False,
    },
    397: {
        "table": "referentiels.vmp_ban",
        "libelle": "Numéro adresse (Base Adresse Nationale)",
        "attendu": 80514,
        "personnel": False,
    },
}

PAGE_SIZE = 5000


def proteger_dossier(out_dir: Path) -> None:
    """Rend le dossier d'extraction inaccessible à git, définitivement.

    Un `.gitignore` contenant `*` neutralise même un `git add -A` lancé depuis la
    racine du dépôt. C'est la seule protection qui ne dépend de personne.
    """

    out_dir.mkdir(parents=True, exist_ok=True)
    garde = out_dir / ".gitignore"
    if not garde.exists():
        garde.write_text(
            "# Donnees a caractere personnel (fichiers fonciers DGFiP/MAJIC).\n"
            "# Ce dossier ne doit JAMAIS entrer dans git.\n"
            "*\n",
            encoding="utf-8",
        )
        print(f"[garde] {garde} écrit : le dossier est invisible pour git")


def extraire(
    session: requests.Session,
    base_url: str,
    layer_id: int,
    out_dir: Path,
    commune: str | None,
    avec_geom: bool,
    page_size: int = PAGE_SIZE,
) -> dict[str, Any]:
    """Télécharge une couche entière, page par page, dans un CSV."""

    meta = COUCHES.get(layer_id, {"table": f"layer_{layer_id}", "libelle": str(layer_id)})
    params: dict[str, Any] = {"limit": page_size, "order_by": "gid"}
    if commune:
        params["filter"] = json.dumps(
            {
                "relation": "AND",
                "operators": [
                    {"column": "id_com", "compare_operator": "=", "value": commune}
                ],
            }
        )

    cible = out_dir / f"{layer_id}_{meta['table'].replace('.', '_')}.csv"
    total: int | None = None
    ecrites = 0
    colonnes: list[str] = []
    writer: csv.DictWriter | None = None

    with cible.open("w", encoding="utf-8-sig", newline="") as handle:
        offset = 0
        while True:
            status, payload = fetch(
                session, base_url, f"vmap/layers/{layer_id}/query", **params, offset=offset
            )
            if status != 200 or not isinstance(payload, dict) or payload.get("status") != 1:
                message = payload.get("errorMessage") if isinstance(payload, dict) else status
                print(f"    [!]arret a l'offset {offset} : {message}")
                break
            if total is None:
                total = payload.get("total_row_number")
            lignes = rows_of(payload)
            if not lignes:
                break

            if writer is None:
                colonnes = [c for c in lignes[0] if avec_geom or c != "geom"]
                writer = csv.DictWriter(handle, fieldnames=colonnes, extrasaction="ignore")
                writer.writeheader()
            writer.writerows(lignes)
            ecrites += len(lignes)
            offset += len(lignes)
            print(f"    {ecrites:>7} / {total or '?'}", end="\r")
            if total is not None and offset >= total:
                break

    print(f"    {ecrites:>7} lignes -> {cible.name}" + " " * 12)
    return {
        "layer_id": layer_id,
        "table": meta["table"],
        "libelle": meta["libelle"],
        "fichier": cible.name,
        "lignes": ecrites,
        "total_annonce": total,
        "colonnes": colonnes,
        "personnel": bool(meta.get("personnel")),
    }


def ecrire_manifeste(out_dir: Path, resultats: list[dict[str, Any]], commune: str | None) -> None:
    """Trace l'origine et la finalité de l'extraction, à côté des données."""

    nominatives = [r for r in resultats if r["personnel"]]
    lignes = [
        "# Manifeste d'extraction — données foncières SIG Sète Agglopôle",
        "",
        f"- **Date d'extraction** : {date.today().isoformat()}",
        f"- **Source** : `https://sig.agglopole.fr/rest_vmap2/v2` (vMap 2, compte nominatif)",
        f"- **Périmètre** : {'commune ' + commune if commune else 'toutes les communes de l’agglo'}",
        "- **Finalité** : alimenter le module Patrimoine de Po2 (Ville de Sète) en information",
        "  de propriété foncière, pour identifier et qualifier le patrimoine de la collectivité.",
        "",
        "## Contenu",
        "",
        "| Couche | Table | Lignes | Nominatif |",
        "| --- | --- | ---: | --- |",
    ]
    for r in resultats:
        lignes.append(
            f"| {r['libelle']} | `{r['table']}` | {r['lignes']} | "
            f"{'**oui**' if r['personnel'] else 'non'} |"
        )
    if nominatives:
        lignes += [
            "",
            "## ⚠️ Données à caractère personnel",
            "",
            "Ce dossier contient des données nominatives issues des fichiers fonciers DGFiP/MAJIC",
            "(nom, prénom, civilité, adresse des propriétaires). Leur communication est encadrée",
            "par l'article L. 107 A du livre des procédures fiscales et par le RGPD.",
            "",
            "- ne pas rediffuser, ne pas publier, ne pas déposer sur un partage ouvert ;",
            "- ne pas committer (un `.gitignore` protège déjà ce dossier) ;",
            "- supprimer dès que l'exploitation est terminée, ou fixer une durée de conservation.",
        ]
    (out_dir / "MANIFESTE.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extraction foncière du SIG de l'agglo.")
    parser.add_argument("--env", help="chemin d'un fichier .env")
    parser.add_argument("--out", default="sig_agglo_data", help="dossier de sortie")
    parser.add_argument("--commune", help="code INSEE pour restreindre (ex. 34301 = Sète)")
    parser.add_argument("--couches", help="liste d'identifiants de couches, séparés par des virgules")
    parser.add_argument("--avec-geom", action="store_true", help="conserve la colonne geom")
    parser.add_argument("--page", type=int, default=PAGE_SIZE, help=f"taille de page (défaut {PAGE_SIZE})")
    args = parser.parse_args()

    env = load_env(args.env)

    def setting(name: str, default: str = "") -> str:
        return env.get(name) or os.environ.get(name) or default

    base_url = setting("SIG_AGGLO_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    user, password = setting("SIG_AGGLO_USER"), setting("SIG_AGGLO_PASSWORD")
    if not user or not password:
        print("Il manque SIG_AGGLO_USER et/ou SIG_AGGLO_PASSWORD (fichier .env).", file=sys.stderr)
        return 2

    layer_ids = (
        [int(x) for x in args.couches.split(",") if x.strip()] if args.couches else list(COUCHES)
    )

    out_dir = Path(args.out)
    proteger_dossier(out_dir)

    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    session.headers.update({"Authorization": login(session, base_url, user, password)})

    resultats = []
    for layer_id in layer_ids:
        meta = COUCHES.get(layer_id, {})
        marque = " [!]nominatif" if meta.get("personnel") else ""
        print(f"[extraction] {layer_id} — {meta.get('libelle', layer_id)}{marque}")
        resultats.append(
            extraire(session, base_url, layer_id, out_dir, args.commune, args.avec_geom, args.page)
        )

    ecrire_manifeste(out_dir, resultats, args.commune)
    (out_dir / "extraction.json").write_text(
        json.dumps(resultats, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    total = sum(r["lignes"] for r in resultats)
    print(f"\n{total} lignes extraites dans {out_dir.resolve()}")
    print("  MANIFESTE.md rappelle l'origine, la finalité et les règles de conservation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
