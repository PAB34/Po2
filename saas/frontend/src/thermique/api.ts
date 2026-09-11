const apiBaseUrl = (import.meta as ImportMeta & { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL ?? "/api";

export type SheetNature = "plan" | "coupe" | "facade" | "plan_masse" | "autre";
export type SheetStatus = "a_classer" | "a_mettre_a_l_echelle" | "prete";
export type PdfPoint = [number, number];

export type SheetCalibration = {
  p1: PdfPoint;
  p2: PdfPoint;
  length_pt: number;
  real_length_m: number;
  denominator_from_cote: number;
  measured_m: number | null;
  ecart_pct: number | null;
};

export type Sheet = {
  id: number;
  project_id: number;
  document_id: number;
  page_index: number;
  label: string;
  nature: SheetNature | null;
  nature_suggested: SheetNature | null;
  level_label: string | null;
  scale_denominator: number | null;
  scale_source: "declaree" | "cote" | null;
  rotation_deg: number;
  page_width_pt: number;
  page_height_pt: number;
  status: SheetStatus;
  calibration: SheetCalibration | null;
};

export type ThermiqueDocument = {
  id: number;
  project_id: number;
  original_filename: string;
  file_format: string;
  size_bytes: number;
  page_count: number;
  created_at: string;
  sheets: Sheet[];
};

export type Project = {
  id: number;
  owner_user_id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  document_count: number;
  sheet_count: number;
  sheets_ready: number;
};

export type ProjectDetail = Project & { documents: ThermiqueDocument[] };

export type UploadResult = {
  project: ProjectDetail;
  imported: string[];
  errors: { filename: string; message: string }[];
};

export type SheetChanges = Partial<{
  label: string;
  nature: SheetNature | null;
  level_label: string | null;
  rotation_deg: number;
  scale_denominator: number | null;
}>;

export type CalibrationPayload = {
  p1: PdfPoint;
  p2: PdfPoint;
  real_length_m: number;
  apply: boolean;
};

async function request<T>(token: string, path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${apiBaseUrl}${path}`, { ...init, headers });
  if (!response.ok) {
    let message = `Erreur ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        message = body.detail;
      }
    } catch {
      // réponse sans corps JSON : on garde le code HTTP
    }
    throw new Error(message);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const thermiqueApi = {
  listProjects: (token: string) => request<Project[]>(token, "/thermique/projects"),
  createProject: (token: string, payload: { name: string; description?: string }) =>
    request<Project>(token, "/thermique/projects", { method: "POST", body: JSON.stringify(payload) }),
  getProject: (token: string, projectId: number) => request<ProjectDetail>(token, `/thermique/projects/${projectId}`),
  updateProject: (token: string, projectId: number, payload: { name?: string; description?: string | null }) =>
    request<Project>(token, `/thermique/projects/${projectId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteProject: (token: string, projectId: number) =>
    request<void>(token, `/thermique/projects/${projectId}`, { method: "DELETE" }),
  uploadDocuments: (token: string, projectId: number, files: File[]) => {
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    return request<UploadResult>(token, `/thermique/projects/${projectId}/documents`, { method: "POST", body: form });
  },
  deleteDocument: (token: string, documentId: number) =>
    request<void>(token, `/thermique/documents/${documentId}`, { method: "DELETE" }),
  updateSheet: (token: string, sheetId: number, changes: SheetChanges) =>
    request<Sheet>(token, `/thermique/sheets/${sheetId}`, { method: "PATCH", body: JSON.stringify(changes) }),
  calibrateSheet: (token: string, sheetId: number, payload: CalibrationPayload) =>
    request<Sheet>(token, `/thermique/sheets/${sheetId}/calibration`, { method: "POST", body: JSON.stringify(payload) }),
  documentFileUrl: (documentId: number) => `${apiBaseUrl}/thermique/documents/${documentId}/file`,
  // Fiche des tuiles d'une planche (rendue par le serveur à la première demande).
  getRaster: (token: string, sheetId: number, rotation: number) =>
    request<import("./raster").RasterManifest>(token, `/thermique/sheets/${sheetId}/raster?rotation=${rotation}`),
  apiUrl: (path: string) => `${apiBaseUrl}${path}`,
};
