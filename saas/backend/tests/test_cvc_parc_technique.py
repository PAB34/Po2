"""Agrégation « état du parc technique » CVC.

Vérifie que le rapport s'appuie bien sur le cycle de vie calculé par équipement
(âge, durée de vie restante, criticité vs référence SYPEMI), qu'il n'agrège que
le lot d'import courant de chaque prestataire, et que la complétude de la donnée
est exposée honnêtement.
"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.db import Base
from app.models.building import Building
from app.models.city import City
from app.models.cvc import CvcInventoryItem
from app.models.equipment import EquipmentReference
from app.models.local import Local  # noqa: F401 (enregistre la table)
from app.models.site import Site  # noqa: F401
from app.services.cvc import PROVIDER_DALKIA, PROVIDER_SPIE, get_cvc_parc_technique

ANNEE = date.today().year


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(City(id=1, nom_commune="Sete", code_commune="34301"))
        session.commit()
        yield session


_REF_SEQ = iter(range(1, 1000))


def _seed_reference(db: Session, duree: int = 20) -> EquipmentReference:
    ref = EquipmentReference(
        id_ligne=next(_REF_SEQ),
        code_niveau_1="CVC",
        libelle_niveau_1="Chauffage ventilation climatisation",
        code_niveau_2="CH",
        libelle_niveau_2="Production de chaleur",
        equipement="Chaudiere",
        sypemi_reference_annees=duree,
    )
    db.add(ref)
    db.flush()
    return ref


def _add_item(
    db: Session,
    *,
    ref: EquipmentReference | None = None,
    age: int | None = None,
    building_id: int | None = None,
    famille: str = "Chaudiere",
    provider: str = PROVIDER_DALKIA,
    batch: str = "batch_1",
) -> CvcInventoryItem:
    item = CvcInventoryItem(
        city_id=1,
        building_id=building_id,
        provider=provider,
        designation="Chaudiere gaz",
        famille=famille,
        equipment_ref_id=ref.id if ref else None,
        date_mis_en_service=(ANNEE - age) if age is not None else None,
        import_batch=batch,
    )
    db.add(item)
    db.flush()
    return item


def test_rapport_vide_ne_plante_pas(db_session):
    report = get_cvc_parc_technique(db_session, city_id=1)
    assert report.equipements_total == 0
    assert report.age_moyen is None
    assert report.completude.rattachement_pct == 0.0


def test_pyramide_des_ages_et_age_moyen(db_session):
    ref = _seed_reference(db_session)
    _add_item(db_session, ref=ref, age=2)    # 0-5
    _add_item(db_session, ref=ref, age=8)    # 6-10
    _add_item(db_session, ref=ref, age=35)   # 30+
    db_session.commit()

    report = get_cvc_parc_technique(db_session, city_id=1)

    assert report.equipements_total == 3
    assert report.age_moyen == 15.0
    buckets = {b.key: b.count for b in report.ages}
    assert buckets["0_5"] == 1
    assert buckets["6_10"] == 1
    assert buckets["30_plus"] == 1


def test_fin_de_vie_et_depassement(db_session):
    ref = _seed_reference(db_session, duree=20)
    _add_item(db_session, ref=ref, age=17)   # reste 3 ans -> fin de vie < 5 ans
    _add_item(db_session, ref=ref, age=25)   # duree depassee
    _add_item(db_session, ref=ref, age=2)    # sain
    db_session.commit()

    report = get_cvc_parc_technique(db_session, city_id=1)

    assert report.fin_de_vie_5ans == 1
    assert report.depasses == 1
    criticites = {b.key: b.count for b in report.criticites}
    assert criticites["depasse"] == 1
    assert criticites["faible"] == 1  # 2/20 = 10 %


def test_equipement_sans_date_ni_reference_est_non_calculable(db_session):
    _add_item(db_session, ref=None, age=None)
    db_session.commit()

    report = get_cvc_parc_technique(db_session, city_id=1)

    assert report.equipements_total == 1
    assert report.age_moyen is None
    assert {b.key: b.count for b in report.ages}["inconnu"] == 1
    # La complétude doit le dire franchement plutôt que de masquer le trou.
    assert report.completude.date_mes_pct == 0.0
    assert report.completude.reference_pct == 0.0


def test_agregation_par_batiment_priorise_les_plus_critiques(db_session):
    ref = _seed_reference(db_session, duree=20)
    sain = Building(city_id=1, nom_batiment="Mediatheque", nom_commune="Sete")
    critique = Building(city_id=1, nom_batiment="Ecole Jean Moulin", nom_commune="Sete")
    db_session.add_all([sain, critique])
    db_session.flush()
    _add_item(db_session, ref=ref, age=2, building_id=sain.id)
    _add_item(db_session, ref=ref, age=25, building_id=critique.id)
    _add_item(db_session, ref=ref, age=18, building_id=critique.id)
    db_session.commit()

    report = get_cvc_parc_technique(db_session, city_id=1)

    assert report.batiments_couverts == 2
    assert report.par_batiment[0].nom_batiment == "Ecole Jean Moulin"
    assert report.par_batiment[0].depasses == 1
    assert report.par_batiment[0].fin_de_vie_5ans == 1


def test_seul_le_lot_courant_de_chaque_prestataire_est_agrege(db_session):
    """Garde-fou contre les doublons d'import (4 lots DALKIA identiques en juin 2026)."""
    ref = _seed_reference(db_session)
    _add_item(db_session, ref=ref, age=5, batch="import_ancien", provider=PROVIDER_DALKIA)
    _add_item(db_session, ref=ref, age=5, batch="import_recent", provider=PROVIDER_DALKIA)
    _add_item(db_session, ref=ref, age=5, batch="spie_1", provider=PROVIDER_SPIE)
    db_session.commit()

    report = get_cvc_parc_technique(db_session, city_id=1)

    # 1 DALKIA (lot courant) + 1 SPIE, l'ancien lot DALKIA est ignoré.
    assert report.equipements_total == 2
    assert {b.key: b.count for b in report.par_provider} == {PROVIDER_DALKIA: 1, PROVIDER_SPIE: 1}


def test_filtres_provider_et_famille(db_session):
    ref = _seed_reference(db_session)
    _add_item(db_session, ref=ref, age=5, famille="Chaudiere", provider=PROVIDER_DALKIA, batch="d1")
    _add_item(db_session, ref=ref, age=5, famille="Split system", provider=PROVIDER_SPIE, batch="s1")
    db_session.commit()

    assert get_cvc_parc_technique(db_session, city_id=1, provider=PROVIDER_SPIE).equipements_total == 1
    assert get_cvc_parc_technique(db_session, city_id=1, famille="Chaudiere").equipements_total == 1
