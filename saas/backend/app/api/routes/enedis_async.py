"""
Endpoints HTTP pour la pipeline async ENEDIS (Phase B-3).

- POST /energie/sync/async/start          → lance un job pour 1 type sur 1 période
- POST /energie/sync/async/backfill-full  → lance ENERGIE 3 ans + CDC 2 ans découpés
- GET  /energie/sync/async/jobs           → liste filtrable des dossiers
- POST /energie/sync/async/poll-now       → déclenche un poll FTP immédiat
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from threading import Lock, Thread
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import SessionLocal, get_db
from app.core.scheduler import trigger_poll_now
from app.models.enedis_async import (
    JOB_STATUSES,
    TYPE_DONNEE_CDC,
    TYPE_DONNEE_ENERGIE,
    TYPE_DONNEES_SUPPORTED,
    EnedisAsyncJob,
)
from app.models.user import User
from app.services.enedis_async import (
    backfill_full_period,
    kickoff_backfill,
    plan_backfill_full_period,
)

router = APIRouter(prefix="/energie/sync/async", tags=["energie-async"])
LOG = logging.getLogger(__name__)
_BACKFILL_FULL_LOCK = Lock()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class StartAsyncRequest(BaseModel):
    type_donnee: Literal["CDC", "ENERGIE"]
    date_start: date
    date_end: date


class AsyncJobOut(BaseModel):
    id: int
    dossier_id: int
    type_donnee: str
    date_start: date
    date_end: date
    prm_count: int
    canal_contact_id: str
    status: str
    requested_at: str | None
    ftp_filename: str | None
    received_at: str | None
    parsed_at: str | None
    finished_at: str | None
    rows_added: int | None
    error_message: str | None

    class Config:
        from_attributes = True


class AsyncJobsSummaryOut(BaseModel):
    total: int
    by_status: dict[str, int]
    by_type: dict[str, dict[str, int]]
    inflight_count: int
    terminal_count: int
    error_count: int
    stale_requested_count: int
    oldest_inflight_at: str | None
    latest_requested_at: str | None
    latest_finished_at: str | None
    backfill_creation_running: bool
    plan: dict[str, dict]


def _serialize_job(job: EnedisAsyncJob) -> AsyncJobOut:
    return AsyncJobOut(
        id=job.id,
        dossier_id=job.dossier_id,
        type_donnee=job.type_donnee,
        date_start=job.date_start,
        date_end=job.date_end,
        prm_count=job.prm_count,
        canal_contact_id=job.canal_contact_id,
        status=job.status,
        requested_at=job.requested_at.isoformat() if job.requested_at else None,
        ftp_filename=job.ftp_filename,
        received_at=job.received_at.isoformat() if job.received_at else None,
        parsed_at=job.parsed_at.isoformat() if job.parsed_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
        rows_added=job.rows_added,
        error_message=job.error_message,
    )


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/start", status_code=status.HTTP_201_CREATED)
def start_async_job(
    payload: StartAsyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Lance un job async ENEDIS pour le type/période spécifiés (sur tous les PRM connus)."""
    try:
        jobs = kickoff_backfill(
            db,
            type_donnee=payload.type_donnee,
            date_start=payload.date_start,
            date_end=payload.date_end,
            requested_by_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {
        "message": f"{len(jobs)} dossier(s) ENEDIS créé(s)",
        "dossier_ids": [j.dossier_id for j in jobs],
        "jobs": [_serialize_job(j).model_dump() for j in jobs],
    }


def _backfill_full_legacy(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Lance le backfill complet : ENERGIE 3 ans + CDC 2 ans en fenêtres."""
    try:
        dossiers = backfill_full_period(db, requested_by_user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {
        "message": "Backfill complet ENEDIS lancé (ENERGIE 3 ans + CDC 2 ans fractionnés par fenêtres).",
        "dossier_ids": {
            "ENERGIE": dossiers.get("ENERGIE", []),
            "CDC": dossiers.get("CDC", []),
        },
        "errors": dossiers.get("errors", []),
        "summary": dossiers.get("summary", {}),
    }


def _run_backfill_full_locked(requested_by_user_id: int) -> None:
    db = SessionLocal()
    try:
        backfill_full_period(db, requested_by_user_id=requested_by_user_id)
    except Exception:
        LOG.exception("Backfill complet ENEDIS async echoue")
    finally:
        db.close()
        _BACKFILL_FULL_LOCK.release()


@router.post("/backfill-full", status_code=status.HTTP_202_ACCEPTED)
def backfill_full(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Planifie le backfill complet dans un thread serveur detache."""
    plan = plan_backfill_full_period()
    if not _BACKFILL_FULL_LOCK.acquire(blocking=False):
        return {
            "message": "Backfill complet ENEDIS deja en cours. Le tableau des dossiers se met a jour progressivement.",
            "background": True,
            "already_running": True,
            "dossier_ids": {"ENERGIE": [], "CDC": []},
            "errors": [],
            "summary": plan,
        }

    Thread(
        target=_run_backfill_full_locked,
        args=(current_user.id,),
        daemon=True,
        name="enedis-backfill-full",
    ).start()
    return {
        "message": "Backfill complet ENEDIS lance en arriere-plan. Les dossiers vont apparaitre progressivement dans le tableau.",
        "background": True,
        "already_running": False,
        "dossier_ids": {"ENERGIE": [], "CDC": []},
        "errors": [],
        "summary": plan,
    }


@router.get("/jobs", response_model=list[AsyncJobOut])
def list_async_jobs(
    type_donnee: str | None = Query(None, description="CDC ou ENERGIE"),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AsyncJobOut]:
    """Liste paginée des dossiers async, plus récents d'abord."""
    if type_donnee and type_donnee not in TYPE_DONNEES_SUPPORTED:
        raise HTTPException(
            status_code=400,
            detail=f"type_donnee doit être dans {TYPE_DONNEES_SUPPORTED}",
        )
    if status_filter and status_filter not in JOB_STATUSES:
        raise HTTPException(
            status_code=400, detail=f"status invalide. Valides : {sorted(JOB_STATUSES)}"
        )
    q = db.query(EnedisAsyncJob).order_by(EnedisAsyncJob.requested_at.desc())
    if type_donnee:
        q = q.filter(EnedisAsyncJob.type_donnee == type_donnee)
    if status_filter:
        q = q.filter(EnedisAsyncJob.status == status_filter)
    return [_serialize_job(j) for j in q.limit(limit).all()]


@router.get("/jobs/summary", response_model=AsyncJobsSummaryOut)
def summarize_async_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AsyncJobsSummaryOut:
    """Retourne les compteurs globaux de suivi, sans limite de pagination."""
    rows = (
        db.query(
            EnedisAsyncJob.type_donnee,
            EnedisAsyncJob.status,
            func.count(EnedisAsyncJob.id),
        )
        .group_by(EnedisAsyncJob.type_donnee, EnedisAsyncJob.status)
        .all()
    )

    by_status = {status_name: 0 for status_name in sorted(JOB_STATUSES)}
    by_type: dict[str, dict[str, int]] = {
        type_name: {status_name: 0 for status_name in sorted(JOB_STATUSES)}
        for type_name in sorted(TYPE_DONNEES_SUPPORTED)
    }
    total = 0
    for type_donnee, status_name, count in rows:
        count_int = int(count)
        total += count_int
        by_status[status_name] = by_status.get(status_name, 0) + count_int
        by_type.setdefault(type_donnee, {s: 0 for s in sorted(JOB_STATUSES)})
        by_type[type_donnee][status_name] = by_type[type_donnee].get(status_name, 0) + count_int

    terminal_count = by_status.get("success", 0) + by_status.get("error", 0)
    error_count = by_status.get("error", 0)
    inflight_statuses = ["requested", "file_received", "decrypted", "parsed"]
    inflight_count = sum(by_status.get(status_name, 0) for status_name in inflight_statuses)

    stale_before = datetime.now(timezone.utc) - timedelta(hours=24)
    stale_requested_count = int(
        db.query(func.count(EnedisAsyncJob.id))
        .filter(EnedisAsyncJob.status == "requested")
        .filter(EnedisAsyncJob.requested_at < stale_before)
        .scalar()
        or 0
    )
    oldest_inflight_at = (
        db.query(func.min(EnedisAsyncJob.requested_at))
        .filter(EnedisAsyncJob.status.in_(inflight_statuses))
        .scalar()
    )
    latest_requested_at = db.query(func.max(EnedisAsyncJob.requested_at)).scalar()
    latest_finished_at = db.query(func.max(EnedisAsyncJob.finished_at)).scalar()

    return AsyncJobsSummaryOut(
        total=total,
        by_status=by_status,
        by_type=by_type,
        inflight_count=inflight_count,
        terminal_count=terminal_count,
        error_count=error_count,
        stale_requested_count=stale_requested_count,
        oldest_inflight_at=_iso(oldest_inflight_at),
        latest_requested_at=_iso(latest_requested_at),
        latest_finished_at=_iso(latest_finished_at),
        backfill_creation_running=_BACKFILL_FULL_LOCK.locked(),
        plan=plan_backfill_full_period(),
    )


@router.get("/jobs/{job_id}", response_model=AsyncJobOut)
def get_async_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AsyncJobOut:
    job = db.query(EnedisAsyncJob).filter(EnedisAsyncJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job introuvable")
    return _serialize_job(job)


@router.post("/poll-now", status_code=status.HTTP_202_ACCEPTED)
def poll_ftp_now(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Déclenche un poll FTP immédiat (sans attendre le prochain cycle scheduler)."""
    background_tasks.add_task(trigger_poll_now)
    return {"message": "Poll FTP déclenché en arrière-plan."}
