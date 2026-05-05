from alembic import op
import sqlalchemy as sa

revision = "0009_add_billing_bpu_lines"
down_revision = "0008_make_tariff_code_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_bpu_lines",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("config_id", sa.Integer, nullable=False),
        sa.Column("year", sa.Integer, nullable=True),
        sa.Column("tariff_code", sa.String(20), nullable=False),
        sa.Column("poste", sa.String(20), nullable=False),
        sa.Column("pu_fourniture", sa.Float, nullable=True),
        sa.Column("pu_capacite", sa.Float, nullable=True),
        sa.Column("pu_cee", sa.Float, nullable=True),
        sa.Column("pu_go", sa.Float, nullable=True),
        sa.Column("pu_total", sa.Float, nullable=True),
        sa.Column("observation", sa.String(300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_billing_bpu_lines_config_id", "billing_bpu_lines", ["config_id"])


def downgrade() -> None:
    op.drop_index("ix_billing_bpu_lines_config_id", table_name="billing_bpu_lines")
    op.drop_table("billing_bpu_lines")
