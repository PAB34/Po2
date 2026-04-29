from fastapi import HTTPException, status
import json
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.city import City
from app.models.local import Local
from app.models.user import User
from app.schemas.building import BuildingCreate, BuildingIgnAttachmentPayload, BuildingNamingSelectionPayload, BuildingUpdate, LocalCreate, LocalUpdate
from app.services.building_naming import _dedupe_candidate_dicts, build_building_payload
from app.services.cities import get_city_by_id


def list_buildings(db: Session, current_user: User) -> list[Building]:
    statement = select(Building).order_by(Building.created_at.desc())
    if current_user.city_id is not None:
        statement = statement.where(Building.city_id == current_user.city_id)
    return list(db.scalars(statement))


def get_building_or_404(db: Session, building_id: int, current_user: User) -> Building:
    statement = select(Building).where(Building.id == building_id)
    building = db.scalar(statement)
    if building is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bâtiment introuvable.")
    if current_user.city_id is not None and building.city_id != current_user.city_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès au bâtiment refusé.")
    return building


def _resolve_city(db: Session, payload: BuildingCreate, current_user: User) -> City | None:
    city_id = current_user.city_id if current_user.city_id is not None else payload.city_id
    if city_id is None:
        return None
    city = get_city_by_id(db, city_id)
    if city is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ville inconnue.")
    return city


def _build_default_local_name(building: Building) -> str:
    return building.nom_batiment or "Local principal"


def _apply_building_payload(building: Building, payload: BuildingCreate, nom_commune: str) -> Building:
    building.dgfip_unique_key = payload.dgfip_unique_key.strip() if payload.dgfip_unique_key else None
    building.dgfip_source_file = payload.dgfip_source_file.strip() if payload.dgfip_source_file else None
    building.dgfip_source_rows_json = payload.dgfip_source_rows_json.strip() if payload.dgfip_source_rows_json else None
    building.dgfip_reference_norm = payload.dgfip_reference_norm.strip() if payload.dgfip_reference_norm else None
    building.nom_batiment = payload.nom_batiment.strip() if payload.nom_batiment else None
    building.nom_commune = nom_commune
    building.numero_voirie = payload.numero_voirie.strip() if payload.numero_voirie else None
    building.indice_repetition = payload.indice_repetition.strip() if payload.indice_repetition else None
    building.nature_voie = payload.nature_voie.strip() if payload.nature_voie else None
    building.nom_voie = payload.nom_voie.strip() if payload.nom_voie else None
    building.prefixe = payload.prefixe.strip() if payload.prefixe else None
    building.section = payload.section.strip() if payload.section else None
    building.numero_plan = payload.numero_plan.strip() if payload.numero_plan else None
    building.adresse_reconstituee = payload.adresse_reconstituee.strip() if payload.adresse_reconstituee else None
    building.latitude = payload.latitude
    building.longitude = payload.longitude
    building.ign_layer = payload.ign_layer.strip() if payload.ign_layer else None
    building.ign_typename = payload.ign_typename.strip() if payload.ign_typename else None
    building.ign_id = payload.ign_id.strip() if payload.ign_id else None
    building.ign_name = payload.ign_name.strip() if payload.ign_name else None
    building.ign_label = payload.ign_label.strip() if payload.ign_label else None
    building.ign_name_proposed = payload.ign_name_proposed.strip() if payload.ign_name_proposed else None
    building.ign_name_source = payload.ign_name_source.strip() if payload.ign_name_source else None
    building.ign_name_distance_m = payload.ign_name_distance_m
    building.ign_attributes_json = payload.ign_attributes_json.strip() if payload.ign_attributes_json else None
    building.ign_toponym_candidates_json = (
        payload.ign_toponym_candidates_json.strip() if payload.ign_toponym_candidates_json else None
    )
    building.parcel_labels_json = payload.parcel_labels_json.strip() if payload.parcel_labels_json else None
    building.majic_building_values_json = payload.majic_building_values_json.strip() if payload.majic_building_values_json else None
    building.majic_entry_values_json = payload.majic_entry_values_json.strip() if payload.majic_entry_values_json else None
    building.majic_level_values_json = payload.majic_level_values_json.strip() if payload.majic_level_values_json else None
    building.majic_door_values_json = payload.majic_door_values_json.strip() if payload.majic_door_values_json else None
    building.source_creation = payload.source_creation or building.source_creation or "MANUEL"
    building.statut_geocodage = payload.statut_geocodage or building.statut_geocodage or "NON_FAIT"
    return building


