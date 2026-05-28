from fastapi import HTTPException, status
import json
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.building_meter import BuildingMeterLink
from app.models.city import City
from app.models.local import Local
from app.models.site import Site
from app.models.user import User
from app.schemas.building import BuildingCreate, BuildingIgnAttachmentPayload, BuildingMeterLinkCreate, BuildingNamingSelectionPayload, BuildingUpdate, LocalCreate, LocalUpdate, SiteCreate, SiteUpdate
from app.services.building_naming import _dedupe_candidate_dicts, build_building_payload
from app.services.cities import get_city_by_id


def list_buildings(db: Session, current_user: User) -> list[Building]:
    statement = select(Building).order_by(Building.created_at.desc())
    if current_user.city_id is not None:
        statement = statement.where(Building.city_id == current_user.city_id)
    return list(db.scalars(statement))


def _normalize_lookup(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def list_sites(db: Session, current_user: User) -> list[Site]:
    statement = select(Site).order_by(Site.nom_site.asc())
    if current_user.city_id is not None:
        statement = statement.where(Site.city_id == current_user.city_id)
    return list(db.scalars(statement))


def get_site_or_404(db: Session, site_id: int, current_user: User) -> Site:
    statement = select(Site).where(Site.id == site_id)
    site = db.scalar(statement)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site introuvable.")
    if current_user.city_id is not None and site.city_id != current_user.city_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces au site refuse.")
    return site


def create_site(db: Session, payload: SiteCreate, current_user: User) -> Site:
    city_id = current_user.city_id if current_user.city_id is not None else payload.city_id
    if city_id is not None and get_city_by_id(db, city_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ville inconnue.")
    nom_site = payload.nom_site.strip()
    for site in list_sites(db, current_user):
        if site.city_id == city_id and _normalize_lookup(site.nom_site) == _normalize_lookup(nom_site):
            if payload.adresse and not site.adresse:
                site.adresse = payload.adresse.strip()
            if payload.source_file and not site.source_file:
                site.source_file = payload.source_file.strip()
            if payload.source_rows_json and not site.source_rows_json:
                site.source_rows_json = payload.source_rows_json.strip()
            db.add(site)
            db.commit()
            db.refresh(site)
            return site
    site = Site(
        city_id=city_id,
        nom_site=nom_site,
        adresse=payload.adresse.strip() if payload.adresse else None,
        source_file=payload.source_file.strip() if payload.source_file else None,
        source_rows_json=payload.source_rows_json.strip() if payload.source_rows_json else None,
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def update_site(db: Session, site: Site, payload: SiteUpdate) -> Site:
    if payload.nom_site is not None:
        site.nom_site = payload.nom_site.strip()
    if payload.adresse is not None:
        site.adresse = payload.adresse.strip() if payload.adresse else None
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


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
    building.site_id = payload.site_id
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
    building.ign_features_json = payload.ign_features_json.strip() if payload.ign_features_json else None
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
    if payload.site_id is not None:
        site = get_site_or_404(db, payload.site_id, current_user)
        if city is not None and site.city_id is not None and site.city_id != city.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le site n'appartient pas a la ville du batiment.")

    building = _apply_building_payload(Building(city_id=city.id if city else None), payload, nom_commune)
    db.add(building)
    db.flush()

    if payload.create_default_local:
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
        selected_features=[dict(f) for f in (payload.selected_features or []) if isinstance(f, dict)] or None,
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
        ign_features_json=generated_payload.get("ign_features_json"),
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
        selected_features=[dict(f) for f in (payload.selected_features or []) if isinstance(f, dict)] or None,
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
        ign_features_json=generated_payload.get("ign_features_json"),
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
    # Resolution multi-features :
    # - payload.selected_features (liste, nouvelle API) si fourni
    # - sinon retro-compat avec payload.selected_feature (singulier)
    features_list: list[dict[str, object]] = []
    if payload.selected_features:
        features_list = [f for f in payload.selected_features if isinstance(f, dict)]
    elif payload.selected_feature:
        features_list = [payload.selected_feature]

    # 1er feature = principal (alimente les champs ign_* legacy)
    primary_feature = features_list[0] if features_list else None
    feature_properties = (primary_feature or {}).get("properties", {}) or {}
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
    if primary_feature:
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
        # Stockage de la liste complete des batiments IGN (incluant le principal)
        building.ign_features_json = json.dumps(features_list, ensure_ascii=False) if features_list else None
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


def list_all_locals(db: Session, current_user: User) -> list[Local]:
    """Liste tous les locaux visibles par l'utilisateur (filtres par city_id via building.city_id)."""
    statement = select(Local).join(Building, Local.building_id == Building.id).order_by(Local.created_at.asc())
    if current_user.city_id is not None:
        statement = statement.where(Building.city_id == current_user.city_id)
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


def list_building_meter_links(db: Session, building: Building) -> list[BuildingMeterLink]:
    statement = (
        select(BuildingMeterLink)
        .where(BuildingMeterLink.building_id == building.id)
        .order_by(BuildingMeterLink.fluid.asc(), BuildingMeterLink.meter_identifier.asc())
    )
    return list(db.scalars(statement))


def get_building_meter_link_or_404(db: Session, building: Building, meter_link_id: int) -> BuildingMeterLink:
    statement = select(BuildingMeterLink).where(
        BuildingMeterLink.id == meter_link_id,
        BuildingMeterLink.building_id == building.id,
    )
    meter_link = db.scalar(statement)
    if meter_link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rattachement compteur introuvable.")
    return meter_link


def _clean_meter_link_text(value: str | None) -> str | None:
    return value.strip() if value and value.strip() else None


def create_building_meter_link(
    db: Session,
    building: Building,
    payload: BuildingMeterLinkCreate,
) -> BuildingMeterLink:
    valid_from = payload.valid_from
    valid_to = payload.valid_to
    if valid_from and valid_to and valid_to < valid_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La fin de validite du rattachement doit suivre son debut.",
        )

    fluid = payload.fluid.strip().upper()
    meter_identifier = payload.meter_identifier.strip()
    duplicate = db.scalar(
        select(BuildingMeterLink).where(
            BuildingMeterLink.building_id == building.id,
            BuildingMeterLink.fluid == fluid,
            BuildingMeterLink.meter_identifier == meter_identifier,
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce compteur est deja rattache a ce batiment pour ce fluide.",
        )

    meter_link = BuildingMeterLink(
        building_id=building.id,
        fluid=fluid,
        meter_identifier=meter_identifier,
        meter_label=_clean_meter_link_text(payload.meter_label),
        usage_label=_clean_meter_link_text(payload.usage_label),
        share_ratio=payload.share_ratio,
        valid_from=valid_from,
        valid_to=valid_to,
        confidence=payload.confidence.strip().upper(),
        validation_status=payload.validation_status.strip().upper(),
        source=payload.source.strip(),
        contract_context=_clean_meter_link_text(payload.contract_context),
        supplier_name=_clean_meter_link_text(payload.supplier_name),
        notes=_clean_meter_link_text(payload.notes),
    )
    db.add(meter_link)
    db.commit()
    db.refresh(meter_link)
    return meter_link


def delete_building_meter_link(db: Session, meter_link: BuildingMeterLink) -> None:
    db.delete(meter_link)
    db.commit()
