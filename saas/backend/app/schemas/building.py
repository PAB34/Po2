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
    source_external_id: str | None = Field(default=None, max_length=255)
    source_payload_json: str | None = None
    source_creation: str | None = Field(default=None, max_length=20)
    statut_geocodage: str | None = Field(default=None, max_length=20)


class BuildingUpdate(BaseModel):
    nom_batiment: str | None = Field(default=None, max_length=255)
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
    source_external_id: str | None
    source_payload_json: str | None
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
    source_external_id: str | None = Field(default=None, max_length=255)
    source_payload_json: str | None = None


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
    source_external_id: str | None
    source_payload_json: str | None
    created_at: datetime
    updated_at: datetime


class BuildingImportConfig(BaseModel):
    sheet_name: str | None = None
    header_row_index: int = Field(default=0, ge=0)
    row_type_column: str | None = None
    building_row_types: list[str] = Field(default_factory=list)
    local_row_types: list[str] = Field(default_factory=list)
    mapping: dict[str, str | None] = Field(default_factory=dict)
    skip_existing_buildings: bool = True
    create_missing_buildings_for_locals: bool = True


class BuildingImportAnalysisRead(BaseModel):
    filename: str
    available_sheets: list[str]
    selected_sheet: str
    header_row_index: int
    columns: list[str]
    total_rows: int
    sample_rows: list[dict[str, str]]
    detected_row_type_values: list[str]
    suggested_config: BuildingImportConfig


class BuildingImportBuildingPreviewRow(BaseModel):
    source_row_number: int
    action: str
    identifier: str
    nom_batiment: str | None = None
    adresse_reconstituee: str | None = None
    nom_commune: str | None = None
    dgfip_reference_norm: str | None = None
    source_external_id: str | None = None
    warnings: list[str]


class BuildingImportLocalPreviewRow(BaseModel):
    source_row_number: int
    action: str
    parent_identifier: str
    nom_local: str | None = None
    type_local: str | None = None
    niveau: str | None = None
    usage: str | None = None
    statut_occupation: str | None = None
    source_external_id: str | None = None
    warnings: list[str]


class BuildingImportPreviewRead(BaseModel):
    filename: str
    selected_sheet: str
    total_rows: int
    building_rows_detected: int
    local_rows_detected: int
    building_preview: list[BuildingImportBuildingPreviewRow]
    local_preview: list[BuildingImportLocalPreviewRow]
    warnings: list[str]


class BuildingImportResultRead(BaseModel):
    filename: str
    selected_sheet: str
    created_buildings: int
    skipped_existing_buildings: int
    created_locals: int
    skipped_existing_locals: int
    warnings: list[str]
