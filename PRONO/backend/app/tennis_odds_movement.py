"""Trajectoire de la cote et closing line, a partir des snapshots deja stockes.

On ne collecte rien de nouveau : `tennis._record_decision_history` insere deja, a chaque
construction de la page, un snapshot par match avec la cote du moment. Sur la base de prod,
91 % des matchs suivis montrent une cote outsider qui bouge d'un snapshot a l'autre
(mediane 5 snapshots/match). Ce module ne fait que LIRE cette serie et en tirer trois
choses :

1. la trajectoire open -> close de la cote outsider ;
2. la closing line = dernier snapshot AVANT le coup d'envoi ;
3. un proxy de CLV (closing line value) : la cote s'est-elle raccourcie (le marche s'est
   deplace vers l'outsider, la lecture anticipait le mouvement) ou allongee (le marche a
   pousse dans l'autre sens).

Pourquoi le CLV et pas le ROI : battre la cloture est un signal exploitable des ~50 paris,
la ou le ROI en demande ~500. C'est le seul moyen de savoir vite si une methode capte du
signal, sans attendre des centaines de resultats. Ici on n'a pas la cote reellement prise
chez un bookmaker -- on mesure donc le mouvement du CONSENSUS entre le premier repere et la
cloture, ce qui teste si le radar pointe des outsiders que le marche finit par resserrer.
"""
from __future__ import annotations

import os
import sqlite3
from collections import defaultdict
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from app.tennis_outsider_radar import _match_key, _number, _norm, _parse_day

DEFAULT_DAYS = 14
MAX_DAYS = 120


def _history_path() -> Path | None:
    root = os.environ.get("PRONO_DATA_DIR")
    return Path(root) / "tennis" / "decision_history.sqlite3" if root else None


def _snapshots(path: str | Path | None = None) -> dict[str, list[dict[str, Any]]]:
    """Tous les snapshots groupes par match, tries du plus ancien au plus recent.

    Contrairement au radar, on garde AUSSI les matchs sans resultat : le suivi de cote
    concerne d'abord les affiches a venir, dont on veut voir la cote se former.
    """
    target = Path(path) if path else _history_path()
    if target is None or not target.exists():
        return {}
    with closing(sqlite3.connect(target)) as db:
        db.row_factory = sqlite3.Row
        columns = {entry[1] for entry in db.execute("PRAGMA table_info(tennis_decisions)")}
        if "outsider_odds" not in columns:
            return {}
        rows = [dict(row) for row in db.execute(
            "SELECT * FROM tennis_decisions ORDER BY calculated_at ASC"
        ).fetchall()]

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if _number(row.get("outsider_odds")) is None:
            continue
        grouped[str(row.get("match_id") or _match_key(row))].append(row)
    return grouped


def _closing_index(snapshots: list[dict[str, Any]]) -> int:
    """Indice du dernier snapshot pris AVANT le coup d'envoi (la closing line).

    Un snapshot posterieur au kickoff est un recalcul, pas un prix de marche : on l'ecarte.
    Si tous sont posterieurs (kickoff mal date), on retombe sur le dernier disponible.
    """
    prematch = [
        index for index, snap in enumerate(snapshots)
        if not (str(snap.get("kickoff") or "") and str(snap.get("calculated_at") or "") > str(snap.get("kickoff") or ""))
    ]
    return prematch[-1] if prematch else len(snapshots) - 1


def _movement(snapshots: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not snapshots:
        return None
    opening = snapshots[0]
    close_i = _closing_index(snapshots)
    closing_snap = snapshots[close_i]
    open_odds = _number(opening.get("outsider_odds"))
    close_odds = _number(closing_snap.get("outsider_odds"))
    if open_odds is None or close_odds is None:
        return None
    delta = round(close_odds - open_odds, 3)
    # "raccourcit" = la cote baisse = probabilite implicite qui monte = marche vers l'outsider.
    direction = "raccourcit" if delta < -0.03 else "derive" if delta > 0.03 else "stable"
    reference = snapshots[0]
    return {
        "match_id": str(reference.get("match_id") or _match_key(reference)),
        "tour": reference.get("tour"),
        "tournament": reference.get("tournament"),
        "kickoff": reference.get("kickoff"),
        "favorite": reference.get("favorite"),
        "outsider": _outsider_name(reference),
        "snapshots": len(snapshots),
        "opening_outsider_odds": round(open_odds, 2),
        "closing_outsider_odds": round(close_odds, 2),
        "delta_odds": delta,
        # Variation de probabilite implicite : plus lisible qu'une variation de cote.
        "implied_move_points": round((1.0 / close_odds - 1.0 / open_odds) * 100, 1),
        "direction": direction,
        "settled": bool(reference.get("result_winner") or snapshots[close_i].get("result_winner")),
        "trajectory": [
            {"at": snap.get("calculated_at"), "outsider_odds": _number(snap.get("outsider_odds"))}
            for snap in snapshots
        ],
    }


def _outsider_name(row: dict[str, Any]) -> str:
    favorite = _norm(row.get("favorite"))
    p1, p2 = str(row.get("player1") or ""), str(row.get("player2") or "")
    if favorite and _norm(p1) == favorite:
        return p2
    if favorite and _norm(p2) == favorite:
        return p1
    return p2 or p1


def match_movement(match_id: str, path: str | Path | None = None) -> dict[str, Any] | None:
    """Trajectoire complete d'un match donne (pour brancher sur une fiche candidate)."""
    return _movement(_snapshots(path).get(str(match_id), []))


def recent_movements(days: int = DEFAULT_DAYS, path: str | Path | None = None) -> dict[str, Any]:
    """Mouvements de cote sur la fenetre, plus l'agregat CLV.

    L'agregat repond a la question utile : les outsiders que le radar suit voient-ils leur
    cote se resserrer (le marche leur donne raison) ou s'allonger ?
    """
    days = max(1, min(int(days), MAX_DAYS))
    cutoff = date.today() - timedelta(days=days)
    movements: list[dict[str, Any]] = []
    for snapshots in _snapshots(path).values():
        if len(snapshots) < 2:
            continue
        reference = snapshots[0]
        played = _parse_day(reference.get("kickoff") or reference.get("calculated_at"))
        if played is None or played < cutoff:
            continue
        move = _movement(snapshots)
        if move:
            movements.append(move)

    movements.sort(key=lambda item: item.get("kickoff") or "", reverse=True)
    shortened = [m for m in movements if m["direction"] == "raccourcit"]
    drifted = [m for m in movements if m["direction"] == "derive"]
    total = len(movements)
    return {
        "days": days,
        "tracked_matches": total,
        "shortened_count": len(shortened),
        "drifted_count": len(drifted),
        "stable_count": total - len(shortened) - len(drifted),
        # Part des outsiders suivis dont le marche a resserre la cote d'ici la cloture.
        "shortened_rate": round(len(shortened) / total * 100, 1) if total else None,
        "average_implied_move_points": round(sum(m["implied_move_points"] for m in movements) / total, 2) if total else None,
        "movements": movements,
    }
