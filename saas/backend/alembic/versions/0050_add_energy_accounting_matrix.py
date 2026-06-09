"""add energy_accounting_site_mappings + energy_accounting_nature_rules (matrice comptable ENGIE)

Revision ID: 0050
Revises: 0049
Create Date: 2026-06-09
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0050"
down_revision = "0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "energy_accounting_site_mappings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("prm_id", sa.String(length=40), nullable=False),
        sa.Column("site_name", sa.String(length=255), nullable=True),
        sa.Column("regroupement", sa.String(length=120), nullable=True),
        sa.Column("family", sa.String(length=120), nullable=True),
        sa.Column("manager", sa.String(length=120), nullable=True),
        sa.Column("alternate_manager", sa.String(length=120), nullable=True),
        sa.Column("service_code", sa.String(length=40), nullable=True),
        sa.Column("service_label", sa.String(length=255), nullable=True),
        sa.Column("function_code", sa.String(length=40), nullable=True),
        sa.Column("function_label", sa.String(length=255), nullable=True),
        sa.Column("antenna_code", sa.String(length=80), nullable=True),
        sa.Column("antenna_label", sa.String(length=255), nullable=True),
        sa.Column("operation_code", sa.String(length=80), nullable=True),
        sa.Column("operation_label", sa.String(length=255), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("city_id", "prm_id", name="uq_energy_accounting_site_city_prm"),
    )
    op.create_index("ix_energy_accounting_site_mappings_city_id", "energy_accounting_site_mappings", ["city_id"])
    op.create_index("ix_energy_accounting_site_mappings_prm_id", "energy_accounting_site_mappings", ["prm_id"])

    op.create_table(
        "energy_accounting_nature_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("supplier", sa.String(length=100), nullable=False, server_default="ENGIE"),
        sa.Column("market", sa.String(length=40), nullable=True),
        sa.Column("billed_item", sa.String(length=160), nullable=False),
        sa.Column("frequency", sa.String(length=40), nullable=True),
        sa.Column("accounting_nature", sa.String(length=40), nullable=False),
        sa.Column("accounting_label", sa.String(length=255), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "city_id", "supplier", "market", "billed_item", "frequency",
            name="uq_energy_accounting_rule_key",
        ),
    )
    op.create_index("ix_energy_accounting_nature_rules_city_id", "energy_accounting_nature_rules", ["city_id"])
    op.create_index("ix_energy_accounting_nature_rules_supplier", "energy_accounting_nature_rules", ["supplier"])
    op.create_index("ix_energy_accounting_nature_rules_billed_item", "energy_accounting_nature_rules", ["billed_item"])
    op.create_index("ix_energy_accounting_nature_rules_accounting_nature", "energy_accounting_nature_rules", ["accounting_nature"])


def downgrade() -> None:
    op.drop_table("energy_accounting_nature_rules")
    op.drop_table("energy_accounting_site_mappings")
