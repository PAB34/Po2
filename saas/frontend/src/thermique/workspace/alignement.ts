import type { PdfPoint } from "../api";
import { appliquer, inverser, type Similitude } from "./superposition";

/**
 * Calage d'un niveau « comme la commande ALIGNER d'AutoCAD » (D201, D202).
 *
 * Trois temps, le calque bougeant après chacun : un point de base (déplacement seul), une rotation autour de
 * ce point (à l'échelle déclarée), puis la longueur : un point du calque et l'endroit où il doit tomber
 * étirent le calque depuis le point de base. La similitude `sim` envoie les points PDF du voisin sur ceux du
 * plan actif, comme dans `superposition.ts`.
 */
export type EtapeAlignement = "base" | "rotation" | "longueur" | "enregistre";

export type Alignement = {
  sens: "inferieur" | "superieur";
  etape: EtapeAlignement;
  sim: Similitude;
  // Les poses au début de chaque étape : « Refaire l'étape » y revient.
  depart: Similitude;
  apresBase: Similitude | null;
  apresRotation: Similitude | null;
  // [point du voisin, point du plan actif].
  base: [PdfPoint, PdfPoint] | null;
  second: [PdfPoint, PdfPoint] | null;
  longueur: [PdfPoint, PdfPoint] | null;
  // Point du voisin cliqué, en attente de son jumeau sur le plan actif.
  enAttente: PdfPoint | null;
  aimante: boolean;
  message: string | null;
  busy: boolean;
};

// Même garde que le serveur : deux points trop proches ne fixent ni une direction ni une longueur.
export const ECART_MIN_PT = 20;
// Aimant des angles droits (Q49) : les plans d'un même bâtiment sont presque toujours dans le même sens.
export const AIMANT_DEG = 1;

const distance = (p: PdfPoint, q: PdfPoint) => Math.hypot(q[0] - p[0], q[1] - p[1]);
const norme = (sim: Similitude) => Math.hypot(sim.a, sim.b);

export function debuterAlignement(sens: "inferieur" | "superieur", sim: Similitude): Alignement {
  return {
    sens,
    etape: "base",
    sim,
    depart: sim,
    apresBase: null,
    apresRotation: null,
    base: null,
    second: null,
    longueur: null,
    enAttente: null,
    aimante: false,
    message: null,
    busy: false,
  };
}

/** Rotation de la similitude, en degrés. */
export function angleDeg(sim: Similitude): number {
  return (Math.atan2(sim.b, sim.a) * 180) / Math.PI;
}

/** Déplacement seul : même rotation, même échelle, et `surVoisin` tombe sur `surPlan`. */
export function deplacer(sim: Similitude, surVoisin: PdfPoint, surPlan: PdfPoint): Similitude {
  const [x, y] = appliquer({ ...sim, tx: 0, ty: 0 }, surVoisin);
  return { a: sim.a, b: sim.b, tx: surPlan[0] - x, ty: surPlan[1] - y };
}

/** Change l'échelle de `sim` sans bouger le point de base ni la rotation. */
function aLEchelle(sim: Similitude, echelle: number, base: [PdfPoint, PdfPoint]): Similitude {
  const k = echelle / norme(sim);
  return deplacer({ ...sim, a: sim.a * k, b: sim.b * k }, base[0], base[1]);
}

/**
 * Rotation autour du point de base : le second point du voisin part dans la direction cliquée sur le plan,
 * à l'échelle `echelle` (rapport des échelles déclarées). Aimantée aux angles droits sauf `libre`.
 */
export function tourner(
  base: [PdfPoint, PdfPoint],
  second: [PdfPoint, PdfPoint],
  echelle: number,
  libre = false,
): { sim: Similitude; aimante: boolean } {
  const [v1, a1] = base;
  const [v2, a2] = second;
  const brut = Math.atan2(a2[1] - a1[1], a2[0] - a1[0]) - Math.atan2(v2[1] - v1[1], v2[0] - v1[0]);
  const droit = (Math.round(brut / (Math.PI / 2)) * Math.PI) / 2;
  const aimante = !libre && Math.abs(brut - droit) <= (AIMANT_DEG * Math.PI) / 180;
  const theta = aimante ? droit : brut;
  const sim = { a: echelle * Math.cos(theta), b: echelle * Math.sin(theta), tx: 0, ty: 0 };
  return { sim: deplacer(sim, v1, a1), aimante };
}

