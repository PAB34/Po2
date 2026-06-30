"""
Service Ligue 1 : assemble le payload de la prochaine journée
(probabilités + dynamiques + blessés) et expose l'actu par équipe.
Cache mémoire pour rester réactif.
"""
import time
import datetime as dt

import numpy as np
import pandas as pd

from .config import JOURNEE_GAP_DAYS
from .data import load_upcoming, load_history
from .probabilities import compute_probabilities
from .dynamics import team_dynamic
from .injuries_tm import injuries_by_team, get_status
from .news import get_team_news, get_league_news
from . import stakes as stakes_mod

_CACHE = {"journee": None, "ts": 0}
CACHE_TTL = 1800  # 30 min
_HIST = None


def _hist():
    global _HIST
    if _HIST is None:
        _HIST = load_history()
    return _HIST


def _first_journee(df):
    df = df.sort_values("Kickoff").reset_index(drop=True)
    if len(df) == 0:
        return df
    start = df["Kickoff"].iloc[0]
    return df[df["Kickoff"] <= start + pd.Timedelta(days=JOURNEE_GAP_DAYS)].copy()


def _select_journee():
    m = load_upcoming()
    if len(m):
        return _first_journee(m), f"Football-Data fixtures · {m['Kickoff'].min().date()}"
    h = _hist()
    last = sorted(h["Season"].astype(str).unique())[-1]
    sd = h[h["Season"].astype(str) == last].sort_values("Kickoff")
    end = sd["Kickoff"].iloc[-1]
    return sd[sd["Kickoff"] >= end - pd.Timedelta(days=JOURNEE_GAP_DAYS)].copy(), \
        f"Démo intersaison · dernière journée {last}"


def _pct(x):
    return None if (x is None or not np.isfinite(x)) else round(float(x) * 100, 1)


def _team_block(team, inj, standings):
    d = team_dynamic(_hist(), team)
    bl = inj.get(team, []) if isinstance(inj, dict) else []
    st = stakes_mod.team_stakes(standings, team)
    return {
        "team": team, "label": d.get("label", ""), "forme": d.get("forme", ""),
        "ppg_recent": d.get("ppg_recent"), "gf_recent": d.get("gf_recent"),
        "ga_recent": d.get("ga_recent"), "summary": d.get("summary", ""),
        "injuries": bl, "injuries_count": len(bl),
        "stakes": {
            "rank": st.get("rank"), "n_teams": st.get("n_teams"), "points": st.get("points"),
            "games_remaining": st.get("games_remaining"), "enjeu_label": st.get("enjeu_label", ""),
            "level": st.get("level", "Indéterminé"), "summary": st.get("summary", ""),
        },
    }


def build_journee(force=False):
    if (not force) and _CACHE["journee"] and (time.time() - _CACHE["ts"]) < CACHE_TTL:
        return _CACHE["journee"]
    matches, src = _select_journee()
    scored = compute_probabilities(matches)
    inj = injuries_by_team()
    season = stakes_mod.current_season(_hist())
    standings = stakes_mod.compute_standings(_hist(), season)
    out = []
    for _, r in scored.iterrows():
        home_block = _team_block(r["HomeTeam"], inj, standings)
        away_block = _team_block(r["AwayTeam"], inj, standings)
        home_st = home_block["stakes"]
        away_st = away_block["stakes"]
        stakes_note = stakes_mod.match_stakes_note(
            {**home_st, "team": r["HomeTeam"]}, {**away_st, "team": r["AwayTeam"]}
        )
        out.append({
            "kickoff": str(r["Kickoff"]), "home": r["HomeTeam"], "away": r["AwayTeam"],
            "p_home": _pct(r["P_home"]), "p_draw": _pct(r["P_draw"]), "p_away": _pct(r["P_away"]),
            "pick": r["pick"], "pick_outcome": r["pick_outcome"],
            "pick_proba": _pct(r["pick_proba"]), "confidence": r["confidence"],
            "home_block": home_block,
            "away_block": away_block,
            "stakes_note": stakes_note,
        })
    health = get_status()
    payload = {
        "source": src,
        "updated": dt.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "odds_source": scored["source"].dropna().unique().tolist() if len(scored) else [],
        "health": {"ok": health.get("ok", True), "issues": health.get("issues", []),
                   "count": health.get("count")},
        "matches": out,
    }
    _CACHE["journee"] = payload
    _CACHE["ts"] = time.time()
    return payload


def team_news(team):
    res = get_team_news(team, max_items=6)
    items = [{
        "title": it["title"], "source": it["source"],
        "date": it["date"].strftime("%d/%m") if it.get("date") else "",
        "link": it["link"], "tags": it["tags"],
    } for it in res.get("items", [])]
    return {"team": team, "error": res.get("error"), "items": items}


_ACTU = {"data": None, "ts": 0}
ACTU_TTL = 900  # 15 min


def league_actu():
    if _ACTU["data"] and (time.time() - _ACTU["ts"]) < ACTU_TTL:
        return _ACTU["data"]
    res = get_league_news(max_items=15)
    items = [{
        "title": it["title"], "source": it["source"],
        "date": it["date"].strftime("%d/%m") if it.get("date") else "",
        "link": it["link"], "tags": it["tags"],
    } for it in res.get("items", [])]
    out = {"error": res.get("error"), "items": items}
    _ACTU["data"] = out
    _ACTU["ts"] = time.time()
    return out


def health():
    return get_status()
