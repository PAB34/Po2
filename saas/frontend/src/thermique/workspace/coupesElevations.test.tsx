import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { StudyReleveElement, VueCoupe } from "../api";
import { AffecterAussiA } from "./ElementPanel";
import { ChoixDeLaVue } from "./FenetreCoupe";

const vue = (id: number, nom: string, nature: VueCoupe["nature"]): VueCoupe =>
  ({ id, sheet_id: 1, nom, nature, cadre: [0, 0, 1, 1], haut: [0, 1] }) as VueCoupe;

const baie = (reste: Partial<StudyReleveElement> = {}): StudyReleveElement =>
  ({ troncon: "T1", debut_m: 0, fin_m: 1.2, type: "menuiserie", composant: "M1", nu_exterieur_cm: 30, nu_interieur_cm: 0, ...reste }) as StudyReleveElement;

describe("coupes et élévations dans une seule fenêtre (D214)", () => {
  it("la liste range les vues en coupes et élévations", () => {
    const html = renderToStaticMarkup(
      <ChoixDeLaVue vues={[vue(1, "COUPE A", "coupe"), vue(2, "FACADE NORD", "facade")]} vueId={2} onChoisir={() => undefined} />,
    );
    expect(html).toContain('label="Coupes"');
    expect(html).toContain('label="Élévations"');
    expect(html).toContain("FACADE NORD");
  });
});

describe("affecter une menuiserie à d'autres pièces (D217)", () => {
  it("dit avec qui la baie est partagée, et à quelle part", () => {
    const html = renderToStaticMarkup(
      <AffecterAussiA element={baie({ pieces_en_plus: ["Bureau A"] })} pieces={["Bureau A", "Bureau B"]} piece="Bureau B" busy={false} onAffecter={() => undefined} />,
    );
    expect(html).toContain("Partagée avec Bureau A : 1/2");
    expect(html).toContain("Affecter aussi à");
  });

  it("sans partage, seul le bouton s'affiche", () => {
    const html = renderToStaticMarkup(
      <AffecterAussiA element={baie()} pieces={["Bureau A"]} piece="Bureau A" busy={false} onAffecter={() => undefined} />,
    );
    expect(html).not.toContain("Partagée");
  });
});
