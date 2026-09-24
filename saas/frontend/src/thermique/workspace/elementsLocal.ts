import type {
  StudyContent,
  StudyElementChanges,
  StudyElementRef,
  StudyOperation,
  StudyReleveElement,
} from "../api";
import { memeElement, refDeElement } from "./elements";

/**
 * Application des gestes d'élément **dans l'écran**, sans serveur (D105).
 *
 * Un recalcul de niveau coûte 3,2 s sur le R+1, et dix gestes envoyés ensemble coûtent le même prix
 * qu'un seul : le coût est le recalcul, pas le geste. Confirmer les 92 éléments douteux un par un avec
 * un aller-retour serveur à chaque clic demanderait cinq minutes d'attente pure.
 *
 * Ces fonctions reproduisent donc, sur la copie affichée, exactement ce que le serveur fera au recalcul.
 * Elles ne touchent que le **relevé brut** — la source de vérité (D99) — jamais le dessin : le plan ne
 * changera qu'au recalcul, et l'écran le dit.
 */

/** Les mêmes contrôles que le serveur, pour refuser tout de suite ce qu'il refuserait. */
export function refusDeCorrection(element: StudyReleveElement, changes: StudyElementChanges): string | null {
  const futur = { ...element, ...changes };
  if (changes.composant != null && !changes.composant.trim()) {
    return "Le composant ne peut pas être vide.";
  }
  const paires: [number | undefined, number | undefined][] = [
    [futur.nu_exterieur_cm, futur.nu_interieur_cm],
    [futur.nu_exterieur_fin_cm, futur.nu_interieur_fin_cm],
  ];
  for (const [exterieur, interieur] of paires) {
    if (exterieur != null && interieur != null && interieur > exterieur) {
      return `Le nu intérieur (${interieur} cm) ne peut pas dépasser le nu extérieur (${exterieur} cm).`;
    }
  }
  return null;
}

function majElement(
  element: StudyReleveElement,
  changes: StudyElementChanges,
  marque: "confirme" | "corrige",
): StudyReleveElement {
  // La première lecture de l'agent est gardée telle quelle : corriger une correction ne l'efface pas.
  const origine = { ...(element.releve_origine ?? {}) };
  for (const champ of Object.keys(changes)) {
    if (!(champ in origine)) {
      origine[champ] = (element as Record<string, unknown>)[champ];
    }
  }
  return {
    ...element,
    ...changes,
    a_verifier: false,
    [marque]: true,
    ...(Object.keys(origine).length > 0 ? { releve_origine: origine } : {}),
  };
}

/** Applique un geste à l'étude affichée et rend une nouvelle étude, sans toucher à l'originale. */
export function appliquerEnLocal(content: StudyContent, operation: StudyOperation): StudyContent {
  if (!operation.type.startsWith("element_")) {
    return content;
  }
  const ref = (operation as { element: StudyElementRef }).element;
  const vise = content.enveloppe.releve_brut.elements.find((element) =>
    memeElement(refDeElement(element), ref),
  );
  if (!vise) {
    return content;
  }

  const partout =
    operation.type === "element_corriger" &&
    operation.portee === "partout" &&
    Boolean(vise.composant);
  const concerne = (element: StudyReleveElement) =>
    partout ? !element.exclu && element.composant === vise.composant : memeElement(refDeElement(element), ref);

  const elements = content.enveloppe.releve_brut.elements.map((element) => {
    if (!concerne(element)) {
      return element;
    }
    switch (operation.type) {
      case "element_confirmer":
        return { ...element, a_verifier: false, confirme: true };
      case "element_corriger":
        return majElement(element, operation.changes, "corrige");
      case "element_ecarter":
        return { ...element, exclu: true, motif_exclusion: operation.motif.slice(0, 300), a_verifier: false };
      case "element_reactiver": {
        const { exclu: _exclu, motif_exclusion: _motif, ...reste } = element;
        return reste as StudyReleveElement;
      }
      default:
        return element;
    }
  });

  return {
    ...content,
    enveloppe: { ...content.enveloppe, releve_brut: { ...content.enveloppe.releve_brut, elements } },
  };
}
