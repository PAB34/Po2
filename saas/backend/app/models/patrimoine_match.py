"""
Boîte de rapprochement patrimoine (PO2-PAT-003).

`PatrimoineMatchItem` : un objet externe (compteur PRM ENEDIS, PCE GRDF, plus tard
site CPE / contrat de maintenance) en attente de rattachement au référentiel
Site / Bâtiment / Local. Chaque item garde sa source, son identifiant, un candidat
proposé avec score, et un statut. Règle cardinale : aucun objet introuvable ne
disparaît — les items ignorés restent listés et rétablissables.

Le rattachement réel (« vérité ») reste dans les tables métier :
- PRM -> `building_meter_links` (fluid=elec) ;
- PCE -> `gas_pces.building_id` (+ `building_meter_links` fluid=gaz).
Cette table est le cockpit de réconciliation, pas le lien canonique.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
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

# Sources supportées (v1 : compteurs).
SOURCE_ENEDIS_PRM = "ENEDIS_PRM"
SOURCE_GRDF_PCE = "GRDF_PCE"

# Statuts de traitement.
STATUS_TODO = "a_traiter"
STATUS_LINKED = "lie"
STATUS_IGNORED = "ignore"
STATUS_TO_CREATE = "a_creer"

# Types de cible patrimoine.
TARGET_BUILDING = "building"
TARGET_SITE = "site"


class PatrimoineMatchItem(Base):
    __tablename__ = "patrimoine_match_items"
    __table_args__ = (
        UniqueConstraint(
            "city_id", "source", "external_id", name="uq_patrimoine_match_source_external"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int | None] = mapped_column(
        ForeignKey("cities.id"), nullable=True, index=True
    )

    # Objet externe
    source: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    context_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Candidat proposé par le moteur
    candidate_target_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    candidate_target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    candidate_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Décision
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=STATUS_TODO, index=True
    )
    resolved_target_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    resolved_target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
