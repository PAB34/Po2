"""Coupes : rattachement des pièces aux locaux du plan et hauteur par local (S5c, S5d, D178 à D185).

Données réelles du projet 1 (Frontignan, R+1, 1/100) : contours des locaux de l'étude, traits de coupe et
bornes des pièces relevés à l'œil (`docs/thermique/verite-terrain-coupes.md`).
"""
import pytest

from app.services import thermique_coupes as coupes

LOCAUX = [
    {"id": i, "nom": n, "contour_pdf": c}
    for i, n, c in [
        ("piece-001", "6.1.1 B.dir + EAPMR", [[1235.7, 1784.5], [1221.3, 1784.5], [1200.7, 1775.9], [1190.1, 1768.7], [1154.6, 1767.7], [1154.1, 1770.6], [1106.6, 1770.6], [1121.0, 1777.3], [1119.6, 1777.8], [1095.8, 1767.8], [1095.8, 1653.0], [1142.1, 1652.5], [1142.6, 1664.5], [1146.0, 1670.8], [1145.0, 1677.0], [1154.6, 1678.0], [1142.1, 1678.5], [1142.1, 1679.9], [1234.8, 1679.9]]),
        ("piece-002", "6.1.2 B.asst (1)", [[1241.5, 1675.6], [1146.0, 1675.6], [1146.0, 1592.1], [1241.5, 1592.1]]),
        ("piece-003", "6.1.2 B.asst (2)", [[1241.5, 1504.7], [1241.5, 1588.2], [1146.0, 1587.7], [1146.0, 1504.7]]),
        ("piece-004", "6.1.2 B.asst (3)", [[1241.5, 1500.4], [1146.0, 1500.4], [1146.4, 1416.9], [1241.5, 1416.9]]),
        ("piece-005", "6.1.2 B.asst (4)", [[1241.5, 1329.5], [1241.5, 1413.0], [1146.4, 1413.0], [1146.0, 1329.5]]),
        ("piece-006", "6.1.2 B.asst (5)", [[1241.5, 1325.2], [1146.0, 1325.2], [1146.0, 1241.7], [1241.5, 1241.7]]),
        ("piece-007", "6.1.2 B.asst (6)", [[1241.0, 1237.8], [1146.4, 1237.8], [1146.4, 1147.1], [1218.9, 1147.1], [1218.9, 1152.9], [1241.5, 1152.9]]),
        ("piece-008", "6.1 conservation et administration (circulation)", [[1142.1, 1648.7], [1104.2, 1648.7], [1103.2, 1639.6], [1104.2, 1352.6], [1103.2, 1205.7], [1099.9, 1195.6], [1102.3, 1194.6], [1101.3, 1187.9], [1068.7, 1185.5], [873.3, 1186.0], [873.3, 1147.1], [1142.1, 1147.1], [1142.6, 1637.7]]),
        ("piece-009", "6.1.3 equipement", [[1218.9, 1143.3], [1101.3, 1143.3], [1101.3, 952.3], [1219.4, 952.3]]),
        ("piece-019", "4.2.4 et 4.3.5 espace formation", [[879.1, 1784.0], [838.3, 1784.5], [819.1, 1775.9], [811.4, 1769.6], [801.8, 1767.7], [776.4, 1767.7], [775.9, 1771.1], [754.3, 1769.6], [753.8, 1781.6], [769.2, 1789.3], [750.0, 1781.2], [750.0, 1474.0], [863.7, 1474.0], [863.7, 1769.2], [865.6, 1761.0], [866.1, 1771.6]]),
        ("piece-020", "4.3.4 et 4.5.2 lecture confort", [[863.7, 1121.7], [750.0, 1121.7], [750.0, 952.3], [859.4, 951.8], [863.7, 952.3]]),
        ("piece-021", "escalier atrium", [[857.0, 1415.0], [818.6, 1415.0], [818.6, 1190.8], [858.0, 1190.8]]),
    ]
]
NIVEAUX = [
    {"nom": "H00", "cote_m": 0.0}, {"nom": "H01", "cote_m": 3.20}, {"nom": "H10", "cote_m": 4.16},
    {"nom": "H11", "cote_m": 7.04}, {"nom": "H20", "cote_m": 8.00}, {"nom": "H21", "cote_m": 10.88},
]
TRAIT_A = {"nom": "A", "points": [[1144.5, 763.0], [1144.5, 1906.0]], "sens": [-1, 0]}
TRAIT_C = {"nom": "C", "points": [[824.0, 763.0], [824.0, 1906.0]], "sens": [1, 0]}
TRAIT_D = {"nom": "D", "points": [[1453.0, 905.75], [249.5, 905.75]], "sens": [0, 1]}


