from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_token
from app.models.pronostics import PronosticsMatch, PronosticsPlayer, PronosticsPrediction
from app.models.user import User
from app.schemas.pronostics import (
    PronosticsLoginRequest,
    PronosticsMatchRead,
    PronosticsPlayerRead,
    PronosticsPredictionsWrite,
    PronosticsRankingRead,
    PronosticsRegisterRequest,
    PronosticsTokenResponse,
)
from app.services.pronostics import (
    authenticate_player,
    calculate_ranking,
    create_player,
    create_player_token,
    ensure_matches,
    get_player_by_id,
    save_predictions,
    sync_scores,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/pronostics", tags=["pronostics"])
security = HTTPBearer(auto_error=False)


def get_current_player(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> PronosticsPlayer:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentification requise.")
    try:
        subject = str(decode_token(credentials.credentials).get("sub", ""))
        prefix, player_id = subject.split(":", maxsplit=1)
        if prefix != "pronostics":
            raise ValueError
        player = get_player_by_id(db, int(player_id))
    except (JWTError, TypeError, ValueError):
        player = None
    if player is None or not player.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide.")
    return player


def _player_read(player: PronosticsPlayer) -> PronosticsPlayerRead:
    return PronosticsPlayerRead(id=player.id, email=player.email, pseudo=player.pseudo, service=player.service)


@router.post("/register", response_model=PronosticsTokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: PronosticsRegisterRequest, db: Session = Depends(get_db)) -> PronosticsTokenResponse:
    try:
        player = create_player(db, **payload.model_dump())
    except ValueError as exc:
        messages = {
            "EMAIL_ALREADY_EXISTS": "Un compte existe déjà avec cette adresse email.",
            "PSEUDO_ALREADY_EXISTS": "Ce pseudo est déjà utilisé.",
        }
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=messages.get(str(exc), "Inscription impossible.")) from exc
    return PronosticsTokenResponse(access_token=create_player_token(player), player=_player_read(player))


@router.post("/login", response_model=PronosticsTokenResponse)
def login(payload: PronosticsLoginRequest, db: Session = Depends(get_db)) -> PronosticsTokenResponse:
    player = authenticate_player(db, **payload.model_dump())
    if player is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants invalides.")
    return PronosticsTokenResponse(access_token=create_player_token(player), player=_player_read(player))


@router.get("/me", response_model=PronosticsPlayerRead)
def me(player: PronosticsPlayer = Depends(get_current_player)) -> PronosticsPlayerRead:
    return _player_read(player)


@router.get("/matches", response_model=list[PronosticsMatchRead])
def matches(
    db: Session = Depends(get_db),
    player: PronosticsPlayer = Depends(get_current_player),
) -> list[PronosticsMatchRead]:
    ensure_matches(db)
    predictions = {
        row.match_id: row
        for row in db.scalars(
            select(PronosticsPrediction).where(PronosticsPrediction.player_id == player.id)
        ).all()
    }
    return [
        PronosticsMatchRead(
            id=match.id,
            group=match.group_name,
            team1=match.team1,
            team2=match.team2,
            match_at=match.match_at,
            stadium=match.stadium,
            locked=match.locked or match.real_score1 is not None or match.real_score2 is not None,
            real_score1=match.real_score1,
            real_score2=match.real_score2,
            prediction_score1=predictions[match.id].score1 if match.id in predictions else None,
            prediction_score2=predictions[match.id].score2 if match.id in predictions else None,
        )
        for match in db.scalars(select(PronosticsMatch).order_by(PronosticsMatch.id)).all()
    ]


@router.put("/predictions", status_code=status.HTTP_204_NO_CONTENT)
def update_predictions(
    payload: PronosticsPredictionsWrite,
    db: Session = Depends(get_db),
    player: PronosticsPlayer = Depends(get_current_player),
) -> None:
    save_predictions(db, player, payload.predictions)


@router.get("/ranking", response_model=list[PronosticsRankingRead])
def ranking(db: Session = Depends(get_db)) -> list[PronosticsRankingRead]:
    ensure_matches(db)
    return calculate_ranking(db)


@router.post("/admin/sync-scores")
def update_scores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int | bool]:
    return sync_scores(db)
