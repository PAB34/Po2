import { describe, expect, it } from "vitest";

import type { StudyContent, StudyReleveElement } from "../api";
import { changesDuPinceau, compositionDe, epaisseurTotaleCm, paroisDuComposant, retracerEntre } from "./parois";

const paroi = (debut: number, fin: number, reste: Partial<StudyReleveElement> = {}): StudyReleveElement =>
  ({
    troncon: "T01",
    debut_m: debut,
    fin_m: fin,
    type: "paroi",
    composant: "P1",
    nu_exterieur_cm: 44,
    nu_interieur_cm: 0,
    couches: [
      { nature: "mur", epaisseur_cm: 20 },
      { nature: "isolant", epaisseur_cm: 12 },
      { nature: "mur", epaisseur_cm: 12 },
    ],
    ...reste,
  }) as StudyReleveElement;

// La feuille (0–1000) est le PDF tel quel ; un tronçon horizontal de 10 m sur 1000 px de page.
const etude = (elements: StudyReleveElement[]): StudyContent =>
  ({
    locaux: [
      {
        id: "a",
        nom: "A",
        contour: [[0, 0], [1000, 0], [1000, 500], [0, 500]],
        contour_pdf: [[0, 0], [1000, 0], [1000, 500], [0, 500]],
      },
    ],
    enveloppe: {
      objets: [],
      liaisons: [],
      releve_brut: { elements },
      manifeste: {
        page_px: [1000, 1000],
        px_par_m: 100,
        troncons: [{ id: "T01", origine_px: [0, 0], direction: [1, 0], debut_m: 0, fin_m: 10, local_debut_m: 0 }],
      },
    },
  }) as unknown as StudyContent;

describe("parois comme les menuiseries (D239, D240)", () => {
  it("le pinceau prend composant, couches et nus de la paroi de référence", () => {
    const composition = compositionDe(paroi(0, 2));
    expect(composition.libelle).toBe("P1 · 44 cm");
    expect(changesDuPinceau(composition)).toMatchObject({
      composant: "P1",
      nu_exterieur_cm: 44,
      nu_interieur_cm: 0,
      nu_exterieur_fin_cm: 44,
      couches: [{ nature: "mur", epaisseur_cm: 20 }, { nature: "isolant", epaisseur_cm: 12 }, { nature: "mur", epaisseur_cm: 12 }],
    });
    expect(epaisseurTotaleCm(paroi(0, 1, { couches: [], nu_exterieur_cm: 30, nu_interieur_cm: -5 }))).toBe(35);
  });

  it("le raccourci vise les autres parois du même composant, actives", () => {
    const content = etude([paroi(0, 2), paroi(2, 4), paroi(4, 5, { composant: "P2" }), paroi(5, 6, { exclu: true })]);
    expect(paroisDuComposant(content, "P1", { troncon: "T01", debut_m: 0, fin_m: 2 }).map((ref) => ref.debut_m)).toEqual([2]);
  });

  it("retracer : deux clics le long de la façade donnent le pan, dans l'ordre", () => {
    const content = etude([paroi(0, 2)]);
    const geste = retracerEntre(content, [700, 3], [150, -2], compositionDe(paroi(0, 2)));
    expect(geste).toMatchObject({ type: "paroi_retracer", debut_m: 1.5, fin_m: 7 });
  });
});
