"""
Chargement des données Football-Data (gratuit).

- load_upcoming() : prochains matchs de Ligue 1 + cotes (fixtures.csv).
- load_history()  : historique (pour le contrôle de fiabilité --check).
- fixtures_from_manual() : saisie manuelle si la source est vide (intersaison).
"""
import os
import numpy as np
import pandas as pd

import time
from .config import (
    LEAGUE_CODE, FOOTBALL_DATA_BASE, FOOTBALL_DATA_FIXTURES_URL,
    SEASON_START_YEARS, RAW_CACHE, RAW_CACHE_TTL_HOURS, ODDS_SOURCES,
)

ODDS_COLS = []
for _, cols in ODDS_SOURCES:
    ODDS_COLS += list(cols.values())
ODDS_COLS += ["MaxH", "MaxD", "MaxA"]  # informatif (meilleur prix)


def _season_code(y):
    return f"{y % 100:02d}{(y + 1) % 100:02d}"


def _read(url):
    try:
        df = pd.read_csv(url, encoding="latin1", on_bad_lines="skip")
        return df if {"HomeTeam", "AwayTeam"}.issubset(df.columns) else None
    except Exception:
        return None


def _kickoff(df):
    date = pd.to_datetime(df.get("Date"), dayfirst=True, errors="coerce")
    time = pd.Series(df.get("Time", "00:00"), index=df.index).fillna("00:00").astype(str).str.strip()
    time = time.where(time.str.match(r"^\d{1,2}:\d{2}$"), "00:00")
    k = pd.to_datetime(date.dt.strftime("%Y-%m-%d") + " " + time, errors="coerce")
    return k.fillna(date)


def _l1_teams_from_history():
    """Équipes ayant joué en L1 récemment (pour filtrer fixtures.csv sans colonne Div fiable)."""
    try:
        hist = load_history()
        recent = hist[hist["Season"].astype(str).isin(["2425", "2526"])]
        return set(recent["HomeTeam"]) | set(recent["AwayTeam"])
    except Exception:
        return set()


def _cache_fresh():
    if not os.path.exists(RAW_CACHE):
        return False
    age_h = (time.time() - os.path.getmtime(RAW_CACHE)) / 3600.0
    return age_h < RAW_CACHE_TTL_HOURS



def _empty_history() -> pd.DataFrame:
    return pd.DataFrame(columns=["Season", "Kickoff", "HomeTeam", "AwayTeam", "FTR", "FTHG", "FTAG"])


def _history_columns(raw: pd.DataFrame) -> list[str]:
    base = ["Season", "Kickoff", "HomeTeam", "AwayTeam", "FTR", "FTHG", "FTAG"]
    return [c for c in base if c in raw.columns] + [c for c in ODDS_COLS if c in raw.columns]


def _load_history_cache() -> pd.DataFrame | None:
    if not os.path.exists(RAW_CACHE):
        return None
    try:
        raw = pd.read_pickle(RAW_CACHE)
        required = {"Season", "Kickoff", "HomeTeam", "AwayTeam"}
        if not required.issubset(raw.columns):
            return None
        return raw[_history_columns(raw)].copy()
    except Exception:
        return None


def load_history(use_cache=True) -> pd.DataFrame:
    if use_cache and _cache_fresh():
        cached = _load_history_cache()
        out = cached if cached is not None else _empty_history()
    else:
        frames = []
        for y in SEASON_START_YEARS:
            df = _read(f"{FOOTBALL_DATA_BASE}/{_season_code(y)}/{LEAGUE_CODE}.csv")
            if df is None or not len(df):
                continue
            df = df[df.get("Div", LEAGUE_CODE).astype(str).str.upper().eq(LEAGUE_CODE)] if "Div" in df else df
            df["Season"] = _season_code(y)
            df["Kickoff"] = _kickoff(df)
            for c in ODDS_COLS + ["FTHG", "FTAG"]:
                df[c] = pd.to_numeric(df.get(c), errors="coerce")
            frames.append(df[["Season", "Kickoff", "HomeTeam", "AwayTeam", "FTR", "FTHG", "FTAG"] + ODDS_COLS])
        if frames:
            out = pd.concat(frames, ignore_index=True)
            try:
                out.to_pickle(RAW_CACHE)  # met a jour le cache
            except Exception:
                pass
        else:
            out = _load_history_cache() if use_cache else None
            if out is None:
                out = _empty_history()
    for c in ODDS_COLS:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=["HomeTeam", "AwayTeam", "Kickoff"])
    return out.sort_values("Kickoff").reset_index(drop=True)

def load_upcoming() -> pd.DataFrame:
    """Prochains matchs de Ligue 1 avec cotes, depuis fixtures.csv."""
    fx = _read(FOOTBALL_DATA_FIXTURES_URL)
    if fx is None or not len(fx):
        return pd.DataFrame()
    fx["Kickoff"] = _kickoff(fx)
    for c in ODDS_COLS:
        fx[c] = pd.to_numeric(fx.get(c), errors="coerce")
    # Filtre Ligue 1 : par colonne Div si présente, sinon par appartenance d'équipe.
    if "Div" in fx.columns and fx["Div"].notna().any():
        f1 = fx[fx["Div"].astype(str).str.upper().eq(LEAGUE_CODE)].copy()
    else:
        teams = _l1_teams_from_history()
        f1 = fx[fx["HomeTeam"].isin(teams) & fx["AwayTeam"].isin(teams)].copy() if teams else fx.iloc[0:0].copy()
    f1["FTR"] = np.nan
    keep = ["Kickoff", "HomeTeam", "AwayTeam", "FTR"] + [c for c in ODDS_COLS if c in f1.columns]
    return f1[keep].dropna(subset=["HomeTeam", "AwayTeam", "Kickoff"]).sort_values("Kickoff").reset_index(drop=True)


def fixtures_from_manual(rows) -> pd.DataFrame:
    """Saisie manuelle. Chaque ligne : Date, Time, HomeTeam, AwayTeam, et au moins
    un jeu de cotes parmi PS*/B365*/Avg*. Ex. PSH/PSD/PSA ou AvgH/AvgD/AvgA."""
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["Kickoff"] = pd.to_datetime(df["Date"].astype(str) + " " + df.get("Time", "00:00").astype(str), errors="coerce")
    df["FTR"] = np.nan
    for c in ODDS_COLS:
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    keep = ["Kickoff", "HomeTeam", "AwayTeam", "FTR"] + ODDS_COLS
    return df[keep]




