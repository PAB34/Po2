"""Application FastAPI PRONO — API privée Ligue 1."""
import warnings
warnings.filterwarnings("ignore")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db_and_seed
from app.auth import router as auth_router
from app.routes_ligue1 import router as ligue1_router
from app.routes_value import router as value_router

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(ligue1_router)
app.include_router(value_router)


@app.on_event("startup")
def _startup():
    init_db_and_seed()


@app.get("/api/health")
def health():
    return {"name": settings.app_name, "version": settings.app_version, "status": "ok"}


# Mode dev optionnel : servir le frontend depuis le même process (PRONO_SERVE_FRONTEND=1).
# En production, le frontend est servi par nginx + Caddy (ce bloc reste inactif).
import os as _os
if _os.environ.get("PRONO_SERVE_FRONTEND") == "1":
    from fastapi.staticfiles import StaticFiles
    _front = _os.environ.get(
        "PRONO_FRONTEND_DIR",
        _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", "frontend")))
    if _os.path.isdir(_front):
        app.mount("/", StaticFiles(directory=_front, html=True), name="frontend")
