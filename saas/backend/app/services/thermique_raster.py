"""Rendu des planches en tuiles d'images (pdfium) pour une visionneuse fluide.

Mesuré sur le projet d'essai (2026-09-11) : dans le navigateur, pdf.js met 10 s à dessiner
le plan niveau 0 et 47 s la coupe AB (≈ 650 000 traits), et recommence à chaque zoom.
pdfium (le moteur PDF de Chrome) rend la même coupe à 300 dpi en 0,9 s côté serveur.
Chaque planche est donc rendue une fois, en pyramide de tuiles PNG : le navigateur
n'affiche plus que des images.

Les mesures restent en coordonnées PDF (points) : la fiche des tuiles fournit la
transformation affine PDF → pixels, calculée par pdfium lui-même (FPDF_PageToDevice),
donc cohérente par construction avec le rendu, rotation comprise.
"""
from __future__ import annotations

import ctypes
import hashlib
import hmac
import io
import json
import math
import shutil
import threading
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image

from app.core.config import settings

TILE_SIZE = 256
# Plus grand côté de l'image rendue : un A1 fait 5063 × 7168 px (≈ 216 dpi), soit
# ≈ 1,2 cm réel par pixel à 1/100. Borne la mémoire à ≈ 110 Mo par rendu.
MAX_SIDE_PX = 7168
TILE_URL_TTL_SECONDS = 12 * 3600
MANIFEST_NAME = "manifest.json"
# Un rendu à la fois : borne la mémoire du serveur.
_BUILD_LOCK = threading.Lock()


def raster_root(project_id: int, sheet_id: int) -> Path:
    return Path(settings.thermique_storage_dir) / f"projet_{project_id}" / "tuiles" / f"planche_{sheet_id}"


def raster_dir(project_id: int, sheet_id: int, rotation: int) -> Path:
    return raster_root(project_id, sheet_id) / f"r{rotation}"


def load_manifest(out_dir: Path) -> dict[str, Any] | None:
    path = out_dir / MANIFEST_NAME
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_raster(pdf_path: Path, page_index: int, rotation: int, out_dir: Path) -> dict[str, Any]:
    manifest = load_manifest(out_dir)
    if manifest is not None:
        return manifest
    with _BUILD_LOCK:
        manifest = load_manifest(out_dir)
        if manifest is None:
            manifest = build_raster(pdf_path, page_index, rotation, out_dir)
    return manifest


def _page_to_raster_transform(page: Any, width_px: int, height_px: int, rotation: int) -> list[float]:
    """Transformation [a, b, c, d, e, f] : px = a·x + c·y + e ; py = b·x + d·y + f."""
    import pypdfium2.raw as pdfium_c

    def device(x: float, y: float) -> tuple[int, int]:
        device_x, device_y = ctypes.c_int(), ctypes.c_int()
        ok = pdfium_c.FPDF_PageToDevice(
            page.raw, 0, 0, width_px, height_px, rotation // 90, x, y, ctypes.byref(device_x), ctypes.byref(device_y)
        )
        if not ok:
            raise RuntimeError("FPDF_PageToDevice a échoué")
        return device_x.value, device_y.value

    # Points de référence éloignés : l'arrondi entier de pdfium devient négligeable.
    reference = 10000.0
    origin_x, origin_y = device(0.0, 0.0)
    along_x = device(reference, 0.0)
    along_y = device(0.0, reference)
    return [
        (along_x[0] - origin_x) / reference,
        (along_x[1] - origin_y) / reference,
        (along_y[0] - origin_x) / reference,
        (along_y[1] - origin_y) / reference,
        float(origin_x),
        float(origin_y),
    ]


def _is_blank(tile: Image.Image) -> bool:
    return all(low >= 250 for low, _high in tile.getextrema())


