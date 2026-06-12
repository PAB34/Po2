"""add energy_type dimension (electricity/gas) on energy invoices

Socle multi-fournisseur : chaque facture porte desormais l'energie facturee.
Les donnees existantes (imports ENGIE) sont de l'electricite.

Revision ID: 0054
Revises: 0053
Create Date: 2026-06-12
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0054"
down_revision = "0053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("energy_invoice_imports", "energy_invoices"):
        op.add_column(
            table,
            sa.Column(
                "energy_type",
                sa.String(length=20),
                nullable=False,
                server_default="electricity",
            ),
        )


def downgrade() -> None:
    for table in ("energy_invoice_imports", "energy_invoices"):
        op.drop_column(table, "energy_type")