def _p(nom, y0, y1, sol, plafond, **k):
    # PC10 et PC11 : la coupe est tournée, son haut est le +x de la page, donc sa droite est le −y.
    return {"nom": nom, "debut": -y1, "fin": -y0, "sol": sol, "plafond": plafond, **k}


VUE_A = {
    "nom": "A", "haut": [1, 0], "niveaux": NIVEAUX,
    "pieces": [
        _p("6.1.1 Bureau direction", 1071.6, 1167.8, "H10", "H11"),
        _p("6.1.2 - Bur.1", 1170.5, 1255.7, "H10", "H11"),
        _p("6.1.2 - Bur.2", 1255.7, 1343.7, "H10", "H11"),
        _p("6.1.2 - Bur.3", 1343.7, 1431.6, "H10", "H11"),
        _p("6.1.2 - Bur.4", 1431.6, 1519.5, "H10", "H11"),
        _p("6.1.2 - Bur.5", 1519.5, 1602.0, "H10", "H11"),
        _p("6.1.2 - Bur.6", 1602.0, 1698.2, "H10", "H11"),
        _p("6.1.3 - Salle d'équipement", 1698.2, 1901.6, "H10", "H11"),
        _p("coursive", 1901.6, 1985.0, "H10", None, exterieur=True),
        _p("5.2.7 - Salle de groupe", 1082.6, 1200.7, "H20", "H21"),
        _p("5.2 - Recherche Documentations", 1200.7, 1665.2, "H20", "H21"),
        _p("2.2.4 - Salle de rencontres", 1577.3, 1989.5, "H00", "H01"),
    ],
}
ATTENDU_A = ["piece-001", *(f"piece-00{i}" for i in range(2, 8)), "piece-009", None]

VUE_C = {
    "nom": "C", "haut": [1, 0], "niveaux": NIVEAUX,
    "pieces": [
        _p("4.2.4 Espace de formation", 1623.9, 1936.4, "H10", "H11"),
        _p(None, 1339.1, 1562.8, "H00", "H21"),
        _p("4.3.4 Jeux vidéo", 1105.2, 1339.1, "H10", "H11"),
        _p("4.1 Kiosque presse adulte", 1562.8, 1936.4, "H00", "H01"),
    ],
}


def test_numero_programme_est_la_cle_des_noms_abreges():
    assert coupes.numero_programme("6.1.2 B.asst (3)") == "6.1.2"
    assert coupes.numero_programme("4.3.4 Jeux vidéo") == "4.3.4"
    assert coupes.numero_programme("4.3.4 et 4.5.2 lecture confort") == "4.3.4"
    assert coupes.numero_programme("escalier atrium") is None
    assert coupes.numero_programme("Bureau (5)") is None


def test_le_trait_dans_le_mur_ne_croise_que_deux_locaux():
    """Coupe A : le trait passe entre la circulation et les bureaux, à 5-7 cm de chacun."""
    plan = coupes.traversees_du_plan(TRAIT_A, LOCAUX, 100)
    assert {t["local"] for t in plan if t["direct"]} == {"piece-001", "piece-009"}
    frolees = {t["local"]: t["distance_m"] for t in plan if not t["direct"]}
    assert set(frolees) >= {"piece-002", "piece-007", "piece-008"}
    assert all(d < coupes.TOLERANCE_TRAIT_M for d in frolees.values())


