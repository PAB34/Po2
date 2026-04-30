from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.models.user import User
from app.services.dju_sync import get_dju_sync_status, is_dju_running, run_dju_sync
from app.services.enedis_sync import (
    get_max_power_status,
    get_sync_status,
    is_max_power_running,
    is_sync_running,
    run_daily_consumption_sync,
    run_max_power_sync,
)

router = APIRouter(prefix="/energie/sync", tags=["energie-sync"])


class SyncStatus(BaseModel):
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    prms_total: int = 0
    prms_done: int = 0
    rows_added: int = 0
    date_from: str | None = None
    date_to: str | None = None
    last_sync_date: str | None = None
    error: str | None = None
    log: list[str] = []


class DjuSyncStatus(BaseModel):
    status: str
    last_sync_date: str | None = None
    rows_added: int = 0
    error: str | None = None
    log: list[str] = []


# ---------------------------------------------------------------------------
# Consommation journalière
# ---------------------------------------------------------------------------

@router.get("/status", response_model=SyncStatus)
def sync_status(current_user: User = Depends(get_current_user)) -> SyncStatus:
    return SyncStatus.model_validate(get_sync_status())


@router.post("/start", status_code=status.HTTP_202_ACCEPTED)
def sync_start(
    background_tasks: BackgroundTasks,
    history_days: int | None = Query(default=None, ge=1, le=1110),
    current_user: User = Depends(get_current_user),
) -> dict:
    if is_sync_running():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Une synchronisation est déjà en cours.")
    background_tasks.add_task(run_daily_consumption_sync, history_days)
    return {"message": "Synchronisation consommation démarrée."}


# ---------------------------------------------------------------------------
# Puissance max journalière
# ---------------------------------------------------------------------------

@router.get("/max-power/status", response_model=SyncStatus)
def max_power_status(current_user: User = Depends(get_current_user)) -> SyncStatus:
    return SyncStatus.model_validate(get_max_power_status())


@router.post("/max-power/start", status_code=status.HTTP_202_ACCEPTED)
def max_power_start(
    background_tasks: BackgroundTasks,
    history_days: int | None = Query(default=None, ge=1, le=1110),
    current_user: User = Depends(get_current_user),
) -> dict:
    if is_max_power_running():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Une synchronisation puissance max est déjà en cours.")
    background_tasks.add_task(run_max_power_sync, history_days)
    return {"message": "Synchronisation puissance max démarrée."}


# ---------------------------------------------------------------------------
# DJU Open-Meteo
# ---------------------------------------------------------------------------

@router.get("/dju/status", response_model=DjuSyncStatus)
def dju_status(current_user: User = Depends(get_current_user)) -> DjuSyncStatus:
    return DjuSyncStatus.model_validate(get_dju_sync_status())


@router.post("/dju/start", status_code=status.HTTP_202_ACCEPTED)
def dju_start(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
) -> dict:
    if is_dju_running():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Une synchronisation DJU est déjà en cours.")
    background_tasks.add_task(run_dju_sync)
    return {"message": "Synchronisation DJU démarrée."}
