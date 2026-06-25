"""add accounting matrices versionnées (contrats, versions, règles, snapshots facture)

Cf. docs/38-Modele-backend-matrices-comptables-versionnees.md

Revision ID: 0064
Revises: 0063
Create Date: 2026-06-25
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0064"
down_revision = "0063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounting_matrix_contracts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("domain", sa.String(length=40), nullable=False),
        sa.Column("supplier", sa.String(length=100), nullable=False),
        sa.Column("contract_code", sa.String(length=120), nullable=True),
        sa.Column("contract_label", sa.String(length=255), nullable=True),
        sa.Column("lot_label", sa.String(length=120), nullable=True),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("contact_name", sa.String(length=255), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "city_id", "domain", "supplier", "contract_code", "lot_label",
            name="uq_accounting_matrix_contract_key",
        ),
    )
    op.create_index("ix_accounting_matrix_contracts_city_id", "accounting_matrix_contracts", ["city_id"])
    op.create_index("ix_accounting_matrix_contracts_domain", "accounting_matrix_contracts", ["domain"])
    op.create_index("ix_accounting_matrix_contracts_supplier", "accounting_matrix_contracts", ["supplier"])
    op.create_index("ix_accounting_matrix_contracts_contract_code", "accounting_matrix_contracts", ["contract_code"])
    op.create_index("ix_accounting_matrix_contracts_status", "accounting_matrix_contracts", ["status"])

    op.create_table(
        "accounting_matrix_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("matrix_contract_id", sa.Integer(), nullable=False),
        sa.Column("version_label", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="manuel"),
        sa.Column("source_filename", sa.String(length=255), nullable=True),
        sa.Column("source_sha256", sa.String(length=64), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("validated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("change_summary_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["matrix_contract_id"], ["accounting_matrix_contracts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accounting_matrix_versions_contract", "accounting_matrix_versions", ["matrix_contract_id"])
    op.create_index("ix_accounting_matrix_versions_status", "accounting_matrix_versions", ["status"])

    op.create_table(
        "accounting_matrix_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("matrix_version_id", sa.Integer(), nullable=False),
        sa.Column("stable_rule_key", sa.String(length=120), nullable=False),
        sa.Column("scope", sa.String(length=30), nullable=False, server_default="billed_item"),
        sa.Column("site_code", sa.String(length=80), nullable=True),
        sa.Column("building_id", sa.Integer(), nullable=True),
        sa.Column("meter_id", sa.String(length=40), nullable=True),
        sa.Column("billed_item_pattern", sa.String(length=255), nullable=True),
        sa.Column("supplier_item_code", sa.String(length=120), nullable=True),
        sa.Column("accounting_service", sa.String(length=120), nullable=True),
        sa.Column("accounting_function", sa.String(length=120), nullable=True),
        sa.Column("accounting_antenna", sa.String(length=120), nullable=True),
        sa.Column("operation_number", sa.String(length=80), nullable=True),
        sa.Column("accounting_nature", sa.String(length=40), nullable=True),
        sa.Column("accounting_label", sa.String(length=255), nullable=True),
        sa.Column("allocation_percent", sa.Float(), nullable=False, server_default="100"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["matrix_version_id"], ["accounting_matrix_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("matrix_version_id", "stable_rule_key", name="uq_accounting_matrix_rule_stable_key"),
    )
    op.create_index("ix_accounting_matrix_rules_version", "accounting_matrix_rules", ["matrix_version_id"])
    op.create_index("ix_accounting_matrix_rules_stable_key", "accounting_matrix_rules", ["stable_rule_key"])
    op.create_index("ix_accounting_matrix_rules_site_code", "accounting_matrix_rules", ["site_code"])
    op.create_index("ix_accounting_matrix_rules_meter_id", "accounting_matrix_rules", ["meter_id"])
    op.create_index("ix_accounting_matrix_rules_accounting_nature", "accounting_matrix_rules", ["accounting_nature"])

    op.create_table(
        "invoice_accounting_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("invoice_source", sa.String(length=40), nullable=False),
        sa.Column("invoice_id", sa.String(length=80), nullable=False),
        sa.Column("matrix_contract_id", sa.Integer(), nullable=True),
        sa.Column("matrix_version_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="proposed"),
        sa.Column("snapshot_json", sa.Text(), nullable=True),
        sa.Column("exceptions_json", sa.Text(), nullable=True),
        sa.Column("validated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["matrix_contract_id"], ["accounting_matrix_contracts.id"]),
        sa.ForeignKeyConstraint(["matrix_version_id"], ["accounting_matrix_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "city_id", "invoice_source", "invoice_id",
            name="uq_invoice_accounting_snapshot_invoice",
        ),
    )
    op.create_index("ix_invoice_accounting_snapshots_city_id", "invoice_accounting_snapshots", ["city_id"])
    op.create_index("ix_invoice_accounting_snapshots_source", "invoice_accounting_snapshots", ["invoice_source"])
    op.create_index("ix_invoice_accounting_snapshots_invoice_id", "invoice_accounting_snapshots", ["invoice_id"])
    op.create_index("ix_invoice_accounting_snapshots_status", "invoice_accounting_snapshots", ["status"])


def downgrade() -> None:
    op.drop_table("invoice_accounting_snapshots")
    op.drop_table("accounting_matrix_rules")
    op.drop_table("accounting_matrix_versions")
    op.drop_table("accounting_matrix_contracts")
