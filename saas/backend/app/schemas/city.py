from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom_commune: str
    code_commune: str | None
    code_postal: str | None
    latitude: float | None
    longitude: float | None
    source_file: str | None
    created_at: datetime
