"""
Client HTTP bas niveau pour l'API GRDF ADICT.

Factorise ce qui est commun à GDA / CONSO / contractuel / technique :
- injection du token (``GrdfTokenManager``) et re-auth automatique sur 401 ;
- respect du débit via le ``RateLimiter`` partagé ;
- retries avec backoff sur 429 / 503 / 504 ;
- helpers ``get_json`` (réponse JSON classique) et ``get_ndjson`` (flux
  ``application/x-ndjson`` de ``GET /droits_acces``).

Les structures de réponse suivent la doc v1.9 (`docs/Modules/GRDF-API.md`). Les
parseurs métier (grdf_gda / grdf_conso / grdf_contractuel) restent tolérants aux
champs absents : à vérifier au premier appel réel.
"""
from __future__ import annotations

import json
import logging
import time as _time
from typing import Any, Iterator

import requests

from app.core.config import settings
from app.services.grdf_auth import get_rate_limiter, get_token_manager

LOG = logging.getLogger(__name__)

_RETRY_BACKOFF = [5, 15, 30]  # secondes, pour 429/503/504


class GrdfApiError(RuntimeError):
    """Erreur d'appel GRDF non récupérable (après retries)."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"GRDF {status_code} : {message}")
        self.status_code = status_code


def _url(path: str) -> str:
    return f"{settings.grdf_base_url.rstrip('/')}/{path.lstrip('/')}"


def _request(path: str, params: dict[str, Any] | None, stream: bool) -> requests.Response:
    """GET authentifié avec rate-limit, re-auth sur 401 et retries sur 429/503/504."""
    tm = get_token_manager()
    rl = get_rate_limiter()
    attempt = 0
    while True:
        rl.acquire()
        try:
            resp = requests.get(
                _url(path),
                params=params,
                headers={"Authorization": f"Bearer {tm.get()}"},
                timeout=120,
                stream=stream,
            )
        finally:
            rl.release()

        if resp.status_code == 401 and attempt == 0:
            # Token périmé malgré la marge → on force un refresh une fois.
            tm.force_refresh()
            attempt += 1
            continue

        if resp.status_code in (429, 503, 504) and attempt < len(_RETRY_BACKOFF):
            wait = _RETRY_BACKOFF[attempt]
            LOG.warning("GRDF %s sur %s — retry dans %ss", resp.status_code, path, wait)
            _time.sleep(wait)
            attempt += 1
            continue

        return resp


def get_json(path: str, params: dict[str, Any] | None = None) -> Any:
    """GET JSON. Lève GrdfApiError si statut HTTP d'erreur (hors 200/201)."""
    resp = _request(path, params, stream=False)
    if resp.status_code not in (200, 201):
        raise GrdfApiError(resp.status_code, resp.text[:300])
    if not resp.content:
        return None
    return resp.json()


def get_ndjson(path: str, params: dict[str, Any] | None = None) -> Iterator[dict]:
    """GET d'un flux ``application/x-ndjson`` — yield un dict par ligne non vide."""
    resp = _request(path, params, stream=True)
    if resp.status_code not in (200, 201):
        raise GrdfApiError(resp.status_code, resp.text[:300])
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.strip():
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            LOG.warning("Ligne ndjson GRDF non parsable ignorée : %s", line[:120])
