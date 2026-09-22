import { describe, expect, it } from "vitest";

import type { StudyRoom } from "../api";
import { sortedStudyRooms } from "./study";

const room = (id: string, nature: StudyRoom["nature"]): StudyRoom => ({
  id,
  nom: id,
  nature,
  contour: [],
  contour_pdf: [],
  surface_m2: 1,
  fiche: { piece: id, local: nature, surface_m2: 1, perimetre_m: 4, cotes: [] },
  synthese: {},
  demandes: [],
});

describe("locaux de l'étude", () => {
  it("range les chauffés, puis les circulations, puis les non chauffés en gardant l'ordre du plan", () => {
    const rooms = [
      room("N1", "non_chauffe"),
      room("C1", "circulation"),
      room("H1", "chauffe"),
      room("H2", "chauffe"),
      room("C2", "circulation"),
    ];
    expect(sortedStudyRooms(rooms).map((item) => item.id)).toEqual(["H1", "H2", "C1", "C2", "N1"]);
    expect(rooms.map((item) => item.id)).toEqual(["N1", "C1", "H1", "H2", "C2"]);
  });
});
