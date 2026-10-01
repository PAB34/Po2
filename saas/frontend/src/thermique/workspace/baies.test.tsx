import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { Baie, MenuiseriesDuProjet } from "../api";
import { BaieDeLaMenuiserie } from "./ElementPanel";
import { ChoixMenuiserie } from "./FenetreCoupe";
import { baieDeElement, mesureDeDeuxCoins, proposerComposants, provenanceBaie } from "./baies";

const baie = (reste: Partial<Baie>): Baie => ({
  composant: "M4",
  largeur_cm: 271,
  mur_rideau: false,
  morceau_a_verifier: false,
  morceaux: [{ troncon: "T22", debut_m: 77.15, fin_m: 79.86 }],
  sheet_id: 1,
  niveau: "R+1",
  hauteur_m: null,
  source: "a_lire",
  vue_id: null,
  vue: null,
  ...reste,
});

const menuiseries: MenuiseriesDuProjet = {
  composants: [
    {
      composant: "M1",
      mur_rideau: true,
      hauteur_m: null,
      a_lire: 0,
      confirmation: null,
      baies: [
        baie({
          composant: "M1",
          largeur_cm: 301,
          mur_rideau: true,
          source: "hauteur_du_local",
          morceaux: [
            { troncon: "T04", debut_m: 16.65, fin_m: 17.26 },
            { troncon: "T05", debut_m: 17.26, fin_m: 19.66 },
          ],
        }),
      ],
    },
    {
      composant: "M4",
      mur_rideau: false,
      hauteur_m: 2.15,
      a_lire: 0,
      confirmation: null,
      baies: [baie({ hauteur_m: 2.15, source: "composant", vue: "FACADE EST", vue_id: 3 }), baie({ largeur_cm: 352 })],
    },
    { composant: "M5", mur_rideau: false, hauteur_m: null, a_lire: 1, confirmation: null, baies: [baie({ composant: "M5", largeur_cm: 268 })] },
  ],
  morceaux_a_verifier: [],
};

describe("baies et hauteur des menuiseries (S5e, D193 à D200)", () => {
  it("un morceau du relevé retrouve sa baie, même réunie d'un tronçon à l'autre", () => {
    expect(baieDeElement(menuiseries, 1, { troncon: "T05", debut_m: 17.26, fin_m: 19.66 })?.largeur_cm).toBe(301);
    expect(baieDeElement(menuiseries, 2, { troncon: "T05", debut_m: 17.26, fin_m: 19.66 })).toBeNull();
  });

  it("deux coins sur une élévation tournée donnent largeur et hauteur", () => {
    const m = (0.0254 / 72) * 100;
    const mesure = mesureDeDeuxCoins([1000, 1500], [1000 + 2.15 / m, 1500 - 2.71 / m], [1, 0], 100);
    expect(mesure.largeur_m).toBeCloseTo(2.71, 3);
    expect(mesure.hauteur_m).toBeCloseTo(2.15, 3);
  });

  it("propose les composants dont une baie colle à ± 5 cm, la plus proche d'abord", () => {
    expect(proposerComposants(menuiseries, 269.5).map((p) => [p.composant, p.ecart_cm])).toEqual([
      ["M4", 1.5],
      ["M5", 1.5],
    ]);
    expect(proposerComposants(menuiseries, 120)).toEqual([]);
  });

  it("dit d'où vient la hauteur", () => {
    expect(provenanceBaie(menuiseries.composants[1].baies[0])).toBe("mesurée sur FACADE EST, pour toutes les M4");
    expect(provenanceBaie(menuiseries.composants[0].baies[0])).toMatch(/mur-rideau/);
    expect(provenanceBaie(menuiseries.composants[1].baies[1])).toBe("à lire sur une élévation");
  });

  it("la fiche d'une menuiserie montre sa baie et propose de la mesurer (D214)", () => {
    const html = renderToStaticMarkup(<BaieDeLaMenuiserie baie={menuiseries.composants[1].baies[0]} onMesurer={() => undefined} />);
    expect(html).toContain("271 cm");
    expect(html).toContain("2,15 m");
    expect(html).toContain("Mesurer de nouveau (coupes et élévations)");
    expect(renderToStaticMarkup(<BaieDeLaMenuiserie baie={menuiseries.composants[1].baies[1]} onMesurer={() => undefined} />)).toContain(
      "Mesurer sa hauteur",
    );
    const morceau = renderToStaticMarkup(<BaieDeLaMenuiserie baie={baie({ largeur_cm: 8, morceau_a_verifier: true })} />);
    expect(morceau).toContain("Morceau de 8 cm");
  });

  it("après deux coins, on choisit tout le composant ou la seule baie", () => {
    const html = renderToStaticMarkup(
      <ChoixMenuiserie largeurM={2.7} hauteurM={2.15} menuiseries={menuiseries} onChoisir={() => undefined} onAnnuler={() => undefined} />,
    );
    expect(html).toContain("Pour toutes les M4");
    expect(html).toContain("Pour cette baie seule");
    const aucune = renderToStaticMarkup(
      <ChoixMenuiserie largeurM={1.2} hauteurM={2.15} menuiseries={menuiseries} onChoisir={() => undefined} onAnnuler={() => undefined} />,
    );
    expect(aucune).toContain("Aucune baie du projet");
  });
});
