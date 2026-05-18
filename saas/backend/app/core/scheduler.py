"""
APScheduler init pour les tâches d'arrière-plan ENEDIS async.

Démarre un BackgroundScheduler au boot de l'API FastAPI. Le job principal
appelle `poll_and_process` toutes les N minutes (configurable via
`enedis_async_poll_interval_minutes`) pour récupérer les fichiers déposés
par ENEDIS sur le FTP, les déchiffrer et les ingérer.

Le scheduler est volontairement permissif :
- Si les vars FTP/ENEDIS sont vides → le job ne fait rien (no-op)
- Si le poll échoue → l'exception est loggée, le scheduler continue
- Idempotence : process_one_file skip les fichiers déjà traités
"""
from __future__ import annotations

import logging
from contextlib import contextmanager

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.db import SessionLocal

LOG = logging.getLogger(__name__)

_SCHEDULER: BackgroundScheduler | None = None


@contextmanager
def _scoped_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _enedis_async_poll_job() -> None:
    """Job appelé périodiquement : poll FTP + traite les nouveaux fichiers."""
    # No-op si la config FTP/ENEDIS n'est pas remplie (évite spam d'erreurs en dev)
    if not settings.ftp_host or not settings.ftp_user or not settings.enedis_canal_contact_id:
        return
    try:
        from app.services.enedis_async import poll_and_process  # noqa: PLC0415
        with _scoped_session() as db:
            counters = poll_and_process(db)
            if counters["found"] > 0 or counters["processed"] > 0:
                LOG.info(
                    "ENEDIS async poll : found=%d processed=%d errors=%d skipped=%d",
                    counters["found"], counters["processed"],
                    counters["errors"], counters["skipped"],
                )
    except Exception:
        LOG.exception("ENEDIS async poll job failed")


def start_scheduler() -> None:
    """À appeler une fois au startup de l'application FastAPI."""
    global _SCHEDULER
    if _SCHEDULER is not None:
        LOG.warning("Scheduler déjà démarré, skip.")
        return
    interval = max(int(settings.enedis_async_poll_interval_minutes), 1)
    _SCHEDULER = BackgroundScheduler(timezone="UTC")
    _SCHEDULER.add_job(
        _enedis_async_poll_job,
        trigger="interval",
        minutes=interval,
        id="enedis_async_poll",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    _SCHEDULER.start()
    LOG.info("APScheduler démarré (poll ENEDIS async toutes les %d min)", interval)


def stop_scheduler() -> None:
    """À appeler au shutdown de l'application FastAPI."""
    global _SCHEDULER
    if _SCHEDULER is not None:
        _SCHEDULER.shutdown(wait=False)
        _SCHEDULER = None
        LOG.info("APScheduler arrêté.")


def trigger_poll_now() -> None:
    """Déclenche manuellement un poll immédiat (utile pour debug/endpoint)."""
    _enedis_async_poll_job()
