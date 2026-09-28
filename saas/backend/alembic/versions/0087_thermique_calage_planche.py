"""outil thermique : le calage d'une planche sur la planche de référence (S2, D173)

Revision ID: 0087
Revises: 0086
Create Date: 2026-09-28
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0087"
down_revision = "0086"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("thermique_sheets") as table:
        table.add_column(sa.Column("calage_json", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("thermique_sheets") as table:
        table.drop_column("calage_json")
