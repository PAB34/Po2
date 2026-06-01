"""add CPE invoice PDF evidences

Revision ID: 0030
Revises: 0029
Create Date: 2026-06-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cpe_invoice_evidences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=600), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("extraction_status", sa.String(length=30), nullable=False),
        sa.Column("validation_status", sa.String(length=30), nullable=False),
        sa.Column("declared_invoice_number", sa.String(length=80), nullable=True),
        sa.Column("revision_date", sa.Date(), nullable=True),
        sa.Column("declared_factor", sa.Float(), nullable=True),
        sa.Column("declared_icht_ime", sa.Float(), nullable=True),
        sa.Column("declared_fsd2", sa.Float(), nullable=True),
        sa.Column("declared_bt40", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["cpe_finance_invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_id", "sha256", name="uq_cpe_invoice_evidence_sha"),
    )
    op.create_index("ix_cpe_invoice_evidences_city_id", "cpe_invoice_evidences", ["city_id"])
    op.create_index("ix_cpe_invoice_evidences_invoice_id", "cpe_invoice_evidences", ["invoice_id"])
    op.create_index("ix_cpe_invoice_evidences_sha256", "cpe_invoice_evidences", ["sha256"])
    op.create_index("ix_cpe_invoice_evidences_uploaded_by_user_id", "cpe_invoice_evidences", ["uploaded_by_user_id"])
    op.add_column(
        "cpe_revision_indices",
        sa.Column("verification_status", sa.String(length=30), server_default="to_verify", nullable=False),
    )
    op.add_column("cpe_revision_indices", sa.Column("evidence_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_cpe_revision_indices_evidence_id",
        "cpe_revision_indices",
        "cpe_invoice_evidences",
        ["evidence_id"],
        ["id"],
    )
    op.create_index("ix_cpe_revision_indices_evidence_id", "cpe_revision_indices", ["evidence_id"])


def downgrade() -> None:
    op.drop_index("ix_cpe_revision_indices_evidence_id", table_name="cpe_revision_indices")
    op.drop_constraint("fk_cpe_revision_indices_evidence_id", "cpe_revision_indices", type_="foreignkey")
    op.drop_column("cpe_revision_indices", "evidence_id")
    op.drop_column("cpe_revision_indices", "verification_status")
    op.drop_index("ix_cpe_invoice_evidences_uploaded_by_user_id", table_name="cpe_invoice_evidences")
    op.drop_index("ix_cpe_invoice_evidences_sha256", table_name="cpe_invoice_evidences")
    op.drop_index("ix_cpe_invoice_evidences_invoice_id", table_name="cpe_invoice_evidences")
    op.drop_index("ix_cpe_invoice_evidences_city_id", table_name="cpe_invoice_evidences")
    op.drop_table("cpe_invoice_evidences")
