"""Draft OS / avenant workflow for CPE DALKIA contract perimeter changes."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CpeContractChangeRequest(Base):
    """Preparation dossier for a CPE perimeter change before the official DPGF import."""

    __tablename__ = "cpe_contract_change_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    baseline_import_id: Mapped[int | None] = mapped_column(
        ForeignKey("cpe_dalkia_ref_imports.id"), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    change_type: Mapped[str] = mapped_column(String(30), nullable=False, default="mixed")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    lot: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    requester_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    dalkia_contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    os_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    avenant_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CpeContractChangeLine(Base):
    """One site movement inside an OS / avenant preparation dossier."""

    __tablename__ = "cpe_contract_change_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("cpe_contract_change_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)

    action: Mapped[str] = mapped_column(String(20), nullable=False)
    code_site: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    site_name: Mapped[str] = mapped_column(String(255), nullable=False)
    lot: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    pce: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tarif: Mapped[str | None] = mapped_column(String(10), nullable=True)

    current_p1_gaz_annual_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_p1_elec_annual_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_p2_annual_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_p3_annual_ht: Mapped[float | None] = mapped_column(Float, nullable=True)

    p1_gaz_annual_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p1_elec_annual_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p2_annual_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p3_annual_ht: Mapped[float | None] = mapped_column(Float, nullable=True)

    nb_mwh_pci: Mapped[float | None] = mapped_column(Float, nullable=True)
    cible_elec_mwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )