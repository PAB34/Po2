"""add cpe_dalkia_ref_bpu (catalogue BPU travaux P3 - Annexe 7)

Revision ID: 0037
Revises: 0036
Create Date: 2026-06-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cpe_dalkia_ref_bpu",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("import_id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("categorie", sa.String(length=20), nullable=False),
        sa.Column("famille", sa.String(length=255), nullable=True),
        sa.Column("code", sa.String(length=30), nullable=True),
        sa.Column("libelle", sa.Text(), nullable=True),
        sa.Column("specificite", sa.String(length=255), nullable=True),
        sa.Column("unite", sa.String(length=40), nullable=True),
        sa.Column("cout_unitaire", sa.Float(), nullable=True),
        sa.Column("cout_nuit", sa.Float(), nullable=True),
        sa.Column("cout_samedi", sa.Float(), nullable=True),
        sa.Column("cout_dimanche", sa.Float(), nullable=True),
        sa.Column("coefficient", sa.Float(), nullable=True),
        sa.Column("coefficient_max", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["import_id"], ["cpe_dalkia_ref_imports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cpe_dalkia_ref_bpu_import_id", "cpe_dalkia_ref_bpu", ["import_id"])
    op.create_index("ix_cpe_dalkia_ref_bpu_city_id", "cpe_dalkia_ref_bpu", ["city_id"])
    op.create_index("ix_cpe_dalkia_ref_bpu_categorie", "cpe_dalkia_ref_bpu", ["categorie"])
    op.create_index("ix_cpe_dalkia_ref_bpu_code", "cpe_dalkia_ref_bpu", ["code"])


def downgrade() -> None:
    op.drop_table("cpe_dalkia_ref_bpu")
