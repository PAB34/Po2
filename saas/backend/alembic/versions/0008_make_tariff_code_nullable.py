from alembic import op
import sqlalchemy as sa

revision = "0008_make_tariff_code_nullable"
down_revision = "0007_add_lot_to_billing_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("billing_configs", "tariff_code", nullable=True)


def downgrade() -> None:
    op.execute("UPDATE billing_configs SET tariff_code = '' WHERE tariff_code IS NULL")
    op.alter_column("billing_configs", "tariff_code", nullable=False)
