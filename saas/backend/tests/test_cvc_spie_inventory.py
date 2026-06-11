"""Tests de l'import inventaire CVC SPIE (2e marché) en parallèle de DALKIA.

Couvre : extraction du nom de bâtiment (LR/34/SETE/<NOM>-MAIRIE), parsing de la date
de mise en service hétérogène, détection automatique du format, combinaison
type+catégorie pour le matching SYPEMI, et coexistence/purge ciblée par provider.
"""
from __future__ import annotations

import io

import openpyxl
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.building import Building  # noqa: F401 (enregistre la table)
from app.models.city import City
from app.models.cvc import CvcInventoryItem
from app.models.equipment import EquipmentReference  # noqa: F401
from app.models.local import Local  # noqa: F401
from app.models.site import Site  # noqa: F401
from app.services.cvc import (
    PROVIDER_DALKIA,
    PROVIDER_SPIE,
    _extract_building_name,
    _parse_mes_year,
    detect_inventory_provider,
    import_cvc_from_excel,
    list_cvc_import_batches,
)

SPIE_HEADER = [
    "Nom du parc",
    "Nom du bâtiment",
    "Zone(s) desservie(s)",
    "Local",
    "Niveau",
    "Catégorie de l'équipement",
    "Type d'équipement",
    "Nom complet de l'équipement (type + complémentaire)",
    "Sous-catégorie de l'équipement",
    "Quantité",
    "Marque",
    "Modèle",
    "N° de série",
    "Puissance",
    "Puissance frigorifique",
    "Puissance calorifique",
    "Capacité",
    "Date de mise en service",
    "Durée de vie restante",
]

DALKIA_HEADER = [
    "SITE", "BATIMENT", "NIVEAU", "LOCAL", "DESIGNATION", "FAMILLE",
    "MARQUE", "MODELE", "STATUT", "ETAT SANTE", "QTE QTE RELEVEE", "DATE MES",
]


def _workbook_bytes(header: list[str], rows: list[list]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(header)
    for row in rows:
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _spie_row(batiment, categorie, type_eq, designation, *, qte=1, marque=None,
              modele=None, serie=None, puissance=None, p_frigo=None, date_mes=None, duree=None):
    return [
        "MAIRIE SETE-BATIMENTS-2025", batiment, None, None, None, categorie, type_eq,
        designation, None, qte, marque, modele, serie, puissance, p_frigo, None, None,
        date_mes, duree,
    ]


# --------------------------------------------------------------------------- #
# Fonctions pures
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("\t LR/34/SETE/PCHS (BAT MODULAIRE)-MAIRIE", "PCHS (BAT MODULAIRE)"),
        (" LR/34/SETE/PCHS (EX BAT EDF)-MAIRIE", "PCHS (EX BAT EDF)"),
        ("LR/34/SETE/BASE MIALLE-MUNOZ-MAIRIE", "BASE MIALLE-MUNOZ"),
        ("LR/34/SETE/AGENCE PORT DES QUILLES-VILLEROY-MAIRIE", "AGENCE PORT DES QUILLES-VILLEROY"),
        ("LR/34/SETE/GALERIE DES BAINS/BUREAU RTS/CLUB DES AINES-MAIRIE", "GALERIE DES BAINS/BUREAU RTS/CLUB DES AINES"),
        ("LR/34/SETE/EGLISE SAINT LOUIS -MAIRIE", "EGLISE SAINT LOUIS"),
        ("LR/34/SETE/MAISON DE L'HABITAT -MAIRIE", "MAISON DE L'HABITAT"),
    ],
)
def test_extract_building_name(raw, expected):
    assert _extract_building_name(raw) == expected


def test_extract_building_name_idempotent():
    once = _extract_building_name("LR/34/SETE/VILLA SALIS-MAIRIE")
    assert _extract_building_name(once) == once == "VILLA SALIS"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("01/2022", 2022),
        ("2025", 2025),
        ("30/09/2022", 2022),
        ("06/2023", 2023),
        (2016, 2016),
        (None, None),
        ("n/a", None),
        ("1850", None),
    ],
)
def test_parse_mes_year(value, expected):
    assert _parse_mes_year(value) == expected


def test_detect_inventory_provider():
    assert detect_inventory_provider(SPIE_HEADER) == PROVIDER_SPIE
    assert detect_inventory_provider(DALKIA_HEADER) == PROVIDER_DALKIA


# --------------------------------------------------------------------------- #
# Intégration sqlite
# --------------------------------------------------------------------------- #

@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


def test_spie_import_extracts_building_and_keeps_provided_life(db_session):
    raw = _workbook_bytes(
        SPIE_HEADER,
        [
            _spie_row("LR/34/SETE/VILLA SALIS-MAIRIE", "SPLIT-SYSTEM - UNITE INTERIEURE",
                      "EMETTEUR", "Split-system - unité intérieure", marque="FUJITSU",
                      p_frigo=2.5, date_mes="01/2022", duree=11),
            _spie_row("\t LR/34/SETE/PCHS (BAT MODULAIRE)-MAIRIE", "GAZ", "CHAUDIERE",
                      "Chaudière murale gaz", qte=0, serie="X12", duree=5),
        ],
    )
    result = import_cvc_from_excel(db_session, raw, [], city_id=1)

    assert result.provider == PROVIDER_SPIE
    assert result.imported == 2
    assert result.import_batch.startswith("spie_")

    items = list(db_session.scalars(select(CvcInventoryItem).order_by(CvcInventoryItem.id)))
    assert {i.site_raw for i in items} == {"VILLA SALIS", "PCHS (BAT MODULAIRE)"}
    assert all(i.provider == PROVIDER_SPIE for i in items)

    villa = next(i for i in items if i.site_raw == "VILLA SALIS")
    assert villa.puissance_frigorifique == 2.5
    assert villa.date_mis_en_service == 2022
    assert villa.type_equipement == "EMETTEUR"
    # Pas de référence SYPEMI seedée -> calcul impossible -> on garde la valeur fournie.
    assert villa.duree_vie_restante == 11
    assert villa.duree_vie_restante_source == "fournie"


def test_provider_purge_is_isolated(db_session):
    dalkia_raw = _workbook_bytes(
        DALKIA_HEADER,
        [["LR/34/SETE/MAGASIN GENERAL-MAIRIE", None, None, None, "Chaudière", "Chaudiere",
          None, None, None, "bon", 1, 2015]],
    )
    dalkia_result = import_cvc_from_excel(db_session, dalkia_raw, [], city_id=1)
    assert dalkia_result.provider == PROVIDER_DALKIA

    spie_raw = _workbook_bytes(
        SPIE_HEADER,
        [_spie_row("LR/34/SETE/VILLA SALIS-MAIRIE", "VRV - UNITE EXTERIEURE", "SYSTEME DE CLIMATISATION", "VRV")],
    )
    import_cvc_from_excel(db_session, spie_raw, [], city_id=1)

    providers = [i.provider for i in db_session.scalars(select(CvcInventoryItem))]
    assert providers.count(PROVIDER_DALKIA) == 1
    assert providers.count(PROVIDER_SPIE) == 1

    # Réimport SPIE : ne doit purger que SPIE, DALKIA intact.
    import_cvc_from_excel(db_session, spie_raw, [], city_id=1)
    providers = [i.provider for i in db_session.scalars(select(CvcInventoryItem))]
    assert providers.count(PROVIDER_DALKIA) == 1
    assert providers.count(PROVIDER_SPIE) == 1

    batches = list_cvc_import_batches(db_session, city_id=1)
    assert {b.provider for b in batches} == {PROVIDER_DALKIA, PROVIDER_SPIE}
