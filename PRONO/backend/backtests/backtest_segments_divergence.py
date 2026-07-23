"""Ou le signal "Elo contre le marche" rapporte-t-il, s'il rapporte quelque part ?

backtest_elo_vs_marche.py a etabli le fait genant : l'Elo qui contredit le marche fait
passer l'outsider de 28,8 % a 40,8 % de victoires, et le ROI reste a -0,0 %. Le book
price deja l'Elo. Globalement.

Reste une question que la moyenne peut cacher : ce -0,0 % est-il uniforme, ou est-ce la
somme d'un segment perdant et d'un segment gagnant ? C'est la seule question a laquelle
ces donnees permettent de repondre en EUROS -- le marche vainqueur est le seul dont les
cotes sont archivees.

Piege principal : en decoupant assez finement, on trouve toujours un segment rentable.
Le protocole s'en protege comme il peut.

  1. EXPLORATION sur 2001-2018. On y regarde tout ce qu'on veut.
  2. VALIDATION sur 2019-2025, jamais consultee pour choisir les segments.
  3. Le nombre de segments testes est affiche : avec 24 segments, en avoir 1 ou 2 qui
     "marchent" par hasard en exploration est l'attendu, pas une decouverte.

Un segment n'est retenu comme piste que s'il est rentable dans les DEUX periodes. Meme
alors, ce n'est pas une preuve : c'est ce qui merite d'etre journalise en reel.

Usage (depuis saas/pronostics/Pronos, comme les autres backtests) :
    python <chemin>/backtest_segments_divergence.py
"""
from __future__ import annotations

import math
import os
import re
from collections import defaultdict

import pandas as pd

K = 32.0
MIN_MATCHES = 20
EXPLORE_END = 2018          # tout ce qui est <= est libre d'exploration
BAD = re.compile(r"RET|W/O|WO\b|DEF|ABD", re.I)
COLS = ["tourney_date", "winner_name", "loser_name", "score", "surface",
        "synth_odds_W", "synth_odds_L", "true_prob_W", "true_prob_L"]

CANDIDATE_PATHS = (
    "data_cache/td/features_v36.csv",
    "saas/pronostics/Pronos/data_cache/td/features_v36.csv",
    "../../../saas/pronostics/Pronos/data_cache/td/features_v36.csv",
)

# Bandes choisies AVANT de regarder le moindre resultat, sur des criteres lisibles :
# de combien l'Elo contredit le marche, et a quel prix se paie l'outsider.
ELO_BANDS = ((0, 50), (50, 100), (100, 200), (200, 10_000))
ODDS_BANDS = ((1.0, 2.0), (2.0, 3.0), (3.0, 5.0), (5.0, 1_000.0))


def _band(value, bands):
    for low, high in bands:
        if low <= value < high:
            return f"{low:g}-{high:g}" if high < 1_000 else f"{low:g}+"
    return None


def _find_dataset() -> str:
    for path in CANDIDATE_PATHS:
        if os.path.exists(path):
            return path
    raise SystemExit(
        "features_v36.csv introuvable. Lancer depuis saas/pronostics/Pronos, "
        "ou depuis la racine du depot."
    )


def _roi(profits: list[float]) -> tuple[float, float, float]:
    """ROI, et demi-largeur de l'intervalle a 95 % (approximation normale).

    L'IC est indispensable ici : un ROI de +4 % sur 300 paris est indiscernable de zero,
    et c'est exactement le genre de chiffre qui donne envie de miser.
    """
    n = len(profits)
    if n < 2:
        return 0.0, 0.0, 0.0
    mean = sum(profits) / n
    var = sum((p - mean) ** 2 for p in profits) / (n - 1)
    return mean, 1.96 * math.sqrt(var / n), math.sqrt(var)


def collect() -> list[dict]:
    df = pd.read_csv(_find_dataset(), usecols=COLS, low_memory=False)
    df = df.dropna(subset=["synth_odds_W", "synth_odds_L", "true_prob_W", "true_prob_L",
                           "winner_name", "loser_name"])
    df = df.sort_values("tourney_date")

    elo: dict[str, float] = defaultdict(lambda: 1500.0)
    played: dict[str, int] = defaultdict(int)
    bets: list[dict] = []

    for row in df.itertuples(index=False):
        w, l = row.winner_name, row.loser_name
        if played[w] >= MIN_MATCHES and played[l] >= MIN_MATCHES:
            if row.true_prob_W >= row.true_prob_L:
                fav, out, out_odds, out_won = w, l, row.synth_odds_L, False
            else:
                fav, out, out_odds, out_won = l, w, row.synth_odds_W, True
            gap = elo[out] - elo[fav]
            if gap > 0 and out_odds and out_odds > 1:   # l'Elo contredit le marche
                bets.append({
                    "year": int(str(row.tourney_date)[:4]),
                    "gap": gap,
                    "odds": float(out_odds),
                    "surface": str(row.surface or "?"),
                    "profit": (float(out_odds) - 1.0) if out_won else -1.0,
                })
        # Elo mis a jour APRES lecture : aucune fuite d'information.
        e = 1.0 / (1.0 + 10 ** ((elo[l] - elo[w]) / 400.0))
        elo[w] += K * (1 - e)
        elo[l] -= K * (1 - e)
        played[w] += 1
        played[l] += 1
    return bets


