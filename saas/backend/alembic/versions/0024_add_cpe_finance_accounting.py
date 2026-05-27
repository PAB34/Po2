"""add cpe finance accounting tables

Revision ID: 0024
Revises: 0023
Create Date: 2026-05-27
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cpe_accounting_nature_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=True),
        sa.Column("market", sa.String(length=30), nullable=False),
        sa.Column("service_sold", sa.String(length=120), nullable=True),
        sa.Column("billed_item", sa.String(length=120), nullable=False),
        sa.Column("frequency", sa.String(length=40), nullable=True),
        sa.Column("accounting_nature", sa.String(length=30), nullable=False),
        sa.Column("accounting_label", sa.String(length=255), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "city_id",
            "market",
            "service_sold",
            "billed_item",
            "frequency",
            name="uq_cpe_accounting_rule_key",
        ),
    )
    op.create_index("ix_cpe_accounting_nature_rules_city_id", "cpe_accounting_nature_rules", ["city_id"])
    op.create_index("ix_cpe_accounting_nature_rules_market", "cpe_accounting_nature_rules", ["market"])
    op.create_index("ix_cpe_accounting_nature_rules_billed_item", "cpe_accounting_nature_rules", ["billed_item"])
    op.create_index(
        "ix_cpe_accounting_nature_rules_accounting_nature",
        "cpe_accounting_nature_rules",
        ["accounting_nature"],
    )

    op.create_table(
        "cpe_accounting_site_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=True),
        sa.Column("code_site", sa.String(length=80), nullable=False),
        sa.Column("site_name", sa.String(length=255), nullable=False),
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
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("city_id", "code_site", name="uq_cpe_accounting_site_city_code"),
    )
    op.create_index("ix_cpe_accounting_site_mappings_city_id", "cpe_accounting_site_mappings", ["city_id"])
    op.create_index("ix_cpe_accounting_site_mappings_code_site", "cpe_accounting_site_mappings", ["code_site"])

    op.create_table(
        "cpe_finance_import_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="dalkia_finance_export"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="imported"),
        sa.Column("line_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invoice_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_ht", sa.Float(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_cpe_finance_import_batches_city_id", "cpe_finance_import_batches", ["city_id"])

    op.create_table(
        "cpe_finance_invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("cpe_finance_import_batches.id"), nullable=False),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=True),
        sa.Column("invoice_number", sa.String(length=80), nullable=False),
        sa.Column("contract_code", sa.String(length=80), nullable=True),
        sa.Column("contract_label", sa.String(length=255), nullable=True),
        sa.Column("invoice_type", sa.String(length=80), nullable=True),
        sa.Column("supplier", sa.String(length=120), nullable=True),
        sa.Column("customer_code", sa.String(length=80), nullable=True),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("total_ht", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="a_controler"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("batch_id", "invoice_number", name="uq_cpe_finance_invoice_batch_number"),
    )
    op.create_index("ix_cpe_finance_invoices_batch_id", "cpe_finance_invoices", ["batch_id"])
    op.create_index("ix_cpe_finance_invoices_city_id", "cpe_finance_invoices", ["city_id"])
    op.create_index("ix_cpe_finance_invoices_invoice_number", "cpe_finance_invoices", ["invoice_number"])
    op.create_index("ix_cpe_finance_invoices_contract_code", "cpe_finance_invoices", ["contract_code"])

    op.create_table(
        "cpe_finance_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("cpe_finance_import_batches.id"), nullable=False),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("cpe_finance_invoices.id"), nullable=False),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=True),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("contract_code", sa.String(length=80), nullable=True),
        sa.Column("invoice_number", sa.String(length=80), nullable=True),
        sa.Column("market", sa.String(length=30), nullable=True),
        sa.Column("market_type", sa.String(length=80), nullable=True),
        sa.Column("service_sold", sa.String(length=120), nullable=True),
        sa.Column("billed_item", sa.String(length=120), nullable=True),
        sa.Column("vat_rate", sa.Float(), nullable=True),
        sa.Column("amount_ht", sa.Float(), nullable=False, server_default="0"),
        sa.Column("consumption", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("site_code_detected", sa.String(length=80), nullable=True),
        sa.Column("accounting_site_id", sa.Integer(), sa.ForeignKey("cpe_accounting_site_mappings.id"), nullable=True),
        sa.Column("accounting_rule_id", sa.Integer(), sa.ForeignKey("cpe_accounting_nature_rules.id"), nullable=True),
        sa.Column("accounting_nature", sa.String(length=30), nullable=True),
        sa.Column("accounting_label", sa.String(length=255), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=True),
    )
    op.create_index("ix_cpe_finance_lines_batch_id", "cpe_finance_lines", ["batch_id"])
    op.create_index("ix_cpe_finance_lines_invoice_id", "cpe_finance_lines", ["invoice_id"])
    op.create_index("ix_cpe_finance_lines_city_id", "cpe_finance_lines", ["city_id"])
    op.create_index("ix_cpe_finance_lines_invoice_number", "cpe_finance_lines", ["invoice_number"])
    op.create_index("ix_cpe_finance_lines_market", "cpe_finance_lines", ["market"])
    op.create_index("ix_cpe_finance_lines_billed_item", "cpe_finance_lines", ["billed_item"])
    op.create_index("ix_cpe_finance_lines_site_code_detected", "cpe_finance_lines", ["site_code_detected"])
    op.create_index("ix_cpe_finance_lines_accounting_site_id", "cpe_finance_lines", ["accounting_site_id"])
    op.create_index("ix_cpe_finance_lines_accounting_rule_id", "cpe_finance_lines", ["accounting_rule_id"])


def downgrade() -> None:
    op.drop_table("cpe_finance_lines")
    op.drop_table("cpe_finance_invoices")
    op.drop_table("cpe_finance_import_batches")
    op.drop_table("cpe_accounting_site_mappings")
    op.drop_table("cpe_accounting_nature_rules")
