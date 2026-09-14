import { describe, expect, it } from "vitest";

import type { PdfPoint } from "./api";
import {
  insertVertex,
  nearestEdge,
  northOnSheet,
  parseSignedNumber,
  polygonArea,
  removeVertex,
  repereOf,
  toProject,
  transferPoint,
  type ZoneEdge,
} from "./metre";
import { SnapIndex, orthogonal, snapPoint } from "./snap";

const M = 1000 / 100 / (25.4 / 72); // points PDF pour 1 m à 1/100

describe("repère commun des niveaux", () => {
  it("reporte un point d'un plan sur un autre plan calé différemment", () => {
    const rdc = repereOf({ echelle: 100, calage: { a: [100, 100], b: [100 + 10 * M, 100] } })!;
    // Même bâtiment imprimé tourné de 90° et décalé sur la planche du R+1.
    const etage = repereOf({ echelle: 100, calage: { a: [500, 200], b: [500, 200 + 10 * M] } })!;
    const coin: PdfPoint = [100 + 3 * M, 100 + 2 * M];
    const [x, y] = toProject(rdc, coin);
    expect(x).toBeCloseTo(3);
    expect(y).toBeCloseTo(2);
    const [u, v] = transferPoint(rdc, etage, coin);
    expect(u).toBeCloseTo(500 - 2 * M);
    expect(v).toBeCloseTo(200 + 3 * M);
    const [nx, ny] = northOnSheet(etage, 0);
    expect(nx).toBeCloseTo(0);
    expect(ny).toBeCloseTo(1);
    expect(repereOf({ echelle: null, calage: { a: [0, 0], b: [1, 0] } })).toBeNull();
  });
});

describe("édition des tracés", () => {
  const square: PdfPoint[] = [
    [0, 0],
    [100, 0],
    [100, 100],
    [0, 100],
  ];
  const cotes: ZoneEdge[] = [
    { donne_sur: "exterieur", composant_id: 1 },
    { donne_sur: "lnc", composant_id: null },
    { donne_sur: "sol", composant_id: null },
    { donne_sur: "mitoyen", composant_id: null },
  ];

  it("ajoute et retire un sommet en gardant les qualifications", () => {
    expect(polygonArea(square)).toBe(10000);
    const edge = nearestEdge(square, [100, 40], 5)!;
    expect(edge.index).toBe(1);
    const inserted = insertVertex(square, cotes, edge.index, edge.point);
    expect(inserted.points[2]).toEqual([100, 40]);
    expect(inserted.cotes.map((cote) => cote.donne_sur)).toEqual(["exterieur", "lnc", "lnc", "sol", "mitoyen"]);
    const removed = removeVertex(inserted.points, inserted.cotes, 2);
    expect(removed.points).toEqual(square);
    expect(removed.cotes.map((cote) => cote.donne_sur)).toEqual(["exterieur", "lnc", "sol", "mitoyen"]);
    const first = removeVertex(square, cotes, 0);
    expect(first.cotes.map((cote) => cote.donne_sur)).toEqual(["lnc", "sol", "mitoyen"]);
  });

  it("lit les nombres saisis en français", () => {
    expect(parseSignedNumber("-1,25")).toBe(-1.25);
    expect(parseSignedNumber("0")).toBe(0);
    expect(parseSignedNumber("")).toBeNull();
    expect(parseSignedNumber("abc")).toBeNull();
  });
});

describe("aimantation", () => {
  // Angle intérieur de deux faces de murs, plus un long trait oblique.
  const index = new SnapIndex([
    [0, 0, 300, 0],
    [0, 0, 0, 300],
    [50, 50, 1050, 1050],
    [200, -100, 200, 100],
  ]);

  it("préfère les sommets, puis les extrémités, les croisements et enfin les traits", () => {
    expect(snapPoint([3, 2], 6, index, [[4, 4]]).kind).toBe("sommet");
    expect(snapPoint([3, 2], 6, index, [])).toEqual({ point: [0, 0], kind: "extremite" });
    const crossing = snapPoint([197, 3], 6, index, []);
    expect(crossing.kind).toBe("intersection");
    expect(crossing.point[0]).toBeCloseTo(200);
    expect(crossing.point[1]).toBeCloseTo(0);
    const onLine = snapPoint([604, 597], 6, index, []);
    expect(onLine.kind).toBe("trait");
    expect(onLine.point[0]).toBeCloseTo(600.5);
    expect(snapPoint([600, 150], 6, index, []).kind).toBe("libre");
    expect(orthogonal([0, 0], [100, 7])).toEqual([100, 0]);
  });
});
