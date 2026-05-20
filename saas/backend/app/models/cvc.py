from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CvcInventoryItem(Base):
    __tablename__ = "cvc_inventory_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    building_id: Mapped[int] = mapped_column(
        ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    equipment_ref_id: Mapped[int | None] = mapped_column(
        ForeignKey("equipment_references.id", ondelete="SET NULL"), nullable=True, index=True
    )
    site_raw: Mapped[str | None] = mapped_column(String(500), nullable=True)
    batiment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    niveau: Mapped[str | None] = mapped_column(String(100), nullable=True)
    local_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    designation: Mapped[str] = mapped_column(String(500), nullable=False)
    statut: Mapped[str | None] = mapped_column(String(100), nullable=True)
    etat_sante: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantite_relevee: Mapped[int | None] = mapped_column(Integer, nullable=True)
    famille: Mapped[str | None] = mapped_column(String(255), nullable=True)
    marque: Mapped[str | None] = mapped_column(String(255), nullable=True)
    modele: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_mis_en_service: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duree_vie_restante: Mapped[float | None] = mapped_column(Float, nullable=True)
    import_batch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
