"""Add central building meter links.

Revision: 0021
Revises: 0020
Create Date: 2026-05-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "building_meter_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("building_id", sa.Integer(), sa.ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fluid", sa.String(length=20), nullable=False),
        sa.Column("meter_identifier", sa.String(length=80), nullable=False),
        sa.Column("meter_label", sa.String(length=255), nullable=True),
        sa.Column("usage_label", sa.String(length=120), nullable=True),
        sa.Column("share_ratio", sa.Float(), nullable=False, server_default="1"),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("confidence", sa.String(length=20), nullable=False, server_default="A_VALIDER"),
        sa.Column("validation_status", sa.String(length=20), nullable=False, server_default="A_VALIDER"),
        sa.Column("source", sa.String(length=120), nullable=False, server_default="MANUEL"),
        sa.Column("contract_context", sa.String(length=120), nullable=True),
        sa.Column("supplier_name", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("building_id", "fluid", "meter_identifier", name="uq_building_meter_link_identifier"),
    )
    op.create_index("ix_building_meter_links_building_id", "building_meter_links", ["building_id"])
    op.create_index("ix_building_meter_links_fluid", "building_meter_links", ["fluid"])
    op.create_index("ix_building_meter_links_meter_identifier", "building_meter_links", ["meter_identifier"])


def downgrade() -> None:
    op.drop_index("ix_building_meter_links_meter_identifier", table_name="building_meter_links")
    op.drop_index("ix_building_meter_links_fluid", table_name="building_meter_links")
    op.drop_index("ix_building_meter_links_building_id", table_name="building_meter_links")
    op.drop_table("building_meter_links")
