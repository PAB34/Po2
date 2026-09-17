// Désignation des calques par l'exemple, étape E1 (docs/thermique/refondation-parcours-decisions.md §10).
import { request, type PdfPoint } from "./api";

export type CalqueCount = { id: number; libelle: string; nombre: number };

export type CalqueRule = {
  id: number;
  signature: string;
  forme: string;
  nature: string;
  exclusions: { planche: number; element: number }[];
  libelle: string;
  forme_libelle: string;
  nature_libelle: string;
  total: number;
  par_planche: CalqueCount[];
};

export type CalquesProject = {
  regles: CalqueRule[];
  natures: Record<string, string>;
  planches: { id: number; libelle: string }[];
};

// « * » = toutes les formes de la signature.
export type CalqueFamily = { forme: string; forme_libelle: string; total: number; par_planche: CalqueCount[] };

export type CalquePick = {
  element: {
    planche: number;
    index: number;
    genre: "trait" | "remplissage";
    signature: string;
    forme: string;
    libelle: string;
    forme_libelle: string;
    // x1, y1, x2, y2… en points PDF
    coords: number[];
  };
  familles: CalqueFamily[];
  regle: { id: number; nature: string; nature_libelle: string; forme: string; exclu: boolean } | null;
};

export type CalqueGeometry = { traits: number[][]; remplissages: number[][]; tronque: boolean };

export type SheetDesignations = { natures: Record<string, { traits: number[][]; remplissages: number[][] }>; tronque: boolean };

// Lasso tracé par Maj + glisser, en points PDF : x1, y1, x2, y2…
export type CalqueLasso = number[];

export type CalqueZone = CalqueGeometry & {
  calques: { id: number; nature: string; nature_libelle: string; libelle: string; forme_libelle: string; actifs: number; retires: number }[];
};

export const NATURE_COLORS: Record<string, string> = {
  mur: "#c0392b",
  isolant: "#e39b00",
  cloison: "#8e44ad",
  menuiserie: "#1f78d1",
  porte: "#16a085",
  garde_corps: "#5d6d7e",
  plancher: "#7f5539",
  toiture: "#2e7d32",
};

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });

export const calquesApi = {
  list: (token: string, projectId: number) => request<CalquesProject>(token, `/thermique/projects/${projectId}/calques`),
  save: (token: string, projectId: number, payload: { signature: string; forme: string; nature: string }) =>
    request<CalquesProject>(token, `/thermique/projects/${projectId}/calques`, json("POST", payload)),
  remove: (token: string, projectId: number, ruleId: number) =>
    request<CalquesProject>(token, `/thermique/projects/${projectId}/calques/${ruleId}`, { method: "DELETE" }),
  toggleExclusion: (token: string, projectId: number, ruleId: number, payload: { planche_id: number; element: number }) =>
    request<CalquesProject>(token, `/thermique/projects/${projectId}/calques/${ruleId}/exclusions`, json("POST", payload)),
  pick: (token: string, sheetId: number, point: PdfPoint, tolerance: number) =>
    request<CalquePick>(token, `/thermique/sheets/${sheetId}/calques/designer`, json("POST", { x: point[0], y: point[1], tolerance })),
  family: (token: string, sheetId: number, signature: string, forme: string) =>
    request<CalqueGeometry>(
      token,
      `/thermique/sheets/${sheetId}/calques/famille?signature=${encodeURIComponent(signature)}&forme=${encodeURIComponent(forme)}`,
    ),
  zone: (token: string, sheetId: number, contour: CalqueLasso) =>
    request<CalqueZone>(token, `/thermique/sheets/${sheetId}/calques/zone`, json("POST", { contour })),
  applyZone: (token: string, sheetId: number, contour: CalqueLasso, regles: number[], action: "retirer" | "remettre") =>
    request<CalquesProject>(token, `/thermique/sheets/${sheetId}/calques/zone/appliquer`, json("POST", { contour, regles, action })),
  designated: (token: string, sheetId: number) => request<SheetDesignations>(token, `/thermique/sheets/${sheetId}/calques/designes`),
};
