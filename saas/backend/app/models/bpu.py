"""
Modèles SQLAlchemy pour le suivi temporel des prix d'énergie (BPU).

Source : Bordereaux de Prix Unitaires (BPU) issus des marchés subséquents
d'achat groupé d'électricité (Hérault Énergies / EDF / ENGIE), allant de
2021 à 2026.

Architecture normalisée 5 tables :
  BpuDocument         (1) ─┬── (N) BpuSegment          (tension/site/TURPE)
                           └── (N) BpuFixedCharge       (abonnements, frais)

  BpuSegment          (1) ─── (N) BpuTimePeriod        (Base/HPH/HCH/HPE/HCE/Pointe/...)

  BpuTimePeriod       (1) ─── (N) BpuPriceComponent    (Fourniture/Capacité/CEE/GO)

Hétérogénéité gérée :
- Unités diverses (€HTT/MWh ENGIE vs c€/kWh HTT EDF) → champ `price_unit` + `unit_normalized`
- Segmentation par tension OU par site (C1-C5) OU par usage → champ `segment_type`
- Composantes prix variables → table dédiée

Statuts d'extraction :
- ok           : parser auto a réussi (BPU textuels)
- ocr_ok       : OCR a réussi avec confiance >= seuil
- ocr_review   : OCR a tourné mais confiance faible → revue manuelle nécessaire
- manual       : saisie manuelle (fallback)
- pending      : pas encore importé
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


# Statuts d'extraction
EXTRACTION_OK = "ok"
EXTRACTION_OCR_OK = "ocr_ok"
EXTRACTION_OCR_REVIEW = "ocr_review"
EXTRACTION_MANUAL = "manual"
EXTRACTION_PENDING = "pending"
EXTRACTION_ERROR = "error"

EXTRACTION_STATUSES = {
    EXTRACTION_OK,
    EXTRACTION_OCR_OK,
    EXTRACTION_OCR_REVIEW,
    EXTRACTION_MANUAL,
    EXTRACTION_PENDING,
    EXTRACTION_ERROR,
}

# Types de segments
SEGMENT_TYPE_TENSION = "tension"  # BT 36 kVA, HTA, etc.
SEGMENT_TYPE_SITE = "site"  # C1, C2, C3, C4, C5
SEGMENT_TYPE_USAGE = "usage"  # Bâtiment, Éclairage public, Bornes

SEGMENT_TYPES = {SEGMENT_TYPE_TENSION, SEGMENT_TYPE_SITE, SEGMENT_TYPE_USAGE}

# Codes de postes horosaisonniers (normalisés)
PERIOD_BASE = "BASE"
PERIOD_POINTE = "POINTE"
PERIOD_HPH = "HPH"  # Heures Pleines Saison Haute
PERIOD_HCH = "HCH"  # Heures Creuses Saison Haute
PERIOD_HPE = "HPE"  # Heures Pleines Saison Basse (Été)
PERIOD_HCE = "HCE"  # Heures Creuses Saison Basse (Été)
PERIOD_HPB = "HPB"  # Heures Pleines Basse (synonyme HPE)
PERIOD_HCB = "HCB"  # Heures Creuses Basse (synonyme HCE)
PERIOD_HP = "HP"    # Heures Pleines (générique)
PERIOD_HC = "HC"    # Heures Creuses (générique)

PERIOD_CODES = {
    PERIOD_BASE, PERIOD_POINTE,
    PERIOD_HPH, PERIOD_HCH, PERIOD_HPE, PERIOD_HCE,
    PERIOD_HPB, PERIOD_HCB, PERIOD_HP, PERIOD_HC,
}

# Composantes de prix
COMPONENT_FOURNITURE = "fourniture"
COMPONENT_CAPACITE = "capacite"
COMPONENT_CEE = "cee"
COMPONENT_CEE_PRECARITE = "cee_precarite"
COMPONENT_CPB = "cpb"
COMPONENT_GO = "go"  # Garanties d'Origine
COMPONENT_RENOUVELABLE = "renouvelable"  # synonyme/extension de GO chez EDF
COMPONENT_AUTRE = "autre"

COMPONENT_TYPES = {
    COMPONENT_FOURNITURE, COMPONENT_CAPACITE,
    COMPONENT_CEE, COMPONENT_CEE_PRECARITE, COMPONENT_CPB,
    COMPONENT_GO, COMPONENT_RENOUVELABLE,
    COMPONENT_AUTRE,
}

# Unités normalisées (cible interne) — on convertit à l'import
UNIT_EUR_PER_MWH = "EUR_PER_MWH"
UNIT_EUR_PER_KWH = "EUR_PER_KWH"
UNIT_CENT_EUR_PER_KWH = "CENT_EUR_PER_KWH"
UNIT_EUR_PER_MONTH = "EUR_PER_MONTH"

# Types de frais fixes
CHARGE_ABONNEMENT = "abonnement"
CHARGE_BRANCHEMENT_PROVISOIRE = "branchement_provisoire"
CHARGE_CONTRAT_TEMPORAIRE = "contrat_temporaire"
CHARGE_AUTRE = "autre"


class BpuDocument(Base):
    """Un BPU = un PDF source, identifié par fournisseur/année/MS/lot/avenant."""

    __tablename__ = "bpu_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Identifiants métier
    supplier: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # EDF, ENGIE
    valid_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 2021, 2022, ..., 2026
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    market_subsequent: Mapped[int | None] = mapped_column(Integer, nullable=True)  # MS1, MS2, MS3
    lot_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 1, 2, 3
    amendment_number: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Avenant 5, 6, ...
    amendment_label: Mapped[str | None] = mapped_column(
        String(80), nullable=True
    )  # "V2", "achat clic", "prix ferme", etc.

    # Source PDF
    pdf_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    pdf_relative_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )  # ex: HERAULT ENERGIE/HISTORIQUE BPU/<file>.pdf
    pdf_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Signature
    signature_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    signatory_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    signatory_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    docusign_envelope_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Extraction
    extraction_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=EXTRACTION_PENDING, index=True
    )
    extraction_method: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # "pdftotext", "tesseract", "manual"
    extraction_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    extraction_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # texte brut extrait (debug)

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    imported_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # Relations
    segments: Mapped[list["BpuSegment"]] = relationship(
        "BpuSegment", back_populates="document", cascade="all, delete-orphan"
    )
    fixed_charges: Mapped[list["BpuFixedCharge"]] = relationship(
        "BpuFixedCharge", back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "supplier", "valid_year", "market_subsequent", "lot_number", "amendment_number",
            name="uq_bpu_document_identity",
        ),
    )


class BpuSegment(Base):
    """Un segment tarifaire dans un BPU (par tension, site C1-C5, ou usage)."""

    __tablename__ = "bpu_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("bpu_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )

    segment_type: Mapped[str] = mapped_column(String(20), nullable=False)  # tension|site|usage
    segment_code: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "BT 36 kVA", "C4", "Bornes"
    segment_label: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Détails optionnels (selon segment_type)
    tension_category: Mapped[str | None] = mapped_column(String(10), nullable=True)  # BT, HTA
    turpe_tariff: Mapped[str | None] = mapped_column(String(10), nullable=True)  # C2, C4, C5
    usage_label: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # "Éclairage public", "Bornes", "Bâtiment"

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relations
    document: Mapped["BpuDocument"] = relationship("BpuDocument", back_populates="segments")
    periods: Mapped[list["BpuTimePeriod"]] = relationship(
        "BpuTimePeriod", back_populates="segment", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("document_id", "segment_type", "segment_code", name="uq_bpu_segment_code"),
    )


class BpuTimePeriod(Base):
    """Un poste horosaisonnier (Base, HPH, HCH, ...) au sein d'un segment."""

    __tablename__ = "bpu_time_periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    segment_id: Mapped[int] = mapped_column(
        ForeignKey("bpu_segments.id", ondelete="CASCADE"), nullable=False, index=True
    )

    period_code: Mapped[str] = mapped_column(String(10), nullable=False)  # BASE, HPH, ...
    period_label: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relations
    segment: Mapped["BpuSegment"] = relationship("BpuSegment", back_populates="periods")
    components: Mapped[list["BpuPriceComponent"]] = relationship(
        "BpuPriceComponent", back_populates="period", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("segment_id", "period_code", name="uq_bpu_period_code"),
    )


