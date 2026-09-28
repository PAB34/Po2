import type { PdfPoint, Sheet } from "../api";
import { groupSheets } from "./levels";

/**
 * Superposition des niveaux (S2, S3 ; D168 à D173).
 *
 * Une planche calée porte une similitude z' = s·z + t (nombres complexes : `s = a + ib` porte rotation et
 * échelle) qui envoie ses points PDF sur ceux de la référence. Montrer le niveau voisin sur le plan actif,
 * c'est composer : points du voisin → référence → points de la planche active.
 */
export type Similitude = { a: number; b: number; tx: number; ty: number };

export const IDENTITE: Similitude = { a: 1, b: 0, tx: 0, ty: 0 };

export function appliquer(sim: Similitude, [x, y]: PdfPoint): PdfPoint {
  return [sim.a * x - sim.b * y + sim.tx, sim.b * x + sim.a * y + sim.ty];
}

/** `apres` ∘ `avant`. */
export function composer(apres: Similitude, avant: Similitude): Similitude {
  return {
    a: apres.a * avant.a - apres.b * avant.b,
    b: apres.a * avant.b + apres.b * avant.a,
    tx: apres.a * avant.tx - apres.b * avant.ty + apres.tx,
    ty: apres.b * avant.tx + apres.a * avant.ty + apres.ty,
  };
}

export function inverser(sim: Similitude): Similitude {
  const norme = sim.a * sim.a + sim.b * sim.b;
  const a = sim.a / norme;
  const b = -sim.b / norme;
  return { a, b, tx: -(a * sim.tx - b * sim.ty), ty: -(b * sim.tx + a * sim.ty) };
}

/** La similitude qui envoie deux points sur deux autres (même calcul que le serveur). */
export function similitude(sources: [PdfPoint, PdfPoint], cibles: [PdfPoint, PdfPoint]): Similitude | null {
  const [z1, z2] = sources;
  const [w1, w2] = cibles;
  const dzx = z2[0] - z1[0];
  const dzy = z2[1] - z1[1];
  const norme = dzx * dzx + dzy * dzy;
  if (norme < 1e-9) return null;
  const dwx = w2[0] - w1[0];
  const dwy = w2[1] - w1[1];
  // s = dw / dz
  const a = (dwx * dzx + dwy * dzy) / norme;
  const b = (dwy * dzx - dwx * dzy) / norme;
  return { a, b, tx: w1[0] - (a * z1[0] - b * z1[1]), ty: w1[1] - (b * z1[0] + a * z1[1]) };
}

/** Vers la référence : l'identité pour la référence, son calage pour une planche calée sur elle, sinon rien. */
export function versReference(sheet: Sheet, referenceId: number | null): Similitude | null {
  if (referenceId == null) return null;
  if (sheet.id === referenceId) return IDENTITE;
  const calage = sheet.calage;
  if (!calage || calage.reference_sheet_id !== referenceId) return null;
  return { a: calage.a, b: calage.b, tx: calage.tx, ty: calage.ty };
}

/**
 * Où poser le voisin sur la planche active. Calées toutes deux : la vraie correspondance. Sinon, une pose
 * provisoire (mêmes centres, rapport des échelles déclarées), annoncée comme telle, qui sert justement à
 * pointer les deux paires de points du calage.
 */
export function correspondance(
  voisin: Sheet,
  actif: Sheet,
  referenceId: number | null,
): { sim: Similitude; calee: boolean } {
  const voisinVersRef = versReference(voisin, referenceId);
  const actifVersRef = versReference(actif, referenceId);
  if (voisinVersRef && actifVersRef) {
    return { sim: composer(inverser(actifVersRef), voisinVersRef), calee: true };
  }
  const echelle =
    voisin.scale_denominator && actif.scale_denominator ? voisin.scale_denominator / actif.scale_denominator : 1;
  const [cxv, cyv] = [voisin.page_width_pt / 2, voisin.page_height_pt / 2];
  const [cxa, cya] = [actif.page_width_pt / 2, actif.page_height_pt / 2];
  return { sim: { a: echelle, b: 0, tx: cxa - echelle * cxv, ty: cya - echelle * cyv }, calee: false };
}

/** Les plans de niveau juste en dessous et juste au-dessus, dans l'ordre du bâtiment (D169). */
export function niveauxVoisins(sheets: Sheet[], actif: Sheet | null): { inferieur: Sheet | null; superieur: Sheet | null } {
  const { levels } = groupSheets(sheets);
  const rang = actif ? levels.findIndex((sheet) => sheet.id === actif.id) : -1;
  if (rang < 0) return { inferieur: null, superieur: null };
  return { inferieur: levels[rang - 1] ?? null, superieur: levels[rang + 1] ?? null };
}

/**
 * Ce qu'il faut enregistrer après deux paires cliquées (D173) : on cale la planche qui ne l'est pas sur celle
 * qui l'est — le voisin si la planche active est calée (ou est la référence), la planche active sinon.
 * `paires` : [point sur le voisin, point sur la planche active], dans les points PDF de chacune.
 */
export function calageAEnregistrer(
  voisin: Sheet,
  actif: Sheet,
  referenceId: number | null,
  paires: [PdfPoint, PdfPoint][],
):
  | { planche: number; cible: number; points: PdfPoint[]; points_cible: PdfPoint[] }
  | { refus: string } {
  if (referenceId == null) {
    return { refus: "Choisissez d'abord la planche de référence du projet : les niveaux se calent sur elle." };
  }
  if (paires.length !== 2) return { refus: "Le calage demande deux paires de points." };
  const surVoisin = paires.map(([v]) => v);
  const surActif = paires.map(([, a]) => a);
  if (versReference(actif, referenceId) && voisin.id !== referenceId) {
    return { planche: voisin.id, cible: actif.id, points: surVoisin, points_cible: surActif };
  }
  if (versReference(voisin, referenceId)) {
    return { planche: actif.id, cible: voisin.id, points: surActif, points_cible: surVoisin };
  }
  return { refus: "Aucune des deux planches n'est calée : calez d'abord l'une d'elles sur la planche de référence." };
}
