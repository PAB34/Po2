from alembic import op
import sqlalchemy as sa

revision = "0010_add_energy_invoice_imports"
down_revision = "0009_add_billing_bpu_lines"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "energy_invoice_imports",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("city_id", sa.Integer, nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer, nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(120), nullable=False),
        sa.Column("storage_path", sa.String(600), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("supplier_guess", sa.String(120), nullable=True),
        sa.Column("invoice_number", sa.String(120), nullable=True),
        sa.Column("invoice_date", sa.Date, nullable=True),
        sa.Column("period_start", sa.Date, nullable=True),
        sa.Column("period_end", sa.Date, nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("analysis_status", sa.String(30), nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_energy_invoice_imports_city_id", "energy_invoice_imports", ["city_id"])
    op.create_index("ix_energy_invoice_imports_uploaded_by_user_id", "energy_invoice_imports", ["uploaded_by_user_id"])
    op.create_index("ix_energy_invoice_imports_sha256", "energy_invoice_imports", ["sha256"])


def downgrade() -> None:
    op.drop_index("ix_energy_invoice_imports_sha256", table_name="energy_invoice_imports")
    op.drop_index("ix_energy_invoice_imports_uploaded_by_user_id", table_name="energy_invoice_imports")
    op.drop_index("ix_energy_invoice_imports_city_id", table_name="energy_invoice_imports")
    op.drop_table("energy_invoice_imports")
