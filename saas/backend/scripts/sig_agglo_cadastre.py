"""Extraction du module cadastre / MAJIC du SIG de l'agglo — maille LOCAL.

Complète `sig_agglo_extract.py`, qui s'arrêtait à la parcelle. Une parcelle en
copropriété n'a qu'un propriétaire — le syndicat — et masque les propriétaires
des appartements. Ceux-ci vivent dans un module `cadastre` de vMap, invisible
dans le catalogue des couches, servi par ses propres routes REST et adossé au
schéma PostgreSQL `s_majic`.

Routes utilisées (relevées dans le module Angular chargé à la demande) :

  GET /cadastre/invariants            les locaux : invariant, parcelle, compte
  GET /cadastre/proprietaires         comptes propriétaires : nom, n° de compte
  GET /cadastre/adresses              adresse cadastrale exacte par parcelle
  GET /cadastre/descriptionparcelles  descriptif complet + compte propriétaire
  GET /cadastre/fichedescriptiveparcelle/{id_par}
      la fiche complète : propriétaires ET tous les locaux, avec type, nature,
      occupation, date de mutation et année de construction

Les quatre premières sont paginées et se récupèrent en quelques minutes. La
cinquième demande un appel par parcelle : le mode `--fiches` est donc
**reprenable** — il relit ce qui a déjà été écrit et repart où il s'était arrêté.

⚠️ Les fiches contiennent des données personnelles plus sensibles encore que
l'extraction parcellaire : date et lieu de naissance des propriétaires. Le
dossier de sortie est protégé de git par son propre `.gitignore`.

Usage :
    python scripts/sig_agglo_cadastre.py --tables
    python scripts/sig_agglo_cadastre.py --fiches
    python scripts/sig_agglo_cadastre.py --fiches --commune 34301
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sig_agglo_extract import proteger_dossier  # noqa: E402
from sig_agglo_recon import DEFAULT_BASE_URL, load_env, login  # noqa: E402

TIMEOUT = 60
PAGE = 5000

# Tables paginées : nom de sortie → route.
TABLES = {
    "locaux": "cadastre/invariants",
    "proprietaires_comptes": "cadastre/proprietaires",
    "adresses_parcelle": "cadastre/adresses",
    "description_parcelles": "cadastre/descriptionparcelles",
}

# Colonnes retenues des deux listes imbriquées de la fiche.
COLS_BATI = ["ID_BAT", "INVAR", "L_DTELOC", "L_CCONLC", "L_DNATLC", "JDATAT", "JANNAT", "DDENOM"]
COLS_PROP = [
    "DQUALP", "DNUPRO", "DDENOM", "DNOMUS", "JDATNSS", "DLDNSS",
    "DLIGN3", "DLIGN4", "DLIGN6", "L_CCODEM", "L_CCODRO", "GDESIP",
]


class Client:
    """Session vMap avec ré-authentification automatique et retours tolérants.

    Le jeton vit une heure ; une extraction de fiches en dure plusieurs. Chaque
    fil a sa propre session HTTP, mais tous partagent le même jeton, renouvelé
    sous verrou dès qu'une réponse 401 arrive.
    """

    def __init__(self, base_url: str, user: str, password: str) -> None:
        self.base_url = base_url
        self._user, self._password = user, password
        self._lock = threading.Lock()
        self._local = threading.local()
        self.token = ""
        self._renouveler()

    def _renouveler(self) -> None:
        with self._lock:
            session = requests.Session()
            self.token = login(session, self.base_url, self._user, self._password)

    def _session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            session.headers.update({"Accept": "application/json"})
            self._local.session = session
        session.headers["Authorization"] = self.token
        return session

    def get(self, path: str, **params: Any) -> tuple[int, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        for tentative in range(4):
            try:
                response = self._session().get(url, params=params or None, timeout=TIMEOUT)
            except requests.RequestException:
                time.sleep(1 + tentative * 2)
                continue
            if response.status_code == 401:
                self._renouveler()
                continue
            if response.status_code >= 500:
                time.sleep(1 + tentative * 2)
                continue
            try:
                return response.status_code, response.json()
            except ValueError:
                return response.status_code, None
        return 0, None


def extraire_table(client: Client, nom: str, route: str, out_dir: Path, commune: str | None) -> int:
    """Télécharge une table paginée dans un CSV."""

    cible = out_dir / f"cadastre_{nom}.csv"
    params: dict[str, Any] = {"limit": PAGE}
    if commune:
        params["id_com"] = commune

    ecrites, total, writer = 0, None, None
    with cible.open("w", encoding="utf-8-sig", newline="") as handle:
        offset = 0
        while True:
            status, payload = client.get(route, **params, offset=offset)
            if status != 200 or not isinstance(payload, dict):
                print(f"    [!] arret a l'offset {offset} (HTTP {status})")
                break
            lignes = [r for r in (payload.get("data") or []) if isinstance(r, dict)]
            if total is None:
                total = payload.get("total_row_number")
            if not lignes:
                break
            if writer is None:
                writer = csv.DictWriter(
                    handle, fieldnames=[c for c in lignes[0] if c != "geom"], extrasaction="ignore"
                )
                writer.writeheader()
            writer.writerows(lignes)
            ecrites += len(lignes)
            offset += len(lignes)
            print(f"    {ecrites:>7} / {total or '?'}", end="\r")
            if total is not None and offset >= total:
                break
    print(f"    {ecrites:>7} lignes -> {cible.name}" + " " * 14)
    return ecrites


def _ids(chemin: Path, avec_contenu: str | None = None) -> set[str]:
    """Lit les id_par d'un CSV partiel, éventuellement ceux qui ont du contenu."""

    if not chemin.is_file():
        return set()
    with chemin.open(encoding="utf-8-sig", newline="") as handle:
        return {
            row["id_par"]
            for row in csv.DictReader(handle)
            if row.get("id_par") and (avec_contenu is None or (row.get(avec_contenu) or "").strip())
        }


