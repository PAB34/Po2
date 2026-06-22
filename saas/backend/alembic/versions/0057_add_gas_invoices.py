"""add gas_invoices (factures gaz TotalEnergies)

Revision ID: 0057
Revises: 0056
Create Date: 2026-06-22
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0057"
down_revision = "0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gas_invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("building_id", sa.Integer(), nullable=True),
        sa.Column("import_batch", sa.String(length=60), nullable=True),
        sa.Column("num_facture", sa.String(length=40), nullable=False),
        sa.Column("type_detail", sa.String(length=20), nullable=True),
        sa.Column("date_comptable", sa.Date(), nullable=True),
        sa.Column("date_echeance", sa.Date(), nullable=True),
        sa.Column("ref_site", sa.String(length=40), nullable=True),
        sa.Column("pce", sa.String(length=20), nullable=False),
        sa.Column("nom_site", sa.String(length=255), nullable=True),
        sa.Column("lib_regroupement", sa.String(length=255), nullable=True),
        sa.Column("code_interne", sa.String(length=40), nullable=True),
        sa.Column("adresse", sa.String(length=255), nullable=True),
        sa.Column("code_postal", sa.String(length=10), nullable=True),
        sa.Column("ville", sa.String(length=120), nullable=True),
        sa.Column("classe_conso", sa.String(length=8), nullable=True),
        sa.Column("tarif_acheminement", sa.String(length=8), nullable=True),
        sa.Column("profil_consommation", sa.String(length=8), nullable=True),
        sa.Column("car_acheminement", sa.Integer(), nullable=True),
        sa.Column("car_conso", sa.Integer(), nullable=True),
        sa.Column("coeff_conversion", sa.Float(), nullable=True),
        sa.Column("matricule_compteur", sa.String(length=40), nullable=True),
        sa.Column("debut_conso", sa.Date(), nullable=True),
        sa.Column("fin_conso", sa.Date(), nullable=True),
        sa.Column("prix_conso_gaz", sa.Float(), nullable=True),
        sa.Column("montant_conso_gaz", sa.Float(), nullable=True),
        sa.Column("abonnement_fournisseur", sa.Float(), nullable=True),
        sa.Column("montant_cee", sa.Float(), nullable=True),
        sa.Column("montant_cee_precarite", sa.Float(), nullable=True),
        sa.Column("montant_cpb", sa.Float(), nullable=True),
        sa.Column("montant_indexation", sa.Float(), nullable=True),
        sa.Column("atrt_terme_fixe", sa.Float(), nullable=True),
        sa.Column("atrd_terme_fixe", sa.Float(), nullable=True),
        sa.Column("atrd_terme_variable", sa.Float(), nullable=True),
        sa.Column("montant_autres", sa.Float(), nullable=True),
        sa.Column("montant_ticgn", sa.Float(), nullable=True),
        sa.Column("montant_cta", sa.Float(), nullable=True),
        sa.Column("total_hors_tva", sa.Float(), nullable=True),
        sa.Column("assiette_tva_tn", sa.Float(), nullable=True),
        sa.Column("tva_tn", sa.Float(), nullable=True),
        sa.Column("assiette_tva_tr", sa.Float(), nullable=True),
        sa.Column("tva_tr", sa.Float(), nullable=True),
        sa.Column("total_ttc", sa.Float(), nullable=True),
        sa.Column("total_conso_kwh", sa.Integer(), nullable=True),
        sa.Column("total_conso_m3", sa.Integer(), nullable=True),
        sa.Column("index_reel", sa.String(length=40), nullable=True),
        sa.Column("type_releve", sa.String(length=60), nullable=True),
        sa.Column("derniere_releve_reelle", sa.Date(), nullable=True),
        sa.Column("control_status", sa.String(length=20), nullable=False, server_default="not_checked"),
        sa.Column("control_issues_json", sa.Text(), nullable=True),
        sa.Column("decision_status", sa.String(length=20), nullable=False, server_default="to_review"),
        sa.Column("decision_comment", sa.Text(), nullable=True),
        sa.Column("finance_exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("city_id", "num_facture", name="uq_gas_invoice_city_num"),
    )
    op.create_index("ix_gas_invoices_city_id", "gas_invoices", ["city_id"])
    op.create_index("ix_gas_invoices_building_id", "gas_invoices", ["building_id"])
    op.create_index("ix_gas_invoices_import_batch", "gas_invoices", ["import_batch"])
    op.create_index("ix_gas_invoices_num_facture", "gas_invoices", ["num_facture"])
    op.create_index("ix_gas_invoices_pce", "gas_invoices", ["pce"])


def downgrade() -> None:
    op.drop_table("gas_invoices")
