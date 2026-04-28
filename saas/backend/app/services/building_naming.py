from __future__ import annotations

from io import BytesIO
import json
import math
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from app.core.config import settings

GEOPF_WFS_URL = "https://data.geopf.fr/wfs/ows"
GEOPF_SEARCH_URL = "https://data.geopf.fr/geocodage/search"
USER_AGENT = "patrimoineop-building-workflow/1.0"

_MAJIC_EXPECTED = {
    "departmentcode": ["Département"],
    "municipalitycode": ["Code Commune"],
    "prefix": ["Préfixe"],
    "section": ["Section"],
    "number": ["N° plan", "N plan"],
    "street_number": ["N° voirie", "N voirie"],
    "street_repeat": ["Indice de répétition", "Indice repetition"],
    "street_type": ["Nature voie"],
    "street_name": ["Nom voie"],
    "city_name": ["Nom de la commune"],
    "building_col": ["Bâtiment"],
    "entry_col": ["Entrée"],
    "level_col": ["Niveau"],
    "door_col": ["Porte"],
}
_MAJIC_GROUP_PERSON_COLUMN_CANDIDATES = ["Groupe personne", "Groupe de personne", "Groupe de personnes"]
_MAJIC_GROUP_PERSON_ALLOWED_VALUES = {
    "4 - Commune",
    "4 - Commune du fichier",
}

_APP_STATE: dict[str, Any] = {
    "cache_geopf": {},
    "cache_geocode": {},
    "cache_ign_features": {},
    "cache_ign_toponymy": {},
    "cache_naming_dataset": {},
    "last_call_by_host": {},
}


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _display_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null"} else text


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", ".")
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    try:
        return float(text)
    except Exception:
        return None


def _to_int_string(value: Any, width: int) -> str:
    numeric = _safe_float(value)
    if numeric is None or math.isnan(numeric):
        return ""
    return str(int(numeric)).zfill(width)


def _find_column(columns: list[str], candidates: list[str]) -> str | None:
    normalized = {_normalize_text(column): column for column in columns}
    for candidate in candidates:
        key = _normalize_text(candidate)
        if key in normalized:
            return normalized[key]
    return None


def _is_allowed_group_person_value(value: Any) -> bool:
    normalized = _normalize_text(value)
    if not normalized:
        return False
    if normalized in {_normalize_text(item) for item in _MAJIC_GROUP_PERSON_ALLOWED_VALUES}:
        return True
    return normalized.startswith("4 ") and "COMMUNE" in normalized


def _build_reference_norm(row: pd.Series, mapping: dict[str, str | None]) -> str:
    department = _to_int_string(row.get(mapping["departmentcode"]), 2) if mapping.get("departmentcode") else ""
    municipality = _to_int_string(row.get(mapping["municipalitycode"]), 3) if mapping.get("municipalitycode") else ""
    prefix = _to_int_string(row.get(mapping["prefix"]), 3) if mapping.get("prefix") else "000"
    section = _display_text(row.get(mapping["section"])).strip().upper() if mapping.get("section") else ""
    number = _to_int_string(row.get(mapping["number"]), 4) if mapping.get("number") else ""
    if not department or not municipality or not section or not number:
        return ""
    return f"{department}{municipality}{prefix or '000'}{section}{number}"


def _build_address_display(row: pd.Series, mapping: dict[str, str | None]) -> str:
    street_number = _display_text(row.get(mapping["street_number"])) if mapping.get("street_number") else ""
    street_number = re.sub(r"\.0$", "", street_number)
    street_repeat = _display_text(row.get(mapping["street_repeat"])) if mapping.get("street_repeat") else ""
    street_repeat = re.sub(r"\.0$", "", street_repeat)
    street_type = _display_text(row.get(mapping["street_type"])) if mapping.get("street_type") else ""
    street_name = _display_text(row.get(mapping["street_name"])) if mapping.get("street_name") else ""
    city_name = _display_text(row.get(mapping["city_name"])) if mapping.get("city_name") else ""
    parts = [street_number, street_repeat, street_type, street_name, city_name]
    return re.sub(r"\s+", " ", " ".join(part for part in parts if part).strip()).strip()


def _feature_actual_name(attributes: dict[str, Any]) -> str:
    for key in [
        "toponyme",
        "nom",
        "nom_officiel",
        "nom_complet",
        "nom_historique",
        "graphie",
        "libelle",
        "designation",
        "appellation",
    ]:
        value = attributes.get(key)
        if value not in [None, ""]:
            return str(value)
    return ""


def _feature_label(attributes: dict[str, Any]) -> str:
    for key in [
        "toponyme",
        "nom",
        "nom_officiel",
        "nom_complet",
        "graphie",
        "nature_detaillee",
        "nature",
        "usage_1",
        "usage_2",
        "etat_de_l_objet",
    ]:
        value = attributes.get(key)
        if value not in [None, ""]:
            return str(value)
    return "(sans libellé)"


def _feature_name(attributes: dict[str, Any]) -> str:
    for key in [
        "toponyme",
        "nom",
        "nom_officiel",
        "nom_complet",
        "nom_historique",
        "graphie",
        "libelle",
        "designation",
        "appellation",
        "nature_detaillee",
        "nature",
    ]:
        value = attributes.get(key)
        if value not in [None, ""]:
            return str(value)
    return ""


def _normalize_candidate_name(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = " ".join(text.split())
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text).casefold()