def create_building(db: Session, payload: BuildingCreate, current_user: User) -> Building:
    city = _resolve_city(db, payload, current_user)
    nom_commune = city.nom_commune if city else (payload.nom_commune.strip() if payload.nom_commune else None)
    if nom_commune is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La commune est obligatoire.")

    building = _apply_building_payload(Building(city_id=city.id if city else None), payload, nom_commune)
    db.add(building)
    db.flush()

    default_local = Local(
        building_id=building.id,
        nom_local=_build_default_local_name(building),
        type_local="PRINCIPAL",
    )
    db.add(default_local)
    db.commit()
    db.refresh(building)
    return building


def create_building_from_naming_selection(
    db: Session,
    payload: BuildingNamingSelectionPayload,
    current_user: User,
) -> Building:
    target_city_id = current_user.city_id if current_user.city_id is not None else payload.city_id
    target_city = get_city_by_id(db, target_city_id) if target_city_id is not None else None
    target_city_name = target_city.nom_commune if target_city is not None else None
    generated_payload = build_building_payload(
        unique_key=payload.unique_key,
        selected_feature=dict(payload.selected_feature) if payload.selected_feature else None,
        validated_name=payload.validated_name,
        city_name=target_city_name,
    )
    existing_statement = select(Building).where(Building.dgfip_unique_key == generated_payload["unique_key"])
    if target_city_id is not None:
        existing_statement = existing_statement.where(Building.city_id == target_city_id)
    existing_building = db.scalar(existing_statement)
    if existing_building is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette adresse DGFIP a déjà été transformée en bâtiment dans votre périmètre.",
        )

    building_payload = BuildingCreate(
        city_id=target_city_id,
        dgfip_unique_key=generated_payload["unique_key"],
        dgfip_source_file=generated_payload["source_file"],
        dgfip_source_rows_json=json.dumps(generated_payload["source_rows"], ensure_ascii=False),
        dgfip_reference_norm=generated_payload["reference_norm"],
        nom_batiment=generated_payload["nom_batiment"],
        nom_commune=generated_payload["nom_commune"],
        numero_voirie=generated_payload["numero_voirie"],
        indice_repetition=generated_payload["indice_repetition"],
        nature_voie=generated_payload["nature_voie"],
        nom_voie=generated_payload["nom_voie"],
        prefixe=generated_payload["prefixe"],
        section=generated_payload["section"],
        numero_plan=generated_payload["numero_plan"],
        adresse_reconstituee=generated_payload["adresse_reconstituee"],
        latitude=generated_payload["latitude"],
        longitude=generated_payload["longitude"],
        ign_layer=generated_payload["ign_layer"],
        ign_typename=generated_payload["ign_typename"],
        ign_id=generated_payload["ign_id"],
        ign_name=generated_payload["ign_name"],
        ign_label=generated_payload["ign_label"],
        ign_name_proposed=generated_payload["ign_name_proposed"],
        ign_name_source=generated_payload["ign_name_source"],
        ign_name_distance_m=generated_payload["ign_name_distance_m"],
        ign_attributes_json=generated_payload["ign_attributes_json"],
        ign_toponym_candidates_json=generated_payload["ign_toponym_candidates_json"],
        parcel_labels_json=generated_payload["parcel_labels_json"],
        majic_building_values_json=generated_payload["majic_building_values_json"],
        majic_entry_values_json=generated_payload["majic_entry_values_json"],
        majic_level_values_json=generated_payload["majic_level_values_json"],
        majic_door_values_json=generated_payload["majic_door_values_json"],
        source_creation=generated_payload["source_creation"],
        statut_geocodage=generated_payload["statut_geocodage"],
    )
    return create_building(db, building_payload, current_user)


