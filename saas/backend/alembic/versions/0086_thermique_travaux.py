"""outil thermique : file des niveaux à analyser par le relais local (D92)

Revision ID: 0086
Revises: 0085
Create Date: 2026-09-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0086"
down_revision = "0085"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "thermique_travaux",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("sheet_id", sa.Integer(), nullable=False),
        sa.Column("statut", sa.String(length=20), nullable=False),
        sa.Column("rang", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("demande_par_user_id", sa.Integer(), nullable=True),
        sa.Column("pris_a", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fini_a", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["thermique_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sheet_id"], ["thermique_sheets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["demande_par_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_thermique_travaux_project_id", "thermique_travaux", ["project_id"])
    op.create_index("ix_thermique_travaux_sheet_id", "thermique_travaux", ["sheet_id"])


def downgrade() -> None:
    op.drop_index("ix_thermique_travaux_sheet_id", table_name="thermique_travaux")
    op.drop_index("ix_thermique_travaux_project_id", table_name="thermique_travaux")
    op.drop_table("thermique_travaux")
