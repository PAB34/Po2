import { describe, expect, it } from "vitest";

import type { StudyContent, StudyReleveElement } from "../api";
import { appliquerEnLocal } from "./elementsLocal";
import { appliquerExtremite, boutLePlusProche, extremitesDuMur, gesteExtremite } from "./murs";

// Même repère que le test serveur : page de 1000 px, 10 px par mètre, tronçon T01 le long du haut de la page,
// extérieur vers le haut ; points PDF = points de la feuille (le local donne un repère identité).
const mur = (reste: Partial<StudyReleveElement> = {}): StudyReleveElement =>
  ({
    troncon: "T01",
    debut_m: 0,
    fin_m: 50,
    type: "paroi",
    composant: "P1",
    nu_exterieur_cm: 0,
    nu_interieur_cm: -50,
    ...reste,
  }) as StudyReleveElement;

const carre: [number, number][] = [[0, 0], [1000, 0], [1000, 1000], [0, 1000]];
const etude = (elements: StudyReleveElement[], lignes: unknown[] = []): StudyContent =>
  ({
    locaux: [{ contour: carre, contour_pdf: carre }],
    enveloppe: {
      manifeste: {
        page_px: [1000, 1000],
        px_par_m: 10,
        troncons: [{ id: "T01", origine_px: [0, 0], direction: [1, 0], normale_ext: [0, -1], debut_m: 0, local_debut_m: 0 }],
      },
      releve_brut: { elements, catalogue: [], observations: [] },
      objets: [],
      lignes_metre: lignes,
    },
  }) as unknown as StudyContent;

const proche = (point: [number, number] | undefined, attendu: [number, number]) => {
  expect(point?.[0]).toBeCloseTo(attendu[0], 6);
  expect(point?.[1]).toBeCloseTo(attendu[1], 6);
};

describe("poignées de la ligne de métré d'un mur (D249)", () => {
  it("les extrémités sont sur la face intérieure, au début et à la fin du mur", () => {
    const bouts = extremitesDuMur(etude([mur()]), mur());
    proche(bouts?.debut, [0, 5]);
    proche(bouts?.fin, [500, 5]);
  });

  it("un point lâché n'importe où devient la borne et la face intérieure de ce bout", () => {
    const content = etude([mur()]);
    const geste = gesteExtremite(content, mur(), "fin", [425, 8]);
    expect(geste).toEqual({
      type: "paroi_extremite",
      element: { troncon: "T01", debut_m: 0, fin_m: 50 },
      extremite: "fin",
      abscisse_m: 42.5,
      nu_interieur_cm: -80,
    });
    expect(gesteExtremite(content, mur(), "debut", [600, 5])).toMatch("trop court");
  });

  it("l'écran applique le geste comme le serveur et redessine la ligne aussitôt", () => {
    const content = etude([mur()], [{ points_pdf: [[0, 5], [500, 5]], source_parcours: { troncon: "T01", debut_m: 0, fin_m: 50 } }]);
    const geste = gesteExtremite(content, mur(), "fin", [425, 8]);
    if (typeof geste === "string") throw new Error(geste);
    const { content: apres, ref } = appliquerExtremite(content, geste);
    expect(ref).toEqual({ troncon: "T01", debut_m: 0, fin_m: 42.5 });
    const deplace = apres.enveloppe.releve_brut.elements[0];
    // Épaisseur de 50 cm gardée au bout déplacé ; le début ne bouge pas.
    expect([deplace.nu_interieur_fin_cm, deplace.nu_exterieur_fin_cm]).toEqual([-80, -30]);
    expect([deplace.nu_interieur_cm, deplace.nu_exterieur_cm]).toEqual([-50, 0]);
    expect(deplace.corrige).toBe(true);
    const lignes = apres.enveloppe.lignes_metre ?? [];
    expect(lignes).toHaveLength(1);
    proche(lignes[0].points_pdf?.[1], [425, 8]);
    // Rejouer le geste (annuler / rétablir) donne la même étude.
    expect(appliquerEnLocal(content, geste).enveloppe.releve_brut.elements[0]).toEqual(deplace);
  });

  it("l'aimant accroche le bout d'un autre mur, jamais un bout du mur lui-même", () => {
    const content = etude(
      [mur(), mur({ debut_m: 60, fin_m: 80 })],
      [
        { points_pdf: [[0, 5], [500, 5]], source_parcours: { troncon: "T01", debut_m: 0, fin_m: 50 } },
        { points_pdf: [[600, 5], [800, 5]], source_parcours: { troncon: "T01", debut_m: 60, fin_m: 80 } },
      ],
    );
    expect(boutLePlusProche(content, mur(), [597, 6], 5)).toEqual([600, 5]);
    expect(boutLePlusProche(content, mur(), [502, 5], 5)).toBeNull();
  });
});
