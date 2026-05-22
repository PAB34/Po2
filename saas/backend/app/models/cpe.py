"""Modèles CPE DALKIA — Contrat de Performance Énergétique Ville de Sète."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class CpeSite(Base):
    """Référentiel des sites du CPE avec leurs cibles contractuelles (Annexe 5.1 AE)."""

    __tablename__ = "cpe_sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)

    # Identification
    code_site: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    nom_site: Mapped[str] = mapped_column(String(255), nullable=False)
    categorie: Mapped[str] = mapped_column(String(20), nullable=False)  # ENS | SPORT | BAM | CULT

    # Cibles contractuelles (Annexe 5.1 — offre finale DALKIA)
    nb_mwh_pci: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    """NB : consommation chauffage de référence en année normale (MWhPCI)."""

    ecs_ref_m3_an: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    """m de référence : volume ECS annuel produit par chaudière gaz (m³/an)."""

    q_ecs_mwh_pci_per_m3: Mapped[float | None] = mapped_column(Float, nullable=True)
    """qECS : énergie unitaire ECS (MWhPCI/m³) — issu du bordereau de prix.
    Si null : NC = QT (pas d'ECS gaz ou coefficient non encore renseigné)."""

    dju_reference: Mapped[float] = mapped_column(Float, nullable=False, default=1426.0)
    """DJU de référence contractuelle (1 426 DJU — station Montpellier, 1981-2010, base 18°C)."""

    # Cibles électricité (Annexe 5.2 — information, pas d'intéressement direct)
    cible_elec_mwh: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Facturation gaz — OS N°3 (prix fixe 5 ans 2026-2030)
    tarif: Mapped[str | None] = mapped_column(String(5), nullable=True)
    """Typ. tarifaire GRDF : T1 | T2 | T3 — détermine le Pu applicable (OS N°3).
    None = pas de compteur gaz propre (sous-comptage ou site sans gaz)."""

    pce: Mapped[str | None] = mapped_column(String(50), nullable=True)
    """Identifiant PCE GRDF du compteur gaz principal (ex : 24349204040145 ou GI091908)."""

    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CpeFinanceImportBatch(Base):
    """Lot persiste d'un export finances DALKIA filtre sur le contrat CPE cible."""

    __tablename__ = "cpe_finance_import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="dalkia_finance_csv")
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_contract_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="completed")
    source_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_line_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ignored_line_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invoice_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    matched_site_line_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unknown_site_line_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_site_code_line_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    invoices: Mapped[list["CpeFinanceInvoice"]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="CpeFinanceInvoice.id",
    )
    lines: Mapped[list["CpeFinanceLine"]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="CpeFinanceLine.source_row_number",
    )