def _dedupe_candidate_dicts(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_name: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for item in candidates or []:
        raw_name = item.get("name") or item.get("label")
        label = " ".join(str(raw_name or "").strip().split())
        if not label:
            continue
        key = _normalize_candidate_name(label)
        if not key:
            continue
        distance = _safe_float(item.get("distance_m"))
        normalized = dict(item)
        normalized["name"] = label
        normalized["label"] = str(item.get("label") or label).strip() or label
        normalized["source"] = str(item.get("source") or "")
        normalized["id"] = str(item.get("id") or "")
        normalized["typename"] = str(item.get("typename") or "")
        normalized["distance_m"] = round(float(distance), 1) if distance is not None else None
        if key not in best_by_name:
            best_by_name[key] = normalized
            order.append(key)
            continue
        previous_distance = _safe_float(best_by_name[key].get("distance_m"))
        if previous_distance is None and distance is not None:
            best_by_name[key] = normalized
        elif distance is not None and previous_distance is not None and distance < previous_distance:
            best_by_name[key] = normalized
    return [best_by_name[key] for key in order]


def _extract_center_from_geometry(geometry: dict[str, Any]) -> tuple[float | None, float | None]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Point" and isinstance(coordinates, list) and len(coordinates) >= 2:
        return float(coordinates[1]), float(coordinates[0])
    points: list[tuple[float, float]] = []

    def collect(obj: Any) -> None:
        if isinstance(obj, list):
            if len(obj) >= 2 and all(isinstance(value, (int, float)) for value in obj[:2]):
                points.append((float(obj[1]), float(obj[0])))
            else:
                for item in obj:
                    collect(item)

    collect(coordinates)
    if not points:
        return None, None
    lat = sum(point[0] for point in points) / len(points)
    lon = sum(point[1] for point in points) / len(points)
    return lat, lon


def _iter_points_from_geometry(geometry: dict[str, Any]) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []

    def collect(obj: Any) -> None:
        if isinstance(obj, list):
            if len(obj) >= 2 and all(isinstance(value, (int, float)) for value in obj[:2]):
                points.append((float(obj[1]), float(obj[0])))
            else:
                for item in obj:
                    collect(item)

    collect((geometry or {}).get("coordinates"))
    return points


def _distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    delta_p = math.radians(lat2 - lat1)
    delta_l = math.radians(lon2 - lon1)
    a = math.sin(delta_p / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(delta_l / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _min_distance_between_geometries_m(source_geometry: dict[str, Any], target_geometry: dict[str, Any]) -> float:
    source_points = _iter_points_from_geometry(source_geometry)
    target_points = _iter_points_from_geometry(target_geometry)
    if not source_points:
        lat, lon = _extract_center_from_geometry(source_geometry)
        if lat is not None and lon is not None:
            source_points = [(lat, lon)]
    if not target_points:
        lat, lon = _extract_center_from_geometry(target_geometry)
        if lat is not None and lon is not None:
            target_points = [(lat, lon)]
    if not source_points or not target_points:
        return 999999.0
    return min(_distance_m(slat, slon, tlat, tlon) for slat, slon in source_points for tlat, tlon in target_points)


def _geometry_to_feature(geometry: dict[str, Any], properties: dict[str, Any]) -> dict[str, Any] | None:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if not geometry_type or coordinates is None:
        return None
    if geometry_type == "Point":
        return {"type": "Feature", "geometry": {"type": "Point", "coordinates": coordinates}, "properties": properties}
    if geometry_type in {"Polygon", "MultiPolygon"}:
        return {"type": "Feature", "geometry": {"type": geometry_type, "coordinates": coordinates}, "properties": properties}
    return None


def _attrs_lower_keys(properties: dict[str, Any]) -> dict[str, Any]:
    return {str(key).lower(): value for key, value in (properties or {}).items()}


def _rate_limited_get(url: str, params: dict[str, Any], host_key: str, timeout: int = 30) -> requests.Response:
    now = time.time()
    last = _APP_STATE["last_call_by_host"].get(host_key, 0.0)
    delta = now - last
    if delta < 1.05:
        time.sleep(1.05 - delta)
    response = requests.get(
        url,
        params=params,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "fr"},
        timeout=timeout,
    )
    _APP_STATE["last_call_by_host"][host_key] = time.time()
    response.raise_for_status()
    return response


def _bbox_around(lat: float, lon: float, radius_m: int = 50) -> tuple[float, float, float, float]:
    delta_lat = radius_m / 111320.0
    delta_lon = radius_m / max(111320.0 * math.cos(math.radians(lat)), 1e-6)
    return lon - delta_lon, lat - delta_lat, lon + delta_lon, lat + delta_lat


def _wfs_layer_features(type_name: str, bbox: tuple[float, float, float, float], count: int = 100) -> dict[str, Any]:
    minx, miny, maxx, maxy = bbox
    response = _rate_limited_get(
        GEOPF_WFS_URL,
        {
            "SERVICE": "WFS",
            "VERSION": "2.0.0",
            "REQUEST": "GetFeature",
            "typeNames": type_name,
            "bbox": f"{minx},{miny},{maxx},{maxy},EPSG:4326",
            "srsName": "EPSG:4326",
            "outputFormat": "application/json",
            "count": count,
        },
        host_key=f"wfs_{type_name}",
        timeout=45,
    )
    return response.json()


def _parse_reference_norm(reference_norm: str) -> dict[str, str] | None:
    reference = _normalize_text(reference_norm).replace(" ", "")
    reference = re.sub(r"[^A-Z0-9]", "", reference)
    pattern = re.compile(r"^(?P<dept>\d{2,3})(?P<commune>\d{3})(?P<prefix>\d{3})(?P<section>[A-Z]{1,2})(?P<number>\d{4})$")
    match = pattern.match(reference)
    if not match:
        return None
    groups = match.groupdict()
    return {
        "departmentcode": groups["dept"],
        "municipalitycode": groups["commune"],
        "prefix": groups["prefix"],
        "section": groups["section"],
        "number": str(int(groups["number"])),
    }


def _geopf_parcel(reference_norm: str) -> dict[str, Any]:
    if reference_norm in _APP_STATE["cache_geopf"]:
        return _APP_STATE["cache_geopf"][reference_norm]
    parsed = _parse_reference_norm(reference_norm)
    if not parsed:
        raise ValueError(f"Référence cadastrale invalide : {reference_norm}")
    response = _rate_limited_get(
        GEOPF_SEARCH_URL,
        {
            "index": "parcel",
            "limit": 1,
            "returntruegeometry": "true",
            "departmentcode": parsed["departmentcode"],
            "municipalitycode": parsed["municipalitycode"],
            "section": parsed["section"],
            "number": parsed["number"],
        },
        host_key="geopf",
        timeout=30,
    )
    features = response.json().get("features", [])
    if not features:
        raise ValueError(f"Parcelle introuvable pour {reference_norm}")
    feature = features[0]
    properties = feature.get("properties", {}) or {}
    geometry = feature.get("geometry", {}) or {}
    lat, lon = _extract_center_from_geometry(geometry)
    result = {
        "reference_norm": reference_norm,
        "label": properties.get("label") or properties.get("name") or reference_norm,
        "lat": lat,
        "lon": lon,
        "feature": _geometry_to_feature(
            geometry,
            {
                "source": "geopf",
                "reference_norm": reference_norm,
                "label": properties.get("label") or properties.get("name") or reference_norm,
            },
        ),
        "raw": feature,
    }
    _APP_STATE["cache_geopf"][reference_norm] = result
    return result


def _geocode_address(address: str) -> dict[str, Any]:
    if address in _APP_STATE["cache_geocode"]:
        return _APP_STATE["cache_geocode"][address]
    response = _rate_limited_get(
        GEOPF_SEARCH_URL,
        {"q": address, "limit": 1},
        host_key="geopf_search",
        timeout=30,
    )
    features = response.json().get("features", [])
    if not features:
        raise ValueError(f"Aucun résultat de géocodage pour : {address}")
    feature = features[0]
    properties = feature.get("properties", {}) or {}
    geometry = feature.get("geometry", {}) or {}
    lat, lon = _extract_center_from_geometry(geometry)
    result = {
        "lat": lat,
        "lon": lon,
        "display_name": properties.get("label") or properties.get("name") or address,
        "properties": properties,
        "raw": feature,
    }
    _APP_STATE["cache_geocode"][address] = result
    return result


def _ign_toponymy(lat: float, lon: float, radius_m: int = 80) -> list[dict[str, Any]]:
    cache_key = f"{round(lat, 6)}|{round(lon, 6)}|topo|{radius_m}"
    if cache_key in _APP_STATE["cache_ign_toponymy"]:
        return _APP_STATE["cache_ign_toponymy"][cache_key]
    bbox = _bbox_around(lat, lon, radius_m=radius_m)
    layer_specs = [
        ("BDTOPO_V3:toponymie_bati", "toponymie_bati"),
        ("BDTOPO_V3:toponymie_lieux_nommes", "toponymie_lieux_nommes"),
        ("BDTOPO_V3:toponymie_services_et_activites", "toponymie_services_et_activites"),
    ]
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for type_name, short_layer in layer_specs:
        try:
            data = _wfs_layer_features(type_name, bbox, count=300)
        except Exception:
            continue
        for feature in data.get("features", []) or []:
            geometry = feature.get("geometry")
            if not geometry:
                continue
            attributes = _attrs_lower_keys(feature.get("properties", {}) or {})
            feature_id = feature.get("id") or attributes.get("cleabs") or attributes.get("id") or ""
            unique_key = (
                short_layer,
                str(feature_id),
                str(attributes.get("graphie") or attributes.get("toponyme") or attributes.get("nom") or ""),
            )
            if unique_key in seen:
                continue
            seen.add(unique_key)
            name = _feature_name(attributes)
            label = _feature_label(attributes)
            if not (name or label):
                continue
            candidates.append(
                {
                    "layer": short_layer,
                    "typename": type_name,
                    "id": feature_id,
                    "object_ref": str(attributes.get("id") or attributes.get("id_objet") or attributes.get("cleabs_objet") or ""),
                    "name": name or label,
                    "label": label or name,
                    "attributes": attributes,
                    "geometry": geometry,
                }
            )
    _APP_STATE["cache_ign_toponymy"][cache_key] = candidates
    return candidates


def _ign_named_areas(lat: float, lon: float, radius_m: int = 180) -> list[dict[str, Any]]:
    cache_key = f"{round(lat, 6)}|{round(lon, 6)}|areas|{radius_m}"
    if cache_key in _APP_STATE["cache_ign_features"]:
        cached = _APP_STATE["cache_ign_features"][cache_key]
        if isinstance(cached, list):
            return cached
    bbox = _bbox_around(lat, lon, radius_m=radius_m)
    layer_specs = [
        ("BDTOPO_V3:zone_d_habitation", "zone_d_habitation"),
        ("BDTOPO_V3:zone_d_activite_ou_d_interet", "zone_d_activite_ou_d_interet"),
        ("BDTOPO_V3:erp", "erp"),
    ]
    areas: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for type_name, short_layer in layer_specs:
        try:
            data = _wfs_layer_features(type_name, bbox, count=200)
        except Exception:
            continue
        for feature in data.get("features", []) or []:
            geometry = feature.get("geometry")
            if not geometry:
                continue
            attributes = _attrs_lower_keys(feature.get("properties", {}) or {})
            feature_id = str(feature.get("id") or attributes.get("cleabs") or attributes.get("id") or "")
            if (short_layer, feature_id) in seen:
                continue
            seen.add((short_layer, feature_id))
            areas.append(
                {
                    "layer": short_layer,
                    "typename": type_name,
                    "id": feature_id,
                    "object_ref": str(attributes.get("cleabs") or attributes.get("id") or feature_id),
                    "name": _feature_actual_name(attributes),
                    "label": _feature_label(attributes),
                    "attributes": attributes,
                    "geometry": geometry,
                }
            )
    _APP_STATE["cache_ign_features"][cache_key] = areas
    return areas


def _resolve_building_name(
    feature: dict[str, Any],
    nearby_toponymy: list[dict[str, Any]],
    nearby_named_areas: list[dict[str, Any]],
) -> dict[str, Any]:
    properties = feature.get("properties", {}) or {}
    attributes = properties.get("attributes", {}) or {}
    direct_name = str(properties.get("name") or _feature_actual_name(attributes) or "").strip()
    if direct_name:
        return {
            "resolved_name": direct_name,
            "resolved_name_source": "batiment",
            "resolved_name_distance_m": 0.0,
            "resolved_name_feature": None,
            "resolved_name_candidates": [],
        }
    feature_geometry = feature.get("geometry", {}) or {}
    feature_ref = str(attributes.get("cleabs") or attributes.get("_feature_id") or "")
    ranked: list[dict[str, Any]] = []
    related_area_ids: set[str] = set()
    for area in nearby_named_areas:
        area_distance = _min_distance_between_geometries_m(feature_geometry, area.get("geometry", {}) or {})
        if area_distance <= 120.0:
            related_area_ids.add(str(area.get("object_ref") or area.get("id") or ""))
            area_name = str(area.get("name") or "").strip()
            if area_name:
                ranked.append(
                    {
                        "score": float(area_distance - 30),
                        "dist_m": float(area_distance),
                        "name": area_name,
                        "source": str(area.get("layer") or ""),
                        "feature": area,
                        "label": str(area.get("label") or area_name),
                        "typename": str(area.get("typename") or ""),
                        "id": str(area.get("id") or ""),
                    }
                )
    for toponym in nearby_toponymy:
        distance = _min_distance_between_geometries_m(feature_geometry, toponym.get("geometry", {}) or {})
        attributes_l = toponym.get("attributes", {}) or {}
        category = str(attributes_l.get("classe") or attributes_l.get("nature") or attributes_l.get("nature_detaillee") or "").upper()
        layer = toponym.get("layer") or ""
        toponym_name = str(toponym.get("name") or toponym.get("label") or "").strip()
        if not toponym_name:
            continue
        toponym_object_ref = str(toponym.get("object_ref") or attributes_l.get("id") or "")
        linked_to_building = bool(feature_ref and toponym_object_ref and toponym_object_ref == feature_ref)
        linked_to_named_area = bool(toponym_object_ref and toponym_object_ref in related_area_ids)
        max_distance = 120.0 if layer == "toponymie_bati" else 200.0
        if not linked_to_building and not linked_to_named_area and distance > max_distance:
            continue
        score = distance
        if linked_to_building:
            score -= 80
        if linked_to_named_area:
            score -= 65
        if layer == "toponymie_bati":
            score -= 25
        elif layer == "toponymie_lieux_nommes":
            score -= 10
        if "HABITATION" in category or "RESIDENCE" in category or "RÉSIDENCE" in category or "BATI" in category:
            score -= 18
        if toponym_name.upper().startswith(("RESIDENCE", "RÉSIDENCE", "CITE", "CITÉ", "LES ", "LE ", "LA ")):
            score -= 8
        ranked.append(
            {
                "score": float(score),
                "dist_m": float(distance),
                "name": toponym_name,
                "source": layer,
                "feature": toponym,
                "label": str(toponym.get("label") or toponym_name),
                "typename": str(toponym.get("typename") or ""),
                "id": str(toponym.get("id") or ""),
            }
        )
    ranked.sort(key=lambda item: (item["score"], item["dist_m"], item["name"]))
    candidates = _dedupe_candidate_dicts(
        [
            {
                "name": str(item["name"]).strip(),
                "source": str(item["source"]),
                "distance_m": round(float(item["dist_m"]), 1),
                "label": str(item.get("label") or item["name"]),
                "typename": str(item.get("typename") or ""),
                "id": str(item.get("id") or ""),
            }
            for item in ranked
        ]
    )[:12]
    if ranked and ranked[0].get("name"):
        best = ranked[0]
        return {
            "resolved_name": str(best["name"]).strip(),
            "resolved_name_source": str(best["source"]),
            "resolved_name_distance_m": round(float(best["dist_m"]), 1),
            "resolved_name_feature": best["feature"],
            "resolved_name_candidates": candidates,
        }
    return {
        "resolved_name": "",
        "resolved_name_source": "",
        "resolved_name_distance_m": None,
        "resolved_name_feature": None,
        "resolved_name_candidates": candidates,
    }


def _ign_buildings(lat: float, lon: float, radius_m: int = 50) -> dict[str, Any]:
    cache_key = f"{round(lat, 6)}|{round(lon, 6)}|{radius_m}|batiments"
    cached = _APP_STATE["cache_ign_features"].get(cache_key)
    if isinstance(cached, dict) and cached.get("type") == "FeatureCollection":
        return cached
    bbox = _bbox_around(lat, lon, radius_m=radius_m)
    layer_specs = [
        ("BDTOPO_V3:batiment", "batiment"),
        ("BDTOPO_V3:construction_surfacique", "construction_surfacique"),
    ]
    nearby_toponymy = _ign_toponymy(lat, lon, radius_m=max(200, radius_m * 4))
    nearby_named_areas = _ign_named_areas(lat, lon, radius_m=max(220, radius_m * 4))
    features: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for type_name, short_layer in layer_specs:
        try:
            data = _wfs_layer_features(type_name, bbox, count=150)
        except Exception:
            continue
        for feature in data.get("features", []) or []:
            geometry = feature.get("geometry")
            if not geometry:
                continue
            properties = feature.get("properties", {}) or {}
            feature_id = feature.get("id") or properties.get("cleabs") or properties.get("id") or ""
            unique_key = (short_layer, str(feature_id))
            if unique_key in seen:
                continue
            seen.add(unique_key)
            attributes = dict(properties)
            attributes["_layer"] = short_layer
            attributes["_typename"] = type_name
            attributes["_feature_id"] = feature_id
            raw_name = _feature_actual_name(attributes)
            raw_label = _feature_label(attributes)
            seed_feature = {
                "type": "Feature",
                "geometry": geometry,
                "properties": {"attributes": attributes, "name": raw_name, "label": raw_label},
            }
            resolved = _resolve_building_name(seed_feature, nearby_toponymy, nearby_named_areas)
            resolved_name = resolved.get("resolved_name") or raw_name or ""
            resolved_label = resolved_name or raw_label
            resolved_candidates = _dedupe_candidate_dicts(resolved.get("resolved_name_candidates") or [])
            if not resolved_candidates and resolved_name:
                fallback_distance = _safe_float(resolved.get("resolved_name_distance_m"))
                resolved_candidates = [
                    {
                        "name": resolved_name,
                        "label": resolved_label or resolved_name,
                        "source": resolved.get("resolved_name_source") or ("batiment" if raw_name else ""),
                        "typename": type_name,
                        "id": str(feature_id),
                        "distance_m": round(float(fallback_distance), 1) if fallback_distance is not None else None,
                    }
                ]
            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {
                        "ign_layer": short_layer,
                        "ign_typename": type_name,
                        "ign_id": str(feature_id),
                        "name": raw_name,
                        "label": raw_label,
                        "resolved_name": resolved_name,
                        "resolved_label": resolved_label,
                        "resolved_name_source": resolved.get("resolved_name_source") or ("batiment" if raw_name else ""),
                        "resolved_name_distance_m": resolved.get("resolved_name_distance_m"),
                        "resolved_name_feature": resolved.get("resolved_name_feature"),
                        "resolved_name_candidates": resolved_candidates,
                        "attributes": attributes,
                    },
                }
            )
    features.sort(
        key=lambda feature: (
            0 if (feature.get("properties", {}) or {}).get("resolved_name") or (feature.get("properties", {}) or {}).get("name") else 1,
            0 if (feature.get("geometry", {}) or {}).get("type") in {"Polygon", "MultiPolygon"} else 1,
            0 if (feature.get("properties", {}) or {}).get("ign_layer") == "batiment" else 1,
            str((feature.get("properties", {}) or {}).get("resolved_label") or (feature.get("properties", {}) or {}).get("label") or ""),
        )
    )
    collection = {"type": "FeatureCollection", "features": features}
    _APP_STATE["cache_ign_features"][cache_key] = collection
    return collection