def test_coupe_a_huit_locaux_sur_huit_au_bon_etage():
    r = coupes.rattacher(TRAIT_A, 100, LOCAUX, VUE_A, 100)
    assert r["etage_sol_m"] == pytest.approx(4.16)
    assert r["calage"] == "noms"
    assert [l["local"] for l in r["lignes"]] == ATTENDU_A
    assert [l["hsp_m"] for l in r["lignes"][:8]] == [2.88] * 8
    assert r["lignes"][-1]["par"] == "extérieur"
    assert r["alertes"] == []


def test_un_sens_du_regard_mal_lu_est_retourne_par_la_coupe():
    """Essai de l'agent (2026-09-29) : un drapeau lu du mauvais côté. La coupe tranche, et le dit."""
    retourne = {**TRAIT_A, "sens": [1, 0]}
    r = coupes.rattacher(retourne, 100, LOCAUX, VUE_A, 100)
    assert r["sens_retourne"] is True
    assert [l["local"] for l in r["lignes"]] == ATTENDU_A
    assert "sens retourné" in r["alertes"][0]
    assert coupes.rattacher(TRAIT_A, 100, LOCAUX, VUE_A, 100)["sens_retourne"] is False


def test_coupe_a_sans_les_noms_le_recouvrement_suffit():
    anonyme = {**VUE_A, "pieces": [{**p, "nom": None} for p in VUE_A["pieces"]]}
    r = coupes.rattacher(TRAIT_A, 100, LOCAUX, anonyme, 100)
    assert r["calage"] == "recouvrement"
    assert [l["local"] for l in r["lignes"]] == ATTENDU_A


def test_coupe_c_signale_la_double_hauteur_sans_l_inventer():
    r = coupes.rattacher(TRAIT_C, 100, LOCAUX, VUE_C, 100)
    assert r["etage_sol_m"] == pytest.approx(4.16)
    par_local = {l["local"]: l for l in r["lignes"] if l["local"]}
    assert par_local["piece-019"]["hsp_m"] == 2.88
    assert par_local["piece-020"]["hsp_m"] == 2.88
    assert par_local["piece-021"]["double_hauteur"] is True
    assert par_local["piece-021"]["hsp_m"] is None
    hauteurs = coupes.hauteurs_des_locaux(LOCAUX, {"C": r})
    assert hauteurs["piece-021"]["source"] == "double_hauteur"
    assert hauteurs["piece-021"]["hauteur_m"] is None


def test_coupe_qui_ne_traverse_aucun_local():
    vue_d = {"nom": "D", "haut": [1, 0], "niveaux": NIVEAUX, "pieces": [_p("coursive", 100, 900, "H10", None, exterieur=True)]}
    r = coupes.rattacher(TRAIT_D, 100, LOCAUX, vue_d, 100)
    assert r["lignes"] == []
    assert r["alertes"]


def test_hauteurs_lue_moyenne_et_deduite():
    """D179 : un local non traversé prend la hauteur la plus fréquente du niveau ; D180 : deux lectures
    différentes donnent la moyenne pondérée par la longueur traversée, signalée."""
    a = coupes.rattacher(TRAIT_A, 100, LOCAUX, VUE_A, 100)
    autre = {
        "lignes": [
            {"local": "piece-009", "hsp_m": 2.70, "longueur_m": 2.0, "double_hauteur": False},
        ]
    }
    h = coupes.hauteurs_des_locaux(LOCAUX, {"A": a, "B": autre})
    assert h["piece-002"] == {
        "hauteur_m": 2.88, "source": "lue",
        "lectures": [{"vue": "A", "hsp_m": 2.88, "longueur_m": pytest.approx(3.006, abs=0.01)}],
        "alerte": None,
    }
    moyenne = h["piece-009"]
    assert moyenne["source"] == "moyenne"
    longueur_a = moyenne["lectures"][0]["longueur_m"]
    assert moyenne["hauteur_m"] == round((2.88 * longueur_a + 2.70 * 2.0) / (longueur_a + 2.0), 2)
    assert moyenne["alerte"]
    assert h["piece-008"] == {"hauteur_m": 2.88, "source": "deduite", "lectures": [], "alerte": None}


