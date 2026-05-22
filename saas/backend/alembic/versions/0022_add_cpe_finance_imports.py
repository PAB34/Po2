"""add CPE DALKIA finance imports

Revision ID: 0022_cpe_finance_imports
Revises: 0021
Create Date: 2026-05-22 16:20:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0022_cpe_finance_imports"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cpe_finance_import_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("target_contract_code", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("source_row_count", sa.Integer(), nullable=False),
        sa.Column("imported_line_count", sa.Integer(), nullable=False),
        sa.Column("ignored_line_count", sa.Integer(), nullable=False),
        sa.Column("invoice_count", sa.Integer(), nullable=False),
        sa.Column("matched_site_line_count", sa.Integer(), nullable=False),
        sa.Column("unknown_site_line_count", sa.Integer(), nullable=False),
        sa.Column("missing_site_code_line_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cpe_finance_import_batches_city_id"),
        "cpe_finance_import_batches",
        ["city_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cpe_finance_import_batches_uploaded_by_user_id"),
        "cpe_finance_import_batches",
        ["uploaded_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cpe_finance_import_batches_sha256"),
        "cpe_finance_import_batches",
        ["sha256"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cpe_finance_import_batches_target_contract_code"),
        "cpe_finance_import_batches",
        ["target_contract_code"],
        unique=False,
    )

    op.create_table(
        "cpe_finance_invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("invoice_number", sa.String(length=120), nullable=False),
        sa.Column("contract_code", sa.String(length=50), nullable=False),
        sa.Column("contract_label", sa.String(length=255), nullable=True),
        sa.Column("market_type", sa.String(length=80), nullable=True),
        sa.Column("invoice_type", sa.String(length=40), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("issued_at", sa.Date(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("original_invoice_number", sa.String(length=120), nullable=True),
        sa.Column("customer_code", sa.String(length=120), nullable=True),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("total_ht", sa.Float(), nullable=False),
        sa.Column("line_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["cpe_finance_import_batches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_id", "invoice_number", name="uq_cpe_finance_invoice_batch_number"),
    )
    op.create_index(op.f("ix_cpe_finance_invoices_batch_id"), "cpe_finance_invoices", ["batch_id"], unique=False)
    op.create_index(
        op.f("ix_cpe_finance_invoices_invoice_number"),
        "cpe_finance_invoices",
        ["invoice_number"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cpe_finance_invoices_contract_code"),
        "cpe_finance_invoices",
        ["contract_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cpe_finance_invoices_invoice_type"),
        "cpe_finance_invoices",
        ["invoice_type"],
        unique=False,
    )

    op.create_table(
        "cpe_finance_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("cpe_site_id", sa.Integer(), nullable=True),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("market", sa.String(length=20), nullable=False),
        sa.Column("sold_service", sa.String(length=255), nullable=True),
        sa.Column("billed_item", sa.String(length=120), nullable=True),
        sa.Column("amount_ht", sa.Float(), nullable=False),
        sa.Column("vat_rate", sa.Float(), nullable=True),
        sa.Column("consumption", sa.Float(), nullable=True),
        sa.Column("consumption_unit", sa.String(length=60), nullable=True),
        sa.Column("prestation_detail", sa.Text(), nullable=True),
        sa.Column("customer_reference", sa.String(length=160), nullable=True),
        sa.Column("recipient_reference", sa.String(length=255), nullable=True),
        sa.Column("base_price", sa.Float(), nullable=True),
        sa.Column("revised_price", sa.Float(), nullable=True),
        sa.Column("reading_index_start", sa.Float(), nullable=True),
        sa.Column("reading_index_end", sa.Float(), nullable=True),
        sa.Column("reading_date_start", sa.Date(), nullable=True),
        sa.Column("reading_date_end", sa.Date(), nullable=True),
        sa.Column("reading_type", sa.String(length=80), nullable=True),
        sa.Column("detected_site_code", sa.String(length=50), nullable=True),
        sa.Column("site_validation_status", sa.String(length=40), nullable=False),
        sa.Column("raw_payload_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["cpe_finance_import_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invoice_id"], ["cpe_finance_invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cpe_site_id"], ["cpe_sites.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cpe_finance_lines_batch_id"), "cpe_finance_lines", ["batch_id"], unique=False)
    op.create_index(op.f("ix_cpe_finance_lines_invoice_id"), "cpe_finance_lines", ["invoice_id"], unique=False)
    op.create_index(op.f("ix_cpe_finance_lines_cpe_site_id"), "cpe_finance_lines", ["cpe_site_id"], unique=False)
    op.create_index(op.f("ix_cpe_finance_lines_market"), "cpe_finance_lines", ["market"], unique=False)
    op.create_index(op.f("ix_cpe_finance_lines_billed_item"), "cpe_finance_lines", ["billed_item"], unique=False)
    op.create_index(
        op.f("ix_cpe_finance_lines_detected_site_code"),
        "cpe_finance_lines",
        ["detected_site_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cpe_finance_lines_site_validation_status"),
        "cpe_finance_lines",
        ["site_validation_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_cpe_finance_lines_site_validation_status"), table_name="cpe_finance_lines")
    op.drop_index(op.f("ix_cpe_finance_lines_detected_site_code"), table_name="cpe_finance_lines")
    op.drop_index(op.f("ix_cpe_finance_lines_billed_item"), table_name="cpe_finance_lines")
    op.drop_index(op.f("ix_cpe_finance_lines_market"), table_name="cpe_finance_lines")
    op.drop_index(op.f("ix_cpe_finance_lines_cpe_site_id"), table_name="cpe_finance_lines")
    op.drop_index(op.f("ix_cpe_finance_lines_invoice_id"), table_name="cpe_finance_lines")
    op.drop_index(op.f("ix_cpe_finance_lines_batch_id"), table_name="cpe_finance_lines")
    op.drop_table("cpe_finance_lines")
    op.drop_index(op.f("ix_cpe_finance_invoices_invoice_type"), table_name="cpe_finance_invoices")
    op.drop_index(op.f("ix_cpe_finance_invoices_contract_code"), table_name="cpe_finance_invoices")
    op.drop_index(op.f("ix_cpe_finance_invoices_invoice_number"), table_name="cpe_finance_invoices")
    op.drop_index(op.f("ix_cpe_finance_invoices_batch_id"), table_name="cpe_finance_invoices")
    op.drop_table("cpe_finance_invoices")
    op.drop_index(op.f("ix_cpe_finance_import_batches_target_contract_code"), table_name="cpe_finance_import_batches")
    op.drop_index(op.f("ix_cpe_finance_import_batches_sha256"), table_name="cpe_finance_import_batches")
    op.drop_index(op.f("ix_cpe_finance_import_batches_uploaded_by_user_id"), table_name="cpe_finance_import_batches")
    op.drop_index(op.f("ix_cpe_finance_import_batches_city_id"), table_name="cpe_finance_import_batches")
    op.drop_table("cpe_finance_import_batches")
