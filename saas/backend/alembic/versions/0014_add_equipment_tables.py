from alembic import op
import sqlalchemy as sa


revision = "0014_add_equipment_tables"
down_revision = "0013_add_enedis_async_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "equipment_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("id_ligne", sa.Integer(), nullable=False, unique=True),
        sa.Column("code_niveau_1", sa.String(20), nullable=False, index=True),
        sa.Column("libelle_niveau_1", sa.String(255), nullable=False),
        sa.Column("code_niveau_2", sa.String(20), nullable=False, index=True),
        sa.Column("libelle_niveau_2", sa.String(500), nullable=False),
        sa.Column("niveau_3", sa.String(500), nullable=True),
        sa.Column("niveau_4", sa.String(500), nullable=True),
        sa.Column("niveau_5", sa.String(500), nullable=True),
        sa.Column("equipement", sa.String(500), nullable=False),
        sa.Column("sypemi_mini_annees", sa.Float(), nullable=True),
        sa.Column("sypemi_reference_annees", sa.Float(), nullable=True),
        sa.Column("sypemi_maxi_annees", sa.Float(), nullable=True),
        sa.Column("fiche_cee", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "building_equipments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("building_id", sa.Integer(), sa.ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("equipment_ref_id", sa.Integer(), sa.ForeignKey("equipment_references.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("etat", sa.String(20), nullable=False),
        sa.Column("quantite", sa.String(20), nullable=False),
        sa.Column("commentaire", sa.Text(), nullable=True),
        sa.Column("duree_vie_restante", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("building_equipments")
    op.drop_table("equipment_references")
