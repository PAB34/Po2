"""add cpe_dalkia_ref_p1_elec (P1 electricite Lot 2 piscines — PSE retenue)

Revision ID: 0045
Revises: 0044
Create Date: 2026-06-05
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cpe_dalkia_ref_p1_elec",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "import_id",
            sa.Integer(),
            sa.ForeignKey("cpe_dalkia_ref_imports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=True),
        sa.Column("code_site", sa.String(length=40), nullable=False),
        sa.Column("pdl", sa.String(length=30), nullable=True),
        sa.Column("prix_unitaire_ht", sa.Float(), nullable=True),
        sa.Column("period_idx", sa.Integer(), nullable=False),
        sa.Column("period_label", sa.String(length=80), nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("qt_mwh", sa.Float(), nullable=True),
        sa.Column("p10_var_ht", sa.Float(), nullable=True),
        sa.Column("p10_total_ht", sa.Float(), nullable=True),
        sa.UniqueConstraint("import_id", "code_site", "period_idx", name="uq_dalkia_p1_elec"),
    )
    op.create_index("ix_cpe_dalkia_ref_p1_elec_import_id", "cpe_dalkia_ref_p1_elec", ["import_id"])
    op.create_index("ix_cpe_dalkia_ref_p1_elec_city_id", "cpe_dalkia_ref_p1_elec", ["city_id"])
    op.create_index("ix_cpe_dalkia_ref_p1_elec_code_site", "cpe_dalkia_ref_p1_elec", ["code_site"])
    op.create_index("ix_cpe_dalkia_ref_p1_elec_period_year", "cpe_dalkia_ref_p1_elec", ["period_year"])


def downgrade() -> None:
    op.drop_index("ix_cpe_dalkia_ref_p1_elec_period_year", table_name="cpe_dalkia_ref_p1_elec")
    op.drop_index("ix_cpe_dalkia_ref_p1_elec_code_site", table_name="cpe_dalkia_ref_p1_elec")
    op.drop_index("ix_cpe_dalkia_ref_p1_elec_city_id", table_name="cpe_dalkia_ref_p1_elec")
    op.drop_index("ix_cpe_dalkia_ref_p1_elec_import_id", table_name="cpe_dalkia_ref_p1_elec")
    op.drop_table("cpe_dalkia_ref_p1_elec")
