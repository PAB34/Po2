"""Journal des decisions tennis : ce qui a ete joue, a quel prix, et ce que ca a donne.

Le module de calibration (app.tennis_decision_calibration) sait deja LIRE une table
`tennis_decisions` et en tirer taux de reussite, ROI et intervalles de Wilson par
bucket. Il n'avait aucune donnee a lire : rien n'ecrivait ces lignes. C'est ce trou
que ce module comble.

Pourquoi c'est le maillon manquant : les backtests historiques ne portent que sur le
marche vainqueur, seul marche dont les cotes sont archivees. Les marches reellement
joues -- "prend au moins un set", handicap jeux -- n'ont aucune cote historique. Le
seul moyen de savoir s'ils battent le marche est donc d'enregistrer les prix pris au
fil de l'eau.

Schema aligne sur ce que records_from_sqlite() attend, plus les colonnes du pari lui
meme (marche, cote prise, mise, issue) que la calibration vainqueur n'utilise pas mais
qui permettent le ROI par marche.

Convention des probabilites : on stocke des fractions (0.62). La calibration accepte
les deux ecritures et expose des pourcentages (62.0) -- ne pas s'etonner de l'ecart
entre ce qui est ecrit ici et ce qu'elle renvoie.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.ligue1.config import DATA_DIR

JOURNAL_PATH = Path(DATA_DIR) / "tennis_decisions.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tennis_decisions (
    id                  TEXT PRIMARY KEY,
    created_at          TEXT NOT NULL,
    kickoff             TEXT,
    tour                TEXT,
    tournament          TEXT,
    surface             TEXT,
    favorite            TEXT NOT NULL,
    opponent            TEXT,
    favorite_odds       REAL,
    outsider_odds       REAL,
    market_probability  REAL NOT NULL,
    elo_probability     REAL,
    elo_gap             REAL,
    decision            TEXT,
    decision_level      TEXT,
    concordance         TEXT,
    context_label       TEXT,
    quality             TEXT,
    -- le pari reellement pris (peut rester vide : on journalise aussi les non-paris)
    market              TEXT,
    selection           TEXT,
    taken_odds          REAL,
    stake               REAL,
    -- renseigne apres le match
    result_winner       TEXT,
    result_score        TEXT,
    bet_won             INTEGER,
    settled_at          TEXT,
    payload_json        TEXT
);
CREATE INDEX IF NOT EXISTS idx_tennis_decisions_settled ON tennis_decisions(result_winner);
CREATE INDEX IF NOT EXISTS idx_tennis_decisions_market ON tennis_decisions(market);
"""


