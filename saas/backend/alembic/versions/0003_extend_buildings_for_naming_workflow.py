from alembic import op
import sqlalchemy as sa

revision = "0003_buildings_naming"
down_revision = "0002_cities_buildings_locals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("buildings", sa.Column("dgfip_unique_key", sa.String(length=40), nullable=True))
    op.add_column("buildings", sa.Column("dgfip_source_file", sa.String(length=255), nullable=True))
    op.add_column("buildings", sa.Column("dgfip_source_rows_json", sa.Text(), nullable=True))
    op.add_column("buildings", sa.Column("dgfip_reference_norm", sa.String(length=32), nullable=True))
    op.add_column("buildings", sa.Column("indice_repetition", sa.String(length=40), nullable=True))
    op.add_column("buildings", sa.Column("ign_layer", sa.String(length=80), nullable=True))
    op.add_column("buildings", sa.Column("ign_typename", sa.String(length=120), nullable=True))
    op.add_column("buildings", sa.Column("ign_id", sa.String(length=120), nullable=True))
    op.add_column("buildings", sa.Column("ign_name", sa.String(length=255), nullable=True))
    op.add_column("buildings", sa.Column("ign_label", sa.String(length=255), nullable=True))
    op.add_column("buildings", sa.Column("ign_name_proposed", sa.String(length=255), nullable=True))
    op.add_column("buildings", sa.Column("ign_name_source", sa.String(length=120), nullable=True))
    op.add_column("buildings", sa.Column("ign_name_distance_m", sa.Float(), nullable=True))
    op.add_column("buildings", sa.Column("ign_attributes_json", sa.Text(), nullable=True))
    op.add_column("buildings", sa.Column("ign_toponym_candidates_json", sa.Text(), nullable=True))
    op.add_column("buildings", sa.Column("parcel_labels_json", sa.Text(), nullable=True))
    op.add_column("buildings", sa.Column("majic_building_values_json", sa.Text(), nullable=True))
    op.add_column("buildings", sa.Column("majic_entry_values_json", sa.Text(), nullable=True))
    op.add_column("buildings", sa.Column("majic_level_values_json", sa.Text(), nullable=True))
    op.add_column("buildings", sa.Column("majic_door_values_json", sa.Text(), nullable=True))
    op.create_index(op.f("ix_buildings_dgfip_unique_key"), "buildings", ["dgfip_unique_key"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_buildings_dgfip_unique_key"), table_name="buildings")
    op.drop_column("buildings", "majic_door_values_json")
    op.drop_column("buildings", "majic_level_values_json")
    op.drop_column("buildings", "majic_entry_values_json")
    op.drop_column("buildings", "majic_building_values_json")
    op.drop_column("buildings", "parcel_labels_json")
    op.drop_column("buildings", "ign_toponym_candidates_json")
    op.drop_column("buildings", "ign_attributes_json")
    op.drop_column("buildings", "ign_name_distance_m")
    op.drop_column("buildings", "ign_name_source")
    op.drop_column("buildings", "ign_name_proposed")
    op.drop_column("buildings", "ign_label")
    op.drop_column("buildings", "ign_name")
    op.drop_column("buildings", "ign_id")
    op.drop_column("buildings", "ign_typename")
    op.drop_column("buildings", "ign_layer")
    op.drop_column("buildings", "indice_repetition")
    op.drop_column("buildings", "dgfip_reference_norm")
    op.drop_column("buildings", "dgfip_source_rows_json")
    op.drop_column("buildings", "dgfip_source_file")
    op.drop_column("buildings", "dgfip_unique_key")
