"""add gas_network_tariffs (ATRD/ATRT — TURPE gaz) + seed T2 2026

Revision ID: 0059
Revises: 0058
Create Date: 2026-06-22
"""
from __future__ import annotations

from datetime import date

from alembic import op
import sqlalchemy as sa


revision = "0059"
down_revision = "0058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    table = op.create_table(
        "gas_network_tariffs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("annee", sa.Integer(), nullable=False),
        sa.Column("option", sa.String(length=8), nullable=False),
        sa.Column("atrd_terme_variable_eur_mwh", sa.Float(), nullable=True),
        sa.Column("atrd_abonnement_annuel_eur", sa.Float(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("source", sa.String(length=160), nullable=True),
        sa.Column("source_url", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("city_id", "annee", "option", name="uq_gas_network_city_annee_option"),
    )
    op.create_index("ix_gas_network_tariffs_city_id", "gas_network_tariffs", ["city_id"])
    op.create_index("ix_gas_network_tariffs_annee", "gas_network_tariffs", ["annee"])

    # Seed : terme variable ATRD T2 2026 dérivé des factures (12,08 €/MWh, très stable).
    # À CONFIRMER contre le barème CRE ATRD publié (éditable via l'API). T1/T3/T4 à compléter.
    src = "Dérivé factures TotalEnergies 2026 — à confirmer barème CRE ATRD"
    url = "https://www.cre.fr/documents/deliberations/tarif-peage-distribution-gaz-naturel-grdf-atrd.html"
    op.bulk_insert(
        table,
        [
            {
                "city_id": None, "annee": 2026, "option": "T2",
                "atrd_terme_variable_eur_mwh": 12.08, "atrd_abonnement_annuel_eur": None,
                "valid_from": date(2026, 1, 1), "valid_to": None, "source": src, "source_url": url,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("gas_network_tariffs")
