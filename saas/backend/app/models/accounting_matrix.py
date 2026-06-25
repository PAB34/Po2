"""Modèles des matrices comptables versionnées (doc 38).

Une matrice comptable V1 est un référentiel versionné, traçable et auditable :
contrat racine -> versions datées -> règles de ventilation, plus un snapshot
immuable figé sur la facture au moment de la décision.

Règle d'or : une version active n'est jamais écrasée par un import ou une
modification ; toute évolution passe par une nouvelle version explicitement
activée. Une facture validée reste liée à la version utilisée au moment de la
décision via ``invoice_accounting_snapshots``.
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class AccountingMatrixContract(Base):
    """Objet racine : une matrice comptable par contrat, lot ou marché."""

    __tablename__ = "accounting_matrix_contracts"
    __table_args__ = (
        UniqueConstraint(
            "city_id",
            "domain",
            "supplier",
            "contract_code",
            "lot_label",
            name="uq_accounting_matrix_contract_key",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)

    # fluides, cpe, maintenance, travaux, futur
    domain: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    # EDF, ENGIE, TotalEnergies, DALKIA, SPIE, SUEZ...
    supplier: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    contract_code: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    contract_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lot_label: Mapped[str | None] = mapped_column(String(120), nullable=True)

    starts_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Interlocuteur entreprise pour préparer une réclamation (doc 38).
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # active, inactive, draft, archived
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list["AccountingMatrixVersion"]] = relationship(
        back_populates="contract",
        cascade="all, delete-orphan",
        order_by="AccountingMatrixVersion.id",
    )


class AccountingMatrixVersion(Base):
    """Version datée d'une matrice. Une seule version active par contrat."""

    __tablename__ = "accounting_matrix_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    matrix_contract_id: Mapped[int] = mapped_column(
        ForeignKey("accounting_matrix_contracts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    version_label: Mapped[str] = mapped_column(String(160), nullable=False)
    # draft, candidate, active, archived
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", index=True)

    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    # manuel, import_xlsx, migration_energie, migration_cpe
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="manuel")
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    validated_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Synthèse des différences (JSON sérialisé en texte, comme le reste du projet).
    change_summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    contract: Mapped["AccountingMatrixContract"] = relationship(back_populates="versions")
    rules: Mapped[list["AccountingMatrixRule"]] = relationship(
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="AccountingMatrixRule.priority",
    )


class AccountingMatrixRule(Base):
    """Règle de ventilation / rattachement comptable au sein d'une version."""

    __tablename__ = "accounting_matrix_rules"
    __table_args__ = (
        UniqueConstraint(
            "matrix_version_id",
            "stable_rule_key",
            name="uq_accounting_matrix_rule_stable_key",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    matrix_version_id: Mapped[int] = mapped_column(
        ForeignKey("accounting_matrix_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Identifiant stable pour l'aller-retour import/export/diff XLSX.
    stable_rule_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    # site, meter, billed_item, subscription, tax, p1, p2, p3, other
    scope: Mapped[str] = mapped_column(String(30), nullable=False, default="billed_item")

    site_code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    building_id: Mapped[int | None] = mapped_column(ForeignKey("buildings.id"), nullable=True)
    meter_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    billed_item_pattern: Mapped[str | None] = mapped_column(String(255), nullable=True)
    supplier_item_code: Mapped[str | None] = mapped_column(String(120), nullable=True)

    accounting_service: Mapped[str | None] = mapped_column(String(120), nullable=True)
    accounting_function: Mapped[str | None] = mapped_column(String(120), nullable=True)
    accounting_antenna: Mapped[str | None] = mapped_column(String(120), nullable=True)
    operation_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    accounting_nature: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    accounting_label: Mapped[str | None] = mapped_column(String(255), nullable=True)

    allocation_percent: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    version: Mapped["AccountingMatrixVersion"] = relationship(back_populates="rules")


class InvoiceAccountingSnapshot(Base):
    """Instantané figé appliqué à une facture au moment de la décision.

    Garantit l'historique : une facture traitée avec la version V3 reste liée
    à V3 même si une V4 est créée ensuite.
    """

    __tablename__ = "invoice_accounting_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "city_id",
            "invoice_source",
            "invoice_id",
            name="uq_invoice_accounting_snapshot_invoice",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)

    # energy_import, gas_totalenergies, cpe_dalkia, futur
    invoice_source: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    invoice_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)

    matrix_contract_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounting_matrix_contracts.id"), nullable=True
    )
    matrix_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounting_matrix_versions.id"), nullable=True
    )

    # proposed, validated, manual_override, blocked, exported
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="proposed", index=True)

    # Résultat complet de l'imputation appliquée + arbitrages, sérialisés en texte.
    snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    exceptions_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    validated_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
