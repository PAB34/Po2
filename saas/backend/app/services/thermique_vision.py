"""Analyse sémantique d'un plan à partir de son rendu raster uniquement.

Cette piste est volontairement isolée des lecteurs de traits PDF, des signatures et des
calques historiques. Le modèle reçoit une vue globale puis six tuiles recouvrantes et
renvoie des objets géométriques structurés. Les coordonnées normalisées sont ensuite
converties dans le repère PDF afin de réutiliser la visionneuse et son édition de points.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import math
import threading
import time
from pathlib import Path
from typing import Any

import httpx
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.thermique import ThermiqueProject, ThermiqueSheet
from app.services.thermique import ThermiqueError, document_path
from app.services.thermique_raster import TILE_SIZE, ensure_raster, raster_dir, raster_root

LOG = logging.getLogger(__name__)

CATEGORIES = (
    "mur_exterieur",
    "refend",
    "cloison",
    "isolation",
    "doublage",
    "menuiserie_exterieure",
    "menuiserie_interieure",
    "terrasse",
    "balcon",
    "poteau",
    "garde_corps",
    "piece",
    "indetermine",
)
GEOMETRIES = ("polyline", "polygon", "bbox")
ANALYSIS_NAME = "vision-analysis.json"
_states: dict[int, dict[str, Any]] = {}
_lock = threading.Lock()


def analysis_path(sheet: ThermiqueSheet) -> Path:
    return raster_root(sheet.project_id, sheet.id) / ANALYSIS_NAME


def _read(sheet: ThermiqueSheet) -> dict[str, Any] | None:
    path = analysis_path(sheet)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _write(sheet: ThermiqueSheet, result: dict[str, Any]) -> None:
    path = analysis_path(sheet)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".json.part")
    partial.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    partial.replace(path)


def state(sheet: ThermiqueSheet) -> dict[str, Any]:
    with _lock:
        running = dict(_states.get(sheet.id) or {})
    result = _read(sheet)
    return {
        "stage": running.get("stage"),
        "running": bool(running.get("running")),
        "error": running.get("error"),
        "result": result,
    }


def start(project: ThermiqueProject, sheet: ThermiqueSheet) -> dict[str, Any]:
    if sheet.project_id != project.id or sheet.nature != "plan":
        raise ThermiqueError("L'analyse visuelle IA se lance sur une planche classée comme plan.")
    if not settings.thermique_vision_api_key:
        raise ThermiqueError(
            "L'analyse visuelle IA n'est pas configurée sur le serveur (THERMIQUE_VISION_API_KEY absente)."
        )
    with _lock:
        if (_states.get(sheet.id) or {}).get("running"):
            current = dict(_states[sheet.id])
            return {"stage": current.get("stage"), "running": True, "error": None, "result": _read(sheet), "_launch": False}
        _states[sheet.id] = {"stage": "raster", "running": True, "error": None}
    return {**state(sheet), "_launch": True}


def _set_stage(sheet_id: int, stage: str) -> None:
    with _lock:
        _states[sheet_id] = {"stage": stage, "running": True, "error": None}


def _finish(sheet_id: int, error: str | None = None) -> None:
    with _lock:
        _states[sheet_id] = {"stage": None, "running": False, "error": error, "finished_at": time.time()}


def compose_raster(directory: Path, manifest: dict[str, Any]) -> Image.Image:
    """Recompose le niveau maximal de la pyramide sans relire le PDF."""
    level = manifest["levels"][-1]
    z = level["z"]
    image = Image.new("RGB", (level["width"], level["height"]), "white")
    for ty in range(level["rows"]):
        for tx in range(level["cols"]):
            path = directory / str(z) / f"{tx}_{ty}.png"
            if not path.is_file():
                continue
            with Image.open(path) as tile:
                image.paste(tile.convert("RGB"), (tx * TILE_SIZE, ty * TILE_SIZE))
    return image


def tile_boxes(width: int, height: int, columns: int = 3, rows: int = 2, overlap: float = 0.08) -> list[tuple[int, int, int, int]]:
    """Six zones régulières avec recouvrement, bornées à l'image."""
    boxes: list[tuple[int, int, int, int]] = []
    cell_w, cell_h = width / columns, height / rows
    pad_x, pad_y = cell_w * overlap, cell_h * overlap
    for row in range(rows):
        for column in range(columns):
            left = max(0, math.floor(column * cell_w - (pad_x if column else 0)))
            top = max(0, math.floor(row * cell_h - (pad_y if row else 0)))
            right = min(width, math.ceil((column + 1) * cell_w + (pad_x if column + 1 < columns else 0)))
            bottom = min(height, math.ceil((row + 1) * cell_h + (pad_y if row + 1 < rows else 0)))
            boxes.append((left, top, right, bottom))
    return boxes


