"""add gas_bpu_prices + seed BPU lot 7 2026 (TotalEnergies / Hérault Énergie)

Revision ID: 0058
Revises: 0057
Create Date: 2026-06-22
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0058"
down_revision = "0057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    table = op.create_table(
        "gas_bpu_prices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("annee", sa.Integer(), nullable=False),
        sa.Column("profil", sa.String(length=8), nullable=False),
        sa.Column("fourniture_ht_mwh", sa.Float(), nullable=True),
        sa.Column("cee_ht_mwh", sa.Float(), nullable=True),
        sa.Column("cee_precarite_ht_mwh", sa.Float(), nullable=True),
        sa.Column("cpb_ht_mwh", sa.Float(), nullable=True),
        sa.Column("go_ht_mwh", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("city_id", "annee", "profil", name="uq_gas_bpu_city_annee_profil"),
    )
    op.create_index("ix_gas_bpu_prices_city_id", "gas_bpu_prices", ["city_id"])
    op.create_index("ix_gas_bpu_prices_annee", "gas_bpu_prices", ["annee"])

    # Seed BPU lot 7 2026 (identique sur T1-T4) — source BPU_2026_Lots_1_2_et_7.xlsx.
    op.bulk_insert(
        table,
        [
            {
                "city_id": None, "annee": 2026, "profil": profil,
                "fourniture_ht_mwh": 35.23, "cee_ht_mwh": 3.89, "cee_precarite_ht_mwh": 3.06,
                "cpb_ht_mwh": 0.41, "go_ht_mwh": 16.25, "source": "BPU_2026_Lots_1_2_et_7.xlsx",
            }
            for profil in ("T1", "T2", "T3", "T4")
        ],
    )


def downgrade() -> None:
    op.drop_table("gas_bpu_prices")
