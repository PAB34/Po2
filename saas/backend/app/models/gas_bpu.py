"""
Référence de prix gaz (BPU lot 7 Hérault Énergie / TotalEnergies).

Prix unitaires de fourniture (€ HT/MWh) par année et profil tarifaire (T1–T4),
source = `BPU_2026_Lots_1_2_et_7.xlsx`. Éditable en base (même philosophie que le
BPU élec canonique). Sert au contrôle prix des factures gaz `GasInvoice`.

N.B. l'acheminement (ATRT/ATRD) n'est PAS ici : il est refacturé à l'euro/euro
sur le barème réglementé GRDF (référentiel distinct, à venir).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class GasBpuPrice(Base):
    __tablename__ = "gas_bpu_prices"
    __table_args__ = (
        UniqueConstraint("city_id", "annee", "profil", name="uq_gas_bpu_city_annee_profil"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    annee: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    profil: Mapped[str] = mapped_column(String(8), nullable=False)  # T1 | T2 | T3 | T4

    fourniture_ht_mwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    cee_ht_mwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    cee_precarite_ht_mwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpb_ht_mwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    go_ht_mwh: Mapped[float | None] = mapped_column(Float, nullable=True)

    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
