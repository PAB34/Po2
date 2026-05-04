from alembic import op
import sqlalchemy as sa

revision = "0006_add_billing_config"
down_revision = "0005_add_code_postal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("supplier", sa.String(length=100), nullable=False),
        sa.Column("tariff_code", sa.String(length=20), nullable=False),
        sa.Column("tariff_label", sa.String(length=300), nullable=True),
        sa.Column("has_hphc", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("representative_prm_id", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("city_id", "supplier", "tariff_code", name="uq_billing_config"),
    )
    op.create_index("ix_billing_configs_city_id", "billing_configs", ["city_id"])

    op.create_table(
        "billing_price_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("config_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("component", sa.String(length=50), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("config_id", "year", "component", name="uq_billing_price"),
    )
    op.create_index("ix_billing_price_entries_config_id", "billing_price_entries", ["config_id"])

    op.create_table(
        "billing_hphc_slots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("config_id", sa.Integer(), nullable=False),
        sa.Column("day_type", sa.String(length=20), nullable=False),
        sa.Column("start_time", sa.String(length=5), nullable=False),
        sa.Column("end_time", sa.String(length=5), nullable=False),
        sa.Column("period", sa.String(length=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_billing_hphc_slots_config_id", "billing_hphc_slots", ["config_id"])


def downgrade() -> None:
    op.drop_index("ix_billing_hphc_slots_config_id", "billing_hphc_slots")
    op.drop_table("billing_hphc_slots")
    op.drop_index("ix_billing_price_entries_config_id", "billing_price_entries")
    op.drop_table("billing_price_entries")
    op.drop_index("ix_billing_configs_city_id", "billing_configs")
    op.drop_table("billing_configs")