class BpuPriceComponent(Base):
    """Un prix unitaire pour une composante donnée (Fourniture/Capacité/CEE/GO) sur un poste."""

    __tablename__ = "bpu_price_components"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    period_id: Mapped[int] = mapped_column(
        ForeignKey("bpu_time_periods.id", ondelete="CASCADE"), nullable=False, index=True
    )

    component_type: Mapped[str] = mapped_column(String(20), nullable=False)  # fourniture, capacite, ...
    component_label: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Prix dans l'unité d'origine du BPU
    price_value: Mapped[float] = mapped_column(Numeric(14, 6), nullable=False)
    price_unit: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # ex: "c€/kWh HTT", "€HTT/MWh"

    # Prix normalisé en EUR/MWh pour comparaisons
    price_value_eur_per_mwh: Mapped[float | None] = mapped_column(Numeric(14, 6), nullable=True)

    is_negative: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    extraction_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relations
    period: Mapped["BpuTimePeriod"] = relationship("BpuTimePeriod", back_populates="components")

    __table_args__ = (
        UniqueConstraint("period_id", "component_type", name="uq_bpu_component_type"),
    )


class BpuFixedCharge(Base):
    """Frais fixes rattachés à un BPU (abonnement mensuel, branchement provisoire, etc.).

    Lié au BpuDocument et optionnellement à un segment précis.
    """

    __tablename__ = "bpu_fixed_charges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("bpu_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    segment_id: Mapped[int | None] = mapped_column(
        ForeignKey("bpu_segments.id", ondelete="SET NULL"), nullable=True, index=True
    )

    charge_type: Mapped[str] = mapped_column(String(40), nullable=False)  # abonnement, branchement_provisoire, ...
    charge_label: Mapped[str | None] = mapped_column(String(200), nullable=True)

    charge_value: Mapped[float] = mapped_column(Numeric(14, 6), nullable=False)
    charge_unit: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # ex: "€HT/mois", "€HT/BP/Mois"
    charge_value_eur_per_month: Mapped[float | None] = mapped_column(
        Numeric(14, 6), nullable=True
    )

    applicable_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    applicable_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relations
    document: Mapped["BpuDocument"] = relationship("BpuDocument", back_populates="fixed_charges")
