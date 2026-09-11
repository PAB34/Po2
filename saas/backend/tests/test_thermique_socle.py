"""Outil de métré thermique — socle (étape 1).

Couvre : verrou des comptes bureaux d'études (outil thermique seulement), suggestion de la
nature et du niveau à partir des noms de fichiers réels du projet d'essai, import PDF en
planches, isolement des projets, échelle et contrôle par une cote.
Voir `docs/thermique/metre-thermique-decisions.md`.
"""
from __future__ import annotations

import json
from io import BytesIO

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBasicCredentials
from pypdf import PdfWriter
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.deps import get_authenticated_user, get_current_user
from app.api.routes.internal_auth import verify_basic_auth
from app.core.config import settings
from app.core.db import Base
from app.core.roles import THERMIQUE_EXTERNAL_ROLE
from app.core.security import create_access_token, get_password_hash
from app.models.user import User
from app.services.thermique import (
    ThermiqueError,
    add_document,
    calibrate_sheet,
    create_external_account,
    create_project,
    delete_project,
    denominator_from_measure,
    document_path,
    get_project_for_user,
    paper_pt_to_real_m,
    serialize_project_detail,
    suggest_nature_and_level,
    update_sheet,
)

PASSWORD = "motdepasse-solide"


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture()
def storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "thermique_storage_dir", str(tmp_path))
    return tmp_path


def _user(db: Session, email: str, role: str = "USER") -> User:
    user = User(
        email=email,
        password_hash=get_password_hash(PASSWORD),
        nom="Nom",
        prenom="Prenom",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _pdf(pages: int = 1, width: float = 1684, height: float = 2384) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=width, height=height)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _bearer(user: User) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=create_access_token(str(user.id)))


# --- Comptes -------------------------------------------------------------------


def test_compte_externe_refuse_sur_po2_mais_accepte_sur_l_outil(db_session):
    externe = _user(db_session, "be@bureau.fr", THERMIQUE_EXTERNAL_ROLE)
    interne = _user(db_session, "agent@ville.fr")

    authentifie = get_authenticated_user(_bearer(externe), db_session)
    assert authentifie.id == externe.id
    with pytest.raises(HTTPException) as exc:
        get_current_user(authentifie)
    assert exc.value.status_code == 403

    assert get_current_user(get_authenticated_user(_bearer(interne), db_session)).id == interne.id


def test_garde_du_site_principal_refuse_les_comptes_de_l_outil(db_session):
    # thermique.* n'a plus de garde navigateur (une seule connexion, Q6) ; celle du site
    # principal doit toujours refuser les comptes bureaux d'études.
    _user(db_session, "be@bureau.fr", THERMIQUE_EXTERNAL_ROLE)
    _user(db_session, "agent@ville.fr")
    externe = HTTPBasicCredentials(username="be@bureau.fr", password=PASSWORD)
    interne = HTTPBasicCredentials(username="agent@ville.fr", password=PASSWORD)

    with pytest.raises(HTTPException) as exc:
        verify_basic_auth(externe, db_session)
    assert exc.value.status_code == 401
    assert verify_basic_auth(interne, db_session).status_code == 204
    with pytest.raises(HTTPException):
        verify_basic_auth(HTTPBasicCredentials(username="agent@ville.fr", password="faux-mdp"), db_session)


def test_creation_compte_bureau_d_etudes(db_session):
    user = create_external_account(db_session, " BE@Bureau.fr ", "Durand", "Lea", PASSWORD)
    assert user.role == THERMIQUE_EXTERNAL_ROLE
    assert user.city_id is None
    assert user.email == "be@bureau.fr"
    with pytest.raises(ThermiqueError):
        create_external_account(db_session, "be@bureau.fr", "Durand", "Lea", PASSWORD)


# --- Suggestions -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("filename", "nature", "level"),
    [
        ("PC01-FRONT-PLANMASSE.pdf", "plan_masse", None),
        ("PC02-FRONT-NIVEAU-1.pdf", "plan", "Niveau -1"),
        ("PC03-FRONT-NIVEAU0.pdf", "plan", "Niveau 0"),
        ("PC04-FRONT-NIVEAU1.pdf", "plan", "Niveau 1"),
        ("PC06-FRONT-NIVEAU3.pdf", "plan", "Niveau 3"),
        ("PC07-FRONT-NIVEAUTOITURE.pdf", "plan", "Toiture"),
        ("PC08-FRONT-ELEVEST-NORD.pdf", "facade", None),
        ("PC09-FRONT-ELEVSUD-OUEST.pdf", "facade", None),
        ("PC10-FRONT-COUPESAB.pdf", "coupe", None),
        ("PC11-FRONT-COUPESCD.pdf", "coupe", None),
        ("Plan RDC.pdf", "plan", "RDC"),
        ("plan R+2 bureaux.pdf", "plan", "R+2"),
        ("Façade sud.pdf", "facade", None),
        ("notice.pdf", None, None),
    ],
)
def test_suggestion_nature_et_niveau(filename, nature, level):
    assert suggest_nature_and_level(filename) == (nature, level)


# --- Échelle -------------------------------------------------------------------


def test_echelle_1_100_retrouve_la_cote_imprimee():
    # Mesuré sur le plan niveau 0 du projet d'essai : 31,82 m à 1/100.
    length_pt = 31.82 * 1000 / 100 / (25.4 / 72)
    assert paper_pt_to_real_m(length_pt, 100) == pytest.approx(31.82)
    assert denominator_from_measure(length_pt, 31.82) == pytest.approx(100)


