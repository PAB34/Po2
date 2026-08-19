"""Import du référentiel patrimoine historique (ASTECH) et rapprochement.

Les points à verrouiller, tous constatés sur le fichier réel de la collectivité :

1. **Choix de la feuille** : le classeur contient `Feuil1` (en-têtes en ligne 2, clé
   `CODE_BIEN` renseignée) et `BAT` (en-têtes en ligne 1, clé `CODEBIEN` **vidée**).
   Prendre la mauvaise feuille fait perdre la clé de rapprochement — et un réexport
   bâti sur ses en-têtes serait refusé par ASTECH.
2. **En-têtes conservés à l'octet près** : ASTECH ne réimporte le fichier modifié que
   si les en-têtes et le code bien sont strictement inchangés.
3. **Périmètre** : par défaut tout le contenu de la feuille `BAT` (genres BATI et SITE,
   y compris les biens sortis du parc), hors Sète marqué hors périmètre, mais une commune
   **absente** ne doit PAS écarter le bien (41 bâtiments sétois n'ont aucune commune).
4. **Idempotence** : rejouer le même export ne duplique rien et ne perd aucune décision.
"""
from __future__ import annotations

import io
import json

import openpyxl
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.building import Building
from app.models.city import City
from app.models.local import Local  # noqa: F401 (enregistre la table)
from app.models.patrimoine_legacy import (
    STATUS_LINKED,
    STATUS_OUT_OF_SCOPE,
    STATUS_TODO,
    PatrimoineLegacyAsset,
    PatrimoineLegacyImport,
)
from app.models.site import Site  # noqa: F401
from app.services.patrimoine_legacy import (
    compute_candidates,
    import_astech_file,
    parse_astech_workbook,
)

# En-têtes tels qu'ils apparaissent dans l'export réel (orthographe incluse).
HEADERS = [
    "CODE_BIEN", "DESIGNATION", "NOMCOURT", "GENRE", "CATEG", "CATEG_DES",
    "SOUSCAT", "SOUSCAT_DES", "COD_COMPTABLE", "CODBAR", "HORSPARC",
    "CODE_PARENT", "NORUE", "BISTER", "LIBELVOIE", "CODPOST", "VILLE",
    "COMMUNE", "REFCAD", "0#SURF",
]

# (code, designation, nomcourt, genre, horsparc, norue, bister, libelvoie, codpost, ville, commune)
ROWS = [
    ("ADMICIMET02", "CIMETIERE LE PY", "CIMETIERE LE PY", "BATI", "N", "0", None, "CAMILLE BLANC", "34200", "SETE", "34301"),
    ("ADMIDECHE01", "DECHETTERIE DE BALARUC LE VIEUX", "DECHETTERIE BALARUC LE VIEUX", "BATI", "N", "0", None, "QUARTIER DES USINES", "34540", "BALARUC LE VIEUX", "34022"),
    ("SAPLWCPUB05", "WC PUBLICS SAINT CLAIR", "WC PUBLICS SAINT CLAIR", "BATI", "N", None, None, None, None, None, None),
    ("ADMIVIEUX99", "ANCIEN LOCAL DESAFFECTE", "ANCIEN LOCAL", "BATI", "O", None, None, None, "34200", "SETE", "34301"),
    ("EVJARDIN01", "JARDIN DU CHATEAU", "JARDIN DU CHATEAU", "EV", "N", None, None, None, "34200", "SETE", "34301"),
]


def _build_workbook() -> bytes:
    """Reproduit la structure réelle : `Feuil1` clé renseignée (en-têtes ligne 2),
    `BAT` clé vidée (en-têtes ligne 1, orthographe `CODEBIEN`)."""
    workbook = openpyxl.Workbook()

    feuil1 = workbook.active
    feuil1.title = "Feuil1"
    feuil1.append([None] * len(HEADERS))  # ligne 1 vide, comme dans l'export réel
    feuil1.append(HEADERS)
    for row in ROWS:
        code, designation, nomcourt, genre, horsparc, norue, bister, voie, cp, ville, commune = row
        feuil1.append([
            code, designation, nomcourt, genre, "ADMI", "ADMINISTRATIF", "SOUS", "SOUS DES",
            None, code, horsparc, None, norue, bister, voie, cp, ville, commune, None, "0",
        ])

    bat = workbook.create_sheet("BAT")
    bat_headers = ["CODEBIEN"] + HEADERS[1:]
    bat.append(bat_headers)
    for row in ROWS:
        _, designation, nomcourt, genre, horsparc, norue, bister, voie, cp, ville, commune = row
        bat.append([
            None, designation, nomcourt, genre, "ADMI", "ADMINISTRATIF", "SOUS", "SOUS DES",
            None, None, horsparc, None, norue, bister, voie, cp, ville, commune, None, "0",
        ])

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


def test_selectionne_la_feuille_dont_la_cle_est_renseignee():
    parsed = parse_astech_workbook(_build_workbook())
    # `BAT` a la clé vidée : la retenir ferait perdre le rapprochement.
    assert parsed["sheet_name"] == "Feuil1"
    assert parsed["header_row"] == 2
    assert parsed["key_header"] == "CODE_BIEN"


