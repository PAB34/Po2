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
  // Échelle usuelle à moins de 1 % de celle déduite de la cote (ex. 99,97 → 100), sinon null.
  standard_scale: number | null;
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
  reference_sheet_id: number | null;
  created_at: string;
  updated_at: string;
  document_count: number;
  sheet_count: number;
  sheets_ready: number;
};

export type ProjectDetail = Project & { documents: ThermiqueDocument[] };

export type StudyLocalNature = "chauffe" | "circulation" | "non_chauffe";
/** Nature d'un côté de local : sur l'enveloppe, le long d'une paroi lue, ou limite d'usage (D59). */
export type StudyLimit = "exterieur" | "paroi" | "convention";
export type StudyLocalState = { status: "a_verifier" | "valide" | "a_revoir"; motif: string | null };
export type StudyEnvelopeItem = {
  composant?: string;
  type?: string;
  composition?: string;
  lineaire_m?: number;
  largeurs_cm?: number[];
};
export type StudySide = {
  adjacence: string;
  voisin?: string;
  longueur_m: number;
  epaisseur_cm?: number | null;
  orientation?: string;
  deperditif: boolean;
  enveloppe?: StudyEnvelopeItem[];
};
export type StudyRoomSheet = {
  piece: string;
  local: StudyLocalNature;
  surface_m2: number;
  perimetre_m: number;
  cotes: StudySide[];
  deperditif_m?: number;
  par_adjacence?: Record<string, number>;
  baies?: StudyEnvelopeItem[];
  ponts?: Record<string, number>;
  liaison_plancher_m?: number;
  a_completer?: string[];
  alertes?: string[];
};
export type StudyRoom = {
  id: string;
  nom: string;
  nature: StudyLocalNature;
  contour: PdfPoint[];
  contour_pdf: PdfPoint[];
  limites: StudyLimit[];
  surface_m2: number;
  fiche: StudyRoomSheet;
  synthese: Record<string, unknown> & {
    parois?: StudyEnvelopeItem[];
    menuiseries?: StudyEnvelopeItem[];
    ponts?: Record<string, number>;
    sur_non_chauffe_m?: number;
  };
  demandes: { piece: string; objet: string; motif: string }[];
};
export type StudyContent = {
  format: "thermique.etude_niveau";
  format_version: number;
  niveau: string;
  locaux: StudyRoom[];
  enveloppe: {
    catalogue: unknown[];
    releve_brut: { elements: unknown[]; catalogue: unknown[]; observations: string[] };
    raccords: unknown[];
    controle: Record<string, unknown>;
    demandes: { piece: string; objet: string; motif: string }[];
  };
  couverture: StudyCoverage;
};
export type StudyCoverage = {
  surface_emprise_m2: number;
  surface_affectee_m2: number;
  surface_non_affectee_m2: number;
  surface_hors_emprise_m2: number;
  chevauchement_m2: number;
  chevauchements: { locaux: string[]; surface_m2: number }[];
  taux_couverture_pct: number;
  zones_non_affectees: PdfPoint[][];
  zones_non_affectees_pdf?: PdfPoint[][];
};
export type StudyOperation =
  | { type: "modifier"; id: string; contour_pdf?: PdfPoint[]; nature?: StudyLocalNature; nom?: string }
  | { type: "couper"; id: string; segment_pdf: PdfPoint[]; noms?: string[] }
  | { type: "fusionner"; ids: string[]; nom?: string };
export type StudyPreview = {
  content: StudyContent;
  couverture: StudyCoverage;
  voisins_modifies: string[];
  bloquant: string | null;
};
export type StudyVersion = {
  version_number: number;
  reason: string;
  created_by_user_id: number | null;
  created_at: string;
};
export type Study = {
  id: number;
  project_id: number;
  sheet_id: number;
  format_version: number;
  version_number: number;
  content: StudyContent;
  local_states: Record<string, StudyLocalState>;
  imported_by_user_id: number | null;
  created_at: string;
  updated_at: string;
};

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

export async function request<T>(token: string, path: string, init: RequestInit = {}): Promise<T> {
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
  updateProject: (token: string, projectId: number, payload: { name?: string; description?: string | null; reference_sheet_id?: number | null }) =>
    request<Project>(token, `/thermique/projects/${projectId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteProject: (token: string, projectId: number) =>
    request<void>(token, `/thermique/projects/${projectId}`, { method: "DELETE" }),
  eraseAllProjects: (token: string, confirmation: string) =>
    request<{ projets_effaces: number }>(token, "/thermique/projects/tout-effacer", {
      method: "POST",
      body: JSON.stringify({ confirmation }),
    }),
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
  getStudy: (token: string, sheetId: number) => request<Study | null>(token, `/thermique/sheets/${sheetId}/etude`),
  importStudy: (token: string, sheetId: number, file: File, replace = false) => {
    const form = new FormData();
    form.append("fichier", file);
    return request<Study>(token, `/thermique/sheets/${sheetId}/etude/importer?remplacer=${replace}`, {
      method: "POST",
      body: form,
    });
  },
  remodelStudy: (token: string, sheetId: number, operations: StudyOperation[], localId?: string | null) =>
    request<StudyPreview>(
      token,
      `/thermique/sheets/${sheetId}/etude/remodeliser${localId ? `?local_id=${encodeURIComponent(localId)}` : ""}`,
      { method: "POST", body: JSON.stringify({ operations }) },
    ),
  saveStudy: (
    token: string,
    sheetId: number,
    payload: { operations: StudyOperation[]; local_id?: string | null; motif?: string; valider?: boolean },
  ) => request<Study>(token, `/thermique/sheets/${sheetId}/etude/enregistrer`, { method: "POST", body: JSON.stringify(payload) }),
  listStudyVersions: (token: string, sheetId: number) =>
    request<StudyVersion[]>(token, `/thermique/sheets/${sheetId}/etude/versions`),
  restoreStudyVersion: (token: string, sheetId: number, numero: number) =>
    request<Study>(token, `/thermique/sheets/${sheetId}/etude/versions/${numero}/restaurer`, { method: "POST" }),
  documentFileUrl: (documentId: number) => `${apiBaseUrl}/thermique/documents/${documentId}/file`,
  // Fiche des tuiles d'une planche (rendue par le serveur à la première demande).
  getRaster: (token: string, sheetId: number, rotation: number) =>
    request<import("./raster").RasterManifest>(token, `/thermique/sheets/${sheetId}/raster?rotation=${rotation}`),
  apiUrl: (path: string) => `${apiBaseUrl}${path}`,
};
