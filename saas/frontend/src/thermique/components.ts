// Bibliothèque de projet et modèles réutilisables (docs/thermique/bibliotheque-projet-decisions.md).
import { request } from "./api";
import type { WallFacing, WallResult, WallType } from "./library";

export type ComponentNature = "paroi" | "menuiserie" | "pont";
export type ComponentStatus = "hypothese" | "conforme_cctp";

export type ComponentCategory = {
  id: string;
  libelle: string;
  singulier: string;
  // « Nouveau mur », « Nouvelle menuiserie »…
  nouveau: string;
  prefixe: string;
  nature: ComponentNature;
  paroi?: WallType;
  donne_sur?: WallFacing;
  sous_categories: string[];
};

export type ComponentResult = {
  grandeur: string;
  unite: string;
  // Vide tant que la composition est incomplète (brouillon).
  valeur: number | null;
  resume: string;
  epaisseur_m?: number | null;
  epaisseur_complete?: boolean;
  sw?: number | null;
  tlw?: number | null;
  detail: WallResult | null;
};

export type LibraryComponent = {
  id: number;
  project_id: number | null;
  categorie: string;
  code: string;
  nom: string;
  statut: ComponentStatus;
  composition: Record<string, unknown>;
  resultat: ComponentResult | null;
  referentiel: Record<string, string> | null;
  notes: string | null;
  source_component_id: number | null;
  created_at: string | null;
  updated_at: string | null;
};

export type ComponentPayload = Partial<{
  categorie: string;
  nom: string;
  code: string;
  statut: ComponentStatus;
  composition: Record<string, unknown>;
  notes: string | null;
}>;

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });

export const componentsApi = {
  categories: (token: string) =>
    request<{ categories: ComponentCategory[]; statuts: Record<ComponentStatus, string> }>(token, "/thermique/composants/categories"),
  evaluate: (token: string, categorie: string, composition: Record<string, unknown>) =>
    request<ComponentResult>(token, "/thermique/composants/evaluer", json("POST", { categorie, composition })),
  listProject: (token: string, projectId: number) => request<LibraryComponent[]>(token, `/thermique/projects/${projectId}/composants`),
  createInProject: (token: string, projectId: number, payload: ComponentPayload) =>
    request<LibraryComponent>(token, `/thermique/projects/${projectId}/composants`, json("POST", payload)),
  importModel: (token: string, projectId: number, modelId: number) =>
    request<LibraryComponent>(token, `/thermique/projects/${projectId}/composants/importer`, json("POST", { modele_id: modelId })),
  listModels: (token: string) => request<LibraryComponent[]>(token, "/thermique/modeles"),
  createModel: (token: string, payload: ComponentPayload) => request<LibraryComponent>(token, "/thermique/modeles", json("POST", payload)),
  update: (token: string, id: number, payload: ComponentPayload) =>
    request<LibraryComponent>(token, `/thermique/composants/${id}`, json("PATCH", payload)),
  remove: (token: string, id: number) => request<void>(token, `/thermique/composants/${id}`, { method: "DELETE" }),
  duplicate: (token: string, id: number) => request<LibraryComponent>(token, `/thermique/composants/${id}/dupliquer`, { method: "POST" }),
  saveAsModel: (token: string, id: number) => request<LibraryComponent>(token, `/thermique/composants/${id}/modele`, { method: "POST" }),
};
