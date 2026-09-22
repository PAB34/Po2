"""Pont local entre un plan raster et l'agent ``thermicien-plan`` de Claude Code.

Ce module ne lit jamais les vecteurs du PDF. Il fabrique un paquet d'images (vue globale et six tuiles),
construit le contrat JSON, puis peut lancer le binaire Claude Code déjà authentifié sur le poste du
thermicien. Il s'agit d'un outil personnel/local : aucune information d'authentification Claude n'entre dans
le backend SaaS et aucun jeton Claude n'est persisté par le projet.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps
from scipy import ndimage

from app.services.thermique import ThermiqueError
from app.services.thermique_vision_geometrie import mettre_au_propre

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


CATEGORY_STYLES = {
    "mur_exterieur": ("Murs extérieurs", "#d73027"),
    "refend": ("Murs de refend", "#7b3294"),
    "cloison": ("Cloisons", "#4575b4"),
    "isolation": ("Isolation", "#fdae61"),
    "doublage": ("Doublages", "#9775fa"),
    "menuiserie_exterieure": ("Menuiseries extérieures", "#00a6d6"),
    "menuiserie_interieure": ("Menuiseries intérieures", "#66c2a5"),
    "terrasse": ("Terrasses", "#8c6d31"),
    "balcon": ("Balcons", "#a6761d"),
    "poteau": ("Poteaux", "#525252"),
    "garde_corps": ("Garde-corps", "#636363"),
    "piece": ("Pièces et espaces", "#1b9e77"),
    "indetermine": ("À déterminer", "#e7298a"),
}


def output_schema() -> dict[str, Any]:
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
                        # nature d'une pièce (D24) ; facultatif, sans objet pour les autres catégories
                        "local": {"type": "string", "enum": ["chauffe", "circulation", "non_chauffe"]},
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


def _save_jpeg(image: Image.Image, path: Path, max_side: int) -> None:
    rendered = image.copy()
    if max(rendered.size) > max_side:
        ratio = max_side / max(rendered.size)
        rendered = rendered.resize(
            (round(rendered.width * ratio), round(rendered.height * ratio)), Image.Resampling.LANCZOS
        )
    rendered.save(path, "JPEG", quality=92, optimize=True)


def detect_plan_box(image: Image.Image) -> tuple[int, int, int, int]:
    """Repère la principale zone dessinée par densité d'encre, sans primitives PDF."""
    preview = image.copy()
    preview.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
    gray = np.asarray(preview.convert("L"))
    ink = gray < 235
    cell = 20
    rows = max(1, gray.shape[0] // cell)
    columns = max(1, gray.shape[1] // cell)
    trimmed = ink[: rows * cell, : columns * cell]
    density = trimmed.reshape(rows, cell, columns, cell).mean(axis=(1, 3))
    occupied = density > 0.03
    occupied[[0, -1], :] = False
    occupied[:, [0, -1]] = False
    # Supprime les chaînes d'une cellule (cadre de feuille, axes et traits de cote)
    # qui relient artificiellement le plan au cartouche.
    occupied = ndimage.binary_opening(occupied, iterations=2)
    occupied = ndimage.binary_dilation(occupied, iterations=2)
    labels, count = ndimage.label(occupied)
    if count == 0:
        return (0, 0, image.width, image.height)
    scores = ndimage.sum(density, labels, range(1, count + 1))
    selected = int(np.argmax(scores)) + 1
    ys, xs = np.where(labels == selected)
    if not len(xs) or not len(ys):
        return (0, 0, image.width, image.height)

    def dense_bounds(mass: np.ndarray, fallback: tuple[int, int]) -> tuple[int, int]:
        if not mass.size or float(mass.max()) <= 0:
            return fallback
        active = ndimage.binary_closing(mass >= float(mass.max()) * 0.12, iterations=1)
        axis_labels, axis_count = ndimage.label(active)
        if axis_count == 0:
            return fallback
        axis_scores = ndimage.sum(mass, axis_labels, range(1, axis_count + 1))
        axis_selected = int(np.argmax(axis_scores)) + 1
        indexes = np.where(axis_labels == axis_selected)[0]
        return (int(indexes.min()), int(indexes.max()))

    selected_density = np.where(labels == selected, density, 0)
    x_min, x_max = dense_bounds(selected_density.sum(axis=0), (int(xs.min()), int(xs.max())))
    y_min, y_max = dense_bounds(selected_density.sum(axis=1), (int(ys.min()), int(ys.max())))
    padding = 3
    left_cell = max(0, x_min - padding)
    top_cell = max(0, y_min - padding)
    right_cell = min(columns, x_max + padding + 1)
    bottom_cell = min(rows, y_max + padding + 1)
    scale_x = image.width / preview.width
    scale_y = image.height / preview.height
    left = round(left_cell * cell * scale_x)
    top = round(top_cell * cell * scale_y)
    right = round(right_cell * cell * scale_x)
    bottom = round(bottom_cell * cell * scale_y)
    if (right - left) * (bottom - top) < image.width * image.height * 0.08:
        return (0, 0, image.width, image.height)
    return (max(0, left), max(0, top), min(image.width, right), min(image.height, bottom))


def prepare_bundle(
    image: Image.Image,
    directory: Path,
    rotation: int = 0,
    auto_crop: bool = True,
) -> dict[str, Any]:
    """Crée la vue globale et les tuiles sans modifier l'image géométrique de référence."""
    if rotation not in {0, 90, 180, 270}:
        raise ThermiqueError("La rotation doit valoir 0, 90, 180 ou 270 degrés.")
    directory.mkdir(parents=True, exist_ok=True)
    source = ImageOps.exif_transpose(image).convert("RGB")
    if rotation:
        source = source.rotate(rotation, expand=True, fillcolor="white")
    page_width, page_height = source.size
    crop_box = detect_plan_box(source) if auto_crop else (0, 0, page_width, page_height)
    source = source.crop(crop_box)
    width, height = source.size
    overview = directory / "overview.jpg"
    _save_jpeg(source, overview, 2400)
    tiles: list[dict[str, Any]] = []
    for index, (left, top, right, bottom) in enumerate(tile_boxes(width, height), 1):
        path = directory / f"tile-{index}.jpg"
        _save_jpeg(source.crop((left, top, right, bottom)), path, 2600)
        tiles.append(
            {
                "index": index,
                "path": str(path.resolve()),
                "box_px": [left, top, right, bottom],
                "box_norm": [
                    round(left * 1000 / width, 3),
                    round(top * 1000 / height, 3),
                    round(right * 1000 / width, 3),
                    round(bottom * 1000 / height, 3),
                ],
            }
        )
    manifest = {
        "version": 1,
        "method": "claude_code_agent_raster",
        "uses_pdf_vectors": False,
        "rotation_deg_ccw": rotation,
        # pdfium et Pillow emploient des sens opposés pour les angles positifs.
        "viewer_rotation_deg": (-rotation) % 360,
        "page_width_px": page_width,
        "page_height_px": page_height,
        "crop_box_px": list(crop_box),
        "width_px": width,
        "height_px": height,
        "overview": str(overview.resolve()),
        "tiles": tiles,
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def build_prompt(manifest: dict[str, Any]) -> str:
    lines = [
        "Analyse ce plan de bâtiment uniquement à partir des images raster suivantes.",
        f"L'image géométrique globale mesure {manifest['width_px']} x {manifest['height_px']} pixels.",
        f"Vue globale : {manifest['overview']}",
        "Lis la vue globale puis chacune des six tuiles avec l'outil Read.",
    ]
    for tile in manifest["tiles"]:
        lines.append(
            f"Tuile {tile['index']}/6 : {tile['path']} ; bornes globales normalisées "
            f"x1,y1,x2,y2 = {tile['box_norm']}."
        )
    lines.extend(
        [
            "Produis l'inventaire exhaustif mais prudent des composants du bâtiment, puis des pièces et "
            "espaces (catégorie piece, polygone au nu intérieur, nom lu dans subtype).",
            "Les pièces couvrent tout l'intérieur du niveau, murs exceptés : circulations, halls, dégagements, "
            "paliers, sanitaires et locaux techniques compris. Pour chaque pièce, indique sa nature dans local : "
            "chauffe, circulation ou non_chauffe (local technique, gaine, escalier encloisonné).",
            "Un vide sur l'étage inférieur, une trémie, un patio ou un puits de lumière n'est pas une pièce ; une "
            "terrasse ou un balcon non plus (catégories terrasse, balcon).",
            "Toutes les coordonnées finales doivent être globales et normalisées de 0 à 1000.",
            "Fusionne les doublons entre tuiles et simplifie les portions droites pour éviter les zigzags.",
        ]
    )
    return "\n".join(lines)


def claude_executable(explicit: str | None = None) -> str:
    candidate = explicit or os.environ.get("CLAUDE_BIN") or shutil.which("claude") or shutil.which("claude.exe")
    if not candidate:
        raise ThermiqueError(
            "Claude Code est introuvable. Installez-le ou renseignez CLAUDE_BIN avec le chemin du binaire."
        )
    return candidate


def parse_cli_output(stdout: str) -> dict[str, Any]:
    try:
        envelope = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ThermiqueError("Claude Code n'a pas renvoyé une enveloppe JSON exploitable.") from exc
    candidate: Any = envelope.get("structured_output") if isinstance(envelope, dict) else None
    if candidate is None and isinstance(envelope, dict):
        candidate = envelope.get("result")
    if isinstance(candidate, str):
        try:
            candidate = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise ThermiqueError("La réponse structurée de Claude Code n'est pas un JSON valide.") from exc
    if candidate is None and isinstance(envelope, dict) and "objects" in envelope:
        candidate = envelope
    if not isinstance(candidate, dict) or not isinstance(candidate.get("objects"), list):
        raise ThermiqueError("Claude Code n'a retourné aucun inventaire d'objets.")
    candidate.setdefault("observations", [])
    return candidate


def cli_environment(source: dict[str, str] | None = None) -> dict[str, str]:
    """Environnement du sous-processus, débarrassé des variables d'une session Claude hôte.

    Lancé depuis une session Claude Code (application de bureau, SDK), le binaire hériterait de l'adresse et
    de l'authentification de l'hôte, refusées hors de celui-ci (erreur 401). Sans ces variables, la CLI reprend
    la connexion locale de l'utilisateur. Aucun secret n'est lu ni transmis.
    """
    environment = dict(os.environ if source is None else source)
    nested = any(key in environment for key in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SESSION_ID"))
    for key in list(environment):
        if key == "CLAUDECODE" or key.startswith(("CLAUDE_CODE_", "CLAUDE_AGENT_SDK")) or key == "CLAUDE_PID":
            del environment[key]
        elif nested and key == "ANTHROPIC_BASE_URL":
            del environment[key]
    return environment


def run_agent(
    manifest: dict[str, Any],
    repository: Path,
    executable: str | None = None,
    model: str = "opus",
    timeout_seconds: int = 900,
) -> tuple[dict[str, Any], dict[str, Any]]:
    bundle_directory = str(Path(manifest["overview"]).resolve().parent)
    command = [
        claude_executable(executable),
        "--add-dir",
        bundle_directory,
        "-p",
        build_prompt(manifest),
        "--agent",
        "thermicien-plan",
        "--model",
        model,
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(output_schema(), ensure_ascii=False, separators=(",", ":")),
        "--tools",
        "Read",
        "--permission-mode",
        "dontAsk",
        "--no-session-persistence",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=repository,
            env=cli_environment(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ThermiqueError(
            "Claude Code n'a pas terminé l'analyse dans le délai prévu. Vérifiez la connexion et l'authentification."
        ) from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()[-1200:]
        raise ThermiqueError(f"Claude Code a interrompu l'analyse ({completed.returncode}) : {detail}")
    try:
        envelope = json.loads(completed.stdout)
    except json.JSONDecodeError:
        envelope = {"raw": completed.stdout}
    return parse_cli_output(completed.stdout), envelope


def save_result(
    raw: dict[str, Any],
    manifest: dict[str, Any],
    destination: Path,
    model: str,
    envelope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    crop_left, crop_top, _, _ = manifest["crop_box_px"]
    page_width = manifest["page_width_px"]
    page_height = manifest["page_height_px"]
    cleaned = [
        {**source, "points": [list(point) for point in source.get("points", [])]}
        for source in raw["objects"]
        if len(source.get("points", [])) >= 2
    ]
    counters: dict[str, int] = {}
    for item in cleaned:
        if item.get("category") not in CATEGORIES:
            item["category"] = "indetermine"
        counters[item["category"]] = counters.get(item["category"], 0) + 1
        item["id"] = f"{item['category']}-{counters[item['category']]:03d}"
    if manifest.get("overview") and Path(manifest["overview"]).is_file():
        with Image.open(manifest["overview"]) as overview:
            ink = 1.0 - np.asarray(overview.convert("L"), dtype=np.float32) / 255.0
        cleanup = mettre_au_propre(cleaned, ink.shape[1], ink.shape[0], ink)
    else:
        cleanup = mettre_au_propre(cleaned, manifest["width_px"], manifest["height_px"])
    objects: list[dict[str, Any]] = []
    for source, item in zip([s for s in raw["objects"] if len(s.get("points", [])) >= 2], cleaned):
        item["points_agent_norm"] = source.get("points", [])
        analysis_points = item["points"]
        item["points_analysis_norm"] = analysis_points
        item["points"] = [
            [
                round((crop_left + float(x) * manifest["width_px"] / 1000) * 1000 / page_width, 3),
                round((crop_top + float(y) * manifest["height_px"] / 1000) * 1000 / page_height, 3),
            ]
            for x, y in analysis_points
        ]
        objects.append(item)
    result = {
        "version": 1,
        "method": "claude_code_agent_raster",
        "uses_pdf_vectors": False,
        "model": model,
        "viewer_rotation_deg": manifest["viewer_rotation_deg"],
        "manifest": manifest,
        "objects": objects,
        "observations": raw.get("observations", []),
        "geometry_cleanup": cleanup,
    }
    if envelope:
        result["usage"] = envelope.get("usage")
        result["session_id"] = envelope.get("session_id")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _font(size: int) -> ImageFont.ImageFont:
    """Police TrueType avec accents (Windows ou Linux), sinon police par défaut."""
    for name in ("arial.ttf", "DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render_projection(result: dict[str, Any], destination: Path) -> Path:
    """Produit une projection lisible sur le raster recadré avec une légende latérale."""
    manifest = result["manifest"]
    with Image.open(manifest["overview"]) as source:
        plan = source.convert("RGBA")
    legend_width = max(360, round(plan.width * 0.22))
    canvas = Image.new("RGBA", (plan.width + legend_width, plan.height), "white")
    canvas.alpha_composite(plan, (0, 0))
    overlay = Image.new("RGBA", canvas.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    font = _font(max(14, round(plan.width / 150)))
    small = _font(max(11, round(plan.width / 220)))
    line_width = max(4, round(plan.width / 550))
    counts: dict[str, int] = {}
    # espaces dessous (fond léger, trait fin), composants dessus
    ordered = sorted(result["objects"], key=lambda item: item["category"] not in {"piece", "terrasse", "balcon", "indetermine"})
    for item in ordered:
        category = item["category"]
        counts[category] = counts.get(category, 0) + 1
        _, color_hex = CATEGORY_STYLES[category]
        red, green, blue = ImageColor.getrgb(color_hex)
        points = [
            (round(float(x) * plan.width / 1000), round(float(y) * plan.height / 1000))
            for x, y in item.get("points_analysis_norm", [])
        ]
        if len(points) < 2:
            continue
        geometry = item.get("geometry_type", "polyline")
        space = category in {"piece", "terrasse", "balcon", "indetermine"}
        if geometry == "bbox" and len(points) == 2:
            (x1, y1), (x2, y2) = points
            points = [(min(x1, x2), min(y1, y2)), (max(x1, x2), min(y1, y2)), (max(x1, x2), max(y1, y2)), (min(x1, x2), max(y1, y2))]
            geometry = "polygon"
        if geometry == "polygon" and len(points) >= 3:
            width = max(2, line_width // 2) if space else line_width
            draw.polygon(points, fill=(red, green, blue, 34 if space else 90), outline=(red, green, blue, 255), width=width)
        else:
            draw.line(points, fill=(red, green, blue, 255), width=line_width, joint="curve")
        radius = (line_width // 2 + 1) if space else line_width + 1
        for x, y in points:
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(red, green, blue, 255))
        if category == "piece":
            cx = sum(x for x, _ in points) / len(points)
            cy = sum(y for _, y in points) / len(points)
            label = f"{item['id'].split('-')[-1]} {item.get('subtype', '')}"[:40]
            box = draw.textbbox((cx, cy), label, font=small, anchor="mm")
            draw.rectangle((box[0] - 3, box[1] - 2, box[2] + 3, box[3] + 2), fill=(255, 255, 255, 200))
            draw.text((cx, cy), label, fill=(15, 90, 70, 255), font=small, anchor="mm")
        elif category != "poteau":
            x, y = points[len(points) // 2]
            box = draw.textbbox((x + 6, y), item["id"], font=small, anchor="lm")
            draw.rectangle((box[0] - 2, box[1] - 2, box[2] + 2, box[3] + 2), fill=(255, 255, 255, 215))
            draw.text((x + 6, y), item["id"], fill=(20, 20, 20, 255), font=small, anchor="lm")
    canvas = Image.alpha_composite(canvas, overlay)
    legend = ImageDraw.Draw(canvas)
    start_x = plan.width + 28
    step = round(font.size * 1.7) if hasattr(font, "size") else 30
    legend.text((start_x, 30), "ANALYSE THERMIQUE IA", fill="#172033", font=font)
    legend.text((start_x, 30 + step), "Composants proposés (raster seul)", fill="#4b5563", font=small)
    y = 30 + 3 * step
    for category in CATEGORIES:
        if not counts.get(category):
            continue
        label, color = CATEGORY_STYLES[category]
        legend.rectangle((start_x, y, start_x + step // 2 + 6, y + step // 2 + 6), fill=color)
        legend.text((start_x + step, y), f"{label} : {counts[category]}", fill="#172033", font=font)
        y += step
    review_count = sum(bool(item.get("review_required")) for item in result["objects"])
    legend.text((start_x, y + step // 2), f"À confirmer : {review_count}", fill="#9f1239", font=font)
    legend.text((start_x, y + 2 * step), "Points éditables dans l'outil", fill="#4b5563", font=small)
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(destination, "PNG", optimize=True)
    return destination
