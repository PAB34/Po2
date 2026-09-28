import type { PdfPoint, StudyBridge, StudyContent, StudyReleveElement } from "../api";
import { pointInPolygon } from "./edition";

/**
 * Poser un pont dans l'écran, sans attendre le serveur (P5, D164).
 *
 * Seul le serveur savait sur quel tronçon tombe un point : chaque ajout recalculait tout le niveau, soit
 * quelques secondes par pont — le défaut déjà corrigé pour les recadrages. L'écran applique ici la **même
 * règle** que `_ajouter_pont` côté serveur, et envoie le tronçon et l'abscisse trouvés : le serveur ne fait
 * plus que les vérifier, au seul recalcul de l'enregistrement.
 */

type Affine = { a: number; b: number; c: number; d: number; e: number; f: number };

/**
 * Passage des points PDF au repère de la feuille (0 à 1000), déduit des locaux eux-mêmes : chacun porte son
 * contour dans les deux repères. La correspondance est affine (c'est la matrice du rendu) ; trois points
 * bien écartés suffisent, on prend les moindres carrés sur tous pour ne dépendre d'aucun arrondi.
 */
export function repereFeuille(content: StudyContent): Affine | null {
  const paires: [PdfPoint, [number, number]][] = [];
  for (const room of content.locaux) {
    const contour = (room as { contour?: [number, number][] }).contour;
    if (!contour || contour.length !== room.contour_pdf.length) continue;
    room.contour_pdf.forEach((point, rang) => paires.push([point, contour[rang]]));
  }
  if (paires.length < 3) return null;
  // Moindres carrés : [x y 1]·(a c e) = X et [x y 1]·(b d f) = Y.
  const m = [
    [0, 0, 0],
    [0, 0, 0],
    [0, 0, 0],
  ];
  const vx = [0, 0, 0];
  const vy = [0, 0, 0];
  for (const [[x, y], [X, Y]] of paires) {
    const ligne = [x, y, 1];
    for (let i = 0; i < 3; i += 1) {
      for (let j = 0; j < 3; j += 1) m[i][j] += ligne[i] * ligne[j];
      vx[i] += ligne[i] * X;
      vy[i] += ligne[i] * Y;
    }
  }
  const sx = resoudre3(m, vx);
  const sy = resoudre3(m, vy);
  if (!sx || !sy) return null;
  return { a: sx[0], c: sx[1], e: sx[2], b: sy[0], d: sy[1], f: sy[2] };
}

function resoudre3(m: number[][], v: number[]): number[] | null {
  const det = (q: number[][]) =>
    q[0][0] * (q[1][1] * q[2][2] - q[1][2] * q[2][1]) -
    q[0][1] * (q[1][0] * q[2][2] - q[1][2] * q[2][0]) +
    q[0][2] * (q[1][0] * q[2][1] - q[1][1] * q[2][0]);
  const d = det(m);
  if (Math.abs(d) < 1e-12) return null;
  return [0, 1, 2].map((colonne) => det(m.map((ligne, i) => ligne.map((valeur, j) => (j === colonne ? v[i] : valeur)))) / d);
}

export const versFeuille = (repere: Affine, [x, y]: PdfPoint): [number, number] => [
  repere.a * x + repere.c * y + repere.e,
  repere.b * x + repere.d * y + repere.f,
];

const arrondi3 = (valeur: number) => Math.round(valeur * 1000) / 1000;

type Troncon = {
  id: string;
  origine_px: [number, number];
  direction: [number, number];
  debut_m: number;
  fin_m: number;
  local_debut_m: number;
  local_fin_m?: number;
};

