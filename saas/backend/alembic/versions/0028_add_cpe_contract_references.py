"""add cpe_contract_references table

Revision ID: 0028
Revises: 0027
Create Date: 2026-05-29
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cpe_contract_references",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("contract_code", sa.String(length=80), nullable=False),
        sa.Column("contract_label", sa.String(length=255), nullable=True),
        sa.Column("reference_kind", sa.String(length=50), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("market", sa.String(length=30), nullable=False),
        sa.Column("billed_item", sa.String(length=120), nullable=False),
        sa.Column("annual_amount_ht", sa.Float(), nullable=True),
        sa.Column("expected_amount_ht", sa.Float(), nullable=True),
        sa.Column("installment_count", sa.Integer(), nullable=True),
        sa.Column("expected_period_months", sa.String(length=80), nullable=True),
        sa.Column("included_billed_items", sa.Text(), nullable=True),
        sa.Column("formula", sa.Text(), nullable=True),
        sa.Column("tolerance_pct", sa.Float(), nullable=True),
        sa.Column("tolerance_eur", sa.Float(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "city_id",
            "contract_code",
            "reference_kind",
            "year",
            "market",
            "billed_item",
            name="uq_cpe_contract_reference_key",
        ),
    )
    op.create_index("ix_cpe_contract_references_city_id", "cpe_contract_references", ["city_id"])
    op.create_index("ix_cpe_contract_references_contract_code", "cpe_contract_references", ["contract_code"])
    op.create_index("ix_cpe_contract_references_reference_kind", "cpe_contract_references", ["reference_kind"])
    op.create_index("ix_cpe_contract_references_year", "cpe_contract_references", ["year"])
    op.create_index("ix_cpe_contract_references_market", "cpe_contract_references", ["market"])
    op.create_index("ix_cpe_contract_references_billed_item", "cpe_contract_references", ["billed_item"])


def downgrade() -> None:
    op.drop_index("ix_cpe_contract_references_billed_item", table_name="cpe_contract_references")
    op.drop_index("ix_cpe_contract_references_market", table_name="cpe_contract_references")
    op.drop_index("ix_cpe_contract_references_year", table_name="cpe_contract_references")
    op.drop_index("ix_cpe_contract_references_reference_kind", table_name="cpe_contract_references")
    op.drop_index("ix_cpe_contract_references_contract_code", table_name="cpe_contract_references")
    op.drop_index("ix_cpe_contract_references_city_id", table_name="cpe_contract_references")
    op.drop_table("cpe_contract_references")
