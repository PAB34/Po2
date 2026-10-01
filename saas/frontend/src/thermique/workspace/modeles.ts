import type { MenuiseriesDuProjet, ModeleMenuiserie, PdfPoint, StudyContent, StudyElementRef, StudyReleveElement } from "../api";
import { parentDeForme, refDeElement } from "./elements";
import { proposerComposants } from "./baies";

// Modèles de menuiserie (D219 à D222) : mesurés en coupe ou en élévation, posés sur les menuiseries du plan
// par le thermicien. Le nom lu par l'IA ne décide plus de rien.

export const MEME_LARGEUR_CM = 2;

const cm = (m: number) => Math.round(m * 100);

/** Le nom proposé : le composant du projet le plus proche en largeur, puis les dimensions mesurées. */
export function nomPropose(largeurM: number, hauteurM: number, menuiseries?: MenuiseriesDuProjet): string {
  const [proche] = proposerComposants(menuiseries, largeurM * 100);
  return `${proche?.composant ?? "M"} ${cm(largeurM)}×${cm(hauteurM)}`;
}

/** Largeur d'une menuiserie relevée sur le plan, en cm. */
export function largeurReleveeCm(element: StudyReleveElement): number {
  return Math.round((element.fin_m - element.debut_m) * 1000) / 10;
}

/** Les menuiseries du niveau de même largeur que le modèle, à ± 2 cm, qui ne le portent pas encore. */
export function menuiseriesDeMemeLargeur(content: StudyContent, modele: Pick<ModeleMenuiserie, "nom" | "largeur_cm">): StudyElementRef[] {
  return content.enveloppe.releve_brut.elements
    .filter(
      (element) =>
        element.type === "menuiserie" &&
        !element.exclu &&
        element.modele !== modele.nom &&
        Math.abs(largeurReleveeCm(element) - modele.largeur_cm) <= MEME_LARGEUR_CM,
    )
    .map(refDeElement);
}

export const cleDeRef = (ref: StudyElementRef) => `${ref.troncon}|${ref.debut_m}|${ref.fin_m}`;

/** La cote d'une menuiserie : celle du modèle posé (D221), sinon la largeur relevée. */
export function texteDeLaCote(element: StudyReleveElement, modeles: ModeleMenuiserie[] = []): { texte: string; posee: boolean } {
  const modele = element.modele ? modeles.find((m) => m.nom === element.modele) : undefined;
  if (modele) {
    return { texte: `${modele.nom} · ${Math.round(modele.largeur_cm)}×${cm(modele.hauteur_m)}`, posee: true };
  }
  return { texte: `${Math.round(largeurReleveeCm(element))} cm`, posee: false };
}

export type CoteDeMenuiserie = { cle: string; point: PdfPoint; texte: string; posee: boolean };

/** Une cote par menuiserie du niveau, au milieu de son premier tracé sur le plan. */
export function cotesDesMenuiseries(content: StudyContent, modeles: ModeleMenuiserie[] = []): CoteDeMenuiserie[] {
  const vues = new Set<string>();
  const cotes: CoteDeMenuiserie[] = [];
  for (const shape of content.enveloppe.objets ?? []) {
    const points = shape.points_pdf ?? [];
    if (shape.category !== "menuiserie_exterieure" || points.length < 2) continue;
    const element = parentDeForme(content, shape);
    if (!element || element.exclu) continue;
    const cle = cleDeRef(refDeElement(element));
    if (vues.has(cle)) continue;
    vues.add(cle);
    const xs = points.map((p) => p[0]);
    const ys = points.map((p) => p[1]);
    const point: PdfPoint = [(Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2];
    cotes.push({ cle, point, ...texteDeLaCote(element, modeles) });
  }
  return cotes;
}
