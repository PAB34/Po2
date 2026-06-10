"""add multi building ids to cvc source mappings

Revision ID: 0051
Revises: 0050
Create Date: 2026-06-10
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0051"
down_revision = "0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cvc_source_building_mappings", sa.Column("building_ids_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("cvc_source_building_mappings", "building_ids_json")