def _resolve_point_and_parcels(address_display: str, references: list[str]) -> dict[str, Any]:
    parcel_features = []
    used_source = "address"
    lat = None
    lon = None
    geocoder_data = None
    parcel_labels: list[str] = []
    for reference in references:
        try:
            parcel = _geopf_parcel(reference)
            parcel_labels.append(parcel.get("label", reference))
            if parcel.get("feature"):
                parcel_features.append(parcel["feature"])
            if lat is None and lon is None and parcel.get("lat") is not None and parcel.get("lon") is not None:
                lat = parcel["lat"]
                lon = parcel["lon"]
                used_source = "parcel"
        except Exception:
            continue
    if lat is None or lon is None:
        geocoder_data = _geocode_address(address_display)
        lat = geocoder_data["lat"]
        lon = geocoder_data["lon"]
        used_source = "address"
    return {
        "lat": lat,
        "lon": lon,
        "used_source": used_source,
        "parcel_feature_collection": {"type": "FeatureCollection", "features": parcel_features},
        "parcel_labels": parcel_labels,
        "geocoder": geocoder_data or {"display_name": address_display},
    }


def _read_uploaded_tabular_file(filename: str, raw_bytes: bytes) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    buffer = BytesIO(raw_bytes)
    if suffix == ".csv":
        dataframe = pd.read_csv(buffer, sep=None, engine="python", dtype=str)
    elif suffix in {".xlsx", ".xlsm"}:
        dataframe = pd.read_excel(buffer, dtype=str)
    elif suffix == ".xls":
        dataframe = pd.read_excel(buffer, dtype=str, engine="xlrd")
    else:
        raise ValueError("Format non pris en charge. Utilise CSV, XLS, XLSX ou XLSM.")
    dataframe = dataframe.fillna("")
    dataframe.columns = [str(column).strip() for column in dataframe.columns]
    return dataframe


