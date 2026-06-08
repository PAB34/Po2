"""add cvc refrigerant pilotage fields

Revision ID: 0048
Revises: 0047
Create Date: 2026-06-08
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cvc_refrigerant_items", sa.Column("detection_permanente", sa.Boolean(), nullable=True))
    op.add_column("cvc_refrigerant_items", sa.Column("dernier_controle_etancheite", sa.Date(), nullable=True))
    op.add_column("cvc_refrigerant_items", sa.Column("prochaine_echeance", sa.Date(), nullable=True))
    op.add_column("cvc_refrigerant_items", sa.Column("titulaire", sa.String(length=255), nullable=True))
    op.add_column("cvc_refrigerant_items", sa.Column("responsable_collectivite", sa.String(length=255), nullable=True))
    op.add_column("cvc_refrigerant_items", sa.Column("statut_action", sa.String(length=80), nullable=True))
    op.add_column("cvc_refrigerant_items", sa.Column("commentaire_gmao", sa.Text(), nullable=True))
    op.create_index(
        "ix_cvc_refrigerant_items_prochaine_echeance",
        "cvc_refrigerant_items",
        ["prochaine_echeance"],
    )
    op.create_index(
        "ix_cvc_refrigerant_items_statut_action",
        "cvc_refrigerant_items",
        ["statut_action"],
    )


def downgrade() -> None:
    op.drop_index("ix_cvc_refrigerant_items_statut_action", table_name="cvc_refrigerant_items")
    op.drop_index("ix_cvc_refrigerant_items_prochaine_echeance", table_name="cvc_refrigerant_items")
    op.drop_column("cvc_refrigerant_items", "commentaire_gmao")
    op.drop_column("cvc_refrigerant_items", "statut_action")
    op.drop_column("cvc_refrigerant_items", "responsable_collectivite")
    op.drop_column("cvc_refrigerant_items", "titulaire")
    op.drop_column("cvc_refrigerant_items", "prochaine_echeance")
    op.drop_column("cvc_refrigerant_items", "dernier_controle_etancheite")
    op.drop_column("cvc_refrigerant_items", "detection_permanente")
