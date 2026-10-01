import { describe, expect, it } from "vitest";

import { coteEcran, pageDuCoteEcran, rotationALEndroit } from "./orientation";

// Rasters de pdfium : page droite (y de la page vers le haut de l'écran) et page tournée d'un quart horaire
// (le haut de la page part à droite de l'écran, sa droite en bas).
const DROITE = [2, 0, 0, -2, 0, 4000];
const QUART = [0, 2, 2, 0, 0, 0];

describe("haut d'une vue vu de l'écran (D207, D208)", () => {
  it("dit où le haut de la page apparaît à l'écran", () => {
    expect(coteEcran([0, 1], DROITE)).toBe("haut");
    expect(coteEcran([0, 1], QUART)).toBe("droite");
    expect(coteEcran([1, 0], QUART)).toBe("bas");
  });

  it("traduit le côté choisi à l'écran en côté de la page", () => {
    // Test du 2026-10-01 : planche tournée, le thermicien voit le haut du dessin à droite.
    expect(pageDuCoteEcran("droite", QUART)).toBe("haut");
    expect(pageDuCoteEcran("bas", QUART)).toBe("droite");
    expect(pageDuCoteEcran("gauche", DROITE)).toBe("gauche");
    expect(pageDuCoteEcran("haut", DROITE)).toBe("haut");
  });

  it("trouve la rotation qui met la vue à l'endroit", () => {
    expect(rotationALEndroit([0, 1], DROITE, 0)).toBe(0);
    expect(rotationALEndroit([1, 0], DROITE, 0)).toBe(270);
    expect(rotationALEndroit([0, 1], QUART, 90)).toBe(0);
    expect(rotationALEndroit([-1, 0], QUART, 90)).toBe(90);
    expect(rotationALEndroit([0, -1], DROITE, 0)).toBe(180);
  });
});
