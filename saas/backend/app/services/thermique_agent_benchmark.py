"""Comparaison neutre de deux lectures IA d'un même paquet de plans raster.

La première sortie est appelée « référence » pour l'appariement, jamais vérité terrain. Le rapport mesure
l'accord entre agents et réserve l'arbitrage métier au thermicien. Aucun vecteur PDF n'est lu.
"""
from __future__ import annotations

import json
import statistics
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.optimize import linear_sum_assignment
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from app.services.thermique_claude_agent import CATEGORIES, GEOMETRIES

REQUIRED_FIELDS = {
    "category", "subtype", "geometry_type", "points", "confidence", "evidence", "review_required",
}
ALLOWED_FIELDS = REQUIRED_FIELDS | {"local"}
MATCH_THRESHOLDS = {"polygon": 0.20, "bbox": 0.10, "polyline": 0.08}


def _normaliser_texte(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").lower())
    return " ".join("".join(char for char in text if not unicodedata.combining(char)).split())


def _points(item: dict[str, Any]) -> list[tuple[float, float]]:
    result = []
    for point in item.get("points", []):
        if isinstance(point, (list, tuple)) and len(point) == 2:
            try:
                result.append((float(point[0]), float(point[1])))
            except (TypeError, ValueError):
                continue
    return result


def valider_sortie(payload: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """Retourne les objets comparables et les anomalies du contrat sans corriger la sortie."""
    issues: list[str] = []
    if not isinstance(payload, dict):
        return [], ["La sortie n'est pas un objet JSON."]
    extra_root = set(payload) - {"objects", "observations"}
    if extra_root:
        issues.append(f"Champs racine inconnus : {', '.join(sorted(extra_root))}")
    objects = payload.get("objects")
    if not isinstance(objects, list):
        return [], ["Le champ objects n'est pas une liste."]
    if not isinstance(payload.get("observations"), list):
        issues.append("Le champ observations n'est pas une liste.")
    elif any(not isinstance(observation, str) for observation in payload["observations"]):
        issues.append("Le champ observations contient une valeur non textuelle.")
    valid: list[dict[str, Any]] = []
    for index, item in enumerate(objects, 1):
        prefix = f"objet {index}"
        item_valid = True
        if not isinstance(item, dict):
            issues.append(f"{prefix}: objet invalide")
            continue
        missing = REQUIRED_FIELDS - set(item)
        if missing:
            issues.append(f"{prefix}: champs manquants {', '.join(sorted(missing))}")
            item_valid = False
        extra = set(item) - ALLOWED_FIELDS
        if extra:
            issues.append(f"{prefix}: champs inconnus {', '.join(sorted(extra))}")
            item_valid = False
        category = item.get("category")
        geometry = item.get("geometry_type")
        if category not in CATEGORIES:
            issues.append(f"{prefix}: catégorie inconnue {category!r}")
            item_valid = False
        if geometry not in GEOMETRIES:
            issues.append(f"{prefix}: géométrie inconnue {geometry!r}")
            item_valid = False
        raw_points = item.get("points")
        points = _points(item)
        if not isinstance(raw_points, list) or len(points) != len(raw_points):
            issues.append(f"{prefix}: points invalides")
            item_valid = False
        minimum = 3 if geometry == "polygon" else 2
        if len(points) < minimum:
            issues.append(f"{prefix}: {len(points)} point(s), minimum {minimum}")
            item_valid = False
        if any(not (0 <= x <= 1000 and 0 <= y <= 1000) for x, y in points):
            issues.append(f"{prefix}: coordonnées hors du domaine 0..1000")
            item_valid = False
        confidence = item.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            issues.append(f"{prefix}: confiance invalide")
            item_valid = False
        if not isinstance(item.get("subtype"), str) or not isinstance(item.get("evidence"), str):
            issues.append(f"{prefix}: subtype ou evidence invalide")
            item_valid = False
        if not isinstance(item.get("review_required"), bool):
            issues.append(f"{prefix}: review_required invalide")
            item_valid = False
        if category == "piece" and "local" in item and item.get("local") not in {"chauffe", "circulation", "non_chauffe"}:
            issues.append(f"{prefix}: nature de local invalide")
            item_valid = False
        if category != "piece" and "local" in item:
            issues.append(f"{prefix}: local n'est autorisé que pour une pièce")
            item_valid = False
        if item_valid:
            valid.append(item)
    return valid, issues


def _shape(item: dict[str, Any]):
    points = _points(item)
    geometry = item.get("geometry_type")
    try:
        if geometry == "bbox" and len(points) >= 2:
            (x1, y1), (x2, y2) = points[:2]
            return box(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        if geometry == "polygon" and len(points) >= 3:
            return Polygon(points).buffer(0)
        if len(points) >= 2:
            return LineString(points)
    except (TypeError, ValueError):
        return None
    return None


def _geometric_score(reference: dict[str, Any], candidate: dict[str, Any]) -> float:
    left, right = _shape(reference), _shape(candidate)
    if left is None or right is None or left.is_empty or right.is_empty:
        return 0.0
    if left.geom_type in {"LineString", "MultiLineString"}:
        left = left.buffer(6, cap_style="flat")
    if right.geom_type in {"LineString", "MultiLineString"}:
        right = right.buffer(6, cap_style="flat")
    union = left.union(right).area
    return float(left.intersection(right).area / union) if union else 0.0


def _name_score(reference: dict[str, Any], candidate: dict[str, Any]) -> float:
    return SequenceMatcher(
        None, _normaliser_texte(reference.get("subtype")), _normaliser_texte(candidate.get("subtype"))
    ).ratio()


def _match_score(reference: dict[str, Any], candidate: dict[str, Any]) -> float:
    geometry = _geometric_score(reference, candidate)
    return 0.9 * geometry + 0.1 * _name_score(reference, candidate) if reference.get("category") == "piece" else geometry


def _apparier(reference: list[dict[str, Any]], candidate: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], set[int], set[int]]:
    matches: list[dict[str, Any]] = []
    used_reference: set[int] = set()
    used_candidate: set[int] = set()
    for category in CATEGORIES:
        refs = [(index, item) for index, item in enumerate(reference) if item.get("category") == category]
        candidates = [(index, item) for index, item in enumerate(candidate) if item.get("category") == category]
        if not refs or not candidates:
            continue
        scores = np.array([[_match_score(left, right) for _, right in candidates] for _, left in refs])
        rows, columns = linear_sum_assignment(-scores)
        for row, column in zip(rows, columns):
            ref_index, ref_item = refs[int(row)]
            candidate_index, candidate_item = candidates[int(column)]
            geometry = _geometric_score(ref_item, candidate_item)
            threshold = MATCH_THRESHOLDS.get(str(ref_item.get("geometry_type")), 0.10)
            if geometry < threshold:
                continue
            used_reference.add(ref_index)
            used_candidate.add(candidate_index)
            matches.append({
                "category": category,
                "reference_index": ref_index,
                "candidate_index": candidate_index,
                "reference_subtype": ref_item.get("subtype"),
                "candidate_subtype": candidate_item.get("subtype"),
                "geometry_score": round(geometry, 4),
                "name_score": round(_name_score(ref_item, candidate_item), 4),
                "local_agreement": ref_item.get("local") == candidate_item.get("local") if category == "piece" else None,
            })
    return matches, used_reference, used_candidate


def _piece_quality(objects: list[dict[str, Any]]) -> dict[str, Any]:
    shapes = []
    invalid = 0
    for item in objects:
        if item.get("category") != "piece" or item.get("geometry_type") != "polygon":
            continue
        raw = Polygon(_points(item))
        if not raw.is_valid:
            invalid += 1
        shape = raw.buffer(0)
        if not shape.is_empty:
            shapes.append(shape)
    if not shapes:
        return {"count": 0, "invalid_polygons": invalid, "overlap_ratio": None, "union_area": 0.0}
    total = sum(shape.area for shape in shapes)
    union = unary_union(shapes)
    return {
        "count": len(shapes),
        "invalid_polygons": invalid,
        "overlap_ratio": round(max(0.0, (total - union.area) / total), 4) if total else 0.0,
        "union_area": round(float(union.area), 2),
    }


def _piece_coverage_iou(reference: list[dict[str, Any]], candidate: list[dict[str, Any]]) -> float | None:
    return _category_coverage_iou(reference, candidate, "piece")


def _coverage_union(items: list[dict[str, Any]], category: str):
    shapes = []
    for item in items:
        if item.get("category") != category:
            continue
        shape = _shape(item)
        if shape is None or shape.is_empty:
            continue
        if shape.geom_type in {"LineString", "MultiLineString"}:
            shape = shape.buffer(6, cap_style="flat")
        shapes.append(shape)
    return unary_union(shapes)


def _category_coverage_iou(
    reference: list[dict[str, Any]], candidate: list[dict[str, Any]], category: str
) -> float | None:
    """Mesure l'accord spatial sans dépendre du découpage en objets."""
    left = _coverage_union(reference, category)
    right = _coverage_union(candidate, category)
    if left.is_empty and right.is_empty:
        return None
    if left.is_empty or right.is_empty:
        return 0.0

    area = left.union(right).area
    return round(float(left.intersection(right).area / area), 4) if area else None


def comparer_sorties(reference_payload: Any, candidate_payload: Any, reference_label: str = "Claude Code", candidate_label: str = "OpenAI") -> dict[str, Any]:
    reference, reference_issues = valider_sortie(reference_payload)
    candidate, candidate_issues = valider_sortie(candidate_payload)
    matches, used_reference, used_candidate = _apparier(reference, candidate)
    unmatched_reference = [item for index, item in enumerate(reference) if index not in used_reference]
    unmatched_candidate = [item for index, item in enumerate(candidate) if index not in used_candidate]
    geometry_scores = [match["geometry_score"] for match in matches]
    categories = {}
    for category in CATEGORIES:
        ref_count = sum(item.get("category") == category for item in reference)
        candidate_count = sum(item.get("category") == category for item in candidate)
        matched = sum(match["category"] == category for match in matches)
        if ref_count or candidate_count:
            categories[category] = {
                "reference": ref_count,
                "candidate": candidate_count,
                "matched": matched,
                "symmetric_match_rate": round(2 * matched / (ref_count + candidate_count), 4),
                "coverage_iou": _category_coverage_iou(reference, candidate, category),
            }
    local_matches = [
        match for match in matches
        if match["category"] == "piece"
        and "local" in reference[match["reference_index"]]
        and "local" in candidate[match["candidate_index"]]
    ]
    local_agreements = [match["local_agreement"] for match in local_matches]
    return {
        "method": "agent_raster_agreement_v1",
        "uses_pdf_vectors": False,
        "warning": "La référence sert à l'appariement ; elle n'est pas une vérité terrain.",
        "labels": {"reference": reference_label, "candidate": candidate_label},
        "summary": {
            "reference_objects": len(reference), "candidate_objects": len(candidate), "matched_objects": len(matches),
            "symmetric_match_rate": round(2 * len(matches) / (len(reference) + len(candidate)), 4) if reference or candidate else 1.0,
            "mean_geometry_score": round(statistics.fmean(geometry_scores), 4) if geometry_scores else None,
            "median_geometry_score": round(statistics.median(geometry_scores), 4) if geometry_scores else None,
            "piece_coverage_iou": _piece_coverage_iou(reference, candidate),
            "piece_nature_agreement": round(sum(bool(value) for value in local_agreements) / len(local_agreements), 4) if local_agreements else None,
            "piece_nature_compared": len(local_agreements),
        },
        "quality": {
            "reference": {
                "schema_issues": reference_issues,
                "review_rate": round(sum(bool(item.get("review_required")) for item in reference) / len(reference), 4) if reference else None,
                "mean_confidence": round(statistics.fmean(float(item["confidence"]) for item in reference), 4) if reference else None,
                "pieces": _piece_quality(reference),
            },
            "candidate": {
                "schema_issues": candidate_issues,
                "review_rate": round(sum(bool(item.get("review_required")) for item in candidate) / len(candidate), 4) if candidate else None,
                "mean_confidence": round(statistics.fmean(float(item["confidence"]) for item in candidate), 4) if candidate else None,
                "pieces": _piece_quality(candidate),
            },
        },
        "categories": categories, "matches": matches,
        "unmatched_reference": [{"category": item.get("category"), "subtype": item.get("subtype")} for item in unmatched_reference],
        "unmatched_candidate": [{"category": item.get("category"), "subtype": item.get("subtype")} for item in unmatched_candidate],
    }


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_item(draw: ImageDraw.ImageDraw, item: dict[str, Any], width: int, height: int, color: tuple[int, int, int, int], line_width: int) -> None:
    points = [(round(x * width / 1000), round(y * height / 1000)) for x, y in _points(item)]
    if item.get("geometry_type") == "bbox" and len(points) >= 2:
        (x1, y1), (x2, y2) = points[:2]
        points = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    if len(points) < 2:
        return
    if item.get("geometry_type") in {"polygon", "bbox"} and len(points) >= 3:
        draw.polygon(points, fill=(*color[:3], 22), outline=color, width=line_width)
    else:
        draw.line(points, fill=color, width=line_width, joint="curve")


def rendre_divergences(background: Path, reference_payload: dict[str, Any], candidate_payload: dict[str, Any], report: dict[str, Any], destination: Path) -> Path:
    reference, _ = valider_sortie(reference_payload)
    candidate, _ = valider_sortie(candidate_payload)
    matched_reference = {match["reference_index"] for match in report["matches"]}
    matched_candidate = {match["candidate_index"] for match in report["matches"]}
    with Image.open(background) as image:
        canvas = image.convert("RGBA")
    overlay = Image.new("RGBA", canvas.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    base_width = max(2, round(canvas.width / 900))
    for index, item in enumerate(reference):
        color = (215, 48, 39, 220) if index in matched_reference else (255, 127, 0, 245)
        _draw_item(draw, item, canvas.width, canvas.height, color, base_width if index in matched_reference else base_width * 2)
    for index, item in enumerate(candidate):
        color = (0, 166, 214, 220) if index in matched_candidate else (197, 27, 125, 245)
        _draw_item(draw, item, canvas.width, canvas.height, color, base_width if index in matched_candidate else base_width * 2)
    canvas = Image.alpha_composite(canvas, overlay)
    legend = ImageDraw.Draw(canvas, "RGBA")
    font_size = max(14, round(canvas.width / 130))
    font = _font(font_size)
    labels = report["labels"]
    lines = [
        (f"{labels['reference']} apparié", (215, 48, 39, 255)),
        (f"{labels['candidate']} apparié", (0, 166, 214, 255)),
        (f"{labels['reference']} sans correspondant", (255, 127, 0, 255)),
        (f"{labels['candidate']} sans correspondant", (197, 27, 125, 255)),
    ]
    line_height = getattr(font, "size", font_size)
    box_height = 18 + len(lines) * (line_height + 10)
    legend.rounded_rectangle((14, 14, 430, box_height), radius=8, fill=(255, 255, 255, 235), outline=(30, 30, 30, 180))
    y = 24
    for label, color in lines:
        legend.line((28, y + line_height / 2, 70, y + line_height / 2), fill=color, width=5)
        legend.text((82, y), label, fill=(20, 20, 20, 255), font=font)
        y += line_height + 10
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(destination, "PNG", optimize=True)
    return destination


def rapport_markdown(report: dict[str, Any]) -> str:
    summary, labels = report["summary"], report["labels"]
    lines = [
        "# Comparatif d'agents thermiciens raster", "",
        f"Référence d'appariement : **{labels['reference']}**. Candidat : **{labels['candidate']}**.", "",
        "> La référence n'est pas une vérité terrain. Les divergences doivent être arbitrées par un thermicien.", "",
        "## Synthèse", "", "| Mesure | Valeur |", "|---|---:|",
        f"| Objets référence | {summary['reference_objects']} |", f"| Objets candidat | {summary['candidate_objects']} |",
        f"| Objets appariés | {summary['matched_objects']} |", f"| Taux d'appariement symétrique | {summary['symmetric_match_rate']:.1%} |",
        f"| Accord géométrique moyen | {summary['mean_geometry_score'] if summary['mean_geometry_score'] is not None else '—'} |",
        f"| IoU de couverture des pièces | {summary['piece_coverage_iou'] if summary['piece_coverage_iou'] is not None else '—'} |",
        f"| Accord sur la nature des pièces appariées | {summary['piece_nature_agreement'] if summary['piece_nature_agreement'] is not None else '—'} |",
        "", "## Par catégorie", "",
        f"| Catégorie | {labels['reference']} | {labels['candidate']} | Appariés | Taux symétrique | Couverture IoU |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for category, values in report["categories"].items():
        coverage = values["coverage_iou"]
        coverage_text = f"{coverage:.1%}" if coverage is not None else "—"
        lines.append(
            f"| {category} | {values['reference']} | {values['candidate']} | {values['matched']} | "
            f"{values['symmetric_match_rate']:.1%} | {coverage_text} |"
        )
    lines.extend([
        "", "## Qualité déclarative", "",
        f"| Mesure | {labels['reference']} | {labels['candidate']} |", "|---|---:|---:|",
    ])
    for metric, label in (("review_rate", "Objets à revoir"), ("mean_confidence", "Confiance moyenne")):
        reference_value = report["quality"]["reference"][metric]
        candidate_value = report["quality"]["candidate"][metric]
        reference_text = f"{reference_value:.1%}" if reference_value is not None else "—"
        candidate_text = f"{candidate_value:.1%}" if candidate_value is not None else "—"
        lines.append(f"| {label} | {reference_text} | {candidate_text} |")
    for metric, label in (("invalid_polygons", "Polygones de pièces invalides"), ("overlap_ratio", "Chevauchement des pièces")):
        reference_value = report["quality"]["reference"]["pieces"][metric]
        candidate_value = report["quality"]["candidate"]["pieces"][metric]
        if metric == "overlap_ratio":
            reference_value = f"{reference_value:.1%}" if reference_value is not None else "—"
            candidate_value = f"{candidate_value:.1%}" if candidate_value is not None else "—"
        lines.append(f"| {label} | {reference_value} | {candidate_value} |")
    lines.extend([
        "", "Le taux symétrique dépend du découpage en objets. La couverture IoU compare l'emprise spatiale",
        "de chaque catégorie et reste donc pertinente lorsqu'un agent produit une façade continue et l'autre plusieurs segments.",
    ])
    for key, title in (
        ("unmatched_reference", f"Sans correspondant côté {labels['reference']}"),
        ("unmatched_candidate", f"Sans correspondant côté {labels['candidate']}"),
    ):
        lines.extend(["", f"## {title}", ""])
        lines.extend([f"- `{item['category']}` — {item['subtype']}" for item in report[key]] or ["- Aucun."])
    for key, title in (("reference", labels["reference"]), ("candidate", labels["candidate"])):
        lines.extend(["", f"## Contrat JSON — {title}", ""])
        issues = report["quality"][key]["schema_issues"]
        lines.extend([f"- {issue}" for issue in issues] or ["- Conforme."])
    return "\n".join(lines) + "\n"


def ecrire_rapport(report: dict[str, Any], destination_json: Path, destination_markdown: Path) -> None:
    destination_json.parent.mkdir(parents=True, exist_ok=True)
    destination_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    destination_markdown.write_text(rapport_markdown(report), encoding="utf-8")
