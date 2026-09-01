const apiBaseUrl = (import.meta as ImportMeta & { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL ?? "/api";

export type HealthResponse = {
  status: string;
  app: string;
  version: string;
};

export type User = {
  id: number;
  email: string;
  nom: string;
  prenom: string;
  telephone: string | null;
  city_id: number | null;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export type RegisterPayload = {
  email: string;
  password: string;
  nom: string;
  prenom: string;
  telephone?: string;
  city_id?: number;
};

export type UpdateMePayload = {
  nom: string;
  prenom: string;
  telephone?: string;
};

export type ChangePasswordPayload = {
  current_password: string;
  new_password: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type City = {
  id: number;
  nom_commune: string;
  code_commune: string | null;
  code_postal: string | null;
  latitude: number | null;
  longitude: number | null;
  source_file: string | null;
  created_at: string;
};

export type Building = {
  id: number;
  city_id: number | null;
  site_id: number | null;
  dgfip_unique_key: string | null;
  dgfip_source_file: string | null;
  dgfip_source_rows_json: string | null;
  dgfip_reference_norm: string | null;
  nom_batiment: string | null;
  nom_commune: string;
  code_postal: string | null;
  numero_voirie: string | null;
  indice_repetition: string | null;
  nature_voie: string | null;
  nom_voie: string | null;
  prefixe: string | null;
  section: string | null;
  numero_plan: string | null;
  adresse_reconstituee: string | null;
  latitude: number | null;
  longitude: number | null;
  ign_layer: string | null;
  ign_typename: string | null;
  ign_id: string | null;
  ign_name: string | null;
  ign_label: string | null;
  ign_name_proposed: string | null;
  ign_name_source: string | null;
  ign_name_distance_m: number | null;
  ign_attributes_json: string | null;
  ign_features_json: string | null;
  ign_toponym_candidates_json: string | null;
  parcel_labels_json: string | null;
  majic_building_values_json: string | null;
  majic_entry_values_json: string | null;
  majic_level_values_json: string | null;
  majic_door_values_json: string | null;
  source_creation: string;
  statut_geocodage: string;
  created_at: string;
  updated_at: string;
};

export type BuildingNamingRow = {
  unique_key: string;
  address_display: string;
  duplicate_count: number;
  source_rows: number[];
  reference_count: number;
  references: string[];
  first_reference_norm: string;
  nom_commune: string;
  numero_voirie: string | null;
  indice_repetition: string | null;
  nature_voie: string | null;
  nom_voie: string | null;
  prefixe: string | null;
  section: string | null;
  numero_plan: string | null;
  majic_building_values: string[];
  majic_entry_values: string[];
  majic_level_values: string[];
  majic_door_values: string[];
};

export type BuildingNamingDataset = {
  filename: string;
  columns: string[];
  mapping: Record<string, string | null>;
  total_rows: number;
  unique_addresses: number;
  filtered_city_name: string | null;
  group_person_column: string;
  group_person_filter: string;
  cache_status: string;
  build_duration_ms: number;
  served_duration_ms: number;
  rows: BuildingNamingRow[];
  majic_configured?: boolean;
  majic_unavailable_reason?: string | null;
};

export type GeoJsonFeature = {
  type: string;
  geometry: {
    type: string;
    coordinates: unknown;
  } | null;
  properties: Record<string, unknown>;
};

export type GeoJsonFeatureCollection = {
  type: string;
  features: GeoJsonFeature[];
};

export type BuildingNamingLookup = {
  unique_key: string;
  input_address: string;
  duplicate_count: number;
  source_rows: number[];
  reference_count: number;
  references: string[];
  lat: number | null;
  lon: number | null;
  used_source: string;
  parcel_feature_collection: GeoJsonFeatureCollection;
  parcel_labels: string[];
  geocoder: Record<string, unknown>;
  feature_collection: GeoJsonFeatureCollection;
};

export type BuildingImportRow = {
  row_number: number;
  source_name: string;
  source_address: string;
  address_display: string;
  validation_status: string;
  validation_message: string | null;
  lat: number | null;
  lon: number | null;
  asset_type: "site" | "building" | "local" | string;
  source_typology: string | null;
  source_parent: string | null;
  source_local_id: string | null;
  source_parcel: string | null;
  source_short_name: string | null;
  source_building_code: string | null;
  source_floor: string | null;
  source_door: string | null;
  source_occupancy_status: string | null;
  expected_citycode: string | null;
  resolved_city: string | null;
  resolved_postcode: string | null;
  resolved_citycode: string | null;
  commune_mismatch: boolean;
};

export type Site = {
  id: number;
  city_id: number | null;
  nom_site: string;
  adresse: string | null;
  source_file: string | null;
  source_rows_json: string | null;
  created_at: string;
  updated_at: string;
};

export type BuildingImportPreview = {
  filename: string;
  columns: string[];
  total_rows: number;
  sample_rows: Array<Record<string, string>>;
  name_column: string | null;
  address_column: string | null;
  typology_column: string | null;
  parent_column: string | null;
  hierarchy_detected: boolean;
  hierarchy_counts: Record<string, number>;
  rows: BuildingImportRow[];
};

export type BuildingImportConfig = {
  name_column?: string | null;
  address_column?: string | null;
  sheet_name?: string | null;
  header_row_index?: number | null;
  row_type_column?: string | null;
  [key: string]: unknown;
};

export type BuildingImportResult = BuildingImportPreview;

export type FreeAddressLookup = BuildingNamingLookup;

export type NearbyDgfipRow = {
  unique_key: string;
  address_display: string;
  nom_commune: string;
  lat: number;
  lon: number;
  distance_m: number;
  majic_building_values: string[];
  majic_entry_values: string[];
  majic_level_values: string[];
  majic_door_values: string[];
};

export type NearbyDgfipResult = {
  majic_configured: boolean;
  majic_unavailable_reason: string | null;
  rows: NearbyDgfipRow[];
};

export type BuildingIgnAttachmentPayload = {
  validated_name?: string;
  selected_feature?: GeoJsonFeature | null;
  selected_features?: GeoJsonFeature[];
  lat?: number | null;
  lon?: number | null;
};

export type CreateBuildingFromNamingPayload = {
  unique_key: string;
  validated_name?: string;
  city_id?: number;
  selected_feature?: GeoJsonFeature | null;
  selected_features?: GeoJsonFeature[];
};

export type CreateBuildingPayload = {
  city_id?: number;
  site_id?: number;
  dgfip_unique_key?: string;
  dgfip_source_file?: string;
  dgfip_source_rows_json?: string;
  dgfip_reference_norm?: string;
  nom_batiment?: string;
  nom_commune?: string;
  code_postal?: string;
  numero_voirie?: string;
  indice_repetition?: string;
  nature_voie?: string;
  nom_voie?: string;
  prefixe?: string;
  section?: string;
  numero_plan?: string;
  adresse_reconstituee?: string;
  latitude?: number;
  longitude?: number;
  ign_layer?: string;
  ign_typename?: string;
  ign_id?: string;
  ign_name?: string;
  ign_label?: string;
  ign_name_proposed?: string;
  ign_name_source?: string;
  ign_name_distance_m?: number;
  ign_attributes_json?: string;
  ign_features_json?: string;
  ign_toponym_candidates_json?: string;
  parcel_labels_json?: string;
  majic_building_values_json?: string;
  majic_entry_values_json?: string;
  majic_level_values_json?: string;
  majic_door_values_json?: string;
  source_creation?: string;
  statut_geocodage?: string;
  create_default_local?: boolean;
};

export type CreateSitePayload = {
  city_id?: number;
  nom_site: string;
  adresse?: string | null;
  source_file?: string | null;
  source_rows_json?: string | null;
};

export type UpdateBuildingPayload = {
  site_id?: number | null;
  nom_batiment?: string | null;
  nom_commune?: string;
  code_postal?: string | null;
  numero_voirie?: string | null;
  indice_repetition?: string | null;
  nature_voie?: string | null;
  nom_voie?: string | null;
  prefixe?: string | null;
  section?: string | null;
  numero_plan?: string | null;
  adresse_reconstituee?: string | null;
  latitude?: number | null;
  longitude?: number | null;
};

export type Local = {
  id: number;
  building_id: number;
  adresse_reconstituee: string | null;
  code_postal: string | null;
  nom_commune: string | null;
  latitude: number | null;
  longitude: number | null;
  dgfip_reference_norm: string | null;
  nom_local: string;
  type_local: string;
  niveau: string | null;
  surface_m2: number | null;
  usage: string | null;
  statut_occupation: string | null;
  commentaire: string | null;
  created_at: string;
  updated_at: string;
};

export type CreateLocalPayload = {
  adresse_reconstituee?: string;
  code_postal?: string;
  nom_commune?: string;
  latitude?: number;
  longitude?: number;
  dgfip_reference_norm?: string;
  nom_local: string;
  type_local: string;
  niveau?: string;
  surface_m2?: number;
  usage?: string;
  statut_occupation?: string;
  commentaire?: string;
};

export type UpdateLocalPayload = {
  building_id?: number;
  nom_local?: string;
  type_local?: string;
  niveau?: string | null;
  surface_m2?: number | null;
  usage?: string | null;
  statut_occupation?: string | null;
  commentaire?: string | null;
};

export type PatrimonyNodeType = "site" | "building" | "local";

export type ReclassifyPatrimonyPayload = {
  target_type: PatrimonyNodeType;
  target_site_id?: number | null;
  target_building_id?: number | null;
  name?: string | null;
};

export type ReclassifyPatrimonyResult = {
  entity_type: PatrimonyNodeType;
  entity_id: number;
};

export type BuildingMeterLink = {
  id: number;
  building_id: number;
  fluid: string;
  meter_identifier: string;
  meter_label: string | null;
  usage_label: string | null;
  share_ratio: number;
  valid_from: string | null;
  valid_to: string | null;
  confidence: string;
  validation_status: string;
  source: string;
  contract_context: string | null;
  supplier_name: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type CreateBuildingMeterLinkPayload = {
  fluid: string;
  meter_identifier: string;
  meter_label?: string;
  usage_label?: string;
  share_ratio?: number;
  valid_from?: string;
  valid_to?: string;
  confidence?: string;
  validation_status?: string;
  source?: string;
  contract_context?: string;
  supplier_name?: string;
  notes?: string;
};

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = "Une erreur est survenue.";

    try {
      const payload = (await response.json()) as { detail?: unknown };
      const detail = payload.detail;
      if (typeof detail === "string") {
        message = detail;
      } else if (Array.isArray(detail)) {
        // FastAPI renvoie une LISTE d'objets sur une erreur de validation (422).
        // Sans ce traitement, `new Error(detail)` affichait « [object Object] ».
        const parts = detail
          .map((item) => {
            if (typeof item === "string") return item;
            const entry = item as { loc?: unknown[]; msg?: string };
            const field = Array.isArray(entry.loc) ? entry.loc.filter((x) => x !== "body").join(".") : "";
            return [field, entry.msg].filter(Boolean).join(" : ");
          })
          .filter(Boolean);
        if (parts.length > 0) message = parts.join(" ; ");
      } else if (detail) {
        message = JSON.stringify(detail);
      }
    } catch {
      message = response.statusText || message;
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

function buildHeaders(token?: string): HeadersInit {
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

function buildAuthHeaders(token?: string): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${apiBaseUrl}/health`);
  return parseResponse<HealthResponse>(response);
}

export async function registerRequest(payload: RegisterPayload): Promise<User> {
  const response = await fetch(`${apiBaseUrl}/auth/register`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify(payload),
  });

  return parseResponse<User>(response);
}

export async function fetchCities(): Promise<City[]> {
  const response = await fetch(`${apiBaseUrl}/cities`, {
    headers: buildHeaders(),
  });

  return parseResponse<City[]>(response);
}

export async function loginRequest(payload: LoginPayload): Promise<TokenResponse> {
  const response = await fetch(`${apiBaseUrl}/auth/login`, {
    method: "POST",
    headers: buildHeaders(),
    body: JSON.stringify(payload),
  });

  return parseResponse<TokenResponse>(response);
}

export async function fetchMe(token: string): Promise<User> {
  const response = await fetch(`${apiBaseUrl}/auth/me`, {
    headers: buildHeaders(token),
  });

  return parseResponse<User>(response);
}

export async function updateMeRequest(token: string, payload: UpdateMePayload): Promise<User> {
  const response = await fetch(`${apiBaseUrl}/auth/me`, {
    method: "PUT",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseResponse<User>(response);
}

export async function changePasswordRequest(token: string, payload: ChangePasswordPayload): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/auth/change-password`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseResponse<void>(response);
}

export async function fetchBuildings(token: string): Promise<Building[]> {
  const response = await fetch(`${apiBaseUrl}/buildings`, {
    headers: buildHeaders(token),
  });

  return parseResponse<Building[]>(response);
}

export async function fetchSites(token: string): Promise<Site[]> {
  const response = await fetch(`${apiBaseUrl}/buildings/sites`, {
    headers: buildHeaders(token),
  });

  return parseResponse<Site[]>(response);
}

export async function fetchAllLocals(token: string): Promise<Local[]> {
  const response = await fetch(`${apiBaseUrl}/buildings/locals`, {
    headers: buildHeaders(token),
  });

  return parseResponse<Local[]>(response);
}

export async function fetchBuildingNamingDataset(token: string): Promise<BuildingNamingDataset> {
  const response = await fetch(`${apiBaseUrl}/buildings/naming/dataset`, {
    headers: buildHeaders(token),
  });

  return parseResponse<BuildingNamingDataset>(response);
}

export async function fetchBuildingNamingLookup(token: string, uniqueKey: string): Promise<BuildingNamingLookup> {
  const response = await fetch(`${apiBaseUrl}/buildings/naming/${encodeURIComponent(uniqueKey)}`, {
    headers: buildHeaders(token),
  });

  return parseResponse<BuildingNamingLookup>(response);
}

export async function fetchFreeAddressLookup(
  token: string,
  address: string,
  options?: { citycode?: string | null; parcel_reference?: string | null; skip_ign_buildings?: boolean },
): Promise<FreeAddressLookup> {
  const payload: Record<string, unknown> = { address };
  if (options?.citycode) payload.citycode = options.citycode;
  if (options?.parcel_reference) payload.parcel_reference = options.parcel_reference;
  if (options?.skip_ign_buildings) payload.skip_ign_buildings = true;
  const response = await fetch(`${apiBaseUrl}/buildings/lookup/free-address`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseResponse<FreeAddressLookup>(response);
}

export async function previewBuildingImportFile(
  token: string,
  file: File,
  nameColumn?: string,
  addressColumn?: string,
  validateAddresses?: boolean,
): Promise<BuildingImportPreview> {
  const formData = new FormData();
  formData.append("file", file);
  if (nameColumn) {
    formData.append("name_column", nameColumn);
  }
  if (addressColumn) {
    formData.append("address_column", addressColumn);
  }
  if (validateAddresses !== undefined) {
    formData.append("validate_addresses", String(validateAddresses));
  }
  const response = await fetch(`${apiBaseUrl}/buildings/import/preview`, {
    method: "POST",
    headers: buildAuthHeaders(token),
    body: formData,
  });

  return parseResponse<BuildingImportPreview>(response);
}

export async function executeBuildingImportFile(
  token: string,
  file: File,
  config?: BuildingImportConfig,
): Promise<BuildingImportResult> {
  return previewBuildingImportFile(token, file, config?.name_column ?? undefined, config?.address_column ?? undefined);
}

export async function createBuildingFromNamingSelection(
  token: string,
  payload: CreateBuildingFromNamingPayload,
): Promise<Building> {
  const response = await fetch(`${apiBaseUrl}/buildings/naming/selection`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseResponse<Building>(response);
}


export async function attachBuildingGeoRequest(
  token: string,
  buildingId: number,
  payload: CreateBuildingFromNamingPayload,
): Promise<Building> {
  const response = await fetch(`${apiBaseUrl}/buildings/${buildingId}/geo-attachment`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseResponse<Building>(response);
}

export async function attachBuildingIgnRequest(
  token: string,
  buildingId: number,
  payload: BuildingIgnAttachmentPayload,
): Promise<Building> {
  const response = await fetch(`${apiBaseUrl}/buildings/${buildingId}/ign-attachment`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseResponse<Building>(response);
}

export async function fetchNearbyDgfip(token: string, buildingId: number): Promise<NearbyDgfipResult> {
  const response = await fetch(`${apiBaseUrl}/buildings/${buildingId}/nearby-dgfip`, {
    headers: buildHeaders(token),
  });

  return parseResponse<NearbyDgfipResult>(response);
}

export async function fetchBuilding(token: string, buildingId: number): Promise<Building> {
  const response = await fetch(`${apiBaseUrl}/buildings/${buildingId}`, {
    headers: buildHeaders(token),
  });

  return parseResponse<Building>(response);
}

export async function fetchBuildingLocals(token: string, buildingId: number): Promise<Local[]> {
  const response = await fetch(`${apiBaseUrl}/buildings/${buildingId}/locals`, {
    headers: buildHeaders(token),
  });

  return parseResponse<Local[]>(response);
}

export async function fetchBuildingMeterLinks(token: string, buildingId: number): Promise<BuildingMeterLink[]> {
  const response = await fetch(`${apiBaseUrl}/buildings/${buildingId}/meters`, {
    headers: buildHeaders(token),
  });

  return parseResponse<BuildingMeterLink[]>(response);
}

export async function createBuildingRequest(token: string, payload: CreateBuildingPayload): Promise<Building> {
  const response = await fetch(`${apiBaseUrl}/buildings`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseResponse<Building>(response);
}

export async function createSiteRequest(token: string, payload: CreateSitePayload): Promise<Site> {
  const response = await fetch(`${apiBaseUrl}/buildings/sites`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseResponse<Site>(response);
}

export type UpdateSitePayload = {
  nom_site?: string;
  adresse?: string | null;
};

export async function updateSiteRequest(token: string, siteId: number, payload: UpdateSitePayload): Promise<Site> {
  const response = await fetch(`${apiBaseUrl}/buildings/sites/${siteId}`, {
    method: "PUT",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseResponse<Site>(response);
}

export async function updateBuildingRequest(token: string, buildingId: number, payload: UpdateBuildingPayload): Promise<Building> {
  const response = await fetch(`${apiBaseUrl}/buildings/${buildingId}`, {
    method: "PUT",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseResponse<Building>(response);
}

export async function createLocalRequest(token: string, buildingId: number, payload: CreateLocalPayload): Promise<Local> {
  const response = await fetch(`${apiBaseUrl}/buildings/${buildingId}/locals`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseResponse<Local>(response);
}

export async function createBuildingMeterLinkRequest(
  token: string,
  buildingId: number,
  payload: CreateBuildingMeterLinkPayload,
): Promise<BuildingMeterLink> {
  const response = await fetch(`${apiBaseUrl}/buildings/${buildingId}/meters`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseResponse<BuildingMeterLink>(response);
}

export async function updateLocalRequest(token: string, buildingId: number, localId: number, payload: UpdateLocalPayload): Promise<Local> {
  const response = await fetch(`${apiBaseUrl}/buildings/${buildingId}/locals/${localId}`, {
    method: "PUT",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseResponse<Local>(response);
}

export async function reclassifySiteRequest(
  token: string,
  siteId: number,
  payload: ReclassifyPatrimonyPayload,
): Promise<ReclassifyPatrimonyResult> {
  const response = await fetch(`${apiBaseUrl}/buildings/sites/${siteId}/reclassify`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseResponse<ReclassifyPatrimonyResult>(response);
}

export async function reclassifyBuildingRequest(
  token: string,
  buildingId: number,
  payload: ReclassifyPatrimonyPayload,
): Promise<ReclassifyPatrimonyResult> {
  const response = await fetch(`${apiBaseUrl}/buildings/${buildingId}/reclassify`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseResponse<ReclassifyPatrimonyResult>(response);
}

export async function reclassifyLocalRequest(
  token: string,
  buildingId: number,
  localId: number,
  payload: ReclassifyPatrimonyPayload,
): Promise<ReclassifyPatrimonyResult> {
  const response = await fetch(`${apiBaseUrl}/buildings/${buildingId}/locals/${localId}/reclassify`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseResponse<ReclassifyPatrimonyResult>(response);
}

export async function deleteAllBuildingsRequest(
  token: string,
  includeSites = false,
): Promise<{ deleted: number; deleted_sites: number }> {
  const response = await fetch(
    `${apiBaseUrl}/buildings?include_sites=${includeSites ? "true" : "false"}`,
    {
      method: "DELETE",
      headers: buildHeaders(token),
    },
  );

  return parseResponse<{ deleted: number; deleted_sites: number }>(response);
}

export async function deleteSiteRequest(token: string, siteId: number): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/buildings/sites/${siteId}`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });
  return parseResponse<void>(response);
}

export async function deleteBuildingRequest(token: string, buildingId: number): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/buildings/${buildingId}`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });
  return parseResponse<void>(response);
}

export async function deleteLocalRequest(token: string, buildingId: number, localId: number): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/buildings/${buildingId}/locals/${localId}`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });

  return parseResponse<void>(response);
}

export async function deleteBuildingMeterLinkRequest(token: string, buildingId: number, meterLinkId: number): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/buildings/${buildingId}/meters/${meterLinkId}`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });

  return parseResponse<void>(response);
}

// --- Energie ---

export type EnergieKpis = {
  total_prms: number;
  total_subscribed_kva: number;
  sous_dimensionnes: number;
  proche_seuil: number;
  sur_souscrits: number;
  calibration_inconnue: number;
  annual_consumption_kwh: number | null;
  annual_consumption_prms: number;
  annual_consumption_start: string | null;
  annual_consumption_end: string | null;
};

export type SupplierDistributionItem = {
  supplier: string;
  total_kva: number;
  prm_count: number;
};

export type EnergyPowerBandItem = {
  band: string;
  label: string;
  prm_count: number;
  total_kva: number;
  annual_consumption_kwh: number | null;
};

export type EnergyCalibrationDistributionItem = {
  status: string;
  label: string;
  prm_count: number;
};

export type EnergyTopConsumerItem = {
  usage_point_id: string;
  name: string;
  contractor: string | null;
  subscribed_power_kva: number | null;
  annual_consumption_kwh: number;
};

export type EnergyDistributionItem = {
  label: string;
  prm_count: number;
  total_kva: number | null;
};

export type PrmListItem = {
  usage_point_id: string;
  name: string;
  address: string;
  contractor: string;
  subscribed_power_kva: number | null;
  tariff: string | null;
  segment: string | null;
  connection_state: string | null;
  services_level: string | null;
  peak_kva_3y: number | null;
  calibration_status: string | null;
  calibration_ratio: number | null;
};

export type EnergieOverview = {
  kpis: EnergieKpis;
  supplier_distribution: SupplierDistributionItem[];
  power_bands: EnergyPowerBandItem[];
  calibration_distribution: EnergyCalibrationDistributionItem[];
  top_consumers: EnergyTopConsumerItem[];
  service_level_distribution: EnergyDistributionItem[];
  segment_distribution: EnergyDistributionItem[];
  tariff_distribution: EnergyDistributionItem[];
  connection_state_distribution: EnergyDistributionItem[];
  dju_seasonal: PrmDjuSeasonal | null;
  prms: PrmListItem[];
};

export type PrmContract = {
  usage_point_id: string;
  contract_start: string | null;
  contract_type: string | null;
  contractor: string | null;
  tariff: string | null;
  subscribed_power_kva: number | null;
  segment: string | null;
  organization_name: string | null;
  name: string | null;
};

export type PrmAddress = {
  address_number_street_name: string | null;
  address_postal_code_city: string | null;
  address_staircase_floor_apartment: string | null;
  address_building: string | null;
  address_insee_code: string | null;
};

export type PrmConnection = {
  serial_number: string | null;
  connection_state: string | null;
  voltage_level: string | null;
  subscribed_kva: number | null;
};

export type PrmSummary = {
  segment: string | null;
  activation_date: string | null;
  last_power_change_date: string | null;
  services_level: string | null;
};

export type PrmCalibration = {
  subscribed_kva: number | null;
  peak_kva_3y: number | null;
  ratio_percent: number | null;
  status: string | null;
  recommendation: string | null;
};

export type PrmDataDiagnostic = {
  source: string;
  label: string;
  has_data: boolean;
  outcome: string | null;
  severity: string;
  message: string;
  action: string | null;
};

export type PowerRecommendationDataQuality = {
  status: string;
  max_power_days: number;
  max_power_months: number;
  max_power_years: number;
  first_max_power_date: string | null;
  last_max_power_date: string | null;
  missing: string[];
};

export type PowerRecommendationScenario = {
  key: string;
  label: string;
  target_power_kva: number;
  delta_kva: number;
  margin_percent: number | null;
  risk: string;
  ratio_after_percent: number | null;
  is_recommended: boolean;
};

export type PowerRecommendationEconomicEstimate = {
  available: boolean;
  annual_amount_eur: number | null;
  reason: string;
};

export type RealPowerCosts = {
  available: boolean;
  penalties_eur: number;
  penalty_periods: number;
  fixed_routing_eur: number | null;
  invoices_count: number;
  period_start: string | null;
  period_end: string | null;
  max_reached_power_kva: number | null;
  subscribed_power_kva: number | null;
  reason: string;
};

export type PrmPowerRecommendation = {
  usage_point_id: string;
  name: string;
  address: string;
  contractor: string | null;
  tariff: string | null;
  segment: string | null;
  annual_consumption_kwh: number | null;
  annual_consumption_start: string | null;
  annual_consumption_end: string | null;
  annual_consumption_days: number;
  subscribed_power_kva: number | null;
  peak_kva: number | null;
  current_ratio_percent: number | null;
  calibration_status: string;
  recommended_power_kva: number | null;
  recommended_scenario: string | null;
  action: string;
  confidence: string;
  data_quality: PowerRecommendationDataQuality;
  scenarios: PowerRecommendationScenario[];
  economic_estimate: PowerRecommendationEconomicEstimate;
  real_costs: RealPowerCosts | null;
  justification: string;
  priority_score: number;
};

export type PowerRecommendationOverview = {
  kpis: {
    total: number;
    increase: number;
    decrease: number;
    maintain: number;
    insufficient_data: number;
    high_confidence: number;
    medium_confidence: number;
  };
  recommendations: PrmPowerRecommendation[];
};

export type PrmDetail = {
  usage_point_id: string;
  contract: PrmContract;
  address: PrmAddress;
  connection: PrmConnection;
  summary: PrmSummary;
  calibration: PrmCalibration;
  data_diagnostics: Record<string, PrmDataDiagnostic>;
};

export type MaxPowerPoint = {
  date: string;
  value_va: number;
};

export type PrmMaxPowerData = {
  usage_point_id: string;
  subscribed_kva: number | null;
  points: MaxPowerPoint[];
};

export type AnnualMonthPoint = {
  month: string;
  max_kva: number;
};

export type AnnualYearProfile = {
  year: string;
  months: AnnualMonthPoint[];
};

export type PrmAnnualProfile = {
  usage_point_id: string;
  subscribed_kva: number | null;
  profiles: AnnualYearProfile[];
};

export type DailyConsumptionPoint = {
  date: string;
  value_kwh: number;
};

export type PrmDailyConsumption = {
  usage_point_id: string;
  points: DailyConsumptionPoint[];
};

export type DjuMonthPoint = {
  month: string;
  dju_chauffe: number;
  dju_froid: number;
};

export type LoadCurvePoint = {
  datetime: string;
  value_w: number;
};

export type PrmLoadCurveData = {
  usage_point_id: string;
  points: LoadCurvePoint[];
};

export async function fetchEnergieOverview(token: string): Promise<EnergieOverview> {
  const response = await fetch(`${apiBaseUrl}/energie`, {
    headers: buildHeaders(token),
  });
  return parseResponse<EnergieOverview>(response);
}

export async function fetchPrmDetail(token: string, prmId: string): Promise<PrmDetail> {
  const response = await fetch(`${apiBaseUrl}/energie/${encodeURIComponent(prmId)}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<PrmDetail>(response);
}

export type FluidsClimateMonth = { month: number; current: number | null; previous: number | null; average: number | null; };
export type FluidsClimateSeries = {
  base_c: number;
  monthly: FluidsClimateMonth[];
  current_total: number | null;
  previous_total: number | null;
  average_total: number | null;
  delta_previous_pct: number | null;
  delta_average_pct: number | null;
};
export type FluidsThermal = {
  scope: string;
  sensitivity_kwh_per_dju: number | null;
  sensitivity_previous: number | null;
  sensitivity_delta_pct: number | null;
  base_load_kwh_per_month: number | null;
  thermosensitive_share_pct: number | null;
  base_load_share_pct: number | null;
  r2: number | null;
  months_used: number;
  window_months: number;
  current_period: string | null;
  previous_period: string | null;
  reliable: boolean;
};
export type FluidsClimateOverview = {
  current_year: number;
  previous_year: number;
  years_in_average: number;
  heating: FluidsClimateSeries;
  cooling: FluidsClimateSeries;
  thermal: FluidsThermal;
};

export async function fetchFluidsClimate(token: string): Promise<FluidsClimateOverview> {
  const response = await fetch(`${apiBaseUrl}/energie/fluids/climate`, {
    headers: buildHeaders(token),
  });
  return parseResponse<FluidsClimateOverview>(response);
}

export async function fetchPowerRecommendations(token: string): Promise<PowerRecommendationOverview> {
  const response = await fetch(`${apiBaseUrl}/energie/preconisations`, {
    headers: buildHeaders(token),
  });
  return parseResponse<PowerRecommendationOverview>(response);
}

export async function fetchPrmPowerRecommendation(token: string, prmId: string): Promise<PrmPowerRecommendation> {
  const response = await fetch(`${apiBaseUrl}/energie/${encodeURIComponent(prmId)}/preconisation`, {
    headers: buildHeaders(token),
  });
  return parseResponse<PrmPowerRecommendation>(response);
}

export async function fetchPrmMaxPower(token: string, prmId: string): Promise<PrmMaxPowerData> {
  const response = await fetch(`${apiBaseUrl}/energie/${encodeURIComponent(prmId)}/max-power`, {
    headers: buildHeaders(token),
  });
  return parseResponse<PrmMaxPowerData>(response);
}

export async function fetchPrmLoadCurve(token: string, prmId: string, days = 7): Promise<PrmLoadCurveData> {
  const response = await fetch(`${apiBaseUrl}/energie/${encodeURIComponent(prmId)}/load-curve?days=${days}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<PrmLoadCurveData>(response);
}

export async function fetchPrmAnnualProfile(token: string, prmId: string): Promise<PrmAnnualProfile> {
  const response = await fetch(`${apiBaseUrl}/energie/${encodeURIComponent(prmId)}/annual-profile`, {
    headers: buildHeaders(token),
  });
  return parseResponse<PrmAnnualProfile>(response);
}

export async function fetchPrmDailyConsumption(token: string, prmId: string, days = 90): Promise<PrmDailyConsumption> {
  const response = await fetch(`${apiBaseUrl}/energie/${encodeURIComponent(prmId)}/daily-consumption?days=${days}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<PrmDailyConsumption>(response);
}

export async function fetchDjuMonthly(token: string): Promise<DjuMonthPoint[]> {
  const response = await fetch(`${apiBaseUrl}/energie/dju/monthly`, {
    headers: buildHeaders(token),
  });
  return parseResponse<DjuMonthPoint[]>(response);
}

export type FluidsElecSeries = {
  monthly: { month: string; kwh: number }[];
  suppliers: { supplier: string; annual_kwh: number }[];
};

export type FluidsElecObservedPricePoint = {
  year: number;
  invoice_count: number;
  total_ttc: number;
  total_ht: number | null;
  total_kwh: number;
  eur_per_kwh_ttc: number;
  eur_per_kwh_ht: number | null;
};

export type FluidsElecObservedPrice = {
  points: FluidsElecObservedPricePoint[];
  current_year: number | null;
  current_eur_per_kwh_ttc: number | null;
  projected_5y_eur_per_kwh_ttc: number | null;
  projected_10y_eur_per_kwh_ttc: number | null;
  method: string;
};

export async function fetchFluidsElecSeries(token: string): Promise<FluidsElecSeries> {
  const response = await fetch(`${apiBaseUrl}/energie/fluids/elec-series`, {
    headers: buildHeaders(token),
  });
  return parseResponse<FluidsElecSeries>(response);
}

export async function fetchFluidsElecObservedPrice(token: string): Promise<FluidsElecObservedPrice> {
  const response = await fetch(`${apiBaseUrl}/energie/fluids/elec-observed-price`, {
    headers: buildHeaders(token),
  });
  return parseResponse<FluidsElecObservedPrice>(response);
}

export type DjuPerfPoint = {
  month: string;
  kwh: number;
  dju: number;
  ratio_kwh_per_dju: number;
};

export type DjuSidePerf = {
  baseline_ratio_kwh_per_dju: number | null;
  months_in_baseline: number;
  last_month: DjuPerfPoint | null;
  last_month_ecart_percent: number | null;
  last_month_status: string | null;
  timeseries: DjuPerfPoint[];
  has_data: boolean;
  is_reliable: boolean;
};

export type PrmDjuPerformance = {
  usage_point_id: string;
  heating: DjuSidePerf;
  cooling: DjuSidePerf;
};

export type SyncStatus = {
  status: string;
  started_at: string | null;
  finished_at: string | null;
  prms_total: number;
  prms_done: number;
  rows_added: number;
  date_from: string | null;
  date_to: string | null;
  last_sync_date: string | null;
  error: string | null;
  log: string[];
};

export async function fetchPrmDjuPerformance(token: string, prmId: string): Promise<PrmDjuPerformance> {
  const response = await fetch(`${apiBaseUrl}/energie/${encodeURIComponent(prmId)}/dju-performance`, {
    headers: buildHeaders(token),
  });
  return parseResponse<PrmDjuPerformance>(response);
}

export type DjuSeasonMonthPoint = {
  month_num: string;
  dju: number;
  kwh: number;
  /** Consommation hors talon : c'est elle qui alimente le ratio. */
  kwh_thermo: number | null;
  ratio: number;
};

export type DjuSeasonYear = {
  label: string;
  months: DjuSeasonMonthPoint[];
};

export type DjuSeasonMonthDiagnostic = {
  season_label: string;
  month_num: string;
  month_label: string;
  status: string;
  reason: string;
  dju: number | null;
  kwh: number | null;
};

export type DjuSeasonData = {
  months_order: string[];
  months_labels: string[];
  years: DjuSeasonYear[];
  cible_by_month: Record<string, number | null>;
  current_label: string | null;
  current_ecart_percent: number | null;
  current_months_count: number;
  expected_months_count: number;
  current_is_complete: boolean;
  month_diagnostics: DjuSeasonMonthDiagnostic[];
  has_data: boolean;
  /** Talon mensuel retire avant calcul du ratio (null = ratio sur conso totale). */
  baseload_kwh_per_month: number | null;
};

export type PrmDjuSeasonal = {
  usage_point_id: string;
  winter: DjuSeasonData;
  summer: DjuSeasonData;
};

export async function fetchPrmDjuSeasonal(token: string, prmId: string): Promise<PrmDjuSeasonal> {
  const response = await fetch(`${apiBaseUrl}/energie/${encodeURIComponent(prmId)}/dju-seasonal`, {
    headers: buildHeaders(token),
  });
  return parseResponse<PrmDjuSeasonal>(response);
}

export async function fetchSyncStatus(token: string): Promise<SyncStatus> {
  const response = await fetch(`${apiBaseUrl}/energie/sync/status`, {
    headers: buildHeaders(token),
  });
  return parseResponse<SyncStatus>(response);
}

export async function startSync(
  token: string,
  options?: { historyDays?: number; prmLimit?: number },
): Promise<{ message: string }> {
  const params = new URLSearchParams();
  if (options?.historyDays) params.set("history_days", String(options.historyDays));
  if (options?.prmLimit) params.set("prm_limit", String(options.prmLimit));
  const qs = params.toString() ? `?${params.toString()}` : "";
  const response = await fetch(`${apiBaseUrl}/energie/sync/start${qs}`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<{ message: string }>(response);
}

export async function fetchMaxPowerSyncStatus(token: string): Promise<SyncStatus> {
  const response = await fetch(`${apiBaseUrl}/energie/sync/max-power/status`, {
    headers: buildHeaders(token),
  });
  return parseResponse<SyncStatus>(response);
}

export async function startMaxPowerSync(
  token: string,
  options?: { historyDays?: number; prmLimit?: number },
): Promise<{ message: string }> {
  const params = new URLSearchParams();
  if (options?.historyDays) params.set("history_days", String(options.historyDays));
  if (options?.prmLimit) params.set("prm_limit", String(options.prmLimit));
  const qs = params.toString() ? `?${params.toString()}` : "";
  const response = await fetch(`${apiBaseUrl}/energie/sync/max-power/start${qs}`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<{ message: string }>(response);
}

export type DjuSyncStatus = {
  status: string;
  last_sync_date: string | null;
  rows_added: number;
  error: string | null;
  log: string[];
};

export type CustomerSyncStatus = {
  status: string;
  started_at: string | null;
  finished_at: string | null;
  last_sync_at: string | null;
  sources_total: number;
  sources_done: number;
  current_source: string | null;
  prms_total: number;
  prms_done: number;
  rows_upserted: number;
  changes_detected: number;
  error: string | null;
  log: string[];
};

export async function fetchDjuSyncStatus(token: string): Promise<DjuSyncStatus> {
  const response = await fetch(`${apiBaseUrl}/energie/sync/dju/status`, {
    headers: buildHeaders(token),
  });
  return parseResponse<DjuSyncStatus>(response);
}

export async function fetchCustomerSyncStatus(token: string): Promise<CustomerSyncStatus> {
  const response = await fetch(`${apiBaseUrl}/energie/sync/customer/status`, {
    headers: buildHeaders(token),
  });
  return parseResponse<CustomerSyncStatus>(response);
}

export type LoadCurveSyncStatus = {
  status: string;
  started_at: string | null;
  finished_at: string | null;
  chunks_total: number;
  chunks_done: number;
  rows_added: number;
  date_from: string | null;
  date_to: string | null;
  last_sync_date: string | null;
  error: string | null;
  log: string[];
};

export async function fetchLoadCurveSyncStatus(token: string): Promise<LoadCurveSyncStatus> {
  const response = await fetch(`${apiBaseUrl}/energie/sync/load-curve/status`, {
    headers: buildHeaders(token),
  });
  return parseResponse<LoadCurveSyncStatus>(response);
}

export async function startLoadCurveSync(
  token: string,
  options?: { historyDays?: number; prmLimit?: number; resetState?: boolean },
): Promise<{ message: string }> {
  const params = new URLSearchParams();
  if (options?.historyDays) params.set("history_days", String(options.historyDays));
  if (options?.prmLimit) params.set("prm_limit", String(options.prmLimit));
  if (options?.resetState) params.set("reset_state", "true");
  const qs = params.toString() ? `?${params.toString()}` : "";
  const response = await fetch(`${apiBaseUrl}/energie/sync/load-curve/start${qs}`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<{ message: string }>(response);
}

export async function startDjuSync(token: string): Promise<{ message: string }> {
  const response = await fetch(`${apiBaseUrl}/energie/sync/dju/start`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<{ message: string }>(response);
}

export async function startCustomerSync(token: string): Promise<{ message: string }> {
  const response = await fetch(`${apiBaseUrl}/energie/sync/customer/start`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<{ message: string }>(response);
}

export type DataSourceRange = {
  first_date: string | null;
  last_date: string | null;
  row_count: number;
};

export type DataRanges = {
  consumption: DataSourceRange;
  max_power: DataSourceRange;
  load_curve: DataSourceRange;
  dju: DataSourceRange;
  contracts: { count: number };
};

export async function fetchDataRanges(token: string): Promise<DataRanges> {
  const response = await fetch(`${apiBaseUrl}/energie/data-ranges`, {
    headers: buildHeaders(token),
  });
  return parseResponse<DataRanges>(response);
}

export type EnergyDataAuditSource = {
  label: string;
  filename: string;
  first_date: string | null;
  last_date: string | null;
  row_count: number;
  prm_count: number;
  missing_prm_count: number;
  weak_prm_count: number;
  outside_contract_prm_count: number;
  bad_date_rows: number;
};

export type MeterProfile = "non_powered" | "non_communicant" | "communicant_closed" | "communicant_open" | "unknown";

export type EnedisOutcome =
  | "ok_data"
  | "ok_empty"
  | "access_not_subscribed"
  | "forbidden"
  | "not_found"
  | "not_eligible"
  | "cdc_inactive"
  | "invalid_period"
  | "invalid_request"
  | "quota_exceeded"
  | "error"
  | "error_technical"
  | null;

export type EnergyDataAuditRow = {
  usage_point_id: string;
  name: string;
  segment: string;
  contractor: string | null;
  tariff: string | null;
  subscribed_power_kva: number | null;
  service_level: string | null;
  connection_state: string | null;
  meter_profile: MeterProfile;
  present_sources: string[];
  missing_sources: string[];
  weak_sources: string[];
  coverage_days: Record<string, number>;
  first_dates: Record<string, string | null>;
  last_dates: Record<string, string | null>;
  enedis_outcomes: Record<string, EnedisOutcome>;
  probable_reason: string;
  correctable_actions: string[];
  severity: string;
};

export type EnergyDataAudit = {
  contracts_count: number;
  sources: Record<string, EnergyDataAuditSource>;
  combo_counts: Record<string, number>;
  missing_by_segment: Record<string, Record<string, number>>;
  profile_counts: Record<MeterProfile, number>;
  summary: {
    all_sources: number;
    partial_sources: number;
    no_source: number;
    info: number;
    with_warnings: number;
    critical: number;
  };
  correctable: Record<string, number>;
  rows: EnergyDataAuditRow[];
};

export async function fetchDataAudit(token: string): Promise<EnergyDataAudit> {
  const response = await fetch(`${apiBaseUrl}/energie/data-audit`, {
    headers: buildHeaders(token),
  });
  return parseResponse<EnergyDataAudit>(response);
}

// â”€â”€ Billing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export type BillingGroupItem = {
  supplier: string;
  tariff_code: string;
  tariff_label: string;
  prm_count: number;
  prm_ids: string[];
  config_id: number | null;
  is_configured: boolean;
};

export type BillingConfigOut = {
  id: number;
  city_id: number;
  supplier: string;
  tariff_code: string;
  tariff_label: string | null;
  has_hphc: boolean;
  representative_prm_id: string | null;
  created_at: string;
  updated_at: string;
};

export type BillingPriceEntryOut = {
  id: number;
  config_id: number;
  year: number | null;
  component: string;
  value: number;
  unit: string | null;
};

export type BillingHphcSlotOut = {
  id: number;
  config_id: number;
  day_type: string;
  start_time: string;
  end_time: string;
  period: string;
};

export type BillingPriceEntryIn = {
  year: number | null;
  component: string;
  value: number;
  unit: string | null;
};

export type BillingHphcSlotIn = {
  day_type: string;
  start_time: string;
  end_time: string;
  period: string;
};

export async function fetchBillingGroups(token: string): Promise<BillingGroupItem[]> {
  const response = await fetch(`${apiBaseUrl}/billing/groups`, { headers: buildHeaders(token) });
  return parseResponse<BillingGroupItem[]>(response);
}

export async function fetchBillingConfigs(token: string): Promise<BillingConfigOut[]> {
  const response = await fetch(`${apiBaseUrl}/billing/configs`, { headers: buildHeaders(token) });
  return parseResponse<BillingConfigOut[]>(response);
}

export async function createBillingConfig(
  token: string,
  payload: { supplier: string; tariff_code: string; tariff_label?: string; has_hphc?: boolean; representative_prm_id?: string },
): Promise<BillingConfigOut> {
  const response = await fetch(`${apiBaseUrl}/billing/configs`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<BillingConfigOut>(response);
}

export async function patchBillingConfig(
  token: string,
  configId: number,
  payload: { has_hphc?: boolean; representative_prm_id?: string; tariff_label?: string },
): Promise<BillingConfigOut> {
  const response = await fetch(`${apiBaseUrl}/billing/configs/${configId}`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<BillingConfigOut>(response);
}

export async function deleteBillingConfig(token: string, configId: number): Promise<void> {
  await fetch(`${apiBaseUrl}/billing/configs/${configId}`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });
}

export async function fetchBillingPrices(token: string, configId: number): Promise<BillingPriceEntryOut[]> {
  const response = await fetch(`${apiBaseUrl}/billing/configs/${configId}/prices`, { headers: buildHeaders(token) });
  return parseResponse<BillingPriceEntryOut[]>(response);
}

export async function setBillingPrices(token: string, configId: number, entries: BillingPriceEntryIn[]): Promise<BillingPriceEntryOut[]> {
  const response = await fetch(`${apiBaseUrl}/billing/configs/${configId}/prices`, {
    method: "PUT",
    headers: buildHeaders(token),
    body: JSON.stringify(entries),
  });
  return parseResponse<BillingPriceEntryOut[]>(response);
}

export async function fetchBillingHphcSlots(token: string, configId: number): Promise<BillingHphcSlotOut[]> {
  const response = await fetch(`${apiBaseUrl}/billing/configs/${configId}/hphc-slots`, { headers: buildHeaders(token) });
  return parseResponse<BillingHphcSlotOut[]>(response);
}

export async function setBillingHphcSlots(token: string, configId: number, slots: BillingHphcSlotIn[]): Promise<BillingHphcSlotOut[]> {
  const response = await fetch(`${apiBaseUrl}/billing/configs/${configId}/hphc-slots`, {
    method: "PUT",
    headers: buildHeaders(token),
    body: JSON.stringify(slots),
  });
  return parseResponse<BillingHphcSlotOut[]>(response);
}

// --- Matrice comptable ENGIE (codification) + fiche de liaison ---

export type EnergyAccountingSiteMapping = {
  id: number;
  city_id: number | null;
  prm_id: string;
  site_name: string | null;
  regroupement: string | null;
  manager: string | null;
  service_code: string | null;
  service_label: string | null;
  function_code: string | null;
  function_label: string | null;
  antenna_code: string | null;
  antenna_label: string | null;
  operation_code: string | null;
  operation_label: string | null;
  active: boolean;
  notes: string | null;
};

export type EnergyAccountingNatureRule = {
  id: number;
  city_id: number | null;
  supplier: string;
  market: string | null;
  billed_item: string;
  frequency: string | null;
  accounting_nature: string;
  accounting_label: string | null;
  active: boolean;
  notes: string | null;
};

export type EnergyCodificationImportResult = {
  filename: string | null;
  nature_rules_created: number;
  nature_rules_updated: number;
  site_mappings_created: number;
  site_mappings_updated: number;
  errors: string[];
};

export type EnergyLiaisonPreviewRow = {
  prm_id: string | null;
  site_name: string | null;
  poste: string | null;
  label: string | null;
  amount_ht: number | null;
  service_code: string | null;
  function_code: string | null;
  antenna_code: string | null;
  operation_code: string | null;
  accounting_nature: string | null;
  accounting_label: string | null;
  status: string;
};

export type EnergyLiaisonPreview = {
  invoice_number: string | null;
  rows_count: number;
  blocked_count: number;
  rows: EnergyLiaisonPreviewRow[];
};

export async function fetchEnergySiteMappings(token: string): Promise<EnergyAccountingSiteMapping[]> {
  const r = await fetch(`${apiBaseUrl}/billing/accounting/site-mappings`, { headers: buildHeaders(token) });
  return parseResponse<EnergyAccountingSiteMapping[]>(r);
}

export async function fetchEnergyNatureRules(token: string): Promise<EnergyAccountingNatureRule[]> {
  const r = await fetch(`${apiBaseUrl}/billing/accounting/nature-rules`, { headers: buildHeaders(token) });
  return parseResponse<EnergyAccountingNatureRule[]>(r);
}

export async function updateEnergySiteMapping(
  token: string, id: number, patch: Partial<EnergyAccountingSiteMapping>,
): Promise<EnergyAccountingSiteMapping> {
  const r = await fetch(`${apiBaseUrl}/billing/accounting/site-mappings/${id}`, {
    method: "PATCH", headers: buildHeaders(token), body: JSON.stringify(patch),
  });
  return parseResponse<EnergyAccountingSiteMapping>(r);
}

export async function updateEnergyNatureRule(
  token: string, id: number, patch: Partial<EnergyAccountingNatureRule>,
): Promise<EnergyAccountingNatureRule> {
  const r = await fetch(`${apiBaseUrl}/billing/accounting/nature-rules/${id}`, {
    method: "PATCH", headers: buildHeaders(token), body: JSON.stringify(patch),
  });
  return parseResponse<EnergyAccountingNatureRule>(r);
}

export async function createEnergyNatureRule(
  token: string, payload: Partial<EnergyAccountingNatureRule> & { billed_item: string; accounting_nature: string },
): Promise<EnergyAccountingNatureRule> {
  const r = await fetch(`${apiBaseUrl}/billing/accounting/nature-rules`, {
    method: "POST", headers: buildHeaders(token), body: JSON.stringify(payload),
  });
  return parseResponse<EnergyAccountingNatureRule>(r);
}

export async function deleteEnergyNatureRule(token: string, id: number): Promise<void> {
  const r = await fetch(`${apiBaseUrl}/billing/accounting/nature-rules/${id}`, {
    method: "DELETE", headers: buildHeaders(token),
  });
  return parseResponse<void>(r);
}

export async function createEnergySiteMapping(
  token: string, payload: Partial<EnergyAccountingSiteMapping> & { prm_id: string },
): Promise<EnergyAccountingSiteMapping> {
  const r = await fetch(`${apiBaseUrl}/billing/accounting/site-mappings`, {
    method: "POST", headers: buildHeaders(token), body: JSON.stringify(payload),
  });
  return parseResponse<EnergyAccountingSiteMapping>(r);
}

export async function deleteEnergySiteMapping(token: string, id: number): Promise<void> {
  const r = await fetch(`${apiBaseUrl}/billing/accounting/site-mappings/${id}`, {
    method: "DELETE", headers: buildHeaders(token),
  });
  return parseResponse<void>(r);
}

export async function importEnergyCodification(token: string, file: File): Promise<EnergyCodificationImportResult> {
  const form = new FormData();
  form.append("file", file);
  const r = await fetch(`${apiBaseUrl}/billing/accounting/import-codification`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  return parseResponse<EnergyCodificationImportResult>(r);
}

export async function bootstrapEnergySiteMappings(token: string): Promise<{ created: number; existing: number }> {
  const r = await fetch(`${apiBaseUrl}/billing/accounting/site-mappings/bootstrap`, {
    method: "POST", headers: buildHeaders(token),
  });
  return parseResponse<{ created: number; existing: number }>(r);
}

export async function fetchInvoiceCodification(token: string, importId: number): Promise<EnergyLiaisonPreview> {
  const r = await fetch(`${apiBaseUrl}/billing/invoices/imports/${importId}/codification`, { headers: buildHeaders(token) });
  return parseResponse<EnergyLiaisonPreview>(r);
}

export async function downloadInvoiceLiaison(token: string, importId: number, invoiceLabel: string): Promise<void> {
  const r = await fetch(`${apiBaseUrl}/billing/invoices/imports/${importId}/liaison.xlsx`, { headers: buildHeaders(token) });
  if (!r.ok) throw new Error(await r.text());
  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `fiche-liaison-engie-${invoiceLabel}.xlsx`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// --- Energy invoice imports ---

export type EnergyInvoiceImport = {
  id: number;
  city_id: number;
  uploaded_by_user_id: number;
  source: string;
  original_filename: string;
  content_type: string | null;
  file_size_bytes: number;
  sha256: string;
  supplier_guess: string | null;
  energy_type: string;
  invoice_number: string | null;
  invoice_date: string | null;
  period_start: string | null;
  period_end: string | null;
  regroupement: string | null;
  market_reference: string | null;
  contract_holder: string | null;
  total_ht: number | null;
  total_ttc: number | null;
  total_consumption_kwh: number | null;
  site_count: number | null;
  status: string;
  analysis_status: string;
  control_status: string;
  control_errors_count: number;
  control_warnings_count: number;
  filter_facets: {
    invoice_months: string[];
    prm_ids: string[];
    fic_numbers: string[];
    site_names: string[];
    site_cities: string[];
    segments: string[];
    tariff_codes: string[];
    tariff_option_labels: string[];
    document_types: string[];
  };
  decision_status: string;
  decision_comment: string | null;
  decision_by_user_id: number | null;
  decision_updated_at: string | null;
  finance_exported_at: string | null;
  control_issues: Array<{
    severity: string;
    code: string;
    message: string;
    scope: string | null;
  }>;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type EnergyInvoiceLine = {
  family?: string;
  label?: string;
  normalized_component?: string | null;
  poste?: string | null;
  period_start?: string | null;
  period_end?: string | null;
  quantity?: number | null;
  quantity_unit?: string | null;
  unit_price_ht?: number | null;
  unit_price_unit?: string | null;
  amount_ht?: number | null;
  vat_rate?: number | null;
  raw_line?: string | null;
};

export type EnergyInvoiceSite = {
  fic_number?: string | null;
  prm_id?: string | null;
  site_name?: string | null;
  regroupement?: string | null;
  period_start?: string | null;
  period_end?: string | null;
  delivery_site_name?: string | null;
  delivery_address?: string | null;
  tariff_option_label?: string | null;
  segment?: string | null;
  subscribed_power_kva?: number | null;
  max_reached_power_kva?: number | null;
  total_ht?: number | null;
  total_vat?: number | null;
  total_ttc?: number | null;
  invoice_lines?: EnergyInvoiceLine[];
};

export type EnergyInvoiceAnalysisResult = {
  supplier?: string;
  document_type?: string;
  page_count?: number;
  site_count?: number;
  fic_count?: number;
  invoice?: Record<string, unknown>;
  sites?: EnergyInvoiceSite[];
  parser_warnings?: string[];
};

export type EnergyInvoiceControlReport = {
  status?: string;
  error_count?: number;
  warning_count?: number;
  issues?: EnergyInvoiceImport["control_issues"];
  bpu?: Record<string, unknown>;
  fixed_charges?: Record<string, unknown>;
  turpe?: Record<string, unknown>;
  taxes?: Record<string, unknown>;
  periods?: Record<string, unknown>;
  consumption?: Record<string, unknown>;
  power?: Record<string, unknown>;
};

export type EnergyInvoiceImportDetail = EnergyInvoiceImport & {
  analysis_result: EnergyInvoiceAnalysisResult | null;
  control_report: EnergyInvoiceControlReport | null;
};

export type EnergyInvoiceDecisionPayload = {
  decision_status: "to_review" | "approved" | "rejected" | "dispute_sent";
  decision_comment?: string | null;
};

export type TurpeVersion = {
  code: string;
  family: string;
  label: string;
  valid_from: string;
  valid_to: string;
  next_expected_update: string;
  successor_hint: string;
  source_label: string;
  source_url: string;
  cre_deliberation_url: string;
  cre_modification_url: string;
  tariff_keys: string[];
};

export type EnergyInvoiceUploadResponse = {
  invoice_import: EnergyInvoiceImport;
  is_duplicate: boolean;
  message: string;
};

export type EnergyInvoiceBatchItem = {
  id: number;
  invoice_import_id: number | null;
  original_filename: string;
  archive_filename: string | null;
  content_type: string | null;
  file_size_bytes: number | null;
  sha256: string | null;
  status: string;
  message: string | null;
  created_at: string;
};

export type EnergyInvoiceBatch = {
  id: number;
  city_id: number;
  uploaded_by_user_id: number;
  source: string;
  status: string;
  file_count: number;
  imported_count: number;
  duplicate_count: number;
  ignored_count: number;
  error_count: number;
  created_at: string;
  updated_at: string;
};

export type EnergyInvoiceBatchDetail = EnergyInvoiceBatch & {
  items: EnergyInvoiceBatchItem[];
};

export type EnergyInvoiceMonthlyConsumptionPoint = {
  month: string;
  billed_kwh: number;
  enedis_kwh: number | null;
  delta_kwh: number | null;
  invoice_count: number;
  billed_prm_count: number;
  prm_count: number;
  enedis_prm_count: number;
};

export type EnergyInvoiceMonthlyConsumption = {
  year: number;
  generated_from: string;
  generated_to: string;
  billed_total_kwh: number;
  enedis_total_kwh: number | null;
  delta_total_kwh: number | null;
  invoice_count: number;
  prm_count: number;
  enedis_prm_count: number;
  months: EnergyInvoiceMonthlyConsumptionPoint[];
};

export type EnergyInvoiceMonthlyConsumptionFilters = {
  search?: string;
  controlStatuses?: string[];
  decisionStatuses?: string[];
  regroupements?: string[];
  contractHolders?: string[];
  issueFamilies?: string[];
  issueCodes?: string[];
  invoiceMonths?: string[];
  prmIds?: string[];
  ficNumbers?: string[];
  siteNames?: string[];
  siteCities?: string[];
  segments?: string[];
  tariffCodes?: string[];
  tariffOptionLabels?: string[];
  documentTypes?: string[];
};

export async function fetchTurpeVersions(token: string): Promise<TurpeVersion[]> {
  const response = await fetch(`${apiBaseUrl}/billing/turpe/versions`, {
    headers: buildHeaders(token),
  });
  return parseResponse<TurpeVersion[]>(response);
}

export async function fetchEnergyInvoiceMonthlyConsumption(
  token: string,
  year: number,
  filters: EnergyInvoiceMonthlyConsumptionFilters = {},
): Promise<EnergyInvoiceMonthlyConsumption> {
  const params = new URLSearchParams({ year: String(year) });
  const search = filters.search?.trim();
  if (search) params.set("search", search);
  filters.controlStatuses?.forEach((value) => params.append("control_status", value));
  filters.decisionStatuses?.forEach((value) => params.append("decision_status", value));
  filters.regroupements?.forEach((value) => params.append("regroupement", value));
  filters.contractHolders?.forEach((value) => params.append("contract_holder", value));
  filters.issueFamilies?.forEach((value) => params.append("issue_family", value));
  filters.issueCodes?.forEach((value) => params.append("issue_code", value));
  filters.invoiceMonths?.forEach((value) => params.append("invoice_month", value));
  filters.prmIds?.forEach((value) => params.append("prm_id", value));
  filters.ficNumbers?.forEach((value) => params.append("fic_number", value));
  filters.siteNames?.forEach((value) => params.append("site_name", value));
  filters.siteCities?.forEach((value) => params.append("site_city", value));
  filters.segments?.forEach((value) => params.append("segment", value));
  filters.tariffCodes?.forEach((value) => params.append("tariff_code", value));
  filters.tariffOptionLabels?.forEach((value) => params.append("tariff_option_label", value));
  filters.documentTypes?.forEach((value) => params.append("document_type", value));
  const response = await fetch(`${apiBaseUrl}/billing/invoices/consumption-monthly?${params.toString()}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<EnergyInvoiceMonthlyConsumption>(response);
}

export async function fetchEnergyInvoiceImports(token: string): Promise<EnergyInvoiceImport[]> {
  const response = await fetch(`${apiBaseUrl}/billing/invoices/imports`, {
    headers: buildHeaders(token),
  });
  return parseResponse<EnergyInvoiceImport[]>(response);
}

export async function fetchEnergyInvoiceBatches(token: string): Promise<EnergyInvoiceBatch[]> {
  const response = await fetch(`${apiBaseUrl}/billing/invoices/batches`, {
    headers: buildHeaders(token),
  });
  return parseResponse<EnergyInvoiceBatch[]>(response);
}

export async function fetchEnergyInvoiceBatch(token: string, batchId: number): Promise<EnergyInvoiceBatchDetail> {
  const response = await fetch(`${apiBaseUrl}/billing/invoices/batches/${batchId}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<EnergyInvoiceBatchDetail>(response);
}

export async function fetchEnergyInvoiceImport(token: string, importId: number): Promise<EnergyInvoiceImportDetail> {
  const response = await fetch(`${apiBaseUrl}/billing/invoices/imports/${importId}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<EnergyInvoiceImportDetail>(response);
}

export async function uploadEnergyInvoiceImport(token: string, file: File): Promise<EnergyInvoiceUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${apiBaseUrl}/billing/invoices/imports`, {
    method: "POST",
    headers: buildAuthHeaders(token),
    body: formData,
  });
  return parseResponse<EnergyInvoiceUploadResponse>(response);
}

// RÃ©ponse de /billing/invoices/imports/xlsx â€” rÃ©sumÃ© d'import multi-factures depuis l'export ENGIE
export type EnergyInvoiceXlsxImportSummary = {
  source: "engie_xlsx_export";
  filename: string;
  total_bordereaux: number;
  created: number;
  updated: number;
  duplicates: number;
  errors: number;
  imports: Array<{
    id: number;
    invoice_number: string | null;
    control_status: string;
    site_count: number | null;
    total_ttc: number | null;
  }>;
  updates: Array<{
    id: number;
    invoice_number: string | null;
    control_status: string;
    site_count: number | null;
    total_ttc: number | null;
    decision_preserved: string | null;
    repair?: boolean;
  }>;
  duplicates_detail: Array<{
    invoice_number: string;
    existing_import_id: number;
    existing_source: string;
  }>;
  errors_detail: Array<{ invoice_number: string | null; message: string }>;
};

export type DeleteAllInvoiceImportsResult = {
  deleted: number;
  files_removed: number;
  files_kept: number;
};

export async function deleteAllEnergyInvoiceImports(token: string): Promise<DeleteAllInvoiceImportsResult> {
  const response = await fetch(`${apiBaseUrl}/billing/invoices/imports?confirm=DELETE`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });
  return parseResponse<DeleteAllInvoiceImportsResult>(response);
}

export async function uploadEngieXlsxExport(
  token: string,
  file: File,
  options?: { forceUpdate?: boolean },
): Promise<EnergyInvoiceBatchDetail> {
  const formData = new FormData();
  formData.append("file", file);
  const qs = options?.forceUpdate ? "?force_update=true" : "";
  const response = await fetch(`${apiBaseUrl}/billing/invoices/imports/xlsx${qs}`, {
    method: "POST",
    headers: buildAuthHeaders(token),
    body: formData,
  });
  return parseResponse<EnergyInvoiceBatchDetail>(response);
}

export async function uploadEdfCsvExport(
  token: string,
  file: File,
  options?: { forceUpdate?: boolean },
): Promise<EnergyInvoiceBatchDetail> {
  const formData = new FormData();
  formData.append("file", file);
  const qs = options?.forceUpdate ? "?force_update=true" : "";
  const response = await fetch(`${apiBaseUrl}/billing/invoices/imports/edf-csv${qs}`, {
    method: "POST",
    headers: buildAuthHeaders(token),
    body: formData,
  });
  return parseResponse<EnergyInvoiceBatchDetail>(response);
}

export async function uploadEnergyInvoiceBatch(token: string, files: File[]): Promise<EnergyInvoiceBatchDetail> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  const response = await fetch(`${apiBaseUrl}/billing/invoices/batches`, {
    method: "POST",
    headers: buildAuthHeaders(token),
    body: formData,
  });
  return parseResponse<EnergyInvoiceBatchDetail>(response);
}

export async function analyzeEnergyInvoiceImport(token: string, importId: number): Promise<EnergyInvoiceImport> {
  const response = await fetch(`${apiBaseUrl}/billing/invoices/imports/${importId}/analyze`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<EnergyInvoiceImport>(response);
}

export async function deleteEnergyInvoiceImport(token: string, importId: number): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/billing/invoices/imports/${importId}`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });
  if (!response.ok && response.status !== 204) {
    await parseResponse<void>(response);
  }
}

export async function updateEnergyInvoiceDecision(
  token: string,
  importId: number,
  payload: EnergyInvoiceDecisionPayload,
): Promise<EnergyInvoiceImportDetail> {
  const response = await fetch(`${apiBaseUrl}/billing/invoices/imports/${importId}/decision`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<EnergyInvoiceImportDetail>(response);
}

// â”€â”€ ENEDIS Async (Phase B + C) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export type EnedisAsyncJobType = "CDC" | "ENERGIE";

export type EnedisAsyncJobStatus =
  | "requested"
  | "file_received"
  | "decrypted"
  | "parsed"
  | "success"
  | "error";

export type EnedisAsyncJob = {
  id: number;
  dossier_id: number;
  type_donnee: EnedisAsyncJobType;
  date_start: string;
  date_end: string;
  prm_count: number;
  canal_contact_id: string;
  status: EnedisAsyncJobStatus;
  requested_at: string | null;
  ftp_filename: string | null;
  received_at: string | null;
  parsed_at: string | null;
  finished_at: string | null;
  rows_added: number | null;
  error_message: string | null;
};

export type EnedisAsyncStartPayload = {
  type_donnee: EnedisAsyncJobType;
  date_start: string;
  date_end: string;
};

export type EnedisAsyncStartResponse = {
  message: string;
  dossier_ids: number[];
  jobs: EnedisAsyncJob[];
};

export type EnedisAsyncBackfillFullResponse = {
  message: string;
  background?: boolean;
  already_running?: boolean;
  dossier_ids: { CDC: number[]; ENERGIE: number[] };
  errors?: Array<{
    type_donnee: EnedisAsyncJobType;
    date_start: string;
    date_end: string;
    prm_count: number;
    batch_index?: number;
    batch_count?: number;
    first_prm?: string | null;
    last_prm?: string | null;
    message: string;
  }>;
  summary?: Record<string, {
    prm_count: number;
    window_count: number;
    batch_size?: number;
    batch_count_per_window?: number;
    expected_dossier_count?: number;
    created_dossier_count?: number;
    date_start?: string;
    date_end?: string;
  }>;
};

export type EnedisAsyncJobsSummary = {
  total: number;
  by_status: Record<EnedisAsyncJobStatus, number>;
  by_type: Record<EnedisAsyncJobType, Record<EnedisAsyncJobStatus, number>>;
  inflight_count: number;
  terminal_count: number;
  error_count: number;
  stale_requested_count: number;
  oldest_inflight_at: string | null;
  latest_requested_at: string | null;
  latest_finished_at: string | null;
  backfill_creation_running: boolean;
  plan: Record<string, {
    prm_count: number;
    window_count: number;
    batch_size?: number;
    batch_count_per_window?: number;
    expected_dossier_count?: number;
    date_start?: string;
    date_end?: string;
  }>;
};

export async function fetchEnedisAsyncJobs(
  token: string,
  filters: { type?: EnedisAsyncJobType; status?: EnedisAsyncJobStatus; limit?: number } = {},
): Promise<EnedisAsyncJob[]> {
  const params = new URLSearchParams();
  if (filters.type) params.set("type_donnee", filters.type);
  if (filters.status) params.set("status", filters.status);
  if (filters.limit) params.set("limit", String(filters.limit));
  const qs = params.toString() ? `?${params.toString()}` : "";
  const response = await fetch(`${apiBaseUrl}/energie/sync/async/jobs${qs}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<EnedisAsyncJob[]>(response);
}

export async function fetchEnedisAsyncJobsSummary(token: string): Promise<EnedisAsyncJobsSummary> {
  const response = await fetch(`${apiBaseUrl}/energie/sync/async/jobs/summary`, {
    headers: buildHeaders(token),
  });
  return parseResponse<EnedisAsyncJobsSummary>(response);
}

export async function startEnedisAsyncJob(
  token: string,
  payload: EnedisAsyncStartPayload,
): Promise<EnedisAsyncStartResponse> {
  const response = await fetch(`${apiBaseUrl}/energie/sync/async/start`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<EnedisAsyncStartResponse>(response);
}

export async function startEnedisAsyncBackfillFull(
  token: string,
): Promise<EnedisAsyncBackfillFullResponse> {
  const response = await fetch(`${apiBaseUrl}/energie/sync/async/backfill-full`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<EnedisAsyncBackfillFullResponse>(response);
}

export async function triggerEnedisAsyncPollNow(token: string): Promise<{ message: string }> {
  const response = await fetch(`${apiBaseUrl}/energie/sync/async/poll-now`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<{ message: string }>(response);
}

// --- Gestion Technique (Equipment) ---

export type EquipmentReference = {
  id: number;
  id_ligne: number;
  code_niveau_1: string;
  libelle_niveau_1: string;
  code_niveau_2: string;
  libelle_niveau_2: string;
  niveau_3: string | null;
  niveau_4: string | null;
  niveau_5: string | null;
  equipement: string;
  sypemi_mini_annees: number | null;
  sypemi_reference_annees: number | null;
  sypemi_maxi_annees: number | null;
  fiche_cee: string | null;
};

export type BuildingEquipment = {
  id: number;
  building_id: number;
  equipment_ref_id: number;
  etat: string;
  quantite: string;
  commentaire: string | null;
  duree_vie_restante: number;
  created_at: string;
  updated_at: string;
  equipment_ref: EquipmentReference | null;
};

export type EquipmentStateCounts = {
  obsolete: number;
  degrade: number;
  moyen: number;
  neuf: number;
  total: number;
  score_sante: number | null;
};

export type BuildingEquipmentSummary = {
  building_id: number;
  counts: EquipmentStateCounts;
};

export type CreateBuildingEquipmentPayload = {
  equipment_ref_id: number;
  etat: string;
  quantite: string;
  commentaire?: string;
};

export type UpdateBuildingEquipmentPayload = {
  etat?: string;
  quantite?: string;
  commentaire?: string;
};

export type BulkCreateEquipmentPayload = {
  items: CreateBuildingEquipmentPayload[];
};

export async function fetchEquipmentReferences(token: string): Promise<EquipmentReference[]> {
  const response = await fetch(`${apiBaseUrl}/equipment/references`, {
    headers: buildHeaders(token),
  });
  return parseResponse<EquipmentReference[]>(response);
}

export async function fetchEquipmentSummaries(token: string): Promise<BuildingEquipmentSummary[]> {
  const response = await fetch(`${apiBaseUrl}/equipment/summaries`, {
    headers: buildHeaders(token),
  });
  return parseResponse<BuildingEquipmentSummary[]>(response);
}

export async function fetchBuildingEquipments(token: string, buildingId: number): Promise<BuildingEquipment[]> {
  const response = await fetch(`${apiBaseUrl}/equipment/buildings/${buildingId}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<BuildingEquipment[]>(response);
}

export async function createBuildingEquipmentRequest(
  token: string,
  buildingId: number,
  payload: CreateBuildingEquipmentPayload,
): Promise<BuildingEquipment> {
  const response = await fetch(`${apiBaseUrl}/equipment/buildings/${buildingId}`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<BuildingEquipment>(response);
}

export async function bulkCreateBuildingEquipments(
  token: string,
  buildingId: number,
  payload: BulkCreateEquipmentPayload,
): Promise<BuildingEquipment[]> {
  const response = await fetch(`${apiBaseUrl}/equipment/buildings/${buildingId}/bulk`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<BuildingEquipment[]>(response);
}

export async function updateBuildingEquipmentRequest(
  token: string,
  buildingId: number,
  equipmentId: number,
  payload: UpdateBuildingEquipmentPayload,
): Promise<BuildingEquipment> {
  const response = await fetch(`${apiBaseUrl}/equipment/buildings/${buildingId}/${equipmentId}`, {
    method: "PUT",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<BuildingEquipment>(response);
}

export async function deleteBuildingEquipmentRequest(
  token: string,
  buildingId: number,
  equipmentId: number,
): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/equipment/buildings/${buildingId}/${equipmentId}`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });
  return parseResponse<void>(response);
}

export async function fetchBuildingEquipmentSummary(
  token: string,
  buildingId: number,
): Promise<EquipmentStateCounts> {
  const response = await fetch(`${apiBaseUrl}/equipment/buildings/${buildingId}/summary`, {
    headers: buildHeaders(token),
  });
  return parseResponse<EquipmentStateCounts>(response);
}

// ===========================================================================
// BPU â€” Bordereaux de Prix Unitaires (suivi temporel des prix d'Ã©nergie)
// ===========================================================================

export type BpuFormulaComponent = {
  code: string; // "fourniture" | "capacite" | "cee" | "go"
  label: string;
  description: string;
};

export type BpuFormulaSegment = { code: string; label: string };
export type BpuFormulaPeriod = { code: string; label: string };

export type BpuFormula = {
  expression: string;
  unit_target: string; // "â‚¬HTT/MWh"
  components: BpuFormulaComponent[];
  segments: BpuFormulaSegment[];
  periods: BpuFormulaPeriod[];
};

export type BpuDocumentSummary = {
  id: number;
  supplier: string;
  valid_year: number;
  valid_from: string | null;
  valid_to: string | null;
  market_subsequent: number | null;
  lot_number: number;
  amendment_number: number | null;
  amendment_label: string | null;
  pdf_filename: string;
  pdf_relative_path: string | null;
  signature_date: string | null;
  extraction_status: string;
  extraction_method: string | null;
  extraction_confidence: number | null;
  created_at: string;
  updated_at: string;
};

export type BpuPriceComponent = {
  id: number;
  period_id: number;
  component_type: string;
  component_label: string | null;
  price_value: number;
  price_unit: string;
  price_value_eur_per_mwh: number | null;
  is_negative: boolean;
  extraction_confidence: number | null;
  notes: string | null;
};

export type BpuTimePeriod = {
  id: number;
  segment_id: number;
  period_code: string;
  period_label: string | null;
  components: BpuPriceComponent[];
};

export type BpuSegment = {
  id: number;
  document_id: number;
  segment_type: string;
  segment_code: string;
  segment_label: string | null;
  tension_category: string | null;
  turpe_tariff: string | null;
  usage_label: string | null;
  notes: string | null;
  periods: BpuTimePeriod[];
};

export type BpuFixedCharge = {
  id: number;
  document_id: number;
  segment_id: number | null;
  charge_type: string;
  charge_label: string | null;
  charge_value: number;
  charge_unit: string;
  charge_value_eur_per_month: number | null;
  applicable_from: string | null;
  applicable_to: string | null;
  notes: string | null;
};

export type BpuDocumentDetail = BpuDocumentSummary & {
  segments: BpuSegment[];
  fixed_charges: BpuFixedCharge[];
  extraction_notes: string | null;
  signatory_name: string | null;
  signatory_role: string | null;
  docusign_envelope_id: string | null;
};

export type BpuTimelinePoint = {
  document_id: number;
  supplier: string;
  valid_year: number;
  valid_from: string | null;
  market_subsequent: number | null;
  lot_number: number;
  amendment_number: number | null;
  segment_code: string;
  period_code: string;
  component_type: string;
  price_value_eur_per_mwh: number | null;
  price_value: number;
  price_unit: string;
};

export type BpuTurpeEvolutionPoint = {
  effective_date: string;
  family: string;
  event_label: string;
  evolution_percent: number | string;
  cumulative_index: number | string;
  source_label: string;
  source_url: string;
  notes: string | null;
};

export type BpuDocumentFilters = {
  supplier?: string;
  valid_year?: number;
  lot_number?: number;
  market_subsequent?: number;
  extraction_status?: string;
};

export type BpuTimelineFilters = {
  component_type?: string;
  period_code?: string;
  segment_code?: string;
  supplier?: string;
  lot_number?: number;
};

export type BpuImportRequest = {
  source_dir?: string;
  only_filename?: string;
  force?: boolean;
  enable_ocr?: boolean;
};

export type BpuImportResult = {
  filename: string;
  status: string;
  document_id: number | null;
  segments_count: number;
  components_count: number;
  fixed_charges_count: number;
  extraction_method: string | null;
  extraction_confidence: number | null;
  error: string | null;
};

export type BpuImportResponse = {
  total: number;
  succeeded: number;
  failed: number;
  skipped: number;
  results: BpuImportResult[];
};

export type BpuXlsxImportResponse = {
  documents: number;
  segments: number;
  periods: number;
  components: number;
  charges: number;
  skipped_prices: number;
  skipped_charges: number;
  errors: number;
};

function buildQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

export async function fetchBpuFormula(token: string): Promise<BpuFormula> {
  const response = await fetch(`${apiBaseUrl}/bpu/formula`, {
    headers: buildHeaders(token),
  });
  return parseResponse<BpuFormula>(response);
}

export async function fetchBpuDocuments(
  token: string,
  filters: BpuDocumentFilters = {},
): Promise<BpuDocumentSummary[]> {
  const qs = buildQuery(filters);
  const response = await fetch(`${apiBaseUrl}/bpu/documents${qs}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<BpuDocumentSummary[]>(response);
}

export async function fetchBpuDocument(
  token: string,
  documentId: number,
): Promise<BpuDocumentDetail> {
  const response = await fetch(`${apiBaseUrl}/bpu/documents/${documentId}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<BpuDocumentDetail>(response);
}

export async function deleteBpuDocument(token: string, documentId: number): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/bpu/documents/${documentId}`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });
  return parseResponse<void>(response);
}

export async function fetchBpuTimeline(
  token: string,
  filters: BpuTimelineFilters = {},
): Promise<BpuTimelinePoint[]> {
  const qs = buildQuery(filters);
  const response = await fetch(`${apiBaseUrl}/bpu/timeline${qs}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<BpuTimelinePoint[]>(response);
}

export async function fetchBpuTurpeEvolution(token: string): Promise<BpuTurpeEvolutionPoint[]> {
  const response = await fetch(`${apiBaseUrl}/bpu/turpe-evolution`, {
    headers: buildHeaders(token),
  });
  return parseResponse<BpuTurpeEvolutionPoint[]>(response);
}

export async function triggerBpuImport(
  token: string,
  payload: BpuImportRequest = {},
): Promise<BpuImportResponse> {
  const response = await fetch(`${apiBaseUrl}/bpu/import`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<BpuImportResponse>(response);
}

export async function triggerBpuXlsxImport(
  token: string,
  payload: { force?: boolean } = {},
): Promise<BpuXlsxImportResponse> {
  const response = await fetch(`${apiBaseUrl}/bpu/import-xlsx`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<BpuXlsxImportResponse>(response);
}

// === BPU Ã©dition tableau ====================================================

export type BpuEditableRow = {
  component_id: number;
  period_id: number;
  segment_id: number;
  document_id: number;
  supplier: string;
  valid_year: number;
  market_subsequent: number | null;
  lot_number: number;
  amendment_number: number | null;
  amendment_label: string | null;
  pdf_filename: string;
  segment_type: string;
  segment_code: string;
  segment_label: string | null;
  tension_category: string | null;
  turpe_tariff: string | null;
  period_code: string;
  period_label: string | null;
  component_type: string;
  component_label: string | null;
  price_value: string;            // Decimal sÃ©rialisÃ© en string par Pydantic
  price_unit: string;
  price_value_eur_per_mwh: string | null;
  is_negative: boolean;
  notes: string | null;
};

export type BpuComponentUpdate = {
  component_type?: string;
  component_label?: string | null;
  price_value?: number | string;
  price_unit?: string;
  price_value_eur_per_mwh?: number | string | null;
  is_negative?: boolean;
  notes?: string | null;
};

export type BpuDocumentUpdate = {
  supplier?: string;
  valid_year?: number;
  market_subsequent?: number | null;
  lot_number?: number;
  amendment_number?: number | null;
  amendment_label?: string | null;
  signature_date?: string | null;
  signatory_name?: string | null;
  extraction_status?: string;
  extraction_notes?: string | null;
};

export async function fetchBpuEditableRows(
  token: string,
  filters: { document_id?: number; supplier?: string; valid_year?: number } = {},
): Promise<BpuEditableRow[]> {
  const search = new URLSearchParams();
  for (const [k, v] of Object.entries(filters)) {
    if (v !== undefined && v !== null && v !== "") search.set(k, String(v));
  }
  const qs = search.toString();
  const response = await fetch(`${apiBaseUrl}/bpu/editable-rows${qs ? `?${qs}` : ""}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<BpuEditableRow[]>(response);
}

export async function updateBpuComponent(
  token: string,
  componentId: number,
  payload: BpuComponentUpdate,
): Promise<BpuPriceComponent> {
  const response = await fetch(`${apiBaseUrl}/bpu/components/${componentId}`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<BpuPriceComponent>(response);
}

export async function deleteBpuComponent(token: string, componentId: number): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/bpu/components/${componentId}`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });
  return parseResponse<void>(response);
}

export async function updateBpuDocument(
  token: string,
  documentId: number,
  payload: BpuDocumentUpdate,
): Promise<BpuDocumentSummary> {
  const response = await fetch(`${apiBaseUrl}/bpu/documents/${documentId}`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<BpuDocumentSummary>(response);
}

// â”€â”€â”€ CVC Inventaire terrain â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export type CvcPreviewResponse = {
  columns: string[];
  total_rows: number;
  unique_sites: string[];
  unique_families: string[];
  sample_rows: Record<string, string | null>[];
};

export type BuildingMatchSuggestion = {
  building_id: number;
  site_id: number | null;
  nom_batiment: string | null;
  adresse: string | null;
  score: number;
};

export type PatrimoineSiteSuggestion = {
  site_id: number;
  nom_site: string;
  adresse: string | null;
  score: number;
};

export type SiteMatchResult = {
  site_raw: string;
  suggestions: BuildingMatchSuggestion[];
  auto_selected_id: number | null;
};

export type CvcMatchBuildingsResponse = {
  matches: SiteMatchResult[];
};

export type CvcImportSiteMatchResult = {
  site_raw: string;
  item_count: number;
  current_site_id: number | null;
  current_building_id: number | null;
  current_building_ids: number[];
  site_suggestions: PatrimoineSiteSuggestion[];
  building_suggestions: BuildingMatchSuggestion[];
  auto_site_id: number | null;
  auto_building_id: number | null;
};

export type CvcImportSiteMatchResponse = {
  matches: CvcImportSiteMatchResult[];
};

export type CvcInventoryItem = {
  id: number;
  city_id: number | null;
  site_id: number | null;
  building_id: number | null;
  local_id: number | null;
  equipment_ref_id: number | null;
  provider: string;
  site_raw: string | null;
  batiment: string | null;
  niveau: string | null;
  local_name: string | null;
  designation: string;
  type_equipement: string | null;
  statut: string | null;
  etat_sante: string | null;
  quantite_relevee: number | null;
  famille: string | null;
  marque: string | null;
  modele: string | null;
  numero_serie: string | null;
  puissance: string | null;
  puissance_frigorifique: number | null;
  puissance_calorifique: number | null;
  capacite: number | null;
  date_mis_en_service: number | null;
  duree_vie_restante: number | null;
  duree_vie_restante_source: string | null;
  duree_vie_restante_calculee: number | null;
  lifecycle_age_years: number | null;
  lifecycle_age_source: string;
  lifecycle_age_label: string | null;
  quantite_fluide_frigorigene: number | null;
  import_batch: string | null;
  criticite_pct: number | null;
  sypemi_reference_annees: number | null;
  sypemi_mini_annees: number | null;
  sypemi_maxi_annees: number | null;
  equipment_ref: EquipmentReference | null;
  requires_refrigerant_quantity: boolean;
  created_at: string;
  updated_at: string;
};

export type CvcImportBatchSummary = {
  import_batch: string;
  provider: string;
  imported: number;
  mapped_items: number;
  reference_mapped_items: number;
  refrigerant_items: number;
  created_at: string | null;
};

export type UpdateCvcInventoryItemPayload = {
  site_id?: number | null;
  building_id?: number | null;
  local_id?: number | null;
  equipment_ref_id?: number | null;
  date_mis_en_service?: number | null;
  quantite_fluide_frigorigene?: number | null;
};

export type CvcSiteMappingPayload = {
  site_raw: string;
  site_id: number | null;
  building_id: number | null;
  building_ids?: number[] | null;
  create_building?: boolean;
  create_building_name?: string | null;
  create_building_names?: string[] | null;
};

export type CvcApplySiteMappingsResult = {
  updated: number;
  mappings_applied: number;
};

export type CvcRecomputeReferencesResult = {
  import_batch: string;
  updated: number;
  matched: number;
  unmatched: number;
  changed: number;
};

export type CvcInventoryItemCompact = {
  id: number;
  site_raw: string | null;
  designation: string;
  famille: string | null;
  marque: string | null;
  modele: string | null;
  date_mis_en_service: number | null;
  import_batch: string | null;
};

export type CvcRefrigerantMatchCandidate = {
  item: CvcInventoryItemCompact;
  score: number;
  method: string;
};

export type CvcRefrigerantItem = {
  id: number;
  city_id: number | null;
  site_id: number | null;
  building_id: number | null;
  cvc_inventory_item_id: number | null;
  import_batch: string;
  source_filename: string | null;
  row_number: number | null;
  site_raw: string | null;
  designation: string;
  quantite_relevee: number | null;
  famille: string | null;
  marque: string | null;
  modele: string | null;
  fluide_frigorigene: string | null;
  quantite_fluide_kg: number | null;
  puissance_froid_kw: number | null;
  date_mis_en_service: number | null;
  gwp: number | null;
  teqco2: number | null;
  esp_status: string | null;
  cout_desp_date_eur: number | null;
  cumul_5_ans_eur: number | null;
  schedule: Record<string, string>;
  detection_permanente: boolean | null;
  dernier_controle_etancheite: string | null;
  prochaine_echeance: string | null;
  titulaire: string | null;
  responsable_collectivite: string | null;
  statut_action: string | null;
  commentaire_gmao: string | null;
  fgas_status: string;
  frequence_controle_mois: number | null;
  statut_conformite: string;
  action_prioritaire: string;
  preuve_attendue: string;
  priorite: string;
  match_status: string;
  match_method: string | null;
  match_score: number | null;
  matched_inventory_item: CvcInventoryItemCompact | null;
  candidates: CvcRefrigerantMatchCandidate[];
  created_at: string;
  updated_at: string;
};

export type CvcRefrigerantBatchSummary = {
  import_batch: string;
  source_filename: string | null;
  imported: number;
  matched_items: number;
  pending_items: number;
  total_fluide_kg: number;
  total_teqco2: number;
  created_at: string | null;
};

export type CvcRefrigerantImportResult = {
  import_batch: string;
  imported: number;
  auto_matched: number;
  pending: number;
  ambiguous: number;
  total_fluide_kg: number;
  total_teqco2: number;
};

export type UpdateCvcRefrigerantItemPayload = {
  cvc_inventory_item_id?: number | null;
  site_id?: number | null;
  building_id?: number | null;
  detection_permanente?: boolean | null;
  dernier_controle_etancheite?: string | null;
  prochaine_echeance?: string | null;
  titulaire?: string | null;
  responsable_collectivite?: string | null;
  statut_action?: string | null;
  commentaire_gmao?: string | null;
};

export type CvcRefrigerantDashboardKpi = {
  key: string;
  label: string;
  value: number | string;
  tone: string;
  helper: string | null;
};

export type CvcRefrigerantActionSummary = {
  item_id: number;
  priority: string;
  theme: string;
  site: string | null;
  equipment: string;
  constat: string;
  action: string;
  preuve_attendue: string;
  responsable: string | null;
  echeance_cible: string | null;
  statut_action: string;
};

export type CvcRefrigerantDashboard = {
  total_items: number;
  latest_batch: string | null;
  latest_batch_label: string | null;
  kpis: CvcRefrigerantDashboardKpi[];
  status_counts: Record<string, number>;
  conformity_counts: Record<string, number>;
  priority_counts: Record<string, number>;
  open_actions: CvcRefrigerantActionSummary[];
  esp_signals: CvcRefrigerantActionSummary[];
};

export type CvcSourceBuildingMapping = {
  id: number;
  city_id: number | null;
  source_type: string;
  import_batch: string;
  source_site_raw: string;
  site_id: number | null;
  building_id: number | null;
  building_ids: number[];
  status: string;
  notes: string | null;
  match_score: number | null;
  match_method: string | null;
  site_suggestions: PatrimoineSiteSuggestion[];
  building_suggestions: BuildingMatchSuggestion[];
  item_count: number;
  refrigerant_count: number;
  created_at: string;
  updated_at: string;
};

export type UpdateCvcSourceBuildingMappingPayload = {
  site_id: number | null;
  building_id: number | null;
  building_ids?: number[] | null;
  status: string;
  notes?: string | null;
};

export type CvcTechnicalCoverageReport = {
  patrimoine_buildings: number;
  cvc_inventory_items: number;
  cvc_refrigerant_items: number;
  inventory_without_building: number;
  refrigerants_without_building: number;
  refrigerants_without_inventory_item: number;
  source_mappings_to_review: number;
  source_mappings_not_found: number;
  patrimoine_buildings_without_cvc: BuildingMatchSuggestion[];
  inventory_unmapped_by_source: Array<Record<string, unknown>>;
  refrigerants_unmapped_by_source: Array<Record<string, unknown>>;
};

export type CvcImportResult = {
  imported: number;
  skipped: number;
  errors: string[];
  import_batch: string;
  provider: string;
  sypemi_matched: number;
  sypemi_unmatched: number;
};

export async function postCvcPreview(token: string, file: File): Promise<CvcPreviewResponse> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${apiBaseUrl}/cvc/preview`, {
    method: "POST",
    headers: buildAuthHeaders(token),
    body: form,
  });
  return parseResponse<CvcPreviewResponse>(response);
}

export async function postCvcMatchBuildings(
  token: string,
  sites: string[],
): Promise<CvcMatchBuildingsResponse> {
  const response = await fetch(`${apiBaseUrl}/cvc/match-buildings`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify({ sites }),
  });
  return parseResponse<CvcMatchBuildingsResponse>(response);
}

export async function postCvcImport(
  token: string,
  file: File,
  mapping: { site_raw: string; building_id: number }[] = [],
  importBatch?: string,
  provider?: string,
): Promise<CvcImportResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("mapping_json", JSON.stringify(mapping));
  if (importBatch) form.append("import_batch", importBatch);
  if (provider) form.append("provider", provider);
  const response = await fetch(`${apiBaseUrl}/cvc/import`, {
    method: "POST",
    headers: buildAuthHeaders(token),
    body: form,
  });
  return parseResponse<CvcImportResult>(response);
}

export async function fetchCvcImportBatches(token: string): Promise<CvcImportBatchSummary[]> {
  const response = await fetch(`${apiBaseUrl}/cvc/imports`, {
    headers: buildHeaders(token),
  });
  return parseResponse<CvcImportBatchSummary[]>(response);
}

export async function fetchCvcImportItems(
  token: string,
  importBatch: string,
): Promise<CvcInventoryItem[]> {
  const response = await fetch(`${apiBaseUrl}/cvc/imports/${encodeURIComponent(importBatch)}/items`, {
    headers: buildHeaders(token),
  });
  return parseResponse<CvcInventoryItem[]>(response);
}

export async function fetchCvcImportSiteMatches(
  token: string,
  importBatch: string,
): Promise<CvcImportSiteMatchResponse> {
  const response = await fetch(`${apiBaseUrl}/cvc/imports/${encodeURIComponent(importBatch)}/site-matches`, {
    headers: buildHeaders(token),
  });
  return parseResponse<CvcImportSiteMatchResponse>(response);
}

export async function applyCvcImportSiteMappings(
  token: string,
  importBatch: string,
  mappings: CvcSiteMappingPayload[],
): Promise<CvcApplySiteMappingsResult> {
  const response = await fetch(`${apiBaseUrl}/cvc/imports/${encodeURIComponent(importBatch)}/site-mappings`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify({ mappings }),
  });
  return parseResponse<CvcApplySiteMappingsResult>(response);
}

// --- Rapprochement compteur energie -> batiment (matching) ---

export type MeterBuildingSuggestion = {
  building_id: number;
  nom_batiment: string | null;
  adresse: string | null;
  score: number;
};

export type MeterMatchResult = {
  fluid: string;
  meter_identifier: string;
  label: string | null;
  address: string | null;
  current_building_id: number | null;
  current_building_name: string | null;
  suggestions: MeterBuildingSuggestion[];
  auto_building_id: number | null;
};

export type MeterMappingPayload = {
  fluid: string;
  meter_identifier: string;
  building_id: number | null;
  meter_label?: string | null;
};

export type MeterMappingApplyResult = {
  applied: number;
  updated: number;
};

export async function fetchMeterMatches(token: string): Promise<MeterMatchResult[]> {
  const response = await fetch(`${apiBaseUrl}/buildings/meters/matching`, {
    headers: buildHeaders(token),
  });
  return (await parseResponse<{ matches: MeterMatchResult[] }>(response)).matches;
}

export async function applyMeterMappings(
  token: string,
  mappings: MeterMappingPayload[],
): Promise<MeterMappingApplyResult> {
  const response = await fetch(`${apiBaseUrl}/buildings/meters/matching/apply`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify({ mappings }),
  });
  return parseResponse<MeterMappingApplyResult>(response);
}

export async function recomputeCvcImportReferences(
  token: string,
  importBatch: string,
): Promise<CvcRecomputeReferencesResult> {
  const response = await fetch(`${apiBaseUrl}/cvc/imports/${encodeURIComponent(importBatch)}/recompute-references`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<CvcRecomputeReferencesResult>(response);
}

// --- État du parc technique CVC (agrégation du cycle de vie) ---

export type CvcParcBucket = {
  key: string;
  label: string;
  count: number;
  share_pct: number;
};

export type CvcParcFamille = {
  famille: string;
  count: number;
  age_moyen: number | null;
  fin_de_vie_5ans: number;
  depasses: number;
};

export type CvcParcBatiment = {
  building_id: number;
  nom_batiment: string | null;
  count: number;
  age_moyen: number | null;
  criticite_moyenne: number | null;
  fin_de_vie_5ans: number;
  depasses: number;
};

export type CvcParcCompletude = {
  rattachement_pct: number;
  date_mes_pct: number;
  reference_pct: number;
  duree_vie_pct: number;
};

export type CvcParcTechniqueReport = {
  equipements_total: number;
  equipements_rattaches: number;
  batiments_couverts: number;
  age_moyen: number | null;
  depasses: number;
  fin_de_vie_5ans: number;
  ages: CvcParcBucket[];
  criticites: CvcParcBucket[];
  par_provider: CvcParcBucket[];
  par_famille: CvcParcFamille[];
  par_batiment: CvcParcBatiment[];
  completude: CvcParcCompletude;
};

export type CvcCarenceChamp = {
  champ: string;
  label: string;
  groupe: string;
  /** false = la colonne n'existe pas dans l'export du prestataire. */
  livre_par_format: boolean;
  manquants: number;
  total: number;
  manquants_pct: number;
};

export type CvcCarenceProvider = {
  provider: string;
  equipements: number;
  champs_non_livres: CvcCarenceChamp[];
  champs_incomplets: CvcCarenceChamp[];
  equipements_incomplets: number;
  completude_globale_pct: number;
};

export type CvcCarencesReport = {
  providers: CvcCarenceProvider[];
  rattachement_manquant: number;
  rattachement_total: number;
};

export async function fetchCvcCarences(token: string): Promise<CvcCarencesReport> {
  const response = await fetch(`${apiBaseUrl}/cvc/carences`, { headers: buildHeaders(token) });
  return parseResponse<CvcCarencesReport>(response);
}

/** Télécharge le classeur de demande de complétude d'un prestataire. */
export async function downloadCvcCarencesWorkbook(token: string, provider: string): Promise<Blob> {
  const response = await fetch(`${apiBaseUrl}/cvc/carences/export?provider=${encodeURIComponent(provider)}`, {
    headers: buildHeaders(token),
  });
  if (!response.ok) {
    throw new Error(`Export impossible (${response.status})`);
  }
  return response.blob();
}

export type CvcParcFilters = {
  provider?: string;
  buildingId?: number;
  famille?: string;
};

export async function fetchCvcParcTechnique(
  token: string,
  filters: CvcParcFilters = {},
): Promise<CvcParcTechniqueReport> {
  const params = new URLSearchParams();
  if (filters.provider) params.set("provider", filters.provider);
  if (filters.buildingId != null) params.set("building_id", String(filters.buildingId));
  if (filters.famille) params.set("famille", filters.famille);
  const qs = params.toString();
  const response = await fetch(`${apiBaseUrl}/cvc/parc-technique${qs ? `?${qs}` : ""}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<CvcParcTechniqueReport>(response);
}

export async function updateCvcItem(
  token: string,
  itemId: number,
  payload: UpdateCvcInventoryItemPayload,
): Promise<CvcInventoryItem> {
  const response = await fetch(`${apiBaseUrl}/cvc/items/${itemId}`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<CvcInventoryItem>(response);
}

export async function fetchCvcBuildingItems(
  token: string,
  buildingId: number,
): Promise<CvcInventoryItem[]> {
  const response = await fetch(`${apiBaseUrl}/cvc/buildings/${buildingId}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<CvcInventoryItem[]>(response);
}

export async function deleteCvcBuildingItems(token: string, buildingId: number): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/cvc/buildings/${buildingId}/items`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });
  return parseResponse<void>(response);
}

export async function deleteCvcItem(token: string, itemId: number): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/cvc/items/${itemId}`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });
  return parseResponse<void>(response);
}

export async function postCvcRefrigerantImport(
  token: string,
  file: File,
): Promise<CvcRefrigerantImportResult> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${apiBaseUrl}/cvc/refrigerants/import`, {
    method: "POST",
    headers: buildAuthHeaders(token),
    body: form,
  });
  return parseResponse<CvcRefrigerantImportResult>(response);
}

export async function fetchCvcRefrigerantBatches(token: string): Promise<CvcRefrigerantBatchSummary[]> {
  const response = await fetch(`${apiBaseUrl}/cvc/refrigerants/imports`, {
    headers: buildHeaders(token),
  });
  return parseResponse<CvcRefrigerantBatchSummary[]>(response);
}

export async function fetchCvcRefrigerantDashboard(token: string): Promise<CvcRefrigerantDashboard> {
  const response = await fetch(`${apiBaseUrl}/cvc/refrigerants/dashboard`, {
    headers: buildHeaders(token),
  });
  return parseResponse<CvcRefrigerantDashboard>(response);
}

export async function fetchCvcRefrigerantItems(
  token: string,
  importBatch: string,
): Promise<CvcRefrigerantItem[]> {
  const response = await fetch(`${apiBaseUrl}/cvc/refrigerants/imports/${encodeURIComponent(importBatch)}/items`, {
    headers: buildHeaders(token),
  });
  return parseResponse<CvcRefrigerantItem[]>(response);
}

export async function updateCvcRefrigerantItem(
  token: string,
  itemId: number,
  payload: UpdateCvcRefrigerantItemPayload,
): Promise<CvcRefrigerantItem> {
  const response = await fetch(`${apiBaseUrl}/cvc/refrigerants/items/${itemId}`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<CvcRefrigerantItem>(response);
}

export async function fetchCvcSourceBuildingMappings(
  token: string,
  filters?: { sourceType?: string; importBatch?: string },
): Promise<CvcSourceBuildingMapping[]> {
  const params = new URLSearchParams();
  if (filters?.sourceType) params.set("source_type", filters.sourceType);
  if (filters?.importBatch) params.set("import_batch", filters.importBatch);
  const query = params.toString();
  const response = await fetch(`${apiBaseUrl}/cvc/source-building-mappings${query ? `?${query}` : ""}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<CvcSourceBuildingMapping[]>(response);
}

export async function updateCvcSourceBuildingMapping(
  token: string,
  mappingId: number,
  payload: UpdateCvcSourceBuildingMappingPayload,
): Promise<CvcSourceBuildingMapping> {
  const response = await fetch(`${apiBaseUrl}/cvc/source-building-mappings/${mappingId}`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<CvcSourceBuildingMapping>(response);
}

export async function fetchCvcTechnicalCoverageReport(token: string): Promise<CvcTechnicalCoverageReport> {
  const response = await fetch(`${apiBaseUrl}/cvc/technical-report`, {
    headers: buildHeaders(token),
  });
  return parseResponse<CvcTechnicalCoverageReport>(response);
}

// â”€â”€ CPE DALKIA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export type CpeSite = {
  id: number;
  city_id: number | null;
  code_site: string;
  nom_site: string;
  categorie: string;
  nb_mwh_pci: number;
  ecs_ref_m3_an: number;
  q_ecs_mwh_pci_per_m3: number | null;
  dju_reference: number;
  cible_elec_mwh: number | null;
  tarif: "T1" | "T2" | "T3" | null;  // OS NÂ°3
  pce: string | null;                  // PCE GRDF
  actif: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type CpeGazReleve = {
  id: number;
  cpe_site_id: number;
  annee: number;
  mois: number;
  qt_mwh_pci: number | null;
  volume_ecs_m3: number | null;
  etat_chauffe: boolean | null;
  source: string;
  date_import: string;
  notes: string | null;
};

export type CpePrixGaz = {
  id: number;
  annee: number;
  tarif: "T1" | "T2" | "T3" | null;  // OS NÂ°3
  pu_eur_mwh_pci: number;             // en â‚¬/MWhPCI (converti depuis PCS)
  source: string;
  notes: string | null;
  updated_at: string;
};

export type CpeResultatAnnuel = {
  id: number;
  cpe_site_id: number;
  annee: number;
  dju_reels: number | null;
  dju_reference: number;
  nb: number;
  n_prime_b: number | null;
  qt_total: number | null;
  m_ecs_total: number | null;
  nc: number | null;
  pu_mwh: number | null;
  ecart: number | null;
  type_resultat: "interessement" | "penalite" | "equilibre" | "insuffisant" | null;
  montant_ht: number | null;
  p2_4_taux: number;
  ecart_pct: number | null;
  alerte_revision_nb: boolean;
  statut: "partiel" | "calcule" | "valide" | "conteste";
  nb_mois_renseignes: number;
  computed_at: string;
};

export type CpeSiteBilanItem = {
  site: CpeSite;
  resultat: CpeResultatAnnuel | null;
  nb_mois_releves: number;
  nb_exercice: number;          // NB utilisÃ© pour le calcul de l'exercice
  nb_source: "dalkia" | "site"; // origine du NB : cible importÃ©e de l'annÃ©e | scalaire de secours
  qt_cumul: number | null;
  nc_cumul: number | null;
  n_prime_b: number | null;
  ecart: number | null;
  type_resultat: string | null;
  montant_ht: number | null;
  statut: string;
};

export type CpeBilanAnnuel = {
  annee: number;
  dju_reels: number | null;
  dju_reference: number;
  pu_mwh: number | null;            // prix T2 (affichage KPI)
  prix_tarifs: Record<string, number>; // {T1: ..., T2: ..., T3: ...} en â‚¬/MWhPCI
  nb_sites_actifs: number;
  nb_sites_complets: number;
  total_interessement_ht: number;
  total_penalite_ht: number;
  solde_ht: number;
  sites: CpeSiteBilanItem[];
};

export type CpeConsoFluideSummary = {
  fluide: string;
  total: number;
  unite: string;
  nb_sites: number;
  nb_mois: number;
  nb_releves: number;
  nb_estimes: number;
};

export type CpeConsoUnknownSite = {
  code_site: string;
  contract_code: string | null;
  fluides: string[];
  nb_mois: number;
  total_energie_mwh: number | null;
  total_volume: number | null;
  nb_estimes: number;
};

export type CpeConsoCoverageSite = {
  site_id: number;
  code_site: string;
  nom_site: string;
  categorie: string;
  mois_couverts: number;
  fluides: string[];
};

export type CpeConsoSynthese = {
  annee: number;
  nb_sites_actifs: number;
  nb_sites_couverts: number;
  nb_sites_sans_conso: number;
  nb_sites_inconnus: number;
  fluides: CpeConsoFluideSummary[];
  sites_sans_conso: CpeConsoCoverageSite[];
  sites_inconnus: CpeConsoUnknownSite[];
};

export type CpeDjuAnnuel = {
  annee: number;
  dju_total: number;
  nb_jours: number;
  source: string;
  profile_code?: string | null;
  profile_label?: string | null;
  station_label?: string | null;
  source_label?: string | null;
  heating_base_c?: number | null;
  cooling_base_c?: number | null;
  reference_dju?: number | null;
  reference_period?: string | null;
  heating_period?: string | null;
  contractual?: boolean;
  compliant_source?: boolean;
  notes?: string | null;
};

export type CpeImportResult = {
  nb_lignes: number;
  nb_inseres: number;
  nb_mis_a_jour: number;
  nb_erreurs: number;
  erreurs: string[];
  sites_inconnus: string[];
};

export type CpeFinanceGroupSummary = {
  code: string;
  nb_lignes: number;
  nb_factures: number;
  montant_ht: number;
};

export type CpeFinanceContractSummary = {
  code_contrat: string;
  libelle_contrat: string | null;
  nb_lignes: number;
  nb_factures: number;
  montant_ht: number;
  periode_debut_min: string | null;
  periode_fin_max: string | null;
  marches: string[];
  types_marche: string[];
  nb_lignes_code_site_cpe: number;
  nb_sites_cpe_distincts: number;
  nb_lignes_consommation: number;
  nb_lignes_index_releve: number;
};

export type CpeFinancePreview = {
  filename: string | null;
  nb_lignes: number;
  nb_factures: number;
  nb_contrats: number;
  montant_ht: number;
  nb_lignes_p1_p2_p3: number;
  nb_lignes_code_site_cpe: number;
  nb_sites_cpe_distincts: number;
  nb_lignes_consommation: number;
  nb_lignes_index_releve: number;
  marches: CpeFinanceGroupSummary[];
  types_facture: CpeFinanceGroupSummary[];
  contrats: CpeFinanceContractSummary[];
  sites_cpe_detectes: string[];
  alertes: string[];
};

export type CpeAccountingImportResult = {
  filename: string | null;
  nature_rules_created: number;
  nature_rules_updated: number;
  site_mappings_created: number;
  site_mappings_updated: number;
  errors: string[];
};

export type CpeAccountingNatureRule = {
  id: number;
  city_id: number | null;
  contract_code: string | null;
  market: string;
  service_sold: string | null;
  billed_item: string;
  frequency: string | null;
  accounting_nature: string;
  accounting_label: string | null;
  active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type CpeContractReference = {
  id: number;
  city_id: number | null;
  contract_code: string;
  contract_label: string | null;
  reference_kind: string;
  year: number;
  market: string;
  billed_item: string;
  annual_amount_ht: number | null;
  expected_amount_ht: number | null;
  installment_count: number | null;
  expected_period_months: string | null;
  included_billed_items: string | null;
  formula: string | null;
  tolerance_pct: number | null;
  tolerance_eur: number | null;
  active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type CpeAccountingSiteMapping = {
  id: number;
  city_id: number | null;
  code_site: string;
  site_name: string;
  family: string | null;
  manager: string | null;
  alternate_manager: string | null;
  service_code: string | null;
  service_label: string | null;
  function_code: string | null;
  function_label: string | null;
  antenna_code: string | null;
  antenna_label: string | null;
  operation_code: string | null;
  operation_label: string | null;
  active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type CpeFinanceImportBatch = {
  id: number;
  city_id: number | null;
  filename: string | null;
  source: string;
  status: string;
  line_count: number;
  invoice_count: number;
  total_ht: number;
  notes: string | null;
  created_at: string;
};

export type CpeFinanceInvoice = {
  id: number;
  batch_id: number;
  city_id: number | null;
  invoice_number: string;
  contract_code: string | null;
  contract_label: string | null;
  invoice_type: string | null;
  supplier: string | null;
  customer_code: string | null;
  customer_name: string | null;
  invoice_date: string | null;
  due_date: string | null;
  period_start: string | null;
  period_end: string | null;
  markets: string | null;
  billed_items: string | null;
  recipient_reference_1: string | null;
  prestation_sites: string | null;
  prestation_detail: string | null;
  evidence_id: number | null;
  evidence_status: string | null;
  evidence_revision_date: string | null;
  evidence_declared_factor: number | null;
  evidence_declared_icht_ime: number | null;
  evidence_declared_fsd2: number | null;
  evidence_declared_bt40: number | null;
  total_ht: number;
  status: string;
  finance_exported_at: string | null;
  billing_days: number | null;
  issue_delay_days: number | null;
  due_in_days: number | null;
  deadline_status: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type CpeFinanceImportResult = {
  batch: CpeFinanceImportBatch;
  invoices: CpeFinanceInvoice[];
  line_count: number;
  matched_accounting_rules: number;
  matched_site_mappings: number;
  warnings: string[];
};

export type CpeFinanceHistoryDeleteResult = {
  batches_deleted: number;
  invoices_deleted: number;
  lines_deleted: number;
  controls_deleted: number;
};

export type CpeFinanceLine = {
  id: number;
  batch_id: number;
  invoice_id: number;
  row_number: number;
  contract_code: string | null;
  invoice_number: string | null;
  market: string | null;
  market_type: string | null;
  service_sold: string | null;
  billed_item: string | null;
  vat_rate: number | null;
  amount_ht: number;
  consumption: number | null;
  unit: string | null;
  base_price: number | null;
  revised_price: number | null;
  detail: string | null;
  site_code_detected: string | null;
  accounting_site_id: number | null;
  accounting_rule_id: number | null;
  accounting_nature: string | null;
  accounting_label: string | null;
  period_start: string | null;
  period_end: string | null;
};

export type CpeFinanceControlReport = {
  generated_at: string;
  scope: string;
  invoice_count: number;
  total_ht: number;
  invoices_ok: number;
  invoices_with_errors: number;
  invoices_blocked: number;
  controls_ok: number;
  controls_error: number;
  controls_blocked: number;
  control_types: Array<{
    control_type: string;
    ok: number;
    error: number;
    blocked: number;
    total: number;
  }>;
  invoices: Array<{
    invoice_id: number;
    invoice_number: string;
    contract_code: string | null;
    contract_label: string | null;
    invoice_type: string | null;
    recipient_ref: string | null;
    market: string | null;
    billed_items: string | null;
    total_ht: number;
    invoice_status: string;
    finance_exported_at: string | null;
    due_date: string | null;
    due_in_days: number | null;
    deadline_status: string;
    ok: number;
    error: number;
    blocked: number;
    controls_total: number;
    control_types: string[];
  }>;
};

export type CpeRevisionIndex = {
  id: number;
  city_id: number | null;
  index_code: string;
  year: number;
  quarter: number;
  value: number;
  source: string | null;
  verification_status: string;
  evidence_id: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type CpeRevisionObservation = {
  market: string;
  year: number;
  quarter: number;
  observed_factor: number;
  expected_factor: number | null;
  delta_factor: number | null;
  status: "to_verify" | "matches_validated" | "conflict";
  line_count: number;
  invoice_numbers: string[];
  required_indices: string[];
  message: string;
};

export type CpeInvoiceEvidence = {
  id: number;
  city_id: number | null;
  invoice_id: number | null;
  uploaded_by_user_id: number;
  original_filename: string;
  sha256: string;
  extraction_status: string;
  validation_status: string;
  evidence_kind: string;
  market: string | null;
  contract_code: string | null;
  year: number | null;
  quarter: number | null;
  effective_date: string | null;
  declared_invoice_number: string | null;
  revision_date: string | null;
  declared_factor: number | null;
  declared_icht_ime: number | null;
  declared_fsd2: number | null;
  declared_bt40: number | null;
  notes: string | null;
  created_at: string;
};

export type CpeFinanceControl = {
  id: number;
  city_id: number | null;
  batch_id: number;
  invoice_id: number;
  line_id: number;
  control_type: string;
  status: string;
  severity: string;
  message: string;
  formula: string | null;
  index_year: number | null;
  index_quarter: number | null;
  icht_ime_value: number | null;
  bt40_value: number | null;
  fsd2_value: number | null;
  expected_factor: number | null;
  base_price: number | null;
  expected_revised_price: number | null;
  actual_revised_price: number | null;
  delta_abs: number | null;
  delta_pct: number | null;
  computed_at: string;
};

export async function fetchCpeSites(token: string): Promise<CpeSite[]> {
  const response = await fetch(`${apiBaseUrl}/cpe/sites`, { headers: buildHeaders(token) });
  return parseResponse<CpeSite[]>(response);
}

export async function fetchCpeBilan(token: string, annee: number): Promise<CpeBilanAnnuel> {
  const response = await fetch(`${apiBaseUrl}/cpe/bilan/${annee}`, { headers: buildHeaders(token) });
  return parseResponse<CpeBilanAnnuel>(response);
}

export type CpeAtterrissageItem = {
  code_site: string;
  nom_site: string;
  site_id: number;
  tarif: string | null;
  nb_exercice: number;
  nb_source: string;
  mois_realises: number;
  nc_realise: number | null;
  nc_projete: number | null;
  n_prime_b_projete: number | null;
  ecart_projete: number | null;
  type_resultat: string | null;
  montant_ht_projete: number | null;
  statut: string;
};

export type CpeAtterrissage = {
  annee: number;
  trimestre: number;
  mois_ecoules: number;
  dju_reel_ecoule: number;
  dju_normal_restant: number;
  dju_projete_annuel: number;
  dju_reference: number;
  dju_method: string;
  has_data: boolean;
  nb_sites_projetes: number;
  total_interessement_projete: number;
  total_penalite_projete: number;
  net_projete: number;
  items: CpeAtterrissageItem[];
};

export async function fetchCpeAtterrissage(token: string, annee: number, trimestre: number): Promise<CpeAtterrissage> {
  const response = await fetch(`${apiBaseUrl}/cpe/bilan/${annee}/atterrissage?trimestre=${trimestre}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<CpeAtterrissage>(response);
}

export type CpeElecPerfItem = {
  site_id: number;
  code_site: string;
  nom_site: string;
  cible_mwh: number | null;
  cible_periode_mwh: number | null;
  cible_source: string;
  conso_reelle_mwh: number | null;
  nb_mois: number;
  ecart_mwh: number | null;
  ecart_pct: number | null;
  statut: string;
};

export type CpeElecPerf = {
  annee: number;
  nb_sites: number;
  nb_avec_cible: number;
  nb_suivis: number;
  total_cible_mwh: number;
  total_cible_periode_mwh: number;
  total_conso_mwh: number;
  total_ecart_mwh: number;
  total_ecart_pct: number | null;
  has_data: boolean;
  items: CpeElecPerfItem[];
};

export async function fetchCpeElecPerformance(token: string, annee: number): Promise<CpeElecPerf> {
  const response = await fetch(`${apiBaseUrl}/cpe/bilan/${annee}/elec-performance`, {
    headers: buildHeaders(token),
  });
  return parseResponse<CpeElecPerf>(response);
}

export type CpeP24Objective = {
  annee: number;
  has_data: boolean;
  objectif_atteint: boolean;
  global_cible_mwh: number;
  global_reel_mwh: number;
  economie_mwh: number;
  economie_pct: number | null;
  gas_cible_mwh: number;
  gas_reel_mwh: number;
  gas_sites: number;
  elec_cible_mwh: number;
  elec_reel_mwh: number;
  elec_sites: number;
  elec_sites_avec_cible: number;
  p24_montant_ht: number;
  p24_taux: number;
  p24_facturable_ht: number;
  p24_a_risque_ht: number;
  gas_mois_min: number;
  complet: boolean;
};

export async function fetchCpeP24Objective(token: string, annee: number): Promise<CpeP24Objective> {
  const response = await fetch(`${apiBaseUrl}/cpe/bilan/${annee}/p24-objective`, {
    headers: buildHeaders(token),
  });
  return parseResponse<CpeP24Objective>(response);
}

export async function fetchCpeConsoSynthese(token: string, annee: number): Promise<CpeConsoSynthese> {
  const response = await fetch(`${apiBaseUrl}/cpe/consommations/synthese/${annee}`, { headers: buildHeaders(token) });
  return parseResponse<CpeConsoSynthese>(response);
}

export async function calculerCpeBilan(token: string, annee: number): Promise<CpeResultatAnnuel[]> {
  const response = await fetch(`${apiBaseUrl}/cpe/bilan/${annee}/calculer`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<CpeResultatAnnuel[]>(response);
}

export async function fetchCpeDju(token: string, annee: number): Promise<CpeDjuAnnuel> {
  const response = await fetch(`${apiBaseUrl}/cpe/dju/${annee}`, { headers: buildHeaders(token) });
  return parseResponse<CpeDjuAnnuel>(response);
}

export async function fetchCpePrixGaz(token: string, annee: number): Promise<CpePrixGaz[]> {
  const response = await fetch(`${apiBaseUrl}/cpe/prix-gaz/${annee}`, { headers: buildHeaders(token) });
  return parseResponse<CpePrixGaz[]>(response);
}

export async function upsertCpePrixGaz(
  token: string,
  payload: { annee: number; tarif?: string | null; pu_eur_mwh_pci: number; notes?: string },
): Promise<CpePrixGaz> {
  const response = await fetch(`${apiBaseUrl}/cpe/prix-gaz`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<CpePrixGaz>(response);
}

export async function fetchCpeReleves(token: string, siteId: number, annee?: number): Promise<CpeGazReleve[]> {
  const url = annee
    ? `${apiBaseUrl}/cpe/sites/${siteId}/releves?annee=${annee}`
    : `${apiBaseUrl}/cpe/sites/${siteId}/releves`;
  const response = await fetch(url, { headers: buildHeaders(token) });
  return parseResponse<CpeGazReleve[]>(response);
}

export type CpeConsoReleve = {
  fluide: string;
  annee: number;
  mois: number;
  consommation: number | null;
  unite: string | null;
  energie_mwh: number | null;
  qualite: string;
  nb_releves: number;
  nb_estimes: number;
};

export async function fetchCpeConsommations(token: string, siteId: number, annee?: number): Promise<CpeConsoReleve[]> {
  const url = annee
    ? `${apiBaseUrl}/cpe/sites/${siteId}/consommations?annee=${annee}`
    : `${apiBaseUrl}/cpe/sites/${siteId}/consommations`;
  const response = await fetch(url, { headers: buildHeaders(token) });
  return parseResponse<CpeConsoReleve[]>(response);
}

export async function upsertCpeReleve(
  token: string,
  siteId: number,
  payload: { annee: number; mois: number; qt_mwh_pci?: number; volume_ecs_m3?: number },
): Promise<CpeGazReleve> {
  const response = await fetch(`${apiBaseUrl}/cpe/sites/${siteId}/releves`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<CpeGazReleve>(response);
}

export async function importCpeCsv(token: string, file: File): Promise<CpeImportResult> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${apiBaseUrl}/cpe/import/csv`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  return parseResponse<CpeImportResult>(response);
}

export async function previewCpeFinanceExport(token: string, file: File): Promise<CpeFinancePreview> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${apiBaseUrl}/cpe/finances/preview`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  return parseResponse<CpeFinancePreview>(response);
}

export async function importCpeAccountingCodification(token: string, file: File): Promise<CpeAccountingImportResult> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${apiBaseUrl}/cpe/accounting/import-codification`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  return parseResponse<CpeAccountingImportResult>(response);
}

export type FinanceCodificationImportResult = {
  filename: string | null;
  dalkia_sites_created: number;
  dalkia_sites_updated: number;
  dalkia_rules_created: number;
  dalkia_rules_updated: number;
  energy_points_created: number;
  energy_points_updated: number;
  energy_rules_created: number;
  energy_rules_updated: number;
  errors: string[];
};

export async function exportCpeAccountingCodification(token: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/cpe/accounting/codification/export.xlsx`, { headers: buildHeaders(token) });
  if (!response.ok) {
    await parseResponse(response);
    return;
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const stamp = new Date().toISOString().slice(0, 10);
  a.download = `codification-finance-${stamp}.xlsx`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function importFinanceCodification(token: string, file: File): Promise<FinanceCodificationImportResult> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${apiBaseUrl}/cpe/accounting/codification/import`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  return parseResponse<FinanceCodificationImportResult>(response);
}

export async function fetchCpeAccountingNatureRules(
  token: string,
  onlyCurrentScope = false,
): Promise<CpeAccountingNatureRule[]> {
  const q = onlyCurrentScope ? "?only_current_scope=true" : "";
  const response = await fetch(`${apiBaseUrl}/cpe/accounting/nature-rules${q}`, { headers: buildHeaders(token) });
  return parseResponse<CpeAccountingNatureRule[]>(response);
}

export async function createCpeAccountingNatureRule(
  token: string,
  payload: Partial<CpeAccountingNatureRule> & { market: string; billed_item: string; accounting_nature: string },
): Promise<CpeAccountingNatureRule> {
  const response = await fetch(`${apiBaseUrl}/cpe/accounting/nature-rules`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<CpeAccountingNatureRule>(response);
}

export async function updateCpeAccountingNatureRule(
  token: string,
  id: number,
  payload: Partial<CpeAccountingNatureRule>,
): Promise<CpeAccountingNatureRule> {
  const response = await fetch(`${apiBaseUrl}/cpe/accounting/nature-rules/${id}`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<CpeAccountingNatureRule>(response);
}

export async function deleteCpeAccountingNatureRule(token: string, id: number): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/cpe/accounting/nature-rules/${id}`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });
  return parseResponse<void>(response);
}

export async function fetchCpeContractReferences(token: string): Promise<CpeContractReference[]> {
  const response = await fetch(`${apiBaseUrl}/cpe/contract-references`, { headers: buildHeaders(token) });
  return parseResponse<CpeContractReference[]>(response);
}

export async function createCpeContractReference(
  token: string,
  payload: Partial<CpeContractReference> & { contract_code: string; reference_kind: string; year: number; market: string; billed_item: string },
): Promise<CpeContractReference> {
  const response = await fetch(`${apiBaseUrl}/cpe/contract-references`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<CpeContractReference>(response);
}

export async function updateCpeContractReference(
  token: string,
  id: number,
  payload: Partial<CpeContractReference>,
): Promise<CpeContractReference> {
  const response = await fetch(`${apiBaseUrl}/cpe/contract-references/${id}`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<CpeContractReference>(response);
}

export async function deleteCpeContractReference(token: string, id: number): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/cpe/contract-references/${id}`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });
  return parseResponse<void>(response);
}

export async function fetchCpeAccountingSiteMappings(token: string): Promise<CpeAccountingSiteMapping[]> {
  const response = await fetch(`${apiBaseUrl}/cpe/accounting/site-mappings`, { headers: buildHeaders(token) });
  return parseResponse<CpeAccountingSiteMapping[]>(response);
}

export async function createCpeAccountingSiteMapping(
  token: string,
  payload: Partial<CpeAccountingSiteMapping> & { code_site: string; site_name: string },
): Promise<CpeAccountingSiteMapping> {
  const response = await fetch(`${apiBaseUrl}/cpe/accounting/site-mappings`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<CpeAccountingSiteMapping>(response);
}

export async function updateCpeAccountingSiteMapping(
  token: string,
  id: number,
  payload: Partial<CpeAccountingSiteMapping>,
): Promise<CpeAccountingSiteMapping> {
  const response = await fetch(`${apiBaseUrl}/cpe/accounting/site-mappings/${id}`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<CpeAccountingSiteMapping>(response);
}

export async function deleteCpeAccountingSiteMapping(token: string, id: number): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/cpe/accounting/site-mappings/${id}`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });
  return parseResponse<void>(response);
}

export async function importCpeFinanceExport(token: string, file: File): Promise<CpeFinanceImportResult> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${apiBaseUrl}/cpe/finances/import`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  return parseResponse<CpeFinanceImportResult>(response);
}

export async function fetchCpeFinanceBatches(token: string): Promise<CpeFinanceImportBatch[]> {
  const response = await fetch(`${apiBaseUrl}/cpe/finances/batches`, { headers: buildHeaders(token) });
  return parseResponse<CpeFinanceImportBatch[]>(response);
}

export async function purgeCpeFinanceDuplicates(token: string): Promise<{ removed: number; kept: number }> {
  const response = await fetch(`${apiBaseUrl}/cpe/finances/purge-duplicates`, { method: "POST", headers: buildHeaders(token) });
  return parseResponse<{ removed: number; kept: number }>(response);
}

export async function purgeEnergyInvoiceDuplicates(token: string): Promise<{ removed: number; kept: number }> {
  const response = await fetch(`${apiBaseUrl}/billing/invoices/imports/purge-duplicates`, { method: "POST", headers: buildHeaders(token) });
  return parseResponse<{ removed: number; kept: number }>(response);
}

export async function reanalyzeAllEnergyInvoices(token: string): Promise<{ reanalyzed: number }> {
  const response = await fetch(`${apiBaseUrl}/billing/invoices/imports/reanalyze-all`, { method: "POST", headers: buildHeaders(token) });
  return parseResponse<{ reanalyzed: number }>(response);
}

export async function fetchCpeFinanceInvoices(token: string, batchId?: number): Promise<CpeFinanceInvoice[]> {
  const url = batchId ? `${apiBaseUrl}/cpe/finances/invoices?batch_id=${batchId}` : `${apiBaseUrl}/cpe/finances/invoices`;
  const response = await fetch(url, { headers: buildHeaders(token) });
  return parseResponse<CpeFinanceInvoice[]>(response);
}

export async function deleteCpeFinanceHistory(token: string): Promise<CpeFinanceHistoryDeleteResult> {
  const response = await fetch(`${apiBaseUrl}/cpe/finances/history`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });
  return parseResponse<CpeFinanceHistoryDeleteResult>(response);
}

export async function fetchCpeFinanceInvoiceLines(token: string, invoiceId: number): Promise<CpeFinanceLine[]> {
  const response = await fetch(`${apiBaseUrl}/cpe/finances/invoices/${invoiceId}/lines`, { headers: buildHeaders(token) });
  return parseResponse<CpeFinanceLine[]>(response);
}

export async function fetchCpeRevisionIndices(token: string, year?: number): Promise<CpeRevisionIndex[]> {
  const url = year ? `${apiBaseUrl}/cpe/revision-indices?year=${year}` : `${apiBaseUrl}/cpe/revision-indices`;
  const response = await fetch(url, { headers: buildHeaders(token) });
  return parseResponse<CpeRevisionIndex[]>(response);
}

export async function fetchCpeRevisionObservations(token: string): Promise<CpeRevisionObservation[]> {
  const response = await fetch(`${apiBaseUrl}/cpe/revision-observations`, { headers: buildHeaders(token) });
  return parseResponse<CpeRevisionObservation[]>(response);
}

export async function fetchCpeRevisionEvidences(token: string): Promise<CpeInvoiceEvidence[]> {
  const response = await fetch(`${apiBaseUrl}/cpe/revision-evidences`, { headers: buildHeaders(token) });
  return parseResponse<CpeInvoiceEvidence[]>(response);
}

export async function uploadCpeRevisionEvidencePdf(token: string, file: File): Promise<CpeInvoiceEvidence> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${apiBaseUrl}/cpe/revision-evidences`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  return parseResponse<CpeInvoiceEvidence>(response);
}

export async function uploadCpeInvoiceEvidencePdf(token: string, invoiceId: number, file: File): Promise<CpeInvoiceEvidence> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${apiBaseUrl}/cpe/finances/invoices/${invoiceId}/evidence-pdf`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  return parseResponse<CpeInvoiceEvidence>(response);
}

export async function applyCpeInvoiceEvidenceDeclaredIndices(token: string, evidenceId: number): Promise<CpeRevisionIndex[]> {
  const response = await fetch(`${apiBaseUrl}/cpe/finances/evidences/${evidenceId}/apply-declared-indices`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<CpeRevisionIndex[]>(response);
}

export async function upsertCpeRevisionIndex(
  token: string,
  payload: { index_code: string; year: number; quarter: number; value: number; source?: string | null; verification_status?: string; evidence_id?: number | null; notes?: string | null },
): Promise<CpeRevisionIndex> {
  const response = await fetch(`${apiBaseUrl}/cpe/revision-indices`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<CpeRevisionIndex>(response);
}

export async function deleteCpeRevisionIndex(token: string, indexId: number): Promise<{ deleted: boolean }> {
  const response = await fetch(`${apiBaseUrl}/cpe/revision-indices/${indexId}`, {
    method: "DELETE",
    headers: buildAuthHeaders(token),
  });
  return parseResponse<{ deleted: boolean }>(response);
}

export async function purgeCpeRevisionIndices(token: string, source: string): Promise<{ deleted: number }> {
  const params = new URLSearchParams({ source });
  const response = await fetch(`${apiBaseUrl}/cpe/revision-indices/purge?${params.toString()}`, {
    method: "DELETE",
    headers: buildAuthHeaders(token),
  });
  return parseResponse<{ deleted: number }>(response);
}

export async function fetchCpeFinanceControls(token: string, invoiceId: number): Promise<CpeFinanceControl[]> {
  const response = await fetch(`${apiBaseUrl}/cpe/finances/invoices/${invoiceId}/controls`, { headers: buildHeaders(token) });
  return parseResponse<CpeFinanceControl[]>(response);
}

export async function recalculateCpeFinanceControls(token: string, invoiceId: number): Promise<CpeFinanceControl[]> {
  const response = await fetch(`${apiBaseUrl}/cpe/finances/invoices/${invoiceId}/controls/recalculate`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<CpeFinanceControl[]>(response);
}

export async function fetchCpeFinanceControlReport(token: string): Promise<CpeFinanceControlReport> {
  const response = await fetch(`${apiBaseUrl}/cpe/finances/controls/report`, { headers: buildHeaders(token) });
  return parseResponse<CpeFinanceControlReport>(response);
}

export async function recalculateAllCpeFinanceControls(token: string): Promise<CpeFinanceControlReport> {
  const response = await fetch(`${apiBaseUrl}/cpe/finances/controls/recalculate`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<CpeFinanceControlReport>(response);
}

export type SupplierContact = {
  id: number;
  supplier: string;
  contact_name: string | null;
  email: string | null;
  phone: string | null;
  role: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};
export type SupplierContactInput = {
  contact_name?: string | null;
  email?: string | null;
  phone?: string | null;
  role?: string | null;
  notes?: string | null;
};

export async function fetchSupplierContacts(token: string): Promise<SupplierContact[]> {
  const response = await fetch(`${apiBaseUrl}/billing/supplier-contacts`, { headers: buildHeaders(token) });
  return parseResponse<SupplierContact[]>(response);
}

export async function upsertSupplierContact(token: string, supplier: string, payload: SupplierContactInput): Promise<SupplierContact> {
  const response = await fetch(`${apiBaseUrl}/billing/supplier-contacts/${encodeURIComponent(supplier)}`, {
    method: "PUT",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<SupplierContact>(response);
}

export async function downloadCpeFinanceControlReport(token: string): Promise<Blob> {
  const response = await fetch(`${apiBaseUrl}/cpe/finances/controls/report.xlsx`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Erreur ${response.status}`);
  }
  return response.blob();
}

export type ComptableReportFiles = Partial<Record<"dalkia" | "engie" | "edf" | "totalenergies", File>>;

export async function downloadComptableControlReport(token: string, files: ComptableReportFiles): Promise<Blob> {
  const form = new FormData();
  for (const [market, file] of Object.entries(files)) {
    if (file) form.append(market, file);
  }
  const response = await fetch(`${apiBaseUrl}/billing/comptable/rapport-controle.xlsx`, {
    method: "POST",
    headers: buildAuthHeaders(token),
    body: form,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Erreur ${response.status}`);
  }
  return response.blob();
}
export type CpeMarketTrackingCell = {
  year: number;
  prevu: number;
  recu: number;
  ecart: number;
  ecart_pct: number | null;
  taux: number | null;
};

export type CpeMarketTrackingTotal = {
  prevu: number;
  recu: number;
  ecart: number;
  ecart_pct: number | null;
  taux: number | null;
};

export type CpeMarketTrackingPoste = {
  poste: string;
  label: string;
  by_year: CpeMarketTrackingCell[];
  total: CpeMarketTrackingTotal;
};

export type CpeP1DpgfLevel = {
  level: string;
  label: string;
  by_year: { year: number; total: number }[];
  total: number;
};

export type CpeP1Dpgf = {
  levels: CpeP1DpgfLevel[];
  has_data: boolean;
};

export type CpeMarketTrackingQuarters = {
  year: number;
  billed: number;
  expected: number;
};

export type CpeDjuYear = {
  year: number;
  dju_real: number | null;
  months: number;
  complete: boolean;
  ratio: number | null;
};

export type CpeDju = {
  reference: number;
  source: string;
  base: number;
  by_year: CpeDjuYear[];
  has_data: boolean;
};

export type CpeMarketTrackingLot = {
  lot: number;
  label: string;
  contract_codes: string[];
  postes: CpeMarketTrackingPoste[];
  totals_by_year: CpeMarketTrackingCell[];
  grand_total: CpeMarketTrackingTotal;
  has_reference: boolean;
  p1_dpgf: CpeP1Dpgf;
  quarters_billed: CpeMarketTrackingQuarters[];
};

export type CpeMarketTracking = {
  years: number[];
  postes: CpeMarketTrackingPoste[];
  totals_by_year: CpeMarketTrackingCell[];
  grand_total: CpeMarketTrackingTotal;
  p1_source: string;
  has_reference: boolean;
  by_lot: CpeMarketTrackingLot[];
  p1_dpgf: CpeP1Dpgf;
  quarters_billed: CpeMarketTrackingQuarters[];
  installments_per_year: number;
  dju: CpeDju | null;
};

export async function fetchCpeMarketTracking(
  token: string,
  yearFrom: number,
  yearTo: number,
): Promise<CpeMarketTracking> {
  const response = await fetch(
    `${apiBaseUrl}/cpe/finances/market-tracking?year_from=${yearFrom}&year_to=${yearTo}`,
    { headers: buildHeaders(token) },
  );
  return parseResponse<CpeMarketTracking>(response);
}

export async function downloadCpeMarketTracking(token: string, yearFrom: number, yearTo: number): Promise<Blob> {
  const response = await fetch(
    `${apiBaseUrl}/cpe/finances/market-tracking.xlsx?year_from=${yearFrom}&year_to=${yearTo}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Erreur ${response.status}`);
  }
  return response.blob();
}

// â”€â”€ Devis petits travaux P3 (type P6 DALKIA) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

export type CpeP3Devis = {
  id: number;
  numero: string;
  devis_date: string | null;
  localisation: string | null;
  site_code: string | null;
  libelle: string | null;
  domaine: string | null;
  type_devis: string | null;
  destinataire: string | null;
  etat: string | null;
  montant_ht: number | null;
  montant_ttc: number | null;
  in_scope: boolean;
};

export type CpeP3DevisImportResult = {
  created: number;
  updated: number;
  in_scope: number;
  out_of_scope: number;
  skipped: number;
  errors: string[];
};

export type CpeP3Atterrissage = {
  year: number;
  provision_p3: number;
  provision_p3_4: number;
  provision_total: number;
  engage_total: number;
  reste_provision: number;
  taux_engagement: number | null;
  devis_count: number;
  by_etat: Array<{ etat: string; count: number; montant_ht: number }>;
  has_provision: boolean;
};

export async function importCpeP3Devis(token: string, file: File): Promise<CpeP3DevisImportResult> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${apiBaseUrl}/cpe/finances/p3-devis/import`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  return parseResponse<CpeP3DevisImportResult>(response);
}

export async function fetchCpeP3Devis(token: string, inScopeOnly = true): Promise<CpeP3Devis[]> {
  const response = await fetch(
    `${apiBaseUrl}/cpe/finances/p3-devis?in_scope_only=${inScopeOnly}`,
    { headers: buildHeaders(token) },
  );
  return parseResponse<CpeP3Devis[]>(response);
}

export async function fetchCpeP3Atterrissage(token: string, year: number): Promise<CpeP3Atterrissage> {
  const response = await fetch(
    `${apiBaseUrl}/cpe/finances/p3-devis/atterrissage?year=${year}`,
    { headers: buildHeaders(token) },
  );
  return parseResponse<CpeP3Atterrissage>(response);
}

export async function updateCpeFinanceInvoice(
  token: string,
  invoiceId: number,
  payload: { status?: string; notes?: string | null },
): Promise<CpeFinanceInvoice> {
  const response = await fetch(`${apiBaseUrl}/cpe/finances/invoices/${invoiceId}`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<CpeFinanceInvoice>(response);
}

export async function downloadCpeFinanceInvoiceLiaison(token: string, invoiceId: number): Promise<Blob> {
  const response = await fetch(`${apiBaseUrl}/cpe/finances/invoices/${invoiceId}/liaison.xlsx`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Erreur ${response.status}`);
  }
  return response.blob();
}

// ---------------------------------------------------------------------------
// GRDF ADICT â€” gaz (PCE, consommations, rapprochement P1 DALKIA)
// ---------------------------------------------------------------------------

export type GrdfPce = {
  id: number;
  id_pce: string;
  nom_site: string | null;
  nom_titulaire: string | null;
  role_tiers: string;
  etat_droit_acces: string | null;
  perim_publiees: boolean;
  tarif_acheminement: string | null;
  car_actuelle: number | null;
  frequence_releve: string | null;
  // Adresse du compteur : GRDF ne restitue aucun nom de site, l'adresse est la
  // seule identification disponible (complement_adresse porte souvent le nom
  // d'usage du batiment).
  numero_rue: string | null;
  nom_rue: string | null;
  complement_adresse: string | null;
  code_postal: string | null;
  commune: string | null;
};

export type GrdfConsoSyncStatus = {
  status: string;
  started_at: string | null;
  finished_at: string | null;
  pce_total: number;
  pce_done: number;
  rows_upserted: number;
  mode: string | null;
  error: string | null;
  log: string[];
};

export type GrdfMonthlyPoint = {
  annee: number;
  mois: number;
  energie_kwh: number;
  mwh_pcs: number;
};

export type GrdfMonthlySeries = {
  id_pce: string;
  nom_site: string | null;
  total_kwh: number;
  points: GrdfMonthlyPoint[];
};

export type GrdfP1ReconcileItem = {
  id_pce: string;
  code_site: string | null;
  nom_site: string | null;
  grdf_mwh_pcs: number;
  dalkia_p1_qt_mwhpcs: number | null;
  dalkia_conso_mwh: number | null;
  p1_total_ht: number | null;
  ecart_mwh: number | null;
  ecart_pct: number | null;
  statut: string;
};

export async function fetchGrdfPces(token: string): Promise<GrdfPce[]> {
  const response = await fetch(`${apiBaseUrl}/grdf/pces`, { headers: buildHeaders(token) });
  return parseResponse<GrdfPce[]>(response);
}

export type GrdfSyncDroitsResult = { total_api: number; created: number; updated: number };

export async function syncGrdfPces(token: string): Promise<GrdfSyncDroitsResult> {
  const response = await fetch(`${apiBaseUrl}/grdf/pces/sync`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<GrdfSyncDroitsResult>(response);
}

export async function fetchGrdfConsoStatus(token: string): Promise<GrdfConsoSyncStatus> {
  const response = await fetch(`${apiBaseUrl}/grdf/conso/status`, { headers: buildHeaders(token) });
  return parseResponse<GrdfConsoSyncStatus>(response);
}

export async function startGrdfBackfill(token: string): Promise<{ message: string }> {
  const response = await fetch(`${apiBaseUrl}/grdf/conso/backfill`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<{ message: string }>(response);
}

export async function startGrdfConsoSync(token: string): Promise<{ message: string }> {
  const response = await fetch(`${apiBaseUrl}/grdf/conso/sync`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<{ message: string }>(response);
}

export type GrdfEnrichResult = { pce_total: number; done: number; errors: number };

export async function enrichGrdfContractuel(token: string): Promise<GrdfEnrichResult> {
  const response = await fetch(`${apiBaseUrl}/grdf/contractuel/enrich`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<GrdfEnrichResult>(response);
}

export async function fetchGrdfMonthly(token: string, idPce?: string): Promise<GrdfMonthlySeries[]> {
  const params = new URLSearchParams();
  if (idPce) params.set("id_pce", idPce);
  const qs = params.toString();
  const response = await fetch(`${apiBaseUrl}/grdf/conso/monthly${qs ? `?${qs}` : ""}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<GrdfMonthlySeries[]>(response);
}

export async function fetchGrdfReconcileP1(token: string, year: number): Promise<GrdfP1ReconcileItem[]> {
  const response = await fetch(`${apiBaseUrl}/grdf/rapprochement-p1/${year}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<GrdfP1ReconcileItem[]>(response);
}

// ---------------------------------------------------------------------------
// Rapprochement patrimoine (PO2-PAT-003) â€” boÃ®te de rÃ©conciliation compteurs â†” patrimoine
// ---------------------------------------------------------------------------

export type PatrimoineMatchItem = {
  id: number;
  source: string;
  external_id: string;
  label: string | null;
  candidate_target_type: string | null;
  candidate_target_id: number | null;
  candidate_label: string | null;
  candidate_score: number | null;
  candidate_reason: string | null;
  status: string;
  resolved_target_type: string | null;
  resolved_target_id: number | null;
  notes: string | null;
  updated_at: string | null;
};

export type PatrimoineMatchCounts = Record<string, number>;

export type PatrimoineTarget = {
  target_type: string;
  target_id: number;
  label: string;
};

export async function fetchPatrimoineMatches(
  token: string,
  params: { source?: string; status?: string } = {},
): Promise<PatrimoineMatchItem[]> {
  const qs = new URLSearchParams();
  if (params.source) qs.set("source", params.source);
  if (params.status) qs.set("status", params.status);
  const suffix = qs.toString();
  const response = await fetch(`${apiBaseUrl}/patrimoine/matches${suffix ? `?${suffix}` : ""}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<PatrimoineMatchItem[]>(response);
}

export async function fetchPatrimoineMatchCounts(token: string): Promise<PatrimoineMatchCounts> {
  const response = await fetch(`${apiBaseUrl}/patrimoine/matches/counts`, {
    headers: buildHeaders(token),
  });
  return parseResponse<PatrimoineMatchCounts>(response);
}

export async function searchPatrimoineTargets(token: string, query: string): Promise<PatrimoineTarget[]> {
  const qs = new URLSearchParams({ q: query });
  const response = await fetch(`${apiBaseUrl}/patrimoine/matches/targets?${qs.toString()}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<PatrimoineTarget[]>(response);
}

export async function collectPatrimoineMatches(token: string): Promise<Record<string, number>> {
  const response = await fetch(`${apiBaseUrl}/patrimoine/matches/collect`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<Record<string, number>>(response);
}

export async function bulkLinkPatrimoineMatches(token: string, minScore = 90): Promise<{ linked: number }> {
  const response = await fetch(`${apiBaseUrl}/patrimoine/matches/bulk-link?min_score=${minScore}`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<{ linked: number }>(response);
}

export async function updatePatrimoineMatch(
  token: string,
  itemId: number,
  payload: {
    status: string;
    resolved_target_type?: string | null;
    resolved_target_id?: number | null;
    notes?: string | null;
  },
): Promise<PatrimoineMatchItem> {
  const response = await fetch(`${apiBaseUrl}/patrimoine/matches/${itemId}`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<PatrimoineMatchItem>(response);
}

// ---------------------------------------------------------------------------
// Factures gaz TotalEnergies (marchÃ© HÃ©rault Ã‰nergie) â€” contrÃ´le v1
// ---------------------------------------------------------------------------

export type GasInvoice = {
  id: number;
  num_facture: string;
  type_detail: string | null;
  date_comptable: string | null;
  date_echeance: string | null;
  pce: string;
  nom_site: string | null;
  lib_regroupement: string | null;
  adresse: string | null;
  ville: string | null;
  classe_conso: string | null;
  tarif_acheminement: string | null;
  debut_conso: string | null;
  fin_conso: string | null;
  prix_conso_gaz: number | null;
  montant_conso_gaz: number | null;
  total_hors_tva: number | null;
  total_ttc: number | null;
  total_conso_kwh: number | null;
  total_conso_m3: number | null;
  building_id: number | null;
  control_status: string;
  control_issues_json: string | null;
  control_detail_json: string | null;
  decision_status: string;
  decision_comment: string | null;
};

export type GasInvoiceIssue = { code: string; family: string; message: string; severity: string };

export type GasPortfolioSite = { site: string; pce: string; count: number; ht: number; kwh: number; linked: boolean };

export type GasPortfolio = {
  count: number;
  total_ht: number;
  total_ttc: number;
  total_kwh: number;
  by_control: Record<string, number>;
  by_decision: Record<string, number>;
  by_site: GasPortfolioSite[];
};

export async function fetchGasInvoices(
  token: string,
  params: { control_status?: string; decision_status?: string } = {},
): Promise<GasInvoice[]> {
  const qs = new URLSearchParams();
  if (params.control_status) qs.set("control_status", params.control_status);
  if (params.decision_status) qs.set("decision_status", params.decision_status);
  const suffix = qs.toString();
  const response = await fetch(`${apiBaseUrl}/gas/invoices${suffix ? `?${suffix}` : ""}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<GasInvoice[]>(response);
}

export async function fetchGasPortfolio(token: string): Promise<GasPortfolio> {
  const response = await fetch(`${apiBaseUrl}/gas/invoices/portfolio`, {
    headers: buildHeaders(token),
  });
  return parseResponse<GasPortfolio>(response);
}

export async function importGasInvoices(token: string, file: File, forceUpdate = false): Promise<Record<string, unknown>> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${apiBaseUrl}/gas/invoices/import?force_update=${forceUpdate}`, {
    method: "POST",
    headers: buildAuthHeaders(token),
    body: form,
  });
  return parseResponse<Record<string, unknown>>(response);
}

export async function recomputeGasControls(token: string): Promise<Record<string, number>> {
  const response = await fetch(`${apiBaseUrl}/gas/invoices/recompute`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<Record<string, number>>(response);
}

export async function setGasInvoiceDecision(
  token: string,
  invoiceId: number,
  decisionStatus: string,
  comment?: string | null,
): Promise<GasInvoice> {
  const response = await fetch(`${apiBaseUrl}/gas/invoices/${invoiceId}/decision`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify({ decision_status: decisionStatus, comment: comment ?? null }),
  });
  return parseResponse<GasInvoice>(response);
}

export type GasBpuPrice = {
  id: number;
  annee: number;
  profil: string;
  fourniture_ht_mwh: number | null;
  cee_ht_mwh: number | null;
  cee_precarite_ht_mwh: number | null;
  cpb_ht_mwh: number | null;
  go_ht_mwh: number | null;
  source: string | null;
};

export async function fetchGasBpu(token: string): Promise<GasBpuPrice[]> {
  const response = await fetch(`${apiBaseUrl}/gas/invoices/bpu`, {
    headers: buildHeaders(token),
  });
  return parseResponse<GasBpuPrice[]>(response);
}

export async function exportGasInvoices(token: string): Promise<Blob> {
  const response = await fetch(`${apiBaseUrl}/gas/invoices/export`, {
    headers: buildAuthHeaders(token),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Erreur ${response.status}`);
  }
  return response.blob();
}

export type GasNetworkTariff = {
  id: number;
  annee: number;
  option: string;
  atrd_terme_variable_eur_mwh: number | null;
  atrd_abonnement_annuel_eur: number | null;
  source: string | null;
  source_url: string | null;
};

export async function fetchGasNetworkTariffs(token: string): Promise<GasNetworkTariff[]> {
  const response = await fetch(`${apiBaseUrl}/gas/invoices/network-tariff`, {
    headers: buildHeaders(token),
  });
  return parseResponse<GasNetworkTariff[]>(response);
}

// ---------------------------------------------------------------------------
// Matrices comptables versionnÃ©es (/api/accounting-matrices/*)
// ---------------------------------------------------------------------------
export type AccountingMatrixVersionV1 = {
  id: number;
  matrix_contract_id: number;
  version_label: string;
  status: string;
  source: string;
  rules_count: number;
  effective_from: string | null;
  effective_to: string | null;
  validated_at: string | null;
};

export type AccountingMatrixContractV1 = {
  id: number;
  domain: string;
  supplier: string;
  contract_code: string | null;
  contract_label: string | null;
  lot_label: string | null;
  status: string;
  active_version_id: number | null;
  active_version_label: string | null;
  versions_count: number;
};

export type AccountingMatrixContractDetailV1 = AccountingMatrixContractV1 & {
  versions: AccountingMatrixVersionV1[];
};

export type AccountingMatrixRuleV1 = {
  id: number;
  matrix_version_id: number;
  stable_rule_key: string;
  scope: string;
  site_code: string | null;
  meter_id: string | null;
  billed_item_pattern: string | null;
  accounting_service: string | null;
  accounting_function: string | null;
  accounting_antenna: string | null;
  operation_number: string | null;
  accounting_nature: string | null;
  accounting_label: string | null;
  allocation_percent: number;
  is_active: boolean;
  site_designation?: string | null;
  suggested_antenna?: string | null;
};

export type AccountingMatrixSeedResultV1 = {
  energy: { contracts_created: number; contracts_skipped: number; rules: number };
  cpe: { contracts_created: number; contracts_skipped: number; rules: number };
  versions_created: number;
};

export async function fetchAccountingMatrixContracts(token: string): Promise<AccountingMatrixContractV1[]> {
  const response = await fetch(`${apiBaseUrl}/accounting-matrices/contracts`, { headers: buildHeaders(token) });
  return parseResponse<AccountingMatrixContractV1[]>(response);
}

export async function fetchAccountingMatrixContract(token: string, contractId: number): Promise<AccountingMatrixContractDetailV1> {
  const response = await fetch(`${apiBaseUrl}/accounting-matrices/contracts/${contractId}`, { headers: buildHeaders(token) });
  return parseResponse<AccountingMatrixContractDetailV1>(response);
}

export async function fetchAccountingMatrixVersionRules(token: string, versionId: number): Promise<AccountingMatrixRuleV1[]> {
  const response = await fetch(`${apiBaseUrl}/accounting-matrices/versions/${versionId}/rules`, { headers: buildHeaders(token) });
  return parseResponse<AccountingMatrixRuleV1[]>(response);
}

export type AccountingMatrixRuleCreateV1 = {
  stable_rule_key: string;
  scope?: string;
  site_code?: string | null;
  meter_id?: string | null;
  billed_item_pattern?: string | null;
  accounting_service?: string | null;
  accounting_function?: string | null;
  accounting_antenna?: string | null;
  operation_number?: string | null;
  accounting_nature?: string | null;
  accounting_label?: string | null;
  allocation_percent?: number;
  priority?: number;
  is_active?: boolean;
};

export type AccountingMatrixRuleUpdateV1 = Partial<Omit<AccountingMatrixRuleCreateV1, "stable_rule_key">>;

export async function createAccountingMatrixRule(token: string, versionId: number, payload: AccountingMatrixRuleCreateV1): Promise<AccountingMatrixRuleV1> {
  const response = await fetch(`${apiBaseUrl}/accounting-matrices/versions/${versionId}/rules`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<AccountingMatrixRuleV1>(response);
}

export async function updateAccountingMatrixRule(token: string, ruleId: number, payload: AccountingMatrixRuleUpdateV1): Promise<AccountingMatrixRuleV1> {
  const response = await fetch(`${apiBaseUrl}/accounting-matrices/rules/${ruleId}`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<AccountingMatrixRuleV1>(response);
}

export async function deleteAccountingMatrixRule(token: string, ruleId: number): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/accounting-matrices/rules/${ruleId}`, {
    method: "DELETE",
    headers: buildAuthHeaders(token),
  });
  if (!response.ok) {
    await parseResponse(response);
  }
}

export async function seedAccountingMatrices(token: string): Promise<AccountingMatrixSeedResultV1> {
  const response = await fetch(`${apiBaseUrl}/accounting-matrices/seed`, { method: "POST", headers: buildHeaders(token) });
  return parseResponse<AccountingMatrixSeedResultV1>(response);
}

export async function downloadAccountingMatrixVersionXlsx(token: string, versionId: number, label?: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/accounting-matrices/versions/${versionId}/export.xlsx`, { headers: buildHeaders(token) });
  if (!response.ok) {
    await parseResponse(response);
    return;
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `matrice-comptable-${label ?? versionId}.xlsx`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export type AccountingMatrixImportPreviewRowV1 = {
  line: number;
  stable_rule_key: string | null;
  status: "ajout" | "modifie" | "inchange" | "erreurs" | string;
  message: string | null;
};

export type AccountingMatrixImportPreviewV1 = {
  contract_id: number;
  reference_version_id: number | null;
  reference_version_label: string | null;
  structural_errors: string[];
  summary: Record<string, number>;
  rows: AccountingMatrixImportPreviewRowV1[];
  absentes_du_fichier: string[];
  can_commit: boolean;
  warnings: string[];
};

export async function previewAccountingMatrixImport(token: string, contractId: number, file: File): Promise<AccountingMatrixImportPreviewV1> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${apiBaseUrl}/accounting-matrices/contracts/${contractId}/import-preview`, {
    method: "POST",
    headers: buildAuthHeaders(token),
    body: form,
  });
  return parseResponse<AccountingMatrixImportPreviewV1>(response);
}

export async function commitAccountingMatrixImport(token: string, contractId: number, versionLabel: string, file: File): Promise<AccountingMatrixVersionV1> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${apiBaseUrl}/accounting-matrices/contracts/${contractId}/import-commit?version_label=${encodeURIComponent(versionLabel)}`, {
    method: "POST",
    headers: buildAuthHeaders(token),
    body: form,
  });
  return parseResponse<AccountingMatrixVersionV1>(response);
}
export type InvoiceAccountingSnapshotV1 = {
  id: number;
  invoice_source: string;
  invoice_id: string;
  matrix_contract_id: number | null;
  matrix_version_id: number | null;
  status: "proposed" | "validated" | "manual_override" | "exported" | string;
  snapshot_json: string | null;
  exceptions_json: string | null;
  validated_by_user_id: number | null;
  validated_at: string | null;
  exported_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type ApplyAccountingMatrixPayloadV1 = {
  matrix_contract_id: number;
  invoice_lines?: Array<{
    billed_item?: string | null;
    site_code?: string | null;
    meter_id?: string | null;
    amount?: number | null;
    line_ref?: string | null;
  }>;
};

export async function fetchInvoiceAccountingSnapshot(
  token: string,
  source: string,
  invoiceId: string | number,
): Promise<InvoiceAccountingSnapshotV1> {
  const response = await fetch(`${apiBaseUrl}/accounting-matrices/invoices/${source}/${invoiceId}/snapshot`, {
    headers: buildHeaders(token),
  });
  return parseResponse<InvoiceAccountingSnapshotV1>(response);
}

export async function applyAccountingMatrixToInvoice(
  token: string,
  source: string,
  invoiceId: string | number,
  payload: ApplyAccountingMatrixPayloadV1,
): Promise<InvoiceAccountingSnapshotV1> {
  const response = await fetch(`${apiBaseUrl}/accounting-matrices/invoices/${source}/${invoiceId}/apply`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify({ invoice_lines: [], ...payload }),
  });
  return parseResponse<InvoiceAccountingSnapshotV1>(response);
}

export async function validateInvoiceAccountingSnapshot(
  token: string,
  source: string,
  invoiceId: string | number,
): Promise<InvoiceAccountingSnapshotV1> {
  const response = await fetch(`${apiBaseUrl}/accounting-matrices/invoices/${source}/${invoiceId}/validate-snapshot`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<InvoiceAccountingSnapshotV1>(response);
}

export async function exportInvoiceAccountingSnapshotToFinance(
  token: string,
  source: string,
  invoiceId: string | number,
): Promise<InvoiceAccountingSnapshotV1> {
  const response = await fetch(`${apiBaseUrl}/accounting-matrices/invoices/${source}/${invoiceId}/export-finance`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<InvoiceAccountingSnapshotV1>(response);
}

// ---------------------------------------------------------------------------
// Budget par marché (/api/accounting-budget/*)
// ---------------------------------------------------------------------------
export type AccountingBudgetLineV1 = {
  id: number;
  matrix_contract_id: number;
  year: number;
  operation_number: string;
  label: string | null;
  amount_budget: number;
  comment: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type AccountingBudgetLineCreateV1 = {
  matrix_contract_id: number;
  year: number;
  operation_number: string;
  label?: string | null;
  amount_budget: number;
  comment?: string | null;
};

export type AccountingBudgetLineUpdateV1 = {
  label?: string | null;
  amount_budget?: number;
  comment?: string | null;
};

export type BudgetSuiviRowV1 = {
  operation_number: string;
  amount_budget: number;
  amount_realized: number;
  amount_landing: number;
  variance_to_budget: number;
};

export type BudgetSuiviV1 = {
  matrix_contract_id: number;
  year: number;
  year_progress_percent: number;
  rows: BudgetSuiviRowV1[];
  unassigned_realized_amount: number;
  total_budget: number;
  total_realized: number;
  total_landing: number;
  snapshots_included: number;
  snapshots_excluded_unknown_year: number;
  snapshots_excluded_other_year: number;
  snapshots_total: number;
  data_completeness_note: string;
};

export async function fetchAccountingBudgetLines(token: string, matrixContractId: number, year: number): Promise<AccountingBudgetLineV1[]> {
  const response = await fetch(`${apiBaseUrl}/accounting-budget/contracts/${matrixContractId}/lines?year=${year}`, { headers: buildHeaders(token) });
  return parseResponse<AccountingBudgetLineV1[]>(response);
}

export async function createAccountingBudgetLine(token: string, payload: AccountingBudgetLineCreateV1): Promise<AccountingBudgetLineV1> {
  const response = await fetch(`${apiBaseUrl}/accounting-budget/lines`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<AccountingBudgetLineV1>(response);
}

export async function updateAccountingBudgetLine(token: string, lineId: number, payload: AccountingBudgetLineUpdateV1): Promise<AccountingBudgetLineV1> {
  const response = await fetch(`${apiBaseUrl}/accounting-budget/lines/${lineId}`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<AccountingBudgetLineV1>(response);
}

export async function deleteAccountingBudgetLine(token: string, lineId: number): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/accounting-budget/lines/${lineId}`, {
    method: "DELETE",
    headers: buildAuthHeaders(token),
  });
  if (!response.ok) {
    await parseResponse(response);
  }
}

export async function fetchBudgetSuivi(token: string, matrixContractId: number, year: number): Promise<BudgetSuiviV1> {
  const response = await fetch(`${apiBaseUrl}/accounting-budget/contracts/${matrixContractId}/suivi?year=${year}`, { headers: buildHeaders(token) });
  return parseResponse<BudgetSuiviV1>(response);
}

// Atterrissage « budget contractuel − réalisé » par poste CPE (stratégie §5bis).
export type ContractBudgetPosteV1 = {
  poste: string;
  label: string;
  budget_base: number;
  coefficient_revision: number;
  revision_detail: string | null;
  budget_contractuel: number;
  realise: number;
  atterrissage: number;
  reste_a_facturer: number;
  ecart_realise_vs_budget: number;
  ecart_atterrissage_vs_budget: number;
  taux_facturation: number | null;
  landing_method: string;
};

export type ContractBudgetOperationV1 = {
  operation_number: string;
  postes: string[];
  budget_contractuel: number;
  realise: number;
  atterrissage: number;
};

export type ContractBudgetLandingV1 = {
  year: number;
  lot: number | null;
  contract_codes: string[];
  year_progress_percent: number;
  postes: ContractBudgetPosteV1[];
  totals: {
    budget_base: number;
    budget_contractuel: number;
    realise: number;
    atterrissage: number;
    reste_a_facturer: number;
    ecart_atterrissage_vs_budget: number;
  };
  by_operation: ContractBudgetOperationV1[];
  projection_note: string;
  source_note: string;
};

export async function fetchContractBudgetLanding(token: string, year: number, lot?: number | null): Promise<ContractBudgetLandingV1> {
  const params = new URLSearchParams({ year: String(year) });
  if (lot != null) params.set("lot", String(lot));
  const response = await fetch(`${apiBaseUrl}/cpe/finances/contract-budget-landing?${params.toString()}`, { headers: buildHeaders(token) });
  return parseResponse<ContractBudgetLandingV1>(response);
}

export type GasBudgetRevisePointV1 = {
  pce: string;
  nom_site: string | null;
  building_id: number | null;
  kwh_n1: number;
  conso_attendue_kwh: number;
  climate_ratio: number;
  peg_ratio: number;
  pu_variable_eur_kwh: number;
  fixe_prevision: number;
  variable_prevision: number;
  prevision_reference: number;
  realise: number;
  realise_fixe: number;
  realise_variable: number;
  kwh_realise: number;
  months_covered: number;
  atterrissage: number;
  ecart_atterrissage_vs_prevision: number;
  landing_method: string;
  has_history: boolean;
};

export type GasBudgetReviseV1 = {
  year: number;
  generated_on: string;
  pce_count: number;
  peg_available: boolean;
  dju_available: boolean;
  totals: {
    fixe_prevision: number;
    variable_prevision: number;
    prevision_reference: number;
    realise: number;
    realise_fixe: number;
    realise_variable: number;
    atterrissage: number;
    ecart_atterrissage_vs_prevision: number;
  };
  points: GasBudgetRevisePointV1[];
  source_note: string;
};

export async function fetchGasBudgetRevise(token: string, year: number): Promise<GasBudgetReviseV1> {
  const params = new URLSearchParams({ year: String(year) });
  const response = await fetch(`${apiBaseUrl}/marches/gas-budget-revise?${params.toString()}`, { headers: buildHeaders(token) });
  return parseResponse<GasBudgetReviseV1>(response);
}

// --- ENGIE électricité : budget révisé fixe/variable par PRM + agrégat bâtiment ---

export type EngieBudgetRevisePointV1 = {
  prm: string;
  site_name: string | null;
  segment: string | null;
  regroupement: string | null;
  building_id: number | null;
  building_name: string | null;
  has_anomaly: boolean;
  anomaly_count: number;
  kwh_n1: number;
  enedis_kwh_n1: number;
  conso_attendue_kwh: number;
  thermo_share: number;
  conso_method: string;
  enedis_available: boolean;
  bpu_ratio: number;
  bpu_available: boolean;
  turpe_ratio: number;
  pu_variable_eur_kwh: number;
  fixe_prevision: number;
  variable_prevision: number;
  prevision_reference: number;
  realise: number;
  realise_fixe: number;
  realise_variable: number;
  kwh_realise: number;
  months_covered: number;
  atterrissage: number;
  ecart_atterrissage_vs_prevision: number;
  landing_method: string;
  has_history: boolean;
};

export type EngieBudgetReviseAggregateV1 = {
  key: number | string | null;
  label: string;
  prm_count: number;
  prevision_reference: number;
  realise: number;
  atterrissage: number;
};

export type EngieBudgetReviseV1 = {
  year: number;
  available_years: number[];
  recommended_year: number;
  generated_on: string;
  prm_count: number;
  turpe_available: boolean;
  bpu_available: boolean;
  bpu_applied_prm_count: number;
  reference_annee_en_vigueur_count: number;
  enedis_available: boolean;
  anomaly_prm_count: number;
  totals: {
    fixe_prevision: number;
    variable_prevision: number;
    prevision_reference: number;
    realise: number;
    realise_fixe: number;
    realise_variable: number;
    atterrissage: number;
    ecart_atterrissage_vs_prevision: number;
  };
  points: EngieBudgetRevisePointV1[];
  buildings: EngieBudgetReviseAggregateV1[];
  regroupements: EngieBudgetReviseAggregateV1[];
  source_note: string;
};

export async function fetchEngieBudgetRevise(token: string, year: number | null): Promise<EngieBudgetReviseV1> {
  const params = new URLSearchParams();
  if (year != null) params.set("year", String(year));
  const qs = params.toString();
  const response = await fetch(`${apiBaseUrl}/marches/engie-elec-budget-revise${qs ? `?${qs}` : ""}`, { headers: buildHeaders(token) });
  return parseResponse<EngieBudgetReviseV1>(response);
}

export async function fetchEdfBudgetRevise(token: string, year: number | null): Promise<EngieBudgetReviseV1> {
  const params = new URLSearchParams();
  if (year != null) params.set("year", String(year));
  const qs = params.toString();
  const response = await fetch(`${apiBaseUrl}/marches/edf-elec-budget-revise${qs ? `?${qs}` : ""}`, { headers: buildHeaders(token) });
  return parseResponse<EngieBudgetReviseV1>(response);
}

export type MarketVariablePointV1 = {
  period: string;
  value: number;
  label: string | null;
  source: string | null;
};

export type MarketVariableSeriesV1 = {
  code: string;
  label: string;
  unit: string;
  market: string;
  family: string;
  periodicity: string;
  points: MarketVariablePointV1[];
};

export type MarketIndicesVariablesV1 = {
  year_from: number;
  year_to: number;
  series: MarketVariableSeriesV1[];
};

export async function fetchMarketIndicesVariables(token: string, yearFrom: number, yearTo: number): Promise<MarketIndicesVariablesV1> {
  const params = new URLSearchParams({ year_from: String(yearFrom), year_to: String(yearTo) });
  const response = await fetch(`${apiBaseUrl}/marches/indices-variables?${params.toString()}`, { headers: buildHeaders(token) });
  return parseResponse<MarketIndicesVariablesV1>(response);
}

// ---------------------------------------------------------------------------
// Référentiel patrimoine historique (ASTECH) — aller-retour
// ---------------------------------------------------------------------------

export type LegacyAsset = {
  id: number;
  code_bien: string;
  designation: string | null;
  nomcourt: string | null;
  genre: string | null;
  categ_des: string | null;
  souscat_des: string | null;
  horsparc: string | null;
  code_parent: string | null;
  source_norue: string | null;
  source_bister: string | null;
  source_libelvoie: string | null;
  source_codpost: string | null;
  source_ville: string | null;
  source_commune: string | null;
  source_refcad: string | null;
  building_id: number | null;
  local_id: number | null;
  target_type: string;
  status: string;
  link_origin: string | null;
  candidate_building_id: number | null;
  candidate_label: string | null;
  candidate_score: number | null;
  candidate_reason: string | null;
  latitude: number | null;
  longitude: number | null;
  resolved_housenumber: string | null;
  resolved_street: string | null;
  resolved_postcode: string | null;
  resolved_city: string | null;
  resolved_citycode: string | null;
  resolved_label: string | null;
  resolved_source: string | null;
  resolved_name: string | null;
  resolved_section: string | null;
  resolved_numero_plan: string | null;
  resolved_refcad: string | null;
  import_batch: string | null;
  notes: string | null;
  updated_at: string | null;
};

export type LegacyImportResult = {
  batch: string;
  sheet_name: string;
  header_row: number;
  columns: number;
  total_rows: number;
  created: number;
  updated: number;
  skipped_scope: number;
  skipped_no_key: number;
  out_of_scope_commune: number;
  /** Aucun code en commun avec les biens déjà présents : codification ASTECH changée. */
  codes_disjoints?: boolean;
  existing_before?: number;
};

export type LegacyCandidatesResult = {
  scanned: number;
  proposed: number;
  auto_linked: number;
  repaired: number;
};

export async function importLegacyAstechFile(
  token: string,
  file: File,
  options?: { genres?: string; includeOutOfPark?: boolean },
): Promise<LegacyImportResult> {
  const params = new URLSearchParams();
  if (options?.genres !== undefined) params.set("genres", options.genres);
  if (options?.includeOutOfPark) params.set("include_out_of_park", "true");
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${apiBaseUrl}/patrimoine/legacy/import?${params.toString()}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  return parseResponse<LegacyImportResult>(response);
}

export async function computeLegacyCandidates(
  token: string,
  autoLink = true,
): Promise<LegacyCandidatesResult> {
  const response = await fetch(
    `${apiBaseUrl}/patrimoine/legacy/candidates?auto_link=${autoLink ? "true" : "false"}`,
    { method: "POST", headers: buildHeaders(token) },
  );
  return parseResponse<LegacyCandidatesResult>(response);
}

export async function fetchLegacyAssets(
  token: string,
  options?: { status?: string; genre?: string; search?: string; limit?: number },
): Promise<LegacyAsset[]> {
  const params = new URLSearchParams();
  if (options?.status) params.set("status", options.status);
  if (options?.genre) params.set("genre", options.genre);
  if (options?.search) params.set("search", options.search);
  params.set("limit", String(options?.limit ?? 2000));
  const response = await fetch(`${apiBaseUrl}/patrimoine/legacy?${params.toString()}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<LegacyAsset[]>(response);
}

export async function fetchLegacyCounts(token: string): Promise<Record<string, number>> {
  const response = await fetch(`${apiBaseUrl}/patrimoine/legacy/counts`, {
    headers: buildHeaders(token),
  });
  return parseResponse<Record<string, number>>(response);
}

export async function updateLegacyAsset(
  token: string,
  assetId: number,
  payload: {
    status?: string | null;
    building_id?: number | null;
    local_id?: number | null;
    /** Nom du bien, tel qu'il repartira dans ASTECH. Le code bien reste intouchable. */
    designation?: string | null;
    clear_building?: boolean;
    /** Rejette la proposition du moteur sans écarter le bien : il reste à traiter. */
    clear_candidate?: boolean;
    latitude?: number | null;
    longitude?: number | null;
    notes?: string | null;
  },
): Promise<LegacyAsset> {
  const response = await fetch(`${apiBaseUrl}/patrimoine/legacy/${assetId}`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<LegacyAsset>(response);
}

export type IgnPointLookup = {
  lat: number;
  lon: number;
  radius_m: number;
  feature_collection: GeoJsonFeatureCollection;
  parcel_feature_collection: GeoJsonFeatureCollection;
  parcel_labels: string[];
};

/** Bâtiments IGN autour d'un point posé sur la carte, sans adresse préalable. */
export async function fetchIgnBuildingsAtPoint(
  token: string,
  lat: number,
  lon: number,
  radiusM = 300,
): Promise<IgnPointLookup> {
  const params = new URLSearchParams({
    lat: String(lat),
    lon: String(lon),
    radius_m: String(radiusM),
  });
  const response = await fetch(`${apiBaseUrl}/buildings/lookup/ign-at-point?${params.toString()}`, {
    headers: buildHeaders(token),
  });
  return parseResponse<IgnPointLookup>(response);
}

/** Ajoute un bâtiment Po2 à la liste ASTECH comme bien « à créer » (décision Q13). */
export async function createLegacyAssetFromBuilding(
  token: string,
  buildingId: number,
): Promise<LegacyAsset> {
  const response = await fetch(`${apiBaseUrl}/patrimoine/legacy/from-building/${buildingId}`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<LegacyAsset>(response);
}

/** Valide les rattachements proposés par le moteur. Sans ids : tout confirmer. */
export async function confirmLegacyProposals(
  token: string,
  assetIds?: number[],
): Promise<{ confirmed: number }> {
  const response = await fetch(`${apiBaseUrl}/patrimoine/legacy/confirm`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify({ asset_ids: assetIds ?? null }),
  });
  return parseResponse<{ confirmed: number }>(response);
}

/**
 * Ajoute un LOCAL Po2 à la liste ASTECH comme bien « à créer » (décision Q13).
 * Pendant de `createLegacyAssetFromBuilding` : un CODE_BIEN désigne souvent un local.
 */
export async function createLegacyAssetFromLocal(
  token: string,
  localId: number,
): Promise<LegacyAsset> {
  const response = await fetch(`${apiBaseUrl}/patrimoine/legacy/from-local/${localId}`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<LegacyAsset>(response);
}

/** Compte ce qui partirait dans le fichier de retour, sans produire le classeur. */
export async function previewLegacyExport(
  token: string,
): Promise<{ exported_rows: number; review_rows: number; columns: string[]; missing_columns: string[]; sheet_name: string }> {
  const response = await fetch(`${apiBaseUrl}/patrimoine/legacy/export/preview`, {
    headers: buildHeaders(token),
  });
  return parseResponse(response);
}

/**
 * Télécharge le classeur de retour ASTECH (feuille réinjectable + traçabilité +
 * à vérifier). Les en-têtes sont recopiés à l'octet près depuis le fichier importé.
 */
export async function downloadLegacyExport(
  token: string,
): Promise<{ blob: Blob; filename: string }> {
  const response = await fetch(`${apiBaseUrl}/patrimoine/legacy/export`, {
    headers: buildHeaders(token),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "Export impossible.");
  }
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  return {
    blob: await response.blob(),
    filename: match?.[1] ?? "retour_astech.xlsx",
  };
}

/**
 * Remise à zéro totale : rattachements, candidats, positions et décisions « ignoré ».
 * Les biens restent, l'écran revient à l'état juste après l'import.
 */
export async function resetLegacyEverything(token: string): Promise<{ reset: number }> {
  const response = await fetch(`${apiBaseUrl}/patrimoine/legacy/reset-all`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<{ reset: number }>(response);
}

/**
 * Efface TOUT le référentiel ASTECH importé (biens + imports), pour repartir d'un
 * export neuf. Les bâtiments et locaux Po2 créés en cours de route sont conservés.
 */
export async function deleteLegacyImports(
  token: string,
): Promise<{ assets_deleted: number; imports_deleted: number }> {
  const response = await fetch(`${apiBaseUrl}/patrimoine/legacy/import`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });
  return parseResponse<{ assets_deleted: number; imports_deleted: number }>(response);
}

/**
 * Fait du bien ASTECH un local du bâtiment auquel il est rattaché — en créant ce local
 * s'il n'existe pas. Le bâtiment porteur reste la source de l'adresse et du cadastre.
 */
export async function convertLegacyAssetToLocal(
  token: string,
  assetId: number,
): Promise<LegacyAsset> {
  const response = await fetch(`${apiBaseUrl}/patrimoine/legacy/${assetId}/to-local`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<LegacyAsset>(response);
}

/**
 * Crée un bien ASTECH **de toutes pièces**, au point donné.
 *
 * Les deux autres entrées partent d'une entité Po2 déjà connue ; celle-ci sert au cas
 * où il n'y a rien de préexistant. Statut « à créer » : le CODE_BIEN sortira vide du
 * réexport, c'est ASTECH qui l'attribuera.
 */
export async function createLegacyAssetAtPoint(
  token: string,
  name: string,
  lat: number,
  lon: number,
): Promise<LegacyAsset> {
  const query = new URLSearchParams({ name, lat: String(lat), lon: String(lon) });
  const response = await fetch(`${apiBaseUrl}/patrimoine/legacy/at-point?${query}`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<LegacyAsset>(response);
}

export type LegacyGeocodeBatch = {
  traites: number;
  positionnes: number;
  echecs: { code_bien: string; motif: string }[];
  restants: number;
};

/**
 * Pose sur leur adresse ASTECH les biens sans position, par lots.
 * L'appelant rappelle jusqu'à `restants === 0`, en cumulant les échecs dans `offset` —
 * un bien introuvable reste sans position et serait sinon rejoué indéfiniment.
 */
export async function geocodePendingLegacyAssets(
  token: string,
  limit: number,
  offset: number,
): Promise<LegacyGeocodeBatch> {
  const response = await fetch(
    `${apiBaseUrl}/patrimoine/legacy/geocode-pending?limit=${limit}&offset=${offset}`,
    { method: "POST", headers: buildHeaders(token) },
  );
  return parseResponse<LegacyGeocodeBatch>(response);
}

/**
 * Retour arrière sur la dernière action du rapprochement (décision Q46).
 *
 * `disponible` dit qu'elle est défaisable ; `libelle` la nomme même quand elle ne l'est
 * pas — un geste de masse (import, purge) pose une borne et laisse `lignes` à zéro.
 */
export type LegacyUndoState = {
  disponible: boolean;
  libelle: string | null;
  lignes: number;
  date: string | null;
};

export type LegacyUndoResult = {
  annule: boolean;
  libelle: string | null;
  lignes: number;
  motif: string | null;
};

export async function peekLegacyUndo(token: string): Promise<LegacyUndoState> {
  const response = await fetch(`${apiBaseUrl}/patrimoine/legacy/undo`, {
    headers: buildHeaders(token),
  });
  return parseResponse<LegacyUndoState>(response);
}

export async function undoLegacyLastAction(token: string): Promise<LegacyUndoResult> {
  const response = await fetch(`${apiBaseUrl}/patrimoine/legacy/undo`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<LegacyUndoResult>(response);
}

export type PatrimonyDuplicateEntry = {
  id: number;
  nom: string | null;
  conserve_id: number;
  liens: number;
};

export type PatrimonyDuplicatesResult = {
  dry_run: boolean;
  batiments_supprimes: PatrimonyDuplicateEntry[];
  locaux_supprimes: PatrimonyDuplicateEntry[];
  /** Locaux qui ne font que redire le nom du bâtiment qui les contient. */
  locaux_homonymes_supprimes: PatrimonyDuplicateEntry[];
  conserves_car_lies: PatrimonyDuplicateEntry[];
};

/**
 * Supprime les doublons **stricts** du référentiel Po2 (bâtiments et locaux).
 * `dryRun` ne supprime rien : il renvoie ce qui partirait, pour l'annoncer avant.
 */
export async function purgePatrimonyDuplicates(
  token: string,
  dryRun: boolean,
): Promise<PatrimonyDuplicatesResult> {
  const response = await fetch(
    `${apiBaseUrl}/buildings/duplicates/purge?dry_run=${dryRun ? "true" : "false"}`,
    { method: "POST", headers: buildHeaders(token) },
  );
  return parseResponse<PatrimonyDuplicatesResult>(response);
}

/**
 * **Réforme** un bien — il sort du parc — ou annule cette réforme.
 * La ligne est conservée dans Po2 : elle sort du parcours et du réexport, et reste
 * consultable sous le filtre « REFORMER ».
 */
export async function markLegacyAssetGone(
  token: string,
  assetId: number,
  gone: boolean,
): Promise<LegacyAsset> {
  const response = await fetch(
    `${apiBaseUrl}/patrimoine/legacy/${assetId}/gone?gone=${gone ? "true" : "false"}`,
    { method: "POST", headers: buildHeaders(token) },
  );
  return parseResponse<LegacyAsset>(response);
}

/**
 * Supprime TOUS les rapprochements ASTECH ↔ Po2 et remet les biens à traiter.
 * Les biens « à créer », « ignoré » et « hors périmètre » sont préservés.
 */
export async function resetLegacyLinks(token: string): Promise<{ cleared: number }> {
  const response = await fetch(`${apiBaseUrl}/patrimoine/legacy/reset-links`, {
    method: "POST",
    headers: buildHeaders(token),
  });
  return parseResponse<{ cleared: number }>(response);
}

/** Repositionne un bâtiment Po2 et rafraîchit son adresse. */
export async function moveBuildingRequest(
  token: string,
  buildingId: number,
  lat: number,
  lon: number,
): Promise<Building> {
  const response = await fetch(`${apiBaseUrl}/buildings/${buildingId}/position`, {
    method: "PATCH",
    headers: buildHeaders(token),
    body: JSON.stringify({ lat, lon, resolve_address: true }),
  });
  return parseResponse<Building>(response);
}
