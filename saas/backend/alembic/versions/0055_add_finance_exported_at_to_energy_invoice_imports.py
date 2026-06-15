"""add finance_exported_at on energy_invoice_imports

Tracabilite de la transmission au service finance, cote factures fournisseurs
(parite avec le marche DALKIA qui horodatait deja l'export de la fiche de liaison).

Revision ID: 0055
Revises: 0054
Create Date: 2026-06-15
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0055"
down_revision = "0054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "energy_invoice_imports",
        sa.Column("finance_exported_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("energy_invoice_imports", "finance_exported_at")
