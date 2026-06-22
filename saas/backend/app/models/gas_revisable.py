"""
Prix de fourniture gaz à prix révisable (indexé PEG), par mois de consommation.

Certains PCE sont en offre révisable mensuelle (TM(M) = PEG(M) − PEG(0) + C) :
le prix conso varie chaque mois selon l'indice PEGAS. Cette table stocke le prix
révisable applicable par mois (€/MWh), éditable, pour contrôler ces factures à
l'absolu (sinon elles ressortent en « prix ≠ BPU ferme »).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class GasSupplyRevisablePrice(Base):
    __tablename__ = "gas_supply_revisable_prices"
    __table_args__ = (
        UniqueConstraint("city_id", "annee", "mois", name="uq_gas_revisable_city_annee_mois"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    annee: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    mois: Mapped[int] = mapped_column(Integer, nullable=False)
    fourniture_eur_mwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
