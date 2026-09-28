"""outil thermique : vues de coupes, traits de coupe des plans, type de travail du relais (S5)

Revision ID: 0088
Revises: 0087
Create Date: 2026-09-28
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0088"
down_revision = "0087"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "thermique_vues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("thermique_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sheet_id", sa.Integer(), sa.ForeignKey("thermique_sheets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nom", sa.String(length=80), nullable=False),
        sa.Column("nature", sa.String(length=20), nullable=False),
        sa.Column("cadre_json", sa.Text(), nullable=False),
        sa.Column("lecture_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("sheet_id", "nom", name="uq_thermique_vue_nom"),
    )
    op.create_index("ix_thermique_vues_project_id", "thermique_vues", ["project_id"])
    op.create_index("ix_thermique_vues_sheet_id", "thermique_vues", ["sheet_id"])
    with op.batch_alter_table("thermique_sheets") as table:
        table.add_column(sa.Column("traits_coupe_json", sa.Text(), nullable=True))
    with op.batch_alter_table("thermique_travaux") as table:
        table.add_column(sa.Column("type", sa.String(length=20), nullable=False, server_default="niveau"))


def downgrade() -> None:
    with op.batch_alter_table("thermique_travaux") as table:
        table.drop_column("type")
    with op.batch_alter_table("thermique_sheets") as table:
        table.drop_column("traits_coupe_json")
    op.drop_index("ix_thermique_vues_sheet_id", table_name="thermique_vues")
    op.drop_index("ix_thermique_vues_project_id", table_name="thermique_vues")
    op.drop_table("thermique_vues")
