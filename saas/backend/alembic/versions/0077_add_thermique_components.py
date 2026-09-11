"""outil de metre thermique : composants de bibliotheque (projet et modeles)

Un composant (mur, plancher, menuiserie, pont thermique...) appartient soit a un projet,
soit aux modeles reutilisables d'un compte (project_id vide). Importer un modele dans un
projet en fait une copie. Voir docs/thermique/bibliotheque-projet-decisions.md.

Revision ID: 0077
Revises: 0076
Create Date: 2026-09-11
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0077"
down_revision = "0076"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "thermique_components",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("thermique_projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="hypothese"),
        sa.Column("composition_json", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("reference_json", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_component_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_thermique_components_owner_user_id", "thermique_components", ["owner_user_id"])
    op.create_index("ix_thermique_components_project_id", "thermique_components", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_thermique_components_project_id", table_name="thermique_components")
    op.drop_index("ix_thermique_components_owner_user_id", table_name="thermique_components")
    op.drop_table("thermique_components")
