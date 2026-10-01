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


def test_un_modele_mesure_et_pose_donne_sa_largeur_et_sa_hauteur_a_la_baie(db_session, tmp_path, monkeypatch):
    """D219 à D222 (test du 2026-10-01) : le nom « M4 » de l'IA couvre deux largeurs ; le thermicien mesure
    un modèle, le pose sur une menuiserie, et la baie hérite de ses dimensions. La capture est gardée."""
    import pypdfium2 as pdfium

    from app.core.config import settings
    from app.models.thermique import ThermiqueEtude
    from app.services import thermique_elements as elements

    monkeypatch.setattr(settings, "thermique_storage_dir", str(tmp_path))
    document = pdfium.PdfDocument.new()
    for _ in range(2):
        document.new_page(1684, 2384)
    pdf = tmp_path / "planches.pdf"
    document.save(str(pdf))
    projet, vue = _projet(db_session)

    with pytest.raises(ThermiqueError, match="en diagonale"):
        men.enregistrer_modele(db_session, vue, _coins(0.02, 1.83), "M4 2", "t", pdf)
    modele = men.enregistrer_modele(db_session, vue, _coins(1.20, 2.15), "M4 120x215", "2026-10-01T10:00:00", pdf)
    assert modele["largeur_mesuree_cm"] == pytest.approx(120) and modele["capture"]
    assert men.capture_du_modele(db_session, projet.id, "M4 120x215").is_file()

    # Le modèle se pose sur la baie M4 de 3,52 m (T23) : elle n'est plus réunie à rien et hérite du modèle.
    etude = db_session.query(ThermiqueEtude).one()
    contenu = json.loads(etude.content_json)
    cible = next(e for e in contenu["enveloppe"]["releve_brut"]["elements"] if e["troncon"] == "T23")
    elements.corriger(contenu, elements.reference(cible), {"modele": "M4 120x215"})
    etude.content_json = json.dumps(contenu)
    db_session.commit()

    projet_men = men.menuiseries_du_projet(db_session, projet.id)
    m4 = next(f for f in projet_men["composants"] if f["composant"] == "M4")
    posee = next(b for b in m4["baies"] if b.get("modele"))
    assert posee["source"] == "modele" and posee["largeur_retenue_cm"] == pytest.approx(120)
    assert posee["hauteur_m"] == pytest.approx(2.15) and posee["surface_m2"] == pytest.approx(2.58)
    assert posee["ecart_modele_cm"] == pytest.approx(232, abs=0.5)
    autre = next(b for b in m4["baies"] if not b.get("modele"))
    assert autre["source"] == "a_lire" and autre["largeur_retenue_cm"] == 271.0
    assert [(m["nom"], m["poses"], m["capture"]) for m in projet_men["modeles"]] == [("M4 120x215", 1, True)]

    # Une seconde mesure du même nom remplace la première ; retirer le modèle le sort de la bibliothèque.
    men.enregistrer_modele(db_session, vue, _coins(1.25, 2.20), "M4 120x215", "2026-10-01T11:00:00")
    assert men.menuiseries_du_projet(db_session, projet.id)["modeles"][0]["largeur_cm"] == pytest.approx(125)
    men.retirer_modele(db_session, projet.id, "M4 120x215")
    assert men.menuiseries_du_projet(db_session, projet.id)["modeles"] == []

    with pytest.raises(ThermiqueError, match="Seule une menuiserie"):
        elements.corriger(contenu, elements.reference(RELEVE[1]), {"modele": "X"})


