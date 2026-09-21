import { describe, expect, it } from "vitest";

import type { Room } from "./pieces";
import { zoneKind, zoneSummary } from "./zoning";

const room = (nom: string, surface_m2: number, classe: Room["classe"] = "chauffe"): Room => ({
  id: Math.random(),
  nom,
  repere: null,
  nom_source: "lu",
  classe,
  classe_source: "propose",
  contour: [0, 0, 10, 0, 10, 10, 0, 10],
  centre: [5, 5],
  surface_m2,
  source: "auto",
});

describe("légende du zonage automatique", () => {
  it("reprend les catégories de la projection de référence", () => {
    expect(zoneKind(room("Bureau assistant 1", 10))).toBe("bureau");
    expect(zoneKind(room("Sanitaires", 7))).toBe("sanitaire");
    expect(zoneKind(room("Circulation administration", 20))).toBe("circulation");
    expect(zoneKind(room("Local équipement", 25))).toBe("equipement");
    expect(zoneKind(room("Plateau public", 300))).toBe("public");
    expect(zoneKind(room("Vide", 12, "exterieur"))).toBe("exterieur");
  });

  it("compte les zones et additionne leurs surfaces", () => {
    expect(zoneSummary([room("Bureau 1", 10), room("Salle de réunion", 20), room("Sanitaires", 5)])).toEqual([
      { kind: "bureau", count: 2, area: 30 },
      { kind: "sanitaire", count: 1, area: 5 },
    ]);
  });
});
