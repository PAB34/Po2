import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.scheduler import start_scheduler, stop_scheduler

LOG = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
def _on_startup() -> None:
    try:
        start_scheduler()
    except Exception:
        LOG.exception("Échec du démarrage du scheduler ENEDIS async")


@app.on_event("shutdown")
def _on_shutdown() -> None:
    try:
        stop_scheduler()
    except Exception:
        LOG.exception("Échec de l'arrêt du scheduler ENEDIS async")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"name": settings.app_name, "version": settings.app_version}
