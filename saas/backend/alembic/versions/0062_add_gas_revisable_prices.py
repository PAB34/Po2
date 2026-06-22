"""add gas_supply_revisable_prices + seed dec 2025

Revision ID: 0062
Revises: 0061
Create Date: 2026-06-22

Prix de fourniture révisable (indexé PEG) par mois. Seed décembre 2025 = 56,88 €/MWh
(valeur unique observée sur les 9 factures révisables du lot TotalEnergies).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0062"
down_revision = "0061"
branch_labels = None
depends_on = None

_TABLE = sa.table(
    "gas_supply_revisable_prices",
    sa.column("id", sa.Integer),
    sa.column("city_id", sa.Integer),
    sa.column("annee", sa.Integer),
    sa.column("mois", sa.Integer),
    sa.column("fourniture_eur_mwh", sa.Float),
    sa.column("source", sa.String),
)


def upgrade() -> None:
    op.create_table(
        "gas_supply_revisable_prices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("annee", sa.Integer(), nullable=False),
        sa.Column("mois", sa.Integer(), nullable=False),
        sa.Column("fourniture_eur_mwh", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("city_id", "annee", "mois", name="uq_gas_revisable_city_annee_mois"),
    )
    op.create_index("ix_gas_supply_revisable_prices_city_id", "gas_supply_revisable_prices", ["city_id"])
    op.create_index("ix_gas_supply_revisable_prices_annee", "gas_supply_revisable_prices", ["annee"])

    op.bulk_insert(
        _TABLE,
        [{
            "city_id": None, "annee": 2025, "mois": 12, "fourniture_eur_mwh": 56.88,
            "source": "Observé factures TotalEnergies (prix révisable PEG déc. 2025)",
        }],
    )


def downgrade() -> None:
    op.drop_table("gas_supply_revisable_prices")
