from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.building import (
    BuildingCreate,
    BuildingIgnAttachmentPayload,
    BuildingImportPreview,
    BuildingMeterLinkCreate,
    BuildingMeterLinkRead,
    BuildingNamingDataset,
    MeterMappingApplyRequest,
    MeterMappingApplyResult,
    MeterMatchResponse,
    BuildingNamingLookupRead,
    BuildingNamingSelectionPayload,
    BuildingRead,
    BuildingUpdate,
    FreeAddressLookupPayload,
    FreeAddressLookupRead,
    LocalCreate,
    LocalRead,
    LocalUpdate,
    NearbyDgfipResult,
    NearbyDgfipRow,
    PatrimonyReclassifyPayload,
    PatrimonyReclassifyResult,
    SiteCreate,
    SiteRead,
    SiteUpdate,
)
from app.services.building_naming import (
    find_nearby_dgfip_rows,
    get_building_naming_rows,
    lookup_building_candidates,
    lookup_free_address_candidates,
    preview_building_import_file,
)
from app.services.buildings import (
    attach_building_geo,
    attach_building_ign,
    create_building,
    create_building_from_naming_selection,
    create_local,
    create_building_meter_link,
    create_site,
    delete_all_buildings,
    delete_building,
    delete_local,
    delete_site,
    delete_building_meter_link,
    get_building_or_404,
    get_local_or_404,
    get_building_meter_link_or_404,
    get_site_or_404,
    list_all_locals,
    list_building_locals,
    list_building_meter_links,
    list_buildings,
    list_sites,
    reclassify_building,
    reclassify_local,
    reclassify_site,
    update_site,
    update_building,
    update_local,
)
from app.services.cities import get_city_by_id
from app.services.meter_matching import apply_meter_mappings, list_meter_matches

router = APIRouter(prefix="/buildings", tags=["buildings"])


def _raise_naming_http_error(error: ValueError) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


def _get_current_user_city_name(db: Session, current_user: User) -> str | None:
    if current_user.city_id is None:
        return None
    city = get_city_by_id(db, current_user.city_id)
    return city.nom_commune if city is not None else None


