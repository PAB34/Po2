"""L'Elo qui contredit LE MARCHE (et non le classement) rapporte-t-il ?

Le test precedent opposait l'Elo au classement, faute de cotes. features_v36.csv
en contient : on peut donc mesurer l'edge reel, en euros, contre le prix du
bookmaker -- le seul juge qui compte.

Elo recalcule point-in-time (aucune fuite : mis a jour APRES lecture du match).
Rendement = mise 1 unite sur l'outsider du marche quand l'Elo le prefere.
"""
from __future__ import annotations

import re
from collections import defaultdict

import pandas as pd

K = 32.0
MIN_MATCHES = 20
BAD = re.compile(r"RET|W/O|WO\b|DEF|ABD", re.I)
SET_SCORE = re.compile(r"^(\d+)-(\d+)")

COLS = ["tourney_date", "winner_name", "loser_name", "score", "surface",
        "synth_odds_W", "synth_odds_L", "true_prob_W", "true_prob_L"]


def took_a_set(score: str, outsider_won: bool) -> bool | None:
    if not score or BAD.search(str(score)):
        return None
    sets = []
    for tok in str(score).split():
        m = SET_SCORE.match(tok)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a <= 20 and b <= 20:
                sets.append((a, b))
    w = sum(a > b for a, b in sets)
    l = sum(b > a for a, b in sets)
    if w != 2 or l not in (0, 1):
        return None
    return True if outsider_won else (l == 1)


def main() -> None:
    df = pd.read_csv("data_cache/td/features_v36.csv", usecols=COLS, low_memory=False)
    df = df.dropna(subset=["synth_odds_W", "synth_odds_L", "true_prob_W", "winner_name", "loser_name"])
    df = df.sort_values("tourney_date")
    print(f"matchs avec cotes : {len(df):,}".replace(",", " "))

    elo: dict[str, float] = defaultdict(lambda: 1500.0)
    played: dict[str, int] = defaultdict(int)
    # groupe -> [n, paris gagnes, profit, prend un set]
    st = defaultdict(lambda: [0, 0, 0.0, 0])
    per = defaultdict(lambda: [0, 0.0])

    for row in df.itertuples(index=False):
        w, l = row.winner_name, row.loser_name
        ready = played[w] >= MIN_MATCHES and played[l] >= MIN_MATCHES
        if ready and row.true_prob_W and row.true_prob_L:
            # favori du MARCHE = plus forte proba devigottee
            if row.true_prob_W >= row.true_prob_L:
                fav, out = w, l
                out_odds, out_won = row.synth_odds_L, False
            else:
                fav, out = l, w
                out_odds, out_won = row.synth_odds_W, True
            if elo[out] > elo[fav]:          # l'Elo contredit le marche
                grp = "Elo CONTRE le marche"
            else:
                grp = "Elo d'accord avec le marche"
            profit = (out_odds - 1.0) if out_won else -1.0
            took = took_a_set(row.score, out_won)
            for key in (grp, "TOUS (parier l'outsider)"):
                s = st[key]
                s[0] += 1
                s[1] += out_won
                s[2] += profit
                if took:
                    s[3] += 1
            if grp == "Elo CONTRE le marche":
                y = str(row.tourney_date)[:4]
                bucket = "2001-2012" if y < "2013" else ("2013-2019" if y < "2020" else "2020-2025")
                p = per[bucket]
                p[0] += 1
                p[1] += profit

        e = 1.0 / (1.0 + 10 ** ((elo[l] - elo[w]) / 400.0))
        elo[w] += K * (1 - e)
        elo[l] -= K * (1 - e)
        played[w] += 1
        played[l] += 1

    print(f"\n{'groupe':<30}{'n':>8}{'gagnes':>9}{'ROI':>9}{'prend >=1 set':>15}")
    for key in ("TOUS (parier l'outsider)", "Elo d'accord avec le marche", "Elo CONTRE le marche"):
        s = st.get(key)
        if not s or not s[0]:
            continue
        print(f"{key:<30}{s[0]:>8}{s[1]/s[0]*100:>8.1f}%{s[2]/s[0]*100:>8.1f}%{s[3]/s[0]*100:>14.1f}%")

    print("\nstabilite du ROI quand l'Elo contredit le marche :")
    for k in ("2001-2012", "2013-2019", "2020-2025"):
        if k in per and per[k][0] > 100:
            print(f"  {k}  n={per[k][0]:>6}   ROI={per[k][1]/per[k][0]*100:+6.1f}%")


if __name__ == "__main__":
    main()
