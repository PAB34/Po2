from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.city import City
from app.models.local import Local
from app.models.user import User
from app.schemas.building import BuildingCreate, BuildingUpdate, LocalCreate, LocalUpdate
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


def create_building(db: Session, payload: BuildingCreate, current_user: User) -> Building:
    city = _resolve_city(db, payload, current_user)
    nom_commune = city.nom_commune if city else (payload.nom_commune.strip() if payload.nom_commune else None)
    if nom_commune is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La commune est obligatoire.")

    building = Building(
        city_id=city.id if city else None,
        nom_batiment=payload.nom_batiment.strip() if payload.nom_batiment else None,
        nom_commune=nom_commune,
        numero_voirie=payload.numero_voirie.strip() if payload.numero_voirie else None,
        nature_voie=payload.nature_voie.strip() if payload.nature_voie else None,
        nom_voie=payload.nom_voie.strip() if payload.nom_voie else None,
        prefixe=payload.prefixe.strip() if payload.prefixe else None,
        section=payload.section.strip() if payload.section else None,
        numero_plan=payload.numero_plan.strip() if payload.numero_plan else None,
        adresse_reconstituee=payload.adresse_reconstituee.strip() if payload.adresse_reconstituee else None,
        latitude=payload.latitude,
        longitude=payload.longitude,
        source_creation="MANUEL",
        statut_geocodage="NON_FAIT",
    )
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


def update_building(db: Session, building: Building, payload: BuildingUpdate) -> Building:
    building.nom_batiment = payload.nom_batiment.strip() if payload.nom_batiment else None
    building.numero_voirie = payload.numero_voirie.strip() if payload.numero_voirie else None
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


def delete_local(db: Session, local: Local) -> None:
    db.delete(local)
    db.commit()
