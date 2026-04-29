from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.building import (
    BuildingCreate,
    BuildingIgnAttachmentPayload,
    BuildingImportPreview,
    BuildingNamingDataset,
    BuildingNamingLookupRead,
    BuildingNamingSelectionPayload,
    BuildingRead,
    BuildingUpdate,
    FreeAddressLookupPayload,
    FreeAddressLookupRead,
    LocalCreate,
    LocalRead,
    LocalUpdate,
    NearbyDgfipRow,
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
    delete_all_buildings,
    delete_local,
    get_building_or_404,
    get_local_or_404,
    list_building_locals,
    list_buildings,
    update_building,
    update_local,
)
from app.services.cities import get_city_by_id

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
        return FreeAddressLookupRead.model_validate(lookup_free_address_candidates(payload.address, city_name=city_name))
    except ValueError as error:
        _raise_naming_http_error(error)


@router.post("/import/preview", response_model=BuildingImportPreview)
async def post_building_import_preview(
    file: UploadFile = File(...),
    name_column: str | None = Form(default=None),
    address_column: str | None = Form(default=None),
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


@router.get("/{building_id}/nearby-dgfip", response_model=list[NearbyDgfipRow])
def get_nearby_dgfip(
    building_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NearbyDgfipRow]:
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
    rows = find_nearby_dgfip_rows(
        ref_lat=building.latitude,
        ref_lon=building.longitude,
        address=address,
        nom_voie=building.nom_voie,
        city_name=city_name,
    )
    return [NearbyDgfipRow.model_validate(r) for r in rows]


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
