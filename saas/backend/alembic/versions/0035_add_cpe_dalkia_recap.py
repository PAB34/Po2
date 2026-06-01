"""add cpe_dalkia_ref_recap table + nb_recap_rows on imports

Revision ID: 0035
Revises: 0034
Create Date: 2026-06-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cpe_dalkia_ref_imports",
        sa.Column("nb_recap_rows", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "cpe_dalkia_ref_recap",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("import_id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(length=40), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("metric", sa.String(length=60), nullable=False),
        sa.Column("metric_label", sa.String(length=255), nullable=True),
        sa.Column("period_year", sa.Integer(), nullable=True),
        sa.Column("period_label", sa.String(length=80), nullable=True),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["import_id"], ["cpe_dalkia_ref_imports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cpe_dalkia_ref_recap_import_id", "cpe_dalkia_ref_recap", ["import_id"])
    op.create_index("ix_cpe_dalkia_ref_recap_city_id", "cpe_dalkia_ref_recap", ["city_id"])
    op.create_index("ix_cpe_dalkia_ref_recap_section", "cpe_dalkia_ref_recap", ["section"])
    op.create_index("ix_cpe_dalkia_ref_recap_category", "cpe_dalkia_ref_recap", ["category"])
    op.create_index("ix_cpe_dalkia_ref_recap_metric", "cpe_dalkia_ref_recap", ["metric"])
    op.create_index("ix_cpe_dalkia_ref_recap_period_year", "cpe_dalkia_ref_recap", ["period_year"])


def downgrade() -> None:
    op.drop_table("cpe_dalkia_ref_recap")
    op.drop_column("cpe_dalkia_ref_imports", "nb_recap_rows")
