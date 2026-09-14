"""outil de metre thermique : niveaux, traces (contour, locaux non chauffes, patios) et nord

Lot M1 du metre sur les plans : chaque niveau porte sa planche, ses hauteurs et son calage
(deux points communs) ; les traces sont stockes en points PDF de la planche du niveau.
Voir docs/thermique/metre-plans-decisions.md.

Revision ID: 0078
Revises: 0077
Create Date: 2026-09-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0078"
down_revision = "0077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("thermique_projects", sa.Column("north_deg", sa.Float(), nullable=True))
    op.create_table(
        "thermique_levels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("thermique_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("altitude_m", sa.Float(), nullable=True),
        sa.Column("floor_height_m", sa.Float(), nullable=True),
        sa.Column("slab_thickness_m", sa.Float(), nullable=True),
        sa.Column("sheet_id", sa.Integer(), sa.ForeignKey("thermique_sheets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("calage_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_thermique_levels_project_id", "thermique_levels", ["project_id"])
    op.create_index("ix_thermique_levels_sheet_id", "thermique_levels", ["sheet_id"])
    op.create_table(
        "thermique_zones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("thermique_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("level_id", sa.Integer(), sa.ForeignKey("thermique_levels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("lnc_type", sa.String(length=30), nullable=True),
        sa.Column("points_json", sa.Text(), nullable=False),
        sa.Column("edges_json", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manuel"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_thermique_zones_project_id", "thermique_zones", ["project_id"])
    op.create_index("ix_thermique_zones_level_id", "thermique_zones", ["level_id"])


def downgrade() -> None:
    op.drop_index("ix_thermique_zones_level_id", table_name="thermique_zones")
    op.drop_index("ix_thermique_zones_project_id", table_name="thermique_zones")
    op.drop_table("thermique_zones")
    op.drop_index("ix_thermique_levels_sheet_id", table_name="thermique_levels")
    op.drop_index("ix_thermique_levels_project_id", table_name="thermique_levels")
    op.drop_table("thermique_levels")
    op.drop_column("thermique_projects", "north_deg")
