from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BuildingNamingCandidate(BaseModel):
    name: str
    label: str | None = None
    source: str | None = None
    typename: str | None = None
    id: str | None = None
    distance_m: float | None = None


class BuildingNamingRow(BaseModel):
    unique_key: str
    address_display: str
    duplicate_count: int
    source_rows: list[int]
    reference_count: int
    references: list[str]
    first_reference_norm: str
    nom_commune: str
    numero_voirie: str | None = None
    indice_repetition: str | None = None
    nature_voie: str | None = None
    nom_voie: str | None = None
    prefixe: str | None = None
    section: str | None = None
    numero_plan: str | None = None
    majic_building_values: list[str]
    majic_entry_values: list[str]
    majic_level_values: list[str]
    majic_door_values: list[str]


class BuildingNamingDataset(BaseModel):
    filename: str
    columns: list[str]
    mapping: dict[str, str | None]
    total_rows: int
    unique_addresses: int
    filtered_city_name: str | None = None
    group_person_column: str
    group_person_filter: str
    cache_status: str
    build_duration_ms: int
    served_duration_ms: int
    rows: list[BuildingNamingRow]


class BuildingNamingLookupRead(BaseModel):
    unique_key: str
    input_address: str
    duplicate_count: int
    source_rows: list[int]
    reference_count: int
    references: list[str]
    lat: float | None = None
    lon: float | None = None
    used_source: str
    parcel_feature_collection: dict[str, object]
    parcel_labels: list[str]
    geocoder: dict[str, object]
    feature_collection: dict[str, object]


class BuildingImportRow(BaseModel):
    row_number: int
    source_name: str
    source_address: str
    address_display: str
    validation_status: str
    validation_message: str | None = None
    lat: float | None = None
    lon: float | None = None


class BuildingImportPreview(BaseModel):
    filename: str
    columns: list[str]
    total_rows: int
    sample_rows: list[dict[str, str]]
    name_column: str | None = None
    address_column: str | None = None
    rows: list[BuildingImportRow]


class FreeAddressLookupPayload(BaseModel):
    address: str = Field(min_length=3, max_length=255)


class FreeAddressLookupRead(BaseModel):
    unique_key: str
    input_address: str
    duplicate_count: int
    source_rows: list[int]
    reference_count: int
    references: list[str]
    lat: float | None = None
    lon: float | None = None
    used_source: str
    parcel_feature_collection: dict[str, object]
    parcel_labels: list[str]
    geocoder: dict[str, object]
    feature_collection: dict[str, object]


class BuildingNamingSelectionPayload(BaseModel):
    unique_key: str
    validated_name: str | None = Field(default=None, max_length=255)
    city_id: int | None = None
    selected_feature: dict[str, object] | None = None


class BuildingCreate(BaseModel):
    city_id: int | None = None
    dgfip_unique_key: str | None = Field(default=None, max_length=40)
    dgfip_source_file: str | None = Field(default=None, max_length=255)
    dgfip_source_rows_json: str | None = None
    dgfip_reference_norm: str | None = Field(default=None, max_length=32)
    nom_batiment: str | None = Field(default=None, max_length=255)
    nom_commune: str | None = Field(default=None, max_length=255)
    code_postal: str | None = Field(default=None, max_length=10)
    numero_voirie: str | None = Field(default=None, max_length=40)
    indice_repetition: str | None = Field(default=None, max_length=40)
    nature_voie: str | None = Field(default=None, max_length=80)
    nom_voie: str | None = Field(default=None, max_length=255)
    prefixe: str | None = Field(default=None, max_length=20)
    section: str | None = Field(default=None, max_length=40)
    numero_plan: str | None = Field(default=None, max_length=40)
    adresse_reconstituee: str | None = Field(default=None, max_length=255)
    latitude: float | None = None
    longitude: float | None = None
    ign_layer: str | None = Field(default=None, max_length=80)
    ign_typename: str | None = Field(default=None, max_length=120)
    ign_id: str | None = Field(default=None, max_length=120)
    ign_name: str | None = Field(default=None, max_length=255)
    ign_label: str | None = Field(default=None, max_length=255)
    ign_name_proposed: str | None = Field(default=None, max_length=255)
    ign_name_source: str | None = Field(default=None, max_length=120)
    ign_name_distance_m: float | None = None
    ign_attributes_json: str | None = None
    ign_toponym_candidates_json: str | None = None
    parcel_labels_json: str | None = None
    majic_building_values_json: str | None = None
    majic_entry_values_json: str | None = None
    majic_level_values_json: str | None = None
    majic_door_values_json: str | None = None
    source_creation: str | None = Field(default=None, max_length=20)
    statut_geocodage: str | None = Field(default=None, max_length=20)


class BuildingUpdate(BaseModel):
    nom_batiment: str | None = Field(default=None, max_length=255)
    nom_commune: str | None = Field(default=None, max_length=255)
    code_postal: str | None = Field(default=None, max_length=10)
    numero_voirie: str | None = Field(default=None, max_length=40)
    indice_repetition: str | None = Field(default=None, max_length=40)
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
    dgfip_unique_key: str | None
    dgfip_source_file: str | None
    dgfip_source_rows_json: str | None
    dgfip_reference_norm: str | None
    nom_batiment: str | None
    nom_commune: str
    code_postal: str | None
    numero_voirie: str | None
    indice_repetition: str | None
    nature_voie: str | None
    nom_voie: str | None
    prefixe: str | None
    section: str | None
    numero_plan: str | None
    adresse_reconstituee: str | None
    latitude: float | None
    longitude: float | None
    ign_layer: str | None
    ign_typename: str | None
    ign_id: str | None
    ign_name: str | None
    ign_label: str | None
    ign_name_proposed: str | None
    ign_name_source: str | None
    ign_name_distance_m: float | None
    ign_attributes_json: str | None
    ign_toponym_candidates_json: str | None
    parcel_labels_json: str | None
    majic_building_values_json: str | None
    majic_entry_values_json: str | None
    majic_level_values_json: str | None
    majic_door_values_json: str | None
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
