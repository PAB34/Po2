import { describe, expect, it } from "vitest";

import { avisSurLaHauteur, avisSurLaMenuiserie, rectangleDeMenuiserie, segmentDeHauteur } from "./mesuresVue";

// À 1/100, 72 pt de la page font 2,54 m.
const PT_PAR_M = 72 / 2.54;

describe("mesures visibles dans une coupe ou une façade (D211)", () => {
  it("le rectangle de la baie suit les axes de la vue et porte ses deux cotes", () => {
    const [largeur, hauteur] = rectangleDeMenuiserie([0, 0], [2.4 * PT_PAR_M, 2.15 * PT_PAR_M], [0, 1], 100);
    expect(largeur.label).toBe("2,40 m");
    expect(hauteur.label).toBe("2,15 m");
    // Vue couchée (haut à droite de la page) : la largeur se compte à la verticale de la page.
    const couchee = rectangleDeMenuiserie([0, 0], [2.15 * PT_PAR_M, -2.4 * PT_PAR_M], [1, 0], 100);
    expect(couchee.map((s) => s.label).filter(Boolean)).toEqual(["2,40 m", "2,15 m"]);
  });

  it("la hauteur se compte le long du haut de la vue, même si le clic dévie", () => {
    expect(segmentDeHauteur([0, 0], [30, 2.7 * PT_PAR_M], [0, 1], 100).label).toBe("2,70 m");
  });

  it("une hauteur impossible bloque, une inhabituelle se signale", () => {
    expect(avisSurLaHauteur(0.9)?.bloquant).toBe(true);
    expect(avisSurLaHauteur(7.5)?.bloquant).toBe(false);
    expect(avisSurLaHauteur(2.7)).toBeNull();
  });

  it("une baie de 2 cm de large est suspecte", () => {
    expect(avisSurLaMenuiserie(0.02, 1.83)).toContain("suspecte");
    expect(avisSurLaMenuiserie(1.2, 2.15)).toBeNull();
  });
});
