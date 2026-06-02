import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.pronostics import PronosticsMatch, PronosticsPlayer, PronosticsPrediction
from app.schemas.pronostics import PronosticsPredictionWrite, PronosticsRankingRead

MATCHES_FILE = Path(__file__).resolve().parent.parent / "data" / "pronostics_matches.json"


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
