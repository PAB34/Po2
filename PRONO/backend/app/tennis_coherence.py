"""Coherence logique entre picks tennis (matrice de correlation empirique).

Le module QUALIFIE les relations entre picks (redondance / tension), il ne recalcule
jamais les probabilites des sous-modeles. Les correlations viennent des donnees
(historique de matchs termines), pas d'un a priori: l'a priori tennis sert seulement
a choisir les marches a inclure dans la matrice.

Deux usages:
  - coherence_flags(picks, circuit, bin): tensions/redondances entre picks d'un match.
  - check_ticket(selections): analyse d'un ticket (intra-match correle, inter-match
    traite comme independant, proba jointe corrigee par frequence historique du bin).

Matrice v1 = 6 marches "match" issus de app.tennis_calibration (favori = mieux classe):
  over_22_5, three_sets, tiebreak, favorite_2_0, favorite_2_1, favorite_cover_2_5.
Les paires props joueur x match sont volontairement HORS v1 (echantillons trop minces).
"""
from __future__ import annotations

import itertools
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MARKETS = ("over_22_5", "three_sets", "tiebreak", "favorite_2_0", "favorite_2_1", "favorite_cover_2_5")

# Seuils sur phi (correlation de deux binaires, attenuee vs continue). Ajustables ici.
# Justification: |phi|>=0.20 = co-occurrence deja nette; >=0.35 = forte (flag prioritaire);
# <0.10 = quasi independant. Avec n en milliers ces valeurs sont largement significatives.
PHI_STRONG = 0.35
PHI_NOTABLE = 0.20
PHI_INDEP = 0.10
MIN_SAMPLE = 200  # sous ce seuil pour une paire: relation "non evaluee", jamais de flag faux

MATRIX_PATH = Path(__file__).resolve().parent / "tennis_data" / "coherence_matrix.json"

# Un pick = un marche + un cote (outcome vise, 1 ou 0). side "yes"->1, "no"->0.
MARKET_LABELS = {
    ("over_22_5", 1): "Over 22.5 jeux",
    ("over_22_5", 0): "Under 22.5 jeux",
    ("three_sets", 1): "Match en 3 sets",
    ("three_sets", 0): "Match en 2 sets",
    ("tiebreak", 1): "Tie-break oui",
    ("tiebreak", 0): "Tie-break non",
    ("favorite_2_0", 1): "Favori 2-0",
    ("favorite_2_1", 1): "Favori 2-1",
    ("favorite_cover_2_5", 1): "Favori -2.5 jeux",
    ("favorite_cover_2_5", 0): "Adversaire +2.5 jeux",
}


def _pair_key(market_a: str, market_b: str) -> str:
    return "|".join(sorted((market_a, market_b)))


def _side_value(side: Any) -> int:
    text = str(side or "").strip().lower()
    if text in {"yes", "oui", "over", "1", "true", "favori", "favorite", "cover"}:
        return 1
    return 0


# ---------------------------------------------------------------------------
# Construction de la matrice (script offline)
# ---------------------------------------------------------------------------
def _scope_stats(records: list[dict]) -> dict:
    n = len(records)
    marginals = {m: (sum(r[m] for r in records) / n if n else 0.0) for m in MARKETS}
    pairs: dict[str, Any] = {}
    for market_a, market_b in itertools.combinations(MARKETS, 2):
        p_a, p_b = marginals[market_a], marginals[market_b]
        p_ab = sum(r[market_a] * r[market_b] for r in records) / n if n else 0.0
        denom = math.sqrt(p_a * (1 - p_a) * p_b * (1 - p_b))
        phi = (p_ab - p_a * p_b) / denom if denom > 0 else 0.0
        pairs[_pair_key(market_a, market_b)] = {
            "n": n, "p_ab": round(p_ab, 4), "phi": round(phi, 4),
        }
    return {"n": n, "marginals": {k: round(v, 4) for k, v in marginals.items()}, "pairs": pairs}


def build_matrix_from_records(records: list[dict], min_sample: int = MIN_SAMPLE) -> dict:
    groups = {
        "ALL": records,
        "ATP": [r for r in records if r.get("tour") == "ATP"],
        "WTA": [r for r in records if r.get("tour") == "WTA"],
    }
    scopes: dict[str, Any] = {}
    for scope, recs in groups.items():
        by_bin = {"all": _scope_stats(recs)}
        for bin_index in range(5):
            bin_recs = [r for r in recs if r.get("bin") == bin_index]
            if bin_recs:
                by_bin[str(bin_index)] = _scope_stats(bin_recs)
        scopes[scope] = by_bin
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "min_sample": min_sample,
        "markets": list(MARKETS),
        "method": "phi empirique par paire de marches, par circuit et par bin de force du favori",
        "scopes": scopes,
    }


