"""Bilan hebdomadaire : les deux mesures qui remplaceront un jour le score deviné.

Le score du radar n'a pas passé l'audit (aucun pouvoir discriminant sur la victoire,
signal Elo compté plusieurs fois). La suite n'est pas de re-régler des poids à l'aveugle,
mais d'accumuler de la mesure et de laisser les données trancher. Deux mesures comptent :

1. CALIBRATION des marchés secondaires (`tennis_journal`) : quand le modèle annonce « prend
   un set à 60 % », est-ce que ça arrive vraiment 60 % du temps ? Réglée automatiquement au
   score ESPN. C'est ce que les backtests historiques ne peuvent pas donner.

2. MOUVEMENT DE COTE / CLV (`tennis_odds_movement`) : les outsiders suivis voient-ils leur
   cote se resserrer d'ici la clôture (le marché leur donne raison) ou s'allonger ?
   Exploitable dès ~50 paris, contre ~500 pour un ROI.

Ce module ne calcule rien de neuf : il regroupe ces deux mesures PAR SEMAINE, pour qu'on
voie l'accumulation sans avoir à ré-analyser un export à chaque fois. La colonne qui
compte au début, c'est `n` : tant qu'il est petit, tout écart reste du bruit.
"""
from __future__ import annotations

import os
import sqlite3
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app import tennis_journal, tennis_odds_movement
from app.tennis_outsider_radar import _parse_day


def _iso_week(value: Any) -> str | None:
    day = _parse_day(value)
    if day is None:
        return None
    year, week, _ = day.isocalendar()
    return f"{year}-S{week:02d}"


def _market_weeks(path: str | Path | None) -> list[dict[str, Any]]:
    """Marchés secondaires réglés, regroupés par semaine de match puis par marché."""
    target = Path(path) if path else tennis_journal.journal_path()
    if target is None or not target.exists():
        return []
    with closing(sqlite3.connect(target)) as db:
        db.row_factory = sqlite3.Row
        columns = {row[1] for row in db.execute("PRAGMA table_info(tennis_market_picks)")} \
            if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tennis_market_picks'").fetchone() else set()
        if not columns:
            return []
        rows = db.execute(
            """SELECT kickoff, market, probability, won FROM tennis_market_picks
               WHERE won IS NOT NULL AND probability IS NOT NULL"""
        ).fetchall()

    by_week: dict[str, dict[str, list[sqlite3.Row]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        week = _iso_week(row["kickoff"])
        if week:
            by_week[week][row["market"]].append(row)

    out = []
    for week in sorted(by_week, reverse=True):
        markets = []
        for market in sorted(by_week[week]):
            items = by_week[week][market]
            n = len(items)
            wins = sum(1 for r in items if r["won"])
            expected = sum(r["probability"] for r in items) / n
            markets.append({
                "market": market,
                "n": n,
                "wins": wins,
                "realised": round(wins / n * 100, 1),
                "expected": round(expected * 100, 1),
                "delta_points": round((wins / n - expected) * 100, 1),
            })
        out.append({"week": week, "markets": markets})
    return out


def _odds_weeks(path: str | Path | None) -> list[dict[str, Any]]:
    """Mouvement de cote regroupé par semaine de match (tout l'historique disponible)."""
    snapshots = tennis_odds_movement._snapshots(path)
    by_week: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for series in snapshots.values():
        if len(series) < 2:
            continue
        move = tennis_odds_movement._movement(series)
        if move is None:
            continue
        week = _iso_week(move.get("kickoff"))
        if week:
            by_week[week].append(move)

    out = []
    for week in sorted(by_week, reverse=True):
        moves = by_week[week]
        total = len(moves)
        shortened = sum(1 for m in moves if m["direction"] == "raccourcit")
        out.append({
            "week": week,
            "tracked": total,
            "shortened": shortened,
            "drifted": sum(1 for m in moves if m["direction"] == "derive"),
            "shortened_rate": round(shortened / total * 100, 1) if total else None,
            "average_implied_move_points": round(sum(m["implied_move_points"] for m in moves) / total, 2) if total else None,
        })
    return out


def weekly_scorecard(path: str | Path | None = None) -> dict[str, Any]:
    """Les deux mesures, en cumulé et semaine par semaine."""
    market_cumulative = tennis_journal.calibration_by_market(path=path, min_sample=1)
    market_weeks = _market_weeks(path)
    odds_all = tennis_odds_movement.recent_movements(days=tennis_odds_movement.MAX_DAYS, path=path)
    odds_weeks = _odds_weeks(path)

    settled_picks = sum(item["n"] for item in market_cumulative)
    # Repère simple : en dessous de ~50 règlements par marché, on lit du bruit.
    ready = all(item["n"] >= 50 for item in market_cumulative) if market_cumulative else False

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "coverage": {
            "settled_market_picks": settled_picks,
            "market_weeks": len(market_weeks),
            "tracked_odds_matches": odds_all.get("tracked_matches", 0),
            "enough_to_read_markets": ready,
            "hint": "Tant que n < ~50 par marché, les écarts restent du bruit : on regarde surtout la pente d'accumulation.",
        },
        "markets": {
            "cumulative": market_cumulative,
            "by_week": market_weeks,
        },
        "odds_movement": {
            "cumulative": {
                "tracked_matches": odds_all.get("tracked_matches"),
                "shortened_count": odds_all.get("shortened_count"),
                "drifted_count": odds_all.get("drifted_count"),
                "shortened_rate": odds_all.get("shortened_rate"),
                "average_implied_move_points": odds_all.get("average_implied_move_points"),
            },
            "by_week": odds_weeks,
        },
    }
