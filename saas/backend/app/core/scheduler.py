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
from datetime import datetime, timedelta

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
                    "ENEDIS async poll : found=%d processed=%d errors=%d skipped=%d pending_requested=%s older_than_24h=%s",
                    counters["found"], counters["processed"],
                    counters["errors"], counters["skipped"],
                    counters.get("pending_requested"),
                    counters.get("pending_older_than_24h"),
                )
    except Exception:
        LOG.exception("ENEDIS async poll job failed")


def _enedis_customer_sync_job() -> None:
    """Job périodique : rafraîchit le référentiel contractuel ENEDIS."""
    if not settings.enedis_customer_sync_enabled:
        return
    if not settings.enedis_client_id or not settings.enedis_client_secret:
        return
    try:
        from app.services.enedis_customer_sync import (  # noqa: PLC0415
            is_customer_sync_running,
            run_customer_sync,
        )

        if is_customer_sync_running():
            LOG.info("ENEDIS customer sync déjà en cours, job périodique ignoré.")
            return
        run_customer_sync()
    except Exception:
        LOG.exception("ENEDIS customer sync job failed")


def _enedis_daily_sync_job() -> None:
    """Job périodique : collecte de la consommation journalière ENEDIS.

    La sync était jusqu'ici purement manuelle, ce qui laissait les données
    vieillir sans signal. La fenêtre étant incrémentale et bornée à la donnée
    réellement reçue, un passage quotidien redemande aussi les jours qu'ENEDIS
    n'avait pas encore publiés au run précédent.
    """
    if not settings.enedis_daily_sync_enabled:
        return
    if not settings.enedis_client_id or not settings.enedis_client_secret:
        return
    try:
        from app.services.enedis_sync import (  # noqa: PLC0415
            is_sync_running,
            run_daily_consumption_sync,
        )

        if is_sync_running():
            LOG.info("Sync conso journalière ENEDIS déjà en cours, job périodique ignoré.")
            return
        run_daily_consumption_sync()
    except Exception:
        LOG.exception("ENEDIS daily consumption sync job failed")


def _grdf_conso_sync_job() -> None:
    """Job périodique : synchro des consommations publiées GRDF.

    Tourne quotidiennement mais la garde par PCE (`run_recent_sync`) respecte la
    préconisation GRDF de ~1 appel/mois/PCE pour les publiées.
    """
    if not settings.grdf_conso_sync_enabled:
        return
    if not settings.grdf_client_id or not settings.grdf_client_secret:
        return
    try:
        from app.services.grdf_conso import is_sync_running, run_recent_sync  # noqa: PLC0415

        if is_sync_running():
            LOG.info("GRDF conso sync déjà en cours, job périodique ignoré.")
            return
        result = run_recent_sync()
        LOG.info("GRDF conso sync : %s", result)
    except Exception:
        LOG.exception("GRDF conso sync job failed")


def _grdf_informatives_sync_job() -> None:
    """Job quotidien optionnel : consommations informatives (PCE JJ/MM, suivi fin)."""
    if not settings.grdf_informatives_sync_enabled:
        return
    if not settings.grdf_client_id or not settings.grdf_client_secret:
        return
    try:
        from app.services.grdf_conso import is_sync_running, run_informatives_sync  # noqa: PLC0415

        if is_sync_running():
            LOG.info("GRDF sync déjà en cours, job informatives ignoré.")
            return
        result = run_informatives_sync()
        LOG.info("GRDF informatives sync : %s", result)
    except Exception:
        LOG.exception("GRDF informatives sync job failed")


def _dju_sync_job() -> None:
    """Job périodique : récupère les DJU (Open-Meteo, profils Sète + DALKIA Montpellier).

    Idempotent (reprend depuis la dernière date connue) et permissif : si le dossier
    de données n'est pas inscriptible ou Open-Meteo indisponible, l'erreur est loggée.
    """
    if not settings.dju_sync_enabled:
        return
    try:
        from app.services.dju_sync import is_dju_running, run_dju_sync  # noqa: PLC0415

        if is_dju_running():
            LOG.info("DJU sync déjà en cours, job périodique ignoré.")
            return
        run_dju_sync()
    except Exception:
        LOG.exception("DJU sync job failed")


def _pronostics_score_sync_job() -> None:
    """Rafraîchit les scores réels du jeu sans bloquer les autres tâches."""
    if not settings.pronostics_score_sync_enabled or not settings.football_data_token:
        return
    try:
        from app.services.pronostics import sync_scores  # noqa: PLC0415

        with _scoped_session() as db:
            result = sync_scores(db)
            if result["updated"] or result["unmatched"]:
                LOG.info("Pronostics score sync : %s", result)
    except Exception:
        LOG.exception("Pronostics score sync job failed")


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
    if settings.enedis_customer_sync_enabled:
        customer_interval = max(int(settings.enedis_customer_sync_interval_hours), 1)
        _SCHEDULER.add_job(
            _enedis_customer_sync_job,
            trigger="interval",
            hours=customer_interval,
            id="enedis_customer_sync",
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )
    if settings.enedis_daily_sync_enabled:
        daily_interval = max(int(settings.enedis_daily_sync_interval_hours), 1)
        _SCHEDULER.add_job(
            _enedis_daily_sync_job,
            trigger="interval",
            hours=daily_interval,
            id="enedis_daily_sync",
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )
    if settings.grdf_conso_sync_enabled:
        grdf_interval = max(int(settings.grdf_conso_sync_interval_hours), 1)
        _SCHEDULER.add_job(
            _grdf_conso_sync_job,
            trigger="interval",
            hours=grdf_interval,
            id="grdf_conso_sync",
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )
    if settings.grdf_informatives_sync_enabled:
        _SCHEDULER.add_job(
            _grdf_informatives_sync_job,
            trigger="interval",
            hours=max(int(settings.grdf_conso_sync_interval_hours), 1),
            id="grdf_informatives_sync",
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )
    if settings.dju_sync_enabled:
        dju_interval = max(int(settings.dju_sync_interval_hours), 1)
        _SCHEDULER.add_job(
            _dju_sync_job,
            trigger="interval",
            hours=dju_interval,
            id="dju_sync",
            max_instances=1,
            coalesce=True,
            replace_existing=True,
            # Premier passage peu après le boot pour remplir sans attendre l'intervalle.
            next_run_time=datetime.now() + timedelta(seconds=30),
        )
    if settings.pronostics_score_sync_enabled:
        score_interval = max(int(settings.pronostics_score_sync_interval_hours), 1)
        _SCHEDULER.add_job(
            _pronostics_score_sync_job,
            trigger="interval",
            hours=score_interval,
            id="pronostics_score_sync",
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
