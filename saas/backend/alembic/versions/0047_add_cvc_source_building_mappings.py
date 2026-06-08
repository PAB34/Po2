"""add cvc source building mappings

Revision ID: 0047
Revises: 0046
Create Date: 2026-06-08
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cvc_refrigerant_items", sa.Column("site_id", sa.Integer(), nullable=True))
    op.add_column("cvc_refrigerant_items", sa.Column("building_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_cvc_refrigerant_items_site_id_sites",
        "cvc_refrigerant_items",
        "sites",
        ["site_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_cvc_refrigerant_items_building_id_buildings",
        "cvc_refrigerant_items",
        "buildings",
        ["building_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_cvc_refrigerant_items_site_id", "cvc_refrigerant_items", ["site_id"])
    op.create_index("ix_cvc_refrigerant_items_building_id", "cvc_refrigerant_items", ["building_id"])

    op.create_table(
        "cvc_source_building_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("import_batch", sa.String(length=255), nullable=False),
        sa.Column("source_site_raw", sa.String(length=500), nullable=False),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="SET NULL"), nullable=True),
        sa.Column("building_id", sa.Integer(), sa.ForeignKey("buildings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="to_review"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("match_method", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_type", "import_batch", "source_site_raw", name="uq_cvc_source_mapping"),
    )
    op.create_index("ix_cvc_source_building_mappings_city_id", "cvc_source_building_mappings", ["city_id"])
    op.create_index("ix_cvc_source_building_mappings_source_type", "cvc_source_building_mappings", ["source_type"])
    op.create_index("ix_cvc_source_building_mappings_import_batch", "cvc_source_building_mappings", ["import_batch"])
    op.create_index("ix_cvc_source_building_mappings_source_site_raw", "cvc_source_building_mappings", ["source_site_raw"])
    op.create_index("ix_cvc_source_building_mappings_site_id", "cvc_source_building_mappings", ["site_id"])
    op.create_index("ix_cvc_source_building_mappings_building_id", "cvc_source_building_mappings", ["building_id"])


def downgrade() -> None:
    op.drop_index("ix_cvc_source_building_mappings_building_id", table_name="cvc_source_building_mappings")
    op.drop_index("ix_cvc_source_building_mappings_site_id", table_name="cvc_source_building_mappings")
    op.drop_index("ix_cvc_source_building_mappings_source_site_raw", table_name="cvc_source_building_mappings")
    op.drop_index("ix_cvc_source_building_mappings_import_batch", table_name="cvc_source_building_mappings")
    op.drop_index("ix_cvc_source_building_mappings_source_type", table_name="cvc_source_building_mappings")
    op.drop_index("ix_cvc_source_building_mappings_city_id", table_name="cvc_source_building_mappings")
    op.drop_table("cvc_source_building_mappings")

    op.drop_index("ix_cvc_refrigerant_items_building_id", table_name="cvc_refrigerant_items")
    op.drop_index("ix_cvc_refrigerant_items_site_id", table_name="cvc_refrigerant_items")
    op.drop_constraint("fk_cvc_refrigerant_items_building_id_buildings", "cvc_refrigerant_items", type_="foreignkey")
    op.drop_constraint("fk_cvc_refrigerant_items_site_id_sites", "cvc_refrigerant_items", type_="foreignkey")
    op.drop_column("cvc_refrigerant_items", "building_id")
    op.drop_column("cvc_refrigerant_items", "site_id")