# ---------------------------------------------------------------------------
# Chargement runtime
# ---------------------------------------------------------------------------
_MATRIX_CACHE: dict[str, Any] | None = None


def load_matrix(path: str | Path | None = None) -> dict | None:
    global _MATRIX_CACHE
    if path is None and _MATRIX_CACHE is not None:
        return _MATRIX_CACHE
    target = Path(path) if path else MATRIX_PATH
    if not target.exists():
        return None
    with open(target, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if path is None:
        _MATRIX_CACHE = data
    return data


def _scope_for(matrix: dict, circuit: str, bin_key: str) -> dict | None:
    scopes = matrix.get("scopes", {})
    scope = scopes.get(str(circuit or "ALL").upper()) or scopes.get("ALL")
    if not scope:
        return None
    return scope.get(str(bin_key)) or scope.get("all")


# ---------------------------------------------------------------------------
# Relation entre deux picks
# ---------------------------------------------------------------------------
def _classify(signed_phi: float) -> tuple[str, str]:
    magnitude = abs(signed_phi)
    if magnitude < PHI_INDEP:
        return "quasi_independant", "info"
    strength = "fort" if magnitude >= PHI_STRONG else "modere"
    return ("redondance" if signed_phi > 0 else "tension"), strength


def relation(matrix: dict, circuit: str, market_a: str, side_a: Any, market_b: str, side_b: Any, bin_key: str = "all", min_sample: int | None = None) -> dict | None:
    if market_a == market_b:
        return None
    threshold = matrix.get("min_sample", MIN_SAMPLE) if min_sample is None else min_sample
    scope = _scope_for(matrix, circuit, bin_key) or _scope_for(matrix, circuit, "all")
    cell = (scope or {}).get("pairs", {}).get(_pair_key(market_a, market_b))
    if not cell:
        return None
    va, vb = _side_value(side_a), _side_value(side_b)
    label_a = MARKET_LABELS.get((market_a, va), f"{market_a}={va}")
    label_b = MARKET_LABELS.get((market_b, vb), f"{market_b}={vb}")
    n = int(cell.get("n") or 0)
    if n < threshold:
        return {"market_a": market_a, "side_a": va, "market_b": market_b, "side_b": vb,
                "label_a": label_a, "label_b": label_b, "n": n, "relation": "non_evaluee",
                "strength": "info", "phi": None,
                "message": f"{label_a} x {label_b}: echantillon insuffisant (n={n} < {threshold}), relation non evaluee."}
    # phi stocke = corr(marketA_out=1, marketB_out=1); inverser le cote inverse le signe.
    signed = float(cell["phi"]) * (1 if va == 1 else -1) * (1 if vb == 1 else -1)
    kind, strength = _classify(signed)
    if kind == "tension":
        message = f"{label_a} et {label_b} tirent en sens oppose (correlation historique {signed:+.2f}, n={n}) : ne pas jouer les deux."
    elif kind == "redondance":
        message = f"{label_a} et {label_b} sont fortement liees (correlation historique {signed:+.2f}, n={n}) : combine redondant, probablement refuse ou mal paye."
    else:
        message = f"{label_a} et {label_b} sont quasi independantes (correlation historique {signed:+.2f}, n={n})."
    return {"market_a": market_a, "side_a": va, "market_b": market_b, "side_b": vb,
            "label_a": label_a, "label_b": label_b, "n": n, "relation": kind,
            "strength": strength, "phi": round(signed, 3), "message": message}


def _joint_estimate(matrix: dict, circuit: str, market_a: str, va: int, market_b: str, vb: int, bin_key: str) -> dict | None:
    scope = _scope_for(matrix, circuit, bin_key)
    if scope is None:
        return None
    cell = scope.get("pairs", {}).get(_pair_key(market_a, market_b))
    marginals = scope.get("marginals", {})
    if not cell or market_a not in marginals or market_b not in marginals:
        return None
    p_a1, p_b1, p_ab = float(marginals[market_a]), float(marginals[market_b]), float(cell["p_ab"])
    grid = {(1, 1): p_ab, (1, 0): p_a1 - p_ab, (0, 1): p_b1 - p_ab, (0, 0): 1 - p_a1 - p_b1 + p_ab}
    joint_corr = max(0.0, grid[(va, vb)])
    p_a_side = p_a1 if va == 1 else 1 - p_a1
    p_b_side = p_b1 if vb == 1 else 1 - p_b1
    joint_independent = p_a_side * p_b_side
    return {
        "bin_used": bin_key if scope is _scope_for(matrix, circuit, bin_key) else "all",
        "p_a": round(p_a_side, 3), "p_b": round(p_b_side, 3),
        "joint_independent": round(joint_independent, 3),
        "joint_corrected": round(joint_corr, 3),
        "note": "proba jointe historique (marges du bin de force, pas les probas exactes du match)",
    }


# ---------------------------------------------------------------------------
# Sorties publiques
# ---------------------------------------------------------------------------
def coherence_flags(picks: list[tuple[str, Any]], circuit: str = "ALL", bin_key: str = "all", matrix: dict | None = None) -> list[dict]:
    """picks = liste de (market, side). Renvoie les paires en tension/redondance notables."""
    matrix = matrix if matrix is not None else load_matrix()
    if not matrix or len(picks) < 2:
        return []
    flags = []
    for (market_a, side_a), (market_b, side_b) in itertools.combinations(picks, 2):
        rel = relation(matrix, circuit, market_a, side_a, market_b, side_b, bin_key=bin_key)
        if rel and rel["relation"] in {"tension", "redondance"} and abs(rel["phi"] or 0) >= PHI_NOTABLE:
            flags.append(rel)
    flags.sort(key=lambda item: abs(item.get("phi") or 0), reverse=True)
    return flags


def check_ticket(selections: list[dict], matrix: dict | None = None) -> dict:
    """selections = [{match_id, market, side, circuit?, bin?}]. Analyse intra/inter-match."""
    matrix = matrix if matrix is not None else load_matrix()
    if not matrix:
        return {"status": "no_matrix", "intra_match": [], "inter_match_pairs": 0, "unevaluated": []}
    by_match: dict[str, list[dict]] = {}
    for sel in selections:
        by_match.setdefault(str(sel.get("match_id") or "?"), []).append(sel)
    intra, unevaluated = [], []
    intra_count = 0
    for match_id, group in by_match.items():
        circuit = str((group[0].get("circuit") or "ALL")).upper()
        bin_key = str(group[0].get("bin") or "all")
        for sel_a, sel_b in itertools.combinations(group, 2):
            market_a, market_b = sel_a.get("market"), sel_b.get("market")
            if market_a not in MARKETS or market_b not in MARKETS or market_a == market_b:
                unevaluated.append({"match_id": match_id, "market_a": market_a, "market_b": market_b, "reason": "hors matrice v1"})
                continue
            intra_count += 1
            rel = relation(matrix, circuit, market_a, sel_a.get("side"), market_b, sel_b.get("side"), bin_key=bin_key)
            if rel is None:
                unevaluated.append({"match_id": match_id, "market_a": market_a, "market_b": market_b, "reason": "paire absente de la matrice"})
                continue
            if rel["relation"] == "non_evaluee":
                unevaluated.append({"match_id": match_id, **{k: rel[k] for k in ("market_a", "market_b", "n", "message")}})
                continue
            entry = {"match_id": match_id, **rel}
            joint = _joint_estimate(matrix, circuit, market_a, rel["side_a"], market_b, rel["side_b"], bin_key)
            if joint:
                entry["joint"] = joint
            intra.append(entry)
    inter_pairs = 0
    match_ids = list(by_match)
    for i in range(len(match_ids)):
        for j in range(i + 1, len(match_ids)):
            inter_pairs += len(by_match[match_ids[i]]) * len(by_match[match_ids[j]])
    intra.sort(key=lambda item: abs(item.get("phi") or 0), reverse=True)
    return {
        "status": "ok",
        "intra_match": intra,
        "inter_match_pairs": inter_pairs,
        "inter_match_note": f"{inter_pairs} paire(s) inter-matchs traitees comme independantes (matchs distincts)",
        "unevaluated": unevaluated,
        "tension_count": sum(1 for item in intra if item["relation"] == "tension"),
        "redundancy_count": sum(1 for item in intra if item["relation"] == "redondance"),
    }


# ---------------------------------------------------------------------------
# CLI: recalcule la matrice depuis l'historique et l'ecrit en config versionnee
# ---------------------------------------------------------------------------
def _load_records() -> list[dict]:
    from app.tennis_coach import TennisCoach
    return list(TennisCoach().calibration.records)


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Recalcule la matrice de coherence tennis depuis l'historique.")
    parser.add_argument("--out", default=str(MATRIX_PATH))
    parser.add_argument("--min-sample", type=int, default=MIN_SAMPLE)
    parser.add_argument("--summary", action="store_true", help="Affiche le tableau des correlations principales.")
    args = parser.parse_args(argv)
    matrix = build_matrix_from_records(_load_records(), min_sample=args.min_sample)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(matrix, handle, ensure_ascii=True, indent=2)
    print(f"Matrice ecrite: {args.out} (n ALL={matrix['scopes']['ALL']['all']['n']})")
    if args.summary:
        for scope in ("ALL", "ATP", "WTA"):
            stats = matrix["scopes"][scope]["all"]
            print(f"\n== {scope} (n={stats['n']}) ==")
            ranked = sorted(stats["pairs"].items(), key=lambda kv: abs(kv[1]["phi"]), reverse=True)
            for key, cell in ranked:
                print(f"  {key:45} phi={cell['phi']:+.3f}  n={cell['n']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
