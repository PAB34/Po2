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
from app.models.local import Local
from app.models.patrimoine_legacy import (
    STATUS_IGNORED,
    STATUS_LINKED,
    STATUS_PROPOSED,
    STATUS_OUT_OF_SCOPE,
    STATUS_TO_CREATE,
    STATUS_TODO,
    PatrimoineLegacyAsset,
    PatrimoineLegacyImport,
)
from app.models.site import Site  # noqa: F401
from app.services.patrimoine_legacy import (
    compute_candidates,
    convert_asset_to_local,
    confirm_proposed,
    create_asset_from_building,
    delete_all_imports,
    import_astech_file,
    parse_astech_workbook,
    reset_all_links,
    reset_everything,
    update_asset,
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
    # Le moteur PROPOSE : la validation reste humaine (décision Q17).
    assert cimetiere.status == STATUS_PROPOSED
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
    assert asset.status == STATUS_PROPOSED


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


def test_deplacer_un_point_fusionne_deplace_aussi_le_batiment_po2(db_session: Session):
    """Un bien rattaché et son bâtiment Po2 ne font plus qu'un point sur la carte :
    déplacer ce point doit déplacer les deux, sinon ils se désolidarisent en silence."""
    from app.services.patrimoine_legacy import update_asset

    db_session.add(
        Building(
            id=7, city_id=1, nom_batiment="HOTEL DE VILLE", nom_commune="Sete",
            adresse_reconstituee="1 QUAI DES MOULINS", latitude=43.40, longitude=3.69,
        )
    )
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    asset = db_session.scalar(
        _all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02")
    )
    update_asset(db_session, asset, building_id=7)

    update_asset(db_session, asset, latitude=43.4111, longitude=3.6999)

    building = db_session.get(Building, 7)
    assert asset.latitude == 43.4111 and asset.longitude == 3.6999
    # Le bâtiment Po2 a suivi : c'est tout l'intérêt du point fusionné.
    assert building.latitude == 43.4111 and building.longitude == 3.6999


def test_ajouter_un_batiment_po2_a_la_liste_astech(db_session: Session):
    """Un bâtiment Po2 sans contrepartie ASTECH doit pouvoir rejoindre la liste comme
    bien « à créer » : sans ça, il ne remonterait jamais dans le fichier de retour."""
    from app.models.patrimoine_legacy import STATUS_TO_CREATE
    from app.services.patrimoine_legacy import create_asset_from_building

    building = Building(
        id=9, city_id=1, nom_batiment="NOUVELLE HALLE", nom_commune="Sete",
        adresse_reconstituee="12 RUE NEUVE", dgfip_reference_norm="34301000AZ0007",
        latitude=43.41, longitude=3.70,
    )
    db_session.add(building)
    db_session.commit()

    created = create_asset_from_building(db_session, 1, building)
    assert created.status == STATUS_TO_CREATE
    assert created.building_id == 9
    assert created.nomcourt == "NOUVELLE HALLE"
    assert created.resolved_refcad == "AZ007"
    # Pas de code ASTECH : c'est le logiciel de la collectivité qui l'attribuera.
    assert created.code_bien.startswith("NOUVEAU_")

    # Idempotent : un second appel ne cree pas de doublon.
    again = create_asset_from_building(db_session, 1, building)
    assert again.id == created.id


def test_confirmation_des_propositions(db_session: Session):
    """Un rattachement automatique n'est pas une validation : il doit être confirmé."""
    from app.services.patrimoine_legacy import confirm_proposed

    db_session.add(Building(id=1, city_id=1, nom_batiment="CIMETIERE LE PY", nom_commune="Sete"))
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    compute_candidates(db_session, 1, auto_link=True)

    asset = db_session.scalar(
        _all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02")
    )
    assert asset.status == STATUS_PROPOSED

    result = confirm_proposed(db_session, 1)
    assert result["confirmed"] >= 1
    db_session.refresh(asset)
    assert asset.status == STATUS_LINKED


def test_rattachement_a_un_local_herite_du_batiment_porteur(db_session: Session):
    """Un CODE_BIEN désigne souvent un local. Le local n'ayant ni adresse ni cadastre,
    c'est le bâtiment parent qui les fournit — sinon viser un local ferait perdre
    l'adresse qu'on cherche justement à renvoyer à ASTECH."""
    from app.models.patrimoine_legacy import TARGET_LOCAL
    from app.services.patrimoine_legacy import update_asset

    db_session.add(
        Building(
            id=5, city_id=1, nom_batiment="GROUPE SCOLAIRE", nom_commune="Sete",
            adresse_reconstituee="12 RUE LACAN", dgfip_reference_norm="34301000AB0042",
            latitude=43.40, longitude=3.69,
        )
    )
    db_session.commit()
    db_session.add(Local(id=3, building_id=5, nom_local="LOGEMENT DE FONCTION", type_local="LOGEMENT"))
    db_session.commit()

    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    asset = db_session.scalar(
        _all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02")
    )
    update_asset(db_session, asset, local_id=3)

    assert asset.target_type == TARGET_LOCAL
    assert asset.local_id == 3
    # Le bâtiment porteur est résolu : c'est lui qui alimente carte et réexport.
    assert asset.building_id == 5
    assert asset.resolved_label == "12 RUE LACAN"
    assert asset.resolved_refcad == "AB042"
    assert asset.latitude == 43.40


def test_l_adresse_propre_du_local_prime_sur_celle_du_batiment(db_session: Session):
    """Le fichier d'inventaire porte une adresse sur chaque ligne, y compris pour les
    locaux : l'entrée d'un local peut différer de celle du bâtiment. Quand le local a
    sa propre adresse, c'est elle qui part vers ASTECH."""
    from app.services.patrimoine_legacy import update_asset

    db_session.add(
        Building(
            id=5, city_id=1, nom_batiment="GROUPE SCOLAIRE", nom_commune="Sete",
            adresse_reconstituee="12 RUE LACAN", dgfip_reference_norm="34301000AB0042",
            latitude=43.40, longitude=3.69,
        )
    )
    db_session.commit()
    db_session.add(
        Local(
            id=4, building_id=5, nom_local="LOGEMENT DE FONCTION", type_local="LOGEMENT",
            adresse_reconstituee="14 RUE LACAN", code_postal="34200", nom_commune="Sete",
            dgfip_reference_norm="34301000AB0043", latitude=43.401, longitude=3.691,
        )
    )
    db_session.commit()

    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    asset = db_session.scalar(
        _all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02")
    )
    update_asset(db_session, asset, local_id=4)

    # L'adresse du LOCAL l'emporte, pas celle du bâtiment parent.
    assert asset.resolved_label == "14 RUE LACAN"
    assert asset.resolved_housenumber == "14"
    assert asset.resolved_refcad == "AB043"
    assert asset.resolved_name == "LOGEMENT DE FONCTION"
    assert asset.latitude == 43.401
    # Le bâtiment porteur reste résolu pour la carte et le réexport.
    assert asset.building_id == 5


def test_un_local_sans_adresse_retombe_sur_le_batiment(db_session: Session):
    from app.services.patrimoine_legacy import update_asset

    db_session.add(
        Building(
            id=6, city_id=1, nom_batiment="MAIRIE", nom_commune="Sete",
            adresse_reconstituee="1 QUAI DES MOULINS", dgfip_reference_norm="34301000AH0024",
        )
    )
    db_session.commit()
    db_session.add(Local(id=8, building_id=6, nom_local="SALLE DES MARIAGES", type_local="SALLE"))
    db_session.commit()

    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    asset = db_session.scalar(
        _all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02")
    )
    update_asset(db_session, asset, local_id=8)

    assert asset.resolved_label == "1 QUAI DES MOULINS"
    assert asset.resolved_refcad == "AH024"


def test_reparation_des_liens_orphelins(db_session: Session):
    """Supprimer le patrimoine Po2 met `building_id` à NULL en cascade. Les biens
    restaient affichés « rattaché » alors qu'ils ne pointaient plus vers rien, et
    disparaissaient de la carte. La reconnaissance doit les remettre à traiter."""
    db_session.add(Building(id=1, city_id=1, nom_batiment="CIMETIERE LE PY", nom_commune="Sete"))
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    compute_candidates(db_session, 1, auto_link=True)

    asset = db_session.scalar(
        _all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02")
    )
    assert asset.status == STATUS_PROPOSED

    # Le bâtiment disparaît : la base met building_id à NULL (ON DELETE SET NULL).
    asset.building_id = None
    db_session.add(asset)
    db_session.commit()

    result = compute_candidates(db_session, 1, auto_link=True)
    assert result["repaired"] >= 1
    db_session.refresh(asset)
    # Remis à traiter puis reproposé contre le référentiel ACTUEL : c'est tout
    # l'intérêt après un réimport du patrimoine, les liens se reconstruisent.
    assert asset.building_id == 1
    assert asset.status == STATUS_PROPOSED


def test_lien_orphelin_sans_candidat_reste_a_traiter(db_session: Session):
    """Si plus aucun bâtiment ne correspond, le bien ne doit pas rester marqué
    « rattaché » à un bâtiment inexistant."""
    db_session.add(Building(id=1, city_id=1, nom_batiment="CIMETIERE LE PY", nom_commune="Sete"))
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    compute_candidates(db_session, 1, auto_link=True)

    asset = db_session.scalar(
        _all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02")
    )
    asset.building_id = None
    db_session.add(asset)
    # Le patrimoine entier a disparu : plus aucune cible possible.
    db_session.delete(db_session.get(Building, 1))
    db_session.commit()

    result = compute_candidates(db_session, 1, auto_link=True)
    assert result["repaired"] >= 1
    db_session.refresh(asset)
    assert asset.status == STATUS_TODO
    assert asset.building_id is None
    assert asset.resolved_label is None


def test_le_rattachement_automatique_fait_heriter_l_adresse(db_session: Session):
    """Le moteur rattache : le bien doit hériter du bâtiment, comme un rattachement manuel.

    Sans cet héritage, les biens proposés par le moteur n'ont aucun champ résolu — donc
    le réexport ASTECH n'a rien à écrire pour eux, même une fois confirmés. Constaté en
    prod le 2026-08-19 : 73 biens rattachés automatiquement, zéro adresse héritée.
    """
    db_session.add(
        Building(
            id=1,
            city_id=1,
            nom_batiment="CIMETIERE LE PY",
            nom_commune="Sete",
            adresse_reconstituee="12 RUE DES CAPECHADES",
            dgfip_reference_norm="34301000AK0149",
        )
    )
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    compute_candidates(db_session, 1, auto_link=True)

    asset = db_session.scalar(
        _all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02")
    )
    assert asset.status == STATUS_PROPOSED
    assert asset.resolved_name == "CIMETIERE LE PY"
    assert asset.resolved_housenumber == "12"
    assert asset.resolved_street == "RUE DES CAPECHADES"
    # Section + plan sur 3 chiffres : le format attendu par ASTECH.
    assert asset.resolved_refcad == "AK149"


def test_la_confirmation_realigne_un_nom_devenu_perime(db_session: Session):
    """Un bâtiment renommé après le rattachement ne doit pas réinjecter l'ancien nom.

    Cas réel : « Attribuer IGN » avait renommé des bâtiments avec le toponyme de la zone
    englobante ; après correction du nom du bâtiment, les biens ASTECH portaient encore
    le nom périmé — celui qui serait reparti dans le fichier de la collectivité.
    """
    db_session.add(
        Building(id=1, city_id=1, nom_batiment="CIMETIERE LE PY", nom_commune="Sete")
    )
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    compute_candidates(db_session, 1, auto_link=True)

    building = db_session.get(Building, 1)
    building.nom_batiment = "CIMETIERE MARIN LE PY"
    db_session.add(building)
    db_session.commit()

    confirm_proposed(db_session, 1)
    asset = db_session.scalar(
        _all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02")
    )
    assert asset.status == STATUS_LINKED
    assert asset.resolved_name == "CIMETIERE MARIN LE PY"


def test_la_purge_supprime_les_rapprochements_sans_toucher_aux_decisions(db_session: Session):
    """« Supprimer tous les rapprochements » remet à traiter, sans effacer le reste.

    Trois invariants : un bien « à créer » n'est pas coupé de son bâtiment (il n'existe
    que par lui), une décision de périmètre (`ignore`, `hors_perimetre`) n'est pas
    annulée, et la position de travail est conservée — l'effacer ferait disparaître le
    bien de la carte.
    """
    db_session.add(
        Building(
            id=1,
            city_id=1,
            nom_batiment="CIMETIERE LE PY",
            nom_commune="Sete",
            adresse_reconstituee="12 RUE DES CAPECHADES",
            latitude=43.4,
            longitude=3.69,
        )
    )
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    compute_candidates(db_session, 1, auto_link=True)

    lie = db_session.scalar(_all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02"))
    assert lie.building_id == 1 and lie.resolved_label is not None

    # Sur un SECOND bâtiment : `create_asset_from_building` est idempotent et renverrait
    # le bien déjà rattaché au bâtiment 1 au lieu d'en créer un.
    db_session.add(Building(id=2, city_id=1, nom_batiment="HALLES CENTRALES", nom_commune="Sete"))
    db_session.commit()
    a_creer = create_asset_from_building(db_session, 1, db_session.get(Building, 2))
    ignore = db_session.scalar(
        _all_assets().where(PatrimoineLegacyAsset.code_bien != "ADMICIMET02")
    )
    ignore.status = STATUS_IGNORED
    ignore.building_id = 1
    db_session.add(ignore)
    db_session.commit()

    result = reset_all_links(db_session, 1)
    assert result["cleared"] >= 1

    db_session.refresh(lie)
    assert lie.building_id is None
    assert lie.status == STATUS_TODO
    # L'adresse héritée n'a plus de source : elle part avec le lien.
    assert lie.resolved_label is None
    # La position empruntée au bâtiment repart avec le lien : un bien ASTECH n'a pas de
    # position à lui. La figer fabriquait de faux points sur d'anciens bâtiments
    # (73 cas sur 82 mesurés en prod). Voir
    # `test_detacher_rend_au_bien_son_absence_de_position` pour la règle complète.
    assert lie.latitude is None

    # Le bien « à créer » garde son bâtiment : il n'existe que grâce à lui.
    db_session.refresh(a_creer)
    assert a_creer.building_id == 2
    assert a_creer.status == STATUS_TO_CREATE

    # Une décision de périmètre n'est pas un rapprochement : elle survit.
    db_session.refresh(ignore)
    assert ignore.status == STATUS_IGNORED


def test_un_bien_peut_devenir_un_local_de_son_batiment(db_session: Session):
    """Le chaînon manquant : créer le local, et NE RIEN perdre pour le retour ASTECH.

    Mesuré en prod le 2026-08-20 : 0 bien sur 79 visait un local, faute de pouvoir en
    créer un. Or c'est le cas normal dès que plusieurs biens ASTECH désignent le même
    bâtiment (le club et ses salles, l'école et son restaurant scolaire).

    Décision Q1 (2026-08-20) : passer au niveau local **précise** la structure, il ne
    retire rien — l'adresse et le cadastre restent ceux du bâtiment porteur, donc ce
    que le bien renvoie à ASTECH est inchangé.
    """
    db_session.add(
        Building(
            id=1,
            city_id=1,
            nom_batiment="CIMETIERE LE PY",
            nom_commune="Sete",
            adresse_reconstituee="12 RUE DES CAPECHADES",
            dgfip_reference_norm="34301000AK0149",
            latitude=43.4,
            longitude=3.69,
        )
    )
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    compute_candidates(db_session, 1, auto_link=True)

    asset = db_session.scalar(_all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02"))
    assert asset.building_id == 1 and asset.target_type == "building"

    converted = convert_asset_to_local(db_session, asset)

    assert converted.target_type == "local"
    assert converted.local_id is not None
    # Le bâtiment porteur RESTE : c'est lui qui porte adresse, cadastre et position.
    assert converted.building_id == 1
    assert converted.resolved_refcad == "AK149"
    assert converted.resolved_housenumber == "12"

    local = db_session.get(Local, converted.local_id)
    assert local.building_id == 1
    assert local.nom_local == "CIMETIERE LE PY"
    # Le local hérite de l'adresse du bâtiment : le laisser vide ferait perdre au bien
    # ce qu'il avait en visant le bâtiment.
    assert local.adresse_reconstituee == "12 RUE DES CAPECHADES"

    # Idempotent : rappeler la conversion ne crée pas un second local.
    convert_asset_to_local(db_session, converted)
    assert len(db_session.scalars(select_locals_of(1)).all()) == 1


def test_la_conversion_en_local_reutilise_un_local_existant(db_session: Session):
    """Cas réel du TENNIS CLUB DU BARROU : le local « SALLE… » est déjà en base.

    En créer un second du même nom ferait un doublon dans le référentiel Po2.
    """
    db_session.add(Building(id=1, city_id=1, nom_batiment="CIMETIERE LE PY", nom_commune="Sete"))
    db_session.commit()
    db_session.add(Local(building_id=1, nom_local="CIMETIERE LE PY", type_local="PRINCIPAL"))
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    compute_candidates(db_session, 1, auto_link=True)

    asset = db_session.scalar(_all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02"))
    converted = convert_asset_to_local(db_session, asset)

    locals_found = db_session.scalars(select_locals_of(1)).all()
    assert len(locals_found) == 1
    assert converted.local_id == locals_found[0].id


def test_un_bien_non_rattache_ne_peut_pas_devenir_un_local(db_session: Session):
    """Sans bâtiment porteur, il n'y a pas de parent où créer le local."""
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    asset = db_session.scalar(_all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02"))
    with pytest.raises(ValueError):
        convert_asset_to_local(db_session, asset)


def select_locals_of(building_id: int):
    from sqlalchemy import select

    return select(Local).where(Local.building_id == building_id)


def test_la_suppression_de_l_import_conserve_le_patrimoine_po2(db_session: Session):
    """« Supprimer l'import ASTECH » efface les biens, pas le patrimoine Po2.

    Les bâtiments et les locaux créés en cours de rapprochement sont désormais des
    données **Po2**, pas des données ASTECH : les supprimer ferait perdre du patrimoine
    réel pour effacer un fichier source. Le moteur les retrouvera au réimport, puisqu'ils
    portent le nom du bien.
    """
    db_session.add(
        Building(id=1, city_id=1, nom_batiment="CIMETIERE LE PY", nom_commune="Sete")
    )
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    compute_candidates(db_session, 1, auto_link=True)

    asset = db_session.scalar(_all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02"))
    convert_asset_to_local(db_session, asset)
    assert len(db_session.scalars(select_locals_of(1)).all()) == 1

    result = delete_all_imports(db_session, 1)

    assert result["assets_deleted"] >= 1
    assert result["imports_deleted"] == 1
    assert db_session.scalars(_all_assets()).all() == []
    # Le patrimoine Po2 survit : bâtiment ET local créés en cours de route.
    assert db_session.get(Building, 1) is not None
    assert len(db_session.scalars(select_locals_of(1)).all()) == 1

    # Et le réimport repart proprement, sans reliquat ni doublon.
    reimport = import_astech_file(
        db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook()
    )
    assert reimport["created"] > 0
    assert reimport["updated"] == 0


def test_detacher_rend_au_bien_son_absence_de_position(db_session: Session):
    """Un bien détaché ne doit PAS garder le point emprunté à son bâtiment.

    Un bien ASTECH n'a pas de position à lui : le fichier réel n'en porte qu'une sur
    444. La version précédente figeait le point du bâtiment dans le bien pour qu'il ne
    disparaisse pas de la carte — elle fabriquait de faux points. Mesuré en prod le
    2026-08-20 : 73 des 82 positions étaient posées exactement sur d'anciens bâtiments.

    Ce qui a été **déplacé volontairement** est en revanche conservé.
    """
    db_session.add(
        Building(id=1, city_id=1, nom_batiment="CIMETIERE LE PY", nom_commune="Sete",
                 latitude=43.4, longitude=3.69)
    )
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    compute_candidates(db_session, 1, auto_link=True)

    herite = db_session.scalar(_all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02"))
    herite.latitude, herite.longitude = 43.4, 3.69  # exactement le bâtiment : emprunté
    deplace = db_session.scalar(_all_assets().where(PatrimoineLegacyAsset.code_bien == "SAPLWCPUB05"))
    deplace.building_id = 1
    deplace.latitude, deplace.longitude = 43.41, 3.70  # posé ailleurs à la main
    db_session.add_all([herite, deplace])
    db_session.commit()

    reset_all_links(db_session, 1)

    db_session.refresh(herite)
    db_session.refresh(deplace)
    # Position empruntée au bâtiment : elle repart avec le lien.
    assert herite.latitude is None
    # Position choisie par l'utilisateur : elle survit, c'est du vrai travail.
    assert deplace.latitude == 43.41


def test_la_remise_a_zero_totale_vide_tout_sauf_le_hors_perimetre(db_session: Session):
    """« Repartir de 0 » : plus rien, sauf le constat de périmètre.

    `hors_perimetre` n'est pas une décision de l'utilisateur mais un fait (bien hors
    Sète, décision Q4), recalculé à chaque import. L'annuler ferait remonter dans la
    file des biens qui n'ont rien à y faire.
    """
    db_session.add(
        Building(id=1, city_id=1, nom_batiment="CIMETIERE LE PY", nom_commune="Sete",
                 latitude=43.4, longitude=3.69)
    )
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    compute_candidates(db_session, 1, auto_link=True)

    ignore = db_session.scalar(_all_assets().where(PatrimoineLegacyAsset.code_bien == "SAPLWCPUB05"))
    ignore.status = STATUS_IGNORED
    ignore.latitude, ignore.longitude = 43.41, 3.70
    db_session.add(ignore)
    db_session.commit()

    reset_everything(db_session, 1)

    for asset in db_session.scalars(_all_assets()):
        if asset.status == STATUS_OUT_OF_SCOPE:
            continue
        assert asset.status == STATUS_TODO
        assert asset.building_id is None
        assert asset.local_id is None
        # Aucune position : c'est bien l'etat d'apres import, ou les biens ASTECH
        # n'apparaissent pas sur la carte faute de coordonnees propres.
        assert asset.latitude is None
        assert asset.candidate_building_id is None
        assert asset.resolved_label is None

    # Le hors-perimetre survit : c'est un constat, pas une decision.
    hors = db_session.scalar(_all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMIDECHE01"))
    assert hors.status == STATUS_OUT_OF_SCOPE


def test_valider_un_candidat_disparu_renvoie_un_message_clair(db_session: Session):
    """`candidate_building_id` n'a pas de clé étrangère : il survit à une purge du parc.

    Cas réel du 2026-08-20 : le patrimoine Po2 avait été réimporté, les bâtiments
    avaient de nouveaux identifiants (1132→1315) et les 294 candidats pointaient vers
    les anciens (937→1131). « Valider ce rattachement » échouait alors sur la contrainte
    d'intégrité — une 500 opaque, donc un bouton qui semblait ne rien faire.
    """
    db_session.add(Building(id=1, city_id=1, nom_batiment="CIMETIERE LE PY", nom_commune="Sete"))
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    asset = db_session.scalar(_all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02"))

    with pytest.raises(ValueError, match="n'existe plus"):
        update_asset(db_session, asset, building_id=999)


def test_reconnaitre_les_noms_nettoie_les_candidats_perimes(db_session: Session):
    """Relancer la reconnaissance doit effacer les candidats qui pointent dans le vide."""
    db_session.add(Building(id=1, city_id=1, nom_batiment="CIMETIERE LE PY", nom_commune="Sete"))
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())

    # Un bien hors périmètre n'est pas rescanné : sans nettoyage explicite, son candidat
    # périmé resterait affiché avec un bouton de validation qui échoue.
    hors = db_session.scalar(_all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMIDECHE01"))
    hors.candidate_building_id = 999
    hors.candidate_label = "BATIMENT DISPARU"
    db_session.add(hors)
    db_session.commit()

    compute_candidates(db_session, 1, auto_link=False)

    db_session.refresh(hors)
    assert hors.candidate_building_id is None
    assert hors.candidate_label is None


def test_le_nom_du_bien_est_modifiable_mais_pas_son_code(db_session: Session):
    """Le libellé ASTECH est parfois fautif ; le code bien, lui, est la clé de retour."""
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    asset = db_session.scalar(_all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02"))

    update_asset(db_session, asset, designation="CIMETIERE MARIN LE PY")

    db_session.refresh(asset)
    # Les deux libellés bougent ensemble : l'écran affiche `nomcourt` en priorité, ne
    # corriger que `designation` ne changerait rien à ce qu'on voit.
    assert asset.designation == "CIMETIERE MARIN LE PY"
    assert asset.nomcourt == "CIMETIERE MARIN LE PY"
    assert asset.code_bien == "ADMICIMET02"


def test_le_rattachement_donne_au_bien_le_nom_du_batiment_po2(db_session: Session):
    """Décision Q11, appliquée au geste : rattacher fait converger les deux référentiels.

    Le nom Po2 gagne et sera réécrit dans ASTECH. Le `code_bien` reste la clé de
    rapprochement, donc renommer ne casse rien au cycle suivant.
    """
    db_session.add(
        Building(id=1, city_id=1, nom_batiment="CIMETIERE MARIN LE PY", nom_commune="Sete")
    )
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    asset = db_session.scalar(_all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02"))
    assert asset.designation == "CIMETIERE LE PY"

    update_asset(db_session, asset, building_id=1)

    db_session.refresh(asset)
    assert asset.designation == "CIMETIERE MARIN LE PY"
    assert asset.nomcourt == "CIMETIERE MARIN LE PY"
    # Le batiment Po2, lui, n'est pas renomme : c'est la source, pas la cible.
    assert db_session.get(Building, 1).nom_batiment == "CIMETIERE MARIN LE PY"
    # Et la cle de reinjection ne bouge jamais.
    assert asset.code_bien == "ADMICIMET02"


def test_un_nom_saisi_a_la_main_gagne_sur_le_nom_du_batiment(db_session: Session):
    """Corriger un libellé dans le même geste ne doit pas se faire écraser."""
    db_session.add(Building(id=1, city_id=1, nom_batiment="NOM PO2", nom_commune="Sete"))
    db_session.commit()
    import_astech_file(db_session, city_id=1, filename="export.xlsx", raw_bytes=_build_workbook())
    asset = db_session.scalar(_all_assets().where(PatrimoineLegacyAsset.code_bien == "ADMICIMET02"))

    update_asset(db_session, asset, building_id=1, designation="NOM CHOISI A LA MAIN")

    db_session.refresh(asset)
    assert asset.designation == "NOM CHOISI A LA MAIN"
