"""Routes Ligue 1 — toutes protégées par la même auth JWT (get_current_user)."""
from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.ligue1 import service

router = APIRouter(prefix="/api/ligue1", tags=["ligue1"])


@router.get("/journee")
def journee(refresh: int = 0, user=Depends(get_current_user)):
    return service.build_journee(force=bool(refresh))


@router.get("/news")
def news(team: str = Query(...), user=Depends(get_current_user)):
    return service.team_news(team)


@router.get("/health")
def health(user=Depends(get_current_user)):
    return service.health()
