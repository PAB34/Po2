"""add cvc provider, power and serial fields

Revision ID: 0052
Revises: 0051
Create Date: 2026-06-11
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0052"
down_revision = "0051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cvc_inventory_items",
        sa.Column("provider", sa.String(length=40), nullable=False, server_default="DALKIA"),
    )
    op.add_column("cvc_inventory_items", sa.Column("type_equipement", sa.String(length=255), nullable=True))
    op.add_column("cvc_inventory_items", sa.Column("numero_serie", sa.String(length=255), nullable=True))
    op.add_column("cvc_inventory_items", sa.Column("puissance", sa.String(length=100), nullable=True))
    op.add_column("cvc_inventory_items", sa.Column("puissance_frigorifique", sa.Float(), nullable=True))
    op.add_column("cvc_inventory_items", sa.Column("puissance_calorifique", sa.Float(), nullable=True))
    op.add_column("cvc_inventory_items", sa.Column("capacite", sa.Float(), nullable=True))
    op.add_column("cvc_inventory_items", sa.Column("duree_vie_restante_source", sa.String(length=40), nullable=True))
    op.create_index("ix_cvc_inventory_items_provider", "cvc_inventory_items", ["provider"])


def downgrade() -> None:
    op.drop_index("ix_cvc_inventory_items_provider", table_name="cvc_inventory_items")
    op.drop_column("cvc_inventory_items", "duree_vie_restante_source")
    op.drop_column("cvc_inventory_items", "capacite")
    op.drop_column("cvc_inventory_items", "puissance_calorifique")
    op.drop_column("cvc_inventory_items", "puissance_frigorifique")
    op.drop_column("cvc_inventory_items", "puissance")
    op.drop_column("cvc_inventory_items", "numero_serie")
    op.drop_column("cvc_inventory_items", "type_equipement")
    op.drop_column("cvc_inventory_items", "provider")
