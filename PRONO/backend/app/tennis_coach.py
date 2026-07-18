"""Coach/fatigue layer for PRONO tennis matches.

The public feed gives upcoming matches and odds. This module adds a second lens:
- surface Elo/form stats when known,
- intra-tournament load from recent results,
- H2H memory, especially same tournament/surface,
- explicit evidence strings for the UI.
"""
from __future__ import annotations

import glob
import json
import math
import os
import re
import time
import unicodedata
import urllib.request as urlrequest
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
from bs4 import BeautifulSoup

from app.tennis_calibration import HistoricalCalibration

DATASET_DIR = Path(__file__).resolve().parent / "tennis_data"
RUNTIME_DIR = Path(os.environ.get("PRONO_DATA_DIR") or (DATASET_DIR / "_runtime")) / "tennis"
RECENT_CACHE = RUNTIME_DIR / "week_results.csv"
PACKAGE_RECENT = DATASET_DIR / "te" / "week_results.csv"
RECENT_TTL = 2 * 3600
ELO_SCALE = 1025.0
LOW_LEVEL = re.compile(r"challenger|itf|utr|futures", re.I)
SEED_RE = re.compile(r"\s*\(\d+\)\s*$")
TE_URL = "https://www.tennisexplorer.com/results/?type={tour}-single&year={y}&month={m}&day={d}"
SPORTSCORE_TEAM_URL = "https://sportscore.com/api/widget/team/?sport=tennis&slug={slug}&limit=10"
SPORTSCORE_TTL = 12 * 3600
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def norm(value: Any) -> str:
    value = SEED_RE.sub("", str(value or "")).strip()
    return " ".join(
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .replace(".", " ")
        .replace("-", " ")
        .split()
    )


def short_key(name: Any) -> str | None:
    parts = norm(name).split()
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    if len(parts[-1]) == 1 and len(parts) >= 2:
        return f"{parts[-2]} {parts[-1][0]}"
    return f"{parts[-1]} {parts[0][0]}"


def _float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    value = _float(value)
    return default if value is None else int(value)


def _parse_date(value: Any) -> date | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text[:10] if fmt == "%Y-%m-%d" else text[:8], fmt).date()
        except ValueError:
            pass
    return None


def _elo_probability(elo_a: float, elo_b: float) -> float:
    return 1 / (1 + 10 ** ((elo_b - elo_a) / ELO_SCALE))


def surface_key(surface: str) -> str:
    label = norm(surface)
    if label in {"terre", "clay"}:
        return "clay"
    if label in {"gazon", "grass"}:
        return "grass"
    return "hard"


def _games(cell: Any) -> int | None:
    text = str(cell).strip()
    if not text.isdigit():
        return None
    value = int(text)
    if value <= 7:
        return value
    if text[0] in "67":
        return int(text[0])
    if len(text) >= 2 and 10 <= int(text[:2]) <= 15:
        return int(text[:2])
    return int(text[0])


def _estimate_minutes(sets_total: int, games_total: int, tiebreaks: int) -> int:
    # TennisExplorer does not expose duration here; this is a load proxy, not official minutes.
    return int(round(sets_total * 18 + games_total * 2.6 + tiebreaks * 8))


def _fresh_match_label(fresh: dict[str, Any]) -> str:
    days = fresh.get("days")
    home = str(fresh.get("home") or "").strip()
    away = str(fresh.get("away") or "").strip()
    competition = str(fresh.get("competition") or "").strip()
    pair = f"{home} vs {away}" if home and away else "match"
    suffix = f", {competition}" if competition else ""
    age = f", {days}j" if days is not None else ""
    return f"{pair}{suffix}{age}"


def _same_tournament(left: Any, right: Any) -> bool:
    a, b = norm(left), norm(right)
    return bool(a and b and (a in b or b in a))


