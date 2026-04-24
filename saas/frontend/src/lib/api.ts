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

export type CreateBuildingFromNamingPayload = {
  unique_key: string;
  validated_name?: string;
  city_id?: number;
  selected_feature?: GeoJsonFeature | null;
};

export type CreateBuildingPayload = {
  city_id?: number;
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
};

export type UpdateBuildingPayload = Omit<CreateBuildingPayload, "city_id" | "nom_commune">;

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

export async function deleteLocalRequest(token: string, buildingId: number, localId: number): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/buildings/${buildingId}/locals/${localId}`, {
    method: "DELETE",
    headers: buildHeaders(token),
  });

  return parseResponse<void>(response);
}