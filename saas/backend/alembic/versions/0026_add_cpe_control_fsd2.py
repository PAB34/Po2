"""add fsd2 to cpe finance controls

Revision ID: 0026
Revises: 0025
Create Date: 2026-05-27
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cpe_finance_controls", sa.Column("fsd2_value", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("cpe_finance_controls", "fsd2_value")
