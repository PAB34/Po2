"""outil de metre thermique : roles valides des signatures graphiques d'un projet

Etape E1 de la refondation : les calques de l'architecte, aplatis dans le PDF, se reconnaissent a leur
signature (plume, couleur, tirets, remplissage). Le thermicien valide le role de chaque signature une fois
par projet ; les roles sont gardes ici en JSON (cle de signature -> role).
Voir docs/thermique/refondation-parcours-decisions.md.

Revision ID: 0080
Revises: 0079
Create Date: 2026-09-16
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0080"
down_revision = "0079"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("thermique_projects", sa.Column("signatures_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("thermique_projects", "signatures_json")
