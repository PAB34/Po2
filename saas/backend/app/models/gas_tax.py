"""
Référentiel taxes gaz réglementées — accise (ex-TICGN) et CTA.

- Accise sur les gaz naturels combustibles (ex-TICGN) : taux réglementé €/MWh,
  daté (révisé au 1er août / 1er février). Appliqué à la consommation.
- CTA (Contribution Tarifaire d'Acheminement) : coefficient réglementé appliqué
  au terme fixe d'acheminement (observé ≈ 24,76 % du terme fixe ATRD).

Éditable et daté comme le TURPE / l'ATRD. Sert au contrôle des lignes taxes des
factures gaz `GasInvoice`.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class GasTaxRate(Base):
    __tablename__ = "gas_tax_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)

    valid_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    ticgn_eur_mwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    cta_coeff_atrd_fixe: Mapped[float | None] = mapped_column(Float, nullable=True)
    tva_normale: Mapped[float | None] = mapped_column(Float, nullable=True)
    tva_reduite: Mapped[float | None] = mapped_column(Float, nullable=True)

    source: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
