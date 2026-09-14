// Métré sur les plans, lot M1 : niveaux, calage, contours (docs/thermique/metre-plans-decisions.md).
import { request, type PdfPoint } from "./api";

export type DonneSur = "exterieur" | "lnc" | "sol" | "mitoyen";
export type ZoneType = "contour" | "lnc" | "patio" | "nu_exterieur";

// Seuls le contour (nu intérieur) et le patio ont des côtés qualifiés (donne sur, composant, mur lu).
export const hasEdges = (type: ZoneType) => type === "contour" || type === "patio";

export type WallInsulation = "interieur" | "exterieur" | "reparti";

// Mur lu sur le plan pour un côté (lot M4a).
export type EdgeWall = { epaisseur_m: number | null; isolant: WallInsulation | null; part_lue: number };

export type ZoneEdge = { donne_sur: DonneSur; composant_id: number | null; mur?: EdgeWall | null };

// Côtés regroupés par épaisseur lue (± 3 cm), proposés comme composant mur.
export type WallType = { epaisseur_m: number; isolant: WallInsulation | null; longueur_m: number; cotes: number[]; composants: number[] };

export type MetreZone = {
  id: number;
  niveau_id: number;
  type: ZoneType;
  nom: string;
  type_lnc: string | null;
  points: PdfPoint[];
  // Côté i = du sommet i au suivant. Vide pour un local non chauffé.
  cotes: ZoneEdge[];
  source: string;
  types_murs?: WallType[];
};

export type ZoneSummary = {
  id: number;
  aire_m2: number | null;
  perimetre_m: number | null;
  cotes_m: number[] | null;
  incluse_dans_contour: boolean | null;
  alertes: string[];
};

export type LevelSummary = {
  zones: ZoneSummary[];
  surface_contour_m2: number | null;
  surface_lnc_m2: number | null;
  surface_patio_m2: number | null;
  surface_nu_exterieur_m2?: number | null;
  surface_chauffee_m2: number | null;
  lineaires_m: Record<DonneSur, number> | null;
  hauteur_interieure_m: number | null;
  surfaces_murs_m2: Record<DonneSur, number> | null;
  alertes: string[];
};

export type Calage = { a: PdfPoint; b: PdfPoint };

export type MetreLevel = {
  id: number;
  nom: string;
  ordre: number;
  altitude_m: number | null;
  hauteur_etage_m: number | null;
  epaisseur_plancher_m: number | null;
  hauteur_sous_plafond_m: number | null;
  hauteurs_source: "manuel" | "coupe" | null;
  planche_id: number | null;
  planche_libelle: string | null;
  echelle: number | null;
  calage: Calage | null;
  calage_ab_m: number | null;
  calage_ecart_m: number | null;
  zones: MetreZone[];
  synthese: LevelSummary;
};

export type Metre = {
  niveaux: MetreLevel[];
  nord_deg: number | null;
  alertes: string[];
  listes: { donne_sur: Record<DonneSur, string>; types_zone: Record<ZoneType, string>; types_lnc: Record<string, string> };
  // Présent après une détection automatique du contour.
  detection?: { aire_m2: number; perimetre_m: number; sommets: number; zones_exterieures_ecartees: number };
  // Présent après une lecture des murs.
  detection_murs?: { cotes_lues: number; cotes: number; types: number };
  // Présent après la détection du nu intérieur et du nu extérieur (lot G1).
  detection_lignes?: {
    nu_interieur_m2: number;
    nu_exterieur_m2: number;
    sommets_interieur: number;
    sommets_exterieur: number;
    epaisseur_typique_m: number | null;
  };
};

// Hauteurs d'un niveau lues entre deux planchers d'une coupe.
export type SectionInterval = { epaisseur_plancher_m: number; hauteur_etage_m: number; hauteur_sous_plafond_m: number };

export type SectionDetection = {
  axe: "horizontal" | "vertical" | null;
  dessins: {
    index: number;
    planchers: { position_m: number; epaisseur_m: number; portee_m: number }[];
    hauteurs_etage_m: number[];
    niveaux_montant: SectionInterval[];
    niveaux_descendant: SectionInterval[];
  }[];
};

export type SnapTraits = {
  classes: { largeur: number; nombre: number; longueur_pt: number }[];
  seuil_propose: number | null;
  seuil: number | null;
  // [x1, y1, x2, y2] en points PDF
  segments: number[][];
  tronque: boolean;
  nombre_total: number;
};

// Murs coupés lus sur les vecteurs du plan : polygones en points PDF, types par épaisseur.
export type DetectedWall = { points: PdfPoint[]; epaisseur_m: number; longueur_m: number; rempli: boolean; courbe?: boolean };