def test_sol_et_plafond_mesures_sont_cales_sur_les_lignes_de_niveau():
    vue = {
        "nom": "X", "haut": [0, 1],
        "niveaux": [{"nom": "N0", "cote_m": 10.0, "position": 500.0}],
        "pieces": [{"nom": "1.1 Salle", "debut": 0, "fin": 100, "sol": 500.0, "plafond": 500.0 + 2.5 / coupes.metres_par_point(50)}],
    }
    [piece] = coupes.pieces_de_la_vue(vue, 50)
    assert piece["sol_m"] == pytest.approx(10.0)
    assert piece["plafond_m"] - piece["sol_m"] == pytest.approx(2.5)


@pytest.mark.parametrize(
    ("trait", "vue", "meme"),
    [("A", "COUPE A", True), ("C", "CC", True), ("C", "Coupe C-C", True), ("A", "AA", True),
     ("A", "B", False), ("A", "Zoom sur menuiserie coupe BB", False), ("1", "11", True)],
)
def test_un_trait_retrouve_sa_vue_par_le_nom(trait, vue, meme):
    from app.services import thermique_lecture_coupes as lecture

    assert lecture.meme_coupe(trait, vue) is meme


@pytest.fixture()
def db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.core.db import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _projet_avec_coupe(db):
    import json

    from app.core.security import get_password_hash
    from app.models.thermique import ThermiqueDocument, ThermiqueEtude, ThermiqueProject, ThermiqueSheet
    from app.models.user import User

    user = User(email="t@b.fr", password_hash=get_password_hash("motdepasse-solide"), nom="N", prenom="P", role="USER", is_active=True)
    db.add(user)
    db.flush()
    projet = ThermiqueProject(owner_user_id=user.id, name="Médiathèque")
    db.add(projet)
    db.flush()
    document = ThermiqueDocument(project_id=projet.id, original_filename="p.pdf", stored_filename="p.pdf", file_format="pdf", size_bytes=1, sha256="x" * 64, page_count=2)
    db.add(document)
    db.flush()

    def planche(page, nature):
        sheet = ThermiqueSheet(project_id=projet.id, document_id=document.id, page_index=page, label=nature, nature=nature,
                               level_label="R+1" if nature == "plan" else None, scale_denominator=100, rotation_deg=0,
                               page_width_pt=1684, page_height_pt=2384)
        db.add(sheet)
        db.flush()
        return sheet

    plan, coupe = planche(0, "plan"), planche(1, "coupe")
    contenu = {"locaux": [{**l, "nature": "chauffe"} for l in LOCAUX]}
    contenu["locaux"][7]["hauteur_m"] = 2.65  # piece-008 : saisie par le thermicien
    db.add(ThermiqueEtude(project_id=projet.id, sheet_id=plan.id, format_version=3, content_json=json.dumps(contenu), local_states_json="{}"))
    db.commit()
    return plan, coupe


def test_des_lectures_rangees_a_la_hauteur_de_chaque_local(db_session):
    from app.services import thermique_lecture_coupes as lecture

    plan, coupe = _projet_avec_coupe(db_session)
    lecture.enregistrer_traits(db_session, plan, [TRAIT_A, TRAIT_C])
    lecture.enregistrer_vues(db_session, coupe, [
        {**VUE_A, "nom": "COUPE A", "nature": "coupe", "cadre": [882, 978, 1573, 2003]},
        {"nom": "Zoom sur menuiserie", "nature": "detail", "cadre": [0, 0, 10, 10], "pieces": []},
    ])

    resultat = lecture.hauteurs_du_plan(db_session, plan)
    assert resultat["traits_sans_vue"] == ["C"]
    assert [c["vue"] for c in resultat["coupes"]] == ["COUPE A"]
    locaux = resultat["locaux"]
    assert locaux["piece-003"]["hauteur_m"] == 2.88 and locaux["piece-003"]["source"] == "lue"
    assert locaux["piece-019"]["source"] == "deduite"
    # La saisie du thermicien l'emporte, la proposition des coupes reste visible.
    assert locaux["piece-008"]["hauteur_m"] == 2.65
    assert locaux["piece-008"]["source"] == "saisie"
    assert locaux["piece-008"]["proposee_m"] == 2.88


