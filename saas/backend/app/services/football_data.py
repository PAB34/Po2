from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import requests

from app.core.config import settings
from app.services.pronostics import _normalize_team


FOOTBALL_DATA_UNAVAILABLE_FIELDS = {
    "fifa_rank": "football-data.org ne fournit pas le classement FIFA officiel.",
    "fifa_points": "football-data.org ne fournit pas les points FIFA.",
    "elo": "football-data.org ne fournit pas d'Elo.",
    "xg_xa": "football-data.org ne fournit pas de xG/xA.",
    "player_rating": "football-data.org ne fournit pas de note moyenne joueur.",
    "injury_status": "football-data.org ne documente pas d'endpoint blessures.",
    "player_confidence": "Variable subjective non exposee par football-data.org.",
    "probable_lineup": "Les lineups sont des donnees de match, pas une prediction future fiable.",
    "travel_fatigue": "A calculer hors API depuis les lieux de match.",
    "diaspora_public": "Non expose par football-data.org.",
    "weather": "Non expose par football-data.org.",
    "odds": "football-data.org ne documente pas de cotes bookmakers.",
}


@dataclass
class FootballDataClient:
    token: str
    base_url: str = settings.football_data_base_url
    timeout: int = 30
    # Tier gratuit football-data.org = 10 req/min. On espace les appels pour
    # rester sous la limite (0 = pas de throttle, ex. tests).
    min_interval_seconds: float = 0.0
    _last_call: float = field(default=0.0, init=False, repr=False)

    def _throttle(self) -> None:
        if self.min_interval_seconds <= 0:
            return
        elapsed = time.monotonic() - self._last_call
        wait = self.min_interval_seconds - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._throttle()
        response = requests.get(
            f"{self.base_url.rstrip('/')}/{path.lstrip('/')}",
            params=params,
            headers={"X-Auth-Token": self.token},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}


def _retry_after_seconds(response: requests.Response | None) -> int:
    """Combien de secondes attendre apres un 429 football-data.org."""
    if response is None:
        return 10
    header = response.headers.get("Retry-After")
    if header and header.isdigit():
        return int(header)
    try:
        match = re.search(r"Wait (\d+) second", response.text)
    except Exception:  # pragma: no cover - defensif
        match = None
    return int(match.group(1)) + 1 if match else 10


def _safe_get(
    api: FootballDataClient,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    errors: list[dict[str, Any]],
    max_retries: int = 3,
) -> dict[str, Any]:
    """Appelle football-data.org sans jamais propager une erreur HTTP.

    Sur 429 (quota tier gratuit = 10 req/min), attend le delai indique puis
    retente (``max_retries`` fois). Toute autre erreur (403 tier, 404, timeout,
    JSON invalide) est enregistree dans ``errors`` et renvoie ``{}`` pour que le
    feed reste exploitable au lieu de remonter un 500 opaque.
    """
    for attempt in range(max_retries + 1):
        try:
            return api.get(path, params=params)
        except requests.HTTPError as exc:
            response = exc.response
            status_code = response.status_code if response is not None else None
            if status_code == 429 and attempt < max_retries:
                time.sleep(_retry_after_seconds(response))
                continue
            body = ""
            if response is not None:
                try:
                    body = response.text[:300]
                except Exception:  # pragma: no cover - defensif
                    body = ""
            errors.append(
                {
                    "endpoint": path,
                    "params": params,
                    "status_code": status_code,
                    "error": str(exc),
                    "body": body,
                }
            )
            return {}
        except requests.RequestException as exc:
            errors.append(
                {
                    "endpoint": path,
                    "params": params,
                    "status_code": None,
                    "error": str(exc),
                    "body": "",
                }
            )
            return {}
        except ValueError as exc:  # JSON invalide
            errors.append(
                {
                    "endpoint": path,
                    "params": params,
                    "status_code": None,
                    "error": f"reponse non-JSON: {exc}",
                    "body": "",
                }
            )
            return {}
    return {}


