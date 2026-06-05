"""add cvc refrigerant registry

Revision ID: 0046
Revises: 0045
Create Date: 2026-06-05
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cvc_refrigerant_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=True),
        sa.Column(
            "cvc_inventory_item_id",
            sa.Integer(),
            sa.ForeignKey("cvc_inventory_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("import_batch", sa.String(length=255), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=True),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("site_raw", sa.String(length=500), nullable=True),
        sa.Column("designation", sa.String(length=500), nullable=False),
        sa.Column("quantite_relevee", sa.Integer(), nullable=True),
        sa.Column("famille", sa.String(length=255), nullable=True),
        sa.Column("marque", sa.String(length=255), nullable=True),
        sa.Column("modele", sa.String(length=255), nullable=True),
        sa.Column("fluide_frigorigene", sa.String(length=80), nullable=True),
        sa.Column("quantite_fluide_kg", sa.Float(), nullable=True),
        sa.Column("puissance_froid_kw", sa.Float(), nullable=True),
        sa.Column("date_mis_en_service", sa.Integer(), nullable=True),
        sa.Column("gwp", sa.Float(), nullable=True),
        sa.Column("teqco2", sa.Float(), nullable=True),
        sa.Column("esp_status", sa.String(length=100), nullable=True),
        sa.Column("cout_desp_date_eur", sa.Float(), nullable=True),
        sa.Column("cumul_5_ans_eur", sa.Float(), nullable=True),
        sa.Column("schedule_json", sa.Text(), nullable=True),
        sa.Column("match_status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("match_method", sa.String(length=100), nullable=True),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_cvc_refrigerant_items_city_id", "cvc_refrigerant_items", ["city_id"])
    op.create_index(
        "ix_cvc_refrigerant_items_cvc_inventory_item_id",
        "cvc_refrigerant_items",
        ["cvc_inventory_item_id"],
    )
    op.create_index("ix_cvc_refrigerant_items_import_batch", "cvc_refrigerant_items", ["import_batch"])


def downgrade() -> None:
    op.drop_index("ix_cvc_refrigerant_items_import_batch", table_name="cvc_refrigerant_items")
    op.drop_index("ix_cvc_refrigerant_items_cvc_inventory_item_id", table_name="cvc_refrigerant_items")
    op.drop_index("ix_cvc_refrigerant_items_city_id", table_name="cvc_refrigerant_items")
    op.drop_table("cvc_refrigerant_items")
