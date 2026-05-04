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
};

export type BuildingImportPreview = {
  filename: string;
  columns: string[];
  total_rows: number;
  sample_rows: Array<Record<string, string>>;
  name_column: string | null;
  address_column: string | null;
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

export type BuildingIgnAttachmentPayload = {
  validated_name?: string;
  selected_feature?: GeoJsonFeature | null;
  lat?: number | null;
  lon?: number | null;
};

export type CreateBuildingFromNamingPayload = {
  unique_key: string;
  validated_name?: string;
  city_id?: number;
  selected_feature?: GeoJsonFeature | null;
};

export type CreateBuildingPayload = {
  city_id?: number;
  dgfip_unique_key?: string;
  dgfip_source_file?: string;
  dgfip_source_rows_json?: string;
  dgfip_reference_norm?: string;
  nom_batiment?: string;
  nom_commune?: string;
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
  ign_toponym_candidates_json?: string;
  parcel_labels_json?: string;
  majic_building_values_json?: string;
  majic_entry_values_json?: string;
  majic_level_values_json?: string;
  majic_door_values_json?: string;
  source_creation?: string;
  statut_geocodage?: string;
};

export type UpdateBuildingPayload = {
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
};

export type Local = {
  id: number;
  building_id: number;
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
  nom_local: string;
  type_local: string;
  niveau?: string;
  surface_m2?: number;
  usage?: string;
  statut_occupation?: string;
  commentaire?: string;
};

export type UpdateLocalPayload = {
  nom_local?: string;
  type_local?: string;
  niveau?: string;
  surface_m2?: number;
  usage?: string;
  statut_occupation?: string;
  commentaire?: string;
};

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = "Une erreur est survenue.";

    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        message = payload.detail;
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

export async function fetchFreeAddressLookup(token: string, address: string): Promise<FreeAddressLookup> {
  const response = await fetch(`${apiBaseUrl}/buildings/lookup/free-address`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify({ address }),
  });

  return parseResponse<FreeAddressLookup>(response);
}

export async function previewBuildingImportFile(
  token: string,
  file: File,
  nameColumn?: string,
  addressColumn?: string,
): Promise<BuildingImportPreview> {
  const formData = new FormData();
  formData.append("file", file);
  if (nameColumn) {
    formData.append("name_column", nameColumn);
  }
  if (addressColumn) {
    formData.append("address_column", addressColumn);
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

export async function fetchNearbyDgfip(token: string, buildingId: number): Promise<NearbyDgfipRow[]> {
  const response = await fetch(`${apiBaseUrl}/buildings/${buildingId}/nearby-dgfip`, {
    headers: buildHeaders(token),
  });

  return parseResponse<NearbyDgfipRow[]>(response);
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

export async function createBuildingRequest(token: string, payload: CreateBuildingPayload): Promise<Building> {
  const response = await fetch(`${apiBaseUrl}/buildings`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseResponse<Building>(response);
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

export async function updateLocalRequest(token: string, buildingId: number, localId: number, payload: UpdateLocalPayload): Promise<Local> {
  const response = await fetch(`${apiBaseUrl}/buildings/${buildingId}/locals/${localId}`, {
    method: "PUT",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return parseResponse<Local>(response);
}

export async function deleteAllBuildingsRequest(token: string): Promise<{ deleted: number }> {
  const response = await fetch(`${apiBaseUrl}/buildings`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });

  return parseResponse<{ deleted: number }>(response);
}

export async function deleteLocalRequest(token: string, buildingId: number, localId: number): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/buildings/${buildingId}/locals/${localId}`, {
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
};

export type SupplierDistributionItem = {
  supplier: string;
  total_kva: number;
  prm_count: number;
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

export type PrmDetail = {
  usage_point_id: string;
  contract: PrmContract;
  address: PrmAddress;
  connection: PrmConnection;
  summary: PrmSummary;
  calibration: PrmCalibration;
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
  ratio: number;
};

export type DjuSeasonYear = {
  label: string;
  months: DjuSeasonMonthPoint[];
};

export type DjuSeasonData = {
  months_order: string[];
  months_labels: string[];
  years: DjuSeasonYear[];
  cible_by_month: Record<string, number | null>;
  current_label: string | null;
  current_ecart_percent: number | null;
  has_data: boolean;
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

export async function startSync(token: string, historyDays?: number): Promise<{ message: string }> {
  const params = historyDays ? `?history_days=${historyDays}` : "";
  const response = await fetch(`${apiBaseUrl}/energie/sync/start${params}`, {
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

export async function startMaxPowerSync(token: string, historyDays?: number): Promise<{ message: string }> {
  const params = historyDays ? `?history_days=${historyDays}` : "";
  const response = await fetch(`${apiBaseUrl}/energie/sync/max-power/start${params}`, {
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

export async function fetchDjuSyncStatus(token: string): Promise<DjuSyncStatus> {
  const response = await fetch(`${apiBaseUrl}/energie/sync/dju/status`, {
    headers: buildHeaders(token),
  });
  return parseResponse<DjuSyncStatus>(response);
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

export async function startLoadCurveSync(token: string): Promise<{ message: string }> {
  const response = await fetch(`${apiBaseUrl}/energie/sync/load-curve/start`, {
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