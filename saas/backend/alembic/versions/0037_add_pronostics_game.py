"""add pronostics game

Revision ID: 0037
Revises: 0036
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0037"
down_revision: str | None = "0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pronostics_players",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("pseudo", sa.String(length=60), nullable=False),
        sa.Column("service", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pseudo"),
    )
    op.create_index(op.f("ix_pronostics_players_email"), "pronostics_players", ["email"], unique=True)
    op.create_table(
        "pronostics_matches",
        sa.Column("id", sa.String(length=10), nullable=False),
        sa.Column("group_name", sa.String(length=10), nullable=False),
        sa.Column("team1", sa.String(length=120), nullable=False),
        sa.Column("team2", sa.String(length=120), nullable=False),
        sa.Column("match_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stadium", sa.String(length=255), nullable=False),
        sa.Column("real_score1", sa.Integer(), nullable=True),
        sa.Column("real_score2", sa.Integer(), nullable=True),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "pronostics_predictions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.String(length=10), nullable=False),
        sa.Column("score1", sa.Integer(), nullable=False),
        sa.Column("score2", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["pronostics_matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["pronostics_players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", "match_id", name="uq_pronostics_prediction_player_match"),
    )


def downgrade() -> None:
    op.drop_table("pronostics_predictions")
    op.drop_table("pronostics_matches")
    op.drop_index(op.f("ix_pronostics_players_email"), table_name="pronostics_players")
    op.drop_table("pronostics_players")
