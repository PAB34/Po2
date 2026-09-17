"""outil de metre thermique : pieces des plans (etape E3)

Espaces fermes par les calques designes, nom lu (reconnaissance de caracteres) ou saisi, classement
chauffe / non chauffe / exterieur. Voir docs/thermique/refondation-parcours-decisions.md §13.

Revision ID: 0081
Revises: 0080
Create Date: 2026-09-17
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0081"
down_revision = "0080"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_thermique_rooms_project_id", "thermique_rooms", ["project_id"])
    op.create_index("ix_thermique_rooms_sheet_id", "thermique_rooms", ["sheet_id"])


def downgrade() -> None:
    op.drop_index("ix_thermique_rooms_sheet_id", table_name="thermique_rooms")
    op.drop_index("ix_thermique_rooms_project_id", table_name="thermique_rooms")
    op.drop_table("thermique_rooms")
