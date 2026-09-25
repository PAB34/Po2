import { describe, expect, it } from "vitest";

import type { PdfPoint, StudyRoom } from "../api";
import {
  contourChanged,
  draftForNewRoom,
  draftFromRoom,
  freeSides,
  insertVertex,
  moveVertex,
  nearestSide,
  nearestVertex,
  removeVertex,
  removeVerticesInLasso,
  straightenSide,
  verticesInLasso,
} from "./edition";

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

describe("supprimer plusieurs sommets d'un coup, au lasso", () => {
  // Une dentelle de sommets au droit d'alcôves : c'est le cas réel qui a motivé le geste.
  const dentelle: PdfPoint[] = [
    [0, 0],
    [10, 0],
    [10, 2],
    [20, 2],
    [20, 0],
    [30, 0],
    [30, 2],
    [40, 2],
    [40, 0],
    [50, 0],
    [50, 50],
    [0, 50],
  ];

  it("retire tous les sommets entourés et laisse le contour passer tout droit", () => {
    // Un lasso grossier autour de la dentelle : la main ne trace jamais un rectangle parfait.
    const { contour, removed } = removeVerticesInLasso(dentelle, [
      [5, -2],
      [25, -1],
      [45, -2],
      [46, 1],
      [45, 4],
      [25, 3],
      [5, 4],
      [4, 1],
    ]);
    expect(removed).toBe(8);
    expect(contour).toEqual([
      [0, 0],
      [50, 0],
      [50, 50],
      [0, 50],
    ]);
  });

  it("ne touche à rien si le lasso n'entoure personne", () => {
    const { contour, removed } = removeVerticesInLasso(dentelle, [
      [100, 100],
      [110, 100],
      [110, 110],
      [100, 110],
    ]);
    expect(removed).toBe(0);
    expect(contour).toBe(dentelle);
  });

  it("refuse de descendre sous le triangle : un local doit rester fermé", () => {
    const triangle: PdfPoint[] = [
      [0, 0],
      [10, 0],
      [0, 10],
    ];
    const { contour, removed } = removeVerticesInLasso(triangle, [
      [-1, -1],
      [11, -1],
      [11, 11],
      [-1, 11],
    ]);
    expect(removed).toBe(0);
    expect(contour).toBe(triangle);
  });

  it("désigne les sommets entourés, et ignore un tracé trop court pour enfermer quoi que ce soit", () => {
    expect(verticesInLasso(dentelle, [[9, -1], [21, -1], [21, 3], [9, 3]])).toEqual([1, 2, 3, 4]);
    expect(verticesInLasso(dentelle, [[9, -1], [21, -1]])).toEqual([]);
  });
});

describe("redresser un côté", () => {
  it("retire les sommets intermédiaires d'une suite de segments presque alignés", () => {
    // Un bord droit lu en cinq petits segments, avec un décrochement franc au bout.
    const contour: PdfPoint[] = [
      [0, 0],
      [10, 0.2],
      [20, -0.1],
      [30, 0.3],
      [40, 0],
      [40, 40],
      [0, 40],
    ];
    const { contour: droit, removed } = straightenSide(contour, 0);
    expect(removed).toBe(3);
    expect(droit).toEqual([
      [0, 0],
      [40, 0],
      [40, 40],
      [0, 40],
    ]);
  });

  it("ne touche pas à un côté déjà droit", () => {
    const { contour, removed } = straightenSide(carre, 0);
    expect(removed).toBe(0);
    expect(contour).toBe(carre);
  });

  it("commence un nouveau local exactement au point du clic droit", () => {
    const draft = draftForNewRoom([42, 84]);
    expect(draft).toMatchObject({ roomId: "", mode: "ajouter", contour: [[42, 84]], nature: "chauffe" });
  });

  it("reconnaît un même cap de part et d'autre de -180° / +180°", () => {
    const contour: PdfPoint[] = [
      [30, 0],
      [20, 0.2],
      [10, -0.2],
      [0, 0],
      [0, 20],
      [30, 20],
    ];
    const { contour: droit, removed } = straightenSide(contour, 0);
    expect(removed).toBe(2);
    expect(droit).toEqual([
      [30, 0],
      [0, 0],
      [0, 20],
      [30, 20],
    ]);
  });
});