def _table(title: str, groups: dict[str, list[float]], min_n: int) -> dict[str, float]:
    print(f"\n{title}")
    print(f"{'segment':<26}{'n':>7}{'ROI':>9}{'IC 95%':>18}{'verdict':>16}")
    kept = {}
    for name in sorted(groups):
        profits = groups[name]
        if len(profits) < min_n:
            print(f"{name:<26}{len(profits):>7}{'':>9}{'echantillon trop mince':>36}")
            continue
        roi, half, _ = _roi(profits)
        low, high = roi - half, roi + half
        verdict = "positif" if low > 0 else ("negatif" if high < 0 else "indiscernable")
        print(f"{name:<26}{len(profits):>7}{roi*100:>+8.1f}%"
              f"{f'[{low*100:+.1f} ; {high*100:+.1f}]':>18}{verdict:>16}")
        kept[name] = roi
    return kept


def main() -> None:
    bets = collect()
    explore = [b for b in bets if b["year"] <= EXPLORE_END]
    validate = [b for b in bets if b["year"] > EXPLORE_END]
    print(f"paris 'Elo contre le marche' : {len(bets)} "
          f"(exploration {len(explore)} jusqu'a {EXPLORE_END}, validation {len(validate)} apres)")

    roi_all, half_all, _ = _roi([b["profit"] for b in bets])
    print(f"ROI global toutes divergences confondues : {roi_all*100:+.1f}% "
          f"[{(roi_all-half_all)*100:+.1f} ; {(roi_all+half_all)*100:+.1f}]")

    def split(sample, key):
        out = defaultdict(list)
        for b in sample:
            label = key(b)
            if label:
                out[label].append(b["profit"])
        return out

    keys = {
        "ecart Elo (points)": lambda b: _band(b["gap"], ELO_BANDS),
        "cote de l'outsider": lambda b: _band(b["odds"], ODDS_BANDS),
        "surface": lambda b: b["surface"] if b["surface"] in {"Hard", "Clay", "Grass"} else None,
        "ecart Elo x cote": lambda b: (
            f"{_band(b['gap'], ELO_BANDS)} @ {_band(b['odds'], ODDS_BANDS)}"
            if _band(b["gap"], ELO_BANDS) and _band(b["odds"], ODDS_BANDS) else None
        ),
    }

    tested, promising = 0, []
    for title, key in keys.items():
        groups = split(explore, key)
        tested += len(groups)
        kept = _table(f"EXPLORATION 2001-{EXPLORE_END} — {title}", groups, min_n=150)
        promising += [(title, name) for name, roi in kept.items() if roi > 0]

    print(f"\n{'='*76}")
    print(f"segments testes en exploration : {tested}")
    print(f"segments au ROI positif en exploration : {len(promising)}")
    print("Rappel : a 24 segments, quelques ROI positifs par hasard sont l'attendu.")

    if not promising:
        print("\nAucun segment positif en exploration : rien a valider. C'est un resultat,")
        print("pas un echec -- il dit que le prix absorbe le signal partout.")
        return

    print(f"\n{'='*76}")
    print(f"VALIDATION {EXPLORE_END+1}-2025 (donnees jamais utilisees pour choisir)")
    survivors = []
    for title, name in promising:
        key = keys[title]
        profits = [b["profit"] for b in validate if key(b) == name]
        if len(profits) < 150:
            print(f"  {name:<30} n={len(profits):<6} trop mince pour conclure")
            continue
        roi, half, _ = _roi(profits)
        low = roi - half
        status = "CONFIRME" if low > 0 else "non confirme"
        print(f"  {name:<30} n={len(profits):<6} ROI {roi*100:+6.1f}% "
              f"[{low*100:+.1f} ; {(roi+half)*100:+.1f}]  {status}")
        if low > 0:
            survivors.append(name)

    print(f"\n{'='*76}")
    if survivors:
        print("Segments rentables dans les DEUX periodes : " + ", ".join(survivors))
        print("A journaliser en reel avant d'y engager quoi que ce soit : deux periodes")
        print("favorables restent deux echantillons, pas une garantie.")
    else:
        print("Aucun segment ne survit a la validation.")
        print("Lecture : le -0,0 % global n'est pas la moyenne d'un gagnant et d'un perdant,")
        print("c'est un zero a peu pres partout. Le book price l'Elo dans tous les segments")
        print("testes -- raison de plus pour porter l'effort sur les marches secondaires,")
        print("ou le prix, lui, n'est pas observable.")


if __name__ == "__main__":
    main()
