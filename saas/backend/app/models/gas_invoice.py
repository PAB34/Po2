"""
Factures gaz TotalEnergies (marché Hérault Énergie, bâtiments Ville).

`GasInvoice` : une facture gaz = une ligne (le fichier source TotalEnergies est déjà
à plat, entièrement décomposé). Distinct des modèles élec (`energy_invoice_*`,
orientés PRM/segments) : le gaz a sa structure propre (PCE, classe B0/B1/B2I,
tarif d'acheminement T1/T2/T3, ATRD/ATRT, TICGN).

Le contrôle v1 porte sur la cohérence (arithmétique, TVA, conversion m³→kWh) ;
le contrôle prix (BPU gaz lot 7, ATRD/ATRT, TICGN) viendra en v2 avec les barèmes.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
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


class GasInvoice(Base):
    __tablename__ = "gas_invoices"
    __table_args__ = (
        UniqueConstraint("city_id", "num_facture", name="uq_gas_invoice_city_num"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    building_id: Mapped[int | None] = mapped_column(
        ForeignKey("buildings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    import_batch: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)

    # Identification
    num_facture: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    type_detail: Mapped[str | None] = mapped_column(String(20), nullable=True)  # FACTURE | AVOIR
    date_comptable: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_echeance: Mapped[date | None] = mapped_column(Date, nullable=True)

    ref_site: Mapped[str | None] = mapped_column(String(40), nullable=True)
    pce: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    nom_site: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lib_regroupement: Mapped[str | None] = mapped_column(String(255), nullable=True)
    code_interne: Mapped[str | None] = mapped_column(String(40), nullable=True)
    adresse: Mapped[str | None] = mapped_column(String(255), nullable=True)
    code_postal: Mapped[str | None] = mapped_column(String(10), nullable=True)
    ville: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Contractuel / technique
    classe_conso: Mapped[str | None] = mapped_column(String(8), nullable=True)
    tarif_acheminement: Mapped[str | None] = mapped_column(String(8), nullable=True)
    profil_consommation: Mapped[str | None] = mapped_column(String(8), nullable=True)
    car_acheminement: Mapped[int | None] = mapped_column(Integer, nullable=True)
    car_conso: Mapped[int | None] = mapped_column(Integer, nullable=True)
    coeff_conversion: Mapped[float | None] = mapped_column(Float, nullable=True)
    matricule_compteur: Mapped[str | None] = mapped_column(String(40), nullable=True)

    # Période
    debut_conso: Mapped[date | None] = mapped_column(Date, nullable=True)
    fin_conso: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Montants (décomposition complète du HT)
    prix_conso_gaz: Mapped[float | None] = mapped_column(Float, nullable=True)  # €/kWh
    montant_conso_gaz: Mapped[float | None] = mapped_column(Float, nullable=True)
    abonnement_fournisseur: Mapped[float | None] = mapped_column(Float, nullable=True)
    montant_cee: Mapped[float | None] = mapped_column(Float, nullable=True)
    montant_cee_precarite: Mapped[float | None] = mapped_column(Float, nullable=True)
    montant_cpb: Mapped[float | None] = mapped_column(Float, nullable=True)
    montant_indexation: Mapped[float | None] = mapped_column(Float, nullable=True)
    atrt_terme_fixe: Mapped[float | None] = mapped_column(Float, nullable=True)
    atrd_terme_fixe: Mapped[float | None] = mapped_column(Float, nullable=True)
    atrd_terme_variable: Mapped[float | None] = mapped_column(Float, nullable=True)
    montant_autres: Mapped[float | None] = mapped_column(Float, nullable=True)
    montant_ticgn: Mapped[float | None] = mapped_column(Float, nullable=True)
    montant_cta: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_hors_tva: Mapped[float | None] = mapped_column(Float, nullable=True)
    assiette_tva_tn: Mapped[float | None] = mapped_column(Float, nullable=True)
    tva_tn: Mapped[float | None] = mapped_column(Float, nullable=True)
    assiette_tva_tr: Mapped[float | None] = mapped_column(Float, nullable=True)
    tva_tr: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_ttc: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Consommation
    total_conso_kwh: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_conso_m3: Mapped[int | None] = mapped_column(Integer, nullable=True)
    index_reel: Mapped[str | None] = mapped_column(String(40), nullable=True)
    type_releve: Mapped[str | None] = mapped_column(String(60), nullable=True)
    derniere_releve_reelle: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Contrôle & décision
    control_status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_checked")
    control_issues_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    control_detail_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_status: Mapped[str] = mapped_column(String(20), nullable=False, default="to_review")
    decision_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    finance_exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
