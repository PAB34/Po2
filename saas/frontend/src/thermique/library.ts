import { thermiqueApi } from "./api";

export type Vitrage = "triple" | "double" | "double_controle_solaire";
export type Menuiserie = "fenetre" | "porte_fenetre";
export type Statut = "valide" | "alerte" | "erreur";

export type ProtectionCase = {
  section: string;
  code: string;
  libelle: string;
  intitule_document: string;
  facteurs: number[];
  page: number | null;
};

export type WindowRow = {
  id: string;
  section: string;
  protection: string;
  menuiserie: Menuiserie;
  vantaux: number;
  sigma: number;
  vitrage: Vitrage;
  avec_protection: boolean;
  u: number;
  s_c: number[];
  s_e: number[];
  tl: number;
  tl_dif: number;
  page: number;
  statut: Statut;
  // Valeur corrigée à l'extraction (coquille du document), toujours signalée.
  correction?: string;
};

export type CorrectionTable = {
  section: string;
  code: string;
  libelle: string;
  colonnes: { orientation: string; position: string; epaisseur_cm: number }[];
  lignes: { menuiserie: Menuiserie; vantaux: number; valeurs: number[]; page: number }[];
  page: number;
};

export type Door = { id: string; nature: string; type: string; ud: number; page: number; statut: Statut };
export type Closure = { id: string; libelle: string; r: number; page: number; statut: Statut };
export type ClosureTable = { r: number[]; lignes: { uw: number; valeurs: number[]; page: number }[] };

export type LibraryEdition = {
  regles: string;
  edition: string;
  extrait_le: string;
  sources: Record<string, { document: string; sha256: string; pages: number }>;
  regles_usage: Record<string, string>;
  protections: ProtectionCase[];
  fenetres: WindowRow[];
  correctifs: CorrectionTable[];
  portes: Door[];
  fermetures: Closure[];
  ujn: ClosureTable;
  uws: ClosureTable;
  controles: { methode: string; erreurs: string[]; alertes: string[]; comptes: Record<string, number> };
};

export type ClosureResult = { uw: number; r: number; ujn: number; uws: number | null; remarque: string | null };

async function getJson<T>(token: string, path: string): Promise<T> {
  const response = await fetch(thermiqueApi.apiUrl(path), { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) {
    let message = `Erreur ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        message = body.detail;
      }
    } catch {
      // réponse sans JSON
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export const libraryApi = {
  windows: (token: string) => getJson<LibraryEdition>(token, "/thermique/bibliotheque/menuiseries"),
  closure: (token: string, uw: number, r: number) =>
    getJson<ClosureResult>(token, `/thermique/bibliotheque/menuiseries/fermeture?uw=${uw}&r=${r}`),
};

export const VITRAGE_LABELS: Record<Vitrage, string> = {
  triple: "Triple",
  double: "Double",
  double_controle_solaire: "Double à contrôle solaire",
};

export const ORIENTATION_LABELS: Record<string, string> = { sud: "Sud", nord: "Nord", est_ouest: "Est / Ouest" };
export const POSITION_LABELS: Record<string, string> = { nu_interieur: "Nu intérieur", nu_exterieur: "Nu extérieur" };

export const SOURCE_LABELS: Record<string, string> = {
  fenetres: "Fenêtres et portes-fenêtres",
  portes: "Portes",
  ujn: "Ujour-nuit",
  uws: "Uws",
  fermetures: "Fermetures",
};

export function menuiserieLabel(menuiserie: Menuiserie, vantaux: number): string {
  return `${menuiserie === "porte_fenetre" ? "Porte-fenêtre" : "Fenêtre"} ${vantaux === 2 ? "2 vantaux" : "1 vantail"}`;
}
