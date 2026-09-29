import { describe, expect, it } from "vitest";

import type { SheetNorth, StudyContent, VueCoupe } from "../api";
import { azimutDuNom, directionPdf, traitsDeFacade } from "./facades";

// Un bâtiment carré de 40 m. La feuille (0..1000, y vers le bas) et le PDF (y vers le haut) se correspondent
// par PDF = (x, 1000 − y) ; l'image du relevé fait 1000 px pour 1000 de feuille, à 10 px par mètre.
const local = {
  id: "L1",
  contour: [[300, 300], [700, 300], [700, 700], [300, 700]],
  contour_pdf: [[300, 700], [700, 700], [700, 300], [300, 300]],
};
const troncon = (id: string, origine: [number, number], direction: [number, number], normale: [number, number]) => ({
  id, origine_px: origine, direction, normale_ext: normale, local_debut_m: 0, local_fin_m: 40, debut_m: 0, fin_m: 40,
});
const content = {
  locaux: [local],
  enveloppe: {
    manifeste: {
      page_px: [1000, 1000],
      px_par_m: 10,
      troncons: [
        troncon("T1", [300, 300], [1, 0], [0, -1]), // haut de l'image
        troncon("T2", [700, 300], [0, 1], [1, 0]), // droite
        troncon("T3", [700, 700], [-1, 0], [0, 1]), // bas
        troncon("T4", [300, 700], [0, -1], [-1, 0]), // gauche
      ],
    },
  },
} as unknown as StudyContent;

const vue = (id: number, nom: string): VueCoupe =>
  ({ id, sheet_id: 9, nom, nature: "facade", cadre: [0, 0, 1, 1], haut: [0, 1] }) as VueCoupe;
const vues = [vue(1, "FACADE NORD"), vue(2, "Façade Est"), vue(3, "FACADE SUD"), vue(4, "Détail")];

describe("façades repérées sur le plan (S5e, D182)", () => {
  it("lit l'orientation écrite dans le nom", () => {
    expect(azimutDuNom("FACADE NORD")).toBe(0);
    expect(azimutDuNom("Façade Est")).toBe(90);
    expect(azimutDuNom("ÉLÉVATION SUD-OUEST")).toBe(225);
    expect(azimutDuNom("Coupe AA")).toBeNull();
  });

  it("tourne la flèche du nord dans le sens horaire", () => {
    const nord: SheetNorth = { p1: [0, 0], p2: [0, 10] } as SheetNorth;
    const est = directionPdf(nord, 90);
    expect(est[0]).toBeCloseTo(1);
    expect(est[1]).toBeCloseTo(0);
  });

  it("nord en haut de la page : la façade nord est le côté du haut", () => {
    const nord = { p1: [500, 500], p2: [500, 600] } as SheetNorth;
    const traits = traitsDeFacade(content, nord, vues);
    const parNom = (nom: string) => traits.filter((t) => t.nom === nom);
    expect(parNom("FACADE NORD").map((t) => t.points)).toEqual([[[300, 700], [700, 700]].map((p) => p.map((v) => expect.closeTo(v, 6)))]);
    expect(parNom("Façade Est")[0].points[0][0]).toBeCloseTo(700);
    expect(parNom("FACADE SUD")[0].points[0][1]).toBeCloseTo(300);
    expect(traits.every((t) => t.facade)).toBe(true);
  });

  it("plan tourné : le nord pointe vers la droite de la page, la façade nord est alors le côté droit", () => {
    const nord = { p1: [500, 500], p2: [600, 500] } as SheetNorth;
    const [nordFacade] = traitsDeFacade(content, nord, vues).filter((t) => t.nom === "FACADE NORD");
    expect(nordFacade.points[0][0]).toBeCloseTo(700);
    expect(nordFacade.points[1][0]).toBeCloseTo(700);
  });

  it("sans nord, aucune façade ne se situe", () => {
    expect(traitsDeFacade(content, null, vues)).toEqual([]);
  });
});