def preview_building_import_file(
    *,
    filename: str,
    raw_bytes: bytes,
    name_column: str | None = None,
    address_column: str | None = None,
) -> dict[str, Any]:
    dataframe = _read_uploaded_tabular_file(filename, raw_bytes)
    columns = list(dataframe.columns)
    sample_rows = [
        {column: _display_text(row.get(column)) for column in columns}
        for _, row in dataframe.head(5).iterrows()
    ]
    rows: list[dict[str, Any]] = []
    if name_column is not None or address_column is not None:
        if not name_column or name_column not in columns:
            raise ValueError("La colonne 'Nom bâtiment' sélectionnée est introuvable dans le fichier.")
        if not address_column or address_column not in columns:
            raise ValueError("La colonne 'Adresse' sélectionnée est introuvable dans le fichier.")
        validation_cache: dict[str, dict[str, Any]] = {}
        for row_index, (_, row) in enumerate(dataframe.iterrows(), start=2):
            source_name = _display_text(row.get(name_column))
            source_address = _display_text(row.get(address_column))
            address_display = re.sub(r"\s+", " ", source_address).strip()
            validation_status = "invalid"
            validation_message = "Adresse absente ou vide."
            lat = None
            lon = None
            if address_display:
                cached_validation = validation_cache.get(address_display)
                if cached_validation is None:
                    try:
                        geocoded = _geocode_address(address_display)
                        cached_validation = {
                            "validation_status": "valid",
                            "validation_message": str(geocoded.get("display_name") or "Adresse compatible avec la recherche IGN."),
                            "lat": geocoded.get("lat"),
                            "lon": geocoded.get("lon"),
                        }
                    except Exception as error:
                        cached_validation = {
                            "validation_status": "invalid",
                            "validation_message": str(error),
                            "lat": None,
                            "lon": None,
                        }
                    validation_cache[address_display] = cached_validation
                validation_status = str(cached_validation["validation_status"])
                validation_message = str(cached_validation["validation_message"])
                lat = _safe_float(cached_validation.get("lat"))
                lon = _safe_float(cached_validation.get("lon"))
            rows.append(
                {
                    "row_number": row_index,
                    "source_name": source_name,
                    "source_address": source_address,
                    "address_display": address_display,
                    "validation_status": validation_status,
                    "validation_message": validation_message,
                    "lat": lat,
                    "lon": lon,
                }
            )
    return {
        "filename": filename,
        "columns": columns,
        "total_rows": int(len(dataframe)),
        "sample_rows": sample_rows,
        "name_column": name_column,
        "address_column": address_column,
        "rows": rows,
    }


