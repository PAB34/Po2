"""Cached access to TennisMyLife's public ATP player match feed."""
from __future__ import annotations

import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

BASE_URL = "https://stats.tennismylife.org"
PLAYER_ID_RE = re.compile(
    r"atptour\.com/en/players/[^\"']+/([a-z0-9]+)/overview", re.I,
)
USER_AGENT = "prono-tennis/1.0 (+private statistical dashboard)"
DEFAULT_TTL = 24 * 3600


def player_slug(name: str) -> str:
    text = unicodedata.normalize("NFKD", str(name or ""))
    text = "".join(char for char in text if not unicodedata.combining(char)).lower()
    return "-".join(re.sub(r"[^a-z0-9]+", " ", text).split())


class TennisMyLifeLiveSource:
    def __init__(self, cache_dir: Path, ttl: int = DEFAULT_TTL):
        self.cache_dir = Path(cache_dir)
        self.ttl = max(300, int(ttl))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def enabled(self) -> bool:
        return os.environ.get("PRONO_TENNIS_LIVE_STATS", "0") == "1"

    def player_matches(self, player: str) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        slug = player_slug(player)
        if not slug:
            return []
        cache_path = self.cache_dir / f"{slug}.json"
        cached = self._read_cache(cache_path)
        if cached and time.time() - float(cached.get("fetched_at") or 0) < self.ttl:
            return list(cached.get("matches") or [])
        try:
            player_id = self._player_id(slug)
            matches = self._fetch_matches(player_id)
            payload = {
                "fetched_at": time.time(),
                "player": player,
                "player_id": player_id,
                "source": "TennisMyLife live",
                "matches": matches,
            }
            self._write_cache(cache_path, payload)
            return matches
        except (OSError, ValueError, json.JSONDecodeError):
            return list((cached or {}).get("matches") or [])

    def _player_id(self, slug: str) -> str:
        html = self._request(f"{BASE_URL}/players/{urllib.parse.quote(slug)}").decode(
            "utf-8", "ignore",
        )
        match = PLAYER_ID_RE.search(html)
        if not match:
            raise ValueError("ATP player id not found")
        return match.group(1).upper()

    def _fetch_matches(self, player_id: str) -> list[dict[str, Any]]:
        query = urllib.parse.urlencode({"id": player_id, "limit": 100})
        raw = self._request(f"{BASE_URL}/api/players/allmatches?{query}")
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, list):
            raise ValueError("Unexpected TennisMyLife payload")
        return [row for row in payload if isinstance(row, dict)][:100]

    @staticmethod
    def _request(url: str) -> bytes:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/html"},
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status != 200:
                raise OSError(f"HTTP {response.status}")
            return response.read()

    @staticmethod
    def _read_cache(path: Path) -> dict[str, Any] | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    @staticmethod
    def _write_cache(path: Path, payload: dict[str, Any]) -> None:
        temporary = path.with_name(f"{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
        temporary.replace(path)
