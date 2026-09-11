"""Périmètre des PRM pris en compte dans les calculs.

Un PRM peut figurer dans les factures sans relever du périmètre exploité : c'est le
cas des points de livraison de Sète Agglopôle Méditerranée, facturés via le même
groupement de commandes que la Ville (marché 2024-FCS-03) alors que la plateforme ne
traite que la Ville.

Le mécanisme de mise à l'écart existait déjà : `EnergyAccountingSiteMapping.active`,
une ligne par PRM, alimentée automatiquement depuis les factures. Il n'était
jusqu'ici qu'affiché, jamais appliqué. Ce module le rend effectif.

Principe retenu : **on masque, on ne supprime pas**. Les factures et leurs lignes
restent intégralement en base — seuls les calculs et les restitutions ignorent les
PRM désactivés. Réactiver un PRM est un simple passage de `active` à `True`.

Un site sans PRM (`prm_id` nul) n'est jamais écarté : il n'est pas identifiable, donc
rien ne permet d'affirmer qu'il est hors périmètre.

Voir `docs/refonte-v1/enedis-referentiel-prm-qualite-decisions.md` (décision D5).
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.invoice import EnergyAccountingSiteMapping, EnergyInvoiceSite


def _inactive_prm_subquery(city_id: int | None):
    stmt = select(EnergyAccountingSiteMapping.prm_id).where(
        EnergyAccountingSiteMapping.active.is_(False),
        EnergyAccountingSiteMapping.prm_id.isnot(None),
    )
    if city_id is not None:
        stmt = stmt.where(EnergyAccountingSiteMapping.city_id == city_id)
    return stmt


def in_scope_clause(city_id: int | None):
    """Condition SQL à ajouter à un `select()` portant sur `EnergyInvoiceSite`.

    Écarte les sites dont le PRM est désactivé, en conservant les sites sans PRM.
    """
    return or_(
        EnergyInvoiceSite.prm_id.is_(None),
        EnergyInvoiceSite.prm_id.not_in(_inactive_prm_subquery(city_id)),
    )


def inactive_prm_ids(db: Session, city_id: int | None) -> set[str]:
    """Ensemble des PRM désactivés, pour les filtrages côté Python."""
    return {
        prm.strip()
        for (prm,) in db.execute(_inactive_prm_subquery(city_id)).all()
        if prm and prm.strip()
    }


def is_in_scope(prm_id: str | None, inactive: set[str]) -> bool:
    """Un site est dans le périmètre s'il n'a pas de PRM, ou si son PRM est actif."""
    cleaned = (prm_id or "").strip()
    if not cleaned:
        return True
    return cleaned not in inactive
