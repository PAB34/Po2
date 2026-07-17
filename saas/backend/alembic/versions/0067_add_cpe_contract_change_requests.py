"""add cpe contract change requests

Revision ID: 0067
Revises: 0066
Create Date: 2026-07-16
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0067"
down_revision = "0066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cpe_contract_change_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("baseline_import_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("change_type", sa.String(length=30), nullable=False, server_default="mixed"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="draft"),
        sa.Column("lot", sa.Integer(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("requester_name", sa.String(length=160), nullable=True),
        sa.Column("dalkia_contact_email", sa.String(length=255), nullable=True),
        sa.Column("os_number", sa.String(length=80), nullable=True),
        sa.Column("avenant_number", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["baseline_import_id"], ["cpe_dalkia_ref_imports.id"]),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cpe_contract_change_requests_city_id", "cpe_contract_change_requests", ["city_id"])
    op.create_index("ix_cpe_contract_change_requests_created_by_user_id", "cpe_contract_change_requests", ["created_by_user_id"])
    op.create_index("ix_cpe_contract_change_requests_baseline_import_id", "cpe_contract_change_requests", ["baseline_import_id"])
    op.create_index("ix_cpe_contract_change_requests_lot", "cpe_contract_change_requests", ["lot"])

    op.create_table(
        "cpe_contract_change_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("code_site", sa.String(length=50), nullable=True),
        sa.Column("site_name", sa.String(length=255), nullable=False),
        sa.Column("lot", sa.Integer(), nullable=True),
        sa.Column("pce", sa.String(length=50), nullable=True),
        sa.Column("tarif", sa.String(length=10), nullable=True),
        sa.Column("current_p1_gaz_annual_ht", sa.Float(), nullable=True),
        sa.Column("current_p1_elec_annual_ht", sa.Float(), nullable=True),
        sa.Column("current_p2_annual_ht", sa.Float(), nullable=True),
        sa.Column("current_p3_annual_ht", sa.Float(), nullable=True),
        sa.Column("p1_gaz_annual_ht", sa.Float(), nullable=True),
        sa.Column("p1_elec_annual_ht", sa.Float(), nullable=True),
        sa.Column("p2_annual_ht", sa.Float(), nullable=True),
        sa.Column("p3_annual_ht", sa.Float(), nullable=True),
        sa.Column("nb_mwh_pci", sa.Float(), nullable=True),
        sa.Column("cible_elec_mwh", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["request_id"], ["cpe_contract_change_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cpe_contract_change_lines_request_id", "cpe_contract_change_lines", ["request_id"])
    op.create_index("ix_cpe_contract_change_lines_city_id", "cpe_contract_change_lines", ["city_id"])
    op.create_index("ix_cpe_contract_change_lines_code_site", "cpe_contract_change_lines", ["code_site"])
    op.create_index("ix_cpe_contract_change_lines_lot", "cpe_contract_change_lines", ["lot"])


def downgrade() -> None:
    op.drop_table("cpe_contract_change_lines")
    op.drop_table("cpe_contract_change_requests")