def _connect(path: str | Path | None = None) -> sqlite3.Connection:
    db_path = Path(path) if path else JOURNAL_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def record_decision(
    *,
    match_id: str,
    favorite: str,
    market_probability: float,
    opponent: str | None = None,
    kickoff: str | None = None,
    tour: str = "ATP",
    tournament: str | None = None,
    surface: str | None = None,
    favorite_odds: float | None = None,
    outsider_odds: float | None = None,
    elo_probability: float | None = None,
    elo_gap: float | None = None,
    decision: str | None = None,
    decision_level: str | None = None,
    concordance: str | None = None,
    context_label: str | None = None,
    quality: str | None = None,
    market: str | None = None,
    selection: str | None = None,
    taken_odds: float | None = None,
    stake: float | None = None,
    extra: dict[str, Any] | None = None,
    path: str | Path | None = None,
) -> str:
    """Enregistre une lecture d'avant-match, avec ou sans pari.

    Journaliser aussi les matchs non joues est volontaire : sans eux on ne mesure
    que les paris pris, ce qui empeche de savoir si le filtre ecarte les bons ou
    les mauvais.
    """
    payload = dict(extra or {})
    payload.update({
        "favori": favorite,
        "adversaire": opponent,
        "proba_marche": market_probability,
        "proba_elo": elo_probability,
        "ecart_elo": elo_gap,
        "decision": decision,
        "concordance": concordance,
        "cote": favorite_odds,
        "cote_outsider": outsider_odds,
        "surface": surface,
        "tour": tour,
        "marche": market,
        "selection": selection,
        "cote_prise": taken_odds,
    })
    with closing(_connect(path)) as db, db:
        db.execute(
            """INSERT OR REPLACE INTO tennis_decisions
               (id, created_at, kickoff, tour, tournament, surface, favorite, opponent,
                favorite_odds, outsider_odds, market_probability, elo_probability, elo_gap,
                decision, decision_level, concordance, context_label, quality,
                market, selection, taken_odds, stake, payload_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                match_id, datetime.now(timezone.utc).isoformat(timespec="seconds"),
                kickoff, tour, tournament, surface, favorite, opponent,
                favorite_odds, outsider_odds, market_probability, elo_probability, elo_gap,
                decision, decision_level, concordance, context_label, quality,
                market, selection, taken_odds, stake,
                json.dumps(payload, ensure_ascii=False),
            ),
        )
    return match_id


def settle(
    match_id: str,
    *,
    winner: str,
    score: str | None = None,
    bet_won: bool | None = None,
    path: str | Path | None = None,
) -> bool:
    """Renseigne le resultat. `bet_won` reste libre : sur un marche secondaire,
    l'issue du pari ne se deduit pas du seul vainqueur."""
    with closing(_connect(path)) as db, db:
        cur = db.execute(
            """UPDATE tennis_decisions
               SET result_winner = ?, result_score = ?, bet_won = ?, settled_at = ?
               WHERE id = ?""",
            (
                winner, score,
                None if bet_won is None else int(bet_won),
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                match_id,
            ),
        )
    return cur.rowcount > 0


def roi_by_market(path: str | Path | None = None, min_sample: int = 1) -> list[dict[str, Any]]:
    """ROI par marche joue, sur les paris regles.

    C'est le tableau que les backtests historiques ne peuvent pas produire, faute de
    cotes archivees sur les marches secondaires.
    """
    with closing(_connect(path)) as db:
        rows = db.execute(
            """SELECT market, taken_odds, stake, bet_won
               FROM tennis_decisions
               WHERE market IS NOT NULL AND taken_odds IS NOT NULL AND bet_won IS NOT NULL"""
        ).fetchall()

    grouped: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        grouped.setdefault(row["market"], []).append(row)

    out: list[dict[str, Any]] = []
    for market, items in sorted(grouped.items()):
        if len(items) < min_sample:
            continue
        staked = sum((r["stake"] or 1.0) for r in items)
        returned = sum((r["stake"] or 1.0) * r["taken_odds"] for r in items if r["bet_won"])
        wins = sum(1 for r in items if r["bet_won"])
        out.append({
            "market": market,
            "n": len(items),
            "wins": wins,
            "win_rate": round(wins / len(items), 4),
            "staked": round(staked, 2),
            "returned": round(returned, 2),
            "profit": round(returned - staked, 2),
            "roi": round((returned - staked) / staked, 4) if staked else None,
            "average_odds": round(sum(r["taken_odds"] for r in items) / len(items), 3),
        })
    return out


def pending(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Decisions enregistrees dont le resultat manque encore."""
    with closing(_connect(path)) as db:
        rows = db.execute(
            """SELECT id, kickoff, tour, tournament, favorite, opponent, market, selection,
                      taken_odds, stake
               FROM tennis_decisions WHERE result_winner IS NULL ORDER BY kickoff"""
        ).fetchall()
    return [dict(row) for row in rows]


def calibration(path: str | Path | None = None, min_sample: int = 50) -> dict[str, Any]:
    """Branche le journal sur le moteur de calibration deja ecrit."""
    from app.tennis_decision_calibration import records_from_sqlite, run_decision_calibration

    records = records_from_sqlite(Path(path) if path else JOURNAL_PATH)
    return run_decision_calibration(records, min_sample=min_sample)
