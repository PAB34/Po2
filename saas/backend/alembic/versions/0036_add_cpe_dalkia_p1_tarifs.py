"""add cpe_dalkia_ref_p1_tarifs (composants prix gaz + coefficients revision Pu)

Revision ID: 0036
Revises: 0035
Create Date: 2026-06-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cpe_dalkia_ref_p1_tarifs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("import_id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("type_tarif", sa.String(length=10), nullable=False),
        sa.Column("p0_fournisseur", sa.Float(), nullable=True),
        sa.Column("ref_peg", sa.Float(), nullable=True),
        sa.Column("terme_acheminement", sa.Float(), nullable=True),
        sa.Column("obligation_cee", sa.Float(), nullable=True),
        sa.Column("ticgn", sa.Float(), nullable=True),
        sa.Column("marge_exploitant_pct", sa.Float(), nullable=True),
        sa.Column("prix_unitaire_ht", sa.Float(), nullable=True),
        sa.Column("coef_a", sa.Float(), nullable=True),
        sa.Column("coef_b", sa.Float(), nullable=True),
        sa.Column("coef_c", sa.Float(), nullable=True),
        sa.Column("coef_d", sa.Float(), nullable=True),
        sa.Column("coef_e", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["import_id"], ["cpe_dalkia_ref_imports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("import_id", "type_tarif", name="uq_dalkia_p1_tarif"),
    )
    op.create_index("ix_cpe_dalkia_ref_p1_tarifs_import_id", "cpe_dalkia_ref_p1_tarifs", ["import_id"])
    op.create_index("ix_cpe_dalkia_ref_p1_tarifs_city_id", "cpe_dalkia_ref_p1_tarifs", ["city_id"])
    op.create_index("ix_cpe_dalkia_ref_p1_tarifs_type_tarif", "cpe_dalkia_ref_p1_tarifs", ["type_tarif"])


def downgrade() -> None:
    op.drop_table("cpe_dalkia_ref_p1_tarifs")