def build_raster(pdf_path: Path, page_index: int, rotation: int, out_dir: Path) -> dict[str, Any]:
    """Rend une page en pyramide de tuiles.

    Les tuiles sont écrites en place et la fiche (manifest.json) en dernier : elle marque
    la fin du rendu, si bien qu'un rendu interrompu reste invisible et sera refait.
    """
    import pypdfium2 as pdfium

    started = time.perf_counter()
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True)

    document = pdfium.PdfDocument(str(pdf_path))
    try:
        page = document[page_index]
        width_pt, height_pt = page.get_size()
        if rotation in (90, 270):
            width_pt, height_pt = height_pt, width_pt
        scale = MAX_SIDE_PX / max(width_pt, height_pt)
        image = page.render(scale=scale, rotation=rotation).to_pil().convert("RGB")
        width_px, height_px = image.size
        transform = _page_to_raster_transform(page, width_px, height_px, rotation)
        page.close()
    finally:
        document.close()

    max_level = max(0, math.ceil(math.log2(max(width_px, height_px) / TILE_SIZE)))
    levels: list[dict[str, int]] = [{} for _ in range(max_level + 1)]
    tiles: dict[str, list[str]] = {}
    current = image
    for z in range(max_level, -1, -1):
        level_dir = out_dir / str(z)
        level_dir.mkdir()
        cols = math.ceil(current.width / TILE_SIZE)
        rows = math.ceil(current.height / TILE_SIZE)
        kept: list[str] = []
        for ty in range(rows):
            for tx in range(cols):
                box = (
                    tx * TILE_SIZE,
                    ty * TILE_SIZE,
                    min((tx + 1) * TILE_SIZE, current.width),
                    min((ty + 1) * TILE_SIZE, current.height),
                )
                tile = current.crop(box)
                if _is_blank(tile):
                    continue  # servie en blanc sans être stockée
                if tile.size != (TILE_SIZE, TILE_SIZE):
                    padded = Image.new("RGB", (TILE_SIZE, TILE_SIZE), "white")
                    padded.paste(tile, (0, 0))
                    tile = padded
                tile.save(level_dir / f"{tx}_{ty}.png", compress_level=6)
                kept.append(f"{tx}_{ty}")
        levels[z] = {"z": z, "width": current.width, "height": current.height, "cols": cols, "rows": rows}
        tiles[str(z)] = kept
        if z > 0:
            current = current.reduce(2)

    manifest = {
        "rotation": rotation,
        "tile_size": TILE_SIZE,
        "width_px": width_px,
        "height_px": height_px,
        "scale": scale,
        "transform": transform,
        "levels": levels,
        "tiles": tiles,
        "build_seconds": round(time.perf_counter() - started, 2),
    }
    partial = out_dir / f"{MANIFEST_NAME}.part"
    partial.write_text(json.dumps(manifest), encoding="utf-8")
    partial.replace(out_dir / MANIFEST_NAME)
    return manifest


# --- Adresses de tuiles signées --------------------------------------------------
# Une balise <img> ne peut pas envoyer d'en-tête d'authentification : la fiche des tuiles
# (appel authentifié) fournit une adresse signée, limitée à une planche et à 12 h.


def _signature(sheet_id: int, rotation: int, expires: int) -> str:
    message = f"thermique-tuiles:{sheet_id}:{rotation}:{expires}".encode()
    return hmac.new(settings.secret_key.encode(), message, hashlib.sha256).hexdigest()[:32]


def tile_url(sheet_id: int, rotation: int, now: float | None = None) -> str:
    expires = int(now if now is not None else time.time()) + TILE_URL_TTL_SECONDS
    signature = _signature(sheet_id, rotation, expires)
    return f"/thermique/sheets/{sheet_id}/tiles/{rotation}/{{z}}/{{x}}/{{y}}.png?e={expires}&s={signature}"


def check_tile_signature(sheet_id: int, rotation: int, expires: int, signature: str, now: float | None = None) -> bool:
    if expires < (now if now is not None else time.time()):
        return False
    return hmac.compare_digest(_signature(sheet_id, rotation, expires), signature)


@lru_cache(maxsize=1)
def white_tile_png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (TILE_SIZE, TILE_SIZE), "white").save(buffer, format="PNG")
    return buffer.getvalue()
