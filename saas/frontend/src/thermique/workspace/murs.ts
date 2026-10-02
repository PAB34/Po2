import type { LigneMetre, PdfPoint, StudyContent, StudyElementRef, StudyReleveElement } from "../api";
import { faitPartieDe, memeElement, refDeElement } from "./elements";
import { repereFeuille, versFeuille } from "./pontsAjoutes";

// D249 : la ligne de métré d'un mur se modifie à la main, extrémité par extrémité, librement sur le plan.
// Le repère d'un tronçon (abscisse le long de la façade, profondeur perpendiculaire) couvre tout le plan : un
// point lâché n'importe où se lit exactement comme une borne du mur et sa face intérieure à ce bout.

type Troncon = {
  id: string;
  origine_px: [number, number];
  direction: [number, number];
  normale_ext: [number, number];
  debut_m: number;
  local_debut_m: number;
};
type Manifeste = { page_px: [number, number]; px_par_m: number; troncons: Troncon[] };

export type Extremite = "debut" | "fin";
export type GesteExtremite = {
  type: "paroi_extremite";
  element: StudyElementRef;
  extremite: Extremite;
  abscisse_m: number;
  nu_interieur_cm: number;
};

/** Longueur sous laquelle un mur est refusé, comme au serveur (`LONGUEUR_MUR_MIN_M`). */
export const LONGUEUR_MUR_MIN_M = 0.05;

const arrondi = (valeur: number, pas: number) => Math.round(valeur / pas) * pas;

function manifesteDe(content: StudyContent): Manifeste | null {
  const manifeste = (content.enveloppe as unknown as { manifeste?: Manifeste }).manifeste;
  return manifeste?.troncons?.length && manifeste.page_px && manifeste.px_par_m ? manifeste : null;
}

/** Feuille (0..1000) → PDF : l'inverse du repère que les locaux donnent (affine). */
function versPdf(content: StudyContent, feuille: [number, number]): PdfPoint | null {
  const r = repereFeuille(content);
  if (!r) return null;
  const det = r.a * r.d - r.b * r.c;
  if (Math.abs(det) < 1e-12) return null;
  const X = feuille[0] - r.e;
  const Y = feuille[1] - r.f;
  return [(r.d * X - r.c * Y) / det, (-r.b * X + r.a * Y) / det];
}

/** Le point d'un tronçon à une abscisse et une profondeur (cm, positive vers l'extérieur), comme `_point`. */
function pointPdf(content: StudyContent, troncon: Troncon, manifeste: Manifeste, abscisse: number, profondeurCm: number): PdfPoint | null {
  const [ox, oy] = troncon.origine_px;
  const [ux, uy] = troncon.direction;
  const [nx, ny] = troncon.normale_ext;
  const local = troncon.local_debut_m + (abscisse - troncon.debut_m);
  const t = profondeurCm / 100;
  const px = ox + (ux * local + nx * t) * manifeste.px_par_m;
  const py = oy + (uy * local + ny * t) * manifeste.px_par_m;
  const [largeur, hauteur] = manifeste.page_px;
  return versPdf(content, [(px * 1000) / largeur, (py * 1000) / hauteur]);
}

/** Les deux extrémités de la ligne de métré d'un mur (face intérieure, au début et à la fin), en points PDF. */
export function extremitesDuMur(content: StudyContent, element: StudyReleveElement): Record<Extremite, PdfPoint> | null {
  const manifeste = manifesteDe(content);
  const troncon = manifeste?.troncons.find((item) => item.id === element.troncon);
  if (!manifeste || !troncon || !troncon.normale_ext) return null;
  const debut = pointPdf(content, troncon, manifeste, element.debut_m, element.nu_interieur_cm);
  const fin = pointPdf(content, troncon, manifeste, element.fin_m, element.nu_interieur_fin_cm ?? element.nu_interieur_cm);
  return debut && fin ? { debut, fin } : null;
}

