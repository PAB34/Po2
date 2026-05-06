from alembic import op
import sqlalchemy as sa

revision = "0011_add_energy_invoice_analysis"
down_revision = "0010_add_energy_invoice_imports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("energy_invoice_imports", sa.Column("regroupement", sa.String(120), nullable=True))
    op.add_column("energy_invoice_imports", sa.Column("total_ttc", sa.Float(), nullable=True))
    op.add_column("energy_invoice_imports", sa.Column("total_consumption_kwh", sa.Float(), nullable=True))
    op.add_column("energy_invoice_imports", sa.Column("site_count", sa.Integer(), nullable=True))
    op.add_column(
        "energy_invoice_imports",
        sa.Column("control_status", sa.String(30), nullable=False, server_default="not_checked"),
    )
    op.add_column(
        "energy_invoice_imports",
        sa.Column("control_errors_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "energy_invoice_imports",
        sa.Column("control_warnings_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("energy_invoice_imports", sa.Column("analysis_result_json", sa.Text(), nullable=True))
    op.add_column("energy_invoice_imports", sa.Column("control_report_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("energy_invoice_imports", "control_report_json")
    op.drop_column("energy_invoice_imports", "analysis_result_json")
    op.drop_column("energy_invoice_imports", "control_warnings_count")
    op.drop_column("energy_invoice_imports", "control_errors_count")
    op.drop_column("energy_invoice_imports", "control_status")
    op.drop_column("energy_invoice_imports", "site_count")
    op.drop_column("energy_invoice_imports", "total_consumption_kwh")
    op.drop_column("energy_invoice_imports", "total_ttc")
    op.drop_column("energy_invoice_imports", "regroupement")

