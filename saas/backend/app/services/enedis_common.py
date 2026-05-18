"""
Utilitaires partagés pour les appels API ENEDIS — synchrones et asynchrones.

Ce module factorise :
- RateLimiter : respect des limites ENEDIS (5 req/s, 5 simultanés, 950/h).
- TokenManager : cache et renouvellement automatique du token OAuth client_credentials.
- get_oauth_token : helper one-shot pour les appels ponctuels.

Les limites par défaut intègrent une marge de sécurité par rapport aux limites
documentées :
- 5 req/s par application cliente (limite ENEDIS)
- 5 appels simultanés par API (marge sur les 10 documentés, tous clients confondus)
- 950 appels/heure par API (marge sur les 1000 documentés)

Avant chaque appel ENEDIS sync :
    rl.acquire()
    try:
        resp = requests.get(...)
    finally:
        rl.release()

Pour récupérer un token frais à chaque appel :
    headers = {"Authorization": f"Bearer {tm.get()}"}
"""
from __future__ import annotations

import logging
import threading
import time as _time
from collections.abc import Callable
from typing import Optional

import requests

from app.core.config import settings

LOG = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class RateLimiter:
    """
    Limiteur de débit thread-safe pour les API ENEDIS synchrones.

    Combine 3 contraintes :
    - **rps** : débit max en req/seconde (sleep entre appels)
    - **max_concurrent** : nombre max d'appels simultanés (Semaphore)
    - **max_hourly** : quota glissant sur 1 heure (bloque si dépassé)

    L'API publique est ``acquire()`` / ``release()``. Toujours appeler
    ``release()`` dans un ``finally`` après un ``acquire()``.

    Le paramètre ``on_quota_wait`` est un callback optionnel qui reçoit
    le nombre de secondes d'attente quand le quota horaire est saturé
    (utile pour logger la pause côté service appelant).
    """

    def __init__(
        self,
        rps: float = 5.0,
        max_concurrent: int = 5,
        max_hourly: int = 950,
        on_quota_wait: Optional[Callable[[float, int], None]] = None,
    ) -> None:
        if rps <= 0:
            raise ValueError("rps must be > 0")
        self._sem = threading.Semaphore(max_concurrent)
        self._min_interval = 1.0 / rps
        self._last_t = 0.0
        self._rps_lock = threading.Lock()
        self._hourly_ts: list[float] = []
        self._hourly_lock = threading.Lock()
        self._max_hourly = max_hourly
        self._on_quota_wait = on_quota_wait

    def acquire(self) -> None:
        """Bloque jusqu'à ce qu'un nouvel appel ENEDIS puisse partir."""
        # 1. Quota horaire glissant
        while True:
            with self._hourly_lock:
                now = _time.monotonic()
                cutoff = now - 3600
                self._hourly_ts = [t for t in self._hourly_ts if t > cutoff]
                if len(self._hourly_ts) < self._max_hourly:
                    break
                wait_s = self._hourly_ts[0] + 3600 - now + 2
            if self._on_quota_wait:
                try:
                    self._on_quota_wait(wait_s, self._max_hourly)
                except Exception:
                    LOG.exception("on_quota_wait callback failed")
            _time.sleep(max(wait_s, 1.0))

        # 2. Concurrence
        self._sem.acquire()

        # 3. Débit req/s
        with self._rps_lock:
            now = _time.monotonic()
            elapsed = now - self._last_t
            if elapsed < self._min_interval:
                _time.sleep(self._min_interval - elapsed)
            self._last_t = _time.monotonic()

        with self._hourly_lock:
            self._hourly_ts.append(_time.monotonic())

    def release(self) -> None:
        self._sem.release()


# ---------------------------------------------------------------------------
# OAuth helpers
# ---------------------------------------------------------------------------


def get_oauth_token() -> tuple[str, int]:
    """
    Récupère un access token ENEDIS via OAuth2 client_credentials.

    Retourne ``(access_token, expires_in_seconds)``. Lève RuntimeError si
    les credentials ne sont pas configurés ou si l'API ne retourne pas
    de token.
    """
    if not settings.enedis_client_id or not settings.enedis_client_secret:
        raise RuntimeError(
            "ENEDIS_CLIENT_ID et ENEDIS_CLIENT_SECRET doivent être définis."
        )
    resp = requests.post(
        settings.enedis_auth_url,
        data={
            "grant_type": "client_credentials",
            "client_id": settings.enedis_client_id,
            "client_secret": settings.enedis_client_secret,
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"Pas de access_token ENEDIS : {resp.text[:300]}")
    expires_in = int(data.get("expires_in", 3600))
    return token, expires_in


class TokenManager:
    """
    Cache thread-safe du token OAuth ENEDIS.

    Le token est conservé en mémoire et renouvelé automatiquement quand
    il approche son expiration (marge configurable, 5 minutes par défaut).

    Utilisation typique :
        tm = TokenManager()
        headers = {"Authorization": f"Bearer {tm.get()}"}

    Le callback ``on_refresh`` est invoqué après chaque renouvellement
    avec l'``expires_in`` retourné par ENEDIS.
    """

    def __init__(
        self,
        margin_seconds: int = 300,
        on_refresh: Optional[Callable[[int], None]] = None,
    ) -> None:
        if margin_seconds < 0:
            raise ValueError("margin_seconds must be >= 0")
        self._margin_s = margin_seconds
        self._on_refresh = on_refresh
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._lock = threading.Lock()

    def get(self) -> str:
        """Retourne un token valide ; le renouvelle si nécessaire."""
        with self._lock:
            if not self._token or _time.monotonic() > self._expires_at - self._margin_s:
                self._refresh()
            assert self._token is not None
            return self._token

    def force_refresh(self) -> str:
        """Force le renouvellement du token (utile après un 401)."""
        with self._lock:
            self._refresh()
            assert self._token is not None
            return self._token

    def _refresh(self) -> None:
        token, expires_in = get_oauth_token()
        self._token = token
        self._expires_at = _time.monotonic() + expires_in
        if self._on_refresh:
            try:
                self._on_refresh(expires_in)
            except Exception:
                LOG.exception("on_refresh callback failed")
