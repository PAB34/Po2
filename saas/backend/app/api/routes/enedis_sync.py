from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.models.user import User
from app.services.enedis_sync import get_sync_status, is_sync_running, run_daily_consumption_sync

router = APIRouter(prefix="/energie/sync", tags=["energie-sync"])


class SyncStatus(BaseModel):
    status: str
    started_at: str | None
    finished_at: str | None
    prms_total: int
    prms_done: int
    rows_added: int
    date_from: str | None
    date_to: str | None
    last_sync_date: str | None
    error: str | None
    log: list[str]


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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une synchronisation est déjà en cours.",
        )
    background_tasks.add_task(run_daily_consumption_sync, history_days)
    return {"message": "Synchronisation démarrée en arrière-plan."}
