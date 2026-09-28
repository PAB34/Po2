import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { StudyContent, StudyEnvelopeShape, StudyReleveElement, StudyRoom } from "../api";
import { elementsDuLocal, faitPartieDe, parentDeForme, viserSurLePlan } from "./elements";
import { StudyMetrics } from "./StudyMetrics";

// Une fenêtre du relevé, de 0 à 3 m sur T01, dessinée en deux morceaux parce que le local derrière change
// à 2,2 m — le cas de la capture : une menuiserie qui se lisait comme deux (retour d'usage M2).
const fenetre: StudyReleveElement = {
  troncon: "T01",
  debut_m: 0,
  fin_m: 3,
  type: "menuiserie",
  composant: "M1",
  nu_exterieur_cm: -3,
  nu_interieur_cm: -35,
};
const morceau = (debut: number, fin: number, piece: string, x0: number, x1: number): StudyEnvelopeShape =>
  ({
    id: `m-${debut}`,
    category: "menuiserie_exterieure",
    subtype: "fenêtre",
    geometry_type: "polyline",
    points_pdf: [
      [x0, 0],
      [x1, 0],
    ],
    source_parcours: { troncon: "T01", debut_m: debut, fin_m: fin, piece },
  }) as unknown as StudyEnvelopeShape;
const morceaux = [morceau(0, 2.2, "Bureau", 0, 220), morceau(2.2, 3, "Couloir", 220, 300)];
const locaux = [
  { id: "L1", nom: "Bureau", contour_pdf: [[0, 0], [220, 0], [220, 200], [0, 200]], fiche: { cotes: [] } },
  { id: "L2", nom: "Couloir", contour_pdf: [[220, 0], [300, 0], [300, 200], [220, 200]], fiche: { cotes: [] } },
] as unknown as StudyRoom[];
const etude = {
  locaux,
  enveloppe: { releve_brut: { elements: [fenetre] }, objets: morceaux, liaisons: [] },
} as unknown as StudyContent;
const ref = { troncon: "T01", debut_m: 0, fin_m: 3 };

describe("un élément dessiné en morceaux reste un seul élément (M2)", () => {
  it("chaque morceau renvoie à l'élément entier du relevé", () => {
    expect(parentDeForme(etude, morceaux[1])).toBe(fenetre);
    expect(faitPartieDe(ref, { troncon: "T01", debut_m: 2.2, fin_m: 3 })).toBe(true);
    expect(faitPartieDe(ref, { troncon: "T02", debut_m: 2.2, fin_m: 3 })).toBe(false);
  });

  it("cliquer le petit morceau désigne la fenêtre entière, dans le local du morceau", () => {
    const vise = viserSurLePlan(etude, locaux, [260, 0], { element: 3, pont: 3 });
    expect(vise?.ref).toEqual(ref);
    expect(vise?.room?.nom).toBe("Couloir");
  });

  it("elle est listée dans les deux locaux qu'elle longe", () => {
    expect(elementsDuLocal(etude, locaux[0])).toEqual([fenetre]);
    expect(elementsDuLocal(etude, locaux[1])).toEqual([fenetre]);
  });

  it("désignée, ses deux morceaux s'allument ; à l'étape des parois, les menuiseries sont épaissies (M1)", () => {
    const html = renderToStaticMarkup(
      <svg>
        <StudyMetrics
          rooms={locaux}
          selected={null}
          shapes={morceaux}
          bridges={[]}
          show={{ metres: false, ponts: false, elements: true, toutesCotes: false }}
          toScreen={(point) => point}
          selectedElement={ref}
          accentMenuiseries
        />
      </svg>,
    );
    expect(html.match(/th-metric-element is-selected/g)).toHaveLength(2);
    expect(html).toContain("th-metrics--parois");
    expect(html).toContain("is-menuiserie");
  });
});
