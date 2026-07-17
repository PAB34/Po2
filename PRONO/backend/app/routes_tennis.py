"""Routes Tennis protegees par l'auth JWT PRONO."""
import time

from fastapi import APIRouter, Depends

from app import tennis
from app.auth import get_current_user


router = APIRouter(prefix="/api/tennis", tags=["tennis"])

_CACHE = {"data": None, "ts": 0.0}
_BRACKET_CACHE = {"data": None, "ts": 0.0}
CACHE_TTL = 1800
BRACKET_CACHE_TTL = 3600


def _payload(force: bool = False) -> dict:
    if force or _CACHE["data"] is None or (time.time() - _CACHE["ts"]) > CACHE_TTL:
        _CACHE["data"] = tennis.build_tennis()
        _CACHE["ts"] = time.time()
    return _CACHE["data"]


def _brackets_payload(force: bool = False) -> dict:
    if force or _BRACKET_CACHE["data"] is None or (time.time() - _BRACKET_CACHE["ts"]) > BRACKET_CACHE_TTL:
        _BRACKET_CACHE["data"] = tennis.build_tennis_brackets()
        _BRACKET_CACHE["ts"] = time.time()
    return _BRACKET_CACHE["data"]


@router.get("/matches")
def tennis_matches(refresh: int = 0, user=Depends(get_current_user)):
    return _payload(force=bool(refresh))


@router.get("/brackets")
def tennis_brackets(refresh: int = 0, user=Depends(get_current_user)):
    return _brackets_payload(force=bool(refresh))


@router.get("")
def tennis_matches_root(refresh: int = 0, user=Depends(get_current_user)):
    return _payload(force=bool(refresh))


@router.get("/")
def tennis_matches_slash(refresh: int = 0, user=Depends(get_current_user)):
    return _payload(force=bool(refresh))
