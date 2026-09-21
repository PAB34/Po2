"""Contrat raster-only de l'analyse visuelle des plans."""
from types import SimpleNamespace

import pytest
from PIL import Image

from app.services import thermique_vision
from app.services.thermique import ThermiqueError


def test_tuiles_recouvrantes_couvrent_toute_image():
    boxes = thermique_vision.tile_boxes(4700, 3700)

    assert len(boxes) == 6
    assert boxes[0][0:2] == (0, 0)
    assert boxes[-1][2:4] == (4700, 3700)
    assert boxes[0][2] > boxes[1][0]
    assert boxes[0][3] > boxes[3][1]


def test_recompose_uniquement_les_tuiles_raster(tmp_path):
    directory = tmp_path / "raster"
    (directory / "0").mkdir(parents=True)
    Image.new("RGB", (256, 256), "black").save(directory / "0" / "0_0.png")
    manifest = {
        "levels": [{"z": 0, "width": 300, "height": 256, "cols": 2, "rows": 1}],
    }

    image = thermique_vision.compose_raster(directory, manifest)

    assert image.size == (300, 256)
    assert image.getpixel((10, 10)) == (0, 0, 0)
    assert image.getpixel((280, 10)) == (255, 255, 255)


def test_coordonnees_normalisees_redeviennent_points_pdf():
    manifest = {
        "width_px": 2000,
        "height_px": 1000,
        "transform": [2.0, 0.0, 0.0, -2.0, 10.0, 810.0],
    }

    assert thermique_vision.normalized_to_pdf([505, 410], manifest) == [500.0, 200.0]


def test_resultat_force_la_revision_sous_le_seuil(monkeypatch):
    monkeypatch.setattr(thermique_vision.settings, "thermique_vision_model", "vision-test")
    manifest = {"width_px": 1000, "height_px": 1000, "transform": [1, 0, 0, 1, 0, 0]}
    raw = {
        "objects": [
            {
                "category": "terrasse",
                "subtype": "accessible",
                "geometry_type": "polygon",
                "points": [[100, 100], [300, 100], [300, 300], [100, 300]],
                "confidence": 0.7,
                "evidence": "trame extérieure et libellé terrasse",
                "review_required": False,
            }
        ],
        "observations": ["aucun balcon visible"],
    }

    result = thermique_vision.normalize_result(raw, manifest)

    assert result["method"] == "ia_visuelle_raster"
    assert result["uses_pdf_vectors"] is False
    assert result["objects"][0]["id"] == "terrasse-001"
    assert result["objects"][0]["review_required"] is True
    assert result["review_count"] == 1


def test_requete_vision_ne_contient_que_des_images_raster(monkeypatch):
    monkeypatch.setattr(thermique_vision.settings, "thermique_vision_model", "vision-test")

    request = thermique_vision.build_request(Image.new("RGB", (600, 400), "white"))
    content = request["input"][0]["content"]
    images = [item for item in content if item["type"] == "input_image"]

    assert request["model"] == "vision-test"
    assert len(images) == 7  # vue globale + six tuiles recouvrantes
    assert all(item["image_url"].startswith("data:image/jpeg;base64,") for item in images)
    assert "file_id" not in str(request)
    assert "json_schema" == request["text"]["format"]["type"]


def test_ajout_et_suppression_manuels_recalculent_le_bilan(tmp_path, monkeypatch):
    path = tmp_path / "vision-analysis.json"
    path.write_text('{"objects":[],"counts":{},"review_count":0}', encoding="utf-8")
    monkeypatch.setattr(thermique_vision, "analysis_path", lambda _sheet: path)
    sheet = SimpleNamespace(id=1, project_id=1)

    added = thermique_vision.create_object(
        sheet,
        {"category": "cloison", "geometry_type": "polyline", "points": [[1, 2], [3, 4]]},
    )

    assert added["objects"][0]["id"] == "manuel-001"
    assert added["counts"] == {"cloison": 1}
    deleted = thermique_vision.delete_object(sheet, "manuel-001")
    assert deleted["objects"] == []
    assert deleted["counts"] == {}


def test_import_agent_claude_reprojette_et_persiste(monkeypatch):
    manifest = {"width_px": 1000, "height_px": 1000, "transform": [1, 0, 0, 1, 0, 0]}
    sheet = SimpleNamespace(id=4, project_id=2, rotation_deg=270, page_index=0, document=object())
    written = {}
    monkeypatch.setattr(thermique_vision, "raster_dir", lambda *_args: None)
    monkeypatch.setattr(thermique_vision, "document_path", lambda _document: None)
    monkeypatch.setattr(thermique_vision, "ensure_raster", lambda *_args: manifest)
    monkeypatch.setattr(thermique_vision, "_write", lambda _sheet, result: written.update(result))

    result = thermique_vision.import_agent_result(
        sheet,
        {
            "model": "opus",
            "viewer_rotation_deg": 270,
            "objects": [
                {
                    "category": "mur_exterieur",
                    "subtype": "façade",
                    "geometry_type": "polyline",
                    "points": [[100, 200], [900, 200]],
                    "confidence": 0.95,
                    "evidence": "double trait épais",
                    "review_required": False,
                }
            ],
            "observations": [],
        },
    )

    assert result["method"] == "claude_code_agent_raster"
    assert result["model"] == "opus"
    assert result["objects"][0]["points"] == [[100.0, 200.0], [900.0, 200.0]]
    assert written["agent_rotation_deg"] == 270


def test_import_agent_refuse_une_rotation_differente():
    sheet = SimpleNamespace(id=4, project_id=2, rotation_deg=0)

    with pytest.raises(ThermiqueError, match="rotation"):
        thermique_vision.import_agent_result(sheet, {"viewer_rotation_deg": 270, "objects": []})
