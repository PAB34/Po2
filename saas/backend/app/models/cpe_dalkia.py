"""Modeles pour les tables de reference du marche CPE DALKIA.

Ces tables sont alimentees par l'import du fichier contractuel DALKIA
(L1 et L2) et servent de reference pour le controle des factures.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
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


class CpeDalkiaRefImport(Base):
    """Historique des imports du fichier contractuel DALKIA."""

    __tablename__ = "cpe_dalkia_ref_imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    lot: Mapped[int] = mapped_column(Integer, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    import_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    nb_sites: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_p2p3_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_cibles_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_p1_gaz_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_ape_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class CpeDalkiaRefSite(Base):
    """Liste de reference des sites du marche CPE DALKIA."""

    __tablename__ = "cpe_dalkia_ref_sites"
    __table_args__ = (
        UniqueConstraint("import_id", "code_site", name="uq_dalkia_site_per_import"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_id: Mapped[int] = mapped_column(
        ForeignKey("cpe_dalkia_ref_imports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    lot: Mapped[int] = mapped_column(Integer, nullable=False)
    code_site: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    nom_batiment: Mapped[str] = mapped_column(String(255), nullable=False)
    entite: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lot_label: Mapped[str | None] = mapped_column(String(40), nullable=True)


class CpeDalkiaRefP2P3(Base):
    """Montants P2 et P3 par site x periode."""

    __tablename__ = "cpe_dalkia_ref_p2p3"
    __table_args__ = (
        UniqueConstraint("import_id", "code_site", "period_idx", name="uq_dalkia_p2p3"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_id: Mapped[int] = mapped_column(
        ForeignKey("cpe_dalkia_ref_imports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    code_site: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    period_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    period_label: Mapped[str] = mapped_column(String(80), nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    p2_1_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p2_2_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p2_3_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p2_4_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p2_total_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p3_1_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p3_2_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p3_3_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p3_4_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p3_total_ht: Mapped[float | None] = mapped_column(Float, nullable=True)


class CpeDalkiaRefCible(Base):
    """Cibles de consommation par site x periode x fluide.

    Pas de contrainte unique sur (code_site, fluid, period_idx) : un meme site peut avoir
    plusieurs lignes par periode (sous-compteurs, PV...).
    """

    __tablename__ = "cpe_dalkia_ref_cibles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_id: Mapped[int] = mapped_column(
        ForeignKey("cpe_dalkia_ref_imports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    code_site: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    fluid: Mapped[str] = mapped_column(String(10), nullable=False)
    period_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    period_label: Mapped[str] = mapped_column(String(80), nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    ref_globale_mwhpci: Mapped[float | None] = mapped_column(Float, nullable=True)
    ref_qt_mwhpci: Mapped[float | None] = mapped_column(Float, nullable=True)
    dju_reference: Mapped[float | None] = mapped_column(Float, nullable=True)
    qt_global_mwhpci: Mapped[float | None] = mapped_column(Float, nullable=True)
    nb_mwhpci: Mapped[float | None] = mapped_column(Float, nullable=True)
    q_ecs: Mapped[float | None] = mapped_column(Float, nullable=True)
    qt_ecs: Mapped[float | None] = mapped_column(Float, nullable=True)


class CpeDalkiaRefP1Gaz(Base):
    """Fourniture gaz P1 par site x periode."""

    __tablename__ = "cpe_dalkia_ref_p1_gaz"
    __table_args__ = (
        UniqueConstraint("import_id", "code_site", "period_idx", name="uq_dalkia_p1_gaz"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_id: Mapped[int] = mapped_column(
        ForeignKey("cpe_dalkia_ref_imports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    code_site: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    pce: Mapped[str | None] = mapped_column(String(30), nullable=True)
    type_tarif: Mapped[str | None] = mapped_column(String(10), nullable=True)
    prix_unitaire_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    atrd_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    cta_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p10_fixe_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    period_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    period_label: Mapped[str] = mapped_column(String(80), nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    qt_mwhpcs: Mapped[float | None] = mapped_column(Float, nullable=True)
    p10_var_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    p10_total_ht: Mapped[float | None] = mapped_column(Float, nullable=True)


class CpeDalkiaRefApe(Base):
    """Travaux APE par site (plusieurs lignes possibles)."""

    __tablename__ = "cpe_dalkia_ref_ape"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    import_id: Mapped[int] = mapped_column(
        ForeignKey("cpe_dalkia_ref_imports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    code_site: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    nom_batiment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    situation_initiale_mwhpci: Mapped[float | None] = mapped_column(Float, nullable=True)
    description_ape: Mapped[str | None] = mapped_column(Text, nullable=True)
    annee_achevement: Mapped[int | None] = mapped_column(Integer, nullable=True)
    montant_ape_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    cee_mwh_cumac: Mapped[float | None] = mapped_column(Float, nullable=True)
    cee_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    subvention_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    gain_energetique_mwhpci: Mapped[float | None] = mapped_column(Float, nullable=True)
    situation_nouvelle_mwhpci: Mapped[float | None] = mapped_column(Float, nullable=True)
    annee_engagement_nouvelle_cible: Mapped[int | None] = mapped_column(Integer, nullable=True)
    emission_co2_evitee: Mapped[float | None] = mapped_column(Float, nullable=True)
    production_enr_auto_mwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    production_enr_vendue_mwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    recette_vente_energie_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    ratio_ht_mwhpci: Mapped[float | None] = mapped_column(Float, nullable=True)
    commentaires: Mapped[str | None] = mapped_column(Text, nullable=True)
