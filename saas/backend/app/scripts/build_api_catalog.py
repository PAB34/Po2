"""Genere le catalogue d'API pour la cartographie editable (docs/api-cartographie).

Introspecte l'application FastAPI vivante (`app.main:app`) et ecrit un fichier
JS autoportant `docs/api-cartographie/api_catalog.js` (=> `window.API_CATALOG`),
lu par `index.html` sans serveur (double-clic / file://).

Le catalogue est la SOURCE DE VERITE regeneree depuis le code. Les annotations
(utile front/back, statut, commentaires, endpoints planifies) vivent cote
navigateur (localStorage) + export JSON, et ne sont pas ecrasees a la regeneration.

Usage (depuis saas/backend, env minimal) :
    DATABASE_URL="sqlite:///:memory:" python -m app.scripts.build_api_catalog
"""

from __future__ import annotations

import inspect
import json
from datetime import datetime, timezone
from pathlib import Path

from app.main import app

_SKIP_METHODS = {"HEAD", "OPTIONS"}


def build_endpoints() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for route in app.routes:
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", "")
        if not methods or not path.startswith("/api"):
            continue
        endpoint = getattr(route, "endpoint", None)
        tags = getattr(route, "tags", None) or []
        router = str(tags[0]) if tags else "(sans tag)"
        doc = inspect.getdoc(endpoint) if endpoint else None
        doc = doc or ""
        summary = doc.split("\n", 1)[0].strip()
        for method in sorted(methods):
            if method in _SKIP_METHODS:
                continue
            rows.append(
                {
                    "id": f"{method} {path}",
                    "method": method,
                    "path": path,
                    "router": router,
                    "prefix": _prefix_of(path),
                    "fn": getattr(endpoint, "__name__", "") if endpoint else "",
                    "summary": summary,
                    "doc": doc,
                }
            )
    rows.sort(key=lambda r: (r["router"], r["path"], r["method"]))
    return rows


def _prefix_of(path: str) -> str:
    # /api/cpe/dalkia-ref/... -> /cpe/dalkia-ref ; heuristique a 2 segments.
    parts = [p for p in path.split("/") if p and p != "api" and not p.startswith("{")]
    if not parts:
        return "/"
    return "/" + "/".join(parts[:2]) if len(parts) >= 2 else "/" + parts[0]


def main() -> None:
    rows = build_endpoints()
    routers: dict[str, int] = {}
    for r in rows:
        routers[r["router"]] = routers.get(r["router"], 0) + 1

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "endpoint_count": len(rows),
        "router_count": len(routers),
        "routers": [{"name": k, "count": v} for k, v in sorted(routers.items())],
        "endpoints": rows,
    }

    out_dir = Path(__file__).resolve().parents[4] / "docs" / "api-cartographie"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "api_catalog.js"
    out_file.write_text(
        "// Genere par app.scripts.build_api_catalog — ne pas editer a la main.\n"
        "window.API_CATALOG = " + json.dumps(payload, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print(f"OK: {len(rows)} endpoints, {len(routers)} routeurs -> {out_file}")


if __name__ == "__main__":
    main()
