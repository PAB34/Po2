"""Quels marches jouer sur l'outsider que l'Elo prefere au marche ?

Deux volets :
  A. profil PRE-MATCH : frequence de chaque marche dans ce groupe vs population,
     avec la cote juste correspondante ;
  B. enchainements SET PAR SET : ce qui conditionne une entree en live
     (notamment : l'outsider revient-il apres avoir perdu le set 1 ?).

Aucune cote de marche secondaire ni de cote live n'existe dans les donnees :
on mesure donc des FREQUENCES, pas un edge. Un ecart de frequence est une
condition necessaire a l'opportunite, pas une preuve.
"""
from __future__ import annotations

import re
from collections import defaultdict

import pandas as pd

K, MIN_MATCHES = 32.0, 20
BAD = re.compile(r"RET|W/O|WO\b|DEF|ABD", re.I)
SET_SCORE = re.compile(r"^(\d+)-(\d+)")
COLS = ["tourney_date", "winner_name", "loser_name", "score", "true_prob_W", "true_prob_L"]


def parse(score):
    if not score or BAD.search(str(score)):
        return None
    sets = []
    for tok in str(score).split():
        m = SET_SCORE.match(tok)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a <= 20 and b <= 20:
                sets.append((a, b))
    if sum(a > b for a, b in sets) != 2 or sum(b > a for a, b in sets) not in (0, 1):
        return None
    return sets


def main():
    df = pd.read_csv("data_cache/td/features_v36.csv", usecols=COLS, low_memory=False)
    df = df.dropna(subset=["true_prob_W", "true_prob_L", "score"]).sort_values("tourney_date")

    elo, played = defaultdict(lambda: 1500.0), defaultdict(int)
    mk = defaultdict(lambda: defaultdict(int))   # groupe -> marche -> compte
    tot = defaultdict(int)
    live = defaultdict(lambda: defaultdict(int))

    for r in df.itertuples(index=False):
        w, l = r.winner_name, r.loser_name
        sets = parse(r.score)
        if sets and played[w] >= MIN_MATCHES and played[l] >= MIN_MATCHES:
            out_is_winner = r.true_prob_W < r.true_prob_L
            fav, out = (l, w) if out_is_winner else (w, l)
            grp = "divergence" if elo[out] > elo[fav] else "concordance"

            # sets vus du cote de l'outsider
            o_sets = [(b, a) if out_is_winner is False else (a, b) for a, b in sets]
            if out_is_winner:
                o_sets = [(a, b) for a, b in sets]
            else:
                o_sets = [(b, a) for a, b in sets]

            o_won_match = out_is_winner
            o_set_wins = sum(a > b for a, b in o_sets)
            games = sum(a + b for a, b in sets)
            s1 = o_sets[0][0] > o_sets[0][1]

            m = {
                "outsider gagne le match": o_won_match,
                "outsider prend >=1 set": o_set_wins >= 1,
                "outsider gagne le set 1": s1,
                "match en 3 sets": len(sets) == 3,
                "over 18.5 jeux": games > 18.5,
                "over 19.5 jeux": games > 19.5,
                "over 22.5 jeux": games > 22.5,
                "tie-break dans le match": any({a, b} == {6, 7} for a, b in sets),
                "outsider +3.5 jeux": (sum(a for a, b in o_sets) - sum(b for a, b in o_sets)) > -3.5,
                "prend un set ET over 18.5": (o_set_wins >= 1) and games > 18.5,
            }
            for g in (grp, "TOUS"):
                tot[g] += 1
                for k, v in m.items():
                    mk[g][k] += bool(v)

            # volet live : enchainements set 1 -> suite
            key = f"{grp}|set1_{'gagne' if s1 else 'perdu'}"
            live[key]["n"] += 1
            live[key]["gagne le match"] += o_won_match
            if len(o_sets) >= 2:
                live[key]["gagne le set 2"] += o_sets[1][0] > o_sets[1][1]
            live[key]["match en 3 sets"] += len(sets) == 3

        e = 1.0 / (1.0 + 10 ** ((elo[l] - elo[w]) / 400.0))
        elo[w] += K * (1 - e); elo[l] -= K * (1 - e)
        played[w] += 1; played[l] += 1

    print(f"n divergence = {tot['divergence']}   n concordance = {tot['concordance']}\n")
    print("A. PROFIL PRE-MATCH (outsider du marche, Elo le prefere)")
    print(f"{'marche':<30}{'divergence':>12}{'concordance':>13}{'ecart':>9}{'cote juste':>12}")
    rows = []
    for k in mk["divergence"]:
        pd_, pc = mk["divergence"][k] / tot["divergence"], mk["concordance"][k] / tot["concordance"]
        rows.append((pd_ - pc, k, pd_, pc))
    for d, k, pd_, pc in sorted(rows, reverse=True):
        print(f"{k:<30}{pd_*100:>11.1f}%{pc*100:>12.1f}%{d*100:>+8.1f}pt{1/pd_ if pd_ else 0:>12.2f}")

    print("\nB. ENCHAINEMENTS SET PAR SET (base d'une entree live)")
    print(f"{'situation':<40}{'n':>7}{'gagne set 2':>13}{'3 sets':>9}{'gagne match':>13}")
    for g in ("divergence", "concordance"):
        for s in ("gagne", "perdu"):
            d = live[f"{g}|set1_{s}"]
            if d["n"] < 100:
                continue
            n = d["n"]
            print(f"{g} - set 1 {s:<22}{n:>7}{d['gagne le set 2']/n*100:>12.1f}%"
                  f"{d['match en 3 sets']/n*100:>8.1f}%{d['gagne le match']/n*100:>12.1f}%")


if __name__ == "__main__":
    main()
