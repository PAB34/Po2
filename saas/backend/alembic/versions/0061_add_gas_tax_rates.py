"""add gas_tax_rates + seed accise (ex-TICGN) & CTA

Revision ID: 0061
Revises: 0060
Create Date: 2026-06-22

Accise gaz naturel combustible (ex-TICGN), taux normal :
- 15,43 €/MWh au 1er août 2025
- 16,39 €/MWh au 1er février 2026
(confirmés contre les factures TotalEnergies + sources CRE/fournisseurs).
CTA observée ≈ 24,76 % du terme fixe ATRD.
"""
from __future__ import annotations

from datetime import date

from alembic import op
import sqlalchemy as sa


revision = "0061"
down_revision = "0060"
branch_labels = None
depends_on = None

_TABLE = sa.table(
    "gas_tax_rates",
    sa.column("id", sa.Integer),
    sa.column("city_id", sa.Integer),
    sa.column("valid_from", sa.Date),
    sa.column("valid_to", sa.Date),
    sa.column("ticgn_eur_mwh", sa.Float),
    sa.column("cta_coeff_atrd_fixe", sa.Float),
    sa.column("source", sa.String),
    sa.column("source_url", sa.String),
)

_SRC = "Accise gaz (ex-TICGN) taux normal + CTA — confirmé factures & sources publiques"
_URL = "https://www.fournisseurs-electricite.com/contrat-electricite-gaz/taxes/accise-gaz"


def upgrade() -> None:
    op.create_table(
        "gas_tax_rates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("ticgn_eur_mwh", sa.Float(), nullable=True),
        sa.Column("cta_coeff_atrd_fixe", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=160), nullable=True),
        sa.Column("source_url", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gas_tax_rates_city_id", "gas_tax_rates", ["city_id"])
    op.create_index("ix_gas_tax_rates_valid_from", "gas_tax_rates", ["valid_from"])

    op.bulk_insert(
        _TABLE,
        [
            {
                "city_id": None, "valid_from": date(2025, 8, 1), "valid_to": date(2026, 1, 31),
                "ticgn_eur_mwh": 15.43, "cta_coeff_atrd_fixe": 0.2476, "source": _SRC, "source_url": _URL,
            },
            {
                "city_id": None, "valid_from": date(2026, 2, 1), "valid_to": None,
                "ticgn_eur_mwh": 16.39, "cta_coeff_atrd_fixe": 0.2476, "source": _SRC, "source_url": _URL,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("gas_tax_rates")
