import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { HauteursDuPlan } from "../api";
import { traitAt, TraitsDeCoupe, traitsCliquables } from "./TraitsDeCoupe";

const hauteurs = {
  sheet_id: 1,
  locaux: {},
  coupes: [
    { trait: "A", deduit: false, vue_id: 11, vue: "COUPE A", vue_sheet_id: 5, alertes: [] },
    { trait: "COUPE C", deduit: true, vue_id: 12, vue: "COUPE C", vue_sheet_id: 6, alertes: [] },
  ],
  traits_sans_vue: ["B"],
  traits: [
    { nom: "A", points: [[1144.5, 763], [1144.5, 1906]], sens: [-1, 0] },
    { nom: "B", points: [[280, 1251], [1453, 1251]], sens: [0, -1] },
    { nom: "COUPE C", points: [[837.6, 900], [837.6, 1800]], sens: [1, 0], deduit: true, vue_id: 12 },
  ],
} as HauteursDuPlan;

describe("traits de coupe sur le plan (S5, D171)", () => {
  it("relevés ou déduits, seuls ceux qui ouvrent une coupe sont cliquables", () => {
    const traits = traitsCliquables(hauteurs);
    expect(traits.map((t) => [t.nom, t.vueId, t.deduit])).toEqual([
      ["A", 11, false],
      ["COUPE C", 12, true],
    ]);
  });

  it("un clic près du trait l'attrape, le plus proche l'emporte", () => {
    const traits = traitsCliquables(hauteurs);
    expect(traitAt(traits, [1150, 1300], 10)?.nom).toBe("A");
    expect(traitAt(traits, [840, 1300], 10)?.nom).toBe("COUPE C");
    expect(traitAt(traits, [1000, 1300], 10)).toBeNull();
  });

  it("un trait déduit se dessine en tirets, avec son nom", () => {
    const html = renderToStaticMarkup(
      <svg>
        <TraitsDeCoupe traits={traitsCliquables(hauteurs)} toScreen={(p) => [p[0] / 2, p[1] / 2]} />
      </svg>,
    );
    expect(html).toContain("is-deduit");
    expect(html).toContain("situé d&#x27;après la coupe");
    expect(html).toContain(">A<");
  });

  it("sans hauteurs lues, rien à montrer", () => {
    expect(traitsCliquables(undefined)).toEqual([]);
  });
});
