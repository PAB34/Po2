"""add cpe_p3_devis (devis petits travaux P3 / type P6 DALKIA)

Revision ID: 0043
Revises: 0042_cvc_inventory_workflow
Create Date: 2026-06-04
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0043"
down_revision = "0042_cvc_inventory_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cpe_p3_devis",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=True),
        sa.Column("numero", sa.String(length=60), nullable=False),
        sa.Column("devis_date", sa.Date(), nullable=True),
        sa.Column("localisation", sa.Text(), nullable=True),
        sa.Column("site_code", sa.String(length=50), nullable=True),
        sa.Column("libelle", sa.Text(), nullable=True),
        sa.Column("domaine", sa.String(length=120), nullable=True),
        sa.Column("type_devis", sa.String(length=20), nullable=True),
        sa.Column("destinataire", sa.String(length=120), nullable=True),
        sa.Column("etat", sa.String(length=60), nullable=True),
        sa.Column("montant_ht", sa.Float(), nullable=True),
        sa.Column("montant_ttc", sa.Float(), nullable=True),
        sa.Column("in_scope", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("city_id", "numero", name="uq_cpe_p3_devis_numero"),
    )
    op.create_index("ix_cpe_p3_devis_city_id", "cpe_p3_devis", ["city_id"])
    op.create_index("ix_cpe_p3_devis_numero", "cpe_p3_devis", ["numero"])
    op.create_index("ix_cpe_p3_devis_site_code", "cpe_p3_devis", ["site_code"])
    op.create_index("ix_cpe_p3_devis_etat", "cpe_p3_devis", ["etat"])
    op.create_index("ix_cpe_p3_devis_devis_date", "cpe_p3_devis", ["devis_date"])
    op.create_index("ix_cpe_p3_devis_in_scope", "cpe_p3_devis", ["in_scope"])


def downgrade() -> None:
    op.drop_index("ix_cpe_p3_devis_in_scope", table_name="cpe_p3_devis")
    op.drop_index("ix_cpe_p3_devis_devis_date", table_name="cpe_p3_devis")
    op.drop_index("ix_cpe_p3_devis_etat", table_name="cpe_p3_devis")
    op.drop_index("ix_cpe_p3_devis_site_code", table_name="cpe_p3_devis")
    op.drop_index("ix_cpe_p3_devis_numero", table_name="cpe_p3_devis")
    op.drop_index("ix_cpe_p3_devis_city_id", table_name="cpe_p3_devis")
    op.drop_table("cpe_p3_devis")
