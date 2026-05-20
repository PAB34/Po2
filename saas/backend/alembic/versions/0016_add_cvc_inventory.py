"""Add cvc_inventory_items table for terrain equipment inventory.

Revision ID: 0016_add_cvc_inventory
Revises: 0015_add_bpu_tables
"""
import sqlalchemy as sa
from alembic import op

revision = "0016_add_cvc_inventory"
down_revision = "0015_add_bpu_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cvc_inventory_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("building_id", sa.Integer(), nullable=False),
        sa.Column("equipment_ref_id", sa.Integer(), nullable=True),
        sa.Column("site_raw", sa.String(500), nullable=True),
        sa.Column("batiment", sa.String(255), nullable=True),
        sa.Column("niveau", sa.String(100), nullable=True),
        sa.Column("local_name", sa.String(255), nullable=True),
        sa.Column("designation", sa.String(500), nullable=False),
        sa.Column("statut", sa.String(100), nullable=True),
        sa.Column("etat_sante", sa.String(100), nullable=True),
        sa.Column("quantite_relevee", sa.Integer(), nullable=True),
        sa.Column("famille", sa.String(255), nullable=True),
        sa.Column("marque", sa.String(255), nullable=True),
        sa.Column("modele", sa.String(255), nullable=True),
        sa.Column("date_mis_en_service", sa.Integer(), nullable=True),
        sa.Column("duree_vie_restante", sa.Float(), nullable=True),
        sa.Column("import_batch", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["equipment_ref_id"], ["equipment_references.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cvc_inventory_items_building_id", "cvc_inventory_items", ["building_id"])
    op.create_index("ix_cvc_inventory_items_equipment_ref_id", "cvc_inventory_items", ["equipment_ref_id"])


def downgrade() -> None:
    op.drop_index("ix_cvc_inventory_items_equipment_ref_id", table_name="cvc_inventory_items")
    op.drop_index("ix_cvc_inventory_items_building_id", table_name="cvc_inventory_items")
    op.drop_table("cvc_inventory_items")