/** Un point PDF lu dans le repère du tronçon du mur : abscisse (m) et profondeur (cm). */
export function positionSurLeTroncon(
  content: StudyContent,
  element: StudyReleveElement,
  point: PdfPoint,
): { abscisse_m: number; profondeur_cm: number } | null {
  const manifeste = manifesteDe(content);
  const troncon = manifeste?.troncons.find((item) => item.id === element.troncon);
  const repere = repereFeuille(content);
  if (!manifeste || !troncon || !troncon.normale_ext || !repere) return null;
  const [fx, fy] = versFeuille(repere, point);
  const [largeur, hauteur] = manifeste.page_px;
  const dx = (fx * largeur) / 1000 - troncon.origine_px[0];
  const dy = (fy * hauteur) / 1000 - troncon.origine_px[1];
  const local = (dx * troncon.direction[0] + dy * troncon.direction[1]) / manifeste.px_par_m;
  const t = (dx * troncon.normale_ext[0] + dy * troncon.normale_ext[1]) / manifeste.px_par_m;
  return {
    abscisse_m: arrondi(troncon.debut_m + local - troncon.local_debut_m, 0.001),
    profondeur_cm: arrondi(t * 100, 0.1),
  };
}

/** Le geste « déplacer cette extrémité ici », ou la raison de le refuser. */
export function gesteExtremite(
  content: StudyContent,
  element: StudyReleveElement,
  extremite: Extremite,
  point: PdfPoint,
): GesteExtremite | string {
  const position = positionSurLeTroncon(content, element, point);
  if (!position) return "Ce niveau n'a pas de repère d'enveloppe : la ligne ne peut pas être déplacée.";
  const debut = extremite === "debut" ? position.abscisse_m : element.debut_m;
  const fin = extremite === "fin" ? position.abscisse_m : element.fin_m;
  if (fin - debut < LONGUEUR_MUR_MIN_M) return "Le mur deviendrait trop court, ou ses deux extrémités se croiseraient.";
  return {
    type: "paroi_extremite",
    element: refDeElement(element),
    extremite,
    abscisse_m: position.abscisse_m,
    nu_interieur_cm: position.profondeur_cm,
  };
}

/**
 * Le geste appliqué dans l'écran, comme le serveur le fera (`deplacer_extremite`) : bornes, face intérieure
 * et extérieure à ce bout (épaisseur gardée), et la ligne de métré redessinée aussitôt.
 */