def attach_building_geo(
    db: Session,
    building: Building,
    payload: BuildingNamingSelectionPayload,
    current_user: User,
) -> Building:
    target_city_id = building.city_id or current_user.city_id or payload.city_id
    target_city = get_city_by_id(db, target_city_id) if target_city_id is not None else None
    target_city_name = target_city.nom_commune if target_city is not None else building.nom_commune
    generated_payload = build_building_payload(
        unique_key=payload.unique_key,
        selected_feature=dict(payload.selected_feature) if payload.selected_feature else None,
        validated_name=payload.validated_name,
        city_name=target_city_name,
    )
    existing_statement = select(Building).where(
        Building.dgfip_unique_key == generated_payload["unique_key"],
        Building.id != building.id,
    )
    if target_city_id is not None:
        existing_statement = existing_statement.where(Building.city_id == target_city_id)
    existing_building = db.scalar(existing_statement)
    if existing_building is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette adresse DGFIP est déjà rattachée à un autre bâtiment dans votre périmètre.",
        )

    building_payload = BuildingCreate(
        city_id=target_city_id,
        dgfip_unique_key=generated_payload["unique_key"],
        dgfip_source_file=generated_payload["source_file"],
        dgfip_source_rows_json=json.dumps(generated_payload["source_rows"], ensure_ascii=False),
        dgfip_reference_norm=generated_payload["reference_norm"],
        nom_batiment=generated_payload["nom_batiment"] or building.nom_batiment,
        nom_commune=generated_payload["nom_commune"] or building.nom_commune,
        numero_voirie=generated_payload["numero_voirie"],
        indice_repetition=generated_payload["indice_repetition"],
        nature_voie=generated_payload["nature_voie"],
        nom_voie=generated_payload["nom_voie"],
        prefixe=generated_payload["prefixe"],
        section=generated_payload["section"],
        numero_plan=generated_payload["numero_plan"],
        adresse_reconstituee=generated_payload["adresse_reconstituee"],
        latitude=generated_payload["latitude"],
        longitude=generated_payload["longitude"],
        ign_layer=generated_payload["ign_layer"],
        ign_typename=generated_payload["ign_typename"],
        ign_id=generated_payload["ign_id"],
        ign_name=generated_payload["ign_name"],
        ign_label=generated_payload["ign_label"],
        ign_name_proposed=generated_payload["ign_name_proposed"],
        ign_name_source=generated_payload["ign_name_source"],
        ign_name_distance_m=generated_payload["ign_name_distance_m"],
        ign_attributes_json=generated_payload["ign_attributes_json"],
        ign_toponym_candidates_json=generated_payload["ign_toponym_candidates_json"],
        parcel_labels_json=generated_payload["parcel_labels_json"],
        majic_building_values_json=generated_payload["majic_building_values_json"],
        majic_entry_values_json=generated_payload["majic_entry_values_json"],
        majic_level_values_json=generated_payload["majic_level_values_json"],
        majic_door_values_json=generated_payload["majic_door_values_json"],
        source_creation=building.source_creation,
        statut_geocodage=generated_payload["statut_geocodage"],
    )
    updated_building = _apply_building_payload(building, building_payload, target_city_name or building.nom_commune)
    updated_building.city_id = target_city_id
    db.add(updated_building)
    db.commit()
    db.refresh(updated_building)
    return updated_building


