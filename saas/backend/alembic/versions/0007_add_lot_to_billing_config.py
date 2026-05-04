from alembic import op
import sqlalchemy as sa

revision = "0007_add_lot_to_billing_config"
down_revision = "0006_add_billing_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("billing_configs", sa.Column("lot", sa.String(length=30), nullable=True))
    op.drop_constraint("uq_billing_config", "billing_configs", type_="unique")
    op.create_unique_constraint("uq_billing_config", "billing_configs", ["city_id", "supplier"])


def downgrade() -> None:
    op.drop_constraint("uq_billing_config", "billing_configs", type_="unique")
    op.create_unique_constraint("uq_billing_config", "billing_configs", ["city_id", "supplier", "tariff_code"])
    op.drop_column("billing_configs", "lot")