export function appliquerExtremite(content: StudyContent, geste: GesteExtremite): { content: StudyContent; ref: StudyElementRef | null } {
  const elements = content.enveloppe.releve_brut.elements;
  const vise = elements.find((element) => memeElement(refDeElement(element), geste.element));
  if (!vise || vise.exclu || vise.type !== "paroi") return { content, ref: null };
  const ext = vise.nu_exterieur_cm;
  const inte = vise.nu_interieur_cm;
  const extFin = vise.nu_exterieur_fin_cm ?? ext;
  const inteFin = vise.nu_interieur_fin_cm ?? inte;
  const face = arrondi(geste.nu_interieur_cm, 0.1);
  let debut = geste.extremite === "debut" ? geste.abscisse_m : vise.debut_m;
  let fin = geste.extremite === "fin" ? geste.abscisse_m : vise.fin_m;
  debut = arrondi(debut, 0.001);
  fin = arrondi(fin, 0.001);
  const prises = new Set(elements.filter((element) => element !== vise).map((e) => `${e.troncon}|${e.debut_m}|${e.fin_m}`));
  while (prises.has(`${vise.troncon}|${debut}|${fin}`)) fin = arrondi(fin + 0.001, 0.001);
  const origine = { ...(vise.releve_origine ?? {}) } as Record<string, unknown>;
  if (!("bornes" in origine)) origine.bornes = [vise.debut_m, vise.fin_m];
  const deplace: StudyReleveElement = {
    ...vise,
    debut_m: debut,
    fin_m: fin,
    nu_exterieur_fin_cm: extFin,
    nu_interieur_fin_cm: inteFin,
    ...(geste.extremite === "debut"
      ? { nu_interieur_cm: face, nu_exterieur_cm: arrondi(face + ext - inte, 0.1) }
      : { nu_interieur_fin_cm: face, nu_exterieur_fin_cm: arrondi(face + extFin - inteFin, 0.1) }),
    corrige: true,
    a_verifier: false,
    releve_origine: origine as StudyReleveElement["releve_origine"],
  };
  const avant = refDeElement(vise);
  const apres = refDeElement(deplace);
  const sansLui = <T extends { source_parcours?: { troncon?: string; debut_m?: number; fin_m?: number } }>(liste: T[] | undefined) =>
    liste?.filter((forme) => {
      const s = forme.source_parcours;
      return !(s?.troncon && s.debut_m != null && s.fin_m != null && faitPartieDe(avant, { troncon: s.troncon, debut_m: s.debut_m, fin_m: s.fin_m }));
    });
  const bouts = extremitesDuMur(content, deplace);
  const ligne: LigneMetre | null = bouts
    ? {
        points_pdf: [bouts.debut, bouts.fin],
        source_parcours: { ...apres, composant: vise.composant ?? null },
        composant: vise.composant ?? "",
        epaisseur_cm: arrondi((deplace.nu_exterieur_cm - deplace.nu_interieur_cm), 0.1),
        epaisseur_fin_cm: arrondi((deplace.nu_exterieur_fin_cm ?? 0) - (deplace.nu_interieur_fin_cm ?? 0), 0.1),
        longueur_m: arrondi(fin - debut, 0.001),
      }
    : null;
  return {
    ref: apres,
    content: {
      ...content,
      enveloppe: {
        ...content.enveloppe,
        // Ses couches redessinées attendent le recalcul, qui part aussitôt (D252) : on les retire d'ici là.
        objets: sansLui(content.enveloppe.objets),
        lignes_metre: [...(sansLui(content.enveloppe.lignes_metre) ?? []), ...(ligne ? [ligne] : [])],
        releve_brut: {
          ...content.enveloppe.releve_brut,
          elements: elements.map((element) => (element === vise ? deplace : element)),
        },
      },
    },
  };
}

/** L'extrémité d'une autre ligne de métré la plus proche du point, à moins de `tolerance` (points PDF) : l'aimant. */
export function boutLePlusProche(
  content: StudyContent,
  element: StudyReleveElement,
  point: PdfPoint,
  tolerance: number,
): PdfPoint | null {
  const lui = refDeElement(element);
  let meilleur: { distance: number; bout: PdfPoint } | null = null;
  for (const ligne of content.enveloppe.lignes_metre ?? []) {
    const points = ligne.points_pdf ?? [];
    if (points.length < 2 || faitPartieDe(lui, ligne.source_parcours)) continue;
    for (const bout of [points[0], points[points.length - 1]]) {
      const distance = Math.hypot(bout[0] - point[0], bout[1] - point[1]);
      if (distance <= tolerance && (!meilleur || distance < meilleur.distance)) meilleur = { distance, bout };
    }
  }
  return meilleur?.bout ?? null;
}

/** Longueur réelle d'une ligne de métré qui irait de `a` à `b` (points PDF), via le repère de l'enveloppe. */
export function longueurEntre(content: StudyContent, element: StudyReleveElement, a: PdfPoint, b: PdfPoint): number | null {
  const pa = positionSurLeTroncon(content, element, a);
  const pb = positionSurLeTroncon(content, element, b);
  if (!pa || !pb) return null;
  return Math.hypot(pb.abscisse_m - pa.abscisse_m, (pb.profondeur_cm - pa.profondeur_cm) / 100);
}