def lookup_free_address_candidates(address: str) -> dict[str, Any]:
    address_display = re.sub(r"\s+", " ", str(address).strip()).strip()
    if len(address_display) < 3:
        raise ValueError("L'adresse doit contenir au moins 3 caractères.")
    point_and_parcels = _resolve_point_and_parcels(address_display, [])
    lat = _safe_float(point_and_parcels.get("lat"))
    lon = _safe_float(point_and_parcels.get("lon"))
    if lat is None or lon is None:
        raise ValueError(f"Impossible de géolocaliser l'adresse : {address_display}")
    return {
        "unique_key": _normalize_text(address_display) or "MANUAL_ADDRESS",
        "input_address": address_display,
        "duplicate_count": 1,
        "source_rows": [],
        "reference_count": 0,
        "references": [],
        "lat": lat,
        "lon": lon,
        "used_source": str(point_and_parcels.get("used_source") or "address"),
        "parcel_feature_collection": point_and_parcels.get("parcel_feature_collection") or {"type": "FeatureCollection", "features": []},
        "parcel_labels": point_and_parcels.get("parcel_labels") or [],
        "geocoder": point_and_parcels.get("geocoder") or {"display_name": address_display},
        "feature_collection": _ign_buildings(lat, lon, radius_m=55),
    }


