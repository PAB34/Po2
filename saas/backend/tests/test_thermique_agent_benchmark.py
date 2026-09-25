"""Comparateur neutre des agents thermiciens raster."""
from app.services.thermique_agent_benchmark import comparer_sorties, valider_sortie


def _piece(name: str, points: list[list[float]], local: str = "chauffe") -> dict:
    return {
        "category": "piece", "subtype": name, "geometry_type": "polygon", "points": points,
        "confidence": 0.8, "evidence": "contour fermé visible", "review_required": False, "local": local,
    }


def _payload(*objects: dict) -> dict:
    return {"objects": list(objects), "observations": []}


def test_sorties_identiques_ont_un_accord_parfait():
    payload = _payload(_piece("Bureau", [[0, 0], [100, 0], [100, 100], [0, 100]]))
    report = comparer_sorties(payload, payload)
    assert report["summary"]["symmetric_match_rate"] == 1
    assert report["summary"]["mean_geometry_score"] == 1
    assert report["summary"]["piece_coverage_iou"] == 1
    assert report["summary"]["piece_nature_agreement"] == 1


def test_comparaison_signale_les_objets_absents_et_supplementaires():
    reference = _payload(
        _piece("Bureau", [[0, 0], [100, 0], [100, 100], [0, 100]]),
        _piece("Salle", [[200, 0], [300, 0], [300, 100], [200, 100]]),
    )
    candidate = _payload(
        _piece("Bureau", [[5, 0], [105, 0], [105, 100], [5, 100]]),
        _piece("Local ajouté", [[500, 0], [600, 0], [600, 100], [500, 100]]),
    )
    report = comparer_sorties(reference, candidate)
    assert report["summary"]["matched_objects"] == 1
    assert report["unmatched_reference"] == [{"category": "piece", "subtype": "Salle"}]
    assert report["unmatched_candidate"] == [{"category": "piece", "subtype": "Local ajouté"}]


def test_validation_ne_corrige_pas_un_contrat_invalide():
    invalid = _piece("Bureau", [[0, 0], [100, 0], [100, 100]])
    invalid["category"] = "mur_refend"
    invalid["confidence"] = 2
    objects, issues = valider_sortie(_payload(invalid))
    assert objects == []
    assert any("catégorie inconnue" in issue for issue in issues)
    assert any("confiance invalide" in issue for issue in issues)


def test_nature_thermique_reste_optionnelle_pour_une_ancienne_sortie():
    legacy = _piece("Bureau", [[0, 0], [100, 0], [100, 100]])
    legacy.pop("local")
    objects, issues = valider_sortie(_payload(legacy))
    assert objects == [legacy]
    assert issues == []


def test_une_gaine_technique_est_une_nature_valide():
    gaine = _piece("Gaine", [[0, 0], [100, 0], [100, 100]], local="gaine_technique")
    objects, issues = valider_sortie(_payload(gaine))
    assert objects == [gaine]
    assert issues == []


def test_objet_avec_confiance_invalide_est_exclu_des_statistiques():
    invalid = _piece("Bureau", [[0, 0], [100, 0], [100, 100]])
    invalid["confidence"] = "forte"
    objects, issues = valider_sortie(_payload(invalid))
    assert objects == []
    assert issues == ["objet 1: confiance invalide"]


def test_couverture_ne_depend_pas_du_decoupage_des_lignes():
    def wall(points: list[list[float]]) -> dict:
        return {
            "category": "mur_exterieur", "subtype": "façade", "geometry_type": "polyline",
            "points": points, "confidence": 0.8, "evidence": "trait épais", "review_required": False,
        }

    reference = _payload(wall([[0, 0], [100, 0]]), wall([[100, 0], [200, 0]]))
    candidate = _payload(wall([[0, 0], [200, 0]]))
    report = comparer_sorties(reference, candidate)
    assert report["categories"]["mur_exterieur"]["symmetric_match_rate"] < 1
    assert report["categories"]["mur_exterieur"]["coverage_iou"] == 1


def test_validation_refuse_les_champs_et_points_hors_contrat():
    invalid = _piece("Bureau", [[0, 0], [100, 0], [100, 100]])
    invalid["commentaire_libre"] = "hors contrat"
    invalid["points"].append(["x", 100])
    objects, issues = valider_sortie({"objects": [invalid], "observations": [3], "meta": {}})
    assert objects == []
    assert any("Champs racine inconnus" in issue for issue in issues)
    assert any("observations contient" in issue for issue in issues)
    assert any("champs inconnus" in issue for issue in issues)
    assert any("points invalides" in issue for issue in issues)
