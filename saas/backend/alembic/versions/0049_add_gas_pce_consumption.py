"""add gas_pces + gas_consumptions (GRDF ADICT — gaz distributeur)

Revision ID: 0049
Revises: 0048
Create Date: 2026-06-09
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gas_pces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("building_id", sa.Integer(), nullable=True),
        sa.Column("id_pce", sa.String(length=20), nullable=False),
        sa.Column("nom_site", sa.String(length=255), nullable=True),
        sa.Column("role_tiers", sa.String(length=40), nullable=False, server_default="AUTORISE_CONTRAT_FOURNITURE"),
        sa.Column("nom_titulaire", sa.String(length=255), nullable=True),
        sa.Column("code_postal", sa.String(length=10), nullable=True),
        sa.Column("courriel_titulaire", sa.String(length=255), nullable=True),
        sa.Column("id_droit_acces", sa.String(length=80), nullable=True),
        sa.Column("etat_droit_acces", sa.String(length=30), nullable=True),
        sa.Column("date_debut_droit_acces", sa.Date(), nullable=True),
        sa.Column("date_fin_droit_acces", sa.Date(), nullable=True),
        sa.Column("perim_publiees", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("perim_informatives", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("perim_contractuelles", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("perim_techniques", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tarif_acheminement", sa.String(length=8), nullable=True),
        sa.Column("car_actuelle", sa.Integer(), nullable=True),
        sa.Column("profil_type", sa.String(length=8), nullable=True),
        sa.Column("frequence_releve", sa.String(length=4), nullable=True),
        sa.Column("code_calibre", sa.String(length=8), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("city_id", "id_pce", name="uq_gas_pce_city_pce"),
    )
    op.create_index("ix_gas_pces_city_id", "gas_pces", ["city_id"])
    op.create_index("ix_gas_pces_building_id", "gas_pces", ["building_id"])
    op.create_index("ix_gas_pces_id_pce", "gas_pces", ["id_pce"])
    op.create_index("ix_gas_pces_etat_droit_acces", "gas_pces", ["etat_droit_acces"])

    op.create_table(
        "gas_consumptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pce_id", sa.Integer(), nullable=False),
        sa.Column("date_debut", sa.Date(), nullable=False),
        sa.Column("date_fin", sa.Date(), nullable=False),
        sa.Column("energie_kwh", sa.Integer(), nullable=True),
        sa.Column("volume_brut_m3", sa.Integer(), nullable=True),
        sa.Column("volume_converti_m3", sa.Integer(), nullable=True),
        sa.Column("coeff_conversion", sa.Float(), nullable=True),
        sa.Column("statut_conso", sa.String(length=20), nullable=True),
        sa.Column("type_conso", sa.String(length=40), nullable=False, server_default="Publiée"),
        sa.Column("type_qualif", sa.String(length=20), nullable=True),
        sa.Column("journee_gaziere", sa.Date(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["pce_id"], ["gas_pces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pce_id", "date_debut", "type_conso", name="uq_gas_conso_pce_debut_type"),
    )
    op.create_index("ix_gas_consumptions_pce_id", "gas_consumptions", ["pce_id"])
    op.create_index("ix_gas_consumptions_date_debut", "gas_consumptions", ["date_debut"])


def downgrade() -> None:
    op.drop_index("ix_gas_consumptions_date_debut", table_name="gas_consumptions")
    op.drop_index("ix_gas_consumptions_pce_id", table_name="gas_consumptions")
    op.drop_table("gas_consumptions")
    op.drop_index("ix_gas_pces_etat_droit_acces", table_name="gas_pces")
    op.drop_index("ix_gas_pces_id_pce", table_name="gas_pces")
    op.drop_index("ix_gas_pces_building_id", table_name="gas_pces")
    op.drop_index("ix_gas_pces_city_id", table_name="gas_pces")
    op.drop_table("gas_pces")
