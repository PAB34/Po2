"""add invoice batches and normalized history

Revision ID: 0018_invoice_history
Revises: 0017_add_sites_hierarchy
Create Date: 2026-05-21 11:10:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0018_invoice_history"
down_revision = "0017_add_sites_hierarchy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "energy_invoice_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False),
        sa.Column("imported_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("ignored_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_energy_invoice_batches_city_id"), "energy_invoice_batches", ["city_id"], unique=False)
    op.create_index(
        op.f("ix_energy_invoice_batches_uploaded_by_user_id"),
        "energy_invoice_batches",
        ["uploaded_by_user_id"],
        unique=False,
    )

    op.create_table(
        "energy_invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("import_id", sa.Integer(), nullable=False),
        sa.Column("supplier", sa.String(length=120), nullable=True),
        sa.Column("invoice_type", sa.String(length=120), nullable=True),
        sa.Column("invoice_number", sa.String(length=120), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("payment_due_date", sa.Date(), nullable=True),
        sa.Column("payment_method", sa.String(length=120), nullable=True),
        sa.Column("global_customer_reference", sa.String(length=120), nullable=True),
        sa.Column("contract_holder", sa.String(length=255), nullable=True),
        sa.Column("contract_siret", sa.String(length=80), nullable=True),
        sa.Column("market_reference", sa.String(length=120), nullable=True),
        sa.Column("regroupement", sa.String(length=120), nullable=True),
        sa.Column("chorus_ej", sa.String(length=120), nullable=True),
        sa.Column("chorus_service_code", sa.String(length=120), nullable=True),
        sa.Column("total_consumption_mwh", sa.Float(), nullable=True),
        sa.Column("total_ht", sa.Float(), nullable=True),
        sa.Column("total_taxes", sa.Float(), nullable=True),
        sa.Column("total_vat", sa.Float(), nullable=True),
        sa.Column("total_ttc", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=12), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["import_id"], ["energy_invoice_imports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("import_id", name="uq_energy_invoices_import_id"),
    )
    op.create_index(op.f("ix_energy_invoices_city_id"), "energy_invoices", ["city_id"], unique=False)
    op.create_index(op.f("ix_energy_invoices_import_id"), "energy_invoices", ["import_id"], unique=False)
    op.create_index(op.f("ix_energy_invoices_supplier"), "energy_invoices", ["supplier"], unique=False)
    op.create_index(op.f("ix_energy_invoices_invoice_number"), "energy_invoices", ["invoice_number"], unique=False)
    op.create_index(op.f("ix_energy_invoices_regroupement"), "energy_invoices", ["regroupement"], unique=False)

    op.create_table(
        "energy_invoice_batch_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("invoice_import_id", sa.Integer(), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("archive_filename", sa.String(length=255), nullable=True),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["energy_invoice_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invoice_import_id"], ["energy_invoice_imports.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_energy_invoice_batch_items_batch_id"), "energy_invoice_batch_items", ["batch_id"], unique=False)
    op.create_index(
        op.f("ix_energy_invoice_batch_items_invoice_import_id"),
        "energy_invoice_batch_items",
        ["invoice_import_id"],
        unique=False,
    )
    op.create_index(op.f("ix_energy_invoice_batch_items_sha256"), "energy_invoice_batch_items", ["sha256"], unique=False)

    op.create_table(
        "energy_invoice_sites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("prm_id", sa.String(length=40), nullable=True),
        sa.Column("site_name", sa.String(length=255), nullable=True),
        sa.Column("delivery_address", sa.String(length=600), nullable=True),
        sa.Column("meter_number", sa.String(length=120), nullable=True),
        sa.Column("meter_type", sa.String(length=120), nullable=True),
        sa.Column("local_customer_reference", sa.String(length=120), nullable=True),
        sa.Column("segment", sa.String(length=30), nullable=True),
        sa.Column("tariff_option_label", sa.String(length=255), nullable=True),
        sa.Column("regroupement", sa.String(length=120), nullable=True),
        sa.Column("summary_period_start", sa.Date(), nullable=True),
        sa.Column("summary_period_end", sa.Date(), nullable=True),
        sa.Column("summary_total_ttc", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["energy_invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_energy_invoice_sites_invoice_id"), "energy_invoice_sites", ["invoice_id"], unique=False)
    op.create_index(op.f("ix_energy_invoice_sites_prm_id"), "energy_invoice_sites", ["prm_id"], unique=False)
    op.create_index(op.f("ix_energy_invoice_sites_regroupement"), "energy_invoice_sites", ["regroupement"], unique=False)

    op.create_table(
        "energy_invoice_checks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=30), nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("scope", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["energy_invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_energy_invoice_checks_invoice_id"), "energy_invoice_checks", ["invoice_id"], unique=False)
    op.create_index(op.f("ix_energy_invoice_checks_severity"), "energy_invoice_checks", ["severity"], unique=False)
    op.create_index(op.f("ix_energy_invoice_checks_code"), "energy_invoice_checks", ["code"], unique=False)

    op.create_table(
        "energy_invoice_periods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_site_id", sa.Integer(), nullable=False),
        sa.Column("fic_number", sa.String(length=120), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("pdf_page_start", sa.Integer(), nullable=True),
        sa.Column("pdf_page_end", sa.Integer(), nullable=True),
        sa.Column("total_ht", sa.Float(), nullable=True),
        sa.Column("total_vat", sa.Float(), nullable=True),
        sa.Column("total_ttc", sa.Float(), nullable=True),
        sa.Column("subscribed_power_kva", sa.Float(), nullable=True),
        sa.Column("max_reached_power_kva", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["invoice_site_id"], ["energy_invoice_sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_energy_invoice_periods_invoice_site_id"), "energy_invoice_periods", ["invoice_site_id"], unique=False)
    op.create_index(op.f("ix_energy_invoice_periods_fic_number"), "energy_invoice_periods", ["fic_number"], unique=False)

    op.create_table(
        "energy_invoice_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_period_id", sa.Integer(), nullable=False),
        sa.Column("family", sa.String(length=120), nullable=True),
        sa.Column("label", sa.String(length=600), nullable=True),
        sa.Column("normalized_code", sa.String(length=120), nullable=True),
        sa.Column("poste", sa.String(length=60), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("quantity_unit", sa.String(length=60), nullable=True),
        sa.Column("unit_price_ht", sa.Float(), nullable=True),
        sa.Column("unit_price_unit", sa.String(length=60), nullable=True),
        sa.Column("amount_ht", sa.Float(), nullable=True),
        sa.Column("vat_rate", sa.Float(), nullable=True),
        sa.Column("raw_line", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["invoice_period_id"], ["energy_invoice_periods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_energy_invoice_lines_invoice_period_id"), "energy_invoice_lines", ["invoice_period_id"], unique=False)
    op.create_index(op.f("ix_energy_invoice_lines_normalized_code"), "energy_invoice_lines", ["normalized_code"], unique=False)

    op.create_table(
        "energy_invoice_meter_reads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_period_id", sa.Integer(), nullable=False),
        sa.Column("period_code", sa.String(length=60), nullable=True),
        sa.Column("meter_number", sa.String(length=120), nullable=True),
        sa.Column("previous_read_date", sa.Date(), nullable=True),
        sa.Column("previous_index", sa.Float(), nullable=True),
        sa.Column("current_read_date", sa.Date(), nullable=True),
        sa.Column("current_index", sa.Float(), nullable=True),
        sa.Column("reading_type", sa.String(length=30), nullable=True),
        sa.Column("difference", sa.Float(), nullable=True),
        sa.Column("energy_kwh", sa.Float(), nullable=True),
        sa.Column("subscribed_power_kva", sa.Float(), nullable=True),
        sa.Column("reached_power_kva", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["invoice_period_id"], ["energy_invoice_periods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_energy_invoice_meter_reads_invoice_period_id"),
        "energy_invoice_meter_reads",
        ["invoice_period_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_energy_invoice_meter_reads_invoice_period_id"), table_name="energy_invoice_meter_reads")
    op.drop_table("energy_invoice_meter_reads")
    op.drop_index(op.f("ix_energy_invoice_lines_normalized_code"), table_name="energy_invoice_lines")
    op.drop_index(op.f("ix_energy_invoice_lines_invoice_period_id"), table_name="energy_invoice_lines")
    op.drop_table("energy_invoice_lines")
    op.drop_index(op.f("ix_energy_invoice_periods_fic_number"), table_name="energy_invoice_periods")
    op.drop_index(op.f("ix_energy_invoice_periods_invoice_site_id"), table_name="energy_invoice_periods")
    op.drop_table("energy_invoice_periods")
    op.drop_index(op.f("ix_energy_invoice_checks_code"), table_name="energy_invoice_checks")
    op.drop_index(op.f("ix_energy_invoice_checks_severity"), table_name="energy_invoice_checks")
    op.drop_index(op.f("ix_energy_invoice_checks_invoice_id"), table_name="energy_invoice_checks")
    op.drop_table("energy_invoice_checks")
    op.drop_index(op.f("ix_energy_invoice_sites_regroupement"), table_name="energy_invoice_sites")
    op.drop_index(op.f("ix_energy_invoice_sites_prm_id"), table_name="energy_invoice_sites")
    op.drop_index(op.f("ix_energy_invoice_sites_invoice_id"), table_name="energy_invoice_sites")
    op.drop_table("energy_invoice_sites")
    op.drop_index(op.f("ix_energy_invoice_batch_items_sha256"), table_name="energy_invoice_batch_items")
    op.drop_index(op.f("ix_energy_invoice_batch_items_invoice_import_id"), table_name="energy_invoice_batch_items")
    op.drop_index(op.f("ix_energy_invoice_batch_items_batch_id"), table_name="energy_invoice_batch_items")
    op.drop_table("energy_invoice_batch_items")
    op.drop_index(op.f("ix_energy_invoices_regroupement"), table_name="energy_invoices")
    op.drop_index(op.f("ix_energy_invoices_invoice_number"), table_name="energy_invoices")
    op.drop_index(op.f("ix_energy_invoices_supplier"), table_name="energy_invoices")
    op.drop_index(op.f("ix_energy_invoices_import_id"), table_name="energy_invoices")
    op.drop_index(op.f("ix_energy_invoices_city_id"), table_name="energy_invoices")
    op.drop_table("energy_invoices")
    op.drop_index(op.f("ix_energy_invoice_batches_uploaded_by_user_id"), table_name="energy_invoice_batches")
    op.drop_index(op.f("ix_energy_invoice_batches_city_id"), table_name="energy_invoice_batches")
    op.drop_table("energy_invoice_batches")
