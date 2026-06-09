"""Routes GRDF ADICT — gaz.

- Référentiel PCE : liste en base + resynchro depuis l'API (`GET /droits_acces`).
- Consommations : déclenchement backfill / synchro récente (tâches de fond) + statut.
- Enrichissement contractuel / technique des PCE.

Toutes les routes sont scopées à la ville de l'utilisateur courant.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.gas import GasPce
from app.models.user import User
from app.services.grdf_conso import (
    get_sync_status,
    is_sync_running,
    run_backfill,
    run_recent_sync,
)

router = APIRouter(prefix="/grdf", tags=["grdf"])


class GasPceOut(BaseModel):
    id: int
    id_pce: str
    nom_site: str | None = None
    nom_titulaire: str | None = None
    role_tiers: str
    etat_droit_acces: str | None = None
    perim_publiees: bool
    tarif_acheminement: str | None = None
    car_actuelle: int | None = None
    frequence_releve: str | None = None

    model_config = {"from_attributes": True}


class ConsoSyncStatus(BaseModel):
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    pce_total: int = 0
    pce_done: int = 0
    rows_upserted: int = 0
    mode: str | None = None
    error: str | None = None
    log: list[str] = []


@router.get("/pces", response_model=list[GasPceOut])
def list_pces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[GasPce]:
    return (
        db.query(GasPce)
        .filter(GasPce.city_id == current_user.city_id)
        .order_by(GasPce.nom_site)
        .all()
    )


@router.post("/pces/sync", status_code=status.HTTP_200_OK)
def sync_pces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Resynchronise le référentiel PCE depuis l'API GRDF (source de vérité)."""
    from app.services.grdf_gda import sync_droits  # noqa: PLC0415

    return sync_droits(db, city_id=current_user.city_id)


@router.get("/conso/status", response_model=ConsoSyncStatus)
def conso_status(current_user: User = Depends(get_current_user)) -> ConsoSyncStatus:
    return ConsoSyncStatus.model_validate(get_sync_status())


@router.post("/conso/backfill", status_code=status.HTTP_202_ACCEPTED)
def conso_backfill(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
) -> dict:
    if is_sync_running():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Une synchronisation gaz est déjà en cours.")
    background_tasks.add_task(run_backfill, None)
    return {"message": "Backfill consommations gaz démarré."}


@router.post("/conso/sync", status_code=status.HTTP_202_ACCEPTED)
def conso_sync(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
) -> dict:
    if is_sync_running():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Une synchronisation gaz est déjà en cours.")
    background_tasks.add_task(run_recent_sync)
    return {"message": "Synchronisation incrémentale gaz démarrée."}


@router.post("/contractuel/enrich", status_code=status.HTTP_200_OK)
def enrich_contractuel(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Enrichit les PCE (tarif, CAR, profil, fréquence, calibre) depuis l'API."""
    from app.services.grdf_contractuel import enrich_pces  # noqa: PLC0415

    return enrich_pces(db, city_id=current_user.city_id)


# ---------------------------------------------------------------------------
# Analytics — suivi temporel + rapprochement P1 DALKIA (Phase 5)
# ---------------------------------------------------------------------------

class MonthlyPointOut(BaseModel):
    model_config = {"from_attributes": True}
    annee: int
    mois: int
    energie_kwh: int
    mwh_pcs: float


class MonthlySeriesOut(BaseModel):
    model_config = {"from_attributes": True}
    id_pce: str
    nom_site: str | None = None
    total_kwh: int
    points: list[MonthlyPointOut]


class P1ReconcileItemOut(BaseModel):
    model_config = {"from_attributes": True}
    id_pce: str
    code_site: str | None = None
    nom_site: str | None = None
    grdf_mwh_pcs: float
    dalkia_p1_qt_mwhpcs: float | None = None
    dalkia_conso_mwh: float | None = None
    p1_total_ht: float | None = None
    ecart_mwh: float | None = None
    ecart_pct: float | None = None
    statut: str


@router.get("/conso/monthly", response_model=list[MonthlySeriesOut])
def conso_monthly(
    id_pce: str | None = None,
    building_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    """Série mensuelle de consommation GRDF (suivi temporel), par PCE."""
    from app.services.gas_analytics import monthly_series  # noqa: PLC0415

    return monthly_series(db, city_id=current_user.city_id, id_pce=id_pce, building_id=building_id)


@router.get("/rapprochement-p1/{year}", response_model=list[P1ReconcileItemOut])
def rapprochement_p1(
    year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    """Rapproche la conso GRDF réelle de la quantité P1 GAZ DALKIA, par PCE × année."""
    from app.services.gas_analytics import reconcile_p1  # noqa: PLC0415

    return reconcile_p1(db, city_id=current_user.city_id, year=year)
