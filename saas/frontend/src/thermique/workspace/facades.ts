import type { PdfPoint, SheetNorth, StudyContent, VueCoupe } from "../api";
import { repereFeuille } from "./pontsAjoutes";
import type { TraitCliquable } from "./TraitsDeCoupe";

/**
 * La façade d'une élévation, repérée sur le plan (S5e, D182, D198).
 *
 * L'élévation dit quelle façade elle montre (« FAÇADE EST ») ; le nord du plan dit quel côté regarde vers l'est.
 * Les tronçons de l'enveloppe portent leur normale extérieure : ceux qui regardent dans la direction de la
 * façade, à 45° près, sont la façade. Tout se calcule à l'écran, sans agent ni serveur.
 */

const ORIENTATIONS: [RegExp, number][] = [
  [/nord[\s-]*est/, 45],
  [/nord[\s-]*ouest/, 315],
  [/sud[\s-]*est/, 135],
  [/sud[\s-]*ouest/, 225],
  [/\bnord\b/, 0],
  [/\best\b/, 90],
  [/\bsud\b/, 180],
  [/\bouest\b/, 270],
];
const TOLERANCE_DEG = 45;

/** Azimut (degrés, sens horaire depuis le nord) écrit dans le nom d'une élévation, ou `null`. */
export function azimutDuNom(nom: string): number | null {
  const texte = nom
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
  for (const [motif, azimut] of ORIENTATIONS) {
    if (motif.test(texte)) return azimut;
  }
  return null;
}

/** Direction d'un azimut dans le repère PDF (y vers le haut), à partir de la flèche du nord du plan. */
export function directionPdf(nord: SheetNorth, azimut: number): [number, number] {
  const nx0 = nord.p2[0] - nord.p1[0];
  const ny0 = nord.p2[1] - nord.p1[1];
  const norme = Math.hypot(nx0, ny0) || 1;
  const [nx, ny] = [nx0 / norme, ny0 / norme];
  const t = (azimut * Math.PI) / 180;
  // Rotation dans le sens horaire, y vers le haut.
  return [nx * Math.cos(t) + ny * Math.sin(t), -nx * Math.sin(t) + ny * Math.cos(t)];
}

type Troncon = {
  id: string;
  origine_px: [number, number];
  direction: [number, number];
  normale_ext: [number, number];
  local_debut_m: number;
  local_fin_m?: number;
  debut_m: number;
  fin_m: number;
};

/** Les traits de chaque façade lue, le long des tronçons de l'enveloppe qui regardent dans sa direction. */
export function traitsDeFacade(
  content: StudyContent | null | undefined,
  nord: SheetNorth | null | undefined,
  vues: VueCoupe[],
): TraitCliquable[] {
  const manifeste = (content?.enveloppe as unknown as {
    manifeste?: { page_px: [number, number]; px_par_m: number; troncons: Troncon[] };
  } | undefined)?.manifeste;
  if (!content || !nord || !manifeste?.troncons?.length) return [];
  const repere = repereFeuille(content);
  if (!repere) return [];
  // Feuille (0..1000) → PDF : inverse de la correspondance affine PDF → feuille.
  const det = repere.a * repere.d - repere.b * repere.c;
  if (Math.abs(det) < 1e-12) return [];
  const [largeur, hauteur] = manifeste.page_px;
  const versPdf = ([px, py]: [number, number]): PdfPoint => {
    const X = (px * 1000) / largeur - repere.e;
    const Y = (py * 1000) / hauteur - repere.f;
    return [(repere.d * X - repere.c * Y) / det, (-repere.b * X + repere.a * Y) / det];
  };
  const vecteurPdf = ([vx, vy]: [number, number]): [number, number] => {
    const X = (vx * 1000) / largeur;
    const Y = (vy * 1000) / hauteur;
    const v: [number, number] = [(repere.d * X - repere.c * Y) / det, (-repere.b * X + repere.a * Y) / det];
    const norme = Math.hypot(v[0], v[1]) || 1;
    return [v[0] / norme, v[1] / norme];
  };
  const cosTolerance = Math.cos((TOLERANCE_DEG * Math.PI) / 180);
  const traits: TraitCliquable[] = [];
  for (const vue of vues) {
    if (vue.nature !== "facade") continue;
    const azimut = azimutDuNom(vue.nom);
    if (azimut === null) continue;
    const dehors = directionPdf(nord, azimut);
    let premier = true;
    for (const troncon of manifeste.troncons) {
      if (!troncon.normale_ext) continue;
      const normale = vecteurPdf(troncon.normale_ext);
      if (normale[0] * dehors[0] + normale[1] * dehors[1] < cosTolerance) continue;
      const fin = troncon.local_fin_m ?? troncon.local_debut_m + troncon.fin_m - troncon.debut_m;
      const point = (local: number): PdfPoint =>
        versPdf([
          troncon.origine_px[0] + troncon.direction[0] * local * manifeste.px_par_m,
          troncon.origine_px[1] + troncon.direction[1] * local * manifeste.px_par_m,
        ]);
      traits.push({
        nom: vue.nom,
        points: [point(troncon.local_debut_m), point(fin)],
        // On regarde la façade depuis l'extérieur : le regard va vers l'intérieur.
        sens: [-dehors[0], -dehors[1]],
        deduit: false,
        vueId: vue.id,
        facade: true,
        etiquette: premier,
      });
      premier = false;
    }
  }
  return traits;
}
