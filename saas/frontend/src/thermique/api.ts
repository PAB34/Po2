const apiBaseUrl = (import.meta as ImportMeta & { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL ?? "/api";

export type SheetNature = "plan" | "coupe" | "facade" | "plan_masse" | "autre";
export type SheetStatus = "a_classer" | "a_mettre_a_l_echelle" | "prete";
export type PdfPoint = [number, number];

/** Flèche du nord tracée sur la planche, en points PDF : `p2` est la pointe, du côté du nord. */
export type SheetNorth = {
  p1: PdfPoint;
  p2: PdfPoint;
  longueur_pt: number;
};

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
  nord: SheetNorth | null;
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

export type StudyLocalNature = "chauffe" | "circulation" | "non_chauffe" | "gaine_technique";
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
  /** Polyligne du côté : un côté est un regroupement de sondages, sa position ne se déduit pas
   *  du contour. Sans elle, aucune cote ne peut être posée sur le plan (D80). */
  trace?: PdfPoint[];
  trace_pdf?: PdfPoint[];
  enveloppe?: StudyEnvelopeItem[];
};
/** Un élément d'enveloppe relevé, tel qu'il se dessine sur le plan (mur, isolant, doublage, menuiserie…). */
export type StudyEnvelopeShape = {
  id: string;
  category: string;
  subtype: string;
  geometry_type: "polygon" | "polyline";
  confidence?: number;
  review_required?: boolean;
  points_pdf?: PdfPoint[];
  source_parcours?: { troncon?: string; debut_m?: number; fin_m?: number; piece?: string | null; composant?: string | null };
};
/**
 * Un élément tel qu'il a été relevé sur l'enveloppe. C'est **la** donnée qui fait foi : les formes
 * dessinées en sont régénérées à chaque recalcul, donc toute correction s'écrit ici (D99).
 */
export type StudyReleveElement = {
  troncon: string;
  debut_m: number;
  fin_m: number;
  type: string;
  composant: string | null;
  nu_exterieur_cm: number;
  nu_interieur_cm: number;
  nu_exterieur_fin_cm?: number;
  nu_interieur_fin_cm?: number;
  confiance?: number;
  /** Ce que l'agent a cru voir : la phrase qui justifie sa lecture. */
  indice?: string;
  a_verifier?: boolean;
  confirme?: boolean;
  corrige?: boolean;
  exclu?: boolean;
  motif_exclusion?: string;
  /** Valeurs lues par l'agent, gardées à côté de la correction humaine (Q7). */
  releve_origine?: Record<string, unknown>;
};
/** Un pont thermique relevé, avec sa position sur la feuille. */
export type StudyBridge = {
  type: string;
  troncon: string;
  abscisse_m?: number;
  longueur_m?: number;
  piece: string | null;
  composant?: string | null;
  point_pdf?: PdfPoint;
  /** État repris du relevé : une liaison écartée reste dessinée, en grisé (D113). */
  exclu?: boolean;
  a_verifier?: boolean;
  confirme?: boolean;
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
    releve_brut: { elements: StudyReleveElement[]; catalogue: unknown[]; observations: string[] };
    /** Tracé reprojeté des éléments relevés, pour les dessiner sur le plan (D75). */
    objets?: StudyEnvelopeShape[];
    /** Liaisons du relevé avec leur position sur la feuille : les ponts thermiques (D74). */
    liaisons?: StudyBridge[];
    raccords: unknown[];
    controle: Record<string, unknown>;
    demandes: { piece: string; objet: string; motif: string }[];
  };
  couverture: StudyCoverage;
  coherence?: StudyCoherence;
};
/** Rapport de la chaîne sur elle-même : les deux lectures du niveau confrontées (D77). */
export type StudyCoherence = {
  version: number;
  niveau: string | null;
  locaux: number;
  anomalies: number;
  statut: "ok" | "attention";
  controles: {
    code: string;
    titre: string;
    statut: "ok" | "attention";
    resume: string;
    anomalies: { message: string; local?: string | null }[];
  }[];
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
/** Un élément relevé, désigné par sa position sur l'enveloppe : la clé que porte aussi son tracé (F4). */
export type StudyElementRef = { troncon: string; debut_m: number; fin_m: number };
/** Ce que F4 laisse corriger : les trois familles qui changent le calcul (Q1). */
export type StudyElementChanges = Partial<{
  type: string;
  composant: string;
  nu_exterieur_cm: number;
  nu_interieur_cm: number;
  nu_exterieur_fin_cm: number;
  nu_interieur_fin_cm: number;
}>;
export type StudyElementScope = "cet_element" | "partout";
export type StudyOperation =
  | { type: "modifier"; id: string; contour_pdf?: PdfPoint[]; nature?: StudyLocalNature; nom?: string }
  | { type: "couper"; id: string; segment_pdf: PdfPoint[]; noms?: string[] }
  | { type: "fusionner"; ids: string[]; nom?: string }
  | { type: "local_ajouter"; contour_pdf: PdfPoint[]; nature: StudyLocalNature; nom: string }
  | { type: "local_supprimer"; id: string }
  | { type: "element_confirmer"; element: StudyElementRef }
  | { type: "element_corriger"; element: StudyElementRef; changes: StudyElementChanges; portee?: StudyElementScope }
  | { type: "element_ecarter"; element: StudyElementRef; motif: string }
  | { type: "element_reactiver"; element: StudyElementRef };
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
/** Un niveau dans la file d'analyse, que le relais du poste vient prendre (F0). */
export type Work = {
  id: number;
  project_id: number;
  sheet_id: number;
  label: string;
  level_label: string | null;
  statut: "en_attente" | "en_cours" | "fini" | "refuse" | "echec";
  rang: number;
  message: string | null;
  pris_a: string | null;
  fini_a: string | null;
  created_at: string;
};
export type QueueResult = {
  ajoutes: Work[];
  /** Niveaux non mis en file, avec la raison en clair : échelle absente, travail déjà fait… */
  ecartes: { sheet_id: number; label: string; motif: string }[];
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
  /** Pose le nord : p1 la base de la flèche, p2 sa pointe du côté du nord. Renvoie les planches modifiées. */
  setNorth: (token: string, sheetId: number, payload: { p1: PdfPoint; p2: PdfPoint; tout_le_projet: boolean }) =>
    request<Sheet[]>(token, `/thermique/sheets/${sheetId}/nord`, { method: "POST", body: JSON.stringify(payload) }),
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
  /** Met en file les niveaux analysables du projet ; le relais du poste videra la file (D93). */
  analyseProject: (token: string, projectId: number) =>
    request<QueueResult>(token, `/thermique/projects/${projectId}/analyser`, { method: "POST" }),
  listWorks: (token: string, projectId: number) =>
    request<Work[]>(token, `/thermique/projects/${projectId}/travaux`),
  documentFileUrl: (documentId: number) => `${apiBaseUrl}/thermique/documents/${documentId}/file`,
  // Fiche des tuiles d'une planche (rendue par le serveur à la première demande).
  getRaster: (token: string, sheetId: number, rotation: number) =>
    request<import("./raster").RasterManifest>(token, `/thermique/sheets/${sheetId}/raster?rotation=${rotation}`),
  apiUrl: (path: string) => `${apiBaseUrl}${path}`,
};
