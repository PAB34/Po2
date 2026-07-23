"""Backtest : la divergence Elo vs classement predit-elle qu'un outsider tient ?

Question posee : "je prends un ticket quand Elo et forme contredisent le favori".
On mesure donc, sur l'historique, si l'outsider (au sens classement) se comporte
mieux quand l'Elo et/ou la forme le designent malgre tout comme le meilleur.

Elo recalcule chronologiquement (K=32, init 1500). Aucune cote disponible dans
l'historique : le "favori du marche" est approche par le mieux classe, ce que
fait deja tennis_calibration.
"""
from __future__ import annotations

import csv
import glob
import re
from collections import defaultdict, deque

SET_SCORE = re.compile(r"^(\d+)-(\d+)")
BAD = re.compile(r"RET|W/O|WO\b|DEF|ABD", re.I)
K = 32.0
MIN_MATCHES = 20      # Elo considere comme etabli
FORM_WINDOW = 10


def parse_sets(score: str):
    if not score or BAD.search(score):
        return None
    sets = []
    for tok in score.split():
        m = SET_SCORE.match(tok)
        if not m:
            continue
        a, b = int(m.group(1)), int(m.group(2))
        if a > 20 or b > 20:
            continue
        sets.append((a, b))
    w = sum(a > b for a, b in sets)
    l = sum(b > a for a, b in sets)
    if w != 2 or l not in (0, 1):
        return None
    return sets, l, sum(a + b for a, b in sets)


def load(patterns):
    rows = []
    for pat in patterns:
        for path in glob.glob(pat):
            with open(path, encoding="utf-8-sig", newline="") as f:
                for r in csv.DictReader(f):
                    rows.append(r)
    rows.sort(key=lambda r: (r.get("tourney_date") or "", r.get("match_num") or ""))
    return rows


def run(rows, label):
    elo = defaultdict(lambda: 1500.0)
    played = defaultdict(int)
    form = defaultdict(lambda: deque(maxlen=FORM_WINDOW))
    # groupe -> [n, outsider_gagne, outsider_prend_un_set]
    stats = defaultdict(lambda: [0, 0, 0, 0])   # n, gagne, prend 1 set, ticket(set+over18.5)

    for r in rows:
        w, l = r.get("winner_name"), r.get("loser_name")
        if not w or not l:
            continue
        parsed = parse_sets(r.get("score", ""))
        try:
            wr, lr = int(r["winner_rank"]), int(r["loser_rank"])
        except (ValueError, TypeError, KeyError):
            wr = lr = None

        ready = played[w] >= MIN_MATCHES and played[l] >= MIN_MATCHES
        if ready and parsed and wr and lr and wr != lr:
            sets, loser_sets, total_games = parsed
            # favori/outsider au sens CLASSEMENT
            fav, out = (w, l) if wr < lr else (l, w)
            out_won = (out == w)
            out_took_set = out_won or loser_sets == 1

            elo_fav = elo[fav] >= elo[out]
            f_fav = sum(form[fav]) / len(form[fav]) if form[fav] else 0.5
            f_out = sum(form[out]) / len(form[out]) if form[out] else 0.5
            form_contra = f_out > f_fav

            if elo_fav and not form_contra:
                key = "tout concorde (Elo + forme avec le favori)"
            elif not elo_fav and form_contra:
                key = "DIVERGENCE FORTE (Elo + forme contre le favori)"
            elif not elo_fav:
                key = "Elo seul contre le favori"
            else:
                key = "forme seule contre le favori"

            for k in (key, "TOUS"):
                s = stats[k]
                s[0] += 1
                s[1] += out_won
                s[2] += out_took_set
                s[3] += (out_took_set and total_games > 18.5)

        # mise a jour Elo + forme
        ew = 1.0 / (1.0 + 10 ** ((elo[l] - elo[w]) / 400.0))
        elo[w] += K * (1 - ew)
        elo[l] -= K * (1 - ew)
        played[w] += 1
        played[l] += 1
        form[w].append(1)
        form[l].append(0)

    print(f"\n===== {label} =====")
    print(f"{'groupe':<46}{'n':>7}{'prend >=1 set':>15}{'ticket set+o18.5':>18}{'cote juste':>12}")
    order = ["TOUS", "tout concorde (Elo + forme avec le favori)", "forme seule contre le favori",
             "Elo seul contre le favori", "DIVERGENCE FORTE (Elo + forme contre le favori)"]
    base = stats["TOUS"]
    for k in order:
        s = stats.get(k)
        if not s or s[0] < 100:
            continue
        took, tick = s[2] / s[0], s[3] / s[0]
        mark = ""
        if k != "TOUS" and base[0]:
            mark = f"   ({(tick - base[3]/base[0])*100:+.1f} pt)"
        print(f"{k:<46}{s[0]:>7}{took*100:>14.1f}%{tick*100:>17.1f}%{1/tick if tick else 0:>12.2f}{mark}")
    return stats


if __name__ == "__main__":
    base = "PRONO/backend/app/tennis_data"
    run(load([f"{base}/tml/*.csv"]), "ATP")
    run(load([f"{base}/tml_wta/*.csv"]), "WTA")
