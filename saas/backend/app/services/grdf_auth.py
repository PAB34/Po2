"""
Authentification et limitation de débit pour l'API GRDF ADICT.

Calqué sur `enedis_common.py` (même mécanique éprouvée) mais adapté à GRDF :
- OAuth2 ``client_credentials`` avec un ``scope`` (/adict/v2) — token API valide ~4h.
- ``RateLimiter`` réutilisé tel quel depuis `enedis_common` (3 contraintes : rps,
  concurrence, quota horaire), paramétré via les settings ``grdf_*``.

Le token *API Data* récupéré ici sert à TOUS les appels API (GDA, CONSO,
contractuel, technique). Il ne faut PAS le confondre avec le token
``authorization_code`` du parcours Client Connect (décodage du consentement),
qui n'est pas géré par ce module.

Utilisation typique :
    tm = get_token_manager()
    headers = {"Authorization": f"Bearer {tm.get()}"}
"""
from __future__ import annotations

import logging
import threading
import time as _time
from typing import Optional

import requests

from app.core.config import settings
from app.services.enedis_common import RateLimiter

LOG = logging.getLogger(__name__)


def get_oauth_token() -> tuple[str, int]:
    """
    Récupère un access token GRDF ADICT via OAuth2 client_credentials.

    Retourne ``(access_token, expires_in_seconds)``. Lève RuntimeError si les
    credentials ne sont pas configurés ou si l'API ne retourne pas de token.
    """
    if not settings.grdf_client_id or not settings.grdf_client_secret:
        raise RuntimeError(
            "GRDF_CLIENT_ID et GRDF_CLIENT_SECRET doivent être définis."
        )
    resp = requests.post(
        settings.grdf_auth_url,
        data={
            "grant_type": "client_credentials",
            "client_id": settings.grdf_client_id,
            "client_secret": settings.grdf_client_secret,
            "scope": settings.grdf_scope,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"Pas de access_token GRDF : {resp.text[:300]}")
    expires_in = int(data.get("expires_in", 14399))
    return token, expires_in


class GrdfTokenManager:
    """
    Cache thread-safe du token OAuth GRDF (API Data), renouvelé automatiquement
    quand il approche son expiration (marge configurable, 5 min par défaut).
    """

    def __init__(self, margin_seconds: int = 300) -> None:
        if margin_seconds < 0:
            raise ValueError("margin_seconds must be >= 0")
        self._margin_s = margin_seconds
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._lock = threading.Lock()

    def get(self) -> str:
        with self._lock:
            if not self._token or _time.monotonic() > self._expires_at - self._margin_s:
                self._refresh()
            assert self._token is not None
            return self._token

    def force_refresh(self) -> str:
        """Force le renouvellement (utile après un 401)."""
        with self._lock:
            self._refresh()
            assert self._token is not None
            return self._token

    def _refresh(self) -> None:
        token, expires_in = get_oauth_token()
        self._token = token
        self._expires_at = _time.monotonic() + expires_in


# Singletons partagés (token + rate limiter) ------------------------------------

_TOKEN_MANAGER: Optional[GrdfTokenManager] = None
_RATE_LIMITER: Optional[RateLimiter] = None
_LOCK = threading.Lock()


def get_token_manager() -> GrdfTokenManager:
    global _TOKEN_MANAGER
    with _LOCK:
        if _TOKEN_MANAGER is None:
            _TOKEN_MANAGER = GrdfTokenManager()
        return _TOKEN_MANAGER


def get_rate_limiter() -> RateLimiter:
    global _RATE_LIMITER
    with _LOCK:
        if _RATE_LIMITER is None:
            _RATE_LIMITER = RateLimiter(
                rps=settings.grdf_max_rps,
                max_concurrent=settings.grdf_max_concurrent,
                max_hourly=settings.grdf_max_hourly,
            )
        return _RATE_LIMITER
