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
    assert manifest["viewer_rotation_deg"] == 270


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
        "viewer_rotation_deg": 270,
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


def test_les_consignes_de_l_agent_passent_par_la_consigne_systeme_sans_son_en_tete():
    """`--agent` coupe la sortie structurée (2026-09-30) : on passe le corps du fichier de l'agent."""
    options = thermique_claude_agent.consignes_de_l_agent("thermicien-plan")
    assert options[0] == "--append-system-prompt"
    assert "--agent" not in options
    assert not options[1].startswith("---") and "name:" not in options[1].splitlines()[0]
    assert len(options[1]) > 200


def test_parse_cli_output_tolere_une_phrase_ou_un_bloc_autour_du_json():
    """Constaté le 2026-09-30 sur le N-1 : l'agent rédige autour de son JSON."""
    import pytest

    objets = [{"category": "cloison", "points": [[0, 0], [1, 1]]}]
    lire = lambda texte: [o["points"] for o in thermique_claude_agent.parse_cli_output(json.dumps({"result": texte}))["objects"]]
    attendu = [objets[0]["points"]]
    assert lire("Voici l'inventaire :\n```json\n" + json.dumps({"objects": objets}) + "\n```\nBonne lecture.") == attendu
    assert lire("Inventaire : " + json.dumps({"objets": objets}) + " fin.") == attendu
    assert lire(json.dumps(objets)) == attendu
    # Vocabulaire propre de l'agent quand la CLI n'impose pas le schéma (N-1 du projet 1).
    composants = {"components": [{"id": "mur_01", "category": "mur_exterieur", "geometry": [[1, 2], [3, 4]], "justification": "trait épais"}]}
    [objet] = thermique_claude_agent.parse_cli_output(json.dumps({"result": "```json\n" + json.dumps(composants) + "\n```"}))["objects"]
    assert objet["points"] == [[1, 2], [3, 4]]
    assert objet["evidence"] == "trait épais"
    assert objet["geometry_type"] == "polyline"
    assert "geometry" not in objet and "id" not in objet
    imbrique = {"composants": [{"categorie": "mur_refend", "geometry": {"type": "polygon", "points": [[1, 2], [3, 4], [5, 6]]}}]}
    [objet] = thermique_claude_agent.parse_cli_output(json.dumps({"result": json.dumps(imbrique)}))["objects"]
    assert (objet["category"], objet["geometry_type"], objet["points"]) == ("refend", "polygon", [[1, 2], [3, 4], [5, 6]])
    with pytest.raises(thermique_claude_agent.ThermiqueError, match="JSON valide"):
        thermique_claude_agent.parse_cli_output(json.dumps({"result": "Je n'ai pas pu lire le plan."}))


def test_cli_environment_retire_la_session_claude_hote():
    hote = {
        "PATH": "x",
        "CLAUDECODE": "1",
        "CLAUDE_CODE_ENTRYPOINT": "desktop",
        "CLAUDE_CODE_SESSION_ID": "s",
        "CLAUDE_AGENT_SDK_VERSION": "1",
        "ANTHROPIC_BASE_URL": "http://127.0.0.1:1",
        "CLAUDE_BIN": "claude",
    }

    environnement = thermique_claude_agent.cli_environment(hote)

    assert environnement == {"PATH": "x", "CLAUDE_BIN": "claude"}


def test_cli_environment_garde_une_adresse_api_choisie_hors_session():
    assert thermique_claude_agent.cli_environment({"ANTHROPIC_BASE_URL": "https://proxy"}) == {
        "ANTHROPIC_BASE_URL": "https://proxy"
    }