/** Le tronçon le plus proche et l'abscisse du pied du point : la règle de `_ajouter_pont`, à l'identique. */
export function projeterSurTroncon(content: StudyContent, feuille: [number, number]): { troncon: string; abscisse_m: number } | null {
  const manifeste = (content.enveloppe as unknown as { manifeste?: { page_px: [number, number]; px_par_m: number; troncons: Troncon[] } })
    .manifeste;
  if (!manifeste?.troncons?.length) return null;
  const [largeur, hauteur] = manifeste.page_px;
  const px = (feuille[0] * largeur) / 1000;
  const py = (feuille[1] * hauteur) / 1000;
  let meilleur: { distance: number; troncon: Troncon; abscisse: number } | null = null;
  for (const troncon of manifeste.troncons) {
    const [ox, oy] = troncon.origine_px;
    const [ux, uy] = troncon.direction;
    const localFin = troncon.local_fin_m ?? troncon.local_debut_m + troncon.fin_m - troncon.debut_m;
    const local = Math.min(Math.max(((px - ox) * ux + (py - oy) * uy) / manifeste.px_par_m, troncon.local_debut_m), localFin);
    const pied = [ox + ux * local * manifeste.px_par_m, oy + uy * local * manifeste.px_par_m];
    const distance = Math.hypot(px - pied[0], py - pied[1]);
    if (!meilleur || distance < meilleur.distance) {
      meilleur = { distance, troncon, abscisse: troncon.debut_m + (local - troncon.local_debut_m) };
    }
  }
  return meilleur ? { troncon: meilleur.troncon.id, abscisse_m: arrondi3(meilleur.abscisse) } : null;
}

/**
 * Le geste complet, prêt à appliquer : tronçon, abscisse libre (deux ponts au même endroit restent deux
 * éléments) et point de la feuille. `null` si le niveau n'a pas de quoi situer un pont.
 */
export function preparerAjout(
  content: StudyContent,
  point_pdf: PdfPoint,
  type_pont: string,
): { type: "pont_ajouter"; point_pdf: PdfPoint; type_pont: string; troncon: string; abscisse_m: number } | null {
  const repere = repereFeuille(content);
  if (!repere) return null;
  const position = projeterSurTroncon(content, versFeuille(repere, point_pdf));
  if (!position) return null;
  const prises = new Set(content.enveloppe.releve_brut.elements.map((e) => `${e.troncon}|${e.debut_m}|${e.fin_m}`));
  let abscisse = position.abscisse_m;
  while (prises.has(`${position.troncon}|${abscisse}|${abscisse}`)) {
    abscisse = arrondi3(abscisse + 0.001);
  }
  return { type: "pont_ajouter", point_pdf, type_pont, troncon: position.troncon, abscisse_m: abscisse };
}

/** Le pont posé, dans le relevé et sur le plan, tel que le serveur le fera à l'enregistrement. */
export function appliquerAjout(
  content: StudyContent,
  operation: { point_pdf: PdfPoint; type_pont: string; troncon?: string; abscisse_m?: number; reference_pont?: string },
): StudyContent {
  if (operation.troncon == null || operation.abscisse_m == null) return content;
  const repere = repereFeuille(content);
  const feuille = repere ? versFeuille(repere, operation.point_pdf) : null;
  const element: StudyReleveElement = {
    troncon: operation.troncon,
    debut_m: operation.abscisse_m,
    fin_m: operation.abscisse_m,
    type: operation.type_pont,
    composant: null,
    nu_exterieur_cm: 0,
    nu_interieur_cm: 0,
    confiance: 1,
    indice: "pont ajouté par le thermicien",
    a_verifier: false,
    confirme: true,
    ajoute: true,
    ...(operation.reference_pont ? { reference_pont: operation.reference_pont } : {}),
    ...(feuille ? { point_feuille: [arrondi3(feuille[0]), arrondi3(feuille[1])] } : {}),
  } as StudyReleveElement;
  const piece = content.locaux.find((room) => pointInPolygon(room.contour_pdf, operation.point_pdf[0], operation.point_pdf[1]));
  const liaison: StudyBridge = {
    type: operation.type_pont,
    troncon: operation.troncon,
    abscisse_m: operation.abscisse_m,
    longueur_m: 0,
    piece: piece?.nom ?? null,
    point_pdf: operation.point_pdf,
    exclu: false,
    a_verifier: false,
    confirme: true,
    ajoute: true,
    angle_mesure_deg: null,
    ...(operation.reference_pont ? { reference_pont: operation.reference_pont } : {}),
  };
  return {
    ...content,
    enveloppe: {
      ...content.enveloppe,
      releve_brut: { ...content.enveloppe.releve_brut, elements: [...content.enveloppe.releve_brut.elements, element] },
      liaisons: [...(content.enveloppe.liaisons ?? []), liaison],
    },
  };
}
