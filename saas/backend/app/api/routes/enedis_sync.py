import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.services.dju_sync import get_dju_sync_status, is_dju_running, run_dju_sync
from app.services.enedis_customer_sync import (
    get_customer_sync_status,
    is_customer_sync_running,
    run_customer_sync,
)
from app.services.enedis_sync import (
    get_load_curve_status,
    get_max_power_status,
    get_sync_status,
    is_load_curve_running,
    is_max_power_running,
    is_sync_running,
    run_daily_consumption_sync,
    run_load_curve_sync,
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


class CustomerSyncStatus(BaseModel):
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    last_sync_at: str | None = None
    sources_total: int = 0
    sources_done: int = 0
    current_source: str | None = None
    prms_total: int = 0
    prms_done: int = 0
    rows_upserted: int = 0
    changes_detected: int = 0
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
    prm_limit: int | None = Query(default=None, ge=1, le=50),
    current_user: User = Depends(get_current_user),
) -> dict:
    if is_sync_running():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Une synchronisation est déjà en cours.")
    background_tasks.add_task(run_daily_consumption_sync, history_days, prm_limit)
    suffix = f" sur les {prm_limit} premiers PRM" if prm_limit else ""
    return {"message": f"Synchronisation consommation démarrée{suffix}."}


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
    prm_limit: int | None = Query(default=None, ge=1, le=50),
    current_user: User = Depends(get_current_user),
) -> dict:
    if is_max_power_running():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Une synchronisation puissance max est déjà en cours.")
    background_tasks.add_task(run_max_power_sync, history_days, prm_limit)
    suffix = f" sur les {prm_limit} premiers PRM" if prm_limit else ""
    return {"message": f"Synchronisation puissance max démarrée{suffix}."}


# ---------------------------------------------------------------------------
# Courbe de charge 30 min
# ---------------------------------------------------------------------------

class LoadCurveSyncStatus(BaseModel):
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    chunks_total: int = 0
    chunks_done: int = 0
    rows_added: int = 0
    date_from: str | None = None
    date_to: str | None = None
    last_sync_date: str | None = None
    error: str | None = None
    log: list[str] = []


@router.get("/load-curve/status", response_model=LoadCurveSyncStatus)
def load_curve_status(current_user: User = Depends(get_current_user)) -> LoadCurveSyncStatus:
    return LoadCurveSyncStatus.model_validate(get_load_curve_status())


@router.post("/load-curve/start", status_code=status.HTTP_202_ACCEPTED)
def load_curve_start(
    background_tasks: BackgroundTasks,
    reset_state: bool = Query(default=False),
    history_days: int | None = Query(default=None, ge=1, le=730),
    prm_limit: int | None = Query(default=None, ge=1, le=50),
    current_user: User = Depends(get_current_user),
) -> dict:
    if is_load_curve_running():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Une synchronisation courbe de charge est déjà en cours.")
    background_tasks.add_task(run_load_curve_sync, reset_state, prm_limit, history_days)
    msg = "Synchronisation courbe de charge démarrée"
    if prm_limit:
        msg += f" sur les {prm_limit} premiers PRM"
    if reset_state:
        msg += " (backfill complet depuis enedis_load_curve_start)."
    elif history_days:
        msg += f" ({history_days} derniers jours)."
    else:
        msg += " (incrémentale depuis last_sync_date)."
    return {"message": msg}


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


# ---------------------------------------------------------------------------
# Référentiel contractuel ENEDIS
# ---------------------------------------------------------------------------

@router.get("/customer/status", response_model=CustomerSyncStatus)
def customer_status(current_user: User = Depends(get_current_user)) -> CustomerSyncStatus:
    return CustomerSyncStatus.model_validate(get_customer_sync_status())


@router.post("/customer/start", status_code=status.HTTP_202_ACCEPTED)
def customer_start(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
) -> dict:
    if is_customer_sync_running():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Une synchronisation contractuelle ENEDIS est déjà en cours.")
    background_tasks.add_task(run_customer_sync)
    return {"message": "Synchronisation du référentiel contractuel ENEDIS démarrée."}


# ---------------------------------------------------------------------------
# Diagnostics — exposition brute des rapports JSON pour analyse
# ---------------------------------------------------------------------------

_DIAG_FILES = {
    "consumption": "enedis_data_diagnostic.json",
    "max_power": "enedis_mp_diagnostic.json",
    "load_curve": "enedis_lc_report.json",
}


@router.get("/diagnostics/{source}")
def diagnostics(
    source: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Expose le rapport JSON brut généré par chaque sync.

    source ∈ {consumption, max_power, load_curve}
    Pour load_curve : retourne aussi un échantillon des 10 premières erreurs techniques
    avec le détail HTTP (utile pour diagnostiquer un échec massif).
    """
    if source not in _DIAG_FILES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source inconnue : {source}")
    path = Path(settings.energie_dir) / _DIAG_FILES[source]
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnostic indisponible — la sync n'a pas encore été exécutée ({path.name}).",
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lecture impossible : {exc}") from exc

    if source == "load_curve" and isinstance(data, dict):
        retry_list = data.get("retry_list") or []
        sample = [item for item in retry_list if item.get("outcome") == "error_technical"][:10]
        data = {**data, "error_technical_sample": sample}
    return data