/**
 * Étape 3 : étire le calque depuis le point de base pour que `surVoisin` tombe sur `surPlan`, sans toucher à
 * la rotation. Le facteur est pris le long de la direction du point : un clic un peu de côté ne compte pas.
 */
export function etirer(sim: Similitude, base: [PdfPoint, PdfPoint], surVoisin: PdfPoint, surPlan: PdfPoint): Similitude {
  const [, a1] = base;
  const [ox, oy] = appliquer(sim, surVoisin);
  const u = [ox - a1[0], oy - a1[1]];
  const w = [surPlan[0] - a1[0], surPlan[1] - a1[1]];
  const k = (u[0] * w[0] + u[1] * w[1]) / (u[0] * u[0] + u[1] * u[1]);
  return aLEchelle(sim, norme(sim) * k, base);
}

/** Écart de l'échelle trouvée sur l'échelle déclarée, en % (positif : le calque a été agrandi). */
export function ecartEchellePct(al: Alignement, echelle: number): number {
  return (norme(al.sim) / echelle - 1) * 100;
}

/** Un clic sur le plan pendant le calage. `echelle` : rapport des échelles déclarées du voisin et du plan. */
export function cliquer(al: Alignement, point: PdfPoint, echelle: number, libre = false): Alignement {
  if (al.busy || al.etape === "enregistre") return al;
  if (!al.enAttente) {
    return { ...al, enAttente: appliquer(inverser(al.sim), point), message: null };
  }
  if (al.etape === "base") {
    const sim = deplacer(al.sim, al.enAttente, point);
    return { ...al, etape: "rotation", sim, apresBase: sim, base: [al.enAttente, point], enAttente: null };
  }
  const base = al.base!;
  if (distance(base[1], point) < ECART_MIN_PT || distance(base[1], appliquer(al.sim, al.enAttente)) < ECART_MIN_PT) {
    return {
      ...al,
      enAttente: null,
      message: "Ce point est trop près du point de base : prenez-en un à l'autre bout du bâtiment.",
    };
  }
  if (al.etape === "rotation") {
    const second: [PdfPoint, PdfPoint] = [al.enAttente, point];
    const { sim, aimante } = tourner(base, second, echelle, libre);
    return { ...al, etape: "longueur", sim, apresRotation: sim, second, enAttente: null, aimante };
  }
  const longueur: [PdfPoint, PdfPoint] = [al.enAttente, point];
  return { ...al, sim: etirer(al.apresRotation ?? al.sim, base, longueur[0], longueur[1]), longueur, enAttente: null };
}

/** « La rotation est déjà bonne » : on la garde telle quelle, à l'échelle déclarée, et on passe à la longueur. */
export function garderLaRotation(al: Alignement, echelle: number): Alignement {
  if (al.etape !== "rotation" || !al.base) return al;
  const sim = aLEchelle(al.sim, echelle, al.base);
  return { ...al, etape: "longueur", sim, apresRotation: sim, second: null, enAttente: null, aimante: false, message: null };
}

/** Revient au début de l'étape en cours, ou à l'étape d'avant si elle n'est pas commencée. */
export function refaireEtape(al: Alignement): Alignement {
  const propre = { enAttente: null, message: null };
  if (al.etape === "longueur" && (al.longueur || al.enAttente) && al.apresRotation) {
    return { ...al, ...propre, sim: al.apresRotation, longueur: null };
  }
  if (al.etape === "longueur" && al.apresBase) {
    return { ...al, ...propre, etape: "rotation", sim: al.apresBase, apresRotation: null, second: null, aimante: false };
  }
  if (al.etape === "rotation" && !al.enAttente) return debuterAlignement(al.sens, al.depart);
  return { ...al, ...propre };
}

/** Deux paires qui décrivent exactement la pose affichée : le serveur en retrouve la même similitude. */
export function pairesAEnregistrer(al: Alignement): [PdfPoint, PdfPoint][] | null {
  if (!al.base) return null;
  const v1 = al.base[0];
  // Un second point du voisin assez loin du premier, même si la rotation a été gardée sans clic.
  const loin = al.longueur?.[0] ?? al.second?.[0] ?? null;
  const v2: PdfPoint = loin && distance(v1, loin) >= ECART_MIN_PT ? loin : [v1[0] + 500, v1[1]];
  return [
    [v1, appliquer(al.sim, v1)],
    [v2, appliquer(al.sim, v2)],
  ];
}
