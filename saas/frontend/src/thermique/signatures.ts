// Catalogue des signatures graphiques d'un projet, étape E1 (docs/thermique/refondation-parcours-decisions.md).
import { request } from "./api";

export type Signature = {
  cle: string;
  genre: "trait" | "aplat";
  libelle: string;
  couleur: string;
  luminance: number;
  largeur?: number;
  tirets?: string;
  nombre: number;
  longueur_m?: number;
  aire_m2?: number;
  part_courte?: number;
  part_appariee?: number;
  part_dans_murs: number;
  part_alignee?: number;
  planches: number[];
  role_propose: string;
  raison: string;
  role: string | null;
};

export type SignatureCatalogue = {
  signatures: Signature[];
  planches: { id: number; libelle: string }[];
  roles_traits: Record<string, string>;
  roles_aplats: Record<string, string>;
  validees: number;
  total: number;
};

// Points PDF : segments [x1, y1, x2, y2] pour un trait, anneaux [[x, y], …] pour un remplissage.
export type SignatureElements = { segments?: number[][]; polygones?: number[][][]; tronque: boolean };

export const signaturesApi = {
  get: (token: string, projectId: number) => request<SignatureCatalogue>(token, `/thermique/projects/${projectId}/signatures`),
  save: (token: string, projectId: number, roles: Record<string, string | null>) =>
    request<SignatureCatalogue>(token, `/thermique/projects/${projectId}/signatures`, { method: "PUT", body: JSON.stringify({ roles }) }),
  elements: (token: string, sheetId: number, cle: string) =>
    request<SignatureElements>(token, `/thermique/sheets/${sheetId}/signatures/elements?cle=${encodeURIComponent(cle)}`),
};
