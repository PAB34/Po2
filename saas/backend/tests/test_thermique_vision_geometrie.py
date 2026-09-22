import numpy as np

from app.services.thermique_vision_geometrie import mettre_au_propre, recaler, redresser, simplifier


def test_simplifier_supprime_les_zigzags_d_un_trait_droit():
    zigzag = [(0, 0), (50, 3), (100, -2), (150, 4), (200, 0)]

    assert simplifier(zigzag) == [(0.0, 0.0), (200.0, 0.0)]


def test_simplifier_garde_les_vrais_angles_d_un_contour():
    contour = [(0, 0), (100, 2), (200, 0), (200, 100), (0, 100)]

    assert len(simplifier(contour, ferme=True)) == 4


def test_redresser_rend_orthogonal_un_mur_presque_droit_et_le_garde_connecte():
    mur = [(0, 0), (300, 12), (310, 200)]

    net = redresser(mur, [0.0, 90.0])

    assert net[0][1] == net[1][1]
    assert abs(net[1][0] - net[2][0]) < 1e-6


def test_redresser_garde_une_facade_en_biais_hors_directions():
    biais = [(0, 0), (300, 90)]

    net = redresser(biais, [0.0, 90.0])

    assert abs((net[1][1] - net[0][1]) / (net[1][0] - net[0][0]) - 0.3) < 1e-6


def test_redresser_ferme_un_rectangle_bruite_en_quatre_sommets():
    piece = [(0, 0), (150, 3), (300, -2), (302, 200), (1, 198)]

    net = redresser(simplifier(piece, ferme=True), [0.0, 90.0], ferme=True)

    assert len(net) == 4
    xs = sorted(round(p[0]) for p in net)
    ys = sorted(round(p[1]) for p in net)
    assert xs[0] == xs[1] and xs[2] == xs[3]
    assert ys[0] == ys[1] and ys[2] == ys[3]


def test_recaler_ramene_un_mur_sur_sa_bande_d_encre():
    encre = np.zeros((200, 400), dtype=np.float32)
    encre[108:118, 20:380] = 1.0  # mur réel centré sur y = 112,5

    net = recaler([(20.0, 100.0), (380.0, 100.0)], encre, 9)

    assert all(abs(y - 112.5) <= 1.5 for _, y in net)


def test_mettre_au_propre_travaille_en_repere_normalise():
    objets = [
        {"category": "cloison", "geometry_type": "polyline", "points": [[100, 100], [500, 104], [900, 99]]},
        {"category": "piece", "geometry_type": "polygon", "points": [[100, 100], [900, 102], [898, 500], [101, 499]]},
    ]

    bilan = mettre_au_propre(objets, 1000, 1000)

    assert len(objets[0]["points"]) == 2
    assert objets[0]["points"][0][1] == objets[0]["points"][1][1]
    assert len(objets[1]["points"]) == 4
    assert bilan["sommets_apres"] < bilan["sommets_avant"]


def test_separer_espaces_ampute_la_grande_piece_d_un_espace_en_bord():
    from app.services.thermique_vision_geometrie import separer_espaces

    grande = {"id": "piece-001", "category": "piece", "geometry_type": "polygon",
              "points": [[0, 0], [100, 0], [100, 100], [0, 100]]}
    coin = {"id": "piece-002", "category": "piece", "geometry_type": "polygon",
            "points": [[60, 0], [100, 0], [100, 40], [60, 40]]}

    assert separer_espaces([grande, coin]) == 1
    assert len(grande["points"]) == 6
    assert "enclaves" not in grande


def test_separer_espaces_rattache_une_tremie_enclavee_sans_trou():
    from app.services.thermique_vision_geometrie import separer_espaces

    grande = {"id": "piece-001", "category": "piece", "geometry_type": "polygon",
              "points": [[0, 0], [100, 0], [100, 100], [0, 100]]}
    vide = {"id": "indetermine-001", "category": "indetermine", "geometry_type": "polygon",
            "points": [[40, 40], [60, 40], [60, 60], [40, 60]]}

    assert separer_espaces([grande, vide]) == 0
    assert grande["enclaves"] == ["indetermine-001"]
    assert len(grande["points"]) == 4
