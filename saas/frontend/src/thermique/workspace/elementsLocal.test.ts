import { describe, expect, it } from "vitest";

import type { StudyContent, StudyReleveElement } from "../api";
import { appliquerEnLocal, refusDeCorrection } from "./elementsLocal";

const element = (reste: Partial<StudyReleveElement> = {}): StudyReleveElement => ({
  troncon: "T01",
  debut_m: 0,
  fin_m: 4.2,
  type: "paroi",
  composant: "P1",
  nu_exterieur_cm: 0,
  nu_interieur_cm: -44,
  a_verifier: true,
  ...reste,
});

const etude = (elements: StudyReleveElement[]): StudyContent =>
  ({ enveloppe: { releve_brut: { elements, catalogue: [], observations: [] }, objets: [] } }) as unknown as StudyContent;

const ref = { troncon: "T01", debut_m: 0, fin_m: 4.2 };
const lire = (content: StudyContent, rang = 0) => content.enveloppe.releve_brut.elements[rang];

describe("appliquer un geste sans attendre le serveur", () => {
  // D105 : un recalcul coûte 3,2 s sur le R+1 ; confirmer 92 éléments un par un ferait attendre
  // cinq minutes. L'écran applique donc le geste lui-même, à l'identique de ce que fera le serveur.

  it("confirme sans toucher à la moindre mesure", () => {
    const avant = etude([element()]);
    const apres = appliquerEnLocal(avant, { type: "element_confirmer", element: ref });
    expect(lire(apres)).toEqual({ ...element(), a_verifier: false, confirme: true });
    // L'étude d'origine n'est pas modifiée : le « Tout annuler » doit pouvoir y revenir.
    expect(lire(avant).a_verifier).toBe(true);
  });

  it("corrige en gardant la lecture d'origine de l'agent", () => {
    const apres = appliquerEnLocal(etude([element()]), {
      type: "element_corriger",
      element: ref,
      changes: { nu_interieur_cm: -39 },
    });
    expect(lire(apres).nu_interieur_cm).toBe(-39);
    expect(lire(apres).releve_origine).toEqual({ nu_interieur_cm: -44 });
    expect(lire(apres).corrige).toBe(true);
    expect(lire(apres).a_verifier).toBe(false);
  });

  it("ne remplace pas la lecture d'origine quand on corrige une correction", () => {
    const une = appliquerEnLocal(etude([element()]), {
      type: "element_corriger",
      element: ref,
      changes: { nu_interieur_cm: -39 },
    });
    const deux = appliquerEnLocal(une, {
      type: "element_corriger",
      element: ref,
      changes: { nu_interieur_cm: -35 },
    });
    expect(lire(deux).nu_interieur_cm).toBe(-35);
    expect(lire(deux).releve_origine).toEqual({ nu_interieur_cm: -44 });
  });

  it("corrige tous les porteurs quand la portée le demande, et eux seuls", () => {
    const content = etude([
      element(),
      element({ troncon: "T02" }),
      element({ troncon: "T03", composant: "M1" }),
      element({ troncon: "T04", exclu: true }),
    ]);
    const apres = appliquerEnLocal(content, {
      type: "element_corriger",
      element: ref,
      changes: { type: "menuiserie" },
      portee: "partout",
    });
    expect(apres.enveloppe.releve_brut.elements.map((item) => item.type)).toEqual([
      "menuiserie",
      "menuiserie",
      "paroi",
      "paroi",
    ]);
  });

  it("écarte avec sa raison, puis rend l'élément intact", () => {
    const ecarte = appliquerEnLocal(etude([element()]), {
      type: "element_ecarter",
      element: ref,
      motif: "trait de cotation",
    });
    expect(lire(ecarte).exclu).toBe(true);
    expect(lire(ecarte).motif_exclusion).toBe("trait de cotation");

    const revenu = appliquerEnLocal(ecarte, { type: "element_reactiver", element: ref });
    expect(lire(revenu).exclu).toBeUndefined();
    expect(lire(revenu).motif_exclusion).toBeUndefined();
  });

  it("ignore un geste qui ne vise aucun élément connu", () => {
    const avant = etude([element()]);
    const apres = appliquerEnLocal(avant, {
      type: "element_confirmer",
      element: { troncon: "T99", debut_m: 0, fin_m: 1 },
    });
    expect(apres).toBe(avant);
  });
});

describe("refuser tout de suite ce que le serveur refuserait", () => {
  it("refuse un nu intérieur au-delà du nu extérieur", () => {
    expect(refusDeCorrection(element(), { nu_interieur_cm: 10 })).toMatch("ne peut pas dépasser");
    expect(refusDeCorrection(element(), { nu_interieur_cm: -50 })).toBeNull();
  });

  it("refuse un composant vide", () => {
    expect(refusDeCorrection(element(), { composant: "   " })).toMatch("ne peut pas être vide");
  });

  it("contrôle aussi le couple de fin, pas seulement celui de début", () => {
    const avecFin = element({ nu_exterieur_fin_cm: 0, nu_interieur_fin_cm: -44 });
    expect(refusDeCorrection(avecFin, { nu_interieur_fin_cm: 12 })).toMatch("ne peut pas dépasser");
  });
});
