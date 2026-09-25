import { describe, expect, it } from "vitest";

import type { StudyRoom } from "../api";
import {
  changeLocalNatureOperation,
  NATURE_COLORS,
  NATURE_LABELS,
  otherLocalNatures,
  roomAt,
  sortedStudyRooms,
} from "./study";

const room = (id: string, nature: StudyRoom["nature"]): StudyRoom => ({
  id,
  nom: id,
  nature,
  contour: [],
  contour_pdf: [],
  limites: [],
  surface_m2: 1,
  fiche: { piece: id, local: nature, surface_m2: 1, perimetre_m: 4, cotes: [] },
  synthese: {},
  demandes: [],
});

describe("locaux de l'étude", () => {
  it("range les chauffés, circulations, non chauffés puis gaines en gardant l'ordre du plan", () => {
    const rooms = [
      room("G1", "gaine_technique"),
      room("N1", "non_chauffe"),
      room("C1", "circulation"),
      room("H1", "chauffe"),
      room("H2", "chauffe"),
      room("C2", "circulation"),
    ];
    expect(sortedStudyRooms(rooms).map((item) => item.id)).toEqual(["H1", "H2", "C1", "C2", "N1", "G1"]);
    expect(rooms.map((item) => item.id)).toEqual(["G1", "N1", "C1", "H1", "H2", "C2"]);
  });

  it("donne à la gaine son libellé et sa couleur propres", () => {
    expect(NATURE_LABELS.gaine_technique).toBe("Gaine technique");
    expect(NATURE_COLORS.gaine_technique).toBe("#7c3aed");
    expect(NATURE_COLORS.gaine_technique).not.toBe(NATURE_COLORS.non_chauffe);
  });

  it("fabrique un geste de nature seul et omet la nature courante du clic droit", () => {
    expect(changeLocalNatureOperation("piece-001", "gaine_technique")).toEqual({
      type: "modifier",
      id: "piece-001",
      nature: "gaine_technique",
    });
    expect(otherLocalNatures("non_chauffe")).toEqual(["chauffe", "circulation", "gaine_technique"]);
  });
});

const carre = (id: string, x0: number, y0: number, cote: number): StudyRoom => ({
  ...room(id, "chauffe"),
  contour_pdf: [
    [x0, y0],
    [x0 + cote, y0],
    [x0 + cote, y0 + cote],
    [x0, y0 + cote],
  ],
});

describe("le local sous un point du plan", () => {
  it("trouve le local visé et ne rend rien dans le vide", () => {
    const locaux = [carre("A", 0, 0, 10), carre("B", 20, 0, 10)];
    expect(roomAt(locaux, [5, 5])?.id).toBe("A");
    expect(roomAt(locaux, [25, 5])?.id).toBe("B");
    expect(roomAt(locaux, [15, 5])).toBeNull();
  });

  it("choisit le plus petit quand deux locaux se recouvrent", () => {
    // Le cas réel du R+1 : un petit local posé dans un grand plateau ouvert.
    const locaux = [carre("plateau", 0, 0, 100), carre("bureau", 10, 10, 5)];
    expect(roomAt(locaux, [12, 12])?.id).toBe("bureau");
    expect(roomAt(locaux, [50, 50])?.id).toBe("plateau");
  });

  it("ignore un local sans contour exploitable", () => {
    expect(roomAt([room("vide", "chauffe")], [1, 1])).toBeNull();
  });
});
