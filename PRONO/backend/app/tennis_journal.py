"""Registre des marches secondaires : ce que le modele annoncait, ce qui est arrive.

Une seule base fait foi : `<PRONO_DATA_DIR>/tennis/decision_history.sqlite3`, celle que
`tennis._record_decision_history()` alimente automatiquement a chaque construction de la
page. Il a existe jusqu'au 23/07/2026 une seconde base alimentee a la main
(`tennis_decisions.db`) : elle est abandonnee. Deux registres pour la meme mesure, c'est
la garantie de calibrer un jour sur la moitie des donnees sans s'en apercevoir.

Ce que ce module ajoute a l'enregistrement des matchs : les marches secondaires. La table
`tennis_decisions` retient la lecture du match (favori, probabilites, decision) ; celle-ci
retient les paris qui en decoulent -- "outsider prend un set", "+3.5 jeux", "gagne le set
1" -- avec la probabilite annoncee et la cote juste, puis leur issue reelle.

CE QUE CA MESURE, ET CE QUE CA NE MESURE PAS. Le reglement est automatique, donc sans
oubli ni saisie : on obtient le taux de reussite reel contre la probabilite annoncee,
soit la CALIBRATION du modele sur ces marches -- ce qu'aucun backtest historique ne
donne, faute de cotes archivees sur ces lignes.

En revanche ce n'est PAS un ROI, et le mot est evite partout dans ce module. Un ROI
suppose la cote reellement obtenue chez un bookmaker : elle n'est archivee nulle part et
aucune source automatique ne la fournit. Mesurer un gain demanderait de saisir le prix
pris a la main, ce qui a ete ecarte. On sait donc dire si le modele annonce juste ; on ne
sait pas dire si le book se trompe.
"""
from __future__ import annotations

import math
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

# Les trois marches mesures comme porteurs de signal par backtest_marches_outsider.py.
# Cles alignees sur celles de tennis._outsider_markets() : la meme chaine va de
# l'affichage jusqu'a la calibration, sans table de correspondance a maintenir.
TRACKED_MARKETS = ("outsider_takes_a_set", "outsider_games_3_5", "outsider_set_1")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tennis_market_picks (
    id                INTEGER PRIMARY KEY,
    calculated_at     TEXT NOT NULL,
    kickoff           TEXT,
    tour              TEXT,
    tournament        TEXT,
    surface           TEXT,
    pair_key          TEXT NOT NULL,
    favorite          TEXT,
    outsider          TEXT,
    market            TEXT NOT NULL,
    selection         TEXT,
    probability       REAL,
    fair_odds         REAL,
    decision_level    TEXT,
    concordance       TEXT,
    won               INTEGER,
    settled_at        TEXT,
    UNIQUE(calculated_at, pair_key, market)
);
CREATE INDEX IF NOT EXISTS idx_market_picks_market ON tennis_market_picks(market);
CREATE INDEX IF NOT EXISTS idx_market_picks_pair ON tennis_market_picks(pair_key);
"""


def journal_path() -> Path | None:
    """Base unique. Absente hors conteneur (PRONO_DATA_DIR non defini) : on ne devine pas."""
    root = os.environ.get("PRONO_DATA_DIR")
    return Path(root) / "tennis" / "decision_history.sqlite3" if root else None


def _connect(path: str | Path | None = None) -> sqlite3.Connection | None:
    target = Path(path) if path else journal_path()
    if target is None:
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(target, timeout=10)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


# ---------------------------------------------------------------------------
# Ecriture : appelee par tennis.build_tennis(), jamais a la main.
# ---------------------------------------------------------------------------
def record_market_picks(rows: list[dict], calculated_at: str, pair_key_of, path=None) -> int:
    """Archive les marches suivis de chaque match a l'affiche.

    On enregistre les trois marches pour TOUS les matchs, pas seulement ceux ou l'Elo
    contredit le marche : sans les matchs ecartes, on ne mesure que ce qu'on a retenu et
    on ne peut plus dire si le filtre elimine les bons ou les mauvais.
    """
    db = _connect(path)
    if db is None:
        return 0
    written = 0
    with closing(db), db:
        for row in rows:
            pair_key = pair_key_of(row.get("joueur1", ""), row.get("joueur2", ""))
            for market in row.get("markets") or []:
                key = market.get("key")
                if key not in TRACKED_MARKETS or market.get("prob") is None:
                    continue
                cursor = db.execute(
                    """INSERT OR IGNORE INTO tennis_market_picks (
                           calculated_at, kickoff, tour, tournament, surface, pair_key,
                           favorite, outsider, market, selection, probability, fair_odds,
                           decision_level, concordance
                       ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        calculated_at, row.get("kickoff"), row.get("tour"), row.get("tournoi"),
                        row.get("surface"), pair_key, row.get("favori"), row.get("outsider"),
                        key, market.get("pick"), (market.get("prob") or 0) / 100.0,
                        market.get("fair_odds"), row.get("decision_level"), row.get("concordance"),
                    ),
                )
                written += cursor.rowcount
    return written


def _same_player(left: Any, right: Any) -> bool:
    return str(left or "").strip().casefold() == str(right or "").strip().casefold()


