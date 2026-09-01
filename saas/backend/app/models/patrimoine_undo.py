"""Journal d'annulation de l'écran de rapprochement ASTECH ↔ Po2.

Une entrée = **une action de l'utilisateur**, avec l'état des lignes touchées AVANT et
APRÈS. Annuler consiste à réécrire l'état d'avant, pas à jouer une action inverse
approximative : une création s'annule en supprimant, une suppression en réinsérant la
ligne telle qu'elle était — identifiant d'origine compris, sans quoi les biens ASTECH qui
la désignaient pointeraient dans le vide.

Le journal est **par collectivité** et ne conserve qu'une pile courte : il sert à
rattraper le geste qu'on vient de faire, pas à tenir un historique. La traçabilité, elle,
vit ailleurs (`link_origin`, `notes`, feuille de traçabilité du réexport).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class PatrimoineUndoEntry(Base):
    __tablename__ = "patrimoine_undo_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int] = mapped_column(
        ForeignKey("cities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Auteur du geste, pour ne jamais proposer à quelqu'un d'annuler l'action d'un autre.
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Libellé lisible : c'est ce que le bouton d'annulation affiche.
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    # Liste de clichés : [{"table": ..., "pk": ..., "before": {...}|null, "after": {...}|null}]
    snapshots_json: Mapped[str] = mapped_column(Text, nullable=False)
    # Une entrée annulée reste en base, marquée, plutôt que d'être effacée : sinon
    # « annuler » deux fois de suite remonterait la pile sans qu'on l'ait demandé.
    undone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
