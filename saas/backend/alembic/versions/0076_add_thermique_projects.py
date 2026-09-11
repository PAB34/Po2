"""outil de metre thermique : projets, fichiers importes, planches

Socle de l'outil thermique.patrimoineaucarre.com (etape 1). Un projet appartient a un
compte (Po2 ou bureau d'etudes), independamment du patrimoine de la Ville. Chaque page
d'un fichier importe devient une planche, dont la nature (plan, coupe, facade, plan
masse) et l'echelle sont validees par l'utilisateur.

Revision ID: 0076
Revises: 0075
Create Date: 2026-09-11
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0076"
down_revision = "0075"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "thermique_projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "owner_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_thermique_projects_owner_user_id", "thermique_projects", ["owner_user_id"])

    op.create_table(
        "thermique_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("thermique_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=64), nullable=False),
        sa.Column("file_format", sa.String(length=10), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_thermique_documents_project_id", "thermique_documents", ["project_id"])
    op.create_index("ix_thermique_documents_sha256", "thermique_documents", ["sha256"])

    op.create_table(
        "thermique_sheets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("thermique_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("thermique_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page_index", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("nature", sa.String(length=20), nullable=True),
        sa.Column("nature_suggested", sa.String(length=20), nullable=True),
        sa.Column("level_label", sa.String(length=80), nullable=True),
        sa.Column("scale_denominator", sa.Float(), nullable=True),
        sa.Column("scale_source", sa.String(length=20), nullable=True),
        sa.Column("calibration_json", sa.Text(), nullable=True),
        sa.Column("rotation_deg", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("page_width_pt", sa.Float(), nullable=False),
        sa.Column("page_height_pt", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_thermique_sheets_project_id", "thermique_sheets", ["project_id"])
    op.create_index("ix_thermique_sheets_document_id", "thermique_sheets", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_thermique_sheets_document_id", table_name="thermique_sheets")
    op.drop_index("ix_thermique_sheets_project_id", table_name="thermique_sheets")
    op.drop_table("thermique_sheets")
    op.drop_index("ix_thermique_documents_sha256", table_name="thermique_documents")
    op.drop_index("ix_thermique_documents_project_id", table_name="thermique_documents")
    op.drop_table("thermique_documents")
    op.drop_index("ix_thermique_projects_owner_user_id", table_name="thermique_projects")
    op.drop_table("thermique_projects")
