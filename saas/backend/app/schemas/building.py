from datetime import date, datetime

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
    majic_configured: bool = True
    majic_unavailable_reason: str | None = None


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
    asset_type: str = "building"
    source_typology: str | None = None
    source_parent: str | None = None
    source_local_id: str | None = None
    source_parcel: str | None = None
    source_short_name: str | None = None
    source_building_code: str | None = None
    source_floor: str | None = None
    source_door: str | None = None
    source_occupancy_status: str | None = None
    expected_citycode: str | None = None
    resolved_city: str | None = None
    resolved_postcode: str | None = None
    resolved_citycode: str | None = None
    commune_mismatch: bool = False


class BuildingImportPreview(BaseModel):
    filename: str
    columns: list[str]
    total_rows: int
    sample_rows: list[dict[str, str]]
    name_column: str | None = None
    address_column: str | None = None
    typology_column: str | None = None
    parent_column: str | None = None
    hierarchy_detected: bool = False
    hierarchy_counts: dict[str, int] = {}
    rows: list[BuildingImportRow]


class SiteCreate(BaseModel):
    city_id: int | None = None
    nom_site: str = Field(min_length=1, max_length=255)
    adresse: str | None = Field(default=None, max_length=255)
    source_file: str | None = Field(default=None, max_length=255)
    source_rows_json: str | None = None


class SiteUpdate(BaseModel):
    nom_site: str | None = Field(default=None, min_length=1, max_length=255)
    adresse: str | None = Field(default=None, max_length=255)


class SiteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    city_id: int | None
    nom_site: str
    adresse: str | None
    source_file: str | None
    source_rows_json: str | None
    created_at: datetime
    updated_at: datetime


class FreeAddressLookupPayload(BaseModel):
    address: str = Field(min_length=3, max_length=255)
    citycode: str | None = Field(default=None, max_length=5)
    # Une cellule du fichier source peut concatener plusieurs parcelles : la limite
    # a 64 caracteres rejetait ces lignes en 422. Le service les decoupe ensuite.
    parcel_reference: str | None = Field(default=None, max_length=1024)
    # Si True : geocodage seul, sans appel WFS BDTOPO (polygones charges cote client).
    skip_ign_buildings: bool = False


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
    # selected_feature : retro-compat (1 seul batiment IGN principal).
    # selected_features : nouvelle API multi (le 1er reste 'principal',
    # tous sont stockes en JSON dans ign_features_json).
    selected_feature: dict[str, object] | None = None
    selected_features: list[dict[str, object]] | None = None


class BuildingIgnAttachmentPayload(BaseModel):
    validated_name: str | None = Field(default=None, max_length=255)
    selected_feature: dict[str, object] | None = None
    selected_features: list[dict[str, object]] | None = None
    lat: float | None = None
    lon: float | None = None


class IgnPointLookupRead(BaseModel):
    """Bâtiments IGN autour d'un point posé sur la carte (sans adresse préalable)."""

    lat: float
    lon: float
    radius_m: int
    feature_collection: dict[str, object]
    parcel_feature_collection: dict[str, object]
    parcel_labels: list[str]


class BuildingPositionPayload(BaseModel):
    """Déplacement d'un bâtiment sur la carte."""

    lat: float
    lon: float
    # Géocodage inverse : l'adresse suit le point, sauf demande contraire.
    resolve_address: bool = True


class NearbyDgfipRow(BaseModel):
    unique_key: str
    address_display: str
    nom_commune: str
    lat: float
    lon: float
    distance_m: float
    majic_building_values: list[str]
    majic_entry_values: list[str]
    majic_level_values: list[str]
    majic_door_values: list[str]


class NearbyDgfipResult(BaseModel):
    majic_configured: bool = True
    majic_unavailable_reason: str | None = None
    rows: list[NearbyDgfipRow] = []


