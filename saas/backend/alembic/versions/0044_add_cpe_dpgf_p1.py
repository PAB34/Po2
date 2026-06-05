"""add cpe_dpgf_p1 (DPGF P1 revise — livrable separe DALKIA, lignee d'import propre)

Revision ID: 0044
Revises: 0043
Create Date: 2026-06-05
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cpe_dpgf_p1_imports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=True),
        sa.Column("lot", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("import_date", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("nb_lines", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_cpe_dpgf_p1_imports_city_id", "cpe_dpgf_p1_imports", ["city_id"])
    op.create_index("ix_cpe_dpgf_p1_imports_lot", "cpe_dpgf_p1_imports", ["lot"])

    op.create_table(
        "cpe_dpgf_p1_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "import_id",
            sa.Integer(),
            sa.ForeignKey("cpe_dpgf_p1_imports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=True),
        sa.Column("lot", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("code_site", sa.String(length=40), nullable=False),
        sa.Column("pce", sa.String(length=30), nullable=True),
        sa.Column("type_tarif", sa.String(length=10), nullable=True),
        sa.Column("prix_unitaire_ht", sa.Float(), nullable=True),
        sa.Column("period_idx", sa.Integer(), nullable=False),
        sa.Column("period_label", sa.String(length=80), nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("qt_mwhpcs", sa.Float(), nullable=True),
        sa.Column("p10_var_ht", sa.Float(), nullable=True),
        sa.Column("p10_total_ht", sa.Float(), nullable=True),
        sa.UniqueConstraint("import_id", "level", "code_site", "period_idx", name="uq_dpgf_p1_line"),
    )
    op.create_index("ix_cpe_dpgf_p1_lines_import_id", "cpe_dpgf_p1_lines", ["import_id"])
    op.create_index("ix_cpe_dpgf_p1_lines_city_id", "cpe_dpgf_p1_lines", ["city_id"])
    op.create_index("ix_cpe_dpgf_p1_lines_lot", "cpe_dpgf_p1_lines", ["lot"])
    op.create_index("ix_cpe_dpgf_p1_lines_level", "cpe_dpgf_p1_lines", ["level"])
    op.create_index("ix_cpe_dpgf_p1_lines_code_site", "cpe_dpgf_p1_lines", ["code_site"])
    op.create_index("ix_cpe_dpgf_p1_lines_period_year", "cpe_dpgf_p1_lines", ["period_year"])


def downgrade() -> None:
    op.drop_index("ix_cpe_dpgf_p1_lines_period_year", table_name="cpe_dpgf_p1_lines")
    op.drop_index("ix_cpe_dpgf_p1_lines_code_site", table_name="cpe_dpgf_p1_lines")
    op.drop_index("ix_cpe_dpgf_p1_lines_level", table_name="cpe_dpgf_p1_lines")
    op.drop_index("ix_cpe_dpgf_p1_lines_lot", table_name="cpe_dpgf_p1_lines")
    op.drop_index("ix_cpe_dpgf_p1_lines_city_id", table_name="cpe_dpgf_p1_lines")
    op.drop_index("ix_cpe_dpgf_p1_lines_import_id", table_name="cpe_dpgf_p1_lines")
    op.drop_table("cpe_dpgf_p1_lines")

    op.drop_index("ix_cpe_dpgf_p1_imports_lot", table_name="cpe_dpgf_p1_imports")
    op.drop_index("ix_cpe_dpgf_p1_imports_city_id", table_name="cpe_dpgf_p1_imports")
    op.drop_table("cpe_dpgf_p1_imports")
