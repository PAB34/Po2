import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { GuideCalage, etapesDuCalage } from "./GuideCalage";

describe("le guide du calage", () => {
  it("désigne l'étape en cours parmi les quatre clics", () => {
    const etapes = etapesDuCalage("RDC", "R+1", "bleu", 1);
    expect(etapes.map((etape) => etape.etat)).toEqual(["faite", "en_cours", "a_venir", "a_venir"]);
    expect(etapes[1].texte).toContain("Repère A sur le R+1");
    expect(etapes[2].texte).toContain("le plus loin possible de A");
  });

  it("dit à quoi servent les points avant de les demander", () => {
    const html = renderToStaticMarkup(<GuideCalage voisin="RDC" plan="R+1" couleur="bleu" clics={0} busy={false} />);
    expect(html).toContain("Superposer le RDC au R+1");
    expect(html).toContain("deux points du bâtiment");
    expect(html).toContain("calque bleu");
  });
});
