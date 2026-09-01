"""journal d'annulation du rapprochement ASTECH

L'ecran de rapprochement ne savait pas revenir en arriere : une fois un rattachement,
un renommage ou une suppression faits, il fallait reconstituer l'etat d'avant a la main,
sans savoir exactement ce que l'action avait touche (adresse heritee, position recopiee,
lignes supprimees en cascade).

Cette table stocke, pour chaque action, l'etat AVANT et APRES des lignes ecrites.
Annuler consiste alors a reecrire l'etat d'avant, ce qui est exact par construction.

Revision ID: 0075
Revises: 0074
Create Date: 2026-09-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0075"
down_revision = "0074"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patrimoine_undo_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "city_id",
            sa.Integer(),
            sa.ForeignKey("cities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("snapshots_json", sa.Text(), nullable=False),
        sa.Column("undone_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_patrimoine_undo_entries_city_id", "patrimoine_undo_entries", ["city_id"]
    )
    op.create_index(
        "ix_patrimoine_undo_entries_created_at", "patrimoine_undo_entries", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_patrimoine_undo_entries_created_at", table_name="patrimoine_undo_entries")
    op.drop_index("ix_patrimoine_undo_entries_city_id", table_name="patrimoine_undo_entries")
    op.drop_table("patrimoine_undo_entries")