@router.get("/naming/dataset", response_model=BuildingNamingDataset)
def get_building_naming_dataset(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BuildingNamingDataset:
    try:
        city_name = _get_current_user_city_name(db, current_user)
        return BuildingNamingDataset.model_validate(get_building_naming_rows(city_name=city_name))
    except ValueError as error:
        # Cas "MAJIC non configure / introuvable" : on degrade en dataset vide
        # plutot que de spammer le frontend avec un 400. Le mode "Creation depuis
        # MAJIC" sera signale comme indisponible. Le mode "Import" continue normalement.
        message = str(error)
        majic_unavailable = (
            "DGFIP/MAJIC n'est pas configuré" in message
            or "DGFIP/MAJIC introuvable" in message
        )
        if majic_unavailable:
            return BuildingNamingDataset.model_validate({
                "filename": "",
                "columns": [],
                "mapping": {},
                "total_rows": 0,
                "unique_addresses": 0,
                "filtered_city_name": None,
                "group_person_column": "",
                "group_person_filter": "",
                "cache_status": "unavailable",
                "build_duration_ms": 0,
                "served_duration_ms": 0,
                "rows": [],
                "majic_configured": False,
                "majic_unavailable_reason": message,
            })
        _raise_naming_http_error(error)


@router.get("/naming/{unique_key}", response_model=BuildingNamingLookupRead)
def get_building_naming_lookup(
    unique_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BuildingNamingLookupRead:
    try:
        city_name = _get_current_user_city_name(db, current_user)
        return BuildingNamingLookupRead.model_validate(lookup_building_candidates(unique_key, city_name=city_name))
    except ValueError as error:
        _raise_naming_http_error(error)


@router.post("/lookup/free-address", response_model=FreeAddressLookupRead)
def post_free_address_lookup(
    payload: FreeAddressLookupPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FreeAddressLookupRead:
    try:
        city_name = _get_current_user_city_name(db, current_user)
        return FreeAddressLookupRead.model_validate(
            lookup_free_address_candidates(
                payload.address,
                city_name=city_name,
                citycode=payload.citycode,
                parcel_reference=payload.parcel_reference,
                skip_ign_buildings=payload.skip_ign_buildings,
            )
        )
    except ValueError as error:
        _raise_naming_http_error(error)


@router.post("/import/preview", response_model=BuildingImportPreview)
async def post_building_import_preview(
    file: UploadFile = File(...),
    name_column: str | None = Form(default=None),
    address_column: str | None = Form(default=None),
    validate_addresses: bool = Form(default=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BuildingImportPreview:
    city_name = _get_current_user_city_name(db, current_user)
    filename = file.filename or "import.csv"
    raw_bytes = await file.read()
    try:
        return BuildingImportPreview.model_validate(
            preview_building_import_file(
                filename=filename,
                raw_bytes=raw_bytes,
                name_column=name_column,
                address_column=address_column,
                validate_addresses=validate_addresses,
                city_name=city_name,
            )
        )
    except ValueError as error:
        _raise_naming_http_error(error)


@router.post("/naming/selection", response_model=BuildingRead, status_code=status.HTTP_201_CREATED)
def post_building_from_naming_selection(
    payload: BuildingNamingSelectionPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BuildingRead:
    try:
        building = create_building_from_naming_selection(db, payload, current_user)
        return BuildingRead.model_validate(building)
    except ValueError as error:
        _raise_naming_http_error(error)


@router.delete("", status_code=status.HTTP_200_OK)
def delete_buildings_all(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    count = delete_all_buildings(db, current_user)
    return {"deleted": count}


@router.get("", response_model=list[BuildingRead])
def get_buildings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BuildingRead]:
    return [BuildingRead.model_validate(building) for building in list_buildings(db, current_user)]


@router.get("/sites", response_model=list[SiteRead])
def get_sites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SiteRead]:
    return [SiteRead.model_validate(site) for site in list_sites(db, current_user)]


@router.get("/locals", response_model=list[LocalRead])
def get_all_locals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LocalRead]:
    """Bulk endpoint : tous les locaux visibles par l'utilisateur (filtres par city via building)."""
    return [LocalRead.model_validate(local) for local in list_all_locals(db, current_user)]


@router.post("/sites", response_model=SiteRead, status_code=status.HTTP_201_CREATED)
def post_site(
    payload: SiteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SiteRead:
    site = create_site(db, payload, current_user)
    return SiteRead.model_validate(site)


@router.put("/sites/{site_id}", response_model=SiteRead)
def put_site(
    site_id: int,
    payload: SiteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SiteRead:
    site = get_site_or_404(db, site_id, current_user)
    updated = update_site(db, site, payload)
    return SiteRead.model_validate(updated)


@router.delete("/sites/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_site(
    site_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    site = get_site_or_404(db, site_id, current_user)
    delete_site(db, site)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/sites/{site_id}/reclassify", response_model=PatrimonyReclassifyResult)
def post_site_reclassify(
    site_id: int,
    payload: PatrimonyReclassifyPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatrimonyReclassifyResult:
    site = get_site_or_404(db, site_id, current_user)
    return reclassify_site(db, site, payload, current_user)


@router.post("", response_model=BuildingRead, status_code=status.HTTP_201_CREATED)
def post_building(
    payload: BuildingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BuildingRead:
    building = create_building(db, payload, current_user)
    return BuildingRead.model_validate(building)


@router.get("/{building_id}", response_model=BuildingRead)
def get_building(
    building_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BuildingRead:
    building = get_building_or_404(db, building_id, current_user)
    return BuildingRead.model_validate(building)


@router.put("/{building_id}", response_model=BuildingRead)
def put_building(
    building_id: int,
    payload: BuildingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BuildingRead:
    building = get_building_or_404(db, building_id, current_user)
    updated_building = update_building(db, building, payload)
    return BuildingRead.model_validate(updated_building)


@router.delete("/{building_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_building(
    building_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    building = get_building_or_404(db, building_id, current_user)
    delete_building(db, building)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{building_id}/reclassify", response_model=PatrimonyReclassifyResult)
def post_building_reclassify(
    building_id: int,
    payload: PatrimonyReclassifyPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatrimonyReclassifyResult:
    building = get_building_or_404(db, building_id, current_user)
    return reclassify_building(db, building, payload, current_user)


@router.post("/{building_id}/geo-attachment", response_model=BuildingRead)
def post_building_geo_attachment(
    building_id: int,
    payload: BuildingNamingSelectionPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BuildingRead:
    try:
        building = get_building_or_404(db, building_id, current_user)
        updated_building = attach_building_geo(db, building, payload, current_user)
        return BuildingRead.model_validate(updated_building)
    except ValueError as error:
        _raise_naming_http_error(error)


@router.post("/{building_id}/ign-attachment", response_model=BuildingRead)
def post_building_ign_attachment(
    building_id: int,
    payload: BuildingIgnAttachmentPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BuildingRead:
    building = get_building_or_404(db, building_id, current_user)
    updated_building = attach_building_ign(db, building, payload)
    return BuildingRead.model_validate(updated_building)


@router.get("/{building_id}/nearby-dgfip", response_model=NearbyDgfipResult)
def get_nearby_dgfip(
    building_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NearbyDgfipResult:
    building = get_building_or_404(db, building_id, current_user)
    city_name = _get_current_user_city_name(db, current_user)
    address: str | None = None
    if building.adresse_reconstituee:
        address = building.adresse_reconstituee.strip()
    else:
        parts = [building.numero_voirie, building.nature_voie, building.nom_voie, building.nom_commune]
        clean = [p.strip() for p in parts if p and p.strip()]
        if len(clean) >= 2:
            address = " ".join(clean)
    try:
        rows = find_nearby_dgfip_rows(
            ref_lat=building.latitude,
            ref_lon=building.longitude,
            address=address,
            nom_voie=building.nom_voie,
            city_name=city_name,
        )
        return NearbyDgfipResult(
            majic_configured=True,
            majic_unavailable_reason=None,
            rows=[NearbyDgfipRow.model_validate(r) for r in rows],
        )
    except ValueError as error:
        # Cas "MAJIC non configure / introuvable" : on degrade en resultat vide
        # avec un flag explicite plutot que de renvoyer 500. Le frontend affichera
        # un message clair "Source MAJIC non disponible".
        message = str(error)
        majic_unavailable = (
            "DGFIP/MAJIC n'est pas configuré" in message
            or "DGFIP/MAJIC introuvable" in message
        )
        if majic_unavailable:
            return NearbyDgfipResult(
                majic_configured=False,
                majic_unavailable_reason=message,
                rows=[],
            )
        raise


@router.get("/{building_id}/locals", response_model=list[LocalRead])
def get_locals(
    building_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LocalRead]:
    building = get_building_or_404(db, building_id, current_user)
    return [LocalRead.model_validate(local) for local in list_building_locals(db, building)]


@router.post("/{building_id}/locals", response_model=LocalRead, status_code=status.HTTP_201_CREATED)
def post_local(
    building_id: int,
    payload: LocalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LocalRead:
    building = get_building_or_404(db, building_id, current_user)
    local = create_local(db, building, payload)
    return LocalRead.model_validate(local)


@router.put("/{building_id}/locals/{local_id}", response_model=LocalRead)
def put_local(
    building_id: int,
    local_id: int,
    payload: LocalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LocalRead:
    building = get_building_or_404(db, building_id, current_user)
    local = get_local_or_404(db, building, local_id)
    updated_local = update_local(db, local, payload)
    return LocalRead.model_validate(updated_local)


@router.delete("/{building_id}/locals/{local_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_local(
    building_id: int,
    local_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    building = get_building_or_404(db, building_id, current_user)
    local = get_local_or_404(db, building, local_id)
    delete_local(db, local)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{building_id}/locals/{local_id}/reclassify", response_model=PatrimonyReclassifyResult)
def post_local_reclassify(
    building_id: int,
    local_id: int,
    payload: PatrimonyReclassifyPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PatrimonyReclassifyResult:
    building = get_building_or_404(db, building_id, current_user)
    local = get_local_or_404(db, building, local_id)
    return reclassify_local(db, local, payload, current_user)


@router.get("/meters/matching", response_model=MeterMatchResponse)
def get_meter_matching(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MeterMatchResponse:
    """Vue d'ensemble des compteurs (PRM/PCE) avec statut de rattachement et suggestion de batiment."""
    return MeterMatchResponse(matches=list_meter_matches(db, current_user))


@router.post("/meters/matching/apply", response_model=MeterMappingApplyResult)
def post_meter_matching_apply(
    payload: MeterMappingApplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MeterMappingApplyResult:
    """Applique en masse les rattachements compteur -> batiment."""
    return apply_meter_mappings(db, current_user, payload.mappings)


@router.get("/{building_id}/meters", response_model=list[BuildingMeterLinkRead])
def get_meter_links(
    building_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BuildingMeterLinkRead]:
    building = get_building_or_404(db, building_id, current_user)
    return [BuildingMeterLinkRead.model_validate(link) for link in list_building_meter_links(db, building)]


@router.post("/{building_id}/meters", response_model=BuildingMeterLinkRead, status_code=status.HTTP_201_CREATED)
def post_meter_link(
    building_id: int,
    payload: BuildingMeterLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BuildingMeterLinkRead:
    building = get_building_or_404(db, building_id, current_user)
    meter_link = create_building_meter_link(db, building, payload)
    return BuildingMeterLinkRead.model_validate(meter_link)


@router.delete("/{building_id}/meters/{meter_link_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_meter_link(
    building_id: int,
    meter_link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    building = get_building_or_404(db, building_id, current_user)
    meter_link = get_building_meter_link_or_404(db, building, meter_link_id)
    delete_building_meter_link(db, meter_link)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
