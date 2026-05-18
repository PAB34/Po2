from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class EquipmentReference(Base):
    __tablename__ = "equipment_references"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    id_ligne: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    code_niveau_1: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    libelle_niveau_1: Mapped[str] = mapped_column(String(255), nullable=False)
    code_niveau_2: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    libelle_niveau_2: Mapped[str] = mapped_column(String(500), nullable=False)
    niveau_3: Mapped[str | None] = mapped_column(String(500), nullable=True)
    niveau_4: Mapped[str | None] = mapped_column(String(500), nullable=True)
    niveau_5: Mapped[str | None] = mapped_column(String(500), nullable=True)
    equipement: Mapped[str] = mapped_column(String(500), nullable=False)
    sypemi_mini_annees: Mapped[float | None] = mapped_column(Float, nullable=True)
    sypemi_reference_annees: Mapped[float | None] = mapped_column(Float, nullable=True)
    sypemi_maxi_annees: Mapped[float | None] = mapped_column(Float, nullable=True)
    fiche_cee: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class BuildingEquipment(Base):
    __tablename__ = "building_equipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, index=True)
    equipment_ref_id: Mapped[int] = mapped_column(ForeignKey("equipment_references.id", ondelete="CASCADE"), nullable=False, index=True)
    etat: Mapped[str] = mapped_column(String(20), nullable=False)
    quantite: Mapped[str] = mapped_column(String(20), nullable=False)
    commentaire: Mapped[str | None] = mapped_column(Text, nullable=True)
    duree_vie_restante: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
