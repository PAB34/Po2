from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.city import City


def list_cities(db: Session) -> list[City]:
    statement = select(City).order_by(City.nom_commune.asc())
    return list(db.scalars(statement))


def get_city_by_id(db: Session, city_id: int) -> City | None:
    statement = select(City).where(City.id == city_id)
    return db.scalar(statement)
