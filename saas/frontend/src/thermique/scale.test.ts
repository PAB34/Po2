import { describe, expect, it } from "vitest";

import { denominatorFromMeasure, distancePt, formatScale, paperPtToRealM, parseDecimal } from "./scale";

describe("échelle des planches", () => {
  // Mesuré sur le plan niveau 0 du projet d'essai : 31,82 m à 1/100.
  const lengthPt = (31.82 * 1000) / 100 / (25.4 / 72);

  it("convertit une longueur papier en mètres réels", () => {
    expect(paperPtToRealM(lengthPt, 100)).toBeCloseTo(31.82, 6);
  });

  it("retrouve l'échelle à partir d'une cote", () => {
    expect(denominatorFromMeasure(lengthPt, 31.82)).toBeCloseTo(100, 6);
  });

  it("mesure la distance entre deux points PDF", () => {
    expect(distancePt([0, 0], [3, 4])).toBe(5);
  });

  it("formate et lit les valeurs à la française", () => {
    expect(formatScale(100)).toBe("1/100");
    expect(formatScale(null)).toBe("non définie");
    expect(parseDecimal("31,82")).toBe(31.82);
    expect(parseDecimal("abc")).toBeNull();
    expect(parseDecimal("-2")).toBeNull();
  });
});
