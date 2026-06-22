"""add patrimoine_match_items (boîte de rapprochement PO2-PAT-003)

Revision ID: 0056
Revises: 0055
Create Date: 2026-06-16
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0056"
down_revision = "0055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patrimoine_match_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("external_id", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("context_json", sa.Text(), nullable=True),
        sa.Column("candidate_target_type", sa.String(length=20), nullable=True),
        sa.Column("candidate_target_id", sa.Integer(), nullable=True),
        sa.Column("candidate_label", sa.String(length=255), nullable=True),
        sa.Column("candidate_score", sa.Float(), nullable=True),
        sa.Column("candidate_reason", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="a_traiter"),
        sa.Column("resolved_target_type", sa.String(length=20), nullable=True),
        sa.Column("resolved_target_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("city_id", "source", "external_id", name="uq_patrimoine_match_source_external"),
    )
    op.create_index("ix_patrimoine_match_items_city_id", "patrimoine_match_items", ["city_id"])
    op.create_index("ix_patrimoine_match_items_source", "patrimoine_match_items", ["source"])
    op.create_index("ix_patrimoine_match_items_external_id", "patrimoine_match_items", ["external_id"])
    op.create_index("ix_patrimoine_match_items_status", "patrimoine_match_items", ["status"])


def downgrade() -> None:
    op.drop_table("patrimoine_match_items")
