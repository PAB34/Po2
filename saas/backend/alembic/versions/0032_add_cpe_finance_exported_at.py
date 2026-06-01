"""Ajoute l'horodatage d'emission de la fiche de liaison finance CPE.

Revision ID: 0032
Revises: 0031
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cpe_finance_invoices", sa.Column("finance_exported_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_cpe_finance_invoices_finance_exported_at", "cpe_finance_invoices", ["finance_exported_at"])


def downgrade() -> None:
    op.drop_index("ix_cpe_finance_invoices_finance_exported_at", table_name="cpe_finance_invoices")
    op.drop_column("cpe_finance_invoices", "finance_exported_at")
