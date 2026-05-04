from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class BillingConfig(Base):
    __tablename__ = "billing_configs"
    __table_args__ = (UniqueConstraint("city_id", "supplier", "tariff_code", name="uq_billing_config"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    supplier: Mapped[str] = mapped_column(String(100), nullable=False)
    tariff_code: Mapped[str] = mapped_column(String(20), nullable=False)
    tariff_label: Mapped[str | None] = mapped_column(String(300), nullable=True)
    lot: Mapped[str | None] = mapped_column(String(30), nullable=True)
    has_hphc: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    representative_prm_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class BillingPriceEntry(Base):
    __tablename__ = "billing_price_entries"
    __table_args__ = (UniqueConstraint("config_id", "year", "component", name="uq_billing_price"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    component: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class BillingHphcSlot(Base):
    __tablename__ = "billing_hphc_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    day_type: Mapped[str] = mapped_column(String(20), nullable=False)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)
    period: Mapped[str] = mapped_column(String(2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