def attach_building_ign(
    db: Session,
    building: Building,
    payload: BuildingIgnAttachmentPayload,
) -> Building:
    feature_properties = (payload.selected_feature or {}).get("properties", {}) or {}
    attributes = feature_properties.get("attributes", {}) or {}
    resolved_candidates = _dedupe_candidate_dicts(feature_properties.get("resolved_name_candidates") or [])

    proposed_name = str(
        payload.validated_name
        or feature_properties.get("resolved_name")
        or feature_properties.get("name")
        or building.nom_batiment
        or ""
    ).strip()

    if proposed_name:
        building.nom_batiment = proposed_name
    if payload.selected_feature:
        building.ign_layer = feature_properties.get("ign_layer")
        building.ign_typename = feature_properties.get("ign_typename")
        building.ign_id = feature_properties.get("ign_id")
        building.ign_name = feature_properties.get("name")
        building.ign_label = feature_properties.get("label")
        building.ign_name_proposed = feature_properties.get("resolved_name")
        building.ign_name_source = feature_properties.get("resolved_name_source")
        building.ign_name_distance_m = feature_properties.get("resolved_name_distance_m")
        building.ign_attributes_json = json.dumps(attributes, ensure_ascii=False) if attributes else None
        building.ign_toponym_candidates_json = json.dumps(resolved_candidates, ensure_ascii=False) if resolved_candidates else None
        building.statut_geocodage = "IGN_VALIDE"
    if payload.lat is not None:
        building.latitude = payload.lat
    if payload.lon is not None:
        building.longitude = payload.lon

    db.add(building)
    db.commit()
    db.refresh(building)
    return building


def update_building(db: Session, building: Building, payload: BuildingUpdate) -> Building:
    building.nom_batiment = payload.nom_batiment.strip() if payload.nom_batiment else None
    if payload.nom_commune:
        building.nom_commune = payload.nom_commune.strip()
    building.code_postal = payload.code_postal.strip() if payload.code_postal else None
    building.numero_voirie = payload.numero_voirie.strip() if payload.numero_voirie else None
    building.indice_repetition = payload.indice_repetition.strip() if payload.indice_repetition else None
    building.nature_voie = payload.nature_voie.strip() if payload.nature_voie else None
    building.nom_voie = payload.nom_voie.strip() if payload.nom_voie else None
    building.prefixe = payload.prefixe.strip() if payload.prefixe else None
    building.section = payload.section.strip() if payload.section else None
    building.numero_plan = payload.numero_plan.strip() if payload.numero_plan else None
    building.adresse_reconstituee = payload.adresse_reconstituee.strip() if payload.adresse_reconstituee else None
    building.latitude = payload.latitude
    building.longitude = payload.longitude
    db.add(building)
    db.commit()
    db.refresh(building)
    return building


def list_building_locals(db: Session, building: Building) -> list[Local]:
    statement = select(Local).where(Local.building_id == building.id).order_by(Local.created_at.asc())
    return list(db.scalars(statement))


def get_local_or_404(db: Session, building: Building, local_id: int) -> Local:
    statement = select(Local).where(Local.id == local_id, Local.building_id == building.id)
    local = db.scalar(statement)
    if local is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Local introuvable.")
    return local


def create_local(db: Session, building: Building, payload: LocalCreate) -> Local:
    local = Local(
        building_id=building.id,
        nom_local=payload.nom_local.strip(),
        type_local=payload.type_local.strip(),
        niveau=payload.niveau.strip() if payload.niveau else None,
        surface_m2=payload.surface_m2,
        usage=payload.usage.strip() if payload.usage else None,
        statut_occupation=payload.statut_occupation.strip() if payload.statut_occupation else None,
        commentaire=payload.commentaire.strip() if payload.commentaire else None,
    )
    db.add(local)
    db.commit()
    db.refresh(local)
    return local


def update_local(db: Session, local: Local, payload: LocalUpdate) -> Local:
    if payload.nom_local is not None:
        local.nom_local = payload.nom_local.strip()
    if payload.type_local is not None:
        local.type_local = payload.type_local.strip()
    local.niveau = payload.niveau.strip() if payload.niveau else None
    local.surface_m2 = payload.surface_m2
    local.usage = payload.usage.strip() if payload.usage else None
    local.statut_occupation = payload.statut_occupation.strip() if payload.statut_occupation else None
    local.commentaire = payload.commentaire.strip() if payload.commentaire else None
    db.add(local)
    db.commit()
    db.refresh(local)
    return local


def delete_all_buildings(db: Session, current_user: User) -> int:
    statement = select(Building)
    if current_user.city_id is not None:
        statement = statement.where(Building.city_id == current_user.city_id)
    buildings = list(db.scalars(statement))
    for building in buildings:
        db.delete(building)
    db.commit()
    return len(buildings)


def delete_local(db: Session, local: Local) -> None:
    db.delete(local)
    db.commit()