def build_pronostics_model_feed(
    *,
    include_player_matches: bool = False,
    recent_team_matches_limit: int = 10,
    recent_player_matches_limit: int = 10,
    date_from: date | None = None,
    client: FootballDataClient | None = None,
) -> dict[str, Any]:
    if not settings.football_data_token and client is None:
        return _empty_feed(configured=False)

    api = client or FootballDataClient(token=settings.football_data_token)
    date_to = date.today()
    # 730 jours : capte le dernier grand tournoi international (ex. EURO 2024),
    # seule source de forme reelle exposee par le tier gratuit pour les nations.
    date_from = date_from or (date_to - timedelta(days=730))

    feed = _empty_feed(configured=True)
    errors: list[dict[str, Any]] = feed["errors"]
    teams_payload = _safe_get(
        api,
        f"competitions/{settings.football_data_competition}/teams",
        params={"season": settings.football_data_season},
        errors=errors,
    )
    competition_teams = teams_payload.get("teams") or []
    feed["coverage"]["competition_teams"] = _status_block(
        retrieved=bool(competition_teams),
        count=len(competition_teams),
        endpoint=f"/v4/competitions/{settings.football_data_competition}/teams",
    )

    for team_ref in competition_teams:
        team = _build_team_feed_row(team_ref)
        team_id = team["football_data_team_id"]
        team_detail: dict[str, Any] = {}
        if team_id is not None:
            team_detail = _safe_get(api, f"teams/{team_id}", errors=errors)
            _merge_team_detail(team, team_detail)
            _append_players(feed, team, team_detail)
            team_matches = _safe_get(
                api,
                f"teams/{team_id}/matches",
                params={
                    "status": "FINISHED",
                    "dateFrom": date_from.isoformat(),
                    "dateTo": date_to.isoformat(),
                },
                errors=errors,
            )
            team["recent_form"] = _summarize_team_matches(
                team, team_matches, limit=recent_team_matches_limit
            )

        feed["teams"].append(team)

    if include_player_matches:
        _enrich_players_with_recent_matches(
            feed,
            api,
            recent_player_matches_limit=recent_player_matches_limit,
            date_from=date_from,
            date_to=date_to,
            errors=errors,
        )

    scorers_payload = _safe_get(
        api,
        f"competitions/{settings.football_data_competition}/scorers",
        params={"season": settings.football_data_season, "limit": 100},
        errors=errors,
    )
    feed["competition_scorers"] = _build_scorers(scorers_payload)
    feed["coverage"]["competition_scorers"] = _status_block(
        retrieved=bool(feed["competition_scorers"]),
        count=len(feed["competition_scorers"]),
        endpoint=f"/v4/competitions/{settings.football_data_competition}/scorers",
    )
    feed["summary"] = {
        "teams": len(feed["teams"]),
        "players": len(feed["players"]),
        "players_with_recent_match_stats": sum(1 for player in feed["players"] if player.get("recent_stats")),
        "competition_scorers": len(feed["competition_scorers"]),
    }
    return feed


def _empty_feed(*, configured: bool) -> dict[str, Any]:
    return {
        "configured": configured,
        "source": "football-data.org",
        "competition": settings.football_data_competition,
        "season": settings.football_data_season,
        "summary": {"teams": 0, "players": 0, "players_with_recent_match_stats": 0, "competition_scorers": 0},
        "coverage": {
            "competition_teams": _status_block(False, 0, "/v4/competitions/{competition}/teams"),
            "competition_scorers": _status_block(False, 0, "/v4/competitions/{competition}/scorers"),
            "player_recent_matches": _status_block(False, 0, "/v4/persons/{id}/matches"),
        },
        "teams": [],
        "players": [],
        "competition_scorers": [],
        "errors": [],
        "unavailable_fields": FOOTBALL_DATA_UNAVAILABLE_FIELDS,
    }


def _status_block(retrieved: bool, count: int, endpoint: str) -> dict[str, Any]:
    return {
        "status": "retrieved" if retrieved else "missing",
        "count": count,
        "endpoint": endpoint,
    }


