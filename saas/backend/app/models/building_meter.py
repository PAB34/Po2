from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class BuildingMeterLink(Base):
    """Manual link between a patrimonial building and an external utility meter."""

    __tablename__ = "building_meter_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    building_id: Mapped[int] = mapped_column(
        ForeignKey("buildings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fluid: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    meter_identifier: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    meter_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    usage_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    share_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="A_VALIDER")
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False, default="A_VALIDER")
    source: Mapped[str] = mapped_column(String(120), nullable=False, default="MANUEL")
    contract_context: Mapped[str | None] = mapped_column(String(120), nullable=True)
    supplier_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "building_id",
            "fluid",
            "meter_identifier",
            name="uq_building_meter_link_identifier",
        ),
    )