def test_une_lecture_illisible_est_refusee_a_l_entree(db_session):
    from app.services import thermique_lecture_coupes as lecture
    from app.services.thermique import ThermiqueError

    plan, coupe = _projet_avec_coupe(db_session)
    with pytest.raises(ThermiqueError, match="illisible"):
        lecture.enregistrer_vues(db_session, coupe, [{"nom": "A", "nature": "coupe", "cadre": [0, 0, 1, 1],
                                                     "pieces": [{"debut": 0, "fin": 1, "sol": "H99"}]}])
    with pytest.raises(ThermiqueError, match="sur un plan"):
        lecture.enregistrer_traits(db_session, coupe, [TRAIT_A])
    with pytest.raises(ThermiqueError, match="sens"):
        lecture.enregistrer_traits(db_session, plan, [{**TRAIT_A, "sens": [0, 0]}])


@pytest.mark.parametrize(("valeur", "attendu"), [(2.5, 2.5), (None, None)])
def test_hauteur_saisie_controlee(valeur, attendu):
    from app.services import thermique_lecture_coupes as lecture

    assert lecture.controler_hauteur(valeur) == attendu


@pytest.mark.parametrize("valeur", [0.5, 40, "2,5"])
def test_hauteur_saisie_hors_bornes_refusee(valeur):
    from app.services import thermique_lecture_coupes as lecture
    from app.services.thermique import ThermiqueError

    with pytest.raises(ThermiqueError):
        lecture.controler_hauteur(valeur)


def test_le_geste_modifier_pose_et_retire_la_hauteur():
    from app.services import thermique_etude_edition as edition

    analyse = {"objects": [{"id": "piece-001", "category": "piece", "subtype": "Bureau", "points": [[0, 0], [10, 0], [10, 10]]}]}
    edition._modifier(analyse, {"id": "piece-001", "hauteur_m": 2.7})
    assert analyse["objects"][0]["hauteur_m"] == 2.7
    edition._modifier(analyse, {"id": "piece-001", "retirer_hauteur": True})
    assert "hauteur_m" not in analyse["objects"][0]


def test_migration_0088_monte_et_redescend_isolee():
    import importlib.util
    from pathlib import Path

    import sqlalchemy as sa
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect

    moteur = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table("thermique_projects", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    sa.Table("thermique_sheets", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    sa.Table("thermique_travaux", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    metadata.create_all(moteur)
    chemin = Path(__file__).parents[1] / "alembic" / "versions" / "0088_thermique_coupes.py"
    spec = importlib.util.spec_from_file_location("migration_0088", chemin)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with moteur.begin() as connexion:
        migration.op = Operations(MigrationContext.configure(connexion))
        migration.upgrade()
        inspection = inspect(connexion)
        assert "thermique_vues" in inspection.get_table_names()
        assert "traits_coupe_json" in {c["name"] for c in inspection.get_columns("thermique_sheets")}
        assert "type" in {c["name"] for c in inspection.get_columns("thermique_travaux")}
        migration.downgrade()
        inspection = inspect(connexion)
        assert "thermique_vues" not in inspection.get_table_names()
        assert "type" not in {c["name"] for c in inspection.get_columns("thermique_travaux")}


def test_ligne_de_niveau_sans_cote_est_refusee():
    vue = {"nom": "X", "haut": [0, 1], "niveaux": [{"nom": "H1"}], "pieces": [{"debut": 0, "fin": 1, "sol": "H1"}]}
    with pytest.raises(ValueError):
        coupes.pieces_de_la_vue(vue, 100)
