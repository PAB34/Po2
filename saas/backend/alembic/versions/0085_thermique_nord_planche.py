"""outil thermique : le nord de la planche, posé par le thermicien (D85)

Revision ID: 0085
Revises: 0084
Create Date: 2026-09-23
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0085"
down_revision = "0084"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("thermique_sheets") as table:
        table.add_column(sa.Column("north_json", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("thermique_sheets") as table:
        table.drop_column("north_json")
