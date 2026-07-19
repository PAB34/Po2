"""Backtest calibration for the PRONO tennis decision layer.

The module evaluates prematch decision snapshots against final results. It is
strictly descriptive: it measures whether historical status buckets were better
or worse calibrated than the no-vig market probability.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
from collections import defaultdict
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

BAD_RESULT = re.compile(r"RET|W/O|WO\b|DEF|ABD|ABANDON", re.I)
INSUFFICIENT = {"donnees insuffisantes", "donnees faibles", "data insufficient", "insufficient"}
PROBABILITY_BANDS = (
    (50.0, 55.0, "50-55"),
    (55.0, 60.0, "55-60"),
    (60.0, 65.0, "60-65"),
    (65.0, 70.0, "65-70"),
    (70.0, 80.0, "70-80"),
    (80.0, 101.0, "80+"),
)
DEFAULT_MIN_SAMPLE = 50


def _norm(value: Any) -> str:
    text = str(value or "").strip().lower()
    repl = str.maketrans({"á": "a", "à": "a", "â": "a", "ä": "a", "ã": "a", "å": "a", "é": "e", "è": "e", "ê": "e", "ë": "e", "í": "i", "ì": "i", "î": "i", "ï": "i", "ó": "o", "ò": "o", "ô": "o", "ö": "o", "õ": "o", "ú": "u", "ù": "u", "û": "u", "ü": "u", "ñ": "n", "ç": "c"})
    return re.sub(r"[^a-z0-9]+", " ", text.translate(repl)).strip()


def _label(value: Any, fallback: str = "Inconnu") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _probability(value: Any) -> float | None:
    number = _number(value)
    if number is None:
        return None
    if number <= 1.0:
        number *= 100.0
    if 0.0 <= number <= 100.0:
        return number
    return None


def _band(probability: float) -> str:
    for low, high, label in PROBABILITY_BANDS:
        if low <= probability < high:
            return label
    return "hors-bande"


def _wilson(successes: float, n: int, z: float = 1.96) -> tuple[float | None, float | None]:
    if n <= 0:
        return None, None
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return max(0.0, centre - margin) * 100.0, min(1.0, centre + margin) * 100.0


@dataclass(frozen=True)
class DecisionRecord:
    match_id: str
    date: str | None
    circuit: str
    surface: str
    favorite: str
    market_probability: float
    elo_probability: float | None
    elo_gap: float | None
    decision: str
    concordance: str
    cycle_favorite: str | None
    fatigue_favorite: str | None
    cycle_opponent: str | None
    fatigue_opponent: str | None
    favorite_odds: float | None
    outsider_odds: float | None
    winner: str
    favorite_won: bool


@dataclass(frozen=True)
class BucketStats:
    bucket_type: str
    bucket: str
    n: int
    favorite_win_rate: float
    market_probability: float
    delta_points: float
    ci95_low: float | None
    ci95_high: float | None
    delta_ci95_low: float | None
    delta_ci95_high: float | None
    brier_market: float
    brier_elo: float | None
    roi_favorite: float | None
    roi_fade: float | None
    conclusion: str
    verdict: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "type": self.bucket_type,
            "bucket": self.bucket,
            "n": self.n,
            "favorite_win_rate": round(self.favorite_win_rate, 1),
            "market_probability": round(self.market_probability, 1),
            "delta_points": round(self.delta_points, 1),
            "ci95": [round(self.ci95_low, 1), round(self.ci95_high, 1)] if self.ci95_low is not None and self.ci95_high is not None else None,
            "delta_ci95": [round(self.delta_ci95_low, 1), round(self.delta_ci95_high, 1)] if self.delta_ci95_low is not None and self.delta_ci95_high is not None else None,
            "brier_market": round(self.brier_market, 4),
            "brier_elo": round(self.brier_elo, 4) if self.brier_elo is not None else None,
            "roi_favorite": round(self.roi_favorite, 3) if self.roi_favorite is not None else None,
            "roi_fade": round(self.roi_fade, 3) if self.roi_fade is not None else None,
            "conclusion": self.conclusion,
            "verdict": self.verdict,
        }


def _is_insufficient(*values: str) -> bool:
    return any(_norm(value) in INSUFFICIENT for value in values if value)


def _winner_matches_favorite(winner: str, favorite: str) -> bool:
    return _norm(winner) == _norm(favorite)


def _record_from_flat(item: dict[str, Any], index: int = 0) -> DecisionRecord | None:
    raw = item.get("raw") if isinstance(item.get("raw"), dict) else item
    identity = item.get("identity") if isinstance(item.get("identity"), dict) else {}
    lecture = item.get("lecture") if isinstance(item.get("lecture"), dict) else {}
    probabilities = item.get("probabilities") if isinstance(item.get("probabilities"), dict) else {}
    elo = item.get("elo") if isinstance(item.get("elo"), dict) else {}
    context = item.get("context") if isinstance(item.get("context"), dict) else {}

    favorite = _label(raw.get("favori") or lecture.get("favorite") or item.get("favori") or item.get("favorite"), "")
    winner = _label(raw.get("winner") or item.get("winner") or item.get("result_winner") or item.get("winner_name"), "")
    market_probability = _probability(raw.get("proba_marche") or probabilities.get("market") or item.get("proba_marche") or item.get("market_probability"))
    if not favorite or not winner or market_probability is None:
        return None
    if BAD_RESULT.search(str(raw.get("score") or raw.get("status") or item.get("score") or item.get("status") or "")):
        return None

    decision = _label(raw.get("decision") or lecture.get("decision") or item.get("decision"))
    concordance = _label(raw.get("concordance") or lecture.get("concordance") or item.get("concordance"))
    if _is_insufficient(decision, concordance):
        return None

    favorite_odds = _number(raw.get("cote") or probabilities.get("odds") or item.get("cote") or item.get("favorite_odds"))
    outsider_odds = _number(raw.get("cote_outsider") or raw.get("outsider_odds") or item.get("cote_outsider") or item.get("outsider_odds"))
    return DecisionRecord(
        match_id=str(item.get("match_id") or raw.get("match_id") or f"row-{index}"),
        date=str(raw.get("kickoff") or identity.get("kickoff_raw") or identity.get("kickoff") or item.get("date") or "") or None,
        circuit=_label(raw.get("tour") or identity.get("circuit") or item.get("circuit"), "ATP").upper(),
        surface=_label(raw.get("surface") or identity.get("surface") or item.get("surface"), "surface inconnue"),
        favorite=favorite,
        market_probability=market_probability,
        elo_probability=_probability(raw.get("proba_elo") or probabilities.get("elo_surface") or probabilities.get("elo_global") or item.get("proba_elo")),
        elo_gap=_number(raw.get("ecart_elo") or elo.get("gap_vs_market_points") or item.get("ecart_elo")),
        decision=decision,
        concordance=concordance,
        cycle_favorite=raw.get("cycle_favori") or context.get("favorite_cycle") or item.get("cycle_favori"),
        fatigue_favorite=raw.get("fatigue_favori") or context.get("favorite_fatigue") or item.get("fatigue_favori"),
        cycle_opponent=raw.get("cycle_adversaire") or context.get("opponent_cycle") or item.get("cycle_adversaire"),
        fatigue_opponent=raw.get("fatigue_adversaire") or context.get("opponent_fatigue") or item.get("fatigue_adversaire"),
        favorite_odds=favorite_odds,
        outsider_odds=outsider_odds,
        winner=winner,
        favorite_won=_winner_matches_favorite(winner, favorite),
    )


def records_from_export_payload(payload: dict[str, Any]) -> list[DecisionRecord]:
    rows: list[dict[str, Any]] = []
    if isinstance(payload.get("matches"), list):
        rows.extend(payload["matches"])
    if isinstance(payload.get("rows"), list):
        rows.extend(payload["rows"])
    if isinstance(payload.get("data"), list):
        rows.extend(payload["data"])
    if not rows and all(key in payload for key in ("favori", "winner", "proba_marche")):
        rows = [payload]
    records = [_record_from_flat(row, index) for index, row in enumerate(rows)]
    return [record for record in records if record is not None]


def records_from_json_file(path: str | Path) -> list[DecisionRecord]:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return records_from_export_payload(payload)


def records_from_sqlite(path: str | Path) -> list[DecisionRecord]:
    db_path = Path(path)
    if not db_path.exists():
        return []
    with closing(sqlite3.connect(db_path)) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM tennis_decisions WHERE result_winner IS NOT NULL").fetchall()
    records: list[DecisionRecord] = []
    for index, row in enumerate(rows):
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            payload = {}
        payload.setdefault("result_winner", row["result_winner"])
        payload.setdefault("winner", row["result_winner"])
        payload.setdefault("match_id", row["id"])
        payload.setdefault("kickoff", row["kickoff"])
        payload.setdefault("tour", row["tour"])
        payload.setdefault("tournoi", row["tournament"])
        payload.setdefault("favori", row["favorite"])
        payload.setdefault("cote", row["favorite_odds"])
        payload.setdefault("proba_marche", row["market_probability"])
        payload.setdefault("proba_elo", row["elo_probability"])
        payload.setdefault("ecart_elo", row["elo_gap"])
        payload.setdefault("decision", row["decision"])
        payload.setdefault("decision_level", row["decision_level"])
        payload.setdefault("impact_contexte", row["context_label"])
        payload.setdefault("qualite", row["quality"])
        record = _record_from_flat(payload, index)
        if record is not None:
            records.append(record)
    return records


def _profit_favorite(record: DecisionRecord) -> float | None:
    if record.favorite_odds is None or record.favorite_odds <= 1:
        return None
    return record.favorite_odds - 1.0 if record.favorite_won else -1.0


def _profit_fade(record: DecisionRecord) -> float | None:
    if record.outsider_odds is None or record.outsider_odds <= 1:
        return None
    return -1.0 if record.favorite_won else record.outsider_odds - 1.0


def _bucket_stats(bucket_type: str, bucket: str, records: list[DecisionRecord], min_sample: int) -> BucketStats:
    n = len(records)
    wins = sum(1 for record in records if record.favorite_won)
    win_rate = wins / n * 100.0 if n else 0.0
    market = sum(record.market_probability for record in records) / n if n else 0.0
    market_errors = [((record.market_probability / 100.0) - float(record.favorite_won)) ** 2 for record in records]
    elo_records = [record for record in records if record.elo_probability is not None]
    elo_errors = [((record.elo_probability or 0.0) / 100.0 - float(record.favorite_won)) ** 2 for record in elo_records]
    fav_profits = [profit for profit in (_profit_favorite(record) for record in records) if profit is not None]
    fade_profits = [profit for profit in (_profit_fade(record) for record in records) if profit is not None]
    ci_low, ci_high = _wilson(wins, n)
    delta_low = ci_low - market if ci_low is not None else None
    delta_high = ci_high - market if ci_high is not None else None
    delta = win_rate - market
    if n < min_sample:
        conclusion = "non_concluant"
        verdict = f"{bucket}: n={n}, echantillon < {min_sample}; ne pas interpreter le delta."
    elif delta_low is not None and delta_high is not None and delta_low <= 0 <= delta_high:
        conclusion = "bruit_probable"
        verdict = f"{bucket}: n={n}, favori realise {win_rate:.1f}% vs {market:.1f}% attendu; delta {delta:+.1f} pts non significatif."
    elif delta < 0:
        anchor = "Elo" if elo_errors and sum(elo_errors) / len(elo_errors) < sum(market_errors) / len(market_errors) else "marche"
        conclusion = "favori_surcote_historique"
        verdict = f"{bucket}: n={n}, favori realise {win_rate:.1f}% vs {market:.1f}% attendu; delta {delta:+.1f} pts significatif, ancre {anchor}."
    else:
        anchor = "Elo" if elo_errors and sum(elo_errors) / len(elo_errors) < sum(market_errors) / len(market_errors) else "marche"
        conclusion = "favori_souscote_historique"
        verdict = f"{bucket}: n={n}, favori realise {win_rate:.1f}% vs {market:.1f}% attendu; delta {delta:+.1f} pts significatif, ancre {anchor}."
    return BucketStats(
        bucket_type=bucket_type,
        bucket=bucket,
        n=n,
        favorite_win_rate=win_rate,
        market_probability=market,
        delta_points=delta,
        ci95_low=ci_low,
        ci95_high=ci_high,
        delta_ci95_low=delta_low,
        delta_ci95_high=delta_high,
        brier_market=sum(market_errors) / len(market_errors) if market_errors else 0.0,
        brier_elo=sum(elo_errors) / len(elo_errors) if elo_errors else None,
        roi_favorite=sum(fav_profits) / len(fav_profits) if fav_profits else None,
        roi_fade=sum(fade_profits) / len(fade_profits) if fade_profits else None,
        conclusion=conclusion,
        verdict=verdict,
    )


def _add(grouped: dict[tuple[str, str], list[DecisionRecord]], bucket_type: str, bucket: str, record: DecisionRecord) -> None:
    grouped[(bucket_type, bucket)].append(record)


def run_decision_calibration(records: Iterable[DecisionRecord], min_sample: int = DEFAULT_MIN_SAMPLE) -> dict[str, Any]:
    clean = [record for record in records if not _is_insufficient(record.decision, record.concordance)]
    grouped: dict[tuple[str, str], list[DecisionRecord]] = defaultdict(list)
    for record in clean:
        decision = _label(record.decision)
        concordance = _label(record.concordance)
        cross = f"{decision} x {concordance}"
        _add(grouped, "decision", decision, record)
        _add(grouped, "concordance", concordance, record)
        _add(grouped, "decision_concordance", cross, record)
        _add(grouped, "probability_band_decision", f"{_band(record.market_probability)} x {decision}", record)
        _add(grouped, "circuit_decision", f"{record.circuit} x {decision}", record)
        surface = _label(record.surface)
        _add(grouped, "surface_decision", f"{surface} x {decision}", record)
    buckets = [_bucket_stats(kind, bucket, rows, min_sample).as_dict() for (kind, bucket), rows in grouped.items()]
    buckets.sort(key=lambda item: (item["type"], -item["n"], item["bucket"]))
    primary = [item for item in buckets if item["type"] == "decision_concordance"]
    decisive = [item for item in primary if item["conclusion"] in {"favori_surcote_historique", "favori_souscote_historique"}]
    return {
        "method": "prematch decision snapshots only; outcome=1 if market favorite won; Wilson 95% interval; buckets with n < min_sample are non-conclusive",
        "min_sample": min_sample,
        "record_count": len(clean),
        "bucket_count": len(buckets),
        "buckets": buckets,
        "primary": primary,
        "decisive": decisive,
    }


def status_summary_for_row(row: dict[str, Any], report: dict[str, Any] | None, min_sample: int = DEFAULT_MIN_SAMPLE) -> dict[str, Any] | None:
    if not report:
        return None
    bucket = f"{_label(row.get('decision'))} x {_label(row.get('concordance'))}"
    candidates = [item for item in report.get("primary", []) if item.get("bucket") == bucket]
    if not candidates:
        return {"bucket": bucket, "conclusion": "non_concluant", "label": "Calibration historique non concluant", "detail": "Aucun historique de statuts identiques avec resultat."}
    item = candidates[0]
    if int(item.get("n") or 0) < min_sample or item.get("conclusion") == "non_concluant":
        return {"bucket": bucket, "n": item.get("n"), "conclusion": "non_concluant", "label": "Calibration historique non concluant", "detail": f"Statuts identiques passes: n={item.get('n')}, seuil {min_sample}."}
    detail = f"Statuts identiques passes: favori realise {item.get('favorite_win_rate')}% vs {item.get('market_probability')}% attendu (n={item.get('n')}, delta {item.get('delta_points'):+.1f} pts)."
    return {"bucket": bucket, "n": item.get("n"), "conclusion": item.get("conclusion"), "label": "Calibration historique du statut", "detail": detail, "bucket_stats": item}


def run_from_sqlite(path: str | Path, min_sample: int = DEFAULT_MIN_SAMPLE) -> dict[str, Any]:
    return run_decision_calibration(records_from_sqlite(path), min_sample=min_sample)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backtest PRONO tennis decision-layer calibration.")
    parser.add_argument("source", help="Path to decision_history.sqlite3 or a JSON export file")
    parser.add_argument("--min-sample", type=int, default=DEFAULT_MIN_SAMPLE)
    args = parser.parse_args(argv)
    path = Path(args.source)
    records = records_from_sqlite(path) if path.suffix.lower() in {".sqlite", ".sqlite3", ".db"} else records_from_json_file(path)
    print(json.dumps(run_decision_calibration(records, min_sample=args.min_sample), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
