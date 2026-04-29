from alembic import op
import sqlalchemy as sa

revision = "0005_add_code_postal"
down_revision = "0004_external_import_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("buildings", sa.Column("code_postal", sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column("buildings", "code_postal")
