from alembic import op
import sqlalchemy as sa

revision = "0004_external_import_fields"
down_revision = "0003_buildings_naming"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("buildings", sa.Column("source_external_id", sa.String(length=255), nullable=True))
    op.add_column("buildings", sa.Column("source_payload_json", sa.Text(), nullable=True))
    op.create_index(op.f("ix_buildings_source_external_id"), "buildings", ["source_external_id"], unique=False)

    op.add_column("locals", sa.Column("source_external_id", sa.String(length=255), nullable=True))
    op.add_column("locals", sa.Column("source_payload_json", sa.Text(), nullable=True))
    op.create_index(op.f("ix_locals_source_external_id"), "locals", ["source_external_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_locals_source_external_id"), table_name="locals")
    op.drop_column("locals", "source_payload_json")
    op.drop_column("locals", "source_external_id")

    op.drop_index(op.f("ix_buildings_source_external_id"), table_name="buildings")
    op.drop_column("buildings", "source_payload_json")
    op.drop_column("buildings", "source_external_id")
