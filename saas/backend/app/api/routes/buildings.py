from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.building import BuildingCreate, BuildingRead, BuildingUpdate, LocalCreate, LocalRead, LocalUpdate
from app.services.buildings import (
    create_building,
    create_local,
    delete_local,
    get_building_or_404,
    get_local_or_404,
    list_building_locals,
    list_buildings,
    update_building,
    update_local,
)

router = APIRouter(prefix="/buildings", tags=["buildings"])


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