def test_les_morceaux_d_une_menuiserie_sont_reunis_dans_le_releve():
    """D223 (2026-10-01) : réunion physique à 6 cm, même composant et même modèle, indéterminé absorbé."""
    from app.services import thermique_elements as elements

    releve = {"elements": [
        _m("T01", 1.00, 1.60, "M1", confirme=True, a_verifier=False),
        _e("T01", 1.61, 1.64, "indetermine"),
        _m("T01", 1.65, 2.20, "M1", confirme=True, a_verifier=False, modele=None),
        _m("T01", 2.24, 2.80, "M1", a_verifier=True),           # 4 cm : réunie aussi
        _m("T01", 2.90, 3.40, "M1"),                            # 10 cm : un trumeau, reste à part
        _m("T01", 3.42, 3.90, "M2"),                            # autre composant : jamais d'office
        _m("T02", 0.00, 0.50, "M1", modele="A"),
        _m("T02", 0.52, 1.00, "M1", modele="B"),                # autre modèle : reste à part
        _m("T03", 0.00, 0.50, "M1"),
        _e("T03", 0.50, 0.55, "about_refend"),                  # un pont sépare
        _m("T03", 0.55, 1.00, "M1"),
    ]}
    assert elements.reunir_menuiseries(releve) == 2
    t01 = [e for e in releve["elements"] if e["troncon"] == "T01"]
    reunie = t01[0]
    assert (reunie["debut_m"], reunie["fin_m"]) == (1.00, 2.80)
    assert [m["debut_m"] for m in reunie["morceaux_reunis"]] == [1.00, 1.65, 2.24]
    assert reunie["confirme"] is False and reunie["a_verifier"] is True
    assert t01[1]["exclu"] and "D223" in t01[1]["motif_exclusion"]
    assert [(e["debut_m"], e["composant"]) for e in t01[2:]] == [(2.90, "M1"), (3.42, "M2")]
    assert len([e for e in releve["elements"] if e["troncon"] in ("T02", "T03") and e["type"] == "menuiserie"]) == 4
    assert elements.reunir_menuiseries(releve) == 0


def test_les_parois_se_reunissent_aussi_et_la_composition_se_copie():
    """D238 : réunion des parois à 6 cm ; D239 : les couches d'une paroi de référence se copient."""
    import pytest

    from app.services import thermique_elements as elements

    couches = [{"nature": "mur", "epaisseur_cm": 20, "indice": ""}, {"nature": "isolant", "epaisseur_cm": 12, "indice": ""}]
    releve = {"elements": [
        {**_e("T01", 0.0, 2.0, "paroi"), "composant": "P1"},
        {**_e("T01", 2.04, 4.0, "paroi"), "composant": "P1"},
        {**_e("T01", 4.0, 5.0, "paroi"), "composant": "P2"},
    ]}
    assert elements.reunir_menuiseries(releve) == 1
    assert [(e["debut_m"], e["fin_m"], e["composant"]) for e in releve["elements"]] == [(0.0, 4.0, "P1"), (4.0, 5.0, "P2")]

    contenu = {"enveloppe": {"releve_brut": releve}}
    cible = releve["elements"][1]
    elements.corriger(contenu, elements.reference(cible), {"composant": "P1", "couches": couches, "nu_exterieur_cm": 44})
    assert cible["couches"][1]["epaisseur_cm"] == 12.0 and cible["composant"] == "P1"
    with pytest.raises(ThermiqueError, match="épaisseur"):
        elements.corriger(contenu, elements.reference(cible), {"couches": [{"nature": "mur", "epaisseur_cm": 0}]})


def test_un_mur_retrace_remplace_les_morceaux_et_garde_menuiseries_et_angles():
    """D240, D241 : sur T01 puis T02, les morceaux bizarres sont écartés, une paroi propre par tronçon,
    la menuiserie et l'angle restent, un morceau qui dépasse est rogné."""
    import pytest

    from app.services.thermique_etude_edition import MOTIF_RETRACE, retracer_paroi

    manifeste = {"troncons": [{"id": "T01", "debut_m": 0.0, "fin_m": 5.0}, {"id": "T02", "debut_m": 5.0, "fin_m": 9.0}]}
    releve = {"elements": [
        {**_e("T01", 0.0, 1.5, "paroi"), "composant": "P9"},            # dépasse le début : rogné
        _e("T01", 1.8, 2.2, "indetermine"),                              # morceau bizarre : écarté
        {**_e("T01", 2.2, 3.0, "paroi"), "composant": "P9"},            # écarté
        _m("T01", 3.0, 4.2, "M1"),                                       # gardée
        _e("T01", 5.0, 5.0, "angle_sortant"),                            # pont : gardé
        {**_e("T02", 5.0, 9.0, "paroi"), "composant": "P9"},            # dépasse la fin : rogné
    ]}
    modele = {"composant": "P1", "couches": [{"nature": "mur", "epaisseur_cm": 20}], "nu_exterieur_cm": 44, "nu_interieur_cm": 0}
    with pytest.raises(ThermiqueError, match="Copiez"):
        retracer_paroi(releve, manifeste, {"debut_m": 1, "fin_m": 7})
    nouveaux = retracer_paroi(releve, manifeste, {"debut_m": 7.0, "fin_m": 1.0, "modele": modele})

    assert [(n["troncon"], n["debut_m"], n["fin_m"]) for n in nouveaux] == [("T01", 1.0, 3.0), ("T01", 4.2, 5.0), ("T02", 5.0, 7.0)]
    assert all(n["composant"] == "P1" and n["retrace"] and n["confirme"] for n in nouveaux)
    par_bornes = {(e["troncon"], e["debut_m"]): e for e in releve["elements"] if not e.get("retrace")}
    assert par_bornes[("T01", 0.0)]["fin_m"] == 1.0 and not par_bornes[("T01", 0.0)].get("exclu")
    assert par_bornes[("T01", 1.8)]["motif_exclusion"] == MOTIF_RETRACE
    assert par_bornes[("T01", 2.2)]["exclu"]
    assert not par_bornes[("T01", 3.0)].get("exclu") and not par_bornes[("T01", 5.0)].get("exclu")
    assert par_bornes[("T02", 7.0)]["fin_m"] == 9.0  # rogné : il commence où finit le mur retracé


