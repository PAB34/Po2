"""Lot M4a : types de murs lus le long du contour (épaisseur, isolant), regroupés et rattachés à la
bibliothèque. Plans fabriqués pour le test. Voir docs/thermique/parois-menuiseries-pt-decisions.md."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import Base
from app.models.thermique import ThermiqueComponent, ThermiqueDocument, ThermiqueSheet
from app.services import thermique_metre
from app.services.thermique import create_project, document_path
from tests.test_thermique_metre import _pdf, _user
from thermique_moteur import enveloppe, traits

M = 1000 / 100 / (25.4 / 72)  # points PDF pour 1 m à 1/100
OX, OY = 60.0, 60.0
EP = 0.30
INTERIEUR = [[OX + EP * M, OY + EP * M], [OX + (10 - EP) * M, OY + EP * M], [OX + (10 - EP) * M, OY + (8 - EP) * M], [OX + EP * M, OY + (8 - EP) * M]]


def _plan_murs_remplis() -> bytes:
    """Mur de 30 cm rempli en gris (maçonnerie), bordé de deux traits épais, sur les quatre façades."""
    e = EP * M
    largeur, hauteur = 10 * M, 8 * M
    bandes = [
        (OX, OY, largeur, e),
        (OX, OY + hauteur - e, largeur, e),
        (OX, OY, e, hauteur),
        (OX + largeur - e, OY, e, hauteur),
    ]
    remplissage = "0.6 g " + " ".join(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re f" for x, y, w, h in bandes)
    faces = "1.5 w " + " ".join(
        f"{x0:.2f} {y0:.2f} {x1 - x0:.2f} {y1 - y0:.2f} re S"
        for x0, y0, x1, y1 in ((OX, OY, OX + largeur, OY + hauteur), (OX + e, OY + e, OX + largeur - e, OY + hauteur - e))
    )
    return _pdf(f"{remplissage} 0 g {faces}".encode()).replace(b"/MediaBox [0 0 600 400]", b"/MediaBox [0 0 600 500]")


def test_epaisseur_des_murs_le_long_du_contour(tmp_path):
    chemin = tmp_path / "plan.pdf"
    chemin.write_bytes(_plan_murs_remplis())
    lus = traits.lire_traits(chemin, 0, avec_couleur=True)
    aplats = traits.lire_aplats(chemin, 0)
    assert len(aplats) == 4 and all(luminance == 153 for _, luminance in aplats)
    analyse = enveloppe.analyser_murs(lus, aplats, INTERIEUR, 1.5, 100)
    assert len(analyse["cotes"]) == 4
    for cote in analyse["cotes"]:
        assert cote["epaisseur_m"] == pytest.approx(EP, abs=0.021)
        assert cote["part_lue"] >= 0.9
    longueurs = [9.4, 7.4, 9.4, 7.4]
    cotes = [{"mur": {k: cote[k] for k in ("epaisseur_m", "isolant", "part_lue")}, "composant_id": None} for cote in analyse["cotes"]]
    types = enveloppe.types_de_murs(cotes, longueurs)
    assert len(types) == 1
    assert sorted(types[0]["cotes"]) == [0, 1, 2, 3]
    assert types[0]["longueur_m"] == pytest.approx(sum(longueurs) * min(c["part_lue"] for c in analyse["cotes"]), rel=0.1)


def test_types_regroupes_a_trois_centimetres():
    cotes = [
        {"mur": {"epaisseur_m": 0.42, "isolant": "reparti", "part_lue": 1.0}},
        {"mur": {"epaisseur_m": 0.44, "isolant": "reparti", "part_lue": 0.5}, "composant_id": 7},
        {"mur": {"epaisseur_m": 0.22, "isolant": None, "part_lue": 1.0}},
        {"mur": {"epaisseur_m": None, "isolant": None, "part_lue": 0.0}},
        {},
    ]
    types = enveloppe.types_de_murs(cotes, [10.0, 4.0, 3.0, 5.0, 2.0])
    assert [(t["epaisseur_m"], t["isolant"], t["longueur_m"], t["cotes"], t["composants"]) for t in types] == [
        (0.42, "reparti", 12.0, [0, 1], [7]),  # moyenne pondérée par la longueur lue : 0,423
        (0.22, None, 3.0, [2], []),
    ]


def test_lecture_et_rattachement_des_murs_dans_le_projet(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "thermique_storage_dir", str(tmp_path))
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        thermicien = _user(db, "be@example.fr")
        projet = create_project(db, thermicien, "Projet", None)
        contenu = _plan_murs_remplis()
        document = ThermiqueDocument(
            project_id=projet.id, original_filename="plan.pdf", stored_filename="plan.pdf", file_format="pdf",
            size_bytes=len(contenu), sha256="a" * 64, page_count=1,
        )
        db.add(document)
        db.flush()
        document_path(document).parent.mkdir(parents=True, exist_ok=True)
        document_path(document).write_bytes(contenu)
        planche = ThermiqueSheet(
            project_id=projet.id, document_id=document.id, page_index=0, label="Plan", nature="plan",
            rotation_deg=0, page_width_pt=600, page_height_pt=500, scale_denominator=100, scale_source="declaree",
        )
        db.add(planche)
        db.commit()
        niveau = thermique_metre.create_level(db, projet, {"nom": "RDC", "planche_id": planche.id})
        zone = thermique_metre.create_zone(db, niveau, {"type": "contour", "points": INTERIEUR})

        resultat = thermique_metre.detect_walls(db, zone)
        assert (resultat["cotes_lues"], resultat["cotes"], resultat["types"]) == (4, 4, 1)
        cotes = json.loads(zone.edges_json)
        assert all(cote["mur"]["epaisseur_m"] == pytest.approx(EP, abs=0.021) for cote in cotes)

        # Changer le « donne sur » d'un côté conserve le mur lu.
        cotes[1]["donne_sur"] = "lnc"
        thermique_metre.update_zone(db, zone, {"cotes": cotes})
        assert json.loads(zone.edges_json)[1]["mur"]["epaisseur_m"] == pytest.approx(EP, abs=0.021)

        type_mur = thermique_metre.serialize_metre(db, projet)["niveaux"][0]["zones"][0]["types_murs"][0]
        composant_id = thermique_metre.accept_wall_type(db, thermicien, zone, type_mur["epaisseur_m"], None)
        composant = db.get(ThermiqueComponent, composant_id)
        assert (composant.category, composant.project_id) == ("murs", projet.id)
        assert composant.name.startswith("Mur 30 cm")
        assert {cote["composant_id"] for cote in json.loads(zone.edges_json)} == {composant_id}
        assert thermique_metre.serialize_metre(db, projet)["niveaux"][0]["zones"][0]["types_murs"][0]["composants"] == [composant_id]
