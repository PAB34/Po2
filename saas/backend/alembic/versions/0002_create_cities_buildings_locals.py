from alembic import op
import sqlalchemy as sa

revision = "0002_create_cities_buildings_locals"
down_revision = "0001_create_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nom_commune", sa.String(length=255), nullable=False),
        sa.Column("code_commune", sa.String(length=20), nullable=True),
        sa.Column("code_postal", sa.String(length=20), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cities_nom_commune"), "cities", ["nom_commune"], unique=False)

    op.create_table(
        "buildings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("dgfip_source_row_id", sa.Integer(), nullable=True),
        sa.Column("nom_batiment", sa.String(length=255), nullable=True),
        sa.Column("nom_commune", sa.String(length=255), nullable=False),
        sa.Column("numero_voirie", sa.String(length=40), nullable=True),
        sa.Column("nature_voie", sa.String(length=80), nullable=True),
        sa.Column("nom_voie", sa.String(length=255), nullable=True),
        sa.Column("prefixe", sa.String(length=20), nullable=True),
        sa.Column("section", sa.String(length=40), nullable=True),
        sa.Column("numero_plan", sa.String(length=40), nullable=True),
        sa.Column("adresse_reconstituee", sa.String(length=255), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("source_creation", sa.String(length=20), nullable=False),
        sa.Column("statut_geocodage", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_buildings_city_id"), "buildings", ["city_id"], unique=False)

    op.create_table(
        "locals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("building_id", sa.Integer(), nullable=False),
        sa.Column("nom_local", sa.String(length=255), nullable=False),
        sa.Column("type_local", sa.String(length=80), nullable=False),
        sa.Column("niveau", sa.String(length=40), nullable=True),
        sa.Column("surface_m2", sa.Float(), nullable=True),
        sa.Column("usage", sa.String(length=120), nullable=True),
        sa.Column("statut_occupation", sa.String(length=120), nullable=True),
        sa.Column("commentaire", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_locals_building_id"), "locals", ["building_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_locals_building_id"), table_name="locals")
    op.drop_table("locals")
    op.drop_index(op.f("ix_buildings_city_id"), table_name="buildings")
    op.drop_table("buildings")
    op.drop_index(op.f("ix_cities_nom_commune"), table_name="cities")
    op.drop_table("cities")
