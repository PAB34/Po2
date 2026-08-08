"""Actualisation de l'Elo ATP depuis la source live TennisMyLife.

Le depot GitHub TML est desormais historique. En production, on remplace le CSV
ATP de l'annee courante par le fichier publie sur stats.tennismylife.org, mis en
cache 24 h. Les fichiers embarques restent le repli hors ligne.

L'Elo est reconstruit chronologiquement avec la convention deja utilisee par les
backtests PRONO : init 1500, K=32, echelle 400. On calcule un Elo global et un
Elo par surface puis on les injecte dans les index de TennisCoach sans modifier
les autres indicateurs (forme, service, contexte, calibration marche).
"""
from __future__ import annotations

import os
import time
import urllib.request as urlrequest
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from app.tennis_coach import norm, stats_keys

TML_YEAR_URL = "https://stats.tennismylife.org/data/{year}.csv"
TML_TTL = 24 * 3600
ELO_INITIAL = 1500.0
ELO_K = 32.0
ELO_UPDATE_SCALE = 400.0
SUPPORTED_SURFACES = ("hard", "clay", "grass")
REQUIRED_COLUMNS = {"tourney_date", "winner_name", "loser_name", "surface"}
READ_COLUMNS = REQUIRED_COLUMNS | {"match_num"}
UA = "Mozilla/5.0 (compatible; PRONO-private-dashboard/1.0)"


def _expected(a: float, b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((b - a) / ELO_UPDATE_SCALE))


def _surface(value: Any) -> str | None:
    label = str(value or "").strip().lower()
    return label if label in SUPPORTED_SURFACES else None


