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
_REPO_ROOT = Path(__file__).resolve().parents[4]

_VALIDATION_STATUS_ORDER = [
    "inventorié",
    "import app OK",
    "test service OK",
    "test endpoint HTTP OK",
    "validé front",
    "validé prod",
    "à corriger",
]

_TARGETS = {
    "auth": ("Administration / socle", "/api/auth", "connexion, profil, mot de passe"),
    "billing": ("Energie / finance", "/api/energie/factures", "factures fournisseurs, controles, decisions, export finance"),
    "bpu": ("Energie / referentiels", "/api/energie/prix", "BPU, TURPE, prix contractuels"),
    "buildings": ("Patrimoine", "/api/patrimoine", "sites, batiments, locaux, rattachements"),
    "cities": ("Administration / socle", "/api/admin/villes", "ville et tenant"),
    "cpe": ("Marches & contrats", "/api/marches/cpe-dalkia", "CPE DALKIA, finances, controles, consommations"),
    "cpe-dalkia": ("Marches & contrats / admin expert", "/api/marches/cpe-dalkia/referentiel", "referentiel contractuel DALKIA"),
    "cvc": ("Technique", "/api/technique/cvc", "inventaire CVC, matching, F-Gaz, ESP"),
    "energie-async": ("Administration / connecteurs", "/api/admin/connecteurs/enedis/async", "jobs async ENEDIS"),
    "energie-sync": ("Energie / admin donnees", "/api/energie/distributeurs/enedis", "acquisition ENEDIS et DJU"),
    "energie": ("Energie", "/api/energie/consommations", "consommations, PRM, DJU, preconisations"),
    "engie": ("Administration / connecteurs en attente", "/api/admin/connecteurs/engie", "proxy API ENGIE potentiel"),
    "equipment": ("Technique", "/api/technique/equipements", "referentiel SYPEMI et equipements"),
    "grdf": ("Energie gaz", "/api/energie/distributeurs/grdf", "PCE, consommations gaz, GRDF"),
    "health": ("Administration / diagnostics", "/api/admin/diagnostics", "sante technique"),
    "internal": ("Technique interne", "/api/internal", "authentification interne"),
    "pronostics": ("Hors produit", "(hors plateforme)", "jeu hors plateforme, ne pas integrer"),
}


def build_endpoints() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
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
        route_file, route_line, source_module = _source_location(endpoint)
        service_modules = _service_imports(route_file)
        target_domain, target_prefix, feature_current = _TARGETS.get(
            router,
            ("A qualifier", "(a qualifier)", "fonctionnalite a qualifier"),
        )
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
                    "route_file": route_file,
                    "route_line": route_line,
                    "source_module": source_module,
                    "service_modules": service_modules,
                    "feature_current": feature_current,
                    "target_domain": target_domain,
                    "target_prefix": target_prefix,
                    **_validation_for(method, path, router),
                }
            )
    rows.sort(key=lambda r: (r["router"], r["path"], r["method"]))
    return rows


def _source_location(endpoint: object | None) -> tuple[str, int | None, str]:
    if endpoint is None:
        return "", None, ""
    source_file = inspect.getsourcefile(endpoint) or ""
    try:
        _, line = inspect.getsourcelines(endpoint)
    except (OSError, TypeError):
        line = None
    module = inspect.getmodule(endpoint)
    module_name = module.__name__ if module else ""
    rel_file = ""
    if source_file:
        try:
            rel_file = Path(source_file).resolve().relative_to(_REPO_ROOT).as_posix()
        except ValueError:
            rel_file = source_file
    return rel_file, line, module_name


def _service_imports(route_file: str) -> list[str]:
    if not route_file:
        return []
    path = _REPO_ROOT / route_file
    if not path.exists():
        return []
    services: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("from app.services import "):
            imported = stripped.removeprefix("from app.services import ")
            for name in imported.split(","):
                service = name.strip().split(" as ")[0]
                if service:
                    services.add(f"app.services.{service}")
        elif stripped.startswith("from app.services."):
            service = stripped.removeprefix("from app.services.").split(" import ", 1)[0]
            if service:
                services.add(f"app.services.{service}")
        elif stripped.startswith("import app.services."):
            service = stripped.removeprefix("import app.services.").split()[0]
            if service:
                services.add(f"app.services.{service}")
    return sorted(services)


def _prefix_of(path: str) -> str:
    # /api/cpe/dalkia-ref/... -> /cpe/dalkia-ref ; heuristique a 2 segments.
    parts = [p for p in path.split("/") if p and p != "api" and not p.startswith("{")]
    if not parts:
        return "/"
    return "/" + "/".join(parts[:2]) if len(parts) >= 2 else "/" + parts[0]


