import { request, type PdfPoint } from "./api";

export type VisionCategory =
  | "mur_exterieur"
  | "refend"
  | "cloison"
  | "isolation"
  | "menuiserie_exterieure"
  | "menuiserie_interieure"
  | "terrasse"
  | "balcon"
  | "poteau"
  | "garde_corps"
  | "indetermine";

export type VisionObject = {
  id: string;
  category: VisionCategory;
  subtype: string;
  geometry_type: "polyline" | "polygon" | "bbox";
  points: PdfPoint[];
  confidence: number;
  evidence: string;
  review_required: boolean;
  source: "ia_visuelle" | "corrige" | "manuel";
  confirmed: boolean;
};

export type VisionResult = {
  version: number;
  method: "ia_visuelle_raster" | "claude_code_agent_raster";
  uses_pdf_vectors: false;
  model: string;
  created_at: number;
  objects: VisionObject[];
  counts: Partial<Record<VisionCategory, number>>;
  review_count: number;
  observations: string[];
  agent_rotation_deg?: 0 | 90 | 180 | 270;
};

export type VisionState = {
  stage: "raster" | "vision" | "normalisation" | null;
  running: boolean;
  error: string | null;
  result: VisionResult | null;
};

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });

export const visionApi = {
  state: (token: string, sheetId: number) => request<VisionState>(token, `/thermique/sheets/${sheetId}/vision-analysis`),
  start: (token: string, sheetId: number) =>
    request<VisionState>(token, `/thermique/sheets/${sheetId}/vision-analysis`, { method: "POST" }),
  importAgent: (token: string, sheetId: number, payload: unknown) =>
    request<VisionState>(token, `/thermique/sheets/${sheetId}/vision-analysis/agent-import`, json("POST", payload)),
  update: (
    token: string,
    sheetId: number,
    objectId: string,
    payload: { points?: PdfPoint[]; category?: VisionCategory; confirmed?: boolean },
  ) => request<VisionResult>(token, `/thermique/sheets/${sheetId}/vision-objects/${encodeURIComponent(objectId)}`, json("PATCH", payload)),
  create: (
    token: string,
    sheetId: number,
    payload: { points: PdfPoint[]; category: VisionCategory; geometry_type: "polyline" | "polygon" },
  ) => request<VisionResult>(token, `/thermique/sheets/${sheetId}/vision-objects`, json("POST", payload)),
  remove: (token: string, sheetId: number, objectId: string) =>
    request<VisionResult>(token, `/thermique/sheets/${sheetId}/vision-objects/${encodeURIComponent(objectId)}`, { method: "DELETE" }),
};

export const VISION_STYLES: Record<VisionCategory, { label: string; color: string }> = {
  mur_exterieur: { label: "Murs extérieurs", color: "#d73027" },
  refend: { label: "Murs de refend", color: "#7b3294" },
  cloison: { label: "Cloisons", color: "#4575b4" },
  isolation: { label: "Isolation", color: "#fdae61" },
  menuiserie_exterieure: { label: "Menuiseries extérieures", color: "#00a6d6" },
  menuiserie_interieure: { label: "Menuiseries intérieures", color: "#66c2a5" },
  terrasse: { label: "Terrasses", color: "#8c6d31" },
  balcon: { label: "Balcons", color: "#a6761d" },
  poteau: { label: "Poteaux", color: "#525252" },
  garde_corps: { label: "Garde-corps", color: "#636363" },
  indetermine: { label: "À déterminer", color: "#e7298a" },
};