def _get_majic_file_path() -> Path:
    configured_path = settings.dgfip_majic_file_path.strip()
    if not configured_path:
        raise ValueError("Le fichier DGFIP/MAJIC n'est pas configuré. Renseigne DGFIP_MAJIC_FILE_PATH dans l'environnement.")
    file_path = Path(configured_path)
    if not file_path.exists():
        raise ValueError(f"Fichier DGFIP/MAJIC introuvable : {file_path}")
    return file_path


def _read_majic_file() -> tuple[str, pd.DataFrame]:
    file_path = _get_majic_file_path()
    if file_path.suffix.lower() == ".csv":
        dataframe = pd.read_csv(file_path, sep=None, engine="python", dtype=str)
    elif file_path.suffix.lower() in {".xlsx", ".xls"}:
        dataframe = pd.read_excel(file_path, dtype=str)
    else:
        raise ValueError("Format non pris en charge. Utilise CSV, XLSX ou XLS.")
    dataframe.columns = [str(column).strip() for column in dataframe.columns]
    return file_path.name, dataframe


def list_majic_columns() -> list[str]:
    _, dataframe = _read_majic_file()
    return list(dataframe.columns)


def _build_naming_dataset_cache_key(city_name: str | None) -> str:
    file_path = _get_majic_file_path()
    file_stat = file_path.stat()
    normalized_city = _normalize_text(city_name)
    return f"{file_path.resolve()}::{file_stat.st_mtime_ns}::{file_stat.st_size}::{normalized_city}"