def test_conserve_les_entetes_a_l_octet_pres(db_session: Session):
    import_astech_file(
        db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook()
    )
    import_row = db_session.scalar(select_import(db_session))
    stored = json.loads(import_row.headers_json)
    # Orthographes exactes : ASTECH refuse l'import si un en-tête a bougé.
    assert stored == HEADERS
    assert "COD_COMPTABLE" in stored and "0#SURF" in stored
    assert import_row.sheet_name == "Feuil1"
    assert import_row.header_row == 2


def select_import(db: Session):
    from sqlalchemy import select

    return select(PatrimoineLegacyImport).where(PatrimoineLegacyImport.city_id == 1)


def test_perimetre_par_defaut_couvre_la_feuille_bat(db_session: Session):
    """Défaut (décision 2026-08-19) : tout le contenu de la feuille `BAT`, soit les
    genres BATI et SITE, **y compris les biens sortis du parc**."""
    result = import_astech_file(
        db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook()
    )
    codes = {asset.code_bien: asset for asset in db_session.scalars(_all_assets())}

    # Sorti du parc : importé, et signalé par `horsparc` plutôt qu'écarté.
    assert "ADMIVIEUX99" in codes
    assert codes["ADMIVIEUX99"].horsparc == "O"
    # Espace vert : hors du périmètre « bâtiments ».
    assert "EVJARDIN01" not in codes
    assert result["skipped_scope"] == 1

    # Hors Sète : importé mais marqué hors périmètre, jamais perdu silencieusement.
    assert codes["ADMIDECHE01"].status == STATUS_OUT_OF_SCOPE

    # Commune absente : reste à traiter. C'est le cas des 41 bâtiments sétois
    # sans commune renseignée, qu'une lecture littérale de la règle supprimerait.
    assert codes["SAPLWCPUB05"].status == STATUS_TODO


def test_perimetre_restrictif_reste_disponible(db_session: Session):
    """Le périmètre reste paramétrable : Q2 n'est pas tranchée par la référente ASTECH."""
    result = import_astech_file(
        db_session,
        city_id=1,
        filename="export.xlsx",
        raw_bytes=_build_workbook(),
        genres=("BATI",),
        include_out_of_park=False,
    )
    codes = {asset.code_bien for asset in db_session.scalars(_all_assets())}
    assert "ADMIVIEUX99" not in codes
    assert "EVJARDIN01" not in codes
    assert result["skipped_scope"] == 2


def _all_assets():
    from sqlalchemy import select

    return select(PatrimoineLegacyAsset).where(PatrimoineLegacyAsset.city_id == 1)


def test_payload_source_conserve_pour_le_reexport(db_session: Session):
    import_astech_file(
        db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook()
    )
    asset = db_session.scalar(
        _all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02")
    )
    payload = json.loads(asset.source_payload_json)
    # Toutes les colonnes d'origine sont là, y compris celles que Po2 n'exploite pas.
    assert set(payload) == set(HEADERS)
    assert payload["CODE_BIEN"] == "ADMICIMET02"
    assert payload["0#SURF"] == "0"


def test_import_idempotent_et_preserve_les_decisions(db_session: Session):
    raw = _build_workbook()
    first = import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=raw)
    assert first["created"] == 4 and first["updated"] == 0

    # L'utilisateur rattache un bien à la main.
    building = Building(id=10, city_id=1, nom_batiment="CIMETIERE LE PY", nom_commune="Sete")
    db_session.add(building)
    db_session.commit()
    asset = db_session.scalar(
        _all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02")
    )
    asset.building_id = 10
    asset.status = STATUS_LINKED
    db_session.add(asset)
    db_session.commit()

    second = import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=raw)
    assert second["created"] == 0 and second["updated"] == 4
    assert db_session.scalar(_count_assets()) == 4

    asset = db_session.scalar(
        _all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02")
    )
    assert asset.building_id == 10
    assert asset.status == STATUS_LINKED


def _count_assets():
    from sqlalchemy import func, select

    return select(func.count(PatrimoineLegacyAsset.id)).where(PatrimoineLegacyAsset.city_id == 1)


def test_rapprochement_auto_des_evidences_et_garde_fou_semantique(db_session: Session):
    db_session.add_all([
        Building(id=1, city_id=1, nom_batiment="CIMETIERE LE PY", nom_commune="Sete"),
        Building(id=2, city_id=1, nom_batiment="CIMETIERE MARIN", nom_commune="Sete"),
        Building(id=3, city_id=1, nom_batiment="HOTEL DE VILLE", nom_commune="Sete"),
    ])
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())

    result = compute_candidates(db_session, 1, auto_link=True)
    assert result["auto_linked"] >= 1

    cimetiere = db_session.scalar(
        _all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02")
    )
    # Nom identique -> rattaché au bon cimetière, pas à « CIMETIERE MARIN ».
    assert cimetiere.building_id == 1
    assert cimetiere.status == STATUS_LINKED
    assert cimetiere.link_origin == "auto"

    # Aucun bâtiment ne ressemble aux WC publics : pas de candidat inventé.
    wc = db_session.scalar(
        _all_assets().where(PatrimoineLegacyAsset.code_bien == "SAPLWCPUB05")
    )
    assert wc.building_id is None
    assert wc.status == STATUS_TODO


