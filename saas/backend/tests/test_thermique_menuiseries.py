"""Baies et hauteur des menuiseries lue en élévation (S5e : D193, D194, D196 à D200).

Séquences reprises du relevé réel du R+1 (projet 1) : menuiserie coupée à la jonction T04/T05, modules de
mur-rideau entre poteaux, tranche de M3 en bout de tronçon.
"""
from __future__ import annotations

import json

import pytest

from app.services import thermique_coupes as coupes
from app.services import thermique_menuiseries as men
from app.services.thermique import ThermiqueError


def _m(troncon, debut, fin, composant, type_menuiserie="fenêtre", **reste):
    return {"troncon": troncon, "debut_m": debut, "fin_m": fin, "type": "menuiserie", "composant": composant,
            "menuiserie_type": type_menuiserie, **reste}


def _e(troncon, debut, fin, type_):
    return {"troncon": troncon, "debut_m": debut, "fin_m": fin, "type": type_}


RELEVE = [
    # T04 → T05 : une même baie coupée à la jonction des tronçons (17,26 m), rien entre les deux.
    _m("T04", 13.55, 16.57, "M1", "mur-rideau"),
    _e("T04", 16.57, 16.65, "about_refend"),
    _m("T04", 16.65, 17.26, "M1", "mur-rideau"),
    _m("T05", 17.26, 19.66, "M1", "mur-rideau"),
    # Modules de mur-rideau entre poteaux : des baies distinctes.
    _e("T09", 35.33, 35.62, "poteau"),
    _m("T09", 35.62, 37.39, "M1", "mur-rideau"),
    _e("T09", 37.39, 37.68, "poteau"),
    # M4 de largeurs différentes, et une tranche de M3 de 8 cm en bout de tronçon.
    _m("T22", 77.15, 79.86, "M4"),
    _e("T22", 79.86, 80.14, "angle_sortant"),
    _m("T23", 80.14, 83.66, "M4"),
    _e("T50", 129.13, 130.68, "paroi"),
    _m("T50", 130.68, 130.76, "M3"),
    # Deux menuiseries de composants différents qui se touchent restent deux baies.
    _m("T11", 43.94, 44.88, "M2"),
    _m("T11", 44.88, 45.63, "M1", "mur-rideau"),
    # Une menuiserie écartée par le thermicien ne compte pas.
    _m("T30", 90.0, 91.0, "M4", exclu=True),
]


def test_les_morceaux_d_une_meme_baie_se_rejoignent_meme_d_un_troncon_a_l_autre():
    baies = men.baies_du_releve(RELEVE)
    largeurs = [(b["composant"], b["largeur_cm"]) for b in baies]
    assert largeurs == [
        ("M1", 302.0), ("M1", 301.0), ("M1", 177.0), ("M2", 94.0), ("M1", 75.0),
        ("M4", 271.0), ("M4", 352.0), ("M3", 8.0),
    ]
    jointe = baies[1]
    assert [m["troncon"] for m in jointe["morceaux"]] == ["T04", "T05"]
    assert [b["morceau_a_verifier"] for b in baies] == [False] * 7 + [True]


def test_mesure_de_deux_coins_sur_une_elevation_tournee():
    vue = type("Vue", (), {"lecture_json": json.dumps({"haut": [1, 0]})})()
    m = coupes.metres_par_point(100)
    largeur, hauteur = men.mesurer(vue, 100, [1000.0, 1500.0], [1000.0 + 1.35 / m, 1500.0 - 1.20 / m])
    assert largeur == pytest.approx(1.20) and hauteur == pytest.approx(1.35)


def test_proposition_par_largeur_a_cinq_centimetres():
    composants = [
        {"composant": "M4", "baies": [{"largeur_cm": 271.0}, {"largeur_cm": 352.0}]},
        {"composant": "M3", "baies": [{"largeur_cm": 83.0}]},
        {"composant": "M5", "baies": [{"largeur_cm": 268.0}]},
    ]
    assert men.proposer(composants, 269.5) == [
        {"composant": "M4", "ecart_cm": 1.5}, {"composant": "M5", "ecart_cm": 1.5},
    ]
    assert men.proposer(composants, 120) == []