def _validation_for(method: str, path: str, router: str) -> dict[str, str]:
    """Niveau de preuve connu pour la matrice.

    Cette annotation reste volontairement prudente : elle atteste seulement la
    meilleure preuve locale versionnee connue, pas une validation production.
    """
    if router == "health":
        return _validation(
            "import app OK",
            "`saas/backend/tests/test_app_boot.py` verifie que `/api/health` est enregistre dans l'application.",
        )

    if router == "billing":
        return _billing_validation(method, path)

    if router == "bpu":
        if path in {"/api/bpu/import-xlsx", "/api/bpu/timeline", "/api/bpu/formula"} or path.startswith("/api/bpu/"):
            return _validation(
                "test service OK",
                "`saas/backend/tests/test_billing_bpu_sync.py` valide le mapping BPU XLSX -> prix courants ; test HTTP endpoint a creer.",
            )

    if router == "cpe":
        return _cpe_validation(path)

    return _validation(
        "inventorié",
        "Endpoint detecte par introspection FastAPI ; preuve fonctionnelle a ajouter avant reaffectation.",
    )


def _billing_validation(method: str, path: str) -> dict[str, str]:
    if path.startswith("/api/billing/accounting/"):
        return _validation(
            "test service OK",
            "`saas/backend/tests/test_energie_accounting.py` couvre import codification, mappings, resolution comptable et liaison XLSX ; test HTTP a creer.",
        )
    if path.endswith("/liaison.xlsx") or path.endswith("/codification"):
        return _validation(
            "test service OK",
            "`saas/backend/tests/test_energie_accounting.py` couvre la codification facture et la generation XLSX finance ; test HTTP a creer.",
        )
    if path.endswith("/decision"):
        return _validation(
            "import app OK",
            "Route chargee par l'application ; test service/HTTP de decision facture a creer.",
        )
    if path.endswith("/analyze"):
        return _validation(
            "test service OK",
            "`saas/backend/tests/test_invoice_analysis_bpu_mapping.py` et `test_billing_bpu_sync.py` couvrent des briques de controle BPU ; test bout-en-bout a creer.",
        )
    if path.endswith("/xlsx"):
        return _validation(
            "test service OK",
            "`saas/backend/tests/test_engie_xlsx_parser.py` couvre le parsing ENGIE XLSX ; test HTTP import a creer.",
        )
    if path.endswith("/edf-csv"):
        return _validation(
            "inventorié",
            "Import EDF CSV inventorie ; preuve service/HTTP specifique a ajouter.",
        )
    if "/api/billing/invoices/batches" in path:
        return _validation(
            "test service OK",
            "`saas/backend/tests/test_invoice_batches.py` couvre les lots et archives ; test HTTP a creer.",
        )
    if "/api/billing/invoices/imports" in path:
        return _validation(
            "import app OK",
            "Route facture chargee par l'application ; preuve fonctionnelle detaillee a completer selon action.",
        )
    if "/api/billing/configs" in path or path == "/api/billing/turpe/versions":
        return _validation(
            "inventorié",
            "Referentiel facture/prix inventorie ; preuve service/HTTP a ajouter avant migration.",
        )
    return _validation(
        "inventorié",
        "Endpoint billing inventorie ; preuve fonctionnelle a ajouter.",
    )


def _cpe_validation(path: str) -> dict[str, str]:
    failing = {
        "/api/cpe/accounting/import-codification": "`saas/backend/tests/test_cpe_accounting_import.py::test_enriched_codification_matches_finance_export_lines` echoue localement : 2047 lignes attendues, 0 matchee.",
        "/api/cpe/bilan/{annee}/atterrissage": "`saas/backend/tests/test_cpe_atterrissage.py` echoue localement sur DJU/interessement.",
        "/api/cpe/dju/{annee}": "`saas/backend/tests/test_cpe_atterrissage.py` et le suivi marche signalent des donnees DJU a corriger.",
        "/api/cpe/finances/market-tracking": "`saas/backend/tests/test_cpe_market_tracking.py::test_dju_block_real_vs_reference` echoue localement : bloc DJU sans donnees.",
    }
    if path in failing:
        return _validation("à corriger", failing[path])
    if path.startswith("/api/cpe/accounting/"):
        return _validation(
            "test service OK",
            "`saas/backend/tests/test_cpe_accounting_import.py` couvre plusieurs briques comptables CPE, avec un cas enrichi encore a corriger.",
        )
    if path.endswith("/liaison.xlsx") or "/controls" in path:
        return _validation(
            "test service OK",
            "Suites CPE comptables et controles facture presentes ; test HTTP bout-en-bout a creer.",
        )
    if "/api/cpe/finances/" in path:
        return _validation(
            "import app OK",
            "Route finances CPE chargee par l'application ; validation parcours facture -> decision -> export a completer.",
        )
    return _validation(
        "inventorié",
        "Endpoint CPE inventorie ; preuve fonctionnelle a completer selon priorite metier.",
    )


