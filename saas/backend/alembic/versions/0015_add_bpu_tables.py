"""Add BPU (Bordereau de Prix Unitaires) tables for energy pricing history.

Revision ID: 0015_add_bpu_tables
Revises: 0014_add_equipment_tables
"""
from alembic import op
import sqlalchemy as sa


revision = "0015_add_bpu_tables"
down_revision = "0014_add_equipment_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # bpu_documents
    op.create_table(
        "bpu_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supplier", sa.String(50), nullable=False),
        sa.Column("valid_year", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("market_subsequent", sa.Integer(), nullable=True),
        sa.Column("lot_number", sa.Integer(), nullable=False),
        sa.Column("amendment_number", sa.Integer(), nullable=True),
        sa.Column("amendment_label", sa.String(80), nullable=True),
        sa.Column("pdf_filename", sa.String(255), nullable=False),
        sa.Column("pdf_relative_path", sa.String(500), nullable=True),
        sa.Column("pdf_sha256", sa.String(64), nullable=True),
        sa.Column("signature_date", sa.Date(), nullable=True),
        sa.Column("signatory_name", sa.String(200), nullable=True),
        sa.Column("signatory_role", sa.String(100), nullable=True),
        sa.Column("docusign_envelope_id", sa.String(64), nullable=True),
        sa.Column("extraction_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("extraction_method", sa.String(20), nullable=True),
        sa.Column("extraction_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("extraction_notes", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("imported_by_user_id", sa.Integer(), nullable=True),
        sa.UniqueConstraint(
            "supplier", "valid_year", "market_subsequent", "lot_number", "amendment_number",
            name="uq_bpu_document_identity",
        ),
    )
    op.create_index("ix_bpu_documents_supplier", "bpu_documents", ["supplier"])
    op.create_index("ix_bpu_documents_valid_year", "bpu_documents", ["valid_year"])
    op.create_index("ix_bpu_documents_lot_number", "bpu_documents", ["lot_number"])
    op.create_index("ix_bpu_documents_pdf_sha256", "bpu_documents", ["pdf_sha256"])
    op.create_index("ix_bpu_documents_extraction_status", "bpu_documents", ["extraction_status"])
    op.create_index("ix_bpu_documents_imported_by_user_id", "bpu_documents", ["imported_by_user_id"])

    # bpu_segments
    op.create_table(
        "bpu_segments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id", sa.Integer(),
            sa.ForeignKey("bpu_documents.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("segment_type", sa.String(20), nullable=False),
        sa.Column("segment_code", sa.String(50), nullable=False),
        sa.Column("segment_label", sa.String(200), nullable=True),
        sa.Column("tension_category", sa.String(10), nullable=True),
        sa.Column("turpe_tariff", sa.String(10), nullable=True),
        sa.Column("usage_label", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("document_id", "segment_type", "segment_code", name="uq_bpu_segment_code"),
    )
    op.create_index("ix_bpu_segments_document_id", "bpu_segments", ["document_id"])

    # bpu_time_periods
    op.create_table(
        "bpu_time_periods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "segment_id", sa.Integer(),
            sa.ForeignKey("bpu_segments.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("period_code", sa.String(10), nullable=False),
        sa.Column("period_label", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("segment_id", "period_code", name="uq_bpu_period_code"),
    )
    op.create_index("ix_bpu_time_periods_segment_id", "bpu_time_periods", ["segment_id"])

    # bpu_price_components
    op.create_table(
        "bpu_price_components",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "period_id", sa.Integer(),
            sa.ForeignKey("bpu_time_periods.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("component_type", sa.String(20), nullable=False),
        sa.Column("component_label", sa.String(100), nullable=True),
        sa.Column("price_value", sa.Numeric(14, 6), nullable=False),
        sa.Column("price_unit", sa.String(30), nullable=False),
        sa.Column("price_value_eur_per_mwh", sa.Numeric(14, 6), nullable=True),
        sa.Column("is_negative", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("extraction_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("period_id", "component_type", name="uq_bpu_component_type"),
    )
    op.create_index("ix_bpu_price_components_period_id", "bpu_price_components", ["period_id"])

    # bpu_fixed_charges
    op.create_table(
        "bpu_fixed_charges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id", sa.Integer(),
            sa.ForeignKey("bpu_documents.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "segment_id", sa.Integer(),
            sa.ForeignKey("bpu_segments.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("charge_type", sa.String(40), nullable=False),
        sa.Column("charge_label", sa.String(200), nullable=True),
        sa.Column("charge_value", sa.Numeric(14, 6), nullable=False),
        sa.Column("charge_unit", sa.String(30), nullable=False),
        sa.Column("charge_value_eur_per_month", sa.Numeric(14, 6), nullable=True),
        sa.Column("applicable_from", sa.Date(), nullable=True),
        sa.Column("applicable_to", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_bpu_fixed_charges_document_id", "bpu_fixed_charges", ["document_id"])
    op.create_index("ix_bpu_fixed_charges_segment_id", "bpu_fixed_charges", ["segment_id"])


def downgrade() -> None:
    op.drop_index("ix_bpu_fixed_charges_segment_id", table_name="bpu_fixed_charges")
    op.drop_index("ix_bpu_fixed_charges_document_id", table_name="bpu_fixed_charges")
    op.drop_table("bpu_fixed_charges")

    op.drop_index("ix_bpu_price_components_period_id", table_name="bpu_price_components")
    op.drop_table("bpu_price_components")

    op.drop_index("ix_bpu_time_periods_segment_id", table_name="bpu_time_periods")
    op.drop_table("bpu_time_periods")

    op.drop_index("ix_bpu_segments_document_id", table_name="bpu_segments")
    op.drop_table("bpu_segments")

    op.drop_index("ix_bpu_documents_imported_by_user_id", table_name="bpu_documents")
    op.drop_index("ix_bpu_documents_extraction_status", table_name="bpu_documents")
    op.drop_index("ix_bpu_documents_pdf_sha256", table_name="bpu_documents")
    op.drop_index("ix_bpu_documents_lot_number", table_name="bpu_documents")
    op.drop_index("ix_bpu_documents_valid_year", table_name="bpu_documents")
    op.drop_index("ix_bpu_documents_supplier", table_name="bpu_documents")
    op.drop_table("bpu_documents")