def index_reprise(out_dir: Path) -> Path:
    """Construit — ou reconstruit — l'index des parcelles réellement traitées.

    Une parcelle a toujours au moins un propriétaire : une ligne sans local NI
    propriétaire est donc un échec, pas un résultat vide. Ces parcelles-là sont
    volontairement laissées hors de l'index pour être rejouées à la reprise.
    """

    index = out_dir / "fiche_parcelles_ok.csv"
    if index.is_file():
        return index
    reussies = _ids(out_dir / "fiche_locaux.csv", "ID_BAT") | _ids(
        out_dir / "fiche_proprietaires.csv", "DNUPRO"
    )
    with index.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id_par"])
        writer.writerows([[p] for p in sorted(reussies)])
    if reussies:
        print(f"    index de reprise reconstruit : {len(reussies)} parcelles deja traitees")
    return index


def extraire_fiches(
    client: Client, out_dir: Path, commune: str | None, workers: int
) -> tuple[int, int]:
    """Appelle la fiche descriptive de chaque parcelle et déplie ses deux listes."""

    source = out_dir / "cadastre_description_parcelles.csv"
    if not source.is_file():
        raise SystemExit(f"Manque {source.name} : lancer d'abord --tables.")
    with source.open(encoding="utf-8-sig", newline="") as handle:
        parcelles = [
            r["ID_PAR"]
            for r in csv.DictReader(handle)
            if r.get("ID_PAR") and (not commune or r.get("ID_COM") == commune)
        ]
    parcelles = sorted(set(parcelles))

    f_locaux = out_dir / "fiche_locaux.csv"
    f_prop = out_dir / "fiche_proprietaires.csv"
    f_index = index_reprise(out_dir)
    faites = _ids(f_index)
    restantes = [p for p in parcelles if p not in faites]
    print(f"    {len(parcelles)} parcelles, {len(faites)} deja faites, {len(restantes)} a traiter")

    mode = "a" if faites else "w"
    n_loc = n_prop = n_echec = 0
    debut = time.time()

    with f_locaux.open(mode, encoding="utf-8-sig", newline="") as hl, \
         f_prop.open(mode, encoding="utf-8-sig", newline="") as hp, \
         f_index.open("a", encoding="utf-8-sig", newline="") as hi:
        w_loc = csv.DictWriter(hl, fieldnames=["id_par"] + COLS_BATI, extrasaction="ignore")
        w_prop = csv.DictWriter(hp, fieldnames=["id_par"] + COLS_PROP, extrasaction="ignore")
        w_index = csv.writer(hi)
        if mode == "w":
            w_loc.writeheader()
            w_prop.writeheader()

        def fiche(id_par: str) -> tuple[str, Any]:
            status, payload = client.get(f"cadastre/fichedescriptiveparcelle/{id_par}")
            return id_par, (payload or {}).get("data") if status == 200 else None

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(fiche, p) for p in restantes]
            for index, future in enumerate(as_completed(futures), start=1):
                id_par, data = future.result()
                if isinstance(data, dict):
                    for bati in data.get("aBatis") or []:
                        if isinstance(bati, dict):
                            w_loc.writerow({"id_par": id_par, **bati})
                            n_loc += 1
                    for prop in data.get("aProprietaires") or []:
                        if isinstance(prop, dict):
                            w_prop.writerow({"id_par": id_par, **prop})
                            n_prop += 1
                    w_index.writerow([id_par])
                else:
                    # Pas d'index : la parcelle sera rejouee a la prochaine reprise.
                    n_echec += 1
                if index % 500 == 0:
                    hl.flush()
                    hp.flush()
                    hi.flush()
                    vitesse = index / max(time.time() - debut, 1)
                    reste = (len(restantes) - index) / max(vitesse, 0.01) / 60
                    print(
                        f"    {index:>6}/{len(restantes)} | {n_loc} locaux | "
                        f"{vitesse:.1f}/s | reste ~{reste:.0f} min",
                        end="\r",
                    )
    print(f"    {n_loc} locaux et {n_prop} proprietaires ecrits"
          + (f", {n_echec} parcelles en echec a rejouer" if n_echec else "") + " " * 20)
    return n_loc, n_prop


