"""Rapprochement des compteurs energie (PRM electricite, PCE gaz) au patrimoine.

Vue d'ensemble + suggestion de batiment + application en masse, calquee sur le
matching CVC site -> batiment (`services/cvc.py`). Le registre canonique du lien
est `BuildingMeterLink` (multi-fluides) ; pour le gaz on synchronise aussi
`GasPce.building_id` afin de ne pas regresser les analytics gaz.

Sources :
- PRM electricite : snapshots ENEDIS charges par `services/energie.py`
  (`_contracts()` / `_addresses()`), cles = `usage_point_id` ;
- PCE gaz : table `gas_pces` (`models/gas.py`), avec `nom_site` et `building_id`.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.building_meter import BuildingMeterLink
from app.models.gas import GasPce
from app.models.user import User
from app.schemas.building import (
    MeterBuildingSuggestion,
    MeterMappingApplyResult,
    MeterMatchResult,
)
from app.services import energie
from app.services.buildings import list_buildings
from app.services.cvc import _build_address, _similarity

# Valeurs de fluide alignees sur la saisie manuelle (BuildingDetailPage).
FLUID_ELEC = "ELECTRICITE"
FLUID_GAZ = "GAZ"

_AUTO_THRESHOLD = 0.65


def _suggest_buildings(
    query: str, buildings: list[Building]
) -> tuple[list[MeterBuildingSuggestion], int | None]:
    """Top 5 batiments par similarite nom/adresse + auto-selection si score eleve."""
    scored: list[tuple[float, Building]] = []
    for building in buildings:
        name = building.nom_batiment or ""
        address = building.adresse_reconstituee or _build_address(building) or ""
        score = max(_similarity(query, name), _similarity(query, address))
        scored.append((score, building))
    scored.sort(key=lambda item: item[0], reverse=True)

    top = scored[:5]
    suggestions = [
        MeterBuildingSuggestion(
            building_id=building.id,
            nom_batiment=building.nom_batiment,
            adresse=_build_address(building) or building.adresse_reconstituee,
            score=round(score, 3),
        )
        for score, building in top
        if score > 0.1
    ]
    auto_id = top[0][1].id if top and top[0][0] >= _AUTO_THRESHOLD else None
    return suggestions, auto_id


def _compose_elec_address(addr: dict[str, str]) -> str | None:
    parts = [
        addr.get("address_building"),
        addr.get("address_number_street_name"),
        addr.get("address_postal_code_city"),
    ]
    composed = ", ".join(part for part in parts if part)
    return composed or None


def list_meter_matches(db: Session, current_user: User) -> list[MeterMatchResult]:
    """Liste unifiee des compteurs connus avec statut de rattachement + suggestion."""
    buildings = list_buildings(db, current_user)
    building_by_id = {building.id: building for building in buildings}
    building_ids = list(building_by_id.keys())

    # Liens existants, indexes par (fluide, identifiant) -> building_id.
    links_by_key: dict[tuple[str, str], int] = {}
    if building_ids:
        for link in db.scalars(
            select(BuildingMeterLink).where(BuildingMeterLink.building_id.in_(building_ids))
        ):
            links_by_key.setdefault((link.fluid.upper(), link.meter_identifier), link.building_id)

    results: list[MeterMatchResult] = []

    # --- Electricite (PRM) ---
    contracts = energie._contracts()
    addresses = energie._addresses()
    for prm_id, contract in sorted(contracts.items()):
        addr = addresses.get(prm_id, {})
        org = contract.get("0_organization_commercial_name") or contract.get("0_organization_name")
        query = " ".join(
            part
            for part in [addr.get("address_building"), addr.get("address_number_street_name"), org]
            if part
        ) or prm_id
        suggestions, auto_id = _suggest_buildings(query, buildings)
        current = links_by_key.get((FLUID_ELEC, prm_id))
        results.append(
            MeterMatchResult(
                fluid=FLUID_ELEC,
                meter_identifier=prm_id,
                label=org or addr.get("address_building"),
                address=_compose_elec_address(addr),
                current_building_id=current,
                current_building_name=building_by_id[current].nom_batiment if current in building_by_id else None,
                suggestions=suggestions,
                auto_building_id=auto_id,
            )
        )

    # --- Gaz (PCE) ---
    for pce in db.scalars(select(GasPce).where(GasPce.city_id == current_user.city_id)):
        query = pce.nom_site or pce.id_pce
        suggestions, auto_id = _suggest_buildings(query, buildings)
        current = pce.building_id if pce.building_id in building_by_id else links_by_key.get((FLUID_GAZ, pce.id_pce))
        results.append(
            MeterMatchResult(
                fluid=FLUID_GAZ,
                meter_identifier=pce.id_pce,
                label=pce.nom_site,
                address=None,
                current_building_id=current,
                current_building_name=building_by_id[current].nom_batiment if current in building_by_id else None,
                suggestions=suggestions,
                auto_building_id=auto_id,
            )
        )

    return results


def apply_meter_mappings(db: Session, current_user: User, mappings) -> MeterMappingApplyResult:
    """Applique les rattachements compteur -> batiment (un batiment canonique par compteur)."""
    building_by_id = {building.id: building for building in list_buildings(db, current_user)}
    building_ids = list(building_by_id.keys())

    applied = 0
    moved = 0
    for mapping in mappings:
        if mapping.building_id is None:
            continue
        building = building_by_id.get(mapping.building_id)
        if building is None:
            continue  # batiment hors perimetre ville : ignore silencieusement

        fluid = mapping.fluid.strip().upper()
        identifier = mapping.meter_identifier.strip()
        if not identifier:
            continue

        # Canonique : un seul lien (fluide, identifiant) dans la ville.
        existing = list(
            db.scalars(
                select(BuildingMeterLink).where(
                    BuildingMeterLink.fluid == fluid,
                    BuildingMeterLink.meter_identifier == identifier,
                    BuildingMeterLink.building_id.in_(building_ids or [-1]),
                )
            )
        )
        chosen: BuildingMeterLink | None = None
        for link in existing:
            if link.building_id == building.id:
                chosen = link
            else:
                db.delete(link)
                moved += 1

        if chosen is None:
            chosen = BuildingMeterLink(
                building_id=building.id,
                fluid=fluid,
                meter_identifier=identifier,
                source="MATCHING",
                confidence="A_VALIDER",
                validation_status="VALIDE",
            )
            db.add(chosen)
        else:
            chosen.validation_status = "VALIDE"
        if mapping.meter_label:
            chosen.meter_label = mapping.meter_label[:255]

        # Gaz : synchroniser le lien direct sur le PCE.
        if fluid == FLUID_GAZ:
            pce = db.scalar(
                select(GasPce).where(
                    GasPce.city_id == current_user.city_id,
                    GasPce.id_pce == identifier,
                )
            )
            if pce is not None:
                pce.building_id = building.id

        applied += 1

    db.commit()
    return MeterMappingApplyResult(applied=applied, updated=moved)
