"""
Données contractuelles et techniques GRDF ADICT → enrichissement de `gas_pces`.

`fetch_donnees_contractuelles` : tarif d'acheminement, CAR, profil.
`fetch_donnees_techniques` : fréquence de relevé, calibre, adresse.
`enrich_pces` boucle sur les PCE actifs au périmètre accordé et met à jour le cache.

Données peu volumineuses et stables → on les met en cache dans `gas_pces` pour les
jointures et l'affichage, mais l'API reste la source de vérité (rafraîchir au besoin).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.gas import GasPce
from app.services.grdf_client import GrdfApiError, get_json

LOG = logging.getLogger(__name__)


def _to_int(value: Any) -> int | None:
    try:
        return int(round(float(value))) if value is not None else None
    except (TypeError, ValueError):
        return None


def fetch_donnees_contractuelles(id_pce: str) -> dict:
    payload = get_json(f"/pce/{id_pce}/donnees_contractuelles") or {}
    dc = payload.get("donnees_contractuelles") or {}
    car = dc.get("car") or {}
    profil = dc.get("profil") or {}
    return {
        "tarif_acheminement": dc.get("tarif_acheminement"),
        "car_actuelle": _to_int(car.get("car_actuelle")),
        "profil_type": profil.get("profil_type_actuel"),
    }


def fetch_donnees_techniques(id_pce: str) -> dict:
    payload = get_json(f"/pce/{id_pce}/donnees_techniques") or {}
    dt = payload.get("donnees_techniques") or {}
    carac = dt.get("caracteristiques_compteur") or {}
    return {
        "frequence_releve": carac.get("frequence"),
        "code_calibre": carac.get("code_calibre"),
    }


def enrich_pces(db: Session, city_id: int | None = None) -> dict:
    """Met à jour tarif/CAR/profil/fréquence/calibre des PCE actifs accordés."""
    q = db.query(GasPce).filter(GasPce.etat_droit_acces == "Active")
    if city_id is not None:
        q = q.filter(GasPce.city_id == city_id)
    pces = q.all()
    done = errors = 0
    for pce in pces:
        try:
            if pce.perim_contractuelles:
                for k, v in fetch_donnees_contractuelles(pce.id_pce).items():
                    if v is not None:
                        setattr(pce, k, v)
            if pce.perim_techniques:
                for k, v in fetch_donnees_techniques(pce.id_pce).items():
                    if v is not None:
                        setattr(pce, k, v)
            pce.last_synced_at = datetime.utcnow()
            db.commit()
            done += 1
        except GrdfApiError as exc:
            db.rollback()
            errors += 1
            LOG.warning("Enrichissement PCE %s échoué : %s", pce.id_pce, exc)
    LOG.info("GRDF enrichissement : %d PCE traités, %d erreurs", done, errors)
    return {"pce_total": len(pces), "done": done, "errors": errors}