def _build_building_naming_rows(city_name: str | None = None) -> dict[str, Any]:
    started_at = time.perf_counter()
    filename, dataframe = _read_majic_file()
    mapping = {key: _find_column(list(dataframe.columns), candidates) for key, candidates in _MAJIC_EXPECTED.items()}
    missing = [key for key in ["departmentcode", "municipalitycode", "section", "number", "street_type", "street_name", "city_name"] if not mapping.get(key)]
    if missing:
        raise ValueError(f"Colonnes MAJIC non trouvées : {', '.join(missing)}")
    work = dataframe.copy()
    group_person_column = _find_column(list(work.columns), _MAJIC_GROUP_PERSON_COLUMN_CANDIDATES)
    if not group_person_column:
        raise ValueError("Colonne MAJIC 'Groupe personne' introuvable dans le fichier source.")
    work = work[work[group_person_column].map(_is_allowed_group_person_value)].copy()
    if work.empty:
        raise ValueError(
            "Aucune ligne MAJIC ne correspond au filtre 'Groupe personne = 4 - Commune'."
        )
    if city_name:
        city_name_normalized = _normalize_text(city_name)
        city_column = mapping["city_name"]
        work = work[work[city_column].map(lambda value: _normalize_text(value) == city_name_normalized)].copy()
        if work.empty:
            raise ValueError(f"Aucune adresse MAJIC trouvée pour la commune '{city_name}'.")
    work["_source_row_number"] = range(1, len(work) + 1)
    work["reference_norm"] = work.apply(lambda row: _build_reference_norm(row, mapping), axis=1)
    work["address_display"] = work.apply(lambda row: _build_address_display(row, mapping), axis=1)
    work["address_norm"] = work["address_display"].map(_normalize_text)
    for extra_key, output_col in [
        ("building_col", "majic_building"),
        ("entry_col", "majic_entry"),
        ("level_col", "majic_level"),
        ("door_col", "majic_door"),
    ]:
        column = mapping.get(extra_key)
        work[output_col] = work[column].map(_display_text) if column else ""
    work = work[(work["address_norm"] != "") | (work["reference_norm"] != "")].copy()
    if work.empty:
        raise ValueError("Aucune adresse ni référence cadastrale exploitable.")
    grouped_rows: list[dict[str, Any]] = []
    for index, (_, subset) in enumerate(work.groupby("address_norm", dropna=False), start=1):
        first = subset.iloc[0]
        references = [reference for reference in subset["reference_norm"].tolist() if reference]
        references_unique = list(dict.fromkeys(references))
        grouped_rows.append(
            {
                "unique_key": str(index),
                "address_display": first["address_display"] if first["address_display"] else "(adresse vide)",
                "duplicate_count": int(len(subset)),
                "source_rows": subset["_source_row_number"].tolist(),
                "reference_count": int(len(references_unique)),
                "references": references_unique,
                "first_reference_norm": references_unique[0] if references_unique else "",
                "nom_commune": _display_text(first.get(mapping["city_name"])) if mapping.get("city_name") else "",
                "numero_voirie": _display_text(first.get(mapping["street_number"])) if mapping.get("street_number") else "",
                "indice_repetition": _display_text(first.get(mapping["street_repeat"])) if mapping.get("street_repeat") else "",
                "nature_voie": _display_text(first.get(mapping["street_type"])) if mapping.get("street_type") else "",
                "nom_voie": _display_text(first.get(mapping["street_name"])) if mapping.get("street_name") else "",
                "prefixe": _display_text(first.get(mapping["prefix"])) if mapping.get("prefix") else "",
                "section": _display_text(first.get(mapping["section"])) if mapping.get("section") else "",
                "numero_plan": _display_text(first.get(mapping["number"])) if mapping.get("number") else "",
                "majic_building_values": sorted({value for value in subset["majic_building"].tolist() if value}),
                "majic_entry_values": sorted({value for value in subset["majic_entry"].tolist() if value}),
                "majic_level_values": sorted({value for value in subset["majic_level"].tolist() if value}),
                "majic_door_values": sorted({value for value in subset["majic_door"].tolist() if value}),
            }
        )
    build_duration_ms = int((time.perf_counter() - started_at) * 1000)
    return {
        "filename": filename,
        "columns": list(dataframe.columns),
        "mapping": mapping,
        "total_rows": int(len(work)),
        "unique_addresses": len(grouped_rows),
        "filtered_city_name": city_name,
        "group_person_column": group_person_column,
        "group_person_filter": "4 - Commune / 4 - Commune du fichier",
        "cache_status": "miss",
        "build_duration_ms": build_duration_ms,
        "served_duration_ms": build_duration_ms,
        "rows": grouped_rows,
    }


