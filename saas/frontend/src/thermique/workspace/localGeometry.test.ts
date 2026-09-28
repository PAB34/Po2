import { describe, expect, it } from "vitest";

import type { StudyContent } from "../api";
import { appliquerGeometrieLocale, rejouerGeometrieLocale } from "./localGeometry";

const content = {
  locaux: [
    { id: "piece-001", nom: "Bureau", nature: "chauffe", contour_pdf: [[0, 0], [10, 0], [0, 10]] },
    { id: "piece-002", nom: "Réserve", nature: "non_chauffe", contour_pdf: [[20, 0], [30, 0], [20, 10]] },
  ],
} as unknown as StudyContent;

describe("aperçu local des modifications géométriques", () => {
  it("affiche immédiatement le contour recadré sans modifier la source", () => {
    const contour = [[1, 1], [12, 1], [1, 12]] as [number, number][];
    const shown = appliquerGeometrieLocale(content, { type: "modifier", id: "piece-001", contour_pdf: contour });
    expect(shown.locaux[0].contour_pdf).toEqual(contour);
    expect(content.locaux[0].contour_pdf).toEqual([[0, 0], [10, 0], [0, 10]]);
  });

  it("masque une suppression puis rejoue le lot dans l'ordre", () => {
    const shown = rejouerGeometrieLocale(content, [
      { type: "modifier", id: "piece-002", nom: "Stock" },
      { type: "local_supprimer", id: "piece-001" },
    ]);
    expect(shown.locaux.map((room) => [room.id, room.nom])).toEqual([["piece-002", "Stock"]]);
  });
});
