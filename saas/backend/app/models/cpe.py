"""Modèles CPE DALKIA — Contrat de Performance Énergétique Ville de Sète."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

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

    actif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


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
    __table_args__ = (UniqueConstraint("annee", name="uq_cpe_prix_gaz_annee"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    annee: Mapped[int] = mapped_column(Integer, nullable=False)

    pu_eur_mwh_pci: Mapped[float] = mapped_column(Float, nullable=False)
    """Prix unitaire moyen annuel en €/MWhPCI."""

    source: Mapped[str] = mapped_column(String(30), nullable=False, default="saisie_manuelle")
    """Origine : contrat_p1 | saisie_manuelle"""

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
