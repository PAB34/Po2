"""
Contacts fournisseurs (DALKIA, ENGIE, EDF, …) pour les réclamations factures.

Un contact éditable par (ville, fournisseur). Sert à pré-remplir le destinataire
des brouillons de réclamation depuis la page Factures & décisions. Aucun envoi
automatique : la plateforme ne fait que préparer le message.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class SupplierContact(Base):
    __tablename__ = "supplier_contacts"
    __table_args__ = (
        UniqueConstraint("city_id", "supplier", name="uq_supplier_contact_city_supplier"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)

    supplier: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    contact_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
