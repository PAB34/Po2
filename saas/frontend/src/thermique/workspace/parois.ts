import type { StudyContent, StudyCouche, StudyElementChanges, StudyEnvelopeShape, StudyReleveElement } from "../api";

// Un mur = une ligne de métré (sa face intérieure) qui porte une composition (D242 à D245). Le thermicien la
// vérifie et la valide mur par mur dans la fiche ; le pinceau de D239 est retiré de l'écran.

const arrondi1 = (valeur: number) => Math.round(valeur * 10) / 10;

/** Épaisseur totale d'une paroi : la somme de ses couches, sinon l'écart entre ses deux nus. */
export function epaisseurTotaleCm(element: Pick<StudyReleveElement, "couches" | "nu_exterieur_cm" | "nu_interieur_cm">): number {
  const somme = (element.couches ?? []).reduce((total, couche) => total + (couche.epaisseur_cm || 0), 0);
  return arrondi1(somme > 0 ? somme : Math.abs(element.nu_exterieur_cm - element.nu_interieur_cm));
}

/** Natures de couche proposées dans la fiche, dans l'ordre où elles se rencontrent de l'extérieur vers l'intérieur. */
export const NATURES_COUCHE: { id: string; label: string }[] = [
  { id: "enduit", label: "enduit" },
  { id: "bardage", label: "bardage" },
  { id: "lame_air", label: "lame d'air" },
  { id: "isolant", label: "isolant" },
  { id: "mur", label: "mur (béton, maçonnerie)" },
  { id: "doublage", label: "doublage" },
  { id: "parement", label: "parement" },
  { id: "autre", label: "autre" },
];

/** Les couches telles que la fiche les édite : sans les couches vides, sans marque « présumé » une fois validées. */
export function couchesValidees(couches: StudyCouche[]): StudyCouche[] {
  return couches
    .filter((couche) => couche.nature && couche.epaisseur_cm > 0)
    .map(({ nature, epaisseur_cm, indice }) => ({ nature, epaisseur_cm: arrondi1(epaisseur_cm), ...(indice ? { indice } : {}) }));
}

/**
 * Les corrections qui donnent sa composition validée à un mur (D243). La ligne de métré est la face intérieure
 * (réponse du 2026-10-02) : le nu intérieur ne bouge pas, le nu extérieur suit l'épaisseur totale.
 */
export function changesDeComposition(element: StudyReleveElement, couches: StudyCouche[]): StudyElementChanges {
  const propres = couchesValidees(couches);
  const total = propres.reduce((somme, couche) => somme + couche.epaisseur_cm, 0);
  const interieurFin = element.nu_interieur_fin_cm ?? element.nu_interieur_cm;
  return {
    couches: propres,
    nu_exterieur_cm: arrondi1(element.nu_interieur_cm + total),
    nu_exterieur_fin_cm: arrondi1(interieurFin + total),
  };
}

// Ce que l'étape des parois ne dessine plus : les couches une à une, remplacées par la ligne de métré (D242).
const COUCHES_DESSINEES = new Set(["mur_exterieur", "isolation", "doublage"]);

/** Les lignes de métré, sous la forme des tracés que le plan sait dessiner et viser. */
export function formesDesLignes(content: StudyContent): StudyEnvelopeShape[] {
  return (content.enveloppe.lignes_metre ?? [])
    .filter((ligne) => (ligne.points_pdf?.length ?? 0) >= 2)
    .map((ligne, rang) => ({
      id: `ligne-metre-${rang + 1}`,
      category: "ligne_metre",
      subtype: `${ligne.composant || "paroi"} · ${ligne.epaisseur_cm} cm`,
      geometry_type: "polyline",
      points_pdf: ligne.points_pdf,
      source_parcours: ligne.source_parcours,
    }));
}

/** Ce que l'étape des parois dessine et laisse viser : les lignes de métré, puis poteaux, garde-corps, menuiseries. */
export function formesEtapeParois(content: StudyContent): StudyEnvelopeShape[] {
  return [...formesDesLignes(content), ...(content.enveloppe.objets ?? []).filter((shape) => !COUCHES_DESSINEES.has(shape.category))];
}