class TennisCoach:
    def __init__(self, dataset_dir: Path = DATASET_DIR):
        self.dataset_dir = Path(dataset_dir)
        self.stats = self._load_stats()
        self.history = self._load_history()
        self.calibration = HistoricalCalibration(self.history)
        self._live_results = pd.DataFrame()
        self._ctx: dict[str, dict[str, Any]] | None = None
        self._ctx_loaded_at = 0.0
        self._freshness_cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def enrich(self, match: dict[str, Any], market_p1: float) -> dict[str, Any]:
        player1 = match["player1"]
        player2 = match["player2"]
        circ = match.get("tour", "ATP")
        surf = surface_key(match.get("surface", "Dur"))
        stats1 = self.player_stats(player1, circ)
        stats2 = self.player_stats(player2, circ)
        ctx = self.context()
        ctx1 = self._player_context(player1, ctx, match.get("tournament"))
        ctx2 = self._player_context(player2, ctx, match.get("tournament"))

        elo1 = self._surface_elo(stats1, surf)
        elo2 = self._surface_elo(stats2, surf)
        elo_p1 = _elo_probability(elo1, elo2) if elo1 is not None and elo2 is not None else None

        # Form remains descriptive. Only current load, recovery and data quality
        # feed the contextual decision, avoiding a second count of recent results.
        cycle1 = self.cycle(player1, stats1, ctx1)
        cycle2 = self.cycle(player2, stats2, ctx2)
        context1 = self.context_assessment(stats1, ctx1)
        context2 = self.context_assessment(stats2, ctx2)
        h2h = self.h2h(player1, player2, match.get("tournament"), surf, circ)

        evidence_quality = self._evidence_quality(stats1, stats2, ctx1, ctx2)
        quality_score = round(0.55 + 0.45 * evidence_quality, 2)
        quality = "elevee" if quality_score >= 0.82 else "moyenne" if quality_score >= 0.68 else "faible"
        decision = self._decision(market_p1, elo_p1, context1, context2, quality_score)

        proofs = []
        if cycle1["evidence"]:
            proofs.append(f"{player1}: " + "; ".join(cycle1["evidence"][:4]))
        if cycle2["evidence"]:
            proofs.append(f"{player2}: " + "; ".join(cycle2["evidence"][:4]))
        if h2h.get("alert"):
            proofs.append(h2h["alert"])
        if elo_p1 is None:
            proofs.append("Elo surface indisponible: marche conserve comme unique reference probabiliste")

        return {
            "p1": market_p1,
            "raw_p1": elo_p1 if elo_p1 is not None else market_p1,
            "market_p1": market_p1,
            "elo_p1": elo_p1,
            "adjustment_pts_p1": 0.0,
            "source": "marche_ancre",
            "quality": quality,
            "quality_score": quality_score,
            "uncertainty_pts": decision["uncertainty_pts"],
            "cycle1": cycle1,
            "cycle2": cycle2,
            "context1": context1,
            "context2": context2,
            "decision": decision,
            "serve1": self._serve_profile(stats1),
            "serve2": self._serve_profile(stats2),
            "h2h": h2h,
            "proofs": " | ".join(proofs),
            "external_sources": sorted(set(cycle1.get("external_sources", []) + cycle2.get("external_sources", []))),
        }

    def context_assessment(self, stats: dict[str, Any] | None, ctx: dict[str, Any] | None) -> dict[str, Any]:
        score = 0.0
        positives: list[str] = []
        risks: list[str] = []
        if not stats:
            risks.append("donnees joueur incompletes")
        else:
            matches_90 = _int(stats.get("matchs_90j"))
            last = _parse_date(stats.get("derniere_date"))
            if matches_90 <= 4:
                risks.append(f"volume recent faible ({matches_90} matchs/90j)")
            if last and (date.today() - last).days >= 30:
                risks.append(f"reference locale ancienne ({(date.today() - last).days}j)")

        if ctx:
            tours = _int(ctx.get("tours_gagnes"))
            sets_lost = _int(ctx.get("sets_laches"))
            games = _int(ctx.get("jeux_joues"))
            last_games = _int(ctx.get("dernier_jeux"))
            decisifs = _int(ctx.get("decisifs"))
            matches_14 = _int(ctx.get("matchs_14j"))
            minutes = _int(ctx.get("charge_minutes_est"))
            repos = ctx.get("repos_jours")
            if tours >= 2 and sets_lost == 0:
                score += 0.04
                positives.append("parcours propre sans set perdu")
            elif tours >= 1:
                score += 0.02
                positives.append(f"{tours} tour(s) franchi(s)")
            if games >= 65 or minutes >= 150:
                score -= 0.12
                risks.append(f"charge tournoi lourde ({games} jeux, ~{minutes} min)")
            elif games >= 45 or minutes >= 110:
                score -= 0.06
                risks.append(f"charge tournoi a surveiller ({games} jeux, ~{minutes} min)")
            if last_games >= 30:
                score -= 0.05
                risks.append(f"dernier match long ({last_games} jeux)")
            if decisifs >= 2:
                score -= 0.06
                risks.append(f"{decisifs} matchs decisifs")
            elif decisifs == 1:
                score -= 0.03
                risks.append("dernier match en 3 sets")
            if matches_14 >= 5:
                score -= 0.04
                risks.append(f"{matches_14} matchs sur 14j")
            if repos is not None:
                rest = int(float(repos))
                if rest == 0:
                    score -= 0.08
                    risks.append("enchainement sans jour de repos")
                elif rest >= 8:
                    risks.append(f"{rest}j sans match officiel")
        else:
            risks.append("parcours du tournoi non detecte")

        score = max(-0.30, min(0.10, score))
        label = "favorable" if score >= 0.05 else "defavorable" if score <= -0.05 else "neutre"
        return {"score": score, "label": label, "positives": positives, "risks": risks}

    def _decision(self, market_p1: float, elo_p1: float | None, context1: dict[str, Any], context2: dict[str, Any], quality_score: float) -> dict[str, Any]:
        favorite_is_p1 = market_p1 >= 0.5
        context_delta_p1 = context1["score"] - context2["score"]
        favorite_context = context_delta_p1 if favorite_is_p1 else -context_delta_p1
        elo_gap_favorite = None
        if elo_p1 is not None:
            market_favorite = market_p1 if favorite_is_p1 else 1 - market_p1
            elo_favorite = elo_p1 if favorite_is_p1 else 1 - elo_p1
            elo_gap_favorite = elo_favorite - market_favorite

        favorite_context_data = context1 if favorite_is_p1 else context2
        opponent_context_data = context2 if favorite_is_p1 else context1
        favorable_reasons = list(favorite_context_data["positives"])
        favorable_reasons.extend(f"adversaire: {reason}" for reason in opponent_context_data["risks"][:2])
        risk_reasons = list(favorite_context_data["risks"])
        risk_reasons.extend(f"adversaire en contexte favorable: {reason}" for reason in opponent_context_data["positives"][:2])
        if elo_gap_favorite is not None and abs(elo_gap_favorite) >= 0.07:
            direction = "superieur" if elo_gap_favorite > 0 else "inferieur"
            risk_reasons.insert(0, f"Elo surface {direction} au marche ({elo_gap_favorite * 100:+.1f} pts)")

        if quality_score < 0.68:
            label, level = "Donnees insuffisantes", "insufficient"
        elif favorite_context <= -0.12 or (elo_gap_favorite is not None and abs(elo_gap_favorite) >= 0.12):
            label, level = "Vigilance forte", "strong"
        elif favorite_context <= -0.05 or (elo_gap_favorite is not None and abs(elo_gap_favorite) >= 0.07):
            label, level = "Vigilance", "watch"
        elif favorite_context >= 0.05 and elo_gap_favorite is not None and abs(elo_gap_favorite) <= 0.06:
            label, level = "Contexte favorable", "favorable"
        else:
            label, level = "Neutre", "neutral"

        elo_divergence = abs(elo_p1 - market_p1) if elo_p1 is not None else 0.0
        width = 0.025 + (1 - quality_score) * 0.08
        width += min(0.06, elo_divergence * 0.30)
        width += min(0.025, abs(context_delta_p1) * 0.08)
        width = min(0.10, width)
        low_p1 = max(0.05, market_p1 - width)
        high_p1 = min(0.95, market_p1 + width)
        reasons = risk_reasons if level in {"strong", "watch", "insufficient"} else favorable_reasons if level == "favorable" else []
        return {
            "label": label,
            "level": level,
            "context_label": "favorable" if favorite_context >= 0.05 else "defavorable" if favorite_context <= -0.05 else "neutre",
            "context_score": round(favorite_context, 3),
            "elo_gap_favorite": round(elo_gap_favorite, 4) if elo_gap_favorite is not None else None,
            "range_p1": [low_p1, high_p1],
            "uncertainty_pts": round((high_p1 - low_p1) * 50, 1),
            "reasons": reasons[:4],
        }
    def _evidence_quality(self, stats1: dict[str, Any] | None, stats2: dict[str, Any] | None, ctx1: dict[str, Any] | None, ctx2: dict[str, Any] | None) -> float:
        stats_score = sum(bool(stats) for stats in (stats1, stats2)) / 2
        sample_score = sum(min(_int((stats or {}).get("matchs_chartes")) / 20, 1) for stats in (stats1, stats2)) / 2
        context_score = sum(bool(ctx) for ctx in (ctx1, ctx2)) / 2
        return min(1.0, 0.45 * stats_score + 0.35 * sample_score + 0.20 * context_score)

    def market_priors(self, tour: str, surface: str, favorite_probability: float) -> dict[str, Any]:
        return self.calibration.estimate(tour, surface, favorite_probability)

    def calibration_report(self, test_year: int = 2025) -> dict[str, Any]:
        return self.calibration.report(test_year)

    def set_live_results(self, rows: list[dict[str, Any]]) -> None:
        self._live_results = pd.DataFrame(rows)
        self._ctx = None
        self._ctx_loaded_at = 0.0
    def _serve_profile(self, stats: dict[str, Any] | None) -> dict[str, Any]:
        if not stats:
            return {"available": False}
        return {
            "available": bool(_float(stats.get("ace_pct")) is not None),
            "ace_pct": _float(stats.get("ace_pct")),
            "df_pct": _float(stats.get("df_pct")),
            "first_in_pct": _float(stats.get("first_in_pct")),
            "first_won_pct": _float(stats.get("first_won_pct")),
            "second_won_pct": _float(stats.get("second_won_pct")),
            "bp_saved_pct": _float(stats.get("bp_saved_pct")),
            "return_won_pct": _float(stats.get("return_won_pct")),
            "sample": _int(stats.get("matchs_chartes")),
        }

    def _canonical_player_name(self, name: str, stats: dict[str, Any] | None) -> str:
        candidate = str((stats or {}).get("player") or name or "").strip()
        if candidate and "." not in candidate:
            return candidate
        key = short_key(name) or short_key(candidate)
        if key and len(self.history):
            mask = (self.history["winner_short"] == key) | (self.history["loser_short"] == key)
            hits = self.history[mask].sort_values("date_i", ascending=False)
            if len(hits):
                row = hits.iloc[0]
                if row.get("winner_short") == key:
                    return str(row.get("winner_name") or candidate or name)
                return str(row.get("loser_name") or candidate or name)
        return candidate or name

    def _sportscore_slug(self, name: str) -> str:
        return "-".join(re.sub(r"[^a-z0-9]+", " ", norm(name)).split())

    def _sportscore_freshness(self, name: str, stats: dict[str, Any] | None) -> dict[str, Any]:
        canonical = self._canonical_player_name(name, stats)
        slug = self._sportscore_slug(canonical)
        if not slug:
            return {"status": "unknown", "source": "SportScore", "name": canonical}
        cached = self._freshness_cache.get(slug)
        if cached and time.time() - cached[0] < SPORTSCORE_TTL:
            return cached[1]
        result = {"status": "unknown", "source": "SportScore", "name": canonical}
        try:
            request = urlrequest.Request(SPORTSCORE_TEAM_URL.format(slug=slug), headers={"User-Agent": UA})
            data = json.loads(urlrequest.urlopen(request, timeout=12).read().decode("utf-8"))
            team_name = ((data.get("team") or {}).get("name") or canonical)
            finished = []
            for match in data.get("matches", []):
                if str(match.get("status") or "").lower() != "finished":
                    continue
                raw_time = str(match.get("time") or "").replace("Z", "+00:00")
                try:
                    played_at = datetime.fromisoformat(raw_time).date()
                except ValueError:
                    continue
                finished.append({
                    "date": played_at,
                    "days": max(0, (date.today() - played_at).days),
                    "competition": match.get("competition") or "",
                    "home": match.get("home") or "",
                    "away": match.get("away") or "",
                })
            if finished:
                latest = max(finished, key=lambda item: item["date"])
                result = {"status": "confirmed_recent" if latest["days"] <= 14 else "probable_inactive", "source": "SportScore", "name": team_name, **latest}
            else:
                result = {"status": "no_finished_match", "source": "SportScore", "name": team_name, "count": data.get("count", 0)}
        except Exception as exc:
            result = {"status": "unavailable", "source": "SportScore", "name": canonical, "error": type(exc).__name__}
        self._freshness_cache[slug] = (time.time(), result)
        return result

    def player_stats(self, name: str, circ: str) -> dict[str, Any] | None:
        bucket = self.stats.get(str(circ).upper(), {})
        return bucket.get(norm(name)) or bucket.get(short_key(name) or "")

    def cycle(self, name: str, stats: dict[str, Any] | None, ctx: dict[str, Any] | None) -> dict[str, Any]:
        score = 0.0
        evidence: list[str] = []
        external_sources: set[str] = set()
        if not stats:
            evidence.append("forme longue inconnue")
            fresh = self._sportscore_freshness(name, stats)
            if fresh.get("status") == "confirmed_recent":
                external_sources.add("SportScore")
                evidence.append(f"match recent retrouve SportScore: {_fresh_match_label(fresh)}")
            elif fresh.get("status") == "probable_inactive":
                external_sources.add("SportScore")
                evidence.append(f"absence recente probable SportScore ({fresh.get('days')}j)")
            elif fresh.get("status") in {"no_finished_match", "unknown"}:
                evidence.append("donnee recente non retrouvee en source secondaire")
        else:
            matches_90 = _int(stats.get("matchs_90j"))
            serie = _int(stats.get("serie"))
            momentum = _float(stats.get("momentum_90j"))
            winrate = _float(stats.get("winrate_90j"))
            last = _parse_date(stats.get("derniere_date"))

            if matches_90 <= 4:
                score -= 0.04
                evidence.append(f"base locale: seulement {matches_90} matchs/90j")
            if last:
                days = (date.today() - last).days
                if days >= 30:
                    fresh = self._sportscore_freshness(name, stats)
                    if fresh.get("status") == "confirmed_recent":
                        external_sources.add("SportScore")
                        score -= 0.02
                        evidence.append(f"base locale ancienne; match recent retrouve SportScore: {_fresh_match_label(fresh)}")
                    elif fresh.get("status") == "probable_inactive":
                        external_sources.add("SportScore")
                        score -= 0.10
                        evidence.append(f"inactivite probable: dernier match SportScore il y a {fresh.get('days')}j")
                    else:
                        score -= 0.07
                        evidence.append(f"dernier match reference il y a {days}j; donnee recente non confirmee")
                elif days <= 7:
                    score += 0.03
                    evidence.append("rythme competitif recent")
            if serie >= 3:
                score += 0.09
                evidence.append(f"serie +{serie}")
            elif serie == 2:
                score += 0.05
                evidence.append("serie +2")
            elif serie <= -2:
                score -= 0.10
                evidence.append(f"serie {serie}")
            elif serie == -1 and matches_90 <= 5:
                score -= 0.05
                evidence.append("serie -1 sur faible volume")
            if momentum is not None:
                if momentum >= 25:
                    score += 0.10
                    evidence.append(f"momentum +{momentum:.0f}")
                elif momentum >= 8:
                    score += 0.06
                    evidence.append(f"momentum +{momentum:.0f}")
                elif momentum <= -20:
                    score -= 0.10
                    evidence.append(f"momentum {momentum:.0f}")
                elif momentum <= 0 and matches_90 <= 5:
                    score -= 0.06
                    evidence.append("momentum neutre/negatif")
            if winrate is not None:
                if winrate >= 0.70 and matches_90 >= 5:
                    score += 0.08
                    evidence.append(f"{winrate:.0%} de victoires sur 90j")
                elif winrate >= 0.80 and matches_90 < 5:
                    score += 0.03
                    evidence.append("signal positif mais echantillon court")

        fatigue_label = "parcours inconnu"
        if ctx:
            tours = _int(ctx.get("tours_gagnes"))
            sets_lost = _int(ctx.get("sets_laches"))
            games = _int(ctx.get("jeux_joues"))
            last_games = _int(ctx.get("dernier_jeux"))
            decisifs = _int(ctx.get("decisifs"))
            tiebreaks = _int(ctx.get("tiebreaks"))
            matches_14 = _int(ctx.get("matchs_14j"))
            minutes = _int(ctx.get("charge_minutes_est"))
            repos = ctx.get("repos_jours")

            if tours >= 2 and sets_lost == 0:
                score += 0.06
                evidence.append("parcours propre sans set perdu")
            elif tours >= 1:
                score += 0.03
                evidence.append(f"{tours} tour(s) deja franchi(s)")
            if games >= 65 or minutes >= 150:
                score -= 0.09
                evidence.append(f"charge tournoi lourde ({games} jeux, ~{minutes} min)")
            elif games >= 45 or minutes >= 110:
                score -= 0.05
                evidence.append(f"charge tournoi a surveiller ({games} jeux, ~{minutes} min)")
            if last_games >= 30:
                score -= 0.05
                evidence.append(f"dernier match long ({last_games} jeux)")
            if decisifs >= 2:
                score -= 0.06
                evidence.append(f"{decisifs} matchs decisifs")
            elif decisifs == 1:
                score -= 0.03
                evidence.append("vient de jouer en 3 sets")
            if tiebreaks >= 2:
                score -= 0.03
                evidence.append(f"{tiebreaks} tie-breaks")
            if matches_14 >= 5:
                score -= 0.05
                evidence.append(f"{matches_14} matchs sur 14j")
            if repos is not None:
                repos_i = int(float(repos))
                if repos_i == 0:
                    score -= 0.06
                    evidence.append("enchainement sans repos")
                elif repos_i >= 8:
                    score -= 0.05
                    evidence.append(f"{repos_i}j sans match officiel")
            if ctx.get("upset_cree"):
                evidence.append("vient de sortir un favori")

            if games >= 65 or minutes >= 150 or decisifs >= 2:
                fatigue_label = "charge lourde"
            elif games >= 45 or last_games >= 30 or decisifs == 1 or matches_14 >= 5:
                fatigue_label = "a surveiller"
            elif tours >= 1:
                fatigue_label = "controlee"
        else:
            evidence.append("parcours tournoi non detecte")

        score = max(-0.35, min(0.30, score))
        if score >= 0.16:
            label = "pic probable"
        elif score >= 0.07:
            label = "montee"
        elif score <= -0.18:
            label = "sous-rythme"
        elif score <= -0.07:
            label = "alerte forme"
        else:
            label = "plateau"
        return {"label": label, "fatigue": fatigue_label, "score": score, "evidence": evidence, "external_sources": sorted(external_sources)}

    def h2h(self, player1: str, player2: str, tournament: str | None, surf: str, circ: str) -> dict[str, Any]:
        if self.history is None or not len(self.history):
            return {"wins1": 0, "wins2": 0, "alert": None, "last": None, "same_tournament": None}
        k1, k2 = norm(player1), norm(player2)
        s1, s2 = short_key(player1), short_key(player2)
        circuit = self.history["tour"].eq(str(circ).upper())
        h = self.history[circuit & (
            (((self.history["winner_k"] == k1) | (self.history["winner_short"] == s1))
             & ((self.history["loser_k"] == k2) | (self.history["loser_short"] == s2)))
            | (((self.history["winner_k"] == k2) | (self.history["winner_short"] == s2))
               & ((self.history["loser_k"] == k1) | (self.history["loser_short"] == s1)))
        )].copy()
        if not len(h):
            return {"wins1": 0, "wins2": 0, "alert": None, "last": None, "same_tournament": None}
        h["winner_side"] = h.apply(lambda r: 1 if r["winner_k"] == k1 or r["winner_short"] == s1 else 2, axis=1)
        h = h.sort_values("date_i", ascending=False)
        wins1 = int((h["winner_side"] == 1).sum())
        wins2 = int((h["winner_side"] == 2).sum())
        last = self._record(h.iloc[0])
        same = h[h["tourney_name"].map(lambda v: _same_tournament(v, tournament))]
        same_rec = self._record(same.iloc[0]) if len(same) else None

        alert = None
        rec = same_rec or last
        if rec:
            winner = rec["winner_name"]
            loser = rec["loser_name"]
            year = str(rec.get("tourney_date") or "")[:4]
            score = rec.get("score") or "score n/a"
            if same_rec:
                alert = f"{rec['tourney_name']} {year}: {winner} avait deja battu {loser} ({score})"
            elif norm(rec.get("surface")) == surf:
                alert = f"H2H sur {rec['surface']}: {winner} avait battu {loser} ({score})"
        return {"wins1": wins1, "wins2": wins2, "alert": alert, "last": last, "same_tournament": same_rec}

    def context(self) -> dict[str, dict[str, Any]]:
        if self._ctx is not None and time.time() - self._ctx_loaded_at < RECENT_TTL:
            return self._ctx
        df = self._recent_results()
        self._ctx = self._build_context(df)
        self._ctx_loaded_at = time.time()
        return self._ctx

    def _player_context(self, player: str, ctx: dict[str, dict[str, Any]], tournament: str | None) -> dict[str, Any] | None:
        key = short_key(player)
        if not key:
            return None
        item = ctx.get(key)
        if item and item.get("tournoi") and tournament and not _same_tournament(item.get("tournoi"), tournament):
            # Keep freshness/global load, but avoid attributing another tournament route.
            item = dict(item)
            item.update({"tournoi": None, "tours_gagnes": 0, "sets_laches": 0, "jeux_joues": 0, "tiebreaks": 0, "decisifs": 0, "dernier_jeux": 0, "charge_minutes_est": 0})
        return item

    def _surface_elo(self, stats: dict[str, Any] | None, surf: str) -> float | None:
        if not stats:
            return None
        value = stats.get(f"elo_{surf}") or stats.get("elo_global")
        return _float(value)

    def _load_stats(self) -> dict[str, dict[str, dict[str, Any]]]:
        files = {"ATP": "joueurs_stats.csv", "WTA": "joueurs_stats_wta.csv"}
        out: dict[str, dict[str, dict[str, Any]]] = {"ATP": {}, "WTA": {}}
        for circ, filename in files.items():
            path = self.dataset_dir / filename
            if not path.exists():
                continue
            df = pd.read_csv(path)
            for row in df.to_dict("records"):
                player = row.get("player")
                for key in (norm(player), short_key(player)):
                    if key:
                        out[circ][key] = row
        advanced_files = {"ATP": "stats_avancees_atp.csv", "WTA": "stats_avancees_wta.csv"}
        for circ, filename in advanced_files.items():
            path = self.dataset_dir / filename
            if not path.exists():
                continue
            df = pd.read_csv(path)
            for row in df.to_dict("records"):
                player = row.get("player")
                for key in (norm(player), short_key(player)):
                    if key:
                        out[circ].setdefault(key, {"player": player}).update(row)
        return out

    def _load_history(self) -> pd.DataFrame:
        frames = []
        cols = {
            "tourney_date", "tourney_name", "surface", "winner_name", "loser_name",
            "score", "round", "best_of", "winner_rank_points", "loser_rank_points",
        }
        sources = (("ATP", self.dataset_dir / "tml"), ("WTA", self.dataset_dir / "tml_wta"))
        for tour, directory in sources:
            for path in glob.glob(str(directory / "*.csv")):
                try:
                    df = pd.read_csv(path, usecols=lambda c: c in cols, dtype=str)
                except (OSError, ValueError):
                    continue
                if len(df):
                    df["tour"] = tour
                    frames.append(df)
        if not frames:
            return pd.DataFrame()
        out = pd.concat(frames, ignore_index=True)
        for column in cols:
            if column not in out:
                out[column] = None
        out["winner_k"] = out["winner_name"].map(norm)
        out["loser_k"] = out["loser_name"].map(norm)
        out["winner_short"] = out["winner_name"].map(short_key)
        out["loser_short"] = out["loser_name"].map(short_key)
        out["date_i"] = pd.to_numeric(out["tourney_date"], errors="coerce").fillna(0).astype(int)
        return out
    def _recent_results(self) -> pd.DataFrame:
        base = pd.DataFrame()
        if RECENT_CACHE.exists() and time.time() - RECENT_CACHE.stat().st_mtime < RECENT_TTL:
            base = pd.read_csv(RECENT_CACHE)
        elif os.environ.get("PRONO_DATA_DIR"):
            try:
                base = self._scrape_recent(days=10)
                if len(base):
                    RECENT_CACHE.parent.mkdir(parents=True, exist_ok=True)
                    base.to_csv(RECENT_CACHE, index=False, encoding="utf-8")
            except Exception:
                base = pd.DataFrame()
        if base.empty and PACKAGE_RECENT.exists():
            base = pd.read_csv(PACKAGE_RECENT)
        frames = [frame.dropna(axis=1, how="all") for frame in (base, self._live_results) if frame is not None and len(frame)]
        if not frames:
            return pd.DataFrame()
        combined = pd.concat(frames, ignore_index=True)
        identity = [column for column in ("date", "tour", "tournament", "winner", "loser") if column in combined]
        return combined.drop_duplicates(subset=identity, keep="last") if identity else combined
    def _scrape_recent(self, days: int = 10, delay: float = 0.2) -> pd.DataFrame:
        rows = []
        today = date.today()
        for offset in range(days, -1, -1):
            day = today - timedelta(days=offset)
            for tour in ("atp", "wta"):
                try:
                    rows.extend(self._parse_day(day, tour))
                except Exception:
                    pass
                time.sleep(delay)
        return pd.DataFrame(rows)

    def _parse_day(self, day: date, tour: str) -> list[dict[str, Any]]:
        request = urlrequest.Request(
            TE_URL.format(tour=tour, y=day.year, m=day.month, d=day.day),
            headers={"User-Agent": UA},
        )
        html = urlrequest.urlopen(request, timeout=30).read()
        soup = BeautifulSoup(html, "lxml")
        out = []
        for table in soup.find_all("table", class_="result"):
            tournament = ""
            rows = table.find_all("tr")
            for i, row in enumerate(rows):
                classes = row.get("class") or []
                if "head" in classes:
                    th = row.find("td", class_="t-name")
                    if th:
                        tournament = th.get_text(strip=True)
                    continue
                if "fRow" not in classes or i + 1 >= len(rows):
                    continue
                row2 = rows[i + 1]
                w_td = row.find("td", class_="t-name")
                l_td = row2.find("td", class_="t-name")
                if not (w_td and w_td.find("a") and l_td and l_td.find("a")):
                    continue
                gw = [g for g in (_games(td.get_text(strip=True)) for td in row.find_all("td", class_="score")) if g is not None]
                gl = [g for g in (_games(td.get_text(strip=True)) for td in row2.find_all("td", class_="score")) if g is not None]
                odds_w = row.find("td", class_="coursew")
                odds_l = row.find("td", class_="course")
                try:
                    ow = float(odds_w.get_text(strip=True)) if odds_w else None
                    ol = float(odds_l.get_text(strip=True)) if odds_l else None
                except ValueError:
                    ow = ol = None
                n_sets = min(len(gw), len(gl))
                out.append({
                    "date": day.isoformat(),
                    "tour": tour.upper(),
                    "tournament": tournament,
                    "winner": SEED_RE.sub("", w_td.get_text(strip=True)).strip(),
                    "loser": SEED_RE.sub("", l_td.get_text(strip=True)).strip(),
                    "sets_w": sum(1 for a, b in zip(gw, gl) if a > b),
                    "sets_l": sum(1 for a, b in zip(gw, gl) if b > a),
                    "games_w": sum(gw[:n_sets]),
                    "games_l": sum(gl[:n_sets]),
                    "tiebreaks": sum(1 for a, b in zip(gw, gl) if a + b >= 13),
                    "odds_w": ow,
                    "odds_l": ol,
                })
        return out

    def _build_context(self, df: pd.DataFrame) -> dict[str, dict[str, Any]]:
        if df is None or not len(df):
            return {}
        ctx: dict[str, dict[str, Any]] = {}
        today = date.today()
        for row in df.itertuples(index=False):
            match_date = _parse_date(getattr(row, "date", None))
            if not match_date:
                continue
            lowtier = bool(LOW_LEVEL.search(str(getattr(row, "tournament", ""))))
            sets_total = _int(getattr(row, "sets_w", 0)) + _int(getattr(row, "sets_l", 0))
            games_total = _int(getattr(row, "games_w", 0)) + _int(getattr(row, "games_l", 0))
            tiebreaks = _int(getattr(row, "tiebreaks", 0))
            minutes_est = _estimate_minutes(sets_total, games_total, tiebreaks)
            for who, won in ((row.winner, True), (row.loser, False)):
                key = short_key(who)
                if not key:
                    continue
                item = ctx.setdefault(key, {
                    "name": who,
                    "matchs_14j": 0,
                    "dernier_match": None,
                    "tournoi": None,
                    "tours_gagnes": 0,
                    "sets_laches": 0,
                    "jeux_joues": 0,
                    "tiebreaks": 0,
                    "decisifs": 0,
                    "dernier_jeux": 0,
                    "charge_minutes_est": 0,
                    "upset_cree": False,
                    "derniere_def": None,
                })
                item["matchs_14j"] += 1
                item["dernier_match"] = max(item["dernier_match"] or match_date, match_date)
                if won and not lowtier:
                    if item["tournoi"] != row.tournament:
                        item.update({
                            "tournoi": row.tournament,
                            "tours_gagnes": 0,
                            "sets_laches": 0,
                            "jeux_joues": 0,
                            "tiebreaks": 0,
                            "decisifs": 0,
                            "dernier_jeux": 0,
                            "charge_minutes_est": 0,
                            "upset_cree": False,
                        })
                    item["tours_gagnes"] += 1
                    item["sets_laches"] += _int(row.sets_l)
                    item["jeux_joues"] += games_total
                    item["tiebreaks"] += tiebreaks
                    item["decisifs"] += int(_int(row.sets_l) >= 1 and sets_total >= 3)
                    item["dernier_jeux"] = games_total
                    item["charge_minutes_est"] += minutes_est
                    if getattr(row, "odds_w", None) and getattr(row, "odds_l", None) and row.odds_w > row.odds_l:
                        item["upset_cree"] = True
                elif not won:
                    item["derniere_def"] = match_date
        for item in ctx.values():
            last = item.get("dernier_match")
            item["repos_jours"] = (today - last).days if last else None
        return ctx

    def _record(self, row: pd.Series) -> dict[str, Any]:
        return {key: row.get(key) for key in row.index}
