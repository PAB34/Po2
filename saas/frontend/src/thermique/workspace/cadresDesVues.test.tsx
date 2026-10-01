import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { VueCoupe } from "../api";
import { ListeDesVues, cadreDeDeuxCoins, etatDeLaVue, hautDeLaVue, modelesDeLaVue } from "./CadresDesVues";

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

  it("l'état d'une vue dit sa nature et ses menuiseries mesurées (D230, D232)", () => {
    expect(etatDeLaVue(vue())).toBe("coupe");
    expect(etatDeLaVue(vue({ nature: "facade" }))).toBe("élévation");
    const mesuree = vue({
      nature: "facade",
      menuiseries: [
        { modele: "M1 120×215", hauteur_m: 2.15, coins: [[0, 0], [10, 10]] },
        { modele: "M1 120×215", hauteur_m: 2.2, coins: [[0, 0], [11, 11]] },
        { modele: "M2 90×215", hauteur_m: 2.15, coins: [[20, 0], [30, 10]] },
        { composant: "M4", largeur_cm: null, hauteur_m: 2.15 },
      ],
    });
    expect(etatDeLaVue(mesuree)).toBe("élévation · 2 menuiseries mesurées");
    expect(modelesDeLaVue(mesuree).map((m) => [m.nom, m.coins[1][0]])).toEqual([["M1 120×215", 11], ["M2 90×215", 30]]);
  });

  it("une vue se crée : le bouton, puis le formulaire après les deux coins (D231)", () => {
    const rendu = (nouvelle: number[] | null) =>
      renderToStaticMarkup(
        <ListeDesVues
          vues={[]}
          choisie={null}
          enCours={null}
          busy={false}
          onChoisir={() => {}}
          onRedessiner={() => {}}
          onCorriger={() => {}}
          onSupprimer={() => {}}
          nouvelle={nouvelle}
          onAjouter={() => {}}
          onCreer={() => {}}
        />,
      );
    expect(rendu(null)).toContain("Ajouter une vue");
    expect(rendu([0, 0, 100, 100])).toContain("Créer la vue");
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
