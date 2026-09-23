import { describe, expect, it } from "vitest";

import type { PdfPoint, StudyRoom } from "../api";
import { contourChanged, draftFromRoom, freeSides, insertVertex, moveVertex, nearestSide, nearestVertex, removeVertex } from "./edition";

const carre: PdfPoint[] = [
  [0, 0],
  [100, 0],
  [100, 100],
  [0, 100],
];

const local = (): StudyRoom => ({
  id: "piece-001",
  nom: "Bureau",
  nature: "chauffe",
  contour: [],
  contour_pdf: carre.map((point) => [...point] as PdfPoint),
  limites: ["exterieur", "paroi", "convention", "convention"],
  surface_m2: 10,
  fiche: { piece: "Bureau", local: "chauffe", surface_m2: 10, perimetre_m: 40, cotes: [] },
  synthese: {},
  demandes: [],
});

describe("édition d'un contour", () => {
  it("attrape le sommet le plus proche et ignore un clic trop loin", () => {
    expect(nearestVertex(carre, [98, 3], 10)).toBe(1);
    expect(nearestVertex(carre, [50, 50], 10)).toBeNull();
  });

  it("trouve le côté sous le curseur", () => {
    expect(nearestSide(carre, [50, 1], 5)).toBe(0);
    expect(nearestSide(carre, [99, 50], 5)).toBe(1);
    expect(nearestSide(carre, [50, 50], 5)).toBeNull();
  });

  it("ajoute un sommet sur le côté visé", () => {
    const suite = insertVertex(carre, [50, 0], 5);
    expect(suite).toHaveLength(5);
    expect(suite[1]).toEqual([50, 0]);
  });

  it("déplace un sommet sans toucher aux autres", () => {
    const suite = moveVertex(carre, 2, [120, 120]);
    expect(suite[2]).toEqual([120, 120]);
    expect(suite[0]).toEqual([0, 0]);
  });

  it("refuse de descendre sous le triangle", () => {
    const triangle: PdfPoint[] = [
      [0, 0],
      [10, 0],
      [0, 10],
    ];
    expect(removeVertex(triangle, 1)).toHaveLength(3);
    expect(removeVertex(carre, 1)).toHaveLength(3);
  });

  it("part du contour du local et voit ce qui a bougé", () => {
    const room = local();
    const draft = draftFromRoom(room);
    expect(draft.roomId).toBe("piece-001");
    expect(contourChanged(room, draft.contour)).toBe(false);
    expect(contourChanged(room, moveVertex(draft.contour, 0, [5, 5]))).toBe(true);
  });

  it("compte les côtés qui ne suivent aucune paroi lue", () => {
    expect(freeSides(local())).toBe(2);
  });
});
