import { describe, expect, it } from "vitest";

import type { StudyContent } from "../api";
import { appliquerEnLocal } from "./elementsLocal";
import { preparerAjout, repereFeuille, versFeuille } from "./pontsAjoutes";

// La feuille (0–1000) est le PDF à l'échelle 2, décalé de (10, 20) : de quoi vérifier que la
// correspondance se retrouve depuis les contours des locaux, sans connaître la matrice du rendu.
const versPdf = ([x, y]: [number, number]): [number, number] => [(x - 10) / 2, (y - 20) / 2];
const contour: [number, number][] = [
  [0, 60],
  [1000, 60],
  [1000, 500],
  [0, 500],
];

const etude = (): StudyContent =>
  ({
    locaux: [{ id: "L1", nom: "Bureau", contour, contour_pdf: contour.map(versPdf) }],
    enveloppe: {
      manifeste: {
        page_px: [1000, 1000],
        px_par_m: 10,
        troncons: [{ id: "T01", origine_px: [0, 0], direction: [1, 0], debut_m: 0, fin_m: 100, local_debut_m: 0 }],
      },
      releve_brut: { elements: [], catalogue: [], observations: [] },
      objets: [],
      liaisons: [],
    },
  }) as unknown as StudyContent;

describe("poser un pont sans attendre le serveur (P5, D164)", () => {
  it("retrouve le passage PDF → feuille depuis les contours des locaux", () => {
    const repere = repereFeuille(etude());
    expect(repere).not.toBeNull();
    const [x, y] = versFeuille(repere!, versPdf([420, 200]));
    expect(x).toBeCloseTo(420, 6);
    expect(y).toBeCloseTo(200, 6);
  });

  it("situe le pont comme le serveur : 420 px sur un tronçon de 100 m en 1000 px donnent 42 m", () => {
    expect(preparerAjout(etude(), versPdf([420, 200]), "angle_sortant")).toMatchObject({
      type: "pont_ajouter",
      troncon: "T01",
      abscisse_m: 42,
    });
  });

  it("le pont apparaît aussitôt, jugé, dans son local, et un second au même endroit reste distinct", () => {
    const premier = preparerAjout(etude(), versPdf([420, 200]), "angle_sortant")!;
    const apres = appliquerEnLocal(etude(), premier);
    const liaison = apres.enveloppe.liaisons?.[0];
    expect(liaison).toMatchObject({ piece: "Bureau", ajoute: true, confirme: true, abscisse_m: 42 });
    expect(apres.enveloppe.releve_brut.elements[0]).toMatchObject({ troncon: "T01", debut_m: 42, ajoute: true });
    expect(preparerAjout(apres, versPdf([420, 200]), "angle_sortant")?.abscisse_m).toBe(42.001);
  });

  it("un niveau sans enveloppe relevée ne peut pas situer de pont", () => {
    const vide = etude();
    (vide.enveloppe as unknown as { manifeste: { troncons: unknown[] } }).manifeste.troncons = [];
    expect(preparerAjout(vide, [10, 10], "angle_sortant")).toBeNull();
  });
});