export type SheetWalls = {
  echelle: number;
  murs: DetectedWall[];
  types: { epaisseur_m: number; longueur_m: number; nombre: number }[];
  parois_composees: { epaisseur_m: number; couches_m: number[]; longueur_m: number }[];
  lineaire_m: number;
};

export type LevelPayload = Partial<{
  nom: string;
  ordre: number;
  altitude_m: number | null;
  hauteur_etage_m: number | null;
  epaisseur_plancher_m: number | null;
  hauteur_sous_plafond_m: number | null;
  planche_id: number | null;
  calage: Calage | null;
}>;

export type ZonePayload = Partial<{ nom: string; type_lnc: string; points: PdfPoint[]; cotes: ZoneEdge[] }>;

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });

export const metreApi = {
  get: (token: string, projectId: number) => request<Metre>(token, `/thermique/projects/${projectId}/metre`),
  createLevel: (token: string, projectId: number, payload: LevelPayload) =>
    request<Metre>(token, `/thermique/projects/${projectId}/niveaux`, json("POST", payload)),
  levelsFromSheets: (token: string, projectId: number) =>
    request<Metre>(token, `/thermique/projects/${projectId}/niveaux/depuis-planches`, { method: "POST" }),
  updateLevel: (token: string, levelId: number, payload: LevelPayload) =>
    request<Metre>(token, `/thermique/niveaux/${levelId}`, json("PATCH", payload)),
  deleteLevel: (token: string, levelId: number) => request<Metre>(token, `/thermique/niveaux/${levelId}`, { method: "DELETE" }),
  setNorth: (token: string, projectId: number, payload: { niveau_id: number; p1: PdfPoint; p2: PdfPoint }) =>
    request<Metre>(token, `/thermique/projects/${projectId}/nord`, json("POST", payload)),
  createZone: (token: string, levelId: number, payload: ZonePayload & { type: ZoneType }) =>
    request<Metre>(token, `/thermique/niveaux/${levelId}/zones`, json("POST", payload)),
  updateZone: (token: string, zoneId: number, payload: ZonePayload) =>
    request<Metre>(token, `/thermique/zones/${zoneId}`, json("PATCH", payload)),
  deleteZone: (token: string, zoneId: number) => request<Metre>(token, `/thermique/zones/${zoneId}`, { method: "DELETE" }),
  traits: (token: string, sheetId: number, seuil: number | null) =>
    request<SnapTraits>(token, `/thermique/sheets/${sheetId}/traits${seuil === null ? "" : `?seuil=${seuil}`}`),
  detectContour: (token: string, levelId: number, remplacer: boolean) =>
    request<Metre>(token, `/thermique/niveaux/${levelId}/detecter-contour`, json("POST", { remplacer })),
  detectLines: (token: string, levelId: number, remplacer: boolean) =>
    request<Metre>(token, `/thermique/niveaux/${levelId}/detecter-lignes`, json("POST", { remplacer })),
  section: (token: string, sheetId: number) => request<SectionDetection>(token, `/thermique/sheets/${sheetId}/coupe`),
  walls: (token: string, sheetId: number) => request<SheetWalls>(token, `/thermique/sheets/${sheetId}/murs`),
  detectWalls: (token: string, zoneId: number) => request<Metre>(token, `/thermique/zones/${zoneId}/detecter-murs`, { method: "POST" }),
  acceptWallType: (token: string, zoneId: number, payload: { epaisseur_m: number; composant_id: number | null }) =>
    request<Metre>(token, `/thermique/zones/${zoneId}/types-murs`, json("POST", payload)),
  applySectionHeights: (
    token: string,
    projectId: number,
    payload: { planche_id: number; dessin: number; sens_montant: boolean; premier_intervalle: number },
  ) => request<Metre>(token, `/thermique/projects/${projectId}/hauteurs-coupe`, json("POST", payload)),
};

// --- Repère commun des niveaux ----------------------------------------------------------------
// Même convention que le moteur : origine au point A, axe x de A vers B, en mètres.

export const PT_TO_M = 25.4 / 72 / 1000;

export type Repere = { ox: number; oy: number; cos: number; sin: number; k: number };

export function repereOf(level: Pick<MetreLevel, "calage" | "echelle">): Repere | null {
  if (!level.calage || !level.echelle) {
    return null;
  }
  const [ax, ay] = level.calage.a;
  const [bx, by] = level.calage.b;
  const angle = Math.atan2(by - ay, bx - ax);
  return { ox: ax, oy: ay, cos: Math.cos(angle), sin: Math.sin(angle), k: PT_TO_M * level.echelle };
}

