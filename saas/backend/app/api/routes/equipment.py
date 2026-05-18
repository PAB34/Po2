from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.equipment import (
    BuildingEquipmentBulkCreate,
    BuildingEquipmentCreate,
    BuildingEquipmentRead,
    BuildingEquipmentSummary,
    BuildingEquipmentUpdate,
    EquipmentReferenceRead,
    EquipmentStateCounts,
)
from app.services.buildings import get_building_or_404, list_buildings
from app.services.equipment import (
    bulk_create_building_equipments,
    compute_all_buildings_summaries,
    compute_building_equipment_summary,
    create_building_equipment,
    delete_building_equipment,
    get_building_equipment_or_none,
    list_building_equipments,
    list_equipment_references,
    update_building_equipment,
)

router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.get("/references", response_model=list[EquipmentReferenceRead])
def get_references(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EquipmentReferenceRead]:
    refs = list_equipment_references(db)
    return [EquipmentReferenceRead.model_validate(r) for r in refs]


@router.get("/summaries", response_model=list[BuildingEquipmentSummary])
def get_all_summaries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BuildingEquipmentSummary]:
    buildings = list_buildings(db, current_user)
    building_ids = [b.id for b in buildings]
    summaries = compute_all_buildings_summaries(db, building_ids)
    result = []
    for bid in building_ids:
        counts = summaries.get(bid, EquipmentStateCounts())
        result.append(BuildingEquipmentSummary(building_id=bid, counts=counts))
    return result


@router.get("/buildings/{building_id}", response_model=list[BuildingEquipmentRead])
def get_building_equipment_list(
    building_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BuildingEquipmentRead]:
    get_building_or_404(db, building_id, current_user)
    items = list_building_equipments(db, building_id)
    return [BuildingEquipmentRead.model_validate(item) for item in items]


@router.post("/buildings/{building_id}", response_model=BuildingEquipmentRead, status_code=status.HTTP_201_CREATED)
def post_building_equipment(
    building_id: int,
    payload: BuildingEquipmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BuildingEquipmentRead:
    get_building_or_404(db, building_id, current_user)
    try:
        be = create_building_equipment(db, building_id, payload)
        return BuildingEquipmentRead.model_validate(be)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/buildings/{building_id}/bulk", response_model=list[BuildingEquipmentRead], status_code=status.HTTP_201_CREATED)
def post_building_equipment_bulk(
    building_id: int,
    payload: BuildingEquipmentBulkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BuildingEquipmentRead]:
    get_building_or_404(db, building_id, current_user)
    try:
        created = bulk_create_building_equipments(db, building_id, payload.items)
        return [BuildingEquipmentRead.model_validate(be) for be in created]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/buildings/{building_id}/{equipment_id}", response_model=BuildingEquipmentRead)
def put_building_equipment(
    building_id: int,
    equipment_id: int,
    payload: BuildingEquipmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BuildingEquipmentRead:
    get_building_or_404(db, building_id, current_user)
    be = get_building_equipment_or_none(db, building_id, equipment_id)
    if be is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Équipement introuvable.")
    updated = update_building_equipment(db, be, payload)
    return BuildingEquipmentRead.model_validate(updated)


@router.delete("/buildings/{building_id}/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_building_equipment(
    building_id: int,
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    get_building_or_404(db, building_id, current_user)
    be = get_building_equipment_or_none(db, building_id, equipment_id)
    if be is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Équipement introuvable.")
    delete_building_equipment(db, be)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/buildings/{building_id}/summary", response_model=EquipmentStateCounts)
def get_building_equipment_summary(
    building_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EquipmentStateCounts:
    get_building_or_404(db, building_id, current_user)
    return compute_building_equipment_summary(db, building_id)