def test_un_nom_identique_reste_rattache_malgre_un_voisin_ressemblant(db_session: Session):
    """Cas réel : « ECOLE ELEMENTAIRE PAUL BERT » a un homonyme proche en base.
    Un score parfait ne doit pas être bloqué par la présence d'un second candidat."""
    db_session.add_all([
        Building(id=1, city_id=1, nom_batiment="CIMETIERE LE PY", nom_commune="Sete"),
        Building(id=2, city_id=1, nom_batiment="CIMETIERE LE PY ANNEXE", nom_commune="Sete"),
    ])
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    compute_candidates(db_session, 1, auto_link=True)

    asset = db_session.scalar(
        _all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02")
    )
    assert asset.building_id == 1
    assert asset.status == STATUS_LINKED


def test_deux_biens_qui_visent_le_meme_batiment_ne_sont_pas_rattaches_seuls(db_session: Session):
    """Cas réel : « SERVICE ENSEIGNEMENT » et « SERVICE E.M.O.P. ENSEIGNEMENT » pointent
    tous deux le même bâtiment. La relation N codes bien -> 1 bâtiment reste permise,
    mais c'est à l'utilisateur de dire lequel est lequel."""
    db_session.add(Building(id=1, city_id=1, nom_batiment="CIMETIERE LE PY", nom_commune="Sete"))
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    # Un second bien historique porte le même nom que le premier.
    db_session.add(
        PatrimoineLegacyAsset(
            city_id=1,
            code_bien="ADMICIMET99",
            designation="CIMETIERE LE PY",
            nomcourt="CIMETIERE LE PY",
            genre="BATI",
            horsparc="N",
            status=STATUS_TODO,
        )
    )
    db_session.commit()

    result = compute_candidates(db_session, 1, auto_link=True)
    assert result["auto_linked"] == 0

    for code in ("ADMICIMET02", "ADMICIMET99"):
        asset = db_session.scalar(_all_assets().where(PatrimoineLegacyAsset.code_bien == code))
        assert asset.building_id is None
        assert asset.status == STATUS_TODO
        assert asset.candidate_building_id == 1
        assert asset.candidate_reason == "plusieurs biens visent ce bâtiment"


def test_rattachement_herite_nom_adresse_et_cadastre(db_session: Session):
    """Déposer un bien ASTECH sur un bâtiment Po2 doit lui faire reprendre TOUT ce que
    Po2 sait : le nom, l'adresse découpée et la référence cadastrale.

    Les bâtiments Po2 ne stockent pas l'adresse découpée (vérifié en prod : numero_voirie,
    nom_voie, section et numero_plan sont vides sur les 183 lignes). Tout est agrégé dans
    `adresse_reconstituee` et `dgfip_reference_norm` : l'héritage doit donc reconstituer
    le découpage, sinon le réexport ASTECH n'a ni numéro, ni voie, ni cadastre à écrire.
    """
    from app.services.patrimoine_legacy import update_asset

    db_session.add(
        Building(
            id=42,
            city_id=1,
            nom_batiment="ECOLE ELEMENTAIRE PAUL BERT",
            nom_commune="Sete",
            adresse_reconstituee="208 AV DU MARECHAL JUIN",
            dgfip_reference_norm="34301000AK0149",
        )
    )
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    asset = db_session.scalar(
        _all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02")
    )

    update_asset(db_session, asset, building_id=42)

    assert asset.resolved_name == "ECOLE ELEMENTAIRE PAUL BERT"
    assert asset.resolved_housenumber == "208"
    assert asset.resolved_street == "AV DU MARECHAL JUIN"
    assert asset.resolved_label == "208 AV DU MARECHAL JUIN"
    assert asset.resolved_section == "AK"
    assert asset.resolved_numero_plan == "0149"
    # Format attendu par ASTECH : section + plan sur 3 chiffres.
    assert asset.resolved_refcad == "AK149"
    assert asset.resolved_source == "building"
    # L'adresse ASTECH d'origine reste intacte : le fichier source n'est pas altéré.
    assert asset.source_libelvoie == "CAMILLE BLANC"


def test_detachement_efface_les_valeurs_heritees(db_session: Session):
    from app.services.patrimoine_legacy import update_asset

    db_session.add(
        Building(
            id=42, city_id=1, nom_batiment="MAIRIE", nom_commune="Sete",
            adresse_reconstituee="1 QUAI DES MOULINS", dgfip_reference_norm="34301000AH0024",
        )
    )
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    asset = db_session.scalar(
        _all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02")
    )
    update_asset(db_session, asset, building_id=42)
    assert asset.resolved_refcad == "AH024"

    update_asset(db_session, asset, clear_building=True, status="a_traiter")
    assert asset.resolved_name is None
    assert asset.resolved_refcad is None
    assert asset.resolved_label is None
