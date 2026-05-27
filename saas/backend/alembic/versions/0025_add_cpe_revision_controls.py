"""add cpe revision controls

Revision ID: 0025
Revises: 0024
Create Date: 2026-05-27
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cpe_finance_lines", sa.Column("base_price", sa.Float(), nullable=True))
    op.add_column("cpe_finance_lines", sa.Column("revised_price", sa.Float(), nullable=True))

    op.create_table(
        "cpe_revision_indices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=True),
        sa.Column("index_code", sa.String(length=30), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("quarter", sa.Integer(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("city_id", "index_code", "year", "quarter", name="uq_cpe_revision_index_period"),
    )
    op.create_index("ix_cpe_revision_indices_city_id", "cpe_revision_indices", ["city_id"])
    op.create_index("ix_cpe_revision_indices_index_code", "cpe_revision_indices", ["index_code"])
    op.create_index("ix_cpe_revision_indices_year", "cpe_revision_indices", ["year"])

    op.create_table(
        "cpe_finance_controls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("cpe_finance_import_batches.id"), nullable=False),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("cpe_finance_invoices.id"), nullable=False),
        sa.Column("line_id", sa.Integer(), sa.ForeignKey("cpe_finance_lines.id"), nullable=False),
        sa.Column("control_type", sa.String(length=40), nullable=False, server_default="revision_p3"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="blocked"),
        sa.Column("severity", sa.String(length=30), nullable=False, server_default="warning"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("formula", sa.Text(), nullable=True),
        sa.Column("index_year", sa.Integer(), nullable=True),
        sa.Column("index_quarter", sa.Integer(), nullable=True),
        sa.Column("icht_ime_value", sa.Float(), nullable=True),
        sa.Column("bt40_value", sa.Float(), nullable=True),
        sa.Column("expected_factor", sa.Float(), nullable=True),
        sa.Column("base_price", sa.Float(), nullable=True),
        sa.Column("expected_revised_price", sa.Float(), nullable=True),
        sa.Column("actual_revised_price", sa.Float(), nullable=True),
        sa.Column("delta_abs", sa.Float(), nullable=True),
        sa.Column("delta_pct", sa.Float(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("line_id", "control_type", name="uq_cpe_finance_control_line_type"),
    )
    op.create_index("ix_cpe_finance_controls_city_id", "cpe_finance_controls", ["city_id"])
    op.create_index("ix_cpe_finance_controls_batch_id", "cpe_finance_controls", ["batch_id"])
    op.create_index("ix_cpe_finance_controls_invoice_id", "cpe_finance_controls", ["invoice_id"])
    op.create_index("ix_cpe_finance_controls_line_id", "cpe_finance_controls", ["line_id"])


def downgrade() -> None:
    op.drop_table("cpe_finance_controls")
    op.drop_table("cpe_revision_indices")
    op.drop_column("cpe_finance_lines", "revised_price")
    op.drop_column("cpe_finance_lines", "base_price")
