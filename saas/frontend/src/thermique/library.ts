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

// --- Matériaux et parois opaques (lot B2a) -------------------------------------------------

export type Material = {
  id: string;
  section: string;
  section_titre: string;
  famille: string | null;
  libelle: string;
  rho_texte: string;
  rho_min: number | null;
  rho_max: number | null;
  lambda: number;
  cp_texte: string;
  mu_sec: string;
  mu_humide: string;
  page: number;
  statut: Statut;
  note_document?: string;
  // Texte de la note de bas de tableau à laquelle renvoie l'appel de note.
  note_texte?: string;
};

export type MaterialsEdition = {
  regles: string;
  edition: string;
  extrait_le: string;
  sources: Record<string, { document: string; sha256: string; pages: number }>;
  regles_usage: Record<string, string>;
  familles: { section: string; titre: string }[];
  materiaux: Material[];
  renvois: { section: string; texte: string; page: number }[];
  verification_constantes: { ok: boolean; controles: number; manquants: string[]; document: string };
  controles: { methode: string; erreurs: string[]; alertes: string[]; comptes: Record<string, number> };
};

export type WallType = "mur" | "plancher_haut" | "plancher_bas";
export type WallFacing = "exterieur" | "local_non_chauffe";
export type WallLayerRequest =
  | { type: "materiau"; materiau_id: string; epaisseur_m: number; isolant?: boolean; libelle?: string }
  | { type: "lambda"; lambda: number; epaisseur_m: number; isolant?: boolean; libelle?: string }
  | { type: "resistance"; r: number; libelle?: string }
  | { type: "lame_air"; epaisseur_mm: number }
  | { type: "lame_air_ventilee" };

export type WallRequest = {
  type: WallType;
  donne_sur: WallFacing;
  niveau_delta_u2: number;
  delta_u1: number;
  couches: WallLayerRequest[];
};

export type WallResult = {
  libelle_type: string;
  couches: {
    index: number;
    type: string;
    libelle: string;
    epaisseur_m?: number;
    epaisseur_mm?: number;
    lambda?: number;
    r: number;
    ignoree?: boolean;
    source?: string;
  }[];
  rsi: number;
  rse: number;
  r_couches: number;
  rt: number;
  uc: number;
  delta_u1: number;
  delta_u2: number;
  up: number;
  up_arrondi: number;
  remarques: string[];
  source: string;
};

export type ThicknessResult = {
  u_cible: number;
  epaisseur_min_m: number;
  epaisseur_arrondie_m: number;
  up_obtenu: number;
  up_obtenu_arrondi: number;
};

async function postJson<T>(token: string, path: string, body: unknown): Promise<T> {
  const response = await fetch(thermiqueApi.apiUrl(path), {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let message = `Erreur ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") {
        message = payload.detail;
      }
    } catch {
      // réponse sans JSON
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

export const wallApi = {
  materials: (token: string) => getJson<MaterialsEdition>(token, "/thermique/bibliotheque/materiaux"),
  compute: (token: string, wall: WallRequest) => postJson<WallResult>(token, "/thermique/bibliotheque/parois/calcul", wall),
  thickness: (token: string, wall: WallRequest, index: number, target: number) =>
    postJson<ThicknessResult>(token, "/thermique/bibliotheque/parois/epaisseur-isolant", {
      paroi: wall,
      index_isolant: index,
      u_cible: target,
    }),
};

export const WALL_TYPE_LABELS: Record<WallType, string> = {
  mur: "Mur (flux horizontal)",
  plancher_haut: "Toiture ou plancher haut (flux ascendant)",
  plancher_bas: "Plancher bas sur extérieur ou local non chauffé (flux descendant)",
};

export const DELTA_U2_LABELS: Record<number, string> = {
  1: "Niveau 1 : aucune cavité ni lame d'air parasite (0)",
  2: "Niveau 2 : cavités traversant l'isolant (0,01)",
  3: "Niveau 3 : cavités reliées à une lame d'air côté chaud (0,04)",
};

export function materialLabel(material: Material): string {
  const density = material.rho_texte ? ` — ${material.rho_texte} kg/m³` : "";
  const title = material.libelle === material.section_titre ? material.libelle : `${material.section_titre} : ${material.libelle}`;
  return `${title}${density}`;
}

export function normalizeSearch(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}
