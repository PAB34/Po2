import type {
  PdfPoint,
  StudyContent,
  StudyElementRef,
  StudyEnvelopeShape,
  StudyReleveElement,
  StudyRoom,
} from "../api";
import { pointInPolygon } from "./edition";

/** Types d'élément lus par l'agent, dans l'ordre où ils reviennent le plus souvent sur un niveau. */
export const TYPES_ELEMENT = [
  "menuiserie",
  "paroi",
  "angle_sortant",
  "angle_rentrant",
  "poteau",
  "garde_corps",
  "about_refend",
  "indetermine",
] as const;

export const LIBELLES_TYPE: Record<string, string> = {
  menuiserie: "Menuiserie",
  paroi: "Paroi",
  angle_sortant: "Angle sortant",
  angle_rentrant: "Angle rentrant",
  poteau: "Poteau",
  garde_corps: "Garde-corps",
  about_refend: "About de refend",
  indetermine: "Indéterminé",
};

export function refDeElement(element: StudyReleveElement): StudyElementRef {
  return { troncon: element.troncon, debut_m: element.debut_m, fin_m: element.fin_m };
}

/** Le tracé porte la position de son élément : c'est par là qu'un clic sur le plan remonte au relevé. */
export function refDeForme(shape: StudyEnvelopeShape): StudyElementRef | null {
  const source = shape.source_parcours;
  if (!source?.troncon || source.debut_m == null || source.fin_m == null) {
    return null;
  }
  return { troncon: source.troncon, debut_m: source.debut_m, fin_m: source.fin_m };
}

export function memeElement(a: StudyElementRef | null, b: StudyElementRef | null): boolean {
  return Boolean(a && b && a.troncon === b.troncon && a.debut_m === b.debut_m && a.fin_m === b.fin_m);
}

export function trouverElement(content: StudyContent, ref: StudyElementRef | null): StudyReleveElement | null {
  if (!ref) {
    return null;
  }
  return (
    content.enveloppe.releve_brut.elements.find((element) => memeElement(refDeElement(element), ref)) ?? null
  );
}

/** Éléments relevés qui touchent un local, dans l'ordre du parcours de l'enveloppe. */
export function elementsDuLocal(content: StudyContent, room: StudyRoom | null): StudyReleveElement[] {
  if (!room) {
    return [];
  }
  const vises = new Set<string>();
  for (const shape of content.enveloppe.objets ?? []) {
    if (shape.source_parcours?.piece !== room.nom) {
      continue;
    }
    const ref = refDeForme(shape);
    if (ref) {
      vises.add(`${ref.troncon}|${ref.debut_m}|${ref.fin_m}`);
    }
  }
  return content.enveloppe.releve_brut.elements.filter((element) =>
    vises.has(`${element.troncon}|${element.debut_m}|${element.fin_m}`),
  );
}

function distanceAuSegment(point: PdfPoint, a: PdfPoint, b: PdfPoint): number {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const longueur = dx * dx + dy * dy;
  if (longueur === 0) {
    return Math.hypot(point[0] - a[0], point[1] - a[1]);
  }
  const brut = ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / longueur;
  const ratio = Math.min(1, Math.max(0, brut));
  return Math.hypot(point[0] - (a[0] + ratio * dx), point[1] - (a[1] + ratio * dy));
}

/**
 * L'élément sous le curseur, parmi les formes d'un local.
 *
 * Le test se fait ici et non par `pointer-events` sur les formes : la couche des métrés doit rester
 * traversante pour que le plan se déplace toujours (D79). Le plus petit l'emporte, pour qu'une
 * menuiserie posée sur un mur reste attrapable.
 */
export function elementAt(
  shapes: StudyEnvelopeShape[],
  point: PdfPoint,
  tolerance: number,
): StudyElementRef | null {
  let meilleur: { ref: StudyElementRef; poids: number } | null = null;
  for (const shape of shapes) {
    const points = shape.points_pdf ?? [];
    if (points.length < 2) {
      continue;
    }
    const ref = refDeForme(shape);
    if (!ref) {
      continue;
    }
    let touche = false;
    if (shape.geometry_type === "polygon" && points.length >= 3) {
      touche = pointInPolygon(points, point[0], point[1]);
    }
    if (!touche) {
      const dernier = shape.geometry_type === "polygon" ? points.length : points.length - 1;
      for (let rang = 0; rang < dernier; rang += 1) {
        if (distanceAuSegment(point, points[rang], points[(rang + 1) % points.length]) <= tolerance) {
          touche = true;
          break;
        }
      }
    }
    if (!touche) {
      continue;
    }
    const xs = points.map((p) => p[0]);
    const ys = points.map((p) => p[1]);
    const poids = (Math.max(...xs) - Math.min(...xs)) * (Math.max(...ys) - Math.min(...ys));
    if (!meilleur || poids < meilleur.poids) {
      meilleur = { ref, poids };
    }
  }
  return meilleur?.ref ?? null;
}

export function formesDuLocal(content: StudyContent, room: StudyRoom | null): StudyEnvelopeShape[] {
  if (!room) {
    return [];
  }
  return (content.enveloppe.objets ?? []).filter((shape) => shape.source_parcours?.piece === room.nom);
}

export function porteursDuComposant(content: StudyContent, composant: string | null): number {
  if (!composant) {
    return 0;
  }
  return content.enveloppe.releve_brut.elements.filter(
    (element) => !element.exclu && element.composant === composant,
  ).length;
}

export type ElementCounts = { total: number; aVerifier: number; ecartes: number; traites: number };

export function compterElements(content: StudyContent): ElementCounts {
  const liste = content.enveloppe.releve_brut.elements;
  return {
    total: liste.length,
    aVerifier: liste.filter((element) => !element.exclu && element.a_verifier).length,
    ecartes: liste.filter((element) => element.exclu).length,
    traites: liste.filter((element) => element.confirme || element.corrige).length,
  };
}

/** Épaisseur lue entre les deux nus, en centimètres : ce que le thermicien vérifie d'un coup d'œil. */
export function epaisseurCm(element: StudyReleveElement): number {
  return Math.round((element.nu_exterieur_cm - element.nu_interieur_cm) * 10) / 10;
}

export function longueurM(element: StudyReleveElement): number {
  return Math.round((element.fin_m - element.debut_m) * 100) / 100;
}

/**
 * Ce qui a changé par rapport à la lecture de l'agent, prêt à afficher.
 *
 * Sans cette comparaison, `releve_origine` ne sert à rien : c'est elle qui permet de juger la qualité
 * de la lecture niveau après niveau (Q7).
 */
export function ecartsAvecLAgent(element: StudyReleveElement): { champ: string; avant: unknown; apres: unknown }[] {
  const origine = element.releve_origine;
  if (!origine) {
    return [];
  }
  return Object.entries(origine)
    .filter(([champ, avant]) => avant !== (element as Record<string, unknown>)[champ])
    .map(([champ, avant]) => ({ champ, avant, apres: (element as Record<string, unknown>)[champ] }));
}
