from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.city import CityRead
from app.services.cities import list_cities

router = APIRouter(prefix="/cities", tags=["cities"])


@router.get("", response_model=list[CityRead])
def get_cities(db: Session = Depends(get_db)) -> list[CityRead]:
    return [CityRead.model_validate(city) for city in list_cities(db)]
