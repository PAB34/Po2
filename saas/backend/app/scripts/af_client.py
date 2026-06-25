"""Client API-Football minimal : cache disque + journal des appels.

Cle lue dans APIFOOTBALL_KEY (jamais ecrite dans le cache ni le log).
Chaque reponse est mise en cache (apifootball_cache/) -> aucun re-appel pour les
memes parametres. Chaque appel reseau est journalise dans api_log.csv
(date, endpoint, params, statut, nb_resultats, depuis_cache).

Usage en module :
    from app.scripts.af_client import AFClient
    af = AFClient(cache_dir)
    data = af.get("teams", {"search": "France"})
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://v3.football.api-sports.io"


class AFClient:
    def __init__(self, cache_dir: str, *, min_interval: float = 4.0):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.log_path = os.path.join(cache_dir, "api_log.csv")
        self.min_interval = min_interval
        self._last = 0.0
        self.network_calls = 0
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(
                    ["date_appel", "endpoint", "parametres", "statut", "nb_resultats", "depuis_cache", "commentaire"]
                )

    def _key(self, path: str, params: dict) -> str:
        raw = path + "?" + urlencode(sorted(params.items()))
        return hashlib.md5(raw.encode()).hexdigest()

    def _log(self, path, params, statut, n, cached, comment=""):
        with open(self.log_path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(
                [datetime.now(timezone.utc).isoformat(timespec="seconds"), path,
                 urlencode(sorted(params.items())), statut, n, "oui" if cached else "non", comment]
            )

    def get(self, path: str, params: dict | None = None, *, force: bool = False) -> dict:
        params = params or {}
        cache_file = os.path.join(self.cache_dir, f"{path.replace('/', '_')}__{self._key(path, params)}.json")
        if os.path.exists(cache_file) and not force:
            data = json.load(open(cache_file, encoding="utf-8"))
            self._log(path, params, "cache", len(data.get("response") or []), True)
            return data

        key = os.environ.get("APIFOOTBALL_KEY", "")
        if not key:
            raise RuntimeError("APIFOOTBALL_KEY absente de l'environnement.")
        wait = self.min_interval - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        url = f"{BASE}/{path}" + ("?" + urlencode(params) if params else "")
        req = Request(url, headers={"x-apisports-key": key})
        try:
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
            status = "ok"
        except Exception as exc:  # pragma: no cover
            self._log(path, params, f"erreur:{exc}", 0, False)
            raise
        finally:
            self._last = time.monotonic()
        self.network_calls += 1
        errs = data.get("errors") or {}
        n = len(data.get("response") or [])
        if not errs:
            json.dump(data, open(cache_file, "w", encoding="utf-8"), ensure_ascii=False)
        self._log(path, params, "ok" if not errs else f"err:{errs}", n, False)
        return data
