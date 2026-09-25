import { describe, expect, it } from "vitest";

import type { StudyContent, StudyOperation } from "../api";
import { annulerOperation, cibleEditable, rejouerOperations, retablirOperation } from "./elementsHistory";

const ref = { troncon: "T01", debut_m: 0, fin_m: 4.2 };
const confirmer: StudyOperation = { type: "element_confirmer", element: ref };
const ecarter: StudyOperation = { type: "element_ecarter", element: ref, motif: "cotation" };
const base = {
  enveloppe: {
    releve_brut: {
      elements: [{ ...ref, type: "paroi", composant: "P1", a_verifier: true }],
      catalogue: [],
      observations: [],
    },
    objets: [],
  },
} as unknown as StudyContent;

describe("historique des corrections d'éléments", () => {
  it("annule la dernière opération et reconstruit le contenu restant", () => {
    const history = annulerOperation({ operations: [confirmer, ecarter], annulees: [] });
    expect(history.operations).toEqual([confirmer]);
    expect(history.annulees).toEqual([ecarter]);
    const element = rejouerOperations(base, history.operations).enveloppe.releve_brut.elements[0];
    expect(element.confirme).toBe(true);
    expect(element.exclu).toBeUndefined();
  });

  it("rétablit exactement l'opération annulée", () => {
    const annule = annulerOperation({ operations: [confirmer, ecarter], annulees: [] });
    const retabli = retablirOperation(annule);
    expect(retabli.operations).toEqual([confirmer, ecarter]);
    expect(retabli.annulees).toEqual([]);
    expect(rejouerOperations(base, retabli.operations).enveloppe.releve_brut.elements[0]).toMatchObject({
      exclu: true,
      motif_exclusion: "cotation",
    });
  });

  it("ne casse rien quand les piles sont vides", () => {
    const vide = { operations: [], annulees: [] };
    expect(annulerOperation(vide)).toBe(vide);
    expect(retablirOperation(vide)).toBe(vide);
  });

  it("une nouvelle action après annulation coupe la branche de rétablissement", () => {
    const annule = annulerOperation({ operations: [confirmer, ecarter], annulees: [] });
    const nouvelleBranche = { operations: [...annule.operations, ecarter], annulees: [] };
    expect(nouvelleBranche.annulees).toEqual([]);
  });
});

describe("protection de la saisie native", () => {
  it("reconnaît les champs et le contenu éditable", () => {
    const cible = (editable: boolean) => ({ matches: () => editable }) as unknown as EventTarget;
    expect(cibleEditable(cible(true))).toBe(true);
    expect(cibleEditable(cible(false))).toBe(false);
    expect(cibleEditable(null)).toBe(false);
  });
});
