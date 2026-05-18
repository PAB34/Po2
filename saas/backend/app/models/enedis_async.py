"""
Modèle SQLAlchemy pour suivre les dossiers de publication asynchrone ENEDIS.

Workflow d'un job (transition de statuts) :

    requested        — POST commanderPublicationPonctuelle accepté, dossier_id retourné
        ↓
    file_received    — fichier chiffré déposé sur FTP, téléchargé localement
        ↓
    decrypted        — fichier AES-256 déchiffré
        ↓
    parsed           — JSON parsé et lignes upsertées dans le CSV cible
        ↓
    success          — tout est OK, données disponibles côté audit

À tout moment :
    error            — étape qui a échoué, error_message renseigné
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


# Statuts métier du dossier async — utilisés en clé string pour rester lisible en SQL.
JOB_STATUS_REQUESTED = "requested"
JOB_STATUS_FILE_RECEIVED = "file_received"
JOB_STATUS_DECRYPTED = "decrypted"
JOB_STATUS_PARSED = "parsed"
JOB_STATUS_SUCCESS = "success"
JOB_STATUS_ERROR = "error"

JOB_STATUSES = {
    JOB_STATUS_REQUESTED,
    JOB_STATUS_FILE_RECEIVED,
    JOB_STATUS_DECRYPTED,
    JOB_STATUS_PARSED,
    JOB_STATUS_SUCCESS,
    JOB_STATUS_ERROR,
}

# Types de données acceptés par l'API ENEDIS commanderPublicationPonctuelle.
# IDX et PMAX sont supportés par l'API mais hors périmètre actuel (voir plan).
TYPE_DONNEE_CDC = "CDC"
TYPE_DONNEE_ENERGIE = "ENERGIE"
TYPE_DONNEES_SUPPORTED = {TYPE_DONNEE_CDC, TYPE_DONNEE_ENERGIE}


class EnedisAsyncJob(Base):
    """Un dossier de publication async ENEDIS.

    Un POST commanderPublicationPonctuelle = 1 ligne avec dossier_id unique.
    Si le backfill nécessite plusieurs appels (> 1000 PRM ou > profondeur max),
    chaque appel crée une ligne distincte avec son propre dossier_id.
    """

    __tablename__ = "enedis_async_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Identifiant ENEDIS du dossier (retourné par l'API)
    dossier_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)

    # Paramètres de la demande
    type_donnee: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # CDC | ENERGIE
    date_start: Mapped[date] = mapped_column(Date, nullable=False)
    date_end: Mapped[date] = mapped_column(Date, nullable=False)
    prm_count: Mapped[int] = mapped_column(Integer, nullable=False)
    canal_contact_id: Mapped[str] = mapped_column(String(32), nullable=False)

    # Cycle de vie
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=JOB_STATUS_REQUESTED, index=True
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ftp_filename: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decrypted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Résultat
    rows_added: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Audit
    requested_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<EnedisAsyncJob id={self.id} dossier_id={self.dossier_id} "
            f"type={self.type_donnee} status={self.status}>"
        )
