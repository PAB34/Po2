"""add accounting_budget_lines (budget annuel par marché, maille opération)

Cf. docs/refonte-v1/suivi-financier-budget-atterrissage-cadrage.md §5

Revision ID: 0066
Revises: 0065
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0066"
down_revision = "0065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounting_budget_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("matrix_contract_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("operation_number", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("amount_budget", sa.Float(), nullable=False, server_default="0"),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["matrix_contract_id"], ["accounting_matrix_contracts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "city_id", "matrix_contract_id", "year", "operation_number",
            name="uq_accounting_budget_line_key",
        ),
    )
    op.create_index("ix_accounting_budget_lines_city_id", "accounting_budget_lines", ["city_id"])
    op.create_index("ix_accounting_budget_lines_matrix_contract_id", "accounting_budget_lines", ["matrix_contract_id"])
    op.create_index("ix_accounting_budget_lines_year", "accounting_budget_lines", ["year"])
    op.create_index("ix_accounting_budget_lines_operation_number", "accounting_budget_lines", ["operation_number"])


def downgrade() -> None:
    op.drop_table("accounting_budget_lines")
