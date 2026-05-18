"""
Tests unitaires de RateLimiter et TokenManager.

Pour exécuter :
    cd saas/backend && pytest tests/test_enedis_common.py -v
"""
from __future__ import annotations

import threading
import time
from unittest.mock import patch

import pytest

from app.services.enedis_common import RateLimiter, TokenManager


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------


def test_ratelimiter_rps_throttling() -> None:
    """À 10 req/s, 5 appels séquentiels doivent prendre au moins 0.4s."""
    rl = RateLimiter(rps=10.0, max_concurrent=10, max_hourly=1000)
    t0 = time.monotonic()
    for _ in range(5):
        rl.acquire()
        rl.release()
    elapsed = time.monotonic() - t0
    # 5 appels à 10 req/s → 4 intervalles de 0.1s = 0.4s minimum
    assert elapsed >= 0.35, f"Expected >= 0.35s, got {elapsed:.3f}s"


def test_ratelimiter_concurrency_bound() -> None:
    """Avec max_concurrent=2, jamais plus de 2 threads actifs simultanément."""
    rl = RateLimiter(rps=100.0, max_concurrent=2, max_hourly=10000)
    active = 0
    max_active = 0
    lock = threading.Lock()

    def worker() -> None:
        nonlocal active, max_active
        rl.acquire()
        try:
            with lock:
                active += 1
                if active > max_active:
                    max_active = active
            time.sleep(0.05)
        finally:
            with lock:
                active -= 1
            rl.release()

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert max_active <= 2, f"Expected max 2 concurrent, got {max_active}"


def test_ratelimiter_hourly_quota_blocks() -> None:
    """Quand le quota horaire est atteint, le callback on_quota_wait est appelé."""
    calls: list[tuple[float, int]] = []
    # Patch sleep pour ne pas vraiment dormir 3600s dans le test
    with patch("app.services.enedis_common._time.sleep") as mock_sleep:
        rl = RateLimiter(
            rps=1000.0,
            max_concurrent=10,
            max_hourly=2,  # quota très petit
            on_quota_wait=lambda w, m: calls.append((w, m)),
        )
        rl.acquire(); rl.release()
        rl.acquire(); rl.release()
        # Le 3e doit déclencher le callback (quota saturé)
        # Mais pour ne pas bloquer le test indéfiniment, on patch le state interne
        # pour faire croire que le timestamp le plus ancien est très récent
        # Le simple fait d'appeler acquire() doit invoquer le callback
        # On exécute dans un thread pour ne pas bloquer
        finished = threading.Event()
        def call_third() -> None:
            rl.acquire(); rl.release()
            finished.set()
        t = threading.Thread(target=call_third, daemon=True)
        t.start()
        time.sleep(0.1)
        assert mock_sleep.called, "Expected _time.sleep to be called for quota wait"
        assert len(calls) >= 1, "Expected on_quota_wait callback to be invoked"
        wait_s, max_h = calls[0]
        assert max_h == 2
        assert wait_s > 3000  # proche de 3600


# ---------------------------------------------------------------------------
# TokenManager
# ---------------------------------------------------------------------------


def test_tokenmanager_caches_token() -> None:
    """Le token est mis en cache et réutilisé sans nouvel appel HTTP."""
    with patch("app.services.enedis_common.get_oauth_token", return_value=("TOKEN_A", 3600)) as mock_get:
        tm = TokenManager()
        assert tm.get() == "TOKEN_A"
        assert tm.get() == "TOKEN_A"
        assert tm.get() == "TOKEN_A"
        assert mock_get.call_count == 1


def test_tokenmanager_refresh_when_expired() -> None:
    """Le token est renouvelé quand il est proche de l'expiration."""
    with patch("app.services.enedis_common.get_oauth_token") as mock_get:
        # 1er appel : token avec expiration courte
        # 2e appel : nouveau token
        mock_get.side_effect = [("TOKEN_A", 100), ("TOKEN_B", 3600)]
        tm = TokenManager(margin_seconds=200)  # marge plus grande que la durée → refresh immédiat au 2e get
        assert tm.get() == "TOKEN_A"
        # Force la condition d'expiration via la marge
        assert tm.get() == "TOKEN_B"
        assert mock_get.call_count == 2


def test_tokenmanager_force_refresh() -> None:
    """force_refresh demande un nouveau token immédiatement."""
    with patch("app.services.enedis_common.get_oauth_token") as mock_get:
        mock_get.side_effect = [("TOKEN_A", 3600), ("TOKEN_B", 3600)]
        tm = TokenManager()
        assert tm.get() == "TOKEN_A"
        assert tm.force_refresh() == "TOKEN_B"
        assert tm.get() == "TOKEN_B"
        assert mock_get.call_count == 2


def test_tokenmanager_on_refresh_callback() -> None:
    """Le callback on_refresh reçoit expires_in."""
    received: list[int] = []
    with patch("app.services.enedis_common.get_oauth_token", return_value=("T", 1800)):
        tm = TokenManager(on_refresh=lambda exp: received.append(exp))
        tm.get()
    assert received == [1800]


def test_tokenmanager_thread_safe() -> None:
    """Sous N threads concurrents, le token est demandé une seule fois."""
    with patch("app.services.enedis_common.get_oauth_token", return_value=("TOKEN", 3600)) as mock_get:
        tm = TokenManager()
        results: list[str] = []
        lock = threading.Lock()
        def worker() -> None:
            r = tm.get()
            with lock:
                results.append(r)
        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(results) == 20
        assert all(r == "TOKEN" for r in results)
        assert mock_get.call_count == 1


# ---------------------------------------------------------------------------
# Validation des paramètres
# ---------------------------------------------------------------------------


def test_ratelimiter_invalid_rps() -> None:
    with pytest.raises(ValueError):
        RateLimiter(rps=0)
    with pytest.raises(ValueError):
        RateLimiter(rps=-1)


def test_tokenmanager_invalid_margin() -> None:
    with pytest.raises(ValueError):
        TokenManager(margin_seconds=-1)