def _data_url(image: Image.Image, max_side: int | None = None) -> str:
    if max_side and max(image.size) > max_side:
        ratio = max_side / max(image.size)
        image = image.resize((round(image.width * ratio), round(image.height * ratio)), Image.Resampling.LANCZOS)
    stream = io.BytesIO()
    image.save(stream, format="JPEG", quality=84, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(stream.getvalue()).decode("ascii")


def _response_schema() -> dict[str, Any]:
    point = {
        "type": "array",
        "items": {"type": "number", "minimum": 0, "maximum": 1000},
        "minItems": 2,
        "maxItems": 2,
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "objects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "category": {"type": "string", "enum": list(CATEGORIES)},
                        "subtype": {"type": "string"},
                        "geometry_type": {"type": "string", "enum": list(GEOMETRIES)},
                        "points": {"type": "array", "items": point, "minItems": 2},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "evidence": {"type": "string"},
                        "review_required": {"type": "boolean"},
                    },
                    "required": [
                        "category",
                        "subtype",
                        "geometry_type",
                        "points",
                        "confidence",
                        "evidence",
                        "review_required",
                    ],
                },
            },
            "observations": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["objects", "observations"],
    }


def build_request(image: Image.Image) -> dict[str, Any]:
    width, height = image.size
    content: list[dict[str, Any]] = [
        {
            "type": "input_text",
            "text": (
                "Tu es un thermicien bâtiment expert en lecture de plans. Analyse uniquement les pixels fournis. "
                "Ignore le cartouche, les axes, les cotes, le mobilier, les textes et les hachures de sol. "
                "Recense séparément murs extérieurs, murs de refend, cloisons, isolation, menuiseries "
                "extérieures, menuiseries intérieures, terrasses, balcons, poteaux et garde-corps. Une porte est "
                "une menuiserie. N'invente rien : indetermine et review_required=true dès que le contexte visuel "
                "ne permet pas de trancher. Les murs, cloisons, isolants et garde-corps sont des polylines sur "
                "leur axe ; les terrasses et balcons sont des polygones ; les menuiseries sont des segments. "
                "Retourne les points dans le repère GLOBAL de l'image, x et y normalisés de 0 à 1000. "
                "Fusionne les doublons visibles dans plusieurs tuiles. Le plan complet vient d'abord, puis six "
                "tuiles de détail dont les bornes globales sont indiquées."
            ),
        },
        {"type": "input_text", "text": f"Vue globale {width} x {height} pixels."},
        {"type": "input_image", "image_url": _data_url(image, 2000), "detail": "high"},
    ]
    for index, (left, top, right, bottom) in enumerate(tile_boxes(width, height), 1):
        normalized = tuple(round(value, 1) for value in (left * 1000 / width, top * 1000 / height, right * 1000 / width, bottom * 1000 / height))
        content.extend(
            [
                {
                    "type": "input_text",
                    "text": f"Tuile {index}/6, bornes globales normalisées x1,y1,x2,y2 = {normalized}.",
                },
                {"type": "input_image", "image_url": _data_url(image.crop((left, top, right, bottom))), "detail": "original"},
            ]
        )
    return {
        "model": settings.thermique_vision_model,
        "store": False,
        "max_output_tokens": 20000,
        "instructions": "Produis un inventaire géométrique exhaustif, prudent et directement contrôlable sur le plan.",
        "input": [{"role": "user", "content": content}],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "inventaire_plan_batiment",
                "strict": True,
                "schema": _response_schema(),
            }
        },
    }


def _output_text(response: dict[str, Any]) -> str:
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return content["text"]
            if content.get("type") == "refusal":
                raise ThermiqueError(f"Le modèle a refusé l'analyse : {content.get('refusal', 'raison inconnue')}")
    raise ThermiqueError("Le modèle n'a retourné aucun inventaire exploitable.")


