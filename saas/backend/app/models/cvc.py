from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CvcInventoryItem(Base):
    __tablename__ = "cvc_inventory_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True)
    building_id: Mapped[int | None] = mapped_column(
        ForeignKey("buildings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    local_id: Mapped[int | None] = mapped_column(
        ForeignKey("locals.id", ondelete="SET NULL"), nullable=True, index=True
    )
    equipment_ref_id: Mapped[int | None] = mapped_column(
        ForeignKey("equipment_references.id", ondelete="SET NULL"), nullable=True, index=True
    )
    site_raw: Mapped[str | None] = mapped_column(String(500), nullable=True)
    batiment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    niveau: Mapped[str | None] = mapped_column(String(100), nullable=True)
    local_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    designation: Mapped[str] = mapped_column(String(500), nullable=False)
    statut: Mapped[str | None] = mapped_column(String(100), nullable=True)
    etat_sante: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantite_relevee: Mapped[int | None] = mapped_column(Integer, nullable=True)
    famille: Mapped[str | None] = mapped_column(String(255), nullable=True)
    marque: Mapped[str | None] = mapped_column(String(255), nullable=True)
    modele: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_mis_en_service: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duree_vie_restante: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantite_fluide_frigorigene: Mapped[float | None] = mapped_column(Float, nullable=True)
    import_batch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class CvcRefrigerantItem(Base):
    __tablename__ = "cvc_refrigerant_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True)
    building_id: Mapped[int | None] = mapped_column(
        ForeignKey("buildings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    cvc_inventory_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("cvc_inventory_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    import_batch: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    site_raw: Mapped[str | None] = mapped_column(String(500), nullable=True)
    designation: Mapped[str] = mapped_column(String(500), nullable=False)
    quantite_relevee: Mapped[int | None] = mapped_column(Integer, nullable=True)
    famille: Mapped[str | None] = mapped_column(String(255), nullable=True)
    marque: Mapped[str | None] = mapped_column(String(255), nullable=True)
    modele: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fluide_frigorigene: Mapped[str | None] = mapped_column(String(80), nullable=True)
    quantite_fluide_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    puissance_froid_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    date_mis_en_service: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gwp: Mapped[float | None] = mapped_column(Float, nullable=True)
    teqco2: Mapped[float | None] = mapped_column(Float, nullable=True)
    esp_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cout_desp_date_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    cumul_5_ans_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    schedule_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    detection_permanente: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    dernier_controle_etancheite: Mapped[date | None] = mapped_column(Date, nullable=True)
    prochaine_echeance: Mapped[date | None] = mapped_column(Date, nullable=True)
    titulaire: Mapped[str | None] = mapped_column(String(255), nullable=True)
    responsable_collectivite: Mapped[str | None] = mapped_column(String(255), nullable=True)
    statut_action: Mapped[str | None] = mapped_column(String(80), nullable=True)
    commentaire_gmao: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_status: Mapped[str] = mapped_column(String(40), nullable=False, server_default="pending")
    match_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class CvcSourceBuildingMapping(Base):
    __tablename__ = "cvc_source_building_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    import_batch: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_site_raw: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True)
    building_id: Mapped[int | None] = mapped_column(
        ForeignKey("buildings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    building_ids_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, server_default="to_review")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    match_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
