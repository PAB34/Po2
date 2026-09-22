"""outil de metre thermique : suppression des anciennes methodes (niveaux, traces, pieces, calques)

Refondation de l'application (docs/thermique/refondation-application-audit.md) : le metre sur contours, les
calques designes par l'exemple et les pieces de l'etape E3 sont remplaces par la chaine sur l'image seule.
Leurs tables et leurs donnees sont supprimees (decision de l'utilisateur du 2026-09-22). Le retour arriere
recree les tables vides (definitions des migrations 0078 a 0081) ; la colonne north_deg est conservee.

Revision ID: 0082
Revises: 0081
Create Date: 2026-09-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0082"
down_revision = "0081"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("thermique_rooms")
    op.drop_table("thermique_zones")
    op.drop_table("thermique_levels")
    with op.batch_alter_table("thermique_projects") as table:
        table.drop_column("signatures_json")


def _horodatage() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def downgrade() -> None:
    op.add_column("thermique_projects", sa.Column("signatures_json", sa.Text(), nullable=True))
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
        *_horodatage(),
        sa.Column("ceiling_height_m", sa.Float(), nullable=True),
        sa.Column("heights_source", sa.String(length=20), nullable=True),
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
        *_horodatage(),
    )
    op.create_index("ix_thermique_zones_project_id", "thermique_zones", ["project_id"])
    op.create_index("ix_thermique_zones_level_id", "thermique_zones", ["level_id"])
    op.create_table(
        "thermique_rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("thermique_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sheet_id", sa.Integer(), sa.ForeignKey("thermique_sheets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("code", sa.String(length=40), nullable=True),
        sa.Column("name_source", sa.String(length=10), nullable=True),
        sa.Column("classe", sa.String(length=20), nullable=False, server_default="chauffe"),
        sa.Column("classe_source", sa.String(length=10), nullable=False, server_default="propose"),
        sa.Column("points_json", sa.Text(), nullable=False),
        sa.Column("area_m2", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=10), nullable=False, server_default="auto"),
        *_horodatage(),
    )
    op.create_index("ix_thermique_rooms_project_id", "thermique_rooms", ["project_id"])
    op.create_index("ix_thermique_rooms_sheet_id", "thermique_rooms", ["sheet_id"])
