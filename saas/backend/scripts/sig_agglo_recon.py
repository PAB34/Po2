"""Reconnaissance de l'API vMap2 du SIG de Sète Agglopôle Méditerranée.

Objectif : savoir CE QUI EST DISPONIBLE avant d'écrire le moindre import.
Le script se connecte avec un compte nominatif (identifiants lus dans un
fichier `.env`, jamais en dur, jamais affichés), puis inventorie les couches
accessibles et, pour celles qui touchent au cadastre ou aux propriétaires,
leur **schéma** : nom des colonnes et nombre de lignes.

**Lecture seule, sans donnée nominative conservée.** Pour connaître les colonnes
d'une couche il faut bien lui demander une ligne (`limit=1`) : cette ligne reste
en mémoire et n'est **jamais écrite sur le disque**. Seuls sortent les noms de
colonnes et les comptages. L'option `--sample` ajoute la *forme* des valeurs
(« texte de 20 caractères », « vide ») pour valider un mapping — toujours sans
la valeur elle-même.

Ce que la reconnaissance du 2026-09-03 a établi, et qui est codé ici :
  - API      : `https://sig.agglopole.fr/rest_vmap2/v2`
  - connexion: `POST /vitis/privatetoken` {user, password, duration}
               → jeton dans `data.token`, porté brut dans l'en-tête `Authorization`
  - couches  : `GET /vmap/layers` (1069 couches)
  - attributs: `GET /vmap/layers/{layer_id}/query?limit=N`
               (filtre possible : `filter={"relation":"AND","operators":[...]}`)

Usage :
    python scripts/sig_agglo_recon.py [--env chemin/.env] [--out dossier] [--sample]

Variables attendues dans le `.env` (voir docs/refonte-v1/sig-agglo-proprietaires-decisions.md) :
    SIG_AGGLO_BASE_URL=https://sig.agglopole.fr/rest_vmap2/v2
    SIG_AGGLO_USER=...
    SIG_AGGLO_PASSWORD=...
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests

DEFAULT_BASE_URL = "https://sig.agglopole.fr/rest_vmap2/v2"
TIMEOUT = 60

# Mots-clés qui font d'une couche un candidat « propriétaire / foncier ».
# On ratisse large : intitulés métier (français) ET noms de tables ou de champs
# MAJIC/DGFiP (ddenom = dénomination du propriétaire, dnupro = compte communal…).
KEYWORDS = (
    "proprietaire",
    "propriétaire",
    "propriete",
    "propriété",
    "proprio",
    "majic",
    "cadastr",
    "parcell",
    "foncier",
    "fonciere",
    "foncière",
    "ddenom",
    "dnupro",
    "compte",
    "tup",
    "uf_",
)


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
def load_env(explicit: str | None) -> dict[str, str]:
    """Lit un `.env` minimaliste (KEY=VALUE) sans dépendance externe.

    Ordre de recherche : chemin explicite, puis `.env` à la racine du dépôt,
    puis `.env` du répertoire courant. Un `#` à l'intérieur d'une valeur est
    conservé (les mots de passe en contiennent), seules les lignes qui
    *commencent* par `#` sont des commentaires. Les valeurs ne sont jamais
    journalisées.
    """

    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    else:
        repo_root = Path(__file__).resolve().parents[3]
        candidates.append(repo_root / ".env")
        candidates.append(Path.cwd() / ".env")

    for path in candidates:
        if not path.is_file():
            continue
        values: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, raw = line.partition("=")
            values[key.strip()] = raw.strip().strip('"').strip("'")
        print(f"[env] lu : {path}")
        return values

    print("[env] aucun fichier .env trouvé (les variables d'environnement seront utilisées)")
    return {}


# --------------------------------------------------------------------------- #
# Connexion
# --------------------------------------------------------------------------- #
def _extract_token(payload: Any) -> str | None:
    """Retrouve le jeton dans la réponse (il est niché sous `data.token`)."""

    if isinstance(payload, dict):
        for key in ("token", "Token", "sessionToken", "session_token"):
            value = payload.get(key)
            if isinstance(value, str) and len(value) > 8:
                return value
        for key in ("data", "result"):
            found = _extract_token(payload.get(key))
            if found:
                return found
    if isinstance(payload, list) and payload:
        return _extract_token(payload[0])
    return None


def login(session: requests.Session, base_url: str, user: str, password: str, duration: int = 3600) -> str:
    """Ouvre une session Vitis et renvoie le jeton.

    Mécanisme relevé dans le client officiel (`authService.ajaxGetToken_`) :
    `POST /vitis/privatetoken` avec `{user, password, duration}` en JSON, puis
    le jeton est porté **tel quel** dans l'en-tête `Authorization` (ni « Basic »
    ni « Bearer »). Le mot de passe ne transite que dans cette requête.
    """

    url = f"{base_url}/vitis/privatetoken"
    try:
        response = session.post(
            url,
            json={"user": user, "password": password, "duration": duration},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:  # réseau, proxy d'entreprise…
        raise SystemExit(f"[auth] échec réseau vers {url} ({exc.__class__.__name__})")

    print(f"[auth] POST /vitis/privatetoken : HTTP {response.status_code}")
    try:
        payload = response.json()
    except ValueError:
        payload = None

    token = _extract_token(payload)
    if token:
        infos = payload.get("data", {}) if isinstance(payload, dict) else {}
        print(f"[auth] connecté — privilèges : {', '.join(infos.get('privileges', [])) or 'inconnus'}")
        return token

    detail = ""
    if isinstance(payload, dict):
        detail = str(payload.get("errorMessage") or payload.get("error") or "")
    raise SystemExit(
        "[auth] connexion refusée"
        + (f" ({detail})" if detail else "")
        + " : vérifier SIG_AGGLO_USER / SIG_AGGLO_PASSWORD, et que le compte a le droit "
        "d'utiliser l'API (et non seulement l'interface web)."
    )


# --------------------------------------------------------------------------- #
# Exploration
# --------------------------------------------------------------------------- #
def fetch(session: requests.Session, base_url: str, path: str, **params: Any) -> tuple[int, Any]:
    """GET tolérant : renvoie (statut, payload) sans jamais lever."""

    try:
        response = session.get(
            f"{base_url}/{path.lstrip('/')}", params=params or None, timeout=TIMEOUT
        )
    except requests.RequestException as exc:
        return 0, {"error": exc.__class__.__name__}
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, {"raw": response.text[:2000]}


def rows_of(payload: Any) -> list[dict[str, Any]]:
    """Extrait la liste de lignes d'une réponse Vitis (`{status, data, ...}`)."""

    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return [row for row in payload["data"] if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def describe_shape(value: Any) -> str:
    """Décrit une valeur sans la divulguer : type, longueur, vide ou non.

    C'est ce qui permet de valider un mapping (« ce champ est bien un texte de
    ~30 caractères, rempli ») sans recopier un nom de propriétaire.
    """

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return f"{type(value).__name__} (~{len(str(value))} chiffres)"
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return "texte vide"
        kind = "numérique" if re.fullmatch(r"[\d\s.,+-]+", stripped) else "texte"
        return f"{kind}, {len(stripped)} car."
    if isinstance(value, (list, dict)):
        return f"{type(value).__name__} ({len(value)} éléments)"
    return type(value).__name__


def is_candidate(layer: dict[str, Any]) -> bool:
    """Vrai si l'intitulé ou la table de la couche évoque le foncier."""

    haystack = " ".join(
        str(layer.get(key) or "") for key in ("name", "schema", "pg_table")
    ).lower()
    return any(keyword in haystack for keyword in KEYWORDS)


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconnaissance du SIG vMap2 de l'agglo (lecture seule).")
    parser.add_argument("--env", help="chemin d'un fichier .env")
    parser.add_argument("--out", default="sig_recon", help="dossier de sortie de l'inventaire")
    parser.add_argument(
        "--sample",
        action="store_true",
        help="décrit aussi la FORME des valeurs de chaque colonne (aucune valeur n'est écrite)",
    )
    parser.add_argument(
        "--all-layers",
        action="store_true",
        help="inventorie les 1000+ couches, pas seulement celles qui touchent au foncier",
    )
    args = parser.parse_args()

    env = load_env(args.env)

    def setting(name: str, default: str = "") -> str:
        return env.get(name) or os.environ.get(name) or default

    base_url = setting("SIG_AGGLO_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    user = setting("SIG_AGGLO_USER")
    password = setting("SIG_AGGLO_PASSWORD")
    if not user or not password:
        print("Il manque SIG_AGGLO_USER et/ou SIG_AGGLO_PASSWORD (fichier .env).", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    session.headers.update({"Authorization": login(session, base_url, user, password)})

    # 1. Le catalogue des couches.
    status, payload = fetch(session, base_url, "vmap/layers")
    layers = rows_of(payload)
    if status != 200 or not layers:
        print(f"[api] GET /vmap/layers : HTTP {status} — inventaire impossible", file=sys.stderr)
        return 1
    print(f"[api] {len(layers)} couches accessibles")
    (out_dir / "vmap_layers.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    selected = layers if args.all_layers else [layer for layer in layers if is_candidate(layer)]
    print(f"[api] {len(selected)} couches à décrire" + ("" if args.all_layers else " (filtre foncier)"))

    # 2. Le schéma de chacune : colonnes + volumétrie, sans conserver de donnée.
    inventory: list[dict[str, Any]] = []
    for index, layer in enumerate(sorted(selected, key=lambda l: str(l.get("name")))):
        layer_id = layer.get("layer_id")
        status, payload = fetch(session, base_url, f"vmap/layers/{layer_id}/query", limit=1)
        entry: dict[str, Any] = {
            "layer_id": layer_id,
            "nom": layer.get("name"),
            "table": f"{layer.get('schema')}.{layer.get('pg_table')}",
            "maj": layer.get("datemaj"),
            "statut": status,
        }
        sample = rows_of(payload)
        if status == 200 and isinstance(payload, dict) and payload.get("status") == 1:
            entry["lignes"] = payload.get("total_row_number")
            entry["colonnes"] = list(sample[0].keys()) if sample else []
            if args.sample and sample:
                # La ligne reste en mémoire : on n'en garde que la forme.
                entry["formes"] = {k: describe_shape(v) for k, v in sample[0].items()}
        else:
            entry["erreur"] = (
                payload.get("errorMessage") if isinstance(payload, dict) else str(payload)[:80]
            )
        inventory.append(entry)
        del payload, sample  # rien de nominatif ne survit à l'itération
        if (index + 1) % 25 == 0:
            print(f"    … {index + 1}/{len(selected)}")

    (out_dir / "inventaire.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    # 3. Une version lisible, triée par volumétrie décroissante.
    lines = [
        "# Inventaire des couches foncières du SIG de l'agglo",
        "",
        "Généré par `scripts/sig_agglo_recon.py` — noms de colonnes et comptages uniquement.",
        "",
        "| Couche | Table | Lignes | MAJ | Colonnes |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for entry in sorted(inventory, key=lambda e: -(e.get("lignes") or 0)):
        if "erreur" in entry:
            continue
        columns = ", ".join(f"`{c}`" for c in entry.get("colonnes", []))
        lines.append(
            f"| {entry['nom']} | `{entry['table']}` | {entry.get('lignes') or ''} "
            f"| {entry.get('maj') or ''} | {columns} |"
        )
    refused = [e for e in inventory if "erreur" in e]
    if refused:
        lines += ["", f"**{len(refused)} couche(s) inaccessibles** (droits ou vue en erreur) :", ""]
        lines += [f"- {e['nom']} (`{e['table']}`) — {e['erreur']}" for e in refused]
    (out_dir / "inventaire.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nInventaire écrit dans : {out_dir.resolve()}")
    print("  - inventaire.md   (tableau lisible)")
    print("  - inventaire.json (même chose, exploitable)")
    print("  - vmap_layers.json (catalogue brut des couches)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