def call_model(image: Image.Image) -> dict[str, Any]:
    url = settings.thermique_vision_base_url.rstrip("/") + "/responses"
    try:
        with httpx.Client(timeout=settings.thermique_vision_timeout_seconds) as client:
            response = client.post(
                url,
                headers={"Authorization": f"Bearer {settings.thermique_vision_api_key}"},
                json=build_request(image),
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500]
        raise ThermiqueError(f"Le service d'analyse visuelle a répondu {exc.response.status_code} : {detail}") from exc
    except httpx.HTTPError as exc:
        raise ThermiqueError("Le service d'analyse visuelle est momentanément inaccessible.") from exc
    try:
        return json.loads(_output_text(response.json()))
    except (ValueError, TypeError) as exc:
        raise ThermiqueError("La réponse IA ne respecte pas le contrat géométrique attendu.") from exc


def normalized_to_pdf(point: list[float], manifest: dict[str, Any]) -> list[float]:
    """Inverse la transformation affine PDF -> raster du manifeste."""
    px = float(point[0]) * manifest["width_px"] / 1000
    py = float(point[1]) * manifest["height_px"] / 1000
    a, b, c, d, e, f = (float(value) for value in manifest["transform"])
    determinant = a * d - b * c
    if abs(determinant) < 1e-12:
        raise ThermiqueError("Le repère de la planche est invalide.")
    x = (d * (px - e) - c * (py - f)) / determinant
    y = (-b * (px - e) + a * (py - f)) / determinant
    return [round(x, 3), round(y, 3)]


REVUE_SOUS = 0.78
# L'agent Claude Code signale lui-même ses doutes ; la revue n'est forcée que sous ce seuil.
REVUE_AGENT_SOUS = 0.5


def normalize_result(raw: dict[str, Any], manifest: dict[str, Any], review_below: float = REVUE_SOUS) -> dict[str, Any]:
    objects: list[dict[str, Any]] = []
    counters: dict[str, int] = {}
    for raw_object in raw.get("objects", []):
        category = raw_object.get("category", "indetermine")
        if category not in CATEGORIES:
            category = "indetermine"
        counters[category] = counters.get(category, 0) + 1
        points_norm = raw_object.get("points") or []
        if len(points_norm) < 2:
            continue
        confidence = max(0.0, min(1.0, float(raw_object.get("confidence", 0))))
        objects.append(
            {
                "id": f"{category}-{counters[category]:03d}",
                "category": category,
                "subtype": str(raw_object.get("subtype") or ""),
                "geometry_type": raw_object.get("geometry_type") if raw_object.get("geometry_type") in GEOMETRIES else "polyline",
                "points": [normalized_to_pdf(point, manifest) for point in points_norm],
                "points_norm": points_norm,
                "confidence": round(confidence, 3),
                "evidence": str(raw_object.get("evidence") or ""),
                "review_required": bool(raw_object.get("review_required")) or confidence < review_below,
                "source": "ia_visuelle",
                "confirmed": False,
                # espaces enclavés (trémie, gaine) à déduire de la surface de cette pièce
                **({"enclaves": [str(v) for v in raw_object["enclaves"]]} if raw_object.get("enclaves") else {}),
            }
        )
    counts = {category: sum(item["category"] == category for item in objects) for category in CATEGORIES}
    return {
        "version": 1,
        "method": "ia_visuelle_raster",
        "uses_pdf_vectors": False,
        "model": settings.thermique_vision_model,
        "created_at": time.time(),
        "objects": objects,
        "counts": {key: value for key, value in counts.items() if value},
        "review_count": sum(item["review_required"] for item in objects),
        "observations": [str(value) for value in raw.get("observations", [])],
    }


def _refresh_summary(result: dict[str, Any]) -> None:
    result["counts"] = {
        category: sum(item["category"] == category for item in result["objects"])
        for category in CATEGORIES
        if any(item["category"] == category for item in result["objects"])
    }
    result["review_count"] = sum(item["review_required"] for item in result["objects"])


def run(sheet_id: int) -> None:
    db: Session = SessionLocal()
    try:
        sheet = db.get(ThermiqueSheet, sheet_id)
        if sheet is None:
            raise ThermiqueError("Planche introuvable.")
        _set_stage(sheet_id, "raster")
        directory = raster_dir(sheet.project_id, sheet.id, sheet.rotation_deg)
        manifest = ensure_raster(document_path(sheet.document), sheet.page_index, sheet.rotation_deg, directory)
        image = compose_raster(directory, manifest)
        _set_stage(sheet_id, "vision")
        raw = call_model(image)
        _set_stage(sheet_id, "normalisation")
        result = normalize_result(raw, manifest)
        _write(sheet, result)
        _finish(sheet_id)
    except Exception as exc:  # noqa: BLE001 - message rendu dans l'interface
        LOG.exception("Analyse visuelle IA impossible sur la planche %s", sheet_id)
        message = str(exc) if isinstance(exc, ThermiqueError) else "Analyse visuelle IA impossible."
        _finish(sheet_id, message)
    finally:
        db.close()


