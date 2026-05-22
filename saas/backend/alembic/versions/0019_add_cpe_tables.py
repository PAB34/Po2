"""add CPE DALKIA tables

Revision ID: 0019_add_cpe_tables
Revises: 0018_invoice_history
Create Date: 2026-05-22 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0019_add_cpe_tables"
down_revision = "0018_invoice_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cpe_sites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("code_site", sa.String(length=50), nullable=False),
        sa.Column("nom_site", sa.String(length=255), nullable=False),
        sa.Column("categorie", sa.String(length=20), nullable=False),
        sa.Column("nb_mwh_pci", sa.Float(), nullable=False),
        sa.Column("ecs_ref_m3_an", sa.Float(), nullable=False),
        sa.Column("q_ecs_mwh_pci_per_m3", sa.Float(), nullable=True),
        sa.Column("dju_reference", sa.Float(), nullable=False),
        sa.Column("cible_elec_mwh", sa.Float(), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_site"),
    )
    op.create_index("ix_cpe_sites_city_id", "cpe_sites", ["city_id"])
    op.create_index("ix_cpe_sites_code_site", "cpe_sites", ["code_site"])

    op.create_table(
        "cpe_gaz_releves",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cpe_site_id", sa.Integer(), nullable=False),
        sa.Column("annee", sa.Integer(), nullable=False),
        sa.Column("mois", sa.Integer(), nullable=False),
        sa.Column("qt_mwh_pci", sa.Float(), nullable=True),
        sa.Column("volume_ecs_m3", sa.Float(), nullable=True),
        sa.Column("etat_chauffe", sa.Boolean(), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("date_import", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["cpe_site_id"], ["cpe_sites.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cpe_site_id", "annee", "mois", name="uq_cpe_releve_site_mois"),
    )
    op.create_index("ix_cpe_gaz_releves_cpe_site_id", "cpe_gaz_releves", ["cpe_site_id"])

    op.create_table(
        "cpe_prix_gaz",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("annee", sa.Integer(), nullable=False),
        sa.Column("pu_eur_mwh_pci", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("annee", name="uq_cpe_prix_gaz_annee"),
    )

    op.create_table(
        "cpe_resultats_annuels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cpe_site_id", sa.Integer(), nullable=False),
        sa.Column("annee", sa.Integer(), nullable=False),
        sa.Column("dju_reels", sa.Float(), nullable=True),
        sa.Column("dju_reference", sa.Float(), nullable=False),
        sa.Column("nb", sa.Float(), nullable=False),
        sa.Column("n_prime_b", sa.Float(), nullable=True),
        sa.Column("qt_total", sa.Float(), nullable=True),
        sa.Column("m_ecs_total", sa.Float(), nullable=True),
        sa.Column("nc", sa.Float(), nullable=True),
        sa.Column("pu_mwh", sa.Float(), nullable=True),
        sa.Column("ecart", sa.Float(), nullable=True),
        sa.Column("type_resultat", sa.String(length=20), nullable=True),
        sa.Column("montant_ht", sa.Float(), nullable=True),
        sa.Column("p2_4_taux", sa.Float(), nullable=False),
        sa.Column("ecart_pct", sa.Float(), nullable=True),
        sa.Column("alerte_revision_nb", sa.Boolean(), nullable=False),
        sa.Column("statut", sa.String(length=20), nullable=False),
        sa.Column("nb_mois_renseignes", sa.Integer(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cpe_site_id"], ["cpe_sites.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cpe_site_id", "annee", name="uq_cpe_resultat_site_annee"),
    )
    op.create_index("ix_cpe_resultats_annuels_cpe_site_id", "cpe_resultats_annuels", ["cpe_site_id"])


def downgrade() -> None:
    op.drop_table("cpe_resultats_annuels")
    op.drop_table("cpe_prix_gaz")
    op.drop_table("cpe_gaz_releves")
    op.drop_index("ix_cpe_sites_code_site", table_name="cpe_sites")
    op.drop_index("ix_cpe_sites_city_id", table_name="cpe_sites")
    op.drop_table("cpe_sites")
