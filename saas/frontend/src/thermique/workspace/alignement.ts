import type { PdfPoint } from "../api";
import { appliquer, inverser, type Similitude } from "./superposition";

/**
 * Calage d'un niveau « comme la commande ALIGNER d'AutoCAD » (D201).
 *
 * Trois temps, le calque bougeant après chacun : un point de base (déplacement seul), une rotation autour de
 * ce point (l'échelle déclarée fait foi), puis, sur demande, l'ajustement de la longueur. La similitude
 * `sim` envoie les points PDF du voisin sur ceux du plan actif, comme dans `superposition.ts`.
 */
export type EtapeAlignement = "base" | "rotation" | "verification" | "enregistre";

export type Alignement = {
  sens: "inferieur" | "superieur";
  etape: EtapeAlignement;
  sim: Similitude;
  // La pose au début, et celle après le point de base : « Refaire l'étape » y revient.
  depart: Similitude;
  apresBase: Similitude | null;
  // [point du voisin, point du plan actif].
  base: [PdfPoint, PdfPoint] | null;
  second: [PdfPoint, PdfPoint] | null;
  // Point du voisin cliqué, en attente de son jumeau sur le plan actif.
  enAttente: PdfPoint | null;
  aimante: boolean;
  longueurAjustee: boolean;
  message: string | null;
  busy: boolean;
};

// Même garde que le serveur : deux points trop proches ne fixent pas une direction.
export const ECART_MIN_PT = 20;
// Aimant des angles droits (Q49) : les plans d'un même bâtiment sont presque toujours dans le même sens.
export const AIMANT_DEG = 1;

const distance = (p: PdfPoint, q: PdfPoint) => Math.hypot(q[0] - p[0], q[1] - p[1]);

export function debuterAlignement(sens: "inferieur" | "superieur", sim: Similitude): Alignement {
  return {
    sens,
    etape: "base",
    sim,
    depart: sim,
    apresBase: null,
    base: null,
    second: null,
    enAttente: null,
    aimante: false,
    longueurAjustee: false,
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

/** De combien le second point tombe trop court (négatif) ou trop loin (positif), en % de sa distance. */
export function ecartLongueurPct(al: Alignement): number | null {
  if (!al.base || !al.second) return null;
  const voulu = distance(al.base[1], al.second[1]);
  const obtenu = distance(al.base[1], appliquer(al.sim, al.second[0]));
  return obtenu > 0 ? (voulu / obtenu - 1) * 100 : null;
}

/** Étape 3 (Q50) : étire le calque depuis le point de base, sans toucher à la rotation. */
export function ajusterLongueur(al: Alignement): Alignement {
  const ecart = ecartLongueurPct(al);
  if (ecart == null || !al.base) return al;
  const k = 1 + ecart / 100;
  const sim = deplacer({ ...al.sim, a: al.sim.a * k, b: al.sim.b * k }, al.base[0], al.base[1]);
  return { ...al, sim, longueurAjustee: true };
}

/** Un clic sur le plan pendant le calage. `echelle` : rapport des échelles déclarées du voisin et du plan. */
export function cliquer(al: Alignement, point: PdfPoint, echelle: number, libre = false): Alignement {
  if (al.busy || (al.etape !== "base" && al.etape !== "rotation")) return al;
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
  const second: [PdfPoint, PdfPoint] = [al.enAttente, point];
  const { sim, aimante } = tourner(base, second, echelle, libre);
  return { ...al, etape: "verification", sim, second, enAttente: null, aimante, longueurAjustee: false };
}

/** Revient au début de l'étape en cours, ou à l'étape d'avant si elle n'est pas commencée. */
export function refaireEtape(al: Alignement): Alignement {
  if (al.etape === "verification" && al.apresBase) {
    return { ...al, etape: "rotation", sim: al.apresBase, second: null, enAttente: null, aimante: false, longueurAjustee: false, message: null };
  }
  if (al.etape === "rotation" && !al.enAttente) return debuterAlignement(al.sens, al.depart);
  return { ...al, enAttente: null, message: null };
}

/** Deux paires qui décrivent exactement la pose affichée : le serveur en retrouve la même similitude. */
export function pairesAEnregistrer(al: Alignement): [PdfPoint, PdfPoint][] | null {
  if (!al.base || !al.second) return null;
  return [
    [al.base[0], appliquer(al.sim, al.base[0])],
    [al.second[0], appliquer(al.sim, al.second[0])],
  ];
}
