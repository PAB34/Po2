import json
from datetime import datetime
from pathlib import Path
import re
import unicodedata

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.pronostics import PronosticsMatch, PronosticsPlayer, PronosticsPrediction
from app.schemas.pronostics import PronosticsPredictionWrite, PronosticsRankingRead

MATCHES_FILE = Path(__file__).resolve().parent.parent / "data" / "pronostics_matches.json"
TEAM_ALIASES = {
    "argentina": "argentine",
    "algeria": "algerie",
    "australia": "australie",
    "austria": "autriche",
    "belgium": "belgique",
    "brazil": "bresil",
    "bosnia and herzegovina": "bosnie herzegovine",
    "canada": "canada",
    "cape verde": "cap vert",
    "colombia": "colombie",
    "congo dr": "rd congo",
    "dr congo": "rd congo",
    "curacao": "curacao",
    "croatia": "croatie",
    "czechia": "tchequie",
    "czech republic": "tchequie",
    "ecuador": "equateur",
    "egypt": "egypte",
    "england": "angleterre",
    "france": "france",
    "germany": "allemagne",
    "ghana": "ghana",
    "haiti": "haiti",
    "iran": "iran",
    "iraq": "irak",
    "ivory coast": "cote d ivoire",
    "japan": "japon",
    "jordan": "jordanie",
    "korea republic": "coree du sud",
    "mexico": "mexique",
    "morocco": "maroc",
    "netherlands": "pays bas",
    "new zealand": "nouvelle zelande",
    "norway": "norvege",
    "portugal": "portugal",
    "qatar": "qatar",
    "scotland": "ecosse",
    "saudi arabia": "arabie saoudite",
    "senegal": "senegal",
    "south africa": "afrique du sud",
    "south korea": "coree du sud",
    "spain": "espagne",
    "sweden": "suede",
    "switzerland": "suisse",
    "tunisia": "tunisie",
    "turkey": "turquie",
    "united states": "etats unis",
    "united states of america": "etats unis",
    "uruguay": "uruguay",
    "usa": "etats unis",
    "uzbekistan": "ouzbekistan",
}
FIFA_RANKINGS = {
    "france": 1, "espagne": 2, "argentine": 3, "angleterre": 4, "portugal": 5,
    "bresil": 6, "pays bas": 7, "maroc": 8, "belgique": 9, "allemagne": 10,
    "croatie": 11, "colombie": 13, "senegal": 14, "mexique": 15, "etats unis": 16,
    "uruguay": 17, "japon": 18, "suisse": 19, "iran": 21, "turquie": 22,
    "equateur": 23, "autriche": 24, "coree du sud": 25, "australie": 27,
    "algerie": 28, "egypte": 29, "canada": 30, "norvege": 31, "panama": 33,
    "cote d ivoire": 34, "suede": 38, "paraguay": 40, "tchequie": 41,
    "ecosse": 43, "tunisie": 44, "rd congo": 46, "ouzbekistan": 50, "qatar": 55,
    "irak": 57, "afrique du sud": 60, "arabie saoudite": 61, "jordanie": 63,
    "bosnie herzegovine": 65, "cap vert": 69, "ghana": 74, "curacao": 82,
    "haiti": 83, "nouvelle zelande": 85,
}


def ensure_matches(db: Session) -> None:
    if db.scalar(select(PronosticsMatch.id).limit(1)) is not None:
        return

    rows = json.loads(MATCHES_FILE.read_text(encoding="utf-8"))
    db.add_all(
        [PronosticsMatch(**{**row, "match_at": datetime.fromisoformat(row["match_at"].replace("Z", "+00:00"))}) for row in rows]
    )
    db.commit()


def create_player(db: Session, *, email: str, password: str, pseudo: str, service: str) -> PronosticsPlayer:
    normalized_email = email.strip().lower()
    normalized_pseudo = pseudo.strip()
    if db.scalar(select(PronosticsPlayer).where(PronosticsPlayer.email == normalized_email)):
        raise ValueError("EMAIL_ALREADY_EXISTS")
    if db.scalar(select(PronosticsPlayer).where(PronosticsPlayer.pseudo == normalized_pseudo)):
        raise ValueError("PSEUDO_ALREADY_EXISTS")

    player = PronosticsPlayer(
        email=normalized_email,
        password_hash=get_password_hash(password),
        pseudo=normalized_pseudo,
        service=service.strip(),
    )
    db.add(player)
    db.commit()
    db.refresh(player)
    return player


def authenticate_player(db: Session, *, email: str, password: str) -> PronosticsPlayer | None:
    player = db.scalar(select(PronosticsPlayer).where(PronosticsPlayer.email == email.strip().lower()))
    if player is None or not player.is_active or not verify_password(password, player.password_hash):
        return None
    return player


def create_player_token(player: PronosticsPlayer) -> str:
    return create_access_token(subject=f"pronostics:{player.id}")


def get_player_by_id(db: Session, player_id: int) -> PronosticsPlayer | None:
    return db.get(PronosticsPlayer, player_id)


def update_player(db: Session, player: PronosticsPlayer, *, pseudo: str, service: str) -> PronosticsPlayer:
    normalized_pseudo = pseudo.strip()
    other = db.scalar(
        select(PronosticsPlayer).where(
            PronosticsPlayer.pseudo == normalized_pseudo,
            PronosticsPlayer.id != player.id,
        )
    )
    if other is not None:
        raise ValueError("PSEUDO_ALREADY_EXISTS")
    player.pseudo = normalized_pseudo
    player.service = service.strip()
    db.commit()
    db.refresh(player)
    return player


