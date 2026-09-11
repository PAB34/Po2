"""Inventaire des couches du SIG rattachables à une parcelle cadastrale.

Le catalogue annonce 1 069 couches ; la question utile n'est pas « lesquelles
existent » mais « lesquelles se joignent au cadastre sans bricolage ». Ce script
interroge chaque couche pour une ligne, relève ses colonnes, et signale celles
qui portent un identifiant de parcelle (`id_par`, `id_uf`, `parcelle`…).

Sortie : `inventaire_couches.csv` — une ligne par couche, avec ses colonnes, son
volume et la clé de jointure repérée. C'est le point de départ du classeur
agrégé, qui ne peut rattacher que ce qui porte une clé.

Usage :
    python scripts/sig_agglo_inventaire.py
    python scripts/sig_agglo_inventaire.py --workers 8
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sig_agglo_recon import DEFAULT_BASE_URL, fetch, load_env, login, rows_of  # noqa: E402

# Colonnes qui permettent un rattachement direct au cadastre, par ordre de
# préférence : une référence de parcelle vaut mieux qu'une simple commune.
CLES = ["id_par", "idpar", "id_parcelle", "parcelle", "geo_parcelle", "id_uf", "idu", "ref_cad"]
CLES_FAIBLES = ["id_com", "insee", "code_insee", "commune", "libcom"]

# Chercher la clé par le nom de colonne ne suffit pas : la couche des
# copropriétés range une référence de parcelle parfaitement valide dans une
# colonne nommée `idtup`. On teste donc aussi la *forme* des valeurs —
# commune (5) + préfixe (3) + section (2) + numéro (4), ex. 34301000AN0097.
# Un SIRET fait lui aussi 14 caractères : sans plus de contrainte, la détection
# par forme confond les deux. Deux garde-fous tirés du format cadastral —
# le code commune de l'Hérault, et une section qui porte au moins une lettre.
FORME_ID_PAR = re.compile(r"^34\d{3}[0-9A-Z]{3}(?=[0-9A-Z]{2}\d{4}$)[0-9A-Z]*[A-Z][0-9A-Z]*$")
COLONNES_INTERDITES = {"siret", "siren", "num_pdl", "code_ape"}


def sonder(session: requests.Session, base_url: str, couche: dict) -> dict:
    layer_id = couche.get("layer_id")
    status, payload = fetch(session, base_url, f"vmap/layers/{layer_id}/query", limit=1)
    lignes = rows_of(payload)
    colonnes = list(lignes[0]) if lignes else []
    minuscules = {c.lower(): c for c in colonnes}
    # Le nom seul ne prouve rien : la couche des départs de feu a bien une
    # colonne `idu`, mais elle contient « 20190915_FABREGUES_1254_ef4 ». Une clé
    # trouvée par son nom n'est retenue que si sa valeur en a aussi la forme —
    # sauf `parcelle`/`section`, volontairement partiels et reconstruits ailleurs.
    par_nom = next((minuscules[c] for c in CLES if c in minuscules), "")
    if par_nom and par_nom.lower() not in {"parcelle", "section"} and lignes:
        valeur = str(lignes[0].get(par_nom) or "").strip()
        if valeur and not FORME_ID_PAR.match(valeur):
            par_nom = ""
    cle = par_nom
    par_forme = ""
    if lignes:
        par_forme = next(
            (
                c
                for c, v in lignes[0].items()
                if c.lower() not in COLONNES_INTERDITES
                and isinstance(v, str)
                and FORME_ID_PAR.match(v.strip())
            ),
            "",
        )
    cle = cle or par_forme
    cle_faible = next((minuscules[c] for c in CLES_FAIBLES if c in minuscules), "")
    total = payload.get("total_row_number") if isinstance(payload, dict) else None
    return {
        "layer_id": layer_id,
        "nom": couche.get("name"),
        "table": f"{couche.get('schema')}.{couche.get('pg_table')}",
        "http": status,
        "lignes": total if total is not None else "",
        "nb_colonnes": len(colonnes),
        "cle_parcelle": cle,
        "cle_detectee_par": "nom + forme" if par_nom else ("forme des valeurs" if cle else ""),
        "cle_commune": cle_faible,
        "colonnes": "|".join(colonnes),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventaire des couches joignables au cadastre.")
    parser.add_argument("--env", help="chemin d'un fichier .env")
    parser.add_argument("--out", default="sig_agglo_data", help="dossier de sortie")
    parser.add_argument("--workers", type=int, default=8, help="requêtes simultanées")
    args = parser.parse_args()

    env = load_env(args.env)

    def setting(name: str, default: str = "") -> str:
        return env.get(name) or os.environ.get(name) or default

    base_url = setting("SIG_AGGLO_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    session = requests.Session()
    session.headers["Authorization"] = login(
        session, base_url, setting("SIG_AGGLO_USER"), setting("SIG_AGGLO_PASSWORD")
    )

    status, payload = fetch(session, base_url, "vmap/layers")
    couches = rows_of(payload)
    if not couches:
        raise SystemExit(f"Catalogue illisible (HTTP {status})")
    print(f"[api] {len(couches)} couches à sonder")

    resultats = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for index, ligne in enumerate(
            pool.map(lambda c: sonder(session, base_url, c), couches), start=1
        ):
            resultats.append(ligne)
            if index % 50 == 0:
                print(f"    {index}/{len(couches)}", end="\r")

    cible = Path(args.out) / "inventaire_couches.csv"
    with cible.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(resultats[0]))
        writer.writeheader()
        writer.writerows(resultats)

    lisibles = [r for r in resultats if r["http"] == 200 and r["nb_colonnes"]]
    joignables = [r for r in lisibles if r["cle_parcelle"]]
    print(f"\n{len(resultats)} couches sondées")
    print(f"  {len(lisibles)} lisibles par ce compte")
    print(f"  {len(joignables)} portent une clé parcelle")
    print(f"\n-> {cible.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
