from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    dgfip_source_row_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dgfip_unique_key: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    dgfip_source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dgfip_source_rows_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    dgfip_reference_norm: Mapped[str | None] = mapped_column(String(32), nullable=True)
    nom_batiment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nom_commune: Mapped[str] = mapped_column(String(255), nullable=False)
    code_postal: Mapped[str | None] = mapped_column(String(10), nullable=True)
    numero_voirie: Mapped[str | None] = mapped_column(String(40), nullable=True)
    indice_repetition: Mapped[str | None] = mapped_column(String(40), nullable=True)
    nature_voie: Mapped[str | None] = mapped_column(String(80), nullable=True)
    nom_voie: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prefixe: Mapped[str | None] = mapped_column(String(20), nullable=True)
    section: Mapped[str | None] = mapped_column(String(40), nullable=True)
    numero_plan: Mapped[str | None] = mapped_column(String(40), nullable=True)
    adresse_reconstituee: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    ign_layer: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ign_typename: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ign_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ign_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ign_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ign_name_proposed: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ign_name_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ign_name_distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    ign_attributes_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ign_toponym_candidates_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    parcel_labels_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    majic_building_values_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    majic_entry_values_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    majic_level_values_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    majic_door_values_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_creation: Mapped[str] = mapped_column(String(20), nullable=False, default="MANUEL")
    statut_geocodage: Mapped[str] = mapped_column(String(20), nullable=False, default="NON_FAIT")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
