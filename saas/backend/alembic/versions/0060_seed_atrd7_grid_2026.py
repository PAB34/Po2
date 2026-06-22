"""seed full ATRD7 GRDF grid 2025-2026 (T1-T4) into gas_network_tariffs

Revision ID: 0060
Revises: 0059
Create Date: 2026-06-22

Barème CRE ATRD 7 GRDF en vigueur au 1er juillet 2025 (valable jusqu'au 30 juin 2026),
applicable aux factures 2026. Terme variable T2 = 12,08 €/MWh confirmé contre les
factures TotalEnergies réelles.
"""
from __future__ import annotations

from datetime import date

from alembic import op
import sqlalchemy as sa


revision = "0060"
down_revision = "0059"
branch_labels = None
depends_on = None


_TABLE = sa.table(
    "gas_network_tariffs",
    sa.column("id", sa.Integer),
    sa.column("city_id", sa.Integer),
    sa.column("annee", sa.Integer),
    sa.column("option", sa.String),
    sa.column("atrd_terme_variable_eur_mwh", sa.Float),
    sa.column("atrd_abonnement_annuel_eur", sa.Float),
    sa.column("valid_from", sa.Date),
    sa.column("valid_to", sa.Date),
    sa.column("source", sa.String),
    sa.column("source_url", sa.String),
)

_SOURCE = "CRE délibération 2025-122 — barème ATRD 7 GRDF au 1er juillet 2025"
_URL = "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000051670357"

_GRID = [
    # option, terme variable €/MWh, abonnement annuel €/an
    ("T1", 44.94, 54.72),
    ("T2", 12.08, 186.12),
    ("T3", 8.69, 1301.40),
    ("T4", 1.18, 21705.72),
]


def upgrade() -> None:
    # Remplace le seed partiel (T2 seul) par la grille complète T1-T4 (lignes generiques city_id NULL).
    op.execute(
        sa.text("DELETE FROM gas_network_tariffs WHERE city_id IS NULL AND annee = 2026")
    )
    op.bulk_insert(
        _TABLE,
        [
            {
                "city_id": None, "annee": 2026, "option": opt,
                "atrd_terme_variable_eur_mwh": var, "atrd_abonnement_annuel_eur": abo,
                "valid_from": date(2025, 7, 1), "valid_to": date(2026, 6, 30),
                "source": _SOURCE, "source_url": _URL,
            }
            for opt, var, abo in _GRID
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM gas_network_tariffs WHERE city_id IS NULL AND annee = 2026 AND option IN ('T1','T3','T4')")
    )
