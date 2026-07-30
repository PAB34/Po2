"""Radar outsiders construit uniquement avec les collecteurs tennis existants.

Deux lectures sont exposees :
- les outsiders ayant gagne/perdu recemment, avec un seul snapshot prematch par match ;
- un classement explicable des outsiders des prochaines affiches.

Le score radar est un indice de priorisation, pas une probabilite ni une promesse de ROI.
"""
from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import unicodedata
from collections import defaultdict
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


DEFAULT_DAYS = 7
MAX_DAYS = 90


def _norm(value: Any) -> str:
    return " ".join(
        unicodedata.normalize("NFKD", str(value or ""))
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .replace(".", " ")
        .replace("-", " ")
        .split()
    )


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _parse_day(value: Any) -> date | None:
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text[:10] if fmt == "%Y-%m-%d" else text[:8], fmt).date()
        except ValueError:
            continue
    return None


def _history_path() -> Path | None:
    root = os.environ.get("PRONO_DATA_DIR")
    return Path(root) / "tennis" / "decision_history.sqlite3" if root else None


def _match_key(row: dict[str, Any]) -> str:
    """Cle de dedup d'un match. INDEPENDANTE de l'horaire (voir tennis._match_identity).

    Priorite au match_id ecrit en base ; a defaut (lignes anterieures a son introduction),
    reconstruction a partir de (circuit, tournoi, paire) -- jamais du kickoff, qui derive
    entre snapshots et faisait recompter le meme match plusieurs fois.
    """
    match_id = str(row.get("match_id") or "").strip()
    if match_id:
        return match_id
    pair = str(row.get("pair_key") or "")
    if not pair:
        pair = "|".join(sorted((_norm(row.get("player1")), _norm(row.get("player2")))))
    tournament = " ".join(str(row.get("tournament") or "").lower().split())
    return "|".join((str(row.get("tour") or "").upper(), tournament, pair))


