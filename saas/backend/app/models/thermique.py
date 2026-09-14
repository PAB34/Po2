"""Outil de métré thermique : projets, fichiers importés et planches.

Une planche = une page d'un fichier importé. Sa nature (plan, coupe, façade, plan masse)
est suggérée à l'import puis validée par l'utilisateur ; son échelle est déclarée puis
contrôlée par une cote. Voir `docs/thermique/metre-thermique-decisions.md`.
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class ThermiqueProject(Base):
    __tablename__ = "thermique_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Nord : degrés, sens trigonométrique, dans le repère commun des niveaux (0 = de A vers B).
    north_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    documents: Mapped[list["ThermiqueDocument"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="ThermiqueDocument.id"
    )
    components: Mapped[list["ThermiqueComponent"]] = relationship(
        cascade="all, delete-orphan", order_by="ThermiqueComponent.id"
    )
    levels: Mapped[list["ThermiqueLevel"]] = relationship(
        cascade="all, delete-orphan", order_by="ThermiqueLevel.position"
    )


class ThermiqueDocument(Base):
    __tablename__ = "thermique_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("thermique_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(64), nullable=False)
    file_format: Mapped[str] = mapped_column(String(10), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    project: Mapped[ThermiqueProject] = relationship(back_populates="documents")
    sheets: Mapped[list["ThermiqueSheet"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="ThermiqueSheet.page_index"
    )


class ThermiqueSheet(Base):
    __tablename__ = "thermique_sheets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("thermique_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("thermique_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_index: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    nature: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nature_suggested: Mapped[str | None] = mapped_column(String(20), nullable=True)
    level_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    scale_denominator: Mapped[float | None] = mapped_column(Float, nullable=True)
    # "declaree" (saisie 1/100…) ou "cote" (déduite d'une cote mesurée sur la planche)
    scale_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Dernière cote de contrôle : deux points en coordonnées PDF (pt) + longueur réelle saisie.
    calibration_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    rotation_deg: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    page_width_pt: Mapped[float] = mapped_column(Float, nullable=False)
    page_height_pt: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    document: Mapped[ThermiqueDocument] = relationship(back_populates="sheets")


class ThermiqueLevel(Base):
    """Niveau du bâtiment pour le métré : sa planche de plan, ses hauteurs et son calage.

    Le calage (deux points A et B communs à tous les niveaux, en points PDF de la planche)
    définit le repère commun qui permet de superposer les niveaux.
    Voir `docs/thermique/metre-plans-decisions.md`.
    """

    __tablename__ = "thermique_levels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("thermique_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    # Rang du niveau, du plus bas au plus haut (−1 sous-sol, 0 rez-de-chaussée…).
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    altitude_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    floor_height_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    slab_thickness_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Hauteur sous plafond saisie ou lue sur une coupe : prime sur hauteur d'étage − plancher.
    ceiling_height_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    # "manuel" ou "coupe" (planche et dessin retenus dans le journal de l'étape)
    heights_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sheet_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("thermique_sheets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    calage_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    zones: Mapped[list["ThermiqueZone"]] = relationship(
        back_populates="level", cascade="all, delete-orphan", order_by="ThermiqueZone.id"
    )


class ThermiqueZone(Base):
    """Tracé d'un niveau : contour chauffé (au nu intérieur), local non chauffé ou patio.

    Points en coordonnées PDF de la planche du niveau ; une qualification par côté
    (donne sur, composant) pour les contours et patios.
    """

    __tablename__ = "thermique_zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("thermique_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    level_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("thermique_levels.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # "contour", "lnc" ou "patio"
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    lnc_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    points_json: Mapped[str] = mapped_column(Text, nullable=False)
    edges_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "manuel" pour l'instant ; "automatique" / "corrige" avec la détection (lot M3).
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manuel", server_default="manuel")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    level: Mapped[ThermiqueLevel] = relationship(back_populates="zones")


class ThermiqueComponent(Base):
    """Composant de bibliothèque : d'un projet (`project_id` renseigné) ou modèle réutilisable du compte.

    La composition est stockée au format d'entrée du moteur ; le résultat est recalculé par le
    serveur à chaque enregistrement, avec les éditions du référentiel utilisées
    (voir `docs/thermique/bibliotheque-projet-decisions.md`).
    """

    __tablename__ = "thermique_components"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("thermique_projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # "hypothese" (étude préliminaire) ou "conforme_cctp"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="hypothese", server_default="hypothese")
    composition_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Composant ou modèle d'origine (copie, import, « enregistrer comme modèle »), sans lien actif.
    source_component_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