def market_outcomes(result: dict, outsider: str) -> dict[str, bool]:
    """Issue reelle de chaque marche suivi, depuis le score ESPN.

    `result` vient de tennis._completed_scoreboard_row() : les scores y sont ecrits du
    point de vue du VAINQUEUR du match. On repasse systematiquement du cote de
    l'outsider, seul referentiel de ces marches. C'est l'inversion la plus facile a
    rater, et elle fausserait la mesure en silence.
    """
    outsider_won = _same_player(result.get("winner"), outsider)
    sets = [tuple(pair) for pair in (result.get("sets") or [])]
    if outsider_won:
        o_sets = list(sets)
        o_games, f_games = result.get("games_w"), result.get("games_l")
        o_set_wins = result.get("sets_w")
    else:
        o_sets = [(right, left) for left, right in sets]
        o_games, f_games = result.get("games_l"), result.get("games_w")
        o_set_wins = result.get("sets_l")

    outcomes: dict[str, bool] = {}
    if o_set_wins is not None:
        outcomes["outsider_takes_a_set"] = o_set_wins >= 1
    if o_games is not None and f_games is not None:
        # "+3.5" : l'outsider couvre s'il perd de 3 jeux au plus, ou s'il gagne.
        outcomes["outsider_games_3_5"] = (o_games - f_games) > -3.5
    if o_sets:
        outcomes["outsider_set_1"] = o_sets[0][0] > o_sets[0][1]
    return outcomes


def settle_from_results(completed: list[dict], pair_key_of, stamp: str, path=None) -> int:
    """Regle les marches des matchs termines. Automatique, donc sans oubli ni biais."""
    db = _connect(path)
    if db is None:
        return 0
    settled = 0
    with closing(db), db:
        for result in completed:
            pair_key = pair_key_of(result.get("winner", ""), result.get("loser", ""))
            outsiders = db.execute(
                """SELECT DISTINCT outsider FROM tennis_market_picks
                   WHERE pair_key = ? AND won IS NULL""", (pair_key,),
            ).fetchall()
            for entry in outsiders:
                for market, won in market_outcomes(result, entry["outsider"]).items():
                    cursor = db.execute(
                        """UPDATE tennis_market_picks SET won = ?, settled_at = ?
                           WHERE pair_key = ? AND market = ? AND won IS NULL
                             AND outsider IS ?""",
                        (int(won), stamp, pair_key, market, entry["outsider"]),
                    )
                    settled += cursor.rowcount
    return settled


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------
def _wilson(wins: int, n: int) -> tuple[float, float]:
    """Intervalle de Wilson a 95 %. Sur quelques dizaines de matchs presque tout ecart
    reste du bruit : l'intervalle est la pour empecher de conclure trop tot."""
    if not n:
        return 0.0, 0.0
    z = 1.96
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def calibration_by_market(path=None, min_sample: int = 20) -> list[dict[str, Any]]:
    """Taux de reussite reel contre probabilite annoncee, marche par marche.

    C'est la mesure que ce registre rend possible -- une calibration, pas un rendement.
    """
    db = _connect(path)
    if db is None:
        return []
    with closing(db):
        rows = db.execute(
            """SELECT market, probability, fair_odds, won FROM tennis_market_picks
               WHERE won IS NOT NULL AND probability IS NOT NULL"""
        ).fetchall()

    grouped: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        grouped.setdefault(row["market"], []).append(row)

    out = []
    for market, items in sorted(grouped.items()):
        n = len(items)
        wins = sum(1 for r in items if r["won"])
        expected = sum(r["probability"] for r in items) / n
        realised = wins / n
        low, high = _wilson(wins, n)
        # Ecart concluant = la probabilite annoncee tombe HORS de l'intervalle observe.
        conclusive = n >= min_sample and not (low <= expected <= high)
        odds = [r["fair_odds"] for r in items if r["fair_odds"]]
        out.append({
            "market": market,
            "n": n,
            "wins": wins,
            "realised": round(realised * 100, 1),
            "expected": round(expected * 100, 1),
            "delta_points": round((realised - expected) * 100, 1),
            "ci95": [round(low * 100, 1), round(high * 100, 1)],
            "average_fair_odds": round(sum(odds) / len(odds), 2) if odds else None,
            "verdict": (
                "echantillon insuffisant" if n < min_sample
                else "modele trop optimiste" if conclusive and realised < expected
                else "modele trop prudent" if conclusive
                else "conforme a l'annonce"
            ),
        })
    return out


def pending(path=None) -> list[dict[str, Any]]:
    """Marches enregistres dont le match n'a pas encore de resultat."""
    db = _connect(path)
    if db is None:
        return []
    with closing(db):
        rows = db.execute(
            """SELECT kickoff, tour, tournament, favorite, outsider, market, selection,
                      probability, fair_odds
               FROM tennis_market_picks WHERE won IS NULL ORDER BY kickoff"""
        ).fetchall()
    return [dict(row) for row in rows]


def calibration(path=None, min_sample: int = 50) -> dict[str, Any]:
    """Calibration des DECISIONS (marche vainqueur), lue sur la meme base unique."""
    from app.tennis_decision_calibration import records_from_sqlite, run_decision_calibration

    target = Path(path) if path else journal_path()
    if target is None or not target.exists():
        return {"record_count": 0, "buckets": [], "status": "no_history"}
    return run_decision_calibration(records_from_sqlite(target), min_sample=min_sample)
