"""Modeles pour l'import du DPGF P1 revise (livrable separe DALKIA).

Quand DALKIA signe un OS impactant le prix gaz (ex. OS N°3), il livre un fichier
``P1 - DPGF LOT x AAAAVn.xlsx`` *separe* du fichier maitre (acte d'engagement). Ce DPGF
contient le P1 gaz revise selon 3 niveaux (feuilles Annexe 6) :

- ``contrat``        : base contractuelle (identique a l'Annexe 6 du maitre) ;
- ``rev_temp``       : revision temperatures (base d'acompte retenue) ;
- ``rev_temp_prix``  : revision temperatures + prix d'achat (OS) — la part variable baisse.

Ces tables ont une **lignee d'import propre**, totalement separee du referentiel maitre
(``cpe_dalkia_ref_*``). Un import DPGF P1 ne desactive jamais un import maitre : il ne touche
que le P1 revise du lot concerne (P2/P3/APE/cibles/RECAP du maitre restent intacts).
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

# Niveaux de revision P1 portes par le DPGF (feuilles Annexe 6).
DPGF_P1_LEVELS = ("contrat", "rev_temp", "rev_temp_prix")
DPGF_P1_LEVEL_LABELS = {
    "contrat": "P1 gaz contrat",
    "rev_temp": "P1 gaz Rév Temp",
    "rev_temp_prix": "P1 gaz Rév T° & prix",
}


class CpeDpgfP1Import(Base):
    """Historique des imports DPGF P1 revise (lignee separee du referentiel maitre)."""

    __tablename__ = "cpe_dpgf_p1_imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    lot: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    import_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    nb_lines: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    acte_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    acte_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_effet: Mapped[date | None] = mapped_column(Date, nullable=True)


class CpeDpgfP1Line(Base):
    """Ligne de P1 gaz revise : site x periode x niveau (contrat/rev_temp/rev_temp_prix)."""

    __tablename__ = "cpe_dpgf_p1_lines"
    __table_args__ = (
        UniqueConstraint("import_id", "level", "code_site", "period_idx", name="uq_dpgf_p1_line"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_id: Mapped[int] = mapped_column(
        ForeignKey("cpe_dpgf_p1_imports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    lot: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    code_site: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    pce: Mapped[str | None] = mapped_column(String(30), nullable=True)
    type_tarif: Mapped[str | None] = mapped_column(String(10), nullable=True)
    prix_unitaire_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    period_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    period_label: Mapped[str] = mapped_column(String(80), nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    qt_mwhpcs: Mapped[float | None] = mapped_column(Float, nullable=True)
    p10_var_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p10_total_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
