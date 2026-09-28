import type { PdfPoint, StudyRoom, StudySide } from "../api";
import { pointInPolygon } from "./edition";
import { distanceAuSegment } from "./elements";

/**
 * Le côté désigné, partagé entre la fiche et le plan (sujet 2, D145).
 *
 * Le rang seul ne suffit pas : après un recalcul, le côté de même rang peut être un autre côté. L'empreinte
 * le vérifie ; si elle ne correspond plus, rien n'est surligné plutôt qu'un voisin. `clic` change à chaque
 * désignation depuis la fiche, pour que le plan revienne au côté même quand on l'a déplacé entre-temps ;
 * il vaut `null` quand le côté a été désigné sur le plan, qui n'a alors pas à bouger.
 */
export type CoteVisee = { localId: string; rang: number; empreinte: string; clic: number | null };

export function empreinteCote(cote: StudySide): string {
  const premier = cote.trace_pdf?.[0];
  return `${cote.longueur_m}|${premier ? `${premier[0]},${premier[1]}` : "-"}`;
}

/** Le rang du côté désigné dans ce local, s'il y est toujours le même côté. */
export function rangVise(room: StudyRoom | null, visee: CoteVisee | null): number | null {
  if (!room || !visee || visee.localId !== room.id) {
    return null;
  }
  const cote = room.fiche.cotes[visee.rang];
  return cote && empreinteCote(cote) === visee.empreinte ? visee.rang : null;
}

export const aUnTrace = (cote: StudySide) => (cote.trace_pdf?.length ?? 0) >= 2;

/**
 * Le côté du local sous le curseur (D149).
 *
 * Sur le R+1, le tracé d'un côté est posé sur le contour (écart maximal 0,89 pt) et le mur qui le porte
 * est au-delà, hors du local. On n'attrape donc un côté que **de l'intérieur** : le mur reste attrapable
 * de l'autre côté du trait.
 */
export function coteAt(room: StudyRoom, point: PdfPoint, tolerance: number): number | null {
  if (!pointInPolygon(room.contour_pdf, point[0], point[1])) {
    return null;
  }
  let meilleur: { rang: number; ecart: number } | null = null;
  for (let rang = 0; rang < room.fiche.cotes.length; rang += 1) {
    const trace = room.fiche.cotes[rang].trace_pdf ?? [];
    for (let segment = 1; segment < trace.length; segment += 1) {
      const ecart = distanceAuSegment(point, trace[segment - 1], trace[segment]);
      if (ecart <= tolerance && (!meilleur || ecart < meilleur.ecart)) {
        meilleur = { rang, ecart };
      }
    }
  }
  return meilleur?.rang ?? null;
}

/** Le milieu du tracé, mesuré le long de la polyligne : c'est là que le plan se centre (D148). */
export function milieuCote(cote: StudySide): PdfPoint | null {
  const trace = cote.trace_pdf ?? [];
  if (trace.length < 2) {
    return null;
  }
  const longueurs = trace.slice(1).map((point, rang) => Math.hypot(point[0] - trace[rang][0], point[1] - trace[rang][1]));
  let reste = longueurs.reduce((total, longueur) => total + longueur, 0) / 2;
  for (let rang = 0; rang < longueurs.length; rang += 1) {
    if (longueurs[rang] > 0 && reste <= longueurs[rang]) {
      const part = reste / longueurs[rang];
      const [x1, y1] = trace[rang];
      const [x2, y2] = trace[rang + 1];
      return [x1 + (x2 - x1) * part, y1 + (y2 - y1) * part];
    }
    reste -= longueurs[rang];
  }
  return trace[trace.length - 1];
}
