"""
Dynamiques d'équipe mesurables (à partir des résultats Football-Data).

Répond, chiffres à l'appui, à : qui est en forme, qui est en baisse, pourquoi.
Tout est calculé depuis les résultats récents — fiable et gratuit. Le contexte
qualitatif (blessés, retours, etc.) est dans news.py.
"""
import numpy as np
import pandas as pd

RES_PTS = {"W": 3, "D": 1, "L": 0}


def _team_matches(hist: pd.DataFrame, team: str) -> pd.DataFrame:
    """Tous les matchs d'une équipe, avec résultat de son point de vue."""
    m = hist[(hist["HomeTeam"] == team) | (hist["AwayTeam"] == team)].copy()
    m = m[m["FTR"].isin(["H", "D", "A"])].sort_values("Kickoff")
    rows = []
    for _, r in m.iterrows():
        home = r["HomeTeam"] == team
        gf = r.get("FTHG") if home else r.get("FTAG")
        ga = r.get("FTAG") if home else r.get("FTHG")
        if r["FTR"] == "D":
            res = "D"
        elif (r["FTR"] == "H") == home:
            res = "W"
        else:
            res = "L"
        rows.append({"Kickoff": r["Kickoff"], "opp": r["AwayTeam"] if home else r["HomeTeam"],
                     "home": home, "gf": gf, "ga": ga, "res": res})
    return pd.DataFrame(rows)


def _trend_label(recent_ppg, prev_ppg):
    if np.isnan(prev_ppg):
        return "récent", ""
    d = recent_ppg - prev_ppg
    if d >= 0.6:
        return "EN FORME ↑", "nette progression"
    if d >= 0.25:
        return "en hausse ↗", "progression"
    if d <= -0.6:
        return "EN BAISSE ↓", "nette baisse de régime"
    if d <= -0.25:
        return "en repli ↘", "léger repli"
    return "stable →", "régularité"


def team_dynamic(hist: pd.DataFrame, team: str, window: int = 5) -> dict:
    tm = _team_matches(hist, team)
    if len(tm) == 0:
        return {"team": team, "summary": f"{team} — pas de données récentes."}
    last = tm.tail(window)
    prev = tm.tail(window * 2).head(window)
    ppg = last["res"].map(RES_PTS).mean()
    ppg_prev = prev["res"].map(RES_PTS).mean() if len(prev) else np.nan
    gf = last["gf"].astype(float).mean()
    ga = last["ga"].astype(float).mean()
    label, why = _trend_label(ppg, ppg_prev)

    # série en cours
    streak_res = list(tm["res"])[::-1]
    cur = streak_res[0]
    n = 0
    for r in streak_res:
        if r == cur:
            n += 1
        else:
            break
    if cur == "W":
        streak = f"{n} victoire(s) de suite"
    elif cur == "L":
        streak = f"{n} défaite(s) de suite"
    else:
        streak = f"{n} nul(s) de suite"
    unbeaten = 0
    for r in streak_res:
        if r in ("W", "D"):
            unbeaten += 1
        else:
            break

    forme = "".join({"W": "V", "D": "N", "L": "D"}[r] for r in last["res"])
    reasons = []
    reasons.append(f"{int(last['res'].map(RES_PTS).sum())} pts sur {len(last)} matchs ({forme})")
    if not np.isnan(ppg_prev):
        reasons.append(f"{ppg:.1f} pts/match vs {ppg_prev:.1f} avant")
    reasons.append(f"{gf:.1f} but(s) marqué(s) / {ga:.1f} encaissé(s) par match")
    if unbeaten >= 3:
        reasons.append(f"{unbeaten} matchs sans défaite")
    elif cur == "L" and n >= 2:
        reasons.append(streak)

    summary = f"{team} — {label} : " + " ; ".join(reasons) + "."
    return {
        "team": team, "label": label, "ppg_recent": round(float(ppg), 2),
        "ppg_prev": None if np.isnan(ppg_prev) else round(float(ppg_prev), 2),
        "gf_recent": round(float(gf), 2), "ga_recent": round(float(ga), 2),
        "forme": forme, "streak": streak, "unbeaten": unbeaten,
        "why": why, "summary": summary,
    }


def journee_dynamics(hist: pd.DataFrame, matches: pd.DataFrame, window: int = 5):
    teams = pd.unique(pd.concat([matches["HomeTeam"], matches["AwayTeam"]]))
    return {t: team_dynamic(hist, t, window) for t in teams}
