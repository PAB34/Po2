"""Jalons J3-J4 de la détection exacte des murs : appariement des faces, jonctions, fins de mur, parois
composées, murs courbes et mesure contre une vérité terrain. Voir docs/thermique/detection-murs-strategie.md."""
from __future__ import annotations

import math

import pytest

from thermique_moteur import evaluation, murs, vecteurs

M = 1000 / 100 / (25.4 / 72)  # points PDF pour 1 m à 1/100


def _faces(segments):
    return murs.faces_de_murs(vecteurs.fusionner_lignes([(*s, 1.56, 0) for s in segments]))


def test_mur_droit_d_epaisseur_exacte_et_fins():
    # Mur de 30 cm sur 5 m, faces hachées en morceaux, fermé par deux petits traits de fin.
    e, L = 0.30 * M, 5 * M
    segments = [(k * L / 10, 0, (k + 1) * L / 10, 0) for k in range(10)] + [(0, e, L, e), (0, 0, 0, e), (L, 0, L, e)]
    faces = _faces(segments)
    trouves = murs.apparier_faces(faces, 100)
    assert len(trouves) == 1
    mur = trouves[0]
    assert mur["epaisseur_m"] == pytest.approx(0.30, abs=0.001)
    assert mur["longueur_m"] == pytest.approx(5.0, abs=0.02)
    fins = murs.fins_de_mur(faces, trouves, 100)
    assert len(fins) == 2 and set(fins.values()) == {0}


def test_pas_de_mur_a_travers_une_jonction_ni_d_un_mur_a_l_autre():
    # Deux murs parallèles de 20 cm séparés par un vide de 40 cm, plus un mur perpendiculaire qui les relie.
    L = 6 * M
    y = [0, 0.20 * M, 0.60 * M, 0.80 * M]
    segments = [(0, v, L, v) for v in y]
    # mur perpendiculaire de 20 cm entre les deux (faces verticales de y=0,20 à 0,60)
    x0, x1 = 3 * M, 3.2 * M
    segments += [(x0, y[1], x0, y[2]), (x1, y[1], x1, y[2])]
    faces = _faces(segments)
    trouves = murs.apparier_faces(faces, 100)
    epaisseurs = sorted(round(t["epaisseur_m"], 2) for t in trouves)
    # deux murs de 20 cm horizontaux, le mur vertical de 20 cm ; jamais le vide de 40 cm ni 80 cm
    assert 0.4 not in epaisseurs and 0.6 not in epaisseurs and 0.8 not in epaisseurs
    assert epaisseurs.count(0.2) >= 3


def test_paroi_composee_locale():
    # Doublage de 10 cm qui longe un mur de 40 cm (0 à 3 m) puis un mur de 20 cm (3 à 6 m).
    L = 6 * M
    segments = [
        (0, 0, L, 0),  # face intérieure du doublage
        (0, 0.10 * M, L, 0.10 * M),  # face commune doublage / murs
        (0, 0.50 * M, 3 * M, 0.50 * M),  # face extérieure du mur de 40 cm
        (3 * M, 0.30 * M, L, 0.30 * M),  # face extérieure du mur de 20 cm
        (3 * M, 0.30 * M, 3 * M, 0.50 * M),  # décroché
    ]
    faces = _faces(segments)
    trouves = murs.apparier_faces(faces, 100)
    parois = murs.parois_composees(trouves)
    epaisseurs = sorted(p["epaisseur_m"] for p in parois)
    assert 0.7 not in [round(e, 2) for e in epaisseurs]  # jamais 10 + 40 + 20
    assert any(round(p["epaisseur_m"], 2) == 0.5 and len(p["couches"]) == 2 for p in parois)
    assert any(round(p["epaisseur_m"], 2) == 0.3 and len(p["couches"]) == 2 for p in parois)


def test_mur_courbe_non_concentrique():
    # Quart de cercle de rayon 2 m (face intérieure) et face extérieure de rayon 2,20 m dont le centre est décalé
    # de 0,3 pt (1 cm à 1/100) : les deux faces ne sont pas exactement concentriques, comme à l'impression.
    def arc(cx, cy, r, morceaux=16):
        pts = [(cx + r * math.cos(math.pi / 2 * k / morceaux), cy + r * math.sin(math.pi / 2 * k / morceaux)) for k in range(morceaux + 1)]
        return [(*pts[k], *pts[k + 1]) for k in range(morceaux)]

    segments = arc(500, 500, 2.0 * M) + arc(500.3, 500.3, 2.2 * M)
    faces = murs.faces_de_murs(vecteurs.fusionner_lignes([(*s, 1.56, 0) for s in segments]))
    arcs = murs.arcs_de_faces(faces, 100)
    assert len(arcs) == 2
    courbes = murs.apparier_arcs(arcs, 100)
    assert len(courbes) == 1
    # Le décalage de centre (1 cm) fait varier l'écart réel entre les deux faces de 20 à 21 cm environ.
    assert courbes[0]["epaisseur_m"] == pytest.approx(0.20, abs=0.02)


def test_feuillure_en_bout_de_mur_suit_le_contour_de_l_aplat():
    # Mur rempli de 30 cm sur 3 m, terminé par une feuillure de 10 × 10 cm dans l'angle (porte).
    e, L, f = 0.30 * M, 3 * M, 0.10 * M
    contour = [(0, 0), (L, 0), (L, e - f), (L - f, e - f), (L - f, e), (0, e)]
    segments = [(*contour[k], *contour[(k + 1) % len(contour)]) for k in range(len(contour))]
    faces = _faces(segments)
    anneaux = [{"luminance": 153, "points": contour, "aire_pt2": 0.0, "facettes": 1}]
    trouves = murs.apparier_faces(faces, 100, anneaux)
    assert [round(t["epaisseur_m"], 2) for t in trouves] == [0.3]
    appariees = {i for t in trouves for i in t["faces"]} | set(murs.fins_de_mur(faces, trouves, 100))
    restantes = {i for i in range(len(faces)) if i not in appariees}
    assert restantes and restantes <= set(murs.faces_de_contour(faces, anneaux, trouves))


def test_mesure_contre_la_verite_terrain():
    reference = [
        {"x1": 0, "y1": 0, "x2": 10 * M, "y2": 0, "epaisseur_m": 0.30},
        {"x1": 0, "y1": 5 * M, "x2": 4 * M, "y2": 5 * M, "epaisseur_m": 0.20},
    ]
    detectes = [
        {"x1": 0, "y1": 0.01 * M, "x2": 10 * M, "y2": 0.01 * M, "epaisseur_m": 0.305},  # juste (axe à 1 cm)
        {"x1": 0, "y1": 5 * M, "x2": 2 * M, "y2": 5 * M, "epaisseur_m": 0.25},  # moitié du mur, épaisseur fausse
        {"x1": 0, "y1": 9 * M, "x2": 3 * M, "y2": 9 * M, "epaisseur_m": 0.10},  # faux mur
    ]
    score = evaluation.evaluer_murs(detectes, reference, 100)
    assert score["lineaire_reference_m"] == pytest.approx(14.0)
    assert score["rappel"] == pytest.approx(12 / 14, abs=1e-3)
    assert score["precision"] == pytest.approx(12 / 15, abs=1e-3)
    assert score["ecart_epaisseur_max_m"] == pytest.approx(0.05)
    assert [f["exces_m"] for f in score["faux_murs"]] == [pytest.approx(3.0)]
    assert [manque["reference"] for manque in score["murs_manques"]] == [1]
