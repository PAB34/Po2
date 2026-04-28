from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Local(Base):
    __tablename__ = "locals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, index=True)
    nom_local: Mapped[str] = mapped_column(String(255), nullable=False)
    type_local: Mapped[str] = mapped_column(String(80), nullable=False)
    niveau: Mapped[str | None] = mapped_column(String(40), nullable=True)
    surface_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    usage: Mapped[str | None] = mapped_column(String(120), nullable=True)
    statut_occupation: Mapped[str | None] = mapped_column(String(120), nullable=True)
    commentaire: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