def _build_team_feed_row(team: dict[str, Any]) -> dict[str, Any]:
    area = team.get("area") or {}
    return {
        "local_team_key": _normalize_team(_api_team_name(team)),
        "football_data_team_id": team.get("id"),
        "official_name": team.get("name"),
        "short_name": team.get("shortName"),
        "tla": team.get("tla"),
        "area_name": area.get("name"),
        "area_code": area.get("code"),
        "crest": team.get("crest"),
        "coach": _coach_row(team.get("coach") or {}),
        "squad_available": bool(team.get("squad")),
        "squad_count": len(team.get("squad") or []),
        "staff_count": len(team.get("staff") or []),
        "market_value": team.get("marketValue"),
        "recent_form": None,
        "retrieved_fields": _available_keys(team, ["id", "name", "shortName", "tla", "area", "crest", "coach", "squad"]),
        "missing_fields": _missing_keys(team, ["coach", "squad", "staff", "marketValue"]),
    }


def _merge_team_detail(team: dict[str, Any], detail: dict[str, Any]) -> None:
    area = detail.get("area") or {}
    team.update(
        {
            "official_name": detail.get("name") or team.get("official_name"),
            "short_name": detail.get("shortName") or team.get("short_name"),
            "tla": detail.get("tla") or team.get("tla"),
            "area_name": area.get("name") or team.get("area_name"),
            "area_code": area.get("code") or team.get("area_code"),
            "crest": detail.get("crest") or team.get("crest"),
            "coach": _coach_row(detail.get("coach") or {}),
            "squad_available": bool(detail.get("squad")),
            "squad_count": len(detail.get("squad") or []),
            "staff_count": len(detail.get("staff") or []),
            "market_value": detail.get("marketValue"),
            "retrieved_fields": _available_keys(detail, ["id", "name", "shortName", "tla", "area", "crest", "coach", "squad"]),
            "missing_fields": _missing_keys(detail, ["coach", "squad", "staff", "marketValue"]),
        }
    )


def _coach_row(coach: dict[str, Any]) -> dict[str, Any] | None:
    if not coach or not any(coach.get(key) for key in ("id", "name", "firstName", "lastName", "nationality")):
        return None
    contract = coach.get("contract") or {}
    return {
        "id": coach.get("id"),
        "name": coach.get("name"),
        "first_name": coach.get("firstName"),
        "last_name": coach.get("lastName"),
        "date_of_birth": coach.get("dateOfBirth"),
        "nationality": coach.get("nationality"),
        "contract_start": contract.get("start"),
        "contract_until": contract.get("until"),
    }


def _append_players(feed: dict[str, Any], team: dict[str, Any], team_detail: dict[str, Any]) -> None:
    for player in team_detail.get("squad") or []:
        current_team = player.get("currentTeam") or {}
        contract = current_team.get("contract") or {}
        feed["players"].append(
            {
                "local_team_key": team["local_team_key"],
                "team_api_id": team["football_data_team_id"],
                "team_official_name": team["official_name"],
                "person_id": player.get("id"),
                "name": player.get("name"),
                "first_name": player.get("firstName"),
                "last_name": player.get("lastName"),
                "position": player.get("position"),
                "date_of_birth": player.get("dateOfBirth"),
                "nationality": player.get("nationality"),
                "shirt_number": player.get("shirtNumber"),
                "market_value": player.get("marketValue"),
                "current_team_id": current_team.get("id"),
                "current_team_name": current_team.get("name"),
                "current_team_contract_start": contract.get("start"),
                "current_team_contract_until": contract.get("until"),
                "recent_stats": None,
                "retrieved_fields": _available_keys(
                    player,
                    ["id", "name", "firstName", "lastName", "position", "dateOfBirth", "nationality", "shirtNumber"],
                ),
                "missing_fields": _missing_keys(player, ["shirtNumber", "marketValue", "currentTeam"]),
            }
        )


