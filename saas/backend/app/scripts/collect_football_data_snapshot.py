"""Collecteur throttle football-data.org -> snapshot JSON.

Le tier gratuit football-data.org est limite a 10 requetes/minute. La
collecte complete (48 equipes x detail + matchs) fait ~100 appels et ne peut
donc pas passer dans un endpoint web synchrone. Ce script espace les appels
(``--interval`` secondes) et ecrit un snapshot JSON exploitable hors-ligne,
qui sert ensuite a alimenter le classeur Excel du modele de pronostic.

Usage (depuis saas/backend/, token dans l'environnement) :

    FOOTBALL_DATA_TOKEN=... DATABASE_URL=sqlite+pysqlite:///:memory: \
    SECRET_KEY=x python -m app.scripts.collect_football_data_snapshot \
        --out ../../outputs/pronostics_model_v0/football_data_snapshot.json

Ne jamais committer ni afficher le token.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from app.core.config import settings
from app.services.football_data import FootballDataClient, build_pronostics_model_feed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="Chemin du snapshot JSON a ecrire.")
    parser.add_argument(
        "--interval",
        type=float,
        default=6.5,
        help="Secondes minimales entre 2 appels API (tier gratuit = 10/min).",
    )
    parser.add_argument(
        "--include-player-matches",
        action="store_true",
        help="Enrichit chaque joueur via persons/{id}/matches (TRES couteux en appels).",
    )
    parser.add_argument(
        "--team-matches-limit",
        type=int,
        default=10,
        help="Nombre de matchs recents retenus par equipe pour la forme.",
    )
    args = parser.parse_args()

    token = settings.football_data_token or os.environ.get("FOOTBALL_DATA_TOKEN", "")
    if not token:
        print("ERREUR: FOOTBALL_DATA_TOKEN absent de l'environnement.", file=sys.stderr)
        return 2

    client = FootballDataClient(token=token, min_interval_seconds=args.interval)
    print(
        f"Collecte football-data.org (interval={args.interval}s, "
        f"include_player_matches={args.include_player_matches})...",
        file=sys.stderr,
    )
    started = time.monotonic()
    feed = build_pronostics_model_feed(
        client=client,
        include_player_matches=args.include_player_matches,
        recent_team_matches_limit=args.team_matches_limit,
    )
    elapsed = round(time.monotonic() - started, 1)

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(feed, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = feed.get("summary", {})
    errors = feed.get("errors", [])
    print(
        f"OK en {elapsed}s -> {out_path}\n"
        f"  equipes={summary.get('teams')} joueurs={summary.get('players')} "
        f"scorers={summary.get('competition_scorers')} erreurs={len(errors)}",
        file=sys.stderr,
    )
    if errors:
        codes: dict[str, int] = {}
        for err in errors:
            key = str(err.get("status_code"))
            codes[key] = codes.get(key, 0) + 1
        print(f"  erreurs par code: {codes}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
