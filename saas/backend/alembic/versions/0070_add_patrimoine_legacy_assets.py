"""add patrimoine legacy (ASTECH) imports and assets

Référentiel patrimoine historique de la collectivité, en aller-retour avec ASTECH :
export ASTECH -> import Po2 -> rapprochement / attribution IGN -> réexport réinjectable.

`patrimoine_legacy_imports` conserve le gabarit du fichier (feuille, ligne d'en-têtes,
en-têtes à l'octet près) : ASTECH ne réimporte que si les en-têtes et le code bien sont
strictement inchangés.

`patrimoine_legacy_assets` porte un bien par `CODE_BIEN` (clé pivot permanente), avec le
payload d'origine conservé pour le réexport. Relation N codes bien -> 1 bâtiment.

Revision ID: 0070
Revises: 0069
Create Date: 2026-08-18
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0070"
down_revision = "0069"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patrimoine_legacy_imports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("batch", sa.String(length=120), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("sheet_name", sa.String(length=120), nullable=False),
        sa.Column("header_row", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("headers_json", sa.Text(), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("imported_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("city_id", "batch", name="uq_legacy_import_city_batch"),
    )
    op.create_index("ix_patrimoine_legacy_imports_city_id", "patrimoine_legacy_imports", ["city_id"])
    op.create_index("ix_patrimoine_legacy_imports_batch", "patrimoine_legacy_imports", ["batch"])

    op.create_table(
        "patrimoine_legacy_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("code_bien", sa.String(length=40), nullable=False),
        sa.Column("designation", sa.String(length=255), nullable=True),
        sa.Column("nomcourt", sa.String(length=255), nullable=True),
        sa.Column("genre", sa.String(length=20), nullable=True),
        sa.Column("categ", sa.String(length=20), nullable=True),
        sa.Column("categ_des", sa.String(length=120), nullable=True),
        sa.Column("souscat_des", sa.String(length=120), nullable=True),
        sa.Column("horsparc", sa.String(length=2), nullable=True),
        sa.Column("code_parent", sa.String(length=40), nullable=True),
        sa.Column("source_norue", sa.String(length=40), nullable=True),
        sa.Column("source_bister", sa.String(length=40), nullable=True),
        sa.Column("source_libelvoie", sa.String(length=255), nullable=True),
        sa.Column("source_codpost", sa.String(length=10), nullable=True),
        sa.Column("source_ville", sa.String(length=120), nullable=True),
        sa.Column("source_commune", sa.String(length=10), nullable=True),
        sa.Column("source_refcad", sa.String(length=40), nullable=True),
        sa.Column("building_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="a_traiter"),
        sa.Column("link_origin", sa.String(length=20), nullable=True),
        sa.Column("candidate_building_id", sa.Integer(), nullable=True),
        sa.Column("candidate_label", sa.String(length=255), nullable=True),
        sa.Column("candidate_score", sa.Float(), nullable=True),
        sa.Column("candidate_reason", sa.String(length=255), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("import_batch", sa.String(length=120), nullable=True),
        sa.Column("source_row_number", sa.Integer(), nullable=True),
        sa.Column("source_payload_json", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("city_id", "code_bien", name="uq_legacy_asset_city_code"),
    )
    for column in ("city_id", "code_bien", "genre", "horsparc", "code_parent", "source_commune", "building_id", "status", "import_batch"):
        op.create_index(f"ix_patrimoine_legacy_assets_{column}", "patrimoine_legacy_assets", [column])


def downgrade() -> None:
    op.drop_table("patrimoine_legacy_assets")
    op.drop_table("patrimoine_legacy_imports")
