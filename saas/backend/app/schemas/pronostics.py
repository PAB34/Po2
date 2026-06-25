from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class PronosticsRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    pseudo: str = Field(min_length=2, max_length=60)
    service: str = Field(min_length=2, max_length=120)


class PronosticsLoginRequest(BaseModel):
    email: EmailStr
    password: str


class PronosticsForgotPasswordRequest(BaseModel):
    email: EmailStr


class PronosticsResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class PronosticsMessageRead(BaseModel):
    message: str


class PronosticsPlayerRead(BaseModel):
    id: int
    email: str
    pseudo: str
    service: str


class PronosticsPlayerUpdate(BaseModel):
    pseudo: str = Field(min_length=2, max_length=60)
    service: str = Field(min_length=2, max_length=120)


class PronosticsChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class PronosticsParticipantRead(BaseModel):
    pseudo: str
    service: str
    predictions_count: int
    points: int
    exact_scores: int
    good_results: int


class PronosticsTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    player: PronosticsPlayerRead


class PronosticsPredictionWrite(BaseModel):
    match_id: str
    score1: int = Field(ge=0, le=20)
    score2: int = Field(ge=0, le=20)


class PronosticsPredictionsWrite(BaseModel):
    predictions: list[PronosticsPredictionWrite]


class PronosticsMatchRead(BaseModel):
    id: str
    group: str
    team1: str
    team2: str
    match_at: datetime
    stadium: str
    locked: bool
    real_score1: int | None
    real_score2: int | None
    prediction_score1: int | None
    prediction_score2: int | None
    fifa_rank1: int | None
    fifa_rank2: int | None


class PronosticsRankingRead(BaseModel):
    rank: int
    pseudo: str
    service: str
    points: int
    exact_scores: int
    good_results: int
    predictions_count: int


class PronosticsModelFeedRead(BaseModel):
    configured: bool
    source: str
    competition: str
    season: int
    summary: dict[str, Any]
    coverage: dict[str, Any]
    teams: list[dict[str, Any]]
    players: list[dict[str, Any]]
    competition_scorers: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    unavailable_fields: dict[str, str]
