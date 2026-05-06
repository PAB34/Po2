from alembic import op
import sqlalchemy as sa

revision = "0012_add_invoice_decision_fields"
down_revision = "0011_add_energy_invoice_analysis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "energy_invoice_imports",
        sa.Column("decision_status", sa.String(30), nullable=False, server_default="to_review"),
    )
    op.add_column("energy_invoice_imports", sa.Column("decision_comment", sa.Text(), nullable=True))
    op.add_column("energy_invoice_imports", sa.Column("decision_by_user_id", sa.Integer(), nullable=True))
    op.add_column("energy_invoice_imports", sa.Column("decision_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        op.f("ix_energy_invoice_imports_decision_by_user_id"),
        "energy_invoice_imports",
        ["decision_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_energy_invoice_imports_decision_by_user_id"), table_name="energy_invoice_imports")
    op.drop_column("energy_invoice_imports", "decision_updated_at")
    op.drop_column("energy_invoice_imports", "decision_by_user_id")
    op.drop_column("energy_invoice_imports", "decision_comment")
    op.drop_column("energy_invoice_imports", "decision_status")