@pytest.fixture()
def db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.core.db import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _projet(db):
    from app.core.security import get_password_hash
    from app.models.thermique import ThermiqueDocument, ThermiqueEtude, ThermiqueProject, ThermiqueSheet, ThermiqueVue
    from app.models.user import User

    user = User(email="t@b.fr", password_hash=get_password_hash("motdepasse-solide"), nom="N", prenom="P", role="USER", is_active=True)
    db.add(user)
    db.flush()
    projet = ThermiqueProject(owner_user_id=user.id, name="Médiathèque")
    db.add(projet)
    db.flush()
    document = ThermiqueDocument(project_id=projet.id, original_filename="p.pdf", stored_filename="p.pdf",
                                 file_format="pdf", size_bytes=1, sha256="x" * 64, page_count=2)
    db.add(document)
    db.flush()
    feuilles = []
    for page, nature in ((0, "plan"), (1, "facade")):
        sheet = ThermiqueSheet(project_id=projet.id, document_id=document.id, page_index=page, label=nature, nature=nature,
                               level_label="R+1" if nature == "plan" else None, scale_denominator=100,
                               rotation_deg=0, page_width_pt=1684, page_height_pt=2384)
        db.add(sheet)
        db.flush()
        feuilles.append(sheet)
    contenu = {"enveloppe": {"releve_brut": {"elements": RELEVE}}}
    db.add(ThermiqueEtude(project_id=projet.id, sheet_id=feuilles[0].id, format_version=3,
                          content_json=json.dumps(contenu), local_states_json="{}"))
    vue = ThermiqueVue(project_id=projet.id, sheet_id=feuilles[1].id, nom="FACADE EST", nature="facade",
                       cadre_json="[0,0,1,1]", lecture_json=json.dumps({"haut": [1, 0], "niveaux": [], "pieces": []}))
    db.add(vue)
    db.commit()
    return projet, vue


def _coins(largeur_m, hauteur_m):
    m = coupes.metres_par_point(100)
    # Élévation tournée : le haut est +x, la droite −y.
    return [[1000.0, 1500.0], [1000.0 + hauteur_m / m, 1500.0 - largeur_m / m]]


def test_une_hauteur_confirmee_vaut_pour_tout_le_composant_puis_une_baie_se_corrige(db_session):
    projet, vue = _projet(db_session)
    avant = men.menuiseries_du_projet(db_session, projet.id)
    m4 = next(f for f in avant["composants"] if f["composant"] == "M4")
    assert m4["a_lire"] == 2 and m4["hauteur_m"] is None
    assert [b["source"] for b in next(f for f in avant["composants"] if f["composant"] == "M1")["baies"]] == ["hauteur_du_local"] * 4
    assert [(p["composant"], p["largeur_cm"]) for p in avant["morceaux_a_verifier"]] == [("M3", 8.0)]

    # Deux coins sur la baie M4 de 2,71 m : 2,15 m pour tout le composant, sur tous les niveaux (D200).
    men.confirmer(db_session, vue, _coins(2.72, 2.15), "M4", None, "2026-09-29T10:00:00")
    apres = next(f for f in men.menuiseries_du_projet(db_session, projet.id)["composants"] if f["composant"] == "M4")
    assert apres["hauteur_m"] == pytest.approx(2.15)
    assert [(b["hauteur_m"], b["source"]) for b in apres["baies"]] == [(pytest.approx(2.15), "composant")] * 2

    # La baie de 3,52 m est plus haute : sa hauteur propre l'emporte, l'autre garde celle du composant.
    men.confirmer(db_session, vue, _coins(3.50, 2.40), "M4", 352.0, "2026-09-29T10:05:00")
    apres = next(f for f in men.menuiseries_du_projet(db_session, projet.id)["composants"] if f["composant"] == "M4")
    assert [(b["largeur_cm"], b["hauteur_m"], b["source"]) for b in apres["baies"]] == [
        (271.0, pytest.approx(2.15), "composant"), (352.0, pytest.approx(2.40), "baie"),
    ]

    men.retirer(db_session, vue, "M4")
    apres = next(f for f in men.menuiseries_du_projet(db_session, projet.id)["composants"] if f["composant"] == "M4")
    assert apres["a_lire"] == 2


def test_une_menuiserie_de_mauvaise_largeur_est_refusee(db_session):
    projet, vue = _projet(db_session)
    with pytest.raises(ThermiqueError, match="pas la même menuiserie"):
        men.confirmer(db_session, vue, _coins(1.20, 2.15), "M4", None, "t")
    with pytest.raises(ThermiqueError, match="deux coins opposés"):
        men.confirmer(db_session, vue, _coins(2.71, 0.05), "M4", None, "t")
    with pytest.raises(ThermiqueError, match="Aucune baie"):
        men.confirmer(db_session, vue, _coins(2.71, 2.15), "M9", None, "t")
