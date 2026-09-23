"""outil thermique : une version d'étude ne garde que les pièces modifiables (D64)

Revision ID: 0084
Revises: 0083
Create Date: 2026-09-23
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0084"
down_revision = "0083"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("thermique_etude_versions") as table:
        table.add_column(sa.Column("pieces_json", sa.Text(), nullable=True))
        table.alter_column("content_json", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    # Les versions sans contenu complet ne sont pas restituables en 0083 : on les écarte.
    op.execute("DELETE FROM thermique_etude_versions WHERE content_json IS NULL")
    with op.batch_alter_table("thermique_etude_versions") as table:
        table.alter_column("content_json", existing_type=sa.Text(), nullable=False)
        table.drop_column("pieces_json")
