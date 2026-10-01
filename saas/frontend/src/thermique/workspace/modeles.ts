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

/** Les menuiseries (baies entières, D224) du niveau de même largeur que le modèle, à ± 2 cm, qui ne le
 *  portent pas encore : tous leurs morceaux. */
export function menuiseriesDeMemeLargeur(content: StudyContent, modele: Pick<ModeleMenuiserie, "nom" | "largeur_cm">): StudyElementRef[] {
  return baiesDuNiveau(content)
    .filter((baie) => {
      const largeur = baie.reduce((total, morceau) => total + largeurReleveeCm(morceau), 0);
      return baie.some((morceau) => morceau.modele !== modele.nom) && Math.abs(largeur - modele.largeur_cm) <= MEME_LARGEUR_CM;
    })
    .flatMap((baie) => baie.map(refDeElement));
}

export const cleDeRef = (ref: StudyElementRef) => `${ref.troncon}|${ref.debut_m}|${ref.fin_m}`;

const CONTIGU_M = 0.02;

/**
 * Les baies du niveau (D224), comme au serveur : des menuiseries contiguës de même composant et de même modèle,
 * sans rien d'actif entre elles, même d'un tronçon au suivant (abscisses globales au parcours). Le relevé ne
 * peut pas réunir deux tronçons (D223) : l'écran, lui, les traite comme une seule menuiserie.
 */
export function baiesDuNiveau(content: StudyContent): StudyReleveElement[][] {
  const actifs = content.enveloppe.releve_brut.elements
    .filter((element) => !element.exclu)
    .sort((a, b) => a.debut_m - b.debut_m || a.fin_m - b.fin_m);
  const baies: StudyReleveElement[][] = [];
  let courante: StudyReleveElement[] | null = null;
  for (const element of actifs) {
    if (element.type !== "menuiserie") {
      courante = null;
      continue;
    }
    const derniere = courante?.[courante.length - 1];
    if (
      courante &&
      derniere &&
      (derniere.composant ?? "") === (element.composant ?? "") &&
      (derniere.modele ?? null) === (element.modele ?? null) &&
      Math.abs(derniere.fin_m - element.debut_m) <= CONTIGU_M
    ) {
      courante.push(element);
      continue;
    }
    courante = [element];
    baies.push(courante);
  }
  return baies;
}

/** La baie entière d'une menuiserie : un clic sur un morceau vise tous les morceaux (D224). */
export function baieDeLElement(content: StudyContent, element: StudyReleveElement): StudyElementRef[] {
  const cle = cleDeRef(refDeElement(element));
  const baie = baiesDuNiveau(content).find((morceaux) => morceaux.some((m) => cleDeRef(refDeElement(m)) === cle));
  return (baie ?? [element]).map(refDeElement);
}

/** L'exposition lisible (D225) : secteur seul, rien tant que le nord n'est pas posé. */
export function expositionLisible(element: Pick<StudyReleveElement, "exposition">): string | null {
  const valeur = element.exposition;
  return valeur && !valeur.toLowerCase().includes("caler") ? valeur : null;
}

/** La cote d'une baie : celle du modèle posé (D221), sinon la largeur relevée ; puis son exposition (D225). */
export function texteDeLaCote(baie: StudyReleveElement | StudyReleveElement[], modeles: ModeleMenuiserie[] = []): { texte: string; posee: boolean } {
  const morceaux = Array.isArray(baie) ? baie : [baie];
  const premier = morceaux[0];
  const exposition = expositionLisible(premier);
  const suffixe = exposition ? ` · ${exposition}` : "";
  const modele = premier.modele ? modeles.find((m) => m.nom === premier.modele) : undefined;
  if (modele) {
    return { texte: `${modele.nom} · ${Math.round(modele.largeur_cm)}×${cm(modele.hauteur_m)}${suffixe}`, posee: true };
  }
  const largeur = morceaux.reduce((total, morceau) => total + largeurReleveeCm(morceau), 0);
  return { texte: `${Math.round(largeur)} cm${suffixe}`, posee: false };
}

export type CoteDeMenuiserie = { cle: string; point: PdfPoint; texte: string; posee: boolean };

/** Une cote par baie du niveau, au milieu du tracé de son plus long morceau sur le plan. */
export function cotesDesMenuiseries(content: StudyContent, modeles: ModeleMenuiserie[] = []): CoteDeMenuiserie[] {
  const tracesParElement = new Map<string, PdfPoint[]>();
  for (const shape of content.enveloppe.objets ?? []) {
    const points = shape.points_pdf ?? [];
    if (shape.category !== "menuiserie_exterieure" || points.length < 2) continue;
    const element = parentDeForme(content, shape);
    if (!element) continue;
    const cle = cleDeRef(refDeElement(element));
    tracesParElement.set(cle, [...(tracesParElement.get(cle) ?? []), ...(points as PdfPoint[])]);
  }
  const cotes: CoteDeMenuiserie[] = [];
  for (const baie of baiesDuNiveau(content)) {
    const plusLong = [...baie].sort((a, b) => b.fin_m - b.debut_m - (a.fin_m - a.debut_m))[0];
    const points = tracesParElement.get(cleDeRef(refDeElement(plusLong)));
    if (!points?.length) continue;
    const xs = points.map((p) => p[0]);
    const ys = points.map((p) => p[1]);
    const point: PdfPoint = [(Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2];
    cotes.push({ cle: cleDeRef(refDeElement(baie[0])), point, ...texteDeLaCote(baie, modeles) });
  }
  return cotes;
}
