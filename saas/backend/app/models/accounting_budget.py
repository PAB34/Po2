"""Budget annuel par marché, à la maille opération (cadrage doc refonte-v1).

Une ligne de budget rattache un montant annuel à un contrat matrice
(`AccountingMatrixContract` = « le marché ») et à une `operation_number`,
le même axe que celui utilisé par `AccountingMatrixRule` / les snapshots de
facture. Le « réalisé » n'est pas stocké ici : il est recalculé à la volée
depuis `invoice_accounting_snapshots` (cf. `app/services/accounting_budget.py`).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AccountingBudgetLine(Base):
    __tablename__ = "accounting_budget_lines"
    __table_args__ = (
        UniqueConstraint(
            "city_id",
            "matrix_contract_id",
            "year",
            "operation_number",
            name="uq_accounting_budget_line_key",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    matrix_contract_id: Mapped[int] = mapped_column(
        ForeignKey("accounting_matrix_contracts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    operation_number: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount_budget: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
