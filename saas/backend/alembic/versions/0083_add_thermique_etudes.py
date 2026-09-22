"""outil thermique : études de niveau versionnées et plan de référence

Revision ID: 0083
Revises: 0082
Create Date: 2026-09-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0083"
down_revision = "0082"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("thermique_projects") as table:
        table.add_column(sa.Column("reference_sheet_id", sa.Integer(), nullable=True))
        table.create_foreign_key(
            "fk_thermique_projects_reference_sheet",
            "thermique_sheets",
            ["reference_sheet_id"],
            ["id"],
            ondelete="SET NULL",
        )
        table.create_index("ix_thermique_projects_reference_sheet_id", ["reference_sheet_id"], unique=False)

    op.create_table(
        "thermique_etudes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("thermique_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sheet_id", sa.Integer(), sa.ForeignKey("thermique_sheets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format_version", sa.Integer(), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=False),
        sa.Column("local_states_json", sa.Text(), nullable=False),
        sa.Column("imported_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("sheet_id", name="uq_thermique_etudes_sheet_id"),
    )
    op.create_index("ix_thermique_etudes_project_id", "thermique_etudes", ["project_id"])
    op.create_index("ix_thermique_etudes_sheet_id", "thermique_etudes", ["sheet_id"])

    op.create_table(
        "thermique_etude_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("etude_id", sa.Integer(), sa.ForeignKey("thermique_etudes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=80), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=False),
        sa.Column("local_states_json", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("etude_id", "version_number", name="uq_thermique_etude_version"),
    )
    op.create_index("ix_thermique_etude_versions_etude_id", "thermique_etude_versions", ["etude_id"])


def downgrade() -> None:
    op.drop_index("ix_thermique_etude_versions_etude_id", table_name="thermique_etude_versions")
    op.drop_table("thermique_etude_versions")
    op.drop_index("ix_thermique_etudes_sheet_id", table_name="thermique_etudes")
    op.drop_index("ix_thermique_etudes_project_id", table_name="thermique_etudes")
    op.drop_table("thermique_etudes")
    with op.batch_alter_table("thermique_projects") as table:
        table.drop_index("ix_thermique_projects_reference_sheet_id")
        table.drop_constraint("fk_thermique_projects_reference_sheet", type_="foreignkey")
        table.drop_column("reference_sheet_id")
