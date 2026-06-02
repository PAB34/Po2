from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class PronosticsPlayer(Base):
    __tablename__ = "pronostics_players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    pseudo: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    service: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    predictions: Mapped[list["PronosticsPrediction"]] = relationship(back_populates="player")


class PronosticsMatch(Base):
    __tablename__ = "pronostics_matches"

    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    group_name: Mapped[str] = mapped_column(String(10), nullable=False)
    team1: Mapped[str] = mapped_column(String(120), nullable=False)
    team2: Mapped[str] = mapped_column(String(120), nullable=False)
    match_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stadium: Mapped[str] = mapped_column(String(255), nullable=False)
    real_score1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    real_score2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    predictions: Mapped[list["PronosticsPrediction"]] = relationship(back_populates="match")


class PronosticsPrediction(Base):
    __tablename__ = "pronostics_predictions"
    __table_args__ = (UniqueConstraint("player_id", "match_id", name="uq_pronostics_prediction_player_match"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("pronostics_players.id", ondelete="CASCADE"), nullable=False)
    match_id: Mapped[str] = mapped_column(ForeignKey("pronostics_matches.id", ondelete="CASCADE"), nullable=False)
    score1: Mapped[int] = mapped_column(Integer, nullable=False)
    score2: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    player: Mapped[PronosticsPlayer] = relationship(back_populates="predictions")
    match: Mapped[PronosticsMatch] = relationship(back_populates="predictions")


class PronosticsPasswordReset(Base):
    __tablename__ = "pronostics_password_resets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("pronostics_players.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
