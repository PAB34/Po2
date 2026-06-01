"""add cpe dalkia reference tables

Revision ID: 0033
Revises: 0032
Create Date: 2026-06-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cpe_dalkia_ref_imports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("lot", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("import_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("nb_sites", sa.Integer(), nullable=False, default=0),
        sa.Column("nb_p2p3_rows", sa.Integer(), nullable=False, default=0),
        sa.Column("nb_cibles_rows", sa.Integer(), nullable=False, default=0),
        sa.Column("nb_p1_gaz_rows", sa.Integer(), nullable=False, default=0),
        sa.Column("nb_ape_rows", sa.Integer(), nullable=False, default=0),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cpe_dalkia_ref_imports_city_id", "cpe_dalkia_ref_imports", ["city_id"])

    op.create_table(
        "cpe_dalkia_ref_sites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("import_id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("lot", sa.Integer(), nullable=False),
        sa.Column("code_site", sa.String(length=40), nullable=False),
        sa.Column("nom_batiment", sa.String(length=255), nullable=False),
        sa.Column("entite", sa.String(length=80), nullable=True),
        sa.Column("lot_label", sa.String(length=40), nullable=True),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["import_id"], ["cpe_dalkia_ref_imports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("import_id", "code_site", name="uq_dalkia_site_per_import"),
    )
    op.create_index("ix_cpe_dalkia_ref_sites_import_id", "cpe_dalkia_ref_sites", ["import_id"])
    op.create_index("ix_cpe_dalkia_ref_sites_city_id", "cpe_dalkia_ref_sites", ["city_id"])
    op.create_index("ix_cpe_dalkia_ref_sites_code_site", "cpe_dalkia_ref_sites", ["code_site"])

    op.create_table(
        "cpe_dalkia_ref_p2p3",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("import_id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("code_site", sa.String(length=40), nullable=False),
        sa.Column("period_idx", sa.Integer(), nullable=False),
        sa.Column("period_label", sa.String(length=80), nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("p2_1_ht", sa.Float(), nullable=True),
        sa.Column("p2_2_ht", sa.Float(), nullable=True),
        sa.Column("p2_3_ht", sa.Float(), nullable=True),
        sa.Column("p2_4_ht", sa.Float(), nullable=True),
        sa.Column("p2_total_ht", sa.Float(), nullable=True),
        sa.Column("p3_1_ht", sa.Float(), nullable=True),
        sa.Column("p3_2_ht", sa.Float(), nullable=True),
        sa.Column("p3_3_ht", sa.Float(), nullable=True),
        sa.Column("p3_4_ht", sa.Float(), nullable=True),
        sa.Column("p3_total_ht", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["import_id"], ["cpe_dalkia_ref_imports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("import_id", "code_site", "period_idx", name="uq_dalkia_p2p3"),
    )
    op.create_index("ix_cpe_dalkia_ref_p2p3_import_id", "cpe_dalkia_ref_p2p3", ["import_id"])
    op.create_index("ix_cpe_dalkia_ref_p2p3_code_site", "cpe_dalkia_ref_p2p3", ["code_site"])
    op.create_index("ix_cpe_dalkia_ref_p2p3_period_year", "cpe_dalkia_ref_p2p3", ["period_year"])

    op.create_table(
        "cpe_dalkia_ref_cibles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("import_id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("code_site", sa.String(length=40), nullable=False),
        sa.Column("fluid", sa.String(length=10), nullable=False),
        sa.Column("period_idx", sa.Integer(), nullable=False),
        sa.Column("period_label", sa.String(length=80), nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("ref_globale_mwhpci", sa.Float(), nullable=True),
        sa.Column("ref_qt_mwhpci", sa.Float(), nullable=True),
        sa.Column("dju_reference", sa.Float(), nullable=True),
        sa.Column("qt_global_mwhpci", sa.Float(), nullable=True),
        sa.Column("nb_mwhpci", sa.Float(), nullable=True),
        sa.Column("q_ecs", sa.Float(), nullable=True),
        sa.Column("qt_ecs", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["import_id"], ["cpe_dalkia_ref_imports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("import_id", "code_site", "fluid", "period_idx", name="uq_dalkia_cible"),
    )
    op.create_index("ix_cpe_dalkia_ref_cibles_import_id", "cpe_dalkia_ref_cibles", ["import_id"])
    op.create_index("ix_cpe_dalkia_ref_cibles_code_site", "cpe_dalkia_ref_cibles", ["code_site"])
    op.create_index("ix_cpe_dalkia_ref_cibles_period_year", "cpe_dalkia_ref_cibles", ["period_year"])

    op.create_table(
        "cpe_dalkia_ref_p1_gaz",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("import_id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("code_site", sa.String(length=40), nullable=False),
        sa.Column("pce", sa.String(length=30), nullable=True),
        sa.Column("type_tarif", sa.String(length=10), nullable=True),
        sa.Column("prix_unitaire_ht", sa.Float(), nullable=True),
        sa.Column("atrd_ht", sa.Float(), nullable=True),
        sa.Column("cta_ht", sa.Float(), nullable=True),
        sa.Column("p10_fixe_ht", sa.Float(), nullable=True),
        sa.Column("period_idx", sa.Integer(), nullable=False),
        sa.Column("period_label", sa.String(length=80), nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("qt_mwhpcs", sa.Float(), nullable=True),
        sa.Column("p10_var_ht", sa.Float(), nullable=True),
        sa.Column("p10_total_ht", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["import_id"], ["cpe_dalkia_ref_imports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("import_id", "code_site", "period_idx", name="uq_dalkia_p1_gaz"),
    )
    op.create_index("ix_cpe_dalkia_ref_p1_gaz_import_id", "cpe_dalkia_ref_p1_gaz", ["import_id"])
    op.create_index("ix_cpe_dalkia_ref_p1_gaz_code_site", "cpe_dalkia_ref_p1_gaz", ["code_site"])
    op.create_index("ix_cpe_dalkia_ref_p1_gaz_period_year", "cpe_dalkia_ref_p1_gaz", ["period_year"])

    op.create_table(
        "cpe_dalkia_ref_ape",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("import_id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("code_site", sa.String(length=40), nullable=False),
        sa.Column("nom_batiment", sa.String(length=255), nullable=True),
        sa.Column("situation_initiale_mwhpci", sa.Float(), nullable=True),
        sa.Column("description_ape", sa.Text(), nullable=True),
        sa.Column("annee_achevement", sa.Integer(), nullable=True),
        sa.Column("montant_ape_ht", sa.Float(), nullable=True),
        sa.Column("cee_mwh_cumac", sa.Float(), nullable=True),
        sa.Column("cee_eur", sa.Float(), nullable=True),
        sa.Column("subvention_ht", sa.Float(), nullable=True),
        sa.Column("gain_energetique_mwhpci", sa.Float(), nullable=True),
        sa.Column("situation_nouvelle_mwhpci", sa.Float(), nullable=True),
        sa.Column("annee_engagement_nouvelle_cible", sa.Integer(), nullable=True),
        sa.Column("emission_co2_evitee", sa.Float(), nullable=True),
        sa.Column("production_enr_auto_mwh", sa.Float(), nullable=True),
        sa.Column("production_enr_vendue_mwh", sa.Float(), nullable=True),
        sa.Column("recette_vente_energie_ht", sa.Float(), nullable=True),
        sa.Column("ratio_ht_mwhpci", sa.Float(), nullable=True),
        sa.Column("commentaires", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["import_id"], ["cpe_dalkia_ref_imports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cpe_dalkia_ref_ape_import_id", "cpe_dalkia_ref_ape", ["import_id"])
    op.create_index("ix_cpe_dalkia_ref_ape_code_site", "cpe_dalkia_ref_ape", ["code_site"])


def downgrade() -> None:
    op.drop_table("cpe_dalkia_ref_ape")
    op.drop_table("cpe_dalkia_ref_p1_gaz")
    op.drop_table("cpe_dalkia_ref_cibles")
    op.drop_table("cpe_dalkia_ref_p2p3")
    op.drop_table("cpe_dalkia_ref_sites")
    op.drop_table("cpe_dalkia_ref_imports")