def _validation(status: str, evidence: str) -> dict[str, str]:
    if status not in _VALIDATION_STATUS_ORDER:
        raise ValueError(f"Statut validation inconnu: {status}")
    return {"validation_status": status, "validation_evidence": evidence}


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

    out_dir = _REPO_ROOT / "docs" / "api-cartographie"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "api_catalog.js"
    out_file.write_text(
        "// Genere par app.scripts.build_api_catalog — ne pas editer a la main.\n"
        "window.API_CATALOG = " + json.dumps(payload, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    matrix_file = _REPO_ROOT / "docs" / "13-Matrice-routes-fonctionnalites-refonte-api.md"
    matrix_file.write_text(_matrix_markdown(payload), encoding="utf-8")
    print(f"OK: {len(rows)} endpoints, {len(routers)} routeurs -> {out_file}")
    print(f"OK: matrice routes/fonctionnalites -> {matrix_file}")


def _matrix_markdown(payload: dict[str, object]) -> str:
    rows = list(payload["endpoints"])  # type: ignore[index]
    routers = list(payload["routers"])  # type: ignore[index]
    lines = [
        "# 13 - Matrice routes, fonctionnalites et refonte API",
        "",
        "> Document genere par `python -m app.scripts.build_api_catalog`.",
        "> Ne pas editer les tables endpoint a la main : corriger le generateur ou les annotations source.",
        "",
        "## 1. Objectif",
        "",
        "Attacher chaque endpoint existant a son code, sa fonctionnalite actuelle, son domaine cible, son prefixe cible et son niveau de preuve.",
        "Cette matrice sert a preparer la refonte progressive de l'API et de l'UX sans perdre ce qui a deja ete developpe.",
        "",
        "Statuts de validation utilises :",
        "",
        "| Statut | Signification |",
        "|---|---|",
        "| `inventorié` | Endpoint repere par introspection, sans preuve fonctionnelle suffisante. |",
        "| `import app OK` | L'application FastAPI importe et enregistre la route. |",
        "| `test service OK` | Une ou plusieurs briques service sont couvertes par des tests versionnes. |",
        "| `test endpoint HTTP OK` | Un test HTTP appelle l'endpoint. |",
        "| `validé front` | Le parcours est verifie depuis l'interface. |",
        "| `validé prod` | Le parcours est verifie en production. |",
        "| `à corriger` | Une preuve locale indique un probleme a traiter. |",
        "",
        "## 2. Synthese par routeur",
        "",
        "| Routeur actuel | Endpoints | Domaine cible dominant | Prefixe cible dominant | Fonctionnalite actuelle |",
        "|---|---:|---|---|---|",
    ]
    for router in routers:
        name = str(router["name"])  # type: ignore[index]
        target_domain, target_prefix, feature = _TARGETS.get(
            name,
            ("A qualifier", "(a qualifier)", "fonctionnalite a qualifier"),
        )
        lines.append(
            f"| `{name}` | {router['count']} | {target_domain} | `{target_prefix}` | {feature} |"  # type: ignore[index]
        )

    lines.extend(["", "## 3. Matrice detaillee", ""])

    current_router = None
    for index, row in enumerate(rows):
        router = str(row["router"])
        if router != current_router:
            current_router = router
            lines.extend(
                [
                    f"### `{router}`",
                    "",
                    "| Endpoint | Code | Services detectes | Fonctionnalite actuelle | Domaine cible | Prefixe cible | Statut validation | Preuve |",
                    "|---|---|---|---|---|---|---|---|",
                ]
            )
        service_values = row.get("service_modules", [])  # type: ignore[union-attr]
        services = ", ".join(_short_service_name(s) for s in service_values)
        code = str(row.get("route_file", ""))
        if row.get("route_line"):
            code = f"{code}:{row['route_line']}"
        lines.append(
            "| "
            f"`{row['method']} {row['path']}` | "
            f"`{code}` | "
            f"{services or '-'} | "
            f"{row.get('feature_current', '')} | "
            f"{row.get('target_domain', '')} | "
            f"`{row.get('target_prefix', '')}` | "
            f"`{row.get('validation_status', '')}` | "
            f"{row.get('validation_evidence', '')} |"
        )
        next_router = str(rows[index + 1]["router"]) if index + 1 < len(rows) else None
        if next_router != router:
            lines.append("")

    lines.extend(
        [
            "## 4. Regles d'utilisation",
            "",
            "- Ne pas renommer les endpoints en masse.",
            "- Utiliser cette matrice pour decider parcours par parcours.",
            "- Commencer par les endpoints du controle facture, de la decision et de l'export finance.",
            "- Faire monter le statut de preuve par parcours : service -> endpoint HTTP -> front -> prod.",
            "- Creer des facades cible si necessaire, puis migrer le front progressivement.",
            "- Supprimer seulement les endpoints confirmes sans usage produit, sans script, sans front et sans cible.",
        ]
    )
    return "\n".join(lines) + "\n"


def _short_service_name(service: object) -> str:
    return str(service).removeprefix("app.services.")


if __name__ == "__main__":
    main()
