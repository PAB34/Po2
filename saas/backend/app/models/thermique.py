"""Outil de métré thermique : projets, fichiers importés et planches.

Une planche = une page d'un fichier importé. Sa nature (plan, coupe, façade, plan masse)
est suggérée à l'import puis validée par l'utilisateur ; son échelle est déclarée puis
contrôlée par une cote. Voir `docs/thermique/metre-thermique-decisions.md`.
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
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
    reference_sheet_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("thermique_sheets.id", ondelete="SET NULL"), nullable=True, index=True
    )
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
    # Nord de la planche : flèche tracée par le thermicien, en coordonnées PDF (pt), donc insensible
    # à la rotation d'affichage. {"p1": [x, y], "p2": [x, y]} — p2 est la pointe, du côté du nord.
    north_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    rotation_deg: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    page_width_pt: Mapped[float] = mapped_column(Float, nullable=False)
    page_height_pt: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    document: Mapped[ThermiqueDocument] = relationship(back_populates="sheets")


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


class ThermiqueEtude(Base):
    """État courant de l'étude importée pour une planche de niveau."""

    __tablename__ = "thermique_etudes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("thermique_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sheet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("thermique_sheets.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    format_version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)
    local_states_json: Mapped[str] = mapped_column(Text, nullable=False)
    imported_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ThermiqueEtudeVersion(Base):
    """Photographie complète d'une étude à chaque import/enregistrement."""

    __tablename__ = "thermique_etude_versions"
    __table_args__ = (UniqueConstraint("etude_id", "version_number", name="uq_thermique_etude_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    etude_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("thermique_etudes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(80), nullable=False)
    # Contenu complet aux seuls imports ; les enregistrements ne gardent que les pièces (D64).
    content_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    pieces_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    local_states_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ThermiqueTravail(Base):
    """Un niveau à analyser, en attente du relais qui tourne sur le poste du thermicien (D92).

    Le serveur ne peut pas lancer les agents : il tient la file, le relais la vide. Une seule ligne
    vivante par planche, pour qu'un double clic sur « Analyser » ne mette pas le même niveau deux fois.
    """

    __tablename__ = "thermique_travaux"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("thermique_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sheet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("thermique_sheets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # en_attente → en_cours → fini ; refuse (garde-fou D94) et echec sont des fins de course.
    statut: Mapped[str] = mapped_column(String(20), nullable=False, default="en_attente")
    # Ordre de passage : le catalogue monte du niveau le plus bas au plus haut (D95).
    rang: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    demande_par_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    pris_a: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fini_a: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
