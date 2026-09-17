// Superposition des niveaux, étape E2 (docs/thermique/refondation-parcours-decisions.md §12).
import { request } from "./api";

export type SuperpositionSheet = {
  id: number;
  libelle: string;
  niveau_id: number | null;
  niveau: string | null;
  valide: boolean;
  // point de la planche + décalage = point de la référence (points PDF)
  decalage: [number, number] | null;
  cale_main: boolean;
};

export type SuperpositionOverview = { reference_id: number | null; planches: SuperpositionSheet[] };

export type SuperpositionProposal = {
  dx: number;
  dy: number;
  score: number;
  score_zero: number;
  etat: "reference" | "superpose" | "decale" | "incertain";
};

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });

export const superpositionApi = {
  overview: (token: string, projectId: number) =>
    request<SuperpositionOverview>(token, `/thermique/projects/${projectId}/superposition`),
  proposal: (token: string, projectId: number, sheetId: number, referenceId: number) =>
    request<SuperpositionProposal>(
      token,
      `/thermique/projects/${projectId}/superposition/proposition?planche_id=${sheetId}&reference_id=${referenceId}`,
    ),
  validate: (token: string, projectId: number, payload: { reference_id: number; planche_id: number; dx: number; dy: number }) =>
    request<SuperpositionOverview>(token, `/thermique/projects/${projectId}/superposition`, json("POST", payload)),
  reset: (token: string, projectId: number, sheetId: number) =>
    request<SuperpositionOverview>(token, `/thermique/projects/${projectId}/superposition/${sheetId}`, { method: "DELETE" }),
};
