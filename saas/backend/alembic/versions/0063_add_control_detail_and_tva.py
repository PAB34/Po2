"""add gas_invoices.control_detail_json + TVA rates in gas_tax_rates

Revision ID: 0063
Revises: 0062
Create Date: 2026-06-22

- control_detail_json : trace lisible de chaque contrôle (fiche de vérification).
- tva_normale / tva_reduite sur gas_tax_rates : sortir les taux TVA du code (éditables, datés).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0063"
down_revision = "0062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("gas_invoices", sa.Column("control_detail_json", sa.Text(), nullable=True))
    op.add_column("gas_tax_rates", sa.Column("tva_normale", sa.Float(), nullable=True))
    op.add_column("gas_tax_rates", sa.Column("tva_reduite", sa.Float(), nullable=True))
    # Seed des taux TVA gaz en vigueur (20 % conso, 5,5 % abonnement/CTA) sur les lignes existantes.
    op.execute(sa.text("UPDATE gas_tax_rates SET tva_normale = 0.20, tva_reduite = 0.055 WHERE tva_normale IS NULL"))


def downgrade() -> None:
    op.drop_column("gas_tax_rates", "tva_reduite")
    op.drop_column("gas_tax_rates", "tva_normale")
    op.drop_column("gas_invoices", "control_detail_json")