def import_agent_result(sheet: ThermiqueSheet, payload: dict[str, Any]) -> dict[str, Any]:
    """Importe le contrat normalisé produit par l'agent Claude Code local."""
    if int(payload.get("viewer_rotation_deg", -1)) != int(sheet.rotation_deg):
        raise ThermiqueError(
            "La rotation du résultat Claude Code ne correspond pas à celle de la planche. "
            f"Résultat : {payload.get('viewer_rotation_deg')}°, planche : {sheet.rotation_deg}°."
        )
    for item in payload.get("objects", []):
        for point in item.get("points", []):
            if len(point) != 2 or any(not 0 <= float(value) <= 1000 for value in point):
                raise ThermiqueError("Les points importés doivent contenir x et y entre 0 et 1000.")
    directory = raster_dir(sheet.project_id, sheet.id, sheet.rotation_deg)
    manifest = ensure_raster(document_path(sheet.document), sheet.page_index, sheet.rotation_deg, directory)
    result = normalize_result(
        {"objects": payload.get("objects", []), "observations": payload.get("observations", [])},
        manifest,
        REVUE_AGENT_SOUS,
    )
    result["method"] = "claude_code_agent_raster"
    result["model"] = str(payload.get("model") or "claude")
    result["agent_rotation_deg"] = int(payload["viewer_rotation_deg"])
    _write(sheet, result)
    return result


def update_object(sheet: ThermiqueSheet, object_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    result = _read(sheet)
    if result is None:
        raise ThermiqueError("Aucune analyse visuelle n'existe encore pour cette planche.")
    target = next((item for item in result["objects"] if item["id"] == object_id), None)
    if target is None:
        raise ThermiqueError("Objet du bâtiment introuvable.")
    if "points" in payload and payload["points"] is not None:
        points = payload["points"]
        if len(points) < 2 or any(len(point) != 2 for point in points):
            raise ThermiqueError("La géométrie doit contenir au moins deux points.")
        target["points"] = [[round(float(x), 3), round(float(y), 3)] for x, y in points]
        target.pop("points_norm", None)
    if payload.get("category") is not None:
        if payload["category"] not in CATEGORIES:
            raise ThermiqueError("Nature d'objet inconnue.")
        target["category"] = payload["category"]
    if payload.get("confirmed") is not None:
        target["confirmed"] = bool(payload["confirmed"])
        if target["confirmed"]:
            target["review_required"] = False
    target["source"] = "corrige"
    target["updated_at"] = time.time()
    _refresh_summary(result)
    _write(sheet, result)
    return result


def create_object(sheet: ThermiqueSheet, payload: dict[str, Any]) -> dict[str, Any]:
    result = _read(sheet)
    if result is None:
        raise ThermiqueError("Lancez d'abord l'analyse visuelle avant d'ajouter un objet.")
    points = payload.get("points") or []
    geometry_type = payload.get("geometry_type")
    minimum = 3 if geometry_type == "polygon" else 2
    if len(points) < minimum or any(len(point) != 2 for point in points):
        raise ThermiqueError(f"Cette géométrie nécessite au moins {minimum} points.")
    numbers = [int(item["id"].split("-")[-1]) for item in result["objects"] if item["id"].startswith("manuel-")]
    result["objects"].append(
        {
            "id": f"manuel-{max(numbers, default=0) + 1:03d}",
            "category": payload["category"],
            "subtype": "",
            "geometry_type": geometry_type,
            "points": [[round(float(x), 3), round(float(y), 3)] for x, y in points],
            "confidence": 1.0,
            "evidence": "Objet ajouté manuellement par le thermicien.",
            "review_required": False,
            "source": "manuel",
            "confirmed": True,
            "created_at": time.time(),
        }
    )
    _refresh_summary(result)
    _write(sheet, result)
    return result


def delete_object(sheet: ThermiqueSheet, object_id: str) -> dict[str, Any]:
    result = _read(sheet)
    if result is None:
        raise ThermiqueError("Aucune analyse visuelle n'existe encore pour cette planche.")
    kept = [item for item in result["objects"] if item["id"] != object_id]
    if len(kept) == len(result["objects"]):
        raise ThermiqueError("Objet du bâtiment introuvable.")
    result["objects"] = kept
    _refresh_summary(result)
    _write(sheet, result)
    return result