# --- Import et planches --------------------------------------------------------------


def test_import_pdf_cree_une_planche_par_page(db_session, storage):
    user = _user(db_session, "agent@ville.fr")
    project = create_project(db_session, user, "Médiathèque", None)

    document = add_document(db_session, project, "PC10-FRONT-COUPESAB.pdf", _pdf(pages=2), user)

    assert document.page_count == 2
    assert document_path(document).is_file()
    assert [sheet.label for sheet in document.sheets] == ["PC10-FRONT-COUPESAB - p. 1", "PC10-FRONT-COUPESAB - p. 2"]
    for sheet in document.sheets:
        assert sheet.nature is None  # suggestion à valider
        assert sheet.nature_suggested == "coupe"
        assert (sheet.page_width_pt, sheet.page_height_pt) == (1684, 2384)

    detail = serialize_project_detail(project)
    assert detail["sheet_count"] == 2
    assert detail["documents"][0]["sheets"][0]["status"] == "a_classer"


def test_import_refuse_doublon_dxf_et_faux_pdf(db_session, storage):
    user = _user(db_session, "agent@ville.fr")
    project = create_project(db_session, user, "Projet", None)
    data = _pdf()
    add_document(db_session, project, "PC03-FRONT-NIVEAU0.pdf", data, user)

    with pytest.raises(ThermiqueError, match="déjà importé"):
        add_document(db_session, project, "copie.pdf", data, user)
    with pytest.raises(ThermiqueError, match="étape 2"):
        add_document(db_session, project, "plan.dxf", b"0\nSECTION", user)
    with pytest.raises(ThermiqueError, match="pas un PDF"):
        add_document(db_session, project, "plan.pdf", b"bonjour", user)


def test_un_projet_n_est_visible_que_de_son_proprietaire(db_session, storage):
    auteur = _user(db_session, "be@bureau.fr", THERMIQUE_EXTERNAL_ROLE)
    autre = _user(db_session, "autre@bureau.fr", THERMIQUE_EXTERNAL_ROLE)
    project = create_project(db_session, auteur, "Projet", None)

    assert get_project_for_user(db_session, auteur, project.id) is not None
    assert get_project_for_user(db_session, autre, project.id) is None


def test_classement_echelle_et_controle_par_cote(db_session, storage):
    user = _user(db_session, "agent@ville.fr")
    project = create_project(db_session, user, "Projet", None)
    sheet = add_document(db_session, project, "PC03-FRONT-NIVEAU0.pdf", _pdf(), user).sheets[0]

    update_sheet(db_session, sheet, {"nature": "plan", "scale_denominator": 100, "rotation_deg": 450})
    assert (sheet.nature, sheet.scale_denominator, sheet.scale_source, sheet.rotation_deg) == ("plan", 100, "declaree", 90)
    with pytest.raises(ThermiqueError):
        update_sheet(db_session, sheet, {"nature": "perspective"})

    # Cote de 31,82 m cliquée à 902 pt d'écart : l'échelle déclarée est confirmée, non remplacée.
    calibrate_sheet(db_session, sheet, [100.0, 200.0], [1002.0, 200.0], 31.82, apply=False)
    detail = serialize_project_detail(project)["documents"][0]["sheets"][0]
    assert detail["status"] == "prete"
    assert detail["scale_denominator"] == 100
    assert detail["calibration"]["denominator_from_cote"] == pytest.approx(100.0, abs=0.05)
    assert abs(detail["calibration"]["ecart_pct"]) < 0.1

    calibrate_sheet(db_session, sheet, [0.0, 0.0], [0.0, 1000.0], 50.0, apply=True)
    assert sheet.scale_source == "cote"
    assert sheet.scale_denominator == pytest.approx(141.73, abs=0.01)
    assert json.loads(sheet.calibration_json)["real_length_m"] == 50.0

    with pytest.raises(ThermiqueError, match="trop proches"):
        calibrate_sheet(db_session, sheet, [0.0, 0.0], [0.2, 0.0], 1.0, apply=True)


def test_suppression_projet_efface_les_fichiers(db_session, storage):
    user = _user(db_session, "agent@ville.fr")
    project = create_project(db_session, user, "Projet", None)
    path = document_path(add_document(db_session, project, "a.pdf", _pdf(), user))
    assert path.is_file()

    delete_project(db_session, project)
    assert not path.exists()


def test_suppression_fichier_efface_le_pdf_et_ses_tuiles(db_session, storage):
    from app.services.thermique import delete_document
    from app.services.thermique_raster import raster_dir

    user = _user(db_session, "agent@ville.fr")
    project = create_project(db_session, user, "Projet", None)
    document = add_document(db_session, project, "a.pdf", _pdf(pages=2), user)
    path = document_path(document)
    tile_dirs = [raster_dir(project.id, sheet.id, 0) for sheet in document.sheets]
    for folder in tile_dirs:
        folder.mkdir(parents=True)
        (folder / "manifest.json").write_text("{}", encoding="utf-8")

    delete_document(db_session, document)

    assert not path.exists()
    assert not any(folder.exists() for folder in tile_dirs)
    assert serialize_project_detail(project)["sheet_count"] == 0
