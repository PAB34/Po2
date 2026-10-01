import { describe, expect, it } from "vitest";

import type { HauteursDuPlan, VueCoupe } from "../api";
import { consigneDuTrait, placeDeLaCoupe, sensDuTrait } from "./PlacerCoupes";

const vue = (id: number): VueCoupe => ({ id, sheet_id: 9, nom: `COUPE ${id}`, nature: "coupe", cadre: [0, 0, 1, 1], haut: [0, 1] });

describe("tracer le trait d'une coupe à la main (D209)", () => {
  it("le regard part du côté du troisième clic", () => {
    expect(sensDuTrait([0, 0], [10, 0], [5, 3])).toEqual([-0, 1]);
    expect(sensDuTrait([0, 0], [10, 0], [5, -3])).toEqual([0, -1]);
  });

  it("guide clic par clic", () => {
    expect(consigneDuTrait({ vueId: 1, points: [] }, "C")).toContain("une extrémité");
    expect(consigneDuTrait({ vueId: 1, points: [[0, 0]] }, "C")).toContain("l'autre extrémité");
    expect(consigneDuTrait({ vueId: 1, points: [[0, 0], [1, 1]] }, "C")).toContain("côté où regarde");
  });

  it("dit si chaque coupe est placée", () => {
    const hauteurs = {
      traits: [{ nom: "COUPE 1", points: [], sens: [0, 1], vue_id: 1, manuel: true }],
      coupes: [{ trait: "COUPE 2", deduit: true, vue_id: 2, vue: "COUPE 2", vue_sheet_id: 9, alertes: [] }],
    } as unknown as HauteursDuPlan;
    expect([1, 2, 3].map((id) => placeDeLaCoupe(vue(id), hauteurs))).toEqual(["a_la_main", "situee", "non_situee"]);
  });
});
