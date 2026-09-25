import type {
  PdfPoint,
  StudyBridge,
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

/** Types qui ne sont pas des surfaces mais des liaisons : ce sont eux, les ponts thermiques. */
export const TYPES_PONT = ["angle_sortant", "angle_rentrant", "about_refend"] as const;

export function estPont(element: StudyReleveElement): boolean {
  return (TYPES_PONT as readonly string[]).includes(element.type);
}

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

const cleDe = (ref: StudyElementRef) => `${ref.troncon}|${ref.debut_m}|${ref.fin_m}`;

/**
 * Éléments relevés qui touchent un local, dans l'ordre du parcours de l'enveloppe.
 *
 * Deux sources, et il faut les deux : les **formes dessinées** pour les murs, menuiseries, poteaux et
 * garde-corps ; les **liaisons** pour les angles et abouts de refend, qui n'ont aucune forme et
 * n'existent sur le plan que comme pastilles. Sur le R+1, les oublier revenait à ignorer 77 des
 * 227 éléments, soit tous les ponts thermiques.
 */
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
      vises.add(cleDe(ref));
    }
  }
  for (const bridge of pontsDuLocal(content, room)) {
    const ref = elementDuPont(content, bridge);
    if (ref) {
      vises.add(cleDe(ref));
    }
  }
  return content.enveloppe.releve_brut.elements.filter((element) =>
    vises.has(cleDe(refDeElement(element))),
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

/**
 * Un pont thermique **est** un élément du relevé : sur le R+1, les 77 liaisons correspondent une à une
 * aux 77 éléments de type angle sortant, angle rentrant ou about de refend. On le retrouve donc par son
 * tronçon et son abscisse, sans reconstruire des bornes qui souffriraient des arrondis.
 */
export function elementDuPont(content: StudyContent, bridge: StudyBridge): StudyElementRef | null {
  const abscisse = bridge.abscisse_m;
  if (abscisse == null) {
    return null;
  }
  const candidats = content.enveloppe.releve_brut.elements.filter(
    (element) => element.troncon === bridge.troncon && element.type === bridge.type,
  );
  const trouve =
    candidats.find(
      (element) => Math.abs((element.debut_m + element.fin_m) / 2 - abscisse) < 1e-6,
    ) ?? candidats.find((element) => element.debut_m <= abscisse && abscisse <= element.fin_m);
  return trouve ? refDeElement(trouve) : null;
}

/**
 * La liaison dessinée qui correspond à un élément de type pont : l'inverse de `elementDuPont`.
 *
 * C'est elle qui porte `point_pdf` et `piece`. Sans ce chemin de retour, l'étape « ponts thermiques »
 * ne peut ni dire dans quel local se trouve le pont en cours, ni amener le plan dessus.
 */
export function pontDeElement(content: StudyContent, element: StudyReleveElement): StudyBridge | null {
  const milieu = (element.debut_m + element.fin_m) / 2;
  const candidats = (content.enveloppe.liaisons ?? []).filter(
    (bridge) => bridge.troncon === element.troncon && bridge.type === element.type,
  );
  return (
    candidats.find((bridge) => bridge.abscisse_m != null && Math.abs(bridge.abscisse_m - milieu) < 1e-6) ??
    candidats.find(
      (bridge) =>
        bridge.abscisse_m != null && element.debut_m <= bridge.abscisse_m && bridge.abscisse_m <= element.fin_m,
    ) ??
    null
  );
}

/** Le pont thermique sous le curseur, parmi ceux dessinés. La pastille fait 5 px de rayon à l'écran. */
export function pontAt(
  bridges: StudyBridge[],
  point: PdfPoint,
  tolerance: number,
): StudyBridge | null {
  let meilleur: { bridge: StudyBridge; ecart: number } | null = null;
  for (const bridge of bridges) {
    const centre = bridge.point_pdf;
    if (!centre) {
      continue;
    }
    const ecart = Math.hypot(point[0] - centre[0], point[1] - centre[1]);
    if (ecart <= tolerance && (!meilleur || ecart < meilleur.ecart)) {
      meilleur = { bridge, ecart };
    }
  }
  return meilleur?.bridge ?? null;
}

export function pontsDuLocal(content: StudyContent, room: StudyRoom | null): StudyBridge[] {
  if (!room) {
    return [];
  }
  return (content.enveloppe.liaisons ?? []).filter((bridge) => bridge.piece === room.nom);
}

export function formesDuLocal(content: StudyContent, room: StudyRoom | null): StudyEnvelopeShape[] {
  if (!room) {
    return [];
  }
  return (content.enveloppe.objets ?? []).filter((shape) => shape.source_parcours?.piece === room.nom);
}

/**
 * L'élément visé n'importe où sur le plan, avec le local auquel il appartient.
 *
 * Un mur est **en dehors** du contour de son local : le contour est le nu intérieur, la paroi est
 * au-delà. Exiger que le local soit déjà ouvert pour attraper son mur rendait le geste introuvable —
 * on clique sur le mur, aucun local n'est sous le curseur, et rien ne se passe. On cherche donc dans
 * tout le niveau, et l'on ouvre le local de l'élément trouvé.
 */
export function viserSurLePlan(
  content: StudyContent,
  rooms: StudyRoom[],
  point: PdfPoint,
  tolerances: { element: number; pont: number },
): { ref: StudyElementRef; room: StudyRoom | null } | null {
  const pont = pontAt(content.enveloppe.liaisons ?? [], point, tolerances.pont);
  const ref = pont ? elementDuPont(content, pont) : elementAt(content.enveloppe.objets ?? [], point, tolerances.element);
  if (!ref) {
    return null;
  }
  const nom = pont
    ? pont.piece
    : ((content.enveloppe.objets ?? []).find((shape) => memeElement(refDeForme(shape), ref))?.source_parcours?.piece ??
      null);
  return { ref, room: rooms.find((room) => room.nom === nom) ?? null };
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
