import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { StudyContent, StudyReleveElement } from "../api";
import { EditeurComposition, IndeterminesDuNiveau } from "./ElementPanel";
import { changesDeComposition, couchesValidees, epaisseurTotaleCm, formesEtapeParois } from "./parois";

const paroi = (reste: Partial<StudyReleveElement> = {}): StudyReleveElement =>
  ({
    troncon: "T01",
    debut_m: 0,
    fin_m: 2,
    type: "paroi",
    composant: "P1",
    nu_exterieur_cm: 44,
    nu_interieur_cm: 0,
    couches: [
      { nature: "mur", epaisseur_cm: 20 },
      { nature: "isolant", epaisseur_cm: 12 },
      { nature: "mur", epaisseur_cm: 12 },
    ],
    ...reste,
  }) as StudyReleveElement;

describe("un mur = une ligne de métré qui porte une composition (D242, D243)", () => {
  it("valider une composition garde la ligne de métré (nu intérieur) et pousse le nu extérieur", () => {
    const changes = changesDeComposition(paroi({ nu_interieur_cm: -3, nu_interieur_fin_cm: -5 }), [
      { nature: "mur", epaisseur_cm: 20 },
      { nature: "isolant", epaisseur_cm: 16 },
      { nature: "doublage", epaisseur_cm: 0 },
    ]);
    expect(changes).toEqual({
      couches: [{ nature: "mur", epaisseur_cm: 20 }, { nature: "isolant", epaisseur_cm: 16 }],
      nu_exterieur_cm: 33,
      nu_exterieur_fin_cm: 31,
    });
    expect(couchesValidees([{ nature: "mur", epaisseur_cm: 13.04, presume: true }])).toEqual([{ nature: "mur", epaisseur_cm: 13 }]);
    expect(epaisseurTotaleCm(paroi())).toBe(44);
  });

  it("l'étape des parois dessine les lignes de métré à la place des couches une à une", () => {
    const content = {
      enveloppe: {
        lignes_metre: [
          { points_pdf: [[0, 0], [100, 0]], source_parcours: { troncon: "T01", debut_m: 0, fin_m: 2 }, composant: "P1", epaisseur_cm: 44, epaisseur_fin_cm: 44, longueur_m: 2 },
        ],
        objets: [
          { id: "a", category: "mur_exterieur", subtype: "", geometry_type: "polygon" },
          { id: "b", category: "isolation", subtype: "", geometry_type: "polygon" },
          { id: "c", category: "poteau", subtype: "", geometry_type: "polygon" },
          { id: "d", category: "menuiserie_exterieure", subtype: "", geometry_type: "polyline" },
        ],
      },
    } as unknown as StudyContent;
    const formes = formesEtapeParois(content);
    expect(formes.map((forme) => forme.category)).toEqual(["ligne_metre", "poteau", "menuiserie_exterieure"]);
    expect(formes[0].subtype).toBe("P1 · 44 cm");
  });

  it("la fiche d'un mur montre ses couches, valider et supprimer", () => {
    const html = renderToStaticMarkup(
      <EditeurComposition element={paroi()} autres={3} busy={false} onValider={() => undefined} onSupprimer={() => undefined} />,
    );
    expect(html).toContain("44 cm");
    expect(html).toContain("à valider");
    expect(html).toContain("Appliquer aussi aux 3 autres murs P1");
    expect(html).toContain("Valider la composition");
    expect(html).toContain("Supprimer ce mur");
    expect(renderToStaticMarkup(
      <EditeurComposition element={paroi({ corrige: true })} autres={0} busy={false} onValider={() => undefined} onSupprimer={() => undefined} />,
    )).toContain("validée");
  });
});

describe("les indéterminés se suppriment, un à un ou tous d'un geste (D254)", () => {
  const content = (elements: StudyReleveElement[]) =>
    ({ enveloppe: { releve_brut: { elements, catalogue: [], observations: [] } } }) as unknown as StudyContent;

  it("annonce leur nombre et leur longueur avant de proposer de tous les supprimer", () => {
    const html = renderToStaticMarkup(
      <IndeterminesDuNiveau
        content={content([
          paroi({ type: "indetermine", debut_m: 165.95, fin_m: 167.5 }),
          paroi({ type: "indetermine", debut_m: 10, fin_m: 10.4 }),
          paroi({ type: "indetermine", debut_m: 20, fin_m: 21, exclu: true }),
          paroi(),
        ])}
        busy={false}
        onSupprimer={() => undefined}
      />,
    );
    expect(html).toContain("2 éléments indéterminés");
    expect(html).toContain("1,95 m");
    expect(html).toContain("Supprimer tous les indéterminés");
  });

  it("ne montre rien quand il n'en reste aucun", () => {
    const html = renderToStaticMarkup(
      <IndeterminesDuNiveau content={content([paroi()])} busy={false} onSupprimer={() => undefined} />,
    );
    expect(html).toBe("");
  });
});