def fifa_rank(team: str) -> int | None:
    return FIFA_RANKINGS.get(_normalize_team(team))


def save_predictions(db: Session, player: PronosticsPlayer, rows: list[PronosticsPredictionWrite]) -> None:
    ensure_matches(db)
    matches = {match.id: match for match in db.scalars(select(PronosticsMatch)).all()}
    existing = {
        prediction.match_id: prediction
        for prediction in db.scalars(
            select(PronosticsPrediction).where(PronosticsPrediction.player_id == player.id)
        ).all()
    }
    for row in rows:
        match = matches.get(row.match_id)
        if match is None or match.locked or match.real_score1 is not None or match.real_score2 is not None:
            continue
        prediction = existing.get(row.match_id)
        if prediction is None:
            prediction = PronosticsPrediction(player_id=player.id, match_id=row.match_id)
            db.add(prediction)
        prediction.score1 = row.score1
        prediction.score2 = row.score2
    db.commit()


def calculate_ranking(db: Session) -> list[PronosticsRankingRead]:
    players = db.scalars(select(PronosticsPlayer).where(PronosticsPlayer.is_active.is_(True))).all()
    matches = {match.id: match for match in db.scalars(select(PronosticsMatch)).all()}
    predictions = db.scalars(select(PronosticsPrediction)).all()
    stats = {
        player.id: {
            "pseudo": player.pseudo,
            "service": player.service,
            "points": 0,
            "exact_scores": 0,
            "good_results": 0,
            "predictions_count": 0,
        }
        for player in players
    }
    for prediction in predictions:
        stat = stats.get(prediction.player_id)
        match = matches.get(prediction.match_id)
        if stat is None or match is None:
            continue
        stat["predictions_count"] += 1
        if match.real_score1 is None or match.real_score2 is None:
            continue
        points, exact, good_result = _score_prediction(
            prediction.score1,
            prediction.score2,
            match.real_score1,
            match.real_score2,
        )
        stat["points"] += points
        stat["exact_scores"] += int(exact)
        stat["good_results"] += int(good_result)

    ranking = sorted(
        stats.values(),
        key=lambda row: (-row["points"], -row["exact_scores"], -row["good_results"], row["pseudo"].lower()),
    )
    return [PronosticsRankingRead(rank=index, **row) for index, row in enumerate(ranking, start=1)]


def sync_scores(db: Session) -> dict[str, int | bool]:
    if not settings.football_data_token:
        return {"configured": False, "api_matches": 0, "finished": 0, "updated": 0, "unmatched": 0}

    ensure_matches(db)
    response = requests.get(
        f"{settings.football_data_base_url}/competitions/{settings.football_data_competition}/matches",
        params={"stage": "GROUP_STAGE", "season": settings.football_data_season},
        headers={"X-Auth-Token": settings.football_data_token},
        timeout=30,
    )
    response.raise_for_status()
    api_matches = response.json().get("matches", [])
    local_matches = db.scalars(select(PronosticsMatch)).all()
    local_by_teams = {
        frozenset((_normalize_team(match.team1), _normalize_team(match.team2))): match for match in local_matches
    }
    result: dict[str, int | bool] = {
        "configured": True,
        "api_matches": len(api_matches),
        "finished": 0,
        "updated": 0,
        "unmatched": 0,
    }
    for api_match in api_matches:
        score = (api_match.get("score") or {}).get("fullTime") or {}
        home_score, away_score = score.get("home"), score.get("away")
        if api_match.get("status") not in {"FINISHED", "AWARDED"} or home_score is None or away_score is None:
            continue
        result["finished"] += 1
        home_name = _api_team_name(api_match.get("homeTeam") or {})
        away_name = _api_team_name(api_match.get("awayTeam") or {})
        local_match = local_by_teams.get(frozenset((_normalize_team(home_name), _normalize_team(away_name))))
        if local_match is None:
            result["unmatched"] += 1
            continue
        if _normalize_team(home_name) == _normalize_team(local_match.team1):
            score1, score2 = int(home_score), int(away_score)
        else:
            score1, score2 = int(away_score), int(home_score)
        if local_match.real_score1 == score1 and local_match.real_score2 == score2 and local_match.locked:
            continue
        local_match.real_score1 = score1
        local_match.real_score2 = score2
        local_match.locked = True
        result["updated"] += 1
    db.commit()
    return result


def _api_team_name(team: dict) -> str:
    return str(team.get("name") or team.get("shortName") or team.get("tla") or "")


def _normalize_team(name: str) -> str:
    normalized = unicodedata.normalize("NFD", str(name).lower())
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized).strip()
    return TEAM_ALIASES.get(normalized, normalized)


def _score_prediction(p1: int, p2: int, r1: int, r2: int) -> tuple[int, bool, bool]:
    exact = p1 == r1 and p2 == r2
    good_result = (p1 > p2) == (r1 > r2) and (p1 < p2) == (r1 < r2)
    if exact:
        return 10, True, True

    points = 5 if good_result else 0
    if p1 - p2 == r1 - r2:
        points += 2
    if p1 == r1:
        points += 1
    if p2 == r2:
        points += 1
    return points, False, good_result