class CpeFinanceInvoice(Base):
    """Facture DALKIA reconstruite depuis ses lignes dans un export finances."""

    __tablename__ = "cpe_finance_invoices"
    __table_args__ = (UniqueConstraint("batch_id", "invoice_number", name="uq_cpe_finance_invoice_batch_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("cpe_finance_import_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invoice_number: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    contract_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    contract_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    market_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    invoice_type: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    issued_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    original_invoice_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    customer_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_ht: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    line_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    batch: Mapped[CpeFinanceImportBatch] = relationship(back_populates="invoices")
    lines: Mapped[list["CpeFinanceLine"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="CpeFinanceLine.source_row_number",
    )


class CpeFinanceLine(Base):
    """Ligne DALKIA a rapprocher d'un site CPE puis a controler par poste P1/P2/P3."""

    __tablename__ = "cpe_finance_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("cpe_finance_import_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("cpe_finance_invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cpe_site_id: Mapped[int | None] = mapped_column(
        ForeignKey("cpe_sites.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    market: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    sold_service: Mapped[str | None] = mapped_column(String(255), nullable=True)
    billed_item: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    amount_ht: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    vat_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    consumption: Mapped[float | None] = mapped_column(Float, nullable=True)
    consumption_unit: Mapped[str | None] = mapped_column(String(60), nullable=True)
    prestation_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    recipient_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    base_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    revised_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    reading_index_start: Mapped[float | None] = mapped_column(Float, nullable=True)
    reading_index_end: Mapped[float | None] = mapped_column(Float, nullable=True)
    reading_date_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    reading_date_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    reading_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    detected_site_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    site_validation_status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    raw_payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    batch: Mapped[CpeFinanceImportBatch] = relationship(back_populates="lines")
    invoice: Mapped[CpeFinanceInvoice] = relationship(back_populates="lines")
    cpe_site: Mapped[CpeSite | None] = relationship()


class CpeGazReleve(Base):
    """Relevés mensuels de consommation gaz par site CPE.

    Alimenté par :
    - Import CSV des fichiers DALKIA (5e jour ouvrable du mois)
    - Futur import API GRDF ADICT (en attente droits d'accès)
    - Saisie manuelle de secours
    """

    __tablename__ = "cpe_gaz_releves"
    __table_args__ = (UniqueConstraint("cpe_site_id", "annee", "mois", name="uq_cpe_releve_site_mois"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cpe_site_id: Mapped[int] = mapped_column(ForeignKey("cpe_sites.id"), nullable=False, index=True)

    annee: Mapped[int] = mapped_column(Integer, nullable=False)
    mois: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-12

    qt_mwh_pci: Mapped[float | None] = mapped_column(Float, nullable=True)
    """QT mensuel : consommation gaz totale relevée compteur (MWhPCI)."""

    volume_ecs_m3: Mapped[float | None] = mapped_column(Float, nullable=True)
    """m mensuel : volume ECS produit par chaudière gaz (m³) — si compteur séparé."""

    etat_chauffe: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    """État de marche chauffage (O/N) — issu du fichier DALKIA."""

    source: Mapped[str] = mapped_column(String(30), nullable=False, default="csv_dalkia")
    """Origine : csv_dalkia | grdf_api | saisie_manuelle"""

    date_import: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class CpePrixGaz(Base):
    """Prix unitaire gaz annuel (Pu) pour le calcul d'intéressement.

    Pu = prix moyen du MWhPCI facturé sur l'exercice, issu de la décomposition
    du décompte définitif P1 (facture de régularisation au 15/02/N+1).
    """

    __tablename__ = "cpe_prix_gaz"
    __table_args__ = (UniqueConstraint("annee", "tarif", name="uq_cpe_prix_gaz_annee_tarif"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    annee: Mapped[int] = mapped_column(Integer, nullable=False)

    tarif: Mapped[str | None] = mapped_column(String(5), nullable=True)
    """Typ. tarifaire : T1 | T2 | T3 (OS N°3). None = global/fallback."""

    pu_eur_mwh_pci: Mapped[float] = mapped_column(Float, nullable=False)
    """Prix unitaire en €/MWhPCI — converti depuis €/MWhPCS via ratio PCS/PCI ≈ 1.1068."""

    source: Mapped[str] = mapped_column(String(30), nullable=False, default="saisie_manuelle")
    """Origine : os3_fixe | contrat_p1 | saisie_manuelle"""

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CpeResultatAnnuel(Base):
    """Résultat calculé d'intéressement ou de pénalité par site et par exercice.

    Calculé automatiquement à partir de CpeGazReleve + DJU réels + CpePrixGaz.
    Statut :
    - partiel  : données manquantes (mois incomplets)
    - calcule  : calculé automatiquement, en attente de validation
    - valide   : validé par le gestionnaire (sert de base pour la facture/avoir)
    - conteste : montant contesté vis-à-vis de DALKIA
    """

    __tablename__ = "cpe_resultats_annuels"
    __table_args__ = (UniqueConstraint("cpe_site_id", "annee", name="uq_cpe_resultat_site_annee"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cpe_site_id: Mapped[int] = mapped_column(ForeignKey("cpe_sites.id"), nullable=False, index=True)
    annee: Mapped[int] = mapped_column(Integer, nullable=False)

    # Données climatiques
    dju_reels: Mapped[float | None] = mapped_column(Float, nullable=True)
    dju_reference: Mapped[float] = mapped_column(Float, nullable=False, default=1426.0)

    # Cible contractuelle
    nb: Mapped[float] = mapped_column(Float, nullable=False)
    """NB de l'exercice (peut différer de CpeSite.nb_mwh_pci si révision de cible)."""

    n_prime_b: Mapped[float | None] = mapped_column(Float, nullable=True)
    """N'B = NB × (DJU_réels / DJU_ref)"""

    # Consommations
    qt_total: Mapped[float | None] = mapped_column(Float, nullable=True)
    """QT annuel total (somme des 12 mois)."""

    m_ecs_total: Mapped[float | None] = mapped_column(Float, nullable=True)
    """m annuel total ECS (somme des 12 mois ou valeur de référence)."""

    nc: Mapped[float | None] = mapped_column(Float, nullable=True)
    """NC = QT – (m × qECS)"""

    # Résultat financier
    pu_mwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    """Prix unitaire gaz de l'exercice (€/MWhPCI)."""

    ecart: Mapped[float | None] = mapped_column(Float, nullable=True)
    """Écart = N'B – NC (positif → intéressement, négatif → pénalité)."""

    type_resultat: Mapped[str | None] = mapped_column(String(20), nullable=True)
    """interessement | penalite | equilibre | insuffisant (NB=0 ou données manquantes)"""

    montant_ht: Mapped[float | None] = mapped_column(Float, nullable=True)
    """Montant HT (€) de l'intéressement (facture DALKIA) ou pénalité (avoir DALKIA)."""

    p2_4_taux: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    """Taux P2.4 : 1.0 si objectifs atteints, 0.5 sinon."""

    # Contrôle révision NB
    ecart_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    """Écart relatif (NC – NB) / NB — utilisé pour détection seuils révision NB."""

    alerte_revision_nb: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    """True si l'écart dépasse les seuils de révision contractuels (8% / 12%)."""

    # Suivi
    statut: Mapped[str] = mapped_column(String(20), nullable=False, default="partiel")
    nb_mois_renseignes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