def _canonical_history(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Un seul snapshot par match : le dernier disponible avant le coup d'envoi.

    Les recalculs restent stockes pour suivre les mouvements de cote, mais ne sont jamais
    comptes comme des matchs independants dans le bilan outsider.
    """
    target = Path(path) if path else _history_path()
    if target is None or not target.exists():
        return []
    with closing(sqlite3.connect(target)) as db:
        db.row_factory = sqlite3.Row
        columns = {entry[1] for entry in db.execute("PRAGMA table_info(tennis_decisions)")}
        if not columns or "result_winner" not in columns:
            return []
        rows = [dict(row) for row in db.execute(
            """SELECT * FROM tennis_decisions
               WHERE result_winner IS NOT NULL
               ORDER BY calculated_at DESC"""
        ).fetchall()]

    selected: dict[str, dict[str, Any]] = {}
    for row in rows:
        calculated = str(row.get("calculated_at") or "")
        kickoff = str(row.get("kickoff") or "")
        # Ecarte un eventuel recalcul post-match quand le timestamp est comparable.
        if kickoff and calculated and calculated > kickoff:
            continue
        key = _match_key(row)
        if key not in selected:
            try:
                payload = json.loads(row.get("payload_json") or "{}")
            except (TypeError, json.JSONDecodeError):
                payload = {}
            row["payload"] = payload if isinstance(payload, dict) else {}
            selected[key] = row
    return list(selected.values())


def _history_item(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload") or {}
    favorite = str(row.get("favorite") or payload.get("favori") or "")
    winner = str(row.get("result_winner") or payload.get("winner") or "")
    outsider = str(payload.get("outsider") or "")
    if not outsider:
        p1, p2 = str(row.get("player1") or ""), str(row.get("player2") or "")
        outsider = p2 if _norm(favorite) == _norm(p1) else p1
    favorite_won = _norm(winner) == _norm(favorite)
    market_favorite = _number(row.get("market_probability"))
    if market_favorite is not None and market_favorite <= 1:
        market_favorite *= 100
    elo_favorite = _number(row.get("elo_probability"))
    if elo_favorite is not None and elo_favorite <= 1:
        elo_favorite *= 100
    outsider_odds = _number(row.get("outsider_odds") or payload.get("cote_outsider"))
    reasons = [
        value for value in (
            row.get("concordance"), row.get("decision"), row.get("context_label"),
            row.get("cycle_opponent"), row.get("fatigue_favorite"),
        ) if value
    ]
    return {
        "date": str(row.get("kickoff") or row.get("calculated_at") or "")[:10],
        "kickoff": row.get("kickoff"),
        "tour": row.get("tour"),
        "tournament": row.get("tournament"),
        "surface": row.get("surface"),
        "favorite": favorite,
        "outsider": outsider,
        "winner": winner,
        "favorite_won": favorite_won,
        "upset": not favorite_won,
        "favorite_odds": _number(row.get("favorite_odds")),
        "outsider_odds": outsider_odds,
        "market_outsider_probability": round(100 - market_favorite, 1) if market_favorite is not None else None,
        "elo_outsider_probability": round(100 - elo_favorite, 1) if elo_favorite is not None else None,
        "elo_edge_points": round(-(float(row.get("elo_gap") or 0)), 1) if row.get("elo_gap") is not None else None,
        "decision": row.get("decision"),
        "decision_level": row.get("decision_level"),
        "concordance": row.get("concordance"),
        "quality": row.get("quality"),
        "favorite_cycle": row.get("cycle_favorite"),
        "favorite_fatigue": row.get("fatigue_favorite"),
        "outsider_cycle": row.get("cycle_opponent"),
        "outsider_fatigue": row.get("fatigue_opponent"),
        "signals": reasons[:5],
        "snapshot_at": row.get("calculated_at"),
    }


def _collector_recent(days: int) -> list[dict[str, Any]]:
    """Secours lorsque l'historique de decisions n'est pas encore assez peuple."""
    try:
        from app import tennis
        frame = tennis._coach()._recent_results()
    except Exception:
        return []
    if frame is None or not len(frame):
        return []
    cutoff = date.today() - timedelta(days=days)
    out = []
    for raw in frame.to_dict("records"):
        played = _parse_day(raw.get("date"))
        if not played or played < cutoff:
            continue
        odds_w, odds_l = _number(raw.get("odds_w")), _number(raw.get("odds_l"))
        if odds_w is None or odds_l is None:
            continue
        winner_is_outsider = odds_w > odds_l
        out.append({
            "date": played.isoformat(), "kickoff": None, "tour": raw.get("tour"),
            "tournament": raw.get("tournament"), "surface": raw.get("surface"),
            "favorite": raw.get("loser") if winner_is_outsider else raw.get("winner"),
            "outsider": raw.get("winner") if winner_is_outsider else raw.get("loser"),
            "winner": raw.get("winner"), "favorite_won": not winner_is_outsider,
            "upset": winner_is_outsider,
            "favorite_odds": odds_l if winner_is_outsider else odds_w,
            "outsider_odds": odds_w if winner_is_outsider else odds_l,
            "market_outsider_probability": None, "elo_outsider_probability": None,
            "elo_edge_points": None, "decision": None, "decision_level": None,
            "concordance": None, "quality": None, "favorite_cycle": None,
            "favorite_fatigue": None, "outsider_cycle": None, "outsider_fatigue": None,
            "signals": ["Resultat et cotes issus du collecteur recent"], "snapshot_at": None,
        })
    return out


def recent_outsiders(days: int = DEFAULT_DAYS, path: str | Path | None = None) -> dict[str, Any]:
    days = max(1, min(int(days), MAX_DAYS))
    cutoff = date.today() - timedelta(days=days)
    history = [
        _history_item(row) for row in _canonical_history(path)
        if (_parse_day(row.get("kickoff") or row.get("calculated_at")) or date.min) >= cutoff
    ]
    source = "decision_history"
    if not history:
        history = _collector_recent(days)
        source = "recent_results_collector"
    history.sort(key=lambda item: (item.get("date") or "", item.get("outsider") or ""), reverse=True)
    wins = [item for item in history if item["upset"]]
    losses = [item for item in history if not item["upset"]]
    priced = [item for item in wins if item.get("outsider_odds")]
    return {
        "days": days,
        "source": source,
        "canonical_match_count": len(history),
        "upset_count": len(wins),
        "favorite_win_count": len(losses),
        "upset_rate": round(len(wins) / len(history) * 100, 1) if history else None,
        "average_winning_outsider_odds": round(sum(item["outsider_odds"] for item in priced) / len(priced), 2) if priced else None,
        "winners": wins,
        "losses": losses,
    }


def _contains(value: Any, *needles: str) -> bool:
    label = _norm(value)
    return any(_norm(needle) in label for needle in needles)


def _score_row(row: dict[str, Any], recent_by_player: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    outsider = str(row.get("outsider") or "")
    market_favorite = _number(row.get("proba_marche"))
    market_outsider = 100 - market_favorite if market_favorite is not None else None
    elo_favorite = _number(row.get("proba_elo"))
    elo_outsider = 100 - elo_favorite if elo_favorite is not None else None
    elo_edge = elo_outsider - market_outsider if elo_outsider is not None and market_outsider is not None else None

    score = 25.0
    reasons: list[str] = []
    warnings: list[str] = []
    if elo_edge is not None:
        if elo_edge >= 12:
            score += 32; reasons.append(f"Elo outsider +{elo_edge:.1f} pts contre le marche")
        elif elo_edge >= 7:
            score += 24; reasons.append(f"Divergence Elo +{elo_edge:.1f} pts")
        elif elo_edge >= 3:
            score += 12; reasons.append(f"Petit avantage Elo +{elo_edge:.1f} pts")
        elif elo_edge <= -7:
            score -= 18; warnings.append(f"Elo defavorable {elo_edge:.1f} pts")
    else:
        score -= 8; warnings.append("Elo indisponible")

    concordance = row.get("concordance")
    if _contains(concordance, "conflit fort"):
        score += 18; reasons.append("Marche contredit par Elo et forme")
    elif _contains(concordance, "divergence elo"):
        score += 13; reasons.append("Divergence Elo detectee")
    elif _contains(concordance, "forme contraire"):
        score += 9; reasons.append("Forme recente opposee au favori")

    if _contains(row.get("impact_contexte"), "desavantage relatif"):
        score += 10; reasons.append("Contexte defavorable au favori")
    if _contains(row.get("cycle_adversaire"), "pic probable", "montee"):
        score += 8; reasons.append(f"Outsider en {row.get('cycle_adversaire')}")
    if _contains(row.get("fatigue_favori"), "charge lourde", "a surveiller"):
        score += 7; reasons.append("Charge du favori a surveiller")
    if _contains(row.get("fatigue_adversaire"), "charge lourde"):
        score -= 9; warnings.append("Outsider en charge lourde")

    recent = recent_by_player.get(_norm(outsider), [])
    if recent:
        bonus = min(14, 7 * len(recent))
        score += bonus
        best = max((_number(item.get("outsider_odds")) or 0 for item in recent), default=0)
        reasons.append(f"{len(recent)} victoire(s) recente(s) comme outsider" + (f", meilleure cote {best:.2f}" if best else ""))

    quality = str(row.get("qualite") or "faible")
    if _contains(quality, "elevee"):
        score += 5
    elif _contains(quality, "faible"):
        score -= 12; warnings.append("Qualite de donnees faible")

    outsider_odds = _number(row.get("cote_outsider"))
    if outsider_odds is not None and 2 <= outsider_odds <= 4:
        score += 3
    score = round(max(0, min(100, score)))
    label = "prioritaire" if score >= 65 else "a etudier" if score >= 48 else "secondaire" if score >= 32 else "ecarter"
    return {
        "tour": row.get("tour"), "tournament": row.get("tournoi"), "kickoff": row.get("kickoff"),
        "time": row.get("heure"), "surface": row.get("surface"), "favorite": row.get("favori"),
        "outsider": outsider, "favorite_odds": _number(row.get("cote")), "outsider_odds": outsider_odds,
        "market_outsider_probability": round(market_outsider, 1) if market_outsider is not None else None,
        "elo_outsider_probability": round(elo_outsider, 1) if elo_outsider is not None else None,
        "elo_edge_points": round(elo_edge, 1) if elo_edge is not None else None,
        "score": score, "label": label, "quality": quality, "decision": row.get("decision"),
        "concordance": concordance, "recent_upsets": len(recent), "reasons": reasons[:4],
        "warnings": warnings[:3], "markets": [market for market in (row.get("markets") or []) if str(market.get("key") or "").startswith("outsider_")],
    }


def _attach_odds_movement(candidate: dict[str, Any], source_row: dict[str, Any], snapshots: dict[str, list[dict[str, Any]]]) -> None:
    """Colle a chaque candidat l'evolution de sa cote outsider depuis le premier snapshot.

    C'est la reponse a "suivre l'evolution de la cote" : la serie est deja en base (un
    snapshot par construction de page), on la resume ici en open/close/direction.
    """
    from app import tennis
    from app.tennis_odds_movement import _movement

    pair_key = tennis._storage_pair(source_row.get("joueur1", ""), source_row.get("joueur2", ""))
    match_id = tennis._match_identity(source_row.get("tour"), source_row.get("tournoi"), pair_key)
    move = _movement(snapshots.get(match_id, []))
    candidate["odds_movement"] = None if move is None else {
        "snapshots": move["snapshots"],
        "opening_outsider_odds": move["opening_outsider_odds"],
        "latest_outsider_odds": move["closing_outsider_odds"],
        "delta_odds": move["delta_odds"],
        "implied_move_points": move["implied_move_points"],
        "direction": move["direction"],
    }


def build_radar(payload: dict[str, Any], days: int = DEFAULT_DAYS, path: str | Path | None = None) -> dict[str, Any]:
    recent = recent_outsiders(days=days, path=path)
    recent_by_player: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in recent.get("winners", []):
        recent_by_player[_norm(item.get("outsider"))].append(item)
    source_rows = list(payload.get("atp") or []) + list(payload.get("wta") or [])
    try:
        from app.tennis_odds_movement import _snapshots
        snapshots = _snapshots(path)
    except Exception:
        snapshots = {}
    candidates = []
    for row in source_rows:
        candidate = _score_row(row, recent_by_player)
        candidate["odds_movement"] = None  # cle toujours presente, meme sans historique
        if snapshots:
            try:
                _attach_odds_movement(candidate, row, snapshots)
            except Exception:
                pass
        candidates.append(candidate)
    candidates.sort(key=lambda item: (-item["score"], item.get("kickoff") or "9999", item.get("outsider") or ""))
    return {
        "updated": payload.get("updated"),
        "days": int(recent.get("days") or days),
        "method": "indice explicable de priorisation; ce score n'est ni une probabilite ni un ROI",
        "candidate_count": len(candidates),
        "priority_count": sum(item["score"] >= 65 for item in candidates),
        "recent_summary": {key: recent.get(key) for key in ("source", "canonical_match_count", "upset_count", "upset_rate", "average_winning_outsider_odds")},
        "candidates": candidates,
    }
