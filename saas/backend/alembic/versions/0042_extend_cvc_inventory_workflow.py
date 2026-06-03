"""Extend CVC inventory workflow with persisted mapping fields.

Revision ID: 0042_extend_cvc_inventory_workflow
Revises: 0041_seed_cpe_contract_scope_references
"""
import sqlalchemy as sa
from alembic import op

revision = "0042_extend_cvc_inventory_workflow"
down_revision = "0041_seed_cpe_contract_scope_references"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cvc_inventory_items", sa.Column("city_id", sa.Integer(), nullable=True))
    op.add_column("cvc_inventory_items", sa.Column("site_id", sa.Integer(), nullable=True))
    op.add_column("cvc_inventory_items", sa.Column("local_id", sa.Integer(), nullable=True))
    op.add_column("cvc_inventory_items", sa.Column("quantite_fluide_frigorigene", sa.Float(), nullable=True))

    op.create_foreign_key(
        "fk_cvc_inventory_items_city_id_cities",
        "cvc_inventory_items",
        "cities",
        ["city_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_cvc_inventory_items_site_id_sites",
        "cvc_inventory_items",
        "sites",
        ["site_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_cvc_inventory_items_local_id_locals",
        "cvc_inventory_items",
        "locals",
        ["local_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_constraint("cvc_inventory_items_building_id_fkey", "cvc_inventory_items", type_="foreignkey")
    op.alter_column("cvc_inventory_items", "building_id", existing_type=sa.Integer(), nullable=True)
    op.create_foreign_key(
        "fk_cvc_inventory_items_building_id_buildings",
        "cvc_inventory_items",
        "buildings",
        ["building_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index("ix_cvc_inventory_items_city_id", "cvc_inventory_items", ["city_id"])
    op.create_index("ix_cvc_inventory_items_site_id", "cvc_inventory_items", ["site_id"])
    op.create_index("ix_cvc_inventory_items_local_id", "cvc_inventory_items", ["local_id"])


def downgrade() -> None:
    op.drop_index("ix_cvc_inventory_items_local_id", table_name="cvc_inventory_items")
    op.drop_index("ix_cvc_inventory_items_site_id", table_name="cvc_inventory_items")
    op.drop_index("ix_cvc_inventory_items_city_id", table_name="cvc_inventory_items")

    op.drop_constraint("fk_cvc_inventory_items_building_id_buildings", "cvc_inventory_items", type_="foreignkey")
    op.alter_column("cvc_inventory_items", "building_id", existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key(
        "cvc_inventory_items_building_id_fkey",
        "cvc_inventory_items",
        "buildings",
        ["building_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("fk_cvc_inventory_items_local_id_locals", "cvc_inventory_items", type_="foreignkey")
    op.drop_constraint("fk_cvc_inventory_items_site_id_sites", "cvc_inventory_items", type_="foreignkey")
    op.drop_constraint("fk_cvc_inventory_items_city_id_cities", "cvc_inventory_items", type_="foreignkey")
    op.drop_column("cvc_inventory_items", "quantite_fluide_frigorigene")
    op.drop_column("cvc_inventory_items", "local_id")
    op.drop_column("cvc_inventory_items", "site_id")
    op.drop_column("cvc_inventory_items", "city_id")
