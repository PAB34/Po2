"""add acte qualification fields (type/label/date_effet) sur les imports DALKIA & DPGF P1

Revision ID: 0053
Revises: 0052
Create Date: 2026-06-11
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0053"
down_revision = "0052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("cpe_dalkia_ref_imports", "cpe_dpgf_p1_imports"):
        op.add_column(table, sa.Column("acte_type", sa.String(length=30), nullable=True))
        op.add_column(table, sa.Column("acte_label", sa.String(length=255), nullable=True))
        op.add_column(table, sa.Column("date_effet", sa.Date(), nullable=True))


def downgrade() -> None:
    for table in ("cpe_dalkia_ref_imports", "cpe_dpgf_p1_imports"):
        op.drop_column(table, "date_effet")
        op.drop_column(table, "acte_label")
        op.drop_column(table, "acte_type")