def test_le_mur_retrace_passe_la_porte_d_entree_du_serveur():
    """Erreur 422 du 2026-10-01 : le geste n'était pas déclaré dans le schéma des opérations. On le fait passer
    par le même chemin que le site : schéma, puis `model_dump(exclude_none=True)`, puis le calcul."""
    from app.schemas.thermique import EtudeEnregistrement
    from app.services.thermique_etude_edition import retracer_paroi

    corps = {
        "operations": [
            {"type": "paroi_retracer", "debut_m": 1.0, "fin_m": 3.0,
             "modele": {"composant": "P1", "couches": [{"nature": "mur", "epaisseur_cm": 20}], "nu_exterieur_cm": 44,
                        "nu_interieur_cm": 0, "libelle": "P1 · 44 cm"}},
            {"type": "element_corriger", "element": {"troncon": "T01", "debut_m": 0.0, "fin_m": 1.0},
             "changes": {"composant": "P1", "couches": [{"nature": "mur", "epaisseur_cm": 20}], "nu_exterieur_cm": 44}},
        ],
        "motif": "mur_retrace",
        "valider": False,
    }
    gestes = [op.model_dump(exclude_none=True) for op in EtudeEnregistrement.model_validate(corps).operations]
    assert gestes[0]["debut_m"] == 1.0 and gestes[0]["modele"]["composant"] == "P1"
    assert gestes[1]["changes"]["couches"][0]["epaisseur_cm"] == 20
    releve = {"elements": [{**_e("T01", 0.0, 4.0, "paroi"), "composant": "P9"}]}
    nouveaux = retracer_paroi(releve, {"troncons": [{"id": "T01", "debut_m": 0.0, "fin_m": 4.0}]}, gestes[0])
    assert [(n["debut_m"], n["fin_m"]) for n in nouveaux] == [(1.0, 3.0)]


def test_l_exposition_d_une_menuiserie_suit_le_nord():
    """D225 : normale sortante du tronçon (repère image) par rapport au nord ; sans nord, « à caler »."""
    from app.services.thermique_etude_edition import exposer_menuiseries

    manifeste = {"troncons": [{"id": "T01", "normale_ext": [0.0, 1.0]}, {"id": "T02", "normale_ext": [1.0, 0.0]}]}
    releve = {"elements": [_m("T01", 0, 1, "M1"), _m("T02", 0, 1, "M1"), _e("T01", 1, 2, "paroi")]}
    exposer_menuiseries(releve, manifeste, 0.0)
    assert [(e.get("exposition"), e.get("azimut_deg")) for e in releve["elements"]] == [("S", 180), ("E", 90), (None, None)]
    exposer_menuiseries(releve, manifeste, 90.0)  # le nord pointe à droite de la feuille : l'est est en bas
    assert [e["exposition"] for e in releve["elements"][:2]] == ["E", "N"]
    exposer_menuiseries(releve, manifeste, None)
    assert releve["elements"][0]["exposition"] == "nord à caler" and releve["elements"][0]["azimut_deg"] is None


def test_une_menuiserie_de_mauvaise_largeur_est_refusee(db_session):
    projet, vue = _projet(db_session)
    with pytest.raises(ThermiqueError, match="pas la même menuiserie"):
        men.confirmer(db_session, vue, _coins(1.20, 2.15), "M4", None, "t")
    with pytest.raises(ThermiqueError, match="deux coins opposés"):
        men.confirmer(db_session, vue, _coins(2.71, 0.05), "M4", None, "t")
    with pytest.raises(ThermiqueError, match="Aucune baie"):
        men.confirmer(db_session, vue, _coins(2.71, 2.15), "M9", None, "t")
