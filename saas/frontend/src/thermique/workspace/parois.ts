import type { CompositionCopiee, PdfPoint, StudyContent, StudyElementChanges, StudyElementRef, StudyOperation, StudyReleveElement } from "../api";
import { refDeElement } from "./elements";
import { projeterSurTroncon, repereFeuille, versFeuille } from "./pontsAjoutes";

// Parois comme les menuiseries (D238 à D241) : on copie la composition d'une paroi de référence (pinceau), on
// la donne à d'autres parois d'un clic, ou l'on retrace un pan de mur entier d'un bout à l'autre.

const arrondi1 = (valeur: number) => Math.round(valeur * 10) / 10;

/** Épaisseur totale d'une paroi : la somme de ses couches, sinon l'écart entre ses deux nus. */
export function epaisseurTotaleCm(element: Pick<StudyReleveElement, "couches" | "nu_exterieur_cm" | "nu_interieur_cm">): number {
  const somme = (element.couches ?? []).reduce((total, couche) => total + (couche.epaisseur_cm || 0), 0);
  return arrondi1(somme > 0 ? somme : Math.abs(element.nu_exterieur_cm - element.nu_interieur_cm));
}

/** Ce que le pinceau prend d'une paroi de référence (D239). */
export function compositionDe(element: StudyReleveElement): CompositionCopiee {
  const couches = (element.couches ?? []).filter((couche) => couche.epaisseur_cm > 0).map((couche) => ({ ...couche }));
  return {
    composant: element.composant,
    couches,
    nu_exterieur_cm: element.nu_exterieur_cm,
    nu_interieur_cm: element.nu_interieur_cm,
    libelle: `${element.composant ?? "paroi"} · ${epaisseurTotaleCm(element)} cm`,
  };
}

/** Les corrections qui donnent la composition copiée à une paroi. */
export function changesDuPinceau(composition: CompositionCopiee): StudyElementChanges {
  return {
    ...(composition.composant ? { composant: composition.composant } : {}),
    ...(composition.couches.length ? { couches: composition.couches } : {}),
    nu_exterieur_cm: composition.nu_exterieur_cm,
    nu_interieur_cm: composition.nu_interieur_cm,
    nu_exterieur_fin_cm: composition.nu_exterieur_cm,
    nu_interieur_fin_cm: composition.nu_interieur_cm,
  };
}

export const correctionDuPinceau = (ref: StudyElementRef, composition: CompositionCopiee): StudyOperation => ({
  type: "element_corriger",
  element: ref,
  changes: changesDuPinceau(composition),
});

/** Les parois du niveau qui portent le composant de la référence, autres qu'elle (raccourci du pinceau). */
export function paroisDuComposant(content: StudyContent, composant: string | null, sauf?: StudyElementRef): StudyElementRef[] {
  if (!composant) return [];
  return content.enveloppe.releve_brut.elements
    .filter(
      (element) =>
        element.type === "paroi" &&
        !element.exclu &&
        element.composant === composant &&
        !(sauf && element.troncon === sauf.troncon && element.debut_m === sauf.debut_m && element.fin_m === sauf.fin_m),
    )
    .map(refDeElement);
}

/** L'abscisse le long de la façade (globale au parcours) d'un point cliqué sur le plan, comme le serveur. */
export function abscisseSurLaFacade(content: StudyContent, point: PdfPoint): number | null {
  const repere = repereFeuille(content);
  if (!repere) return null;
  const position = projeterSurTroncon(content, versFeuille(repere, point));
  return position ? position.abscisse_m : null;
}

/** Le geste « retracer un mur » entre deux clics (D240), ou null si la façade ne se retrouve pas. */
export function retracerEntre(content: StudyContent, a: PdfPoint, b: PdfPoint, composition: CompositionCopiee): StudyOperation | null {
  const debut = abscisseSurLaFacade(content, a);
  const fin = abscisseSurLaFacade(content, b);
  if (debut === null || fin === null) return null;
  return { type: "paroi_retracer", debut_m: Math.min(debut, fin), fin_m: Math.max(debut, fin), modele: composition };
}
