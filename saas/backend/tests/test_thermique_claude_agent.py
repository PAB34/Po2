"""Préparation et décodage du pont Claude Code local."""
import json

from PIL import Image

from app.services import thermique_claude_agent


def test_prepare_bundle_fournit_vue_globale_et_six_tuiles(tmp_path):
    manifest = thermique_claude_agent.prepare_bundle(
        Image.new("RGB", (600, 400), "white"), tmp_path, auto_crop=False
    )

    assert manifest["uses_pdf_vectors"] is False
    assert manifest["width_px"] == 600
    assert len(manifest["tiles"]) == 6
    assert (tmp_path / "overview.jpg").is_file()
    assert all((tmp_path / f"tile-{index}.jpg").is_file() for index in range(1, 7))
    assert manifest["tiles"][0]["box_norm"][0:2] == [0.0, 0.0]
    assert manifest["tiles"][-1]["box_norm"][2:4] == [1000.0, 1000.0]


def test_prepare_bundle_applique_rotation_sans_perdre_le_repere(tmp_path):
    manifest = thermique_claude_agent.prepare_bundle(
        Image.new("RGB", (600, 400), "white"), tmp_path, 90, auto_crop=False
    )

    assert manifest["width_px"] == 400
    assert manifest["height_px"] == 600
    assert manifest["rotation_deg_ccw"] == 90


def test_detect_plan_box_prefere_le_dessin_principal_au_cartouche():
    image = Image.new("RGB", (1000, 600), "white")
    pixels = image.load()
    for y in range(100, 500):
        for x in range(80, 620):
            if x % 25 < 7 or y % 25 < 7:
                pixels[x, y] = (0, 0, 0)
    for y in range(250, 520):
        for x in range(760, 950):
            if x % 35 < 5 or y % 35 < 5:
                pixels[x, y] = (0, 0, 0)

    left, top, right, bottom = thermique_claude_agent.detect_plan_box(image)

    assert left < 100
    assert right < 760
    assert top < 120
    assert bottom > 480


def test_save_result_reprojette_les_points_du_crop_sur_la_page(tmp_path):
    raw = {"objects": [{"category": "cloison", "points": [[0, 0], [1000, 1000]]}], "observations": []}
    manifest = {
        "crop_box_px": [100, 50, 900, 450],
        "page_width_px": 1000,
        "page_height_px": 500,
        "width_px": 800,
        "height_px": 400,
    }

    result = thermique_claude_agent.save_result(raw, manifest, tmp_path / "result.json", "opus")

    assert result["objects"][0]["points_analysis_norm"] == [[0, 0], [1000, 1000]]
    assert result["objects"][0]["points"] == [[100.0, 100.0], [900.0, 900.0]]
    assert result["objects"][0]["id"] == "cloison-001"


def test_render_projection_ajoute_une_legende(tmp_path):
    overview = tmp_path / "overview.jpg"
    Image.new("RGB", (600, 400), "white").save(overview)
    result = {
        "manifest": {"overview": str(overview)},
        "objects": [
            {
                "id": "mur_exterieur-001",
                "category": "mur_exterieur",
                "geometry_type": "polyline",
                "points_analysis_norm": [[100, 100], [900, 900]],
                "review_required": False,
            }
        ],
    }

    destination = thermique_claude_agent.render_projection(result, tmp_path / "projection.png")

    with Image.open(destination) as projection:
        assert projection.width > 600
        assert projection.height == 400


def test_parse_cli_output_accepte_structured_output():
    raw = {"objects": [{"category": "cloison"}], "observations": []}

    assert thermique_claude_agent.parse_cli_output(json.dumps({"structured_output": raw})) == raw


def test_parse_cli_output_accepte_resultat_json_en_texte():
    raw = {"objects": [], "observations": ["plan vide"]}

    assert thermique_claude_agent.parse_cli_output(json.dumps({"result": json.dumps(raw)})) == raw
