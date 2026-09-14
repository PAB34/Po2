"""Lot M3 : contour au nu intérieur détecté sur un plan et planchers repérés sur une coupe, à partir
de PDF fabriqués pour le test, puis report dans le métré du projet.
Voir docs/thermique/agent-verification-decisions.md."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import Base
from app.models.thermique import ThermiqueDocument, ThermiqueSheet
from app.services import thermique_metre
from app.services.thermique import ThermiqueError, create_project, document_path
from tests.test_thermique_metre import _pdf, _user
from thermique_moteur import coupes, detection, metre, traits

M = 1000 / 100 / (25.4 / 72)  # points PDF pour 1 m à 1/100
OX, OY = 60.0, 60.0
FACE_INTERIEURE = (OX + 0.3 * M, OY + 0.3 * M, OX + 9.7 * M, OY + 7.7 * M)
DESSUS_DALLES = [0.0, 2.88, 7.04, 10.88]  # m
EPAISSEURS = [0.25, 0.20, 0.16, 0.16]


def _rectangle(x0, y0, x1, y1, largeur, porte=None):
    """Contour tracé ; `porte` = (x_debut, x_fin) : ouverture dans le côté bas."""
    if porte:
        lignes = [f"{x0:.2f} {y0:.2f} m {porte[0]:.2f} {y0:.2f} l S", f"{porte[1]:.2f} {y0:.2f} m {x1:.2f} {y0:.2f} l S"]
    else:
        lignes = [f"{x0:.2f} {y0:.2f} m {x1:.2f} {y0:.2f} l S"]
    lignes += [
        f"{x1:.2f} {y0:.2f} m {x1:.2f} {y1:.2f} l S",
        f"{x1:.2f} {y1:.2f} m {x0:.2f} {y1:.2f} l S",
        f"{x0:.2f} {y1:.2f} m {x0:.2f} {y0:.2f} l S",
    ]
    return f"{largeur} w " + " ".join(lignes)


def _plan_pdf() -> bytes:
    # Mur extérieur de 30 cm (deux faces épaisses), porte de 1 m en façade basse, cloison fine qui
    # touche la façade : le contour doit suivre la face intérieure, porte refermée.
    porte = (OX + 4 * M, OX + 5 * M)
    contenu = " ".join(
        [
            _rectangle(OX, OY, OX + 10 * M, OY + 8 * M, 1.5, porte=porte),
            _rectangle(*FACE_INTERIEURE, 1.5, porte=porte),
            f"0.35 w {OX + 5 * M:.2f} {OY + 0.3 * M:.2f} m {OX + 5 * M:.2f} {OY + 4 * M:.2f} l S",
        ]
    )
    return _pdf(contenu.encode()).replace(b"/MediaBox [0 0 600 400]", b"/MediaBox [0 0 600 500]")


def _coupe_pdf() -> bytes:
    # Coupe tournée de 90° sur la feuille : planchers = paires de traits verticaux de 12 m.
    y0, y1 = 40.0, 40.0 + 12 * M
    lignes = []
    for dessus, epaisseur in zip(DESSUS_DALLES, EPAISSEURS):
        for x in (30 + (dessus - epaisseur) * M, 30 + dessus * M):
            lignes.append(f"{x:.2f} {y0:.2f} m {x:.2f} {y1:.2f} l S")
    lignes.append(f"20 {y0:.2f} m 20 {y0 + 0.8 * M:.2f} l S")  # petit trait parasite
    return _pdf(("1.5 w " + " ".join(lignes)).encode())


# --- Moteur ------------------------------------------------------------------------------------


def test_contour_au_nu_interieur_d_un_batiment_simple(tmp_path):
    chemin = tmp_path / "niveau.pdf"
    chemin.write_bytes(_plan_pdf())
    lus = traits.lire_traits(chemin, 0, avec_couleur=True)
    assert all(len(t) == 6 and t[5] == 0 for t in lus)  # traits noirs : luminance 0
    seuil = traits.seuil_propose(traits.classes_epaisseur(lus))
    assert seuil == 1.5
    resultat = detection.detecter_contour(lus, seuil, 100)
    assert resultat is not None
    assert resultat["aire_m2"] == pytest.approx(9.4 * 7.4, rel=0.01)
    assert resultat["perimetre_m"] == pytest.approx(2 * (9.4 + 7.4), rel=0.01)
    xs = sorted(x for x, _ in resultat["points"])
    assert xs[0] == pytest.approx(FACE_INTERIEURE[0], abs=0.5) and xs[-1] == pytest.approx(FACE_INTERIEURE[2], abs=0.5)
    zone = metre.synthese_niveau(100, 3.0, 0.2, [{"id": 1, "type": "contour", "points": resultat["points"], "cotes": []}], 2.6)
    assert zone["hauteur_interieure_m"] == 2.6  # la hauteur sous plafond saisie prime


def test_planchers_d_une_coupe_et_hauteurs_par_niveau(tmp_path):
    chemin = tmp_path / "coupe.pdf"
    chemin.write_bytes(_coupe_pdf())
    resultat = coupes.detecter_planchers(traits.lire_traits(chemin, 0), 0.9, 100)
    assert resultat["axe"] == "vertical" and len(resultat["dessins"]) == 1
    dessin = resultat["dessins"][0]
    assert [p["epaisseur_m"] for p in dessin["planchers"]] == pytest.approx(EPAISSEURS, abs=0.01)
    assert dessin["hauteurs_etage_m"] == pytest.approx([2.88, 4.16, 3.84], abs=0.01)
    niveaux = coupes.niveaux_depuis_coupe(dessin, resultat["pt_par_m"], sens_montant=True)
    assert niveaux[1] == {"epaisseur_plancher_m": 0.2, "hauteur_etage_m": 4.16, "hauteur_sous_plafond_m": 4.0}
    # Lu dans l'autre sens, le dessus de dalle devient l'autre face : les hauteurs d'étage changent de
    # la différence d'épaisseur entre planchers (4,16 → 4,20 ; 2,88 → 2,93).
    inverse = coupes.niveaux_depuis_coupe(dessin, resultat["pt_par_m"], sens_montant=False)
    assert [n["hauteur_etage_m"] for n in inverse] == pytest.approx([3.84, 4.20, 2.93], abs=0.01)


# --- Service -----------------------------------------------------------------------------------


def test_detection_et_hauteurs_reportees_dans_le_metre(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "thermique_storage_dir", str(tmp_path))
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        thermicien = _user(db, "be@example.fr")
        projet = create_project(db, thermicien, "Projet", None)
        planches = []
        for nom, nature, contenu in (("plan.pdf", "plan", _plan_pdf()), ("coupe.pdf", "coupe", _coupe_pdf())):
            document = ThermiqueDocument(
                project_id=projet.id, original_filename=nom, stored_filename=nom, file_format="pdf",
                size_bytes=len(contenu), sha256=nom.ljust(64, "0")[:64], page_count=1,
            )
            db.add(document)
            db.flush()
            document_path(document).parent.mkdir(parents=True, exist_ok=True)
            document_path(document).write_bytes(contenu)
            planche = ThermiqueSheet(
                project_id=projet.id, document_id=document.id, page_index=0, label=nom, nature=nature,
                rotation_deg=0, page_width_pt=600, page_height_pt=500, scale_denominator=100, scale_source="declaree",
            )
            db.add(planche)
            planches.append(planche)
        db.commit()
        plan, coupe = planches
        rdc = thermique_metre.create_level(db, projet, {"nom": "RDC", "planche_id": plan.id})
        thermique_metre.create_level(db, projet, {"nom": "R+1"})

        info = thermique_metre.detect_contour(db, rdc)
        assert info["aire_m2"] == pytest.approx(69.56, rel=0.01)
        thermique_metre.detect_contour(db, rdc)  # une détection non retouchée est simplement remplacée
        contours = [zone for zone in rdc.zones if zone.kind == "contour"]
        assert len(contours) == 1 and contours[0].source == "automatique"

        points = json.loads(contours[0].points_json)
        points[0] = [points[0][0] + 5, points[0][1]]
        thermique_metre.update_zone(db, contours[0], {"points": points})
        assert contours[0].source == "corrige"
        with pytest.raises(ThermiqueError, match="confirmez"):
            thermique_metre.detect_contour(db, rdc)
        db.rollback()
        thermique_metre.detect_contour(db, rdc, replace=True)
        assert [zone.source for zone in rdc.zones] == ["automatique"]

        section = thermique_metre.sheet_section(coupe)
        assert section["dessins"][0]["hauteurs_etage_m"] == pytest.approx([2.88, 4.16, 3.84], abs=0.01)
        assert thermique_metre.apply_section_heights(db, projet, coupe, 0, True, 1) == 2
        niveaux = thermique_metre.serialize_metre(db, projet)["niveaux"]
        assert (niveaux[0]["hauteur_etage_m"], niveaux[0]["hauteurs_source"]) == (4.16, "coupe")
        assert niveaux[1]["hauteur_sous_plafond_m"] == pytest.approx(3.68, abs=0.01)
        assert niveaux[0]["synthese"]["hauteur_interieure_m"] == pytest.approx(4.0, abs=0.01)

        thermique_metre.update_level(db, projet, rdc, {"hauteur_sous_plafond_m": 3.9})
        assert rdc.heights_source == "manuel"
        with pytest.raises(ThermiqueError, match="Dessin"):
            thermique_metre.apply_section_heights(db, projet, coupe, 5, True, 0)
