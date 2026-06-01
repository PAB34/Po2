"""drop unique constraint on cpe_dalkia_ref_cibles

Un meme site peut avoir plusieurs lignes par periode (sous-compteurs PV, etc.)
la contrainte unique (import_id, code_site, fluid, period_idx) cause des violations
lors de l'import.

Revision ID: 0034
Revises: 0033
Create Date: 2026-06-01
"""
from __future__ import annotations

from alembic import op


revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_dalkia_cible", "cpe_dalkia_ref_cibles", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_dalkia_cible",
        "cpe_dalkia_ref_cibles",
        ["import_id", "code_site", "fluid", "period_idx"],
    )
