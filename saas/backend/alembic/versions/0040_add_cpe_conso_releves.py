"""add cpe_conso_releves (suivi consommations multi-fluides DALKIA)

Revision ID: 0040
Revises: 0039
Create Date: 2026-06-03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cpe_conso_releves",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("cpe_site_id", sa.Integer(), nullable=True),
        sa.Column("code_site", sa.String(length=50), nullable=False),
        sa.Column("contract_code", sa.String(length=80), nullable=True),
        sa.Column("fluide", sa.String(length=12), nullable=False),
        sa.Column("annee", sa.Integer(), nullable=False),
        sa.Column("mois", sa.Integer(), nullable=False),
        sa.Column("consommation", sa.Float(), nullable=True),
        sa.Column("unite", sa.String(length=10), nullable=True),
        sa.Column("energie_mwh", sa.Float(), nullable=True),
        sa.Column("nb_releves", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nb_estimes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("qualite", sa.String(length=12), nullable=False, server_default="reel"),
        sa.Column("source", sa.String(length=30), nullable=False, server_default="csv_dalkia"),
        sa.Column("date_import", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["cpe_site_id"], ["cpe_sites.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_site", "fluide", "annee", "mois", name="uq_cpe_conso_site_fluide_mois"),
    )
    op.create_index("ix_cpe_conso_releves_city_id", "cpe_conso_releves", ["city_id"])
    op.create_index("ix_cpe_conso_releves_cpe_site_id", "cpe_conso_releves", ["cpe_site_id"])
    op.create_index("ix_cpe_conso_releves_code_site", "cpe_conso_releves", ["code_site"])
    op.create_index("ix_cpe_conso_releves_fluide", "cpe_conso_releves", ["fluide"])
    op.create_index("ix_cpe_conso_releves_annee", "cpe_conso_releves", ["annee"])
    op.create_index("ix_cpe_conso_releves_contract_code", "cpe_conso_releves", ["contract_code"])


def downgrade() -> None:
    op.drop_table("cpe_conso_releves")