class BuildingCreate(BaseModel):
    city_id: int | None = None
    site_id: int | None = None
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
    ign_features_json: str | None = None
    ign_toponym_candidates_json: str | None = None
    parcel_labels_json: str | None = None
    majic_building_values_json: str | None = None
    majic_entry_values_json: str | None = None
    majic_level_values_json: str | None = None
    majic_door_values_json: str | None = None
    source_creation: str | None = Field(default=None, max_length=20)
    statut_geocodage: str | None = Field(default=None, max_length=20)
    create_default_local: bool = True


class BuildingUpdate(BaseModel):
    # site_id : permet le drag&drop d'un batiment vers un autre site dans l'UI cascade.
    # `unset` (champ absent du payload) = ne touche pas, None = detache du site.
    site_id: int | None = None
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
    site_id: int | None
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
    ign_features_json: str | None = None
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
    adresse_reconstituee: str | None = Field(default=None, max_length=255)
    code_postal: str | None = Field(default=None, max_length=10)
    nom_commune: str | None = Field(default=None, max_length=255)
    latitude: float | None = None
    longitude: float | None = None
    dgfip_reference_norm: str | None = Field(default=None, max_length=32)


class LocalUpdate(BaseModel):
    # building_id : permet le drag&drop d'un local vers un autre batiment dans l'UI cascade.
    # Champ absent du payload = ne touche pas ; entier fourni = deplace.
    building_id: int | None = None
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
    adresse_reconstituee: str | None = None
    code_postal: str | None = None
    nom_commune: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    dgfip_reference_norm: str | None = None
    created_at: datetime
    updated_at: datetime


class PatrimonyReclassifyPayload(BaseModel):
    target_type: str = Field(pattern="^(site|building|local)$")
    target_site_id: int | None = None
    target_building_id: int | None = None
    name: str | None = Field(default=None, max_length=255)


class PatrimonyReclassifyResult(BaseModel):
    entity_type: str
    entity_id: int


class BuildingMeterLinkCreate(BaseModel):
    fluid: str = Field(min_length=1, max_length=20)
    meter_identifier: str = Field(min_length=1, max_length=80)
    meter_label: str | None = Field(default=None, max_length=255)
    usage_label: str | None = Field(default=None, max_length=120)
    share_ratio: float = Field(default=1.0, ge=0, le=1)
    valid_from: date | None = None
    valid_to: date | None = None
    confidence: str = Field(default="A_VALIDER", min_length=1, max_length=20)
    validation_status: str = Field(default="A_VALIDER", min_length=1, max_length=20)
    source: str = Field(default="MANUEL", min_length=1, max_length=120)
    contract_context: str | None = Field(default=None, max_length=120)
    supplier_name: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)


class BuildingMeterLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    building_id: int
    fluid: str
    meter_identifier: str
    meter_label: str | None
    usage_label: str | None
    share_ratio: float
    valid_from: date | None
    valid_to: date | None
    confidence: str
    validation_status: str
    source: str
    contract_context: str | None
    supplier_name: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


# --- Rapprochement compteur energie -> batiment (matching) ---


class MeterBuildingSuggestion(BaseModel):
    building_id: int
    nom_batiment: str | None
    adresse: str | None
    score: float


class MeterMatchResult(BaseModel):
    fluid: str
    meter_identifier: str
    label: str | None = None
    address: str | None = None
    current_building_id: int | None = None
    current_building_name: str | None = None
    suggestions: list[MeterBuildingSuggestion] = Field(default_factory=list)
    auto_building_id: int | None = None


class MeterMatchResponse(BaseModel):
    matches: list[MeterMatchResult]


class MeterMapping(BaseModel):
    fluid: str = Field(min_length=1, max_length=20)
    meter_identifier: str = Field(min_length=1, max_length=80)
    building_id: int | None = None
    meter_label: str | None = Field(default=None, max_length=255)


class MeterMappingApplyRequest(BaseModel):
    mappings: list[MeterMapping]


class MeterMappingApplyResult(BaseModel):
    applied: int
    updated: int
