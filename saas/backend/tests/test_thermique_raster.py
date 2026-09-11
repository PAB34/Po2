"""Tuiles des planches (pdfium) : position exacte d'un repère après rendu, rotation comprise,
et adresses de tuiles signées. Voir `app/services/thermique_raster.py`."""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from app.services import thermique_raster
from app.services.thermique_raster import (
    TILE_SIZE,
    build_raster,
    check_tile_signature,
    ensure_raster,
    tile_url,
)

# Carré noir de 40 pt dont le centre est en (120, 220), sur une page 600 × 800 pt.
MARK_CENTER = (120.0, 220.0)


def _pdf_with_mark(path: Path, intrinsic_rotation: int = 0) -> Path:
    writer = PdfWriter()
    page = writer.add_blank_page(width=600, height=800)
    content = DecodedStreamObject()
    content.set_data(b"0 0 0 rg 100 200 40 40 re f")
    page[NameObject("/Contents")] = writer._add_object(content)
    if intrinsic_rotation:
        page.rotate(intrinsic_rotation)
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def _pixel(out_dir: Path, manifest: dict, point: tuple[float, float]) -> tuple[int, int, int]:
    a, b, c, d, e, f = manifest["transform"]
    px = a * point[0] + c * point[1] + e
    py = b * point[0] + d * point[1] + f
    z = len(manifest["levels"]) - 1
    tx, ty = int(px // TILE_SIZE), int(py // TILE_SIZE)
    tile_path = out_dir / str(z) / f"{tx}_{ty}.png"
    if not tile_path.is_file():
        return (255, 255, 255)  # tuile blanche non stockée
    return Image.open(tile_path).convert("RGB").getpixel((int(px) % TILE_SIZE, int(py) % TILE_SIZE))


@pytest.mark.parametrize("intrinsic_rotation", [0, 90])
@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_le_repere_tombe_au_bon_pixel(tmp_path, intrinsic_rotation, rotation):
    pdf = _pdf_with_mark(tmp_path / "plan.pdf", intrinsic_rotation)
    out_dir = tmp_path / "tuiles"

    manifest = build_raster(pdf, 0, rotation, out_dir)

    portrait = (intrinsic_rotation + rotation) % 180 == 0
    assert (manifest["height_px"] > manifest["width_px"]) == portrait
    # pdfium arrondit la taille de l'image au pixel supérieur.
    assert abs(max(manifest["width_px"], manifest["height_px"]) - thermique_raster.MAX_SIDE_PX) <= 1
    assert sum(_pixel(out_dir, manifest, MARK_CENTER)) < 100  # noir sous le repère
    assert sum(_pixel(out_dir, manifest, (400.0, 600.0))) > 700  # blanc ailleurs
    # Niveau 0 = toute la planche dans une tuile.
    assert manifest["levels"][0]["cols"] == 1 and manifest["levels"][0]["rows"] == 1


def test_rendu_fait_une_seule_fois(tmp_path, monkeypatch):
    pdf = _pdf_with_mark(tmp_path / "plan.pdf")
    out_dir = tmp_path / "tuiles"
    first = ensure_raster(pdf, 0, 0, out_dir)

    def interdit(*_args, **_kwargs):
        raise AssertionError("la planche ne doit pas être rendue deux fois")

    monkeypatch.setattr(thermique_raster, "build_raster", interdit)
    assert ensure_raster(pdf, 0, 0, out_dir) == first


def test_adresse_de_tuile_signee():
    url = tile_url(7, 90, now=1_000_000)
    query = dict(part.split("=") for part in url.split("?")[1].split("&"))
    expires, signature = int(query["e"]), query["s"]

    assert url.startswith("/thermique/sheets/7/tiles/90/{z}/{x}/{y}.png?")
    assert check_tile_signature(7, 90, expires, signature, now=1_000_000)
    assert not check_tile_signature(8, 90, expires, signature, now=1_000_000)  # autre planche
    assert not check_tile_signature(7, 0, expires, signature, now=1_000_000)  # autre rotation
    assert not check_tile_signature(7, 90, expires, "0" * 32, now=1_000_000)
    assert not check_tile_signature(7, 90, expires, signature, now=expires + 1)  # expirée
