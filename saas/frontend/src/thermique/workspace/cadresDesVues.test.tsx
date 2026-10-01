import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { VueCoupe } from "../api";
import { ListeDesVues, cadreDeDeuxCoins, etatDeLaVue, hautDeLaVue } from "./CadresDesVues";

const vue = (reste: Partial<VueCoupe> = {}): VueCoupe =>
  ({ id: 1, sheet_id: 3, nom: "COUPE A", nature: "coupe", cadre: [50, 1900, 1650, 2360], haut: [1, 0], pieces: [], ...reste }) as VueCoupe;

describe("les cadres des vues (D205)", () => {
  it("deux coins dans n'importe quel ordre donnent le même cadre", () => {
    expect(cadreDeDeuxCoins([1573, 978], [882, 2003])).toEqual([882, 978, 1573, 2003]);
  });

  it("le haut de la vue se lit comme un côté de la page", () => {
    expect(hautDeLaVue([1, 0])).toBe("droite");
    expect(hautDeLaVue([0, -1])).toBe("bas");
    expect(hautDeLaVue([0, 1])).toBe("haut");
  });

  it("une coupe sans pièce signale un cadre à vérifier, une coupe corrigée attend sa relecture", () => {
    expect(etatDeLaVue(vue())).toContain("cadre à vérifier");
    expect(etatDeLaVue(vue({ a_relire: true }))).toContain("à relire");
    expect(etatDeLaVue(vue({ pieces: [{}, {}] }))).toBe("2 pièces lues");
    expect(etatDeLaVue(vue({ nature: "facade" }))).toBe("façade");
  });

  it("la fiche dit quel coin cliquer pendant qu'on redessine", () => {
    const rendu = (premier: [number, number] | null) =>
      renderToStaticMarkup(
        <ListeDesVues
          vues={[vue()]}
          choisie={1}
          enCours={{ vueId: 1, premier }}
          busy={false}
          onChoisir={() => {}}
          onRedessiner={() => {}}
          onCorriger={() => {}}
          onSupprimer={() => {}}
        />,
      );
    expect(rendu(null)).toContain("Cliquez un coin");
    expect(rendu([1, 1])).toContain("Cliquez le coin opposé");
  });
});