def _date_label(value: int) -> str | None:
    text = str(int(value or 0))
    if len(text) != 8:
        return None
    try:
        return datetime.strptime(text, "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def _valid_csv(path: Path, expected_year: int | None = None) -> bool:
    try:
        probe = pd.read_csv(path, usecols=lambda column: column in READ_COLUMNS, dtype=str)
    except (OSError, ValueError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return False
    if probe.empty or not REQUIRED_COLUMNS.issubset(probe.columns):
        return False
    if expected_year is None:
        return True
    years = pd.to_numeric(probe["tourney_date"], errors="coerce").dropna().astype("int64").astype(str).str[:4]
    return bool(len(years) and (years == str(expected_year)).any())


def _runtime_cache(dataset_dir: Path, year: int) -> Path:
    data_root = os.environ.get("PRONO_DATA_DIR")
    if data_root:
        root = Path(data_root) / "tennis" / "tml_live"
    else:
        root = Path(dataset_dir) / "_runtime" / "tennis" / "tml_live"
    return root / f"{year}.csv"


def _download_live_year(target: Path, year: int) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    request = urlrequest.Request(TML_YEAR_URL.format(year=year), headers={"User-Agent": UA})
    try:
        with urlrequest.urlopen(request, timeout=20) as response, tmp.open("wb") as output:
            output.write(response.read())
        if not _valid_csv(tmp, expected_year=year):
            raise ValueError("TennisMyLife CSV invalide ou schema inattendu")
        os.replace(tmp, target)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
    return target


def current_year_file(dataset_dir: Path, year: int | None = None, now: float | None = None) -> tuple[Path, str]:
    """Retourne le meilleur CSV de l'annee courante et sa provenance.

    Le reseau n'est utilise que lorsque PRONO_DATA_DIR est present, donc les tests
    et usages locaux restent deterministes. Un cache valide, meme ancien, est
    prefere au CSV embarque si la source live devient momentanement indisponible.
    """
    year = int(year or date.today().year)
    now = float(now if now is not None else time.time())
    packaged = Path(dataset_dir) / "tml" / f"{year}.csv"
    cache = _runtime_cache(Path(dataset_dir), year)

    if cache.exists() and _valid_csv(cache, expected_year=year):
        if now - cache.stat().st_mtime < TML_TTL:
            return cache, "TennisMyLife live (cache <24h)"

    if os.environ.get("PRONO_DATA_DIR"):
        try:
            return _download_live_year(cache, year), "TennisMyLife live"
        except Exception:
            if cache.exists() and _valid_csv(cache, expected_year=year):
                return cache, "TennisMyLife live (cache de secours)"

    return packaged, "TennisMyLife embarque"


def history_paths(dataset_dir: Path, current_file: Path, year: int | None = None) -> list[Path]:
    """Historique ATP embarque, avec remplacement de l'annee courante."""
    year = int(year or date.today().year)
    directory = Path(dataset_dir) / "tml"
    paths = [path for path in directory.glob("*.csv") if path.name != f"{year}.csv"]
    if current_file.exists():
        paths.append(current_file)
    elif (directory / f"{year}.csv").exists():
        paths.append(directory / f"{year}.csv")
    return sorted(paths, key=lambda path: path.name)


def _load_matches(paths: Iterable[Path]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in paths:
        try:
            frame = pd.read_csv(path, usecols=lambda column: column in READ_COLUMNS, dtype=str)
        except (OSError, ValueError, pd.errors.ParserError, pd.errors.EmptyDataError):
            continue
        if frame.empty or not REQUIRED_COLUMNS.issubset(frame.columns):
            continue
        if "match_num" not in frame:
            frame["match_num"] = "0"
        frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=sorted(READ_COLUMNS))
    matches = pd.concat(frames, ignore_index=True)
    matches["_date"] = pd.to_numeric(matches["tourney_date"], errors="coerce").fillna(0).astype("int64")
    matches["_match"] = pd.to_numeric(matches["match_num"], errors="coerce").fillna(0).astype("int64")
    return matches.sort_values(["_date", "_match"], kind="stable")


def _find_or_create_row(coach: Any, player: str) -> dict[str, Any]:
    player_key = norm(player)
    exact = coach._stats_exact.setdefault("ATP", {})
    bucket = coach.stats.setdefault("ATP", {})
    ambiguous = coach._ambiguous_stats_keys.setdefault("ATP", set())

    row = exact.get(player_key)
    if row is None:
        for alias in stats_keys(player):
            if alias in ambiguous:
                continue
            candidate = bucket.get(alias)
            if candidate is not None:
                row = candidate
                break
    if row is None:
        row = {"player": player}
    row.setdefault("player", player)
    exact[player_key] = row

    for alias in stats_keys(player):
        existing = bucket.get(alias)
        if existing is not None and existing is not row and norm(existing.get("player")) != player_key:
            ambiguous.add(alias)
            continue
        bucket[alias] = row
    return row


def rebuild_atp_elo(coach: Any, paths: Iterable[Path], source: str = "TennisMyLife") -> dict[str, Any]:
    """Recalcule puis injecte les Elo ATP dans un TennisCoach existant."""
    matches = _load_matches(paths)
    if matches.empty:
        return {"source": source, "players": 0, "matches": 0, "latest_date": None, "status": "no_data"}

    global_elo: defaultdict[str, float] = defaultdict(lambda: ELO_INITIAL)
    surface_elo = {surface: defaultdict(lambda: ELO_INITIAL) for surface in SUPPORTED_SURFACES}
    counts: defaultdict[str, int] = defaultdict(int)
    latest: defaultdict[str, int] = defaultdict(int)
    names: dict[str, str] = {}

    for record in matches.to_dict("records"):
        winner = str(record.get("winner_name") or "").strip()
        loser = str(record.get("loser_name") or "").strip()
        wk, lk = norm(winner), norm(loser)
        if not wk or not lk or wk == lk:
            continue
        names[wk], names[lk] = winner, loser
        played_on = int(record.get("_date") or 0)

        win_expectation = _expected(global_elo[wk], global_elo[lk])
        delta = ELO_K * (1.0 - win_expectation)
        global_elo[wk] += delta
        global_elo[lk] -= delta

        surface = _surface(record.get("surface"))
        if surface:
            ratings = surface_elo[surface]
            surface_expectation = _expected(ratings[wk], ratings[lk])
            surface_delta = ELO_K * (1.0 - surface_expectation)
            ratings[wk] += surface_delta
            ratings[lk] -= surface_delta

        counts[wk] += 1
        counts[lk] += 1
        latest[wk] = max(latest[wk], played_on)
        latest[lk] = max(latest[lk], played_on)

    for player_key, rating in global_elo.items():
        player = names.get(player_key, player_key)
        row = _find_or_create_row(coach, player)
        row["elo_global"] = round(rating)
        for surface in SUPPORTED_SURFACES:
            value = surface_elo[surface].get(player_key)
            if value is not None:
                row[f"elo_{surface}"] = round(value)
        row["n_matchs_total"] = counts[player_key]
        row["etabli"] = counts[player_key] >= 20
        last_date = _date_label(latest[player_key])
        if last_date:
            row["derniere_date"] = last_date
        row["elo_source"] = source

    latest_date = _date_label(int(matches["_date"].max()))
    return {
        "source": source,
        "players": len(global_elo),
        "matches": int(len(matches)),
        "latest_date": latest_date,
        "status": "ok",
    }


def refresh_coach_if_needed(coach: Any, force: bool = False, now: float | None = None) -> dict[str, Any]:
    """Actualise l'Elo ATP d'un coach au plus une fois par 24 h."""
    now = float(now if now is not None else time.time())
    refreshed_at = float(getattr(coach, "_atp_elo_refreshed_at", 0.0) or 0.0)
    previous = getattr(coach, "_atp_elo_refresh_summary", None)
    if not force and previous and now - refreshed_at < TML_TTL:
        return previous

    year = date.today().year
    current_file, source = current_year_file(Path(coach.dataset_dir), year=year, now=now)
    summary = rebuild_atp_elo(coach, history_paths(Path(coach.dataset_dir), current_file, year=year), source=source)
    summary["refreshed_at"] = datetime.fromtimestamp(now, tz=timezone.utc).isoformat()
    coach._atp_elo_refreshed_at = now
    coach._atp_elo_refresh_summary = summary
    return summary