def _summarize_team_matches(
    team: dict[str, Any], payload: dict[str, Any], *, limit: int = 10
) -> dict[str, Any]:
    all_matches = payload.get("matches") or []
    # On ne garde que les N matchs termines les plus recents (tri par date desc).
    finished = [
        match
        for match in all_matches
        if (match.get("score") or {}).get("fullTime", {}).get("home") is not None
        and (match.get("score") or {}).get("fullTime", {}).get("away") is not None
    ]
    finished.sort(key=lambda match: match.get("utcDate") or "", reverse=True)
    matches = finished[: max(1, limit)]

    goals_for = 0
    goals_against = 0
    clean_sheets = 0
    wins = 0
    draws = 0
    losses = 0
    played = 0
    normalized_team = team["local_team_key"]
    for match in matches:
        score = (match.get("score") or {}).get("fullTime") or {}
        home_score, away_score = score.get("home"), score.get("away")
        home = _normalize_team(_api_team_name(match.get("homeTeam") or {}))
        away = _normalize_team(_api_team_name(match.get("awayTeam") or {}))
        if normalized_team == home:
            gf, ga = int(home_score), int(away_score)
        elif normalized_team == away:
            gf, ga = int(away_score), int(home_score)
        else:
            continue
        played += 1
        goals_for += gf
        goals_against += ga
        clean_sheets += int(ga == 0)
        wins += int(gf > ga)
        draws += int(gf == ga)
        losses += int(gf < ga)

    return {
        "status": "retrieved" if played else "missing",
        "matches_available": len(all_matches),
        "matches_count": len(matches),
        "played_count": played,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "clean_sheets": clean_sheets,
        "goals_for_per_match": round(goals_for / played, 2) if played else None,
        "goals_against_per_match": round(goals_against / played, 2) if played else None,
    }


def _enrich_players_with_recent_matches(
    feed: dict[str, Any],
    api: FootballDataClient,
    *,
    recent_player_matches_limit: int,
    date_from: date,
    date_to: date,
    errors: list[dict[str, Any]],
) -> None:
    enriched = 0
    for player in feed["players"]:
        person_id = player.get("person_id")
        if person_id is None:
            continue
        payload = _safe_get(
            api,
            f"persons/{person_id}/matches",
            params={
                "limit": recent_player_matches_limit,
                "dateFrom": date_from.isoformat(),
                "dateTo": date_to.isoformat(),
                "status": "FINISHED",
            },
            errors=errors,
        )
        aggregations = payload.get("aggregations") or {}
        player["recent_stats"] = {
            "status": "retrieved" if aggregations else "missing",
            "matches_on_pitch": aggregations.get("matchesOnPitch"),
            "starting_xi": aggregations.get("startingXI"),
            "minutes_played": aggregations.get("minutesPlayed"),
            "goals": aggregations.get("goals"),
            "assists": aggregations.get("assists"),
            "subbed_in": aggregations.get("subbedIn"),
            "subbed_out": aggregations.get("subbedOut"),
            "yellow_cards": aggregations.get("yellowCards"),
            "red_cards": aggregations.get("redCards"),
        }
        enriched += int(bool(aggregations))
    feed["coverage"]["player_recent_matches"] = _status_block(
        retrieved=enriched > 0,
        count=enriched,
        endpoint="/v4/persons/{id}/matches",
    )


def _build_scorers(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in payload.get("scorers") or []:
        player = row.get("player") or {}
        team = row.get("team") or {}
        rows.append(
            {
                "person_id": player.get("id"),
                "player_name": player.get("name"),
                "team_id": team.get("id"),
                "team_name": team.get("name"),
                "goals": row.get("goals"),
                "assists": row.get("assists"),
                "penalties": row.get("penalties"),
            }
        )
    return rows


def _api_team_name(team: dict[str, Any]) -> str:
    return str(team.get("name") or team.get("shortName") or team.get("tla") or "")


def _available_keys(payload: dict[str, Any], keys: list[str]) -> list[str]:
    return [key for key in keys if payload.get(key) not in (None, [], {})]


def _missing_keys(payload: dict[str, Any], keys: list[str]) -> list[str]:
    return [key for key in keys if payload.get(key) in (None, [], {})]
