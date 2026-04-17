from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BuildingCreate(BaseModel):
    city_id: int | None = None
    nom_batiment: str | None = Field(default=None, max_length=255)
    nom_commune: str | None = Field(default=None, max_length=255)
    numero_voirie: str | None = Field(default=None, max_length=40)
    nature_voie: str | None = Field(default=None, max_length=80)
    nom_voie: str | None = Field(default=None, max_length=255)
    prefixe: str | None = Field(default=None, max_length=20)
    section: str | None = Field(default=None, max_length=40)
    numero_plan: str | None = Field(default=None, max_length=40)
    adresse_reconstituee: str | None = Field(default=None, max_length=255)
    latitude: float | None = None
    longitude: float | None = None


class BuildingUpdate(BaseModel):
    nom_batiment: str | None = Field(default=None, max_length=255)
    numero_voirie: str | None = Field(default=None, max_length=40)
    nature_voie: str | None = Field(default=None, max_length=80)
    nom_voie: str | None = Field(default=None, max_length=255)
    prefixe: str | None = Field(default=None, max_length=20)
    section: str | None = Field(default=None, max_length=40)
    numero_plan: str | None = Field(default=None, max_length=40)
    adresse_reconstituee: str | None = Field(default=None, max_length=255)
    latitude: float | None = None
    longitude: float | None = None


class BuildingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city_id: int | None
    nom_batiment: str | None
    nom_commune: str
    numero_voirie: str | None
    nature_voie: str | None
    nom_voie: str | None
    prefixe: str | None
    section: str | None
    numero_plan: str | None
    adresse_reconstituee: str | None
    latitude: float | None
    longitude: float | None
    source_creation: str
    statut_geocodage: str
    created_at: datetime
    updated_at: datetime


class LocalCreate(BaseModel):
    nom_local: str = Field(min_length=1, max_length=255)
    type_local: str = Field(min_length=1, max_length=80)
    niveau: str | None = Field(default=None, max_length=40)
    surface_m2: float | None = None
    usage: str | None = Field(default=None, max_length=120)
    statut_occupation: str | None = Field(default=None, max_length=120)
    commentaire: str | None = Field(default=None, max_length=500)


class LocalUpdate(BaseModel):
    nom_local: str | None = Field(default=None, min_length=1, max_length=255)
    type_local: str | None = Field(default=None, min_length=1, max_length=80)
    niveau: str | None = Field(default=None, max_length=40)
    surface_m2: float | None = None
    usage: str | None = Field(default=None, max_length=120)
    statut_occupation: str | None = Field(default=None, max_length=120)
    commentaire: str | None = Field(default=None, max_length=500)


class LocalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    building_id: int
    nom_local: str
    type_local: str
    niveau: str | None
    surface_m2: float | None
    usage: str | None
    statut_occupation: str | None
    commentaire: str | None
    created_at: datetime
    updated_at: datetime
