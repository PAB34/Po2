"""
Modèles GRDF — gaz (distributeur).

`GasPce` : référentiel des Points de Comptage et d'Estimation (PCE) gaz, avec
l'état du droit d'accès (consentement) GRDF ADICT et les données contractuelles/
techniques mises en cache.

`GasConsumption` : relevés de consommation (publiées définitives et informatives)
récupérés via l'API CONSO, l'`energie` en kWh étant la valeur principale.

Distinct des tables `cpe_*` (P1 DALKIA) et `building_meter_links` (rattachement
patrimoine) : ici on stocke la donnée distributeur brute, source unique du suivi
temporel gaz et du rapprochement avec les factures P1.
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


class GasPce(Base):
    """Point de Comptage et d'Estimation gaz + état du droit d'accès GRDF."""

    __tablename__ = "gas_pces"
    __table_args__ = (UniqueConstraint("city_id", "id_pce", name="uq_gas_pce_city_pce"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(
        ForeignKey("cities.id"), nullable=True, index=True
    )
    building_id: Mapped[int | None] = mapped_column(
        ForeignKey("buildings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    id_pce: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    nom_site: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Droit d'accès / consentement
    role_tiers: Mapped[str] = mapped_column(
        String(40), nullable=False, default="AUTORISE_CONTRAT_FOURNITURE"
    )
    nom_titulaire: Mapped[str | None] = mapped_column(String(255), nullable=True)
    code_postal: Mapped[str | None] = mapped_column(String(10), nullable=True)
    courriel_titulaire: Mapped[str | None] = mapped_column(String(255), nullable=True)
    id_droit_acces: Mapped[str | None] = mapped_column(String(80), nullable=True)
    etat_droit_acces: Mapped[str | None] = mapped_column(
        String(30), nullable=True, index=True
    )  # null / "A valider" / "Active" / "Révoquée"
    date_debut_droit_acces: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_fin_droit_acces: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Périmètres accordés
    perim_publiees: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    perim_informatives: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    perim_contractuelles: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    perim_techniques: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Données contractuelles / techniques mises en cache
    tarif_acheminement: Mapped[str | None] = mapped_column(String(8), nullable=True)
    car_actuelle: Mapped[int | None] = mapped_column(Integer, nullable=True)  # kWh/an
    profil_type: Mapped[str | None] = mapped_column(String(8), nullable=True)
    frequence_releve: Mapped[str | None] = mapped_column(String(4), nullable=True)  # 6M/1M/MM/JJ
    code_calibre: Mapped[str | None] = mapped_column(String(8), nullable=True)

    # Adresse du compteur (donnees_techniques.situation_compteur). GRDF ne fournit
    # AUCUN nom de site : l'adresse est la seule identification exploitable, et
    # `complement_adresse` porte souvent le nom d'usage du bâtiment (ex. « LOUIS
    # CATANZANO »). Sert aussi de clé de rapprochement vers le patrimoine.
    numero_rue: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nom_rue: Mapped[str | None] = mapped_column(String(255), nullable=True)
    complement_adresse: Mapped[str | None] = mapped_column(String(255), nullable=True)
    commune: Mapped[str | None] = mapped_column(String(120), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class GasConsumption(Base):
    """Relevé de consommation gaz GRDF (publiée ou informative)."""

    __tablename__ = "gas_consumptions"
    __table_args__ = (
        UniqueConstraint(
            "pce_id", "date_debut", "type_conso", name="uq_gas_conso_pce_debut_type"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pce_id: Mapped[int] = mapped_column(
        ForeignKey("gas_pces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date_debut: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    date_fin: Mapped[date] = mapped_column(Date, nullable=False)
    energie_kwh: Mapped[int | None] = mapped_column(Integer, nullable=True)
    volume_brut_m3: Mapped[int | None] = mapped_column(Integer, nullable=True)
    volume_converti_m3: Mapped[int | None] = mapped_column(Integer, nullable=True)
    coeff_conversion: Mapped[float | None] = mapped_column(Float, nullable=True)
    statut_conso: Mapped[str | None] = mapped_column(String(20), nullable=True)  # Provisoire/Définitive
    type_conso: Mapped[str] = mapped_column(String(40), nullable=False, default="Publiée")
    type_qualif: Mapped[str | None] = mapped_column(String(20), nullable=True)  # Mesuré/Estimé/Corrigé
    journee_gaziere: Mapped[date | None] = mapped_column(Date, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
