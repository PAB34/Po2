"""add sites hierarchy

Revision ID: 0017_add_sites_hierarchy
Revises: 0016_add_cvc_inventory
Create Date: 2026-05-20 14:15:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0017_add_sites_hierarchy"
down_revision = "0016_add_cvc_inventory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("nom_site", sa.String(length=255), nullable=False),
        sa.Column("adresse", sa.String(length=255), nullable=True),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column("source_rows_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sites_city_id"), "sites", ["city_id"], unique=False)
    op.create_index(op.f("ix_sites_nom_site"), "sites", ["nom_site"], unique=False)
    op.add_column("buildings", sa.Column("site_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_buildings_site_id"), "buildings", ["site_id"], unique=False)
    op.create_foreign_key(
        "fk_buildings_site_id_sites",
        "buildings",
        "sites",
        ["site_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_buildings_site_id_sites", "buildings", type_="foreignkey")
    op.drop_index(op.f("ix_buildings_site_id"), table_name="buildings")
    op.drop_column("buildings", "site_id")
    op.drop_index(op.f("ix_sites_nom_site"), table_name="sites")
    op.drop_index(op.f("ix_sites_city_id"), table_name="sites")
    op.drop_table("sites")
