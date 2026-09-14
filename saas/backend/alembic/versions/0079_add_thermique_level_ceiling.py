"""outil de metre thermique : hauteur sous plafond et origine des hauteurs d'un niveau

Lot M3 : les hauteurs d'un niveau peuvent etre lues sur une coupe (planchers detectes) ou
saisies ; la hauteur sous plafond saisie prime sur hauteur d'etage - epaisseur de plancher.
Les traces gardent leur source (automatique, corrige, manuel) : colonne deja presente.
Voir docs/thermique/agent-verification-decisions.md.

Revision ID: 0079
Revises: 0078
Create Date: 2026-09-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0079"
down_revision = "0078"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("thermique_levels", sa.Column("ceiling_height_m", sa.Float(), nullable=True))
    op.add_column("thermique_levels", sa.Column("heights_source", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("thermique_levels", "heights_source")
    op.drop_column("thermique_levels", "ceiling_height_m")
