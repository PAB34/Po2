from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    dgfip_source_row_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nom_batiment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nom_commune: Mapped[str] = mapped_column(String(255), nullable=False)
    numero_voirie: Mapped[str | None] = mapped_column(String(40), nullable=True)
    nature_voie: Mapped[str | None] = mapped_column(String(80), nullable=True)
    nom_voie: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prefixe: Mapped[str | None] = mapped_column(String(20), nullable=True)
    section: Mapped[str | None] = mapped_column(String(40), nullable=True)
    numero_plan: Mapped[str | None] = mapped_column(String(40), nullable=True)
    adresse_reconstituee: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_creation: Mapped[str] = mapped_column(String(20), nullable=False, default="MANUEL")
    statut_geocodage: Mapped[str] = mapped_column(String(20), nullable=False, default="NON_FAIT")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