def get_building_naming_rows(city_name: str | None = None) -> dict[str, Any]:
    started_at = time.perf_counter()
    cache_key = _build_naming_dataset_cache_key(city_name)
    cached = _APP_STATE["cache_naming_dataset"].get(cache_key)
    if cached is not None:
        served_duration_ms = int((time.perf_counter() - started_at) * 1000)
        return {
            **cached,
            "cache_status": "hit",
            "served_duration_ms": served_duration_ms,
        }
    dataset = _build_building_naming_rows(city_name=city_name)
    _APP_STATE["cache_naming_dataset"][cache_key] = dataset
    return {
        **dataset,
        "cache_status": "miss",
        "served_duration_ms": int((time.perf_counter() - started_at) * 1000),
    }


def warm_building_naming_cache(city_name: str | None = None) -> dict[str, Any]:
    return get_building_naming_rows(city_name=city_name)


def lookup_building_candidates(unique_key: str, city_name: str | None = None) -> dict[str, Any]:
    data = get_building_naming_rows(city_name=city_name)
    row = next((item for item in data["rows"] if item["unique_key"] == str(unique_key)), None)
    if row is None:
        raise ValueError(f"Clé inconnue : {unique_key}")
    resolved = _resolve_point_and_parcels(row["address_display"], row["references"])
    feature_collection = _ign_buildings(resolved["lat"], resolved["lon"], radius_m=50)
    return {
        "unique_key": row["unique_key"],
        "input_address": row["address_display"],
        "duplicate_count": row["duplicate_count"],
        "source_rows": row["source_rows"],
        "reference_count": row["reference_count"],
        "references": row["references"],
        "lat": resolved["lat"],
        "lon": resolved["lon"],
        "used_source": resolved["used_source"],
        "parcel_feature_collection": resolved["parcel_feature_collection"],
        "parcel_labels": resolved["parcel_labels"],
        "geocoder": resolved["geocoder"],
        "feature_collection": feature_collection,
    }


def build_building_payload(
    unique_key: str,
    selected_feature: dict[str, Any] | None,
    validated_name: str | None,
    city_name: str | None = None,
) -> dict[str, Any]:
    data = get_building_naming_rows(city_name=city_name)
    row = next((item for item in data["rows"] if item["unique_key"] == str(unique_key)), None)
    if row is None:
        raise ValueError(f"Clé inconnue : {unique_key}")
    resolved = _resolve_point_and_parcels(row["address_display"], row["references"])
    feature_properties = (selected_feature or {}).get("properties", {}) or {}
    attributes = feature_properties.get("attributes", {}) or {}
    resolved_candidates = _dedupe_candidate_dicts(feature_properties.get("resolved_name_candidates") or [])
    proposed_name = str(
        validated_name
        or feature_properties.get("resolved_name")
        or feature_properties.get("name")
        or feature_properties.get("resolved_label")
        or feature_properties.get("label")
        or ""
    ).strip()
    return {
        "unique_key": row["unique_key"],
        "source_file": data["filename"],
        "source_rows": row["source_rows"],
        "reference_norm": row["first_reference_norm"] or None,
        "nom_batiment": proposed_name or None,
        "nom_commune": row["nom_commune"],
        "numero_voirie": row["numero_voirie"] or None,
        "indice_repetition": row["indice_repetition"] or None,
        "nature_voie": row["nature_voie"] or None,
        "nom_voie": row["nom_voie"] or None,
        "prefixe": row["prefixe"] or None,
        "section": row["section"] or None,
        "numero_plan": row["numero_plan"] or None,
        "adresse_reconstituee": row["address_display"] or None,
        "latitude": resolved["lat"],
        "longitude": resolved["lon"],
        "source_creation": "DGFIP_MAJIC",
        "statut_geocodage": "IGN_VALIDE" if selected_feature else "A_VERIFIER",
        "majic_building_values_json": json.dumps(row["majic_building_values"], ensure_ascii=False),
        "majic_entry_values_json": json.dumps(row["majic_entry_values"], ensure_ascii=False),
        "majic_level_values_json": json.dumps(row["majic_level_values"], ensure_ascii=False),
        "majic_door_values_json": json.dumps(row["majic_door_values"], ensure_ascii=False),
        "ign_layer": feature_properties.get("ign_layer") if selected_feature else None,
        "ign_typename": feature_properties.get("ign_typename") if selected_feature else None,
        "ign_id": feature_properties.get("ign_id") if selected_feature else None,
        "ign_name": feature_properties.get("name") if selected_feature else None,
        "ign_label": feature_properties.get("label") if selected_feature else None,
        "ign_name_proposed": feature_properties.get("resolved_name") if selected_feature else None,
        "ign_name_source": feature_properties.get("resolved_name_source") if selected_feature else None,
        "ign_name_distance_m": feature_properties.get("resolved_name_distance_m") if selected_feature else None,
        "ign_attributes_json": json.dumps(attributes, ensure_ascii=False) if attributes else None,
        "ign_toponym_candidates_json": json.dumps(resolved_candidates, ensure_ascii=False) if resolved_candidates else None,
        "parcel_labels_json": json.dumps(resolved["parcel_labels"], ensure_ascii=False) if resolved["parcel_labels"] else None,
    }
