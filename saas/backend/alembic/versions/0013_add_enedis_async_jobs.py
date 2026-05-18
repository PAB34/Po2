from alembic import op
import sqlalchemy as sa


revision = "0013_add_enedis_async_jobs"
down_revision = "0012_add_invoice_decision_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enedis_async_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dossier_id", sa.BigInteger(), nullable=False),
        sa.Column("type_donnee", sa.String(16), nullable=False),
        sa.Column("date_start", sa.Date(), nullable=False),
        sa.Column("date_end", sa.Date(), nullable=False),
        sa.Column("prm_count", sa.Integer(), nullable=False),
        sa.Column("canal_contact_id", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="requested"),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("ftp_filename", sa.String(255), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decrypted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rows_added", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        op.f("ix_enedis_async_jobs_dossier_id"),
        "enedis_async_jobs",
        ["dossier_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_enedis_async_jobs_type_donnee"),
        "enedis_async_jobs",
        ["type_donnee"],
        unique=False,
    )
    op.create_index(
        op.f("ix_enedis_async_jobs_status"),
        "enedis_async_jobs",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_enedis_async_jobs_ftp_filename"),
        "enedis_async_jobs",
        ["ftp_filename"],
        unique=False,
    )
    op.create_index(
        op.f("ix_enedis_async_jobs_requested_by_user_id"),
        "enedis_async_jobs",
        ["requested_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_enedis_async_jobs_requested_by_user_id"), table_name="enedis_async_jobs")
    op.drop_index(op.f("ix_enedis_async_jobs_ftp_filename"), table_name="enedis_async_jobs")
    op.drop_index(op.f("ix_enedis_async_jobs_status"), table_name="enedis_async_jobs")
    op.drop_index(op.f("ix_enedis_async_jobs_type_donnee"), table_name="enedis_async_jobs")
    op.drop_index(op.f("ix_enedis_async_jobs_dossier_id"), table_name="enedis_async_jobs")
    op.drop_table("enedis_async_jobs")
