import { describe, expect, it } from "vitest";

import type { Sheet } from "../api";
import { groupSheets, levelRank, referenceSheet } from "./levels";

const sheet = (id: number, nature: Sheet["nature"], level: string | null, label = `P${id}`): Sheet => ({
  id,
  project_id: 1,
  document_id: 1,
  page_index: 0,
  label,
  nature,
  nature_suggested: null,
  level_label: level,
  scale_denominator: 100,
  scale_source: "declaree",
  rotation_deg: 0,
  page_width_pt: 100,
  page_height_pt: 100,
  status: "prete",
  calibration: null,
  nord: null,
});

describe("levelRank", () => {
  it("reconnaît les libellés courants", () => {
    expect(levelRank("RDC")).toBe(0);
    expect(levelRank("Niveau 0")).toBe(0);
    expect(levelRank("R+1")).toBe(1);
    expect(levelRank("Niveau 2")).toBe(2);
    expect(levelRank("1er étage")).toBe(1);
    expect(levelRank("Sous-sol")).toBe(-1);
    expect(levelRank("R-2")).toBe(-2);
    expect(levelRank("Toiture")).toBe(99);
    expect(levelRank("Mezzanine")).toBeNull();
  });
});

describe("groupSheets et referenceSheet", () => {
  const sheets = [
    sheet(1, "plan", "R+1"),
    sheet(2, "coupe", null, "Coupe AA"),
    sheet(3, "plan", "Toiture"),
    sheet(4, "plan", "RDC"),
    sheet(5, "plan", "Sous-sol"),
    sheet(6, "facade", null, "Façade nord"),
    sheet(7, null, null, "Plan masse"),
  ];

  it("range les niveaux du plus bas au plus haut et le reste par type", () => {
    const groups = groupSheets(sheets);
    expect(groups.levels.map((item) => item.id)).toEqual([5, 4, 1, 3]);
    expect(groups.sections.map((item) => item.id)).toEqual([2]);
    expect(groups.elevations.map((item) => item.id)).toEqual([6]);
    expect(groups.others.map((item) => item.id)).toEqual([7]);
  });

  it("ouvre le RDC par défaut, ou le plan choisi", () => {
    expect(referenceSheet(sheets, null)?.id).toBe(4);
    expect(referenceSheet(sheets, 1)?.id).toBe(1);
    expect(referenceSheet(sheets, 999)?.id).toBe(4);
    expect(referenceSheet([sheet(8, "plan", "R+1")], null)?.id).toBe(8);
  });
});