def main() -> int:
    parser = argparse.ArgumentParser(description="Extraction cadastre/MAJIC a la maille local.")
    parser.add_argument("--env", help="chemin d'un fichier .env")
    parser.add_argument("--out", default="sig_agglo_data", help="dossier de sortie")
    parser.add_argument("--commune", help="code INSEE pour restreindre (ex. 34301 = Sete)")
    parser.add_argument("--tables", action="store_true", help="extrait les 4 tables paginees")
    parser.add_argument("--fiches", action="store_true", help="appelle la fiche de chaque parcelle")
    parser.add_argument("--workers", type=int, default=5, help="appels simultanes (defaut 5)")
    args = parser.parse_args()

    if not args.tables and not args.fiches:
        parser.error("choisir --tables et/ou --fiches")

    env = load_env(args.env)

    def setting(name: str, default: str = "") -> str:
        return env.get(name) or os.environ.get(name) or default

    base_url = setting("SIG_AGGLO_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    user, password = setting("SIG_AGGLO_USER"), setting("SIG_AGGLO_PASSWORD")
    if not user or not password:
        print("Il manque SIG_AGGLO_USER et/ou SIG_AGGLO_PASSWORD (fichier .env).", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    proteger_dossier(out_dir)
    client = Client(base_url, user, password)

    resume: dict[str, Any] = {}
    if args.tables:
        for nom, route in TABLES.items():
            print(f"[table] {nom}")
            resume[nom] = extraire_table(client, nom, route, out_dir, args.commune)
    if args.fiches:
        print("[fiches] fiche descriptive parcelle par parcelle")
        n_loc, n_prop = extraire_fiches(client, out_dir, args.commune, args.workers)
        resume["fiche_locaux"] = n_loc
        resume["fiche_proprietaires"] = n_prop

    (out_dir / "cadastre_extraction.json").write_text(
        json.dumps(resume, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"\nTermine. {sum(resume.values())} lignes au total dans {out_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
