"""
Référentiel tarif réseau gaz — ATRD (distribution GRDF) / ATRT (transport).

Équivalent gaz du TURPE électricité : tarif d'accès aux réseaux fixé par la CRE,
refacturé à l'euro/euro, révisé ~annuellement (1er juillet). Éditable et daté,
comme `services/turpe.py` côté élec.

Seule la part **terme variable ATRD** (€/MWh) est propre à l'option tarifaire
(T1–T4) ; les termes fixes ATRD/ATRT dépendent de la capacité souscrite du PCE
et restent contrôlés en cohérence. Ce référentiel sert au contrôle ABSOLU du
terme variable (détecte une dérive uniforme qu'une médiane observée ne verrait pas).
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class GasNetworkTariff(Base):
    __tablename__ = "gas_network_tariffs"
    __table_args__ = (
        UniqueConstraint("city_id", "annee", "option", name="uq_gas_network_city_annee_option"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    annee: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    option: Mapped[str] = mapped_column(String(8), nullable=False)  # T1 | T2 | T3 | T4

    atrd_terme_variable_eur_mwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    atrd_abonnement_annuel_eur: Mapped[float | None] = mapped_column(Float, nullable=True)

    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
