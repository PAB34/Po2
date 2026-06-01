"""generalize CPE revision evidences

Revision ID: 0031
Revises: 0030
Create Date: 2026-06-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("cpe_invoice_evidences", "invoice_id", existing_type=sa.Integer(), nullable=True)
    op.add_column(
        "cpe_invoice_evidences",
        sa.Column("evidence_kind", sa.String(length=40), server_default="invoice_pdf", nullable=False),
    )
    op.add_column("cpe_invoice_evidences", sa.Column("market", sa.String(length=30), nullable=True))
    op.add_column("cpe_invoice_evidences", sa.Column("contract_code", sa.String(length=80), nullable=True))
    op.add_column("cpe_invoice_evidences", sa.Column("year", sa.Integer(), nullable=True))
    op.add_column("cpe_invoice_evidences", sa.Column("quarter", sa.Integer(), nullable=True))
    op.add_column("cpe_invoice_evidences", sa.Column("effective_date", sa.Date(), nullable=True))
    op.create_index("ix_cpe_invoice_evidences_market", "cpe_invoice_evidences", ["market"])
    op.create_index("ix_cpe_invoice_evidences_contract_code", "cpe_invoice_evidences", ["contract_code"])
    op.create_index("ix_cpe_invoice_evidences_year", "cpe_invoice_evidences", ["year"])

    op.create_table(
        "cpe_invoice_evidence_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("evidence_id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["evidence_id"], ["cpe_invoice_evidences.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invoice_id"], ["cpe_finance_invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evidence_id", "invoice_id", name="uq_cpe_invoice_evidence_link"),
    )
    op.create_index("ix_cpe_invoice_evidence_links_evidence_id", "cpe_invoice_evidence_links", ["evidence_id"])
    op.create_index("ix_cpe_invoice_evidence_links_invoice_id", "cpe_invoice_evidence_links", ["invoice_id"])
    op.execute(
        """
        INSERT INTO cpe_invoice_evidence_links (evidence_id, invoice_id)
        SELECT id, invoice_id
        FROM cpe_invoice_evidences
        WHERE invoice_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE cpe_revision_indices
        SET evidence_id = NULL
        WHERE evidence_id IN (
            SELECT id
            FROM cpe_invoice_evidences
            WHERE invoice_id IS NULL
        )
        """
    )
    op.execute(
        """
        DELETE FROM cpe_invoice_evidences
        WHERE invoice_id IS NULL
        """
    )
    op.drop_index("ix_cpe_invoice_evidence_links_invoice_id", table_name="cpe_invoice_evidence_links")
    op.drop_index("ix_cpe_invoice_evidence_links_evidence_id", table_name="cpe_invoice_evidence_links")
    op.drop_table("cpe_invoice_evidence_links")
    op.drop_index("ix_cpe_invoice_evidences_year", table_name="cpe_invoice_evidences")
    op.drop_index("ix_cpe_invoice_evidences_contract_code", table_name="cpe_invoice_evidences")
    op.drop_index("ix_cpe_invoice_evidences_market", table_name="cpe_invoice_evidences")
    op.drop_column("cpe_invoice_evidences", "effective_date")
    op.drop_column("cpe_invoice_evidences", "quarter")
    op.drop_column("cpe_invoice_evidences", "year")
    op.drop_column("cpe_invoice_evidences", "contract_code")
    op.drop_column("cpe_invoice_evidences", "market")
    op.drop_column("cpe_invoice_evidences", "evidence_kind")
    op.alter_column("cpe_invoice_evidences", "invoice_id", existing_type=sa.Integer(), nullable=False)