export function toProject(r: Repere, [x, y]: PdfPoint): [number, number] {
  const dx = x - r.ox;
  const dy = y - r.oy;
  return [(dx * r.cos + dy * r.sin) * r.k, (-dx * r.sin + dy * r.cos) * r.k];
}

export function fromProject(r: Repere, [u, v]: [number, number]): PdfPoint {
  const dx = u / r.k;
  const dy = v / r.k;
  return [r.ox + dx * r.cos - dy * r.sin, r.oy + dx * r.sin + dy * r.cos];
}

// Point d'une planche reporté sur la planche d'un autre niveau (calque des niveaux voisins).
export function transferPoint(from: Repere, to: Repere, point: PdfPoint): PdfPoint {
  return fromProject(to, toProject(from, point));
}

// Direction du nord sur une planche (vecteur unitaire en points PDF).
export function northOnSheet(r: Repere, northDeg: number): [number, number] {
  const u = Math.cos((northDeg * Math.PI) / 180);
  const v = Math.sin((northDeg * Math.PI) / 180);
  return [u * r.cos - v * r.sin, u * r.sin + v * r.cos];
}

// --- Géométrie des tracés -----------------------------------------------------------------------

export function polygonArea(points: PdfPoint[]): number {
  let total = 0;
  points.forEach(([x1, y1], i) => {
    const [x2, y2] = points[(i + 1) % points.length];
    total += x1 * y2 - x2 * y1;
  });
  return Math.abs(total) / 2;
}

export function pointInPolygon([x, y]: PdfPoint, points: PdfPoint[]): boolean {
  let inside = false;
  for (let i = 0, j = points.length - 1; i < points.length; j = i, i += 1) {
    const [xi, yi] = points[i];
    const [xj, yj] = points[j];
    if (yi > y !== yj > y && x < xi + ((y - yi) * (xj - xi)) / (yj - yi)) {
      inside = !inside;
    }
  }
  return inside;
}

export function projectOnSegment(p: PdfPoint, a: PdfPoint, b: PdfPoint): { point: PdfPoint; distance: number } {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const length2 = dx * dx + dy * dy;
  const t = length2 === 0 ? 0 : Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length2));
  const point: PdfPoint = [a[0] + t * dx, a[1] + t * dy];
  return { point, distance: Math.hypot(p[0] - point[0], p[1] - point[1]) };
}

export function nearestVertex(points: PdfPoint[], p: PdfPoint, tolerance: number): number | null {
  let best: number | null = null;
  let bestDistance = tolerance;
  points.forEach((vertex, i) => {
    const distance = Math.hypot(vertex[0] - p[0], vertex[1] - p[1]);
    if (distance <= bestDistance) {
      best = i;
      bestDistance = distance;
    }
  });
  return best;
}

export function nearestEdge(points: PdfPoint[], p: PdfPoint, tolerance: number): { index: number; point: PdfPoint } | null {
  let best: { index: number; point: PdfPoint } | null = null;
  let bestDistance = tolerance;
  points.forEach((a, i) => {
    const projection = projectOnSegment(p, a, points[(i + 1) % points.length]);
    if (projection.distance <= bestDistance) {
      best = { index: i, point: projection.point };
      bestDistance = projection.distance;
    }
  });
  return best;
}

// Ajoute un sommet sur le côté `edge` : les deux moitiés gardent la qualification du côté.
export function insertVertex(points: PdfPoint[], cotes: ZoneEdge[], edge: number, point: PdfPoint) {
  const nextPoints = [...points.slice(0, edge + 1), point, ...points.slice(edge + 1)];
  const nextCotes = cotes.length === points.length ? [...cotes.slice(0, edge + 1), { ...cotes[edge] }, ...cotes.slice(edge + 1)] : cotes;
  return { points: nextPoints, cotes: nextCotes };
}

// Retire un sommet : le côté fusionné garde la qualification du côté qui arrivait au sommet.
export function removeVertex(points: PdfPoint[], cotes: ZoneEdge[], index: number) {
  const nextPoints = points.filter((_, i) => i !== index);
  const nextCotes = cotes.length === points.length ? cotes.filter((_, i) => i !== index) : cotes;
  if (index === 0 && nextCotes.length === nextPoints.length && cotes.length === points.length) {
    nextCotes[nextCotes.length - 1] = { ...cotes[cotes.length - 1] };
  }
  return { points: nextPoints, cotes: nextCotes };
}

// Nombre saisi en français, zéro et négatifs admis (altitude). Vide → null.
export function parseSignedNumber(value: string): number | null {
  const cleaned = value.replace(/\s/g, "").replace(",", ".");
  if (cleaned === "") {
    return null;
  }
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}
