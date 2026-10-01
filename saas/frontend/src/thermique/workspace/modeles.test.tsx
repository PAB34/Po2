import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { MenuiseriesDuProjet, ModeleMenuiserie, StudyContent, StudyReleveElement } from "../api";
import { BaieDeLaMenuiserie, ChoixDuModele } from "./ElementPanel";
import { baieDeLElement, baiesDuNiveau, cotesDesMenuiseries, menuiseriesDeMemeLargeur, nomPropose, texteDeLaCote } from "./modeles";
import { BibliothequeModeles, ModeleDeMenuiserie } from "./ModelesMenuiseries";

const menuiserie = (debut: number, fin: number, reste: Partial<StudyReleveElement> = {}): StudyReleveElement =>
  ({ troncon: "T1", debut_m: debut, fin_m: fin, type: "menuiserie", composant: "M1", nu_exterieur_cm: 30, nu_interieur_cm: 0, ...reste }) as StudyReleveElement;

const modele: ModeleMenuiserie = {
  nom: "M1 120×215",
  largeur_cm: 120,
  hauteur_m: 2.15,
  vue_id: 3,
  vue: "FACADE EST",
  capture: false,
  horodatage: null,
  poses: 2,
};

describe("modèles de menuiserie (D219 à D222)", () => {
  it("propose un nom : composant le plus proche, puis les dimensions", () => {
    const menuiseries = { composants: [{ composant: "M4", baies: [{ largeur_cm: 121 }] }] } as unknown as MenuiseriesDuProjet;
    expect(nomPropose(1.2, 2.15, menuiseries)).toBe("M4 120×215");
    expect(nomPropose(0.8, 2.15)).toBe("M 80×215");
  });

  it("le trait du plan hérite de la cote du modèle posé, et porte son exposition (D221, D225)", () => {
    expect(texteDeLaCote(menuiserie(0, 2.4, { modele: "M1 120×215", exposition: "SO" }), [modele])).toEqual({
      texte: "M1 120×215 · 120×215 · SO",
      posee: true,
    });
    expect(texteDeLaCote(menuiserie(0, 1.21, { exposition: "nord à caler" }), [modele])).toEqual({ texte: "121 cm", posee: false });
  });

  it("une baie coupée à la jonction de deux tronçons ne fait qu'une cote et qu'un clic (D224)", () => {
    const content = {
      enveloppe: {
        objets: [
          { id: "a", category: "menuiserie_exterieure", points_pdf: [[0, 0], [60, 0]], source_parcours: { troncon: "T1", debut_m: 0, fin_m: 0.6 } },
          { id: "b", category: "menuiserie_exterieure", points_pdf: [[60, 0], [60, 40]], source_parcours: { troncon: "T2", debut_m: 0.6, fin_m: 1.2 } },
        ],
        releve_brut: {
          elements: [
            menuiserie(0, 0.6, { troncon: "T1" }),
            menuiserie(0.6, 1.2, { troncon: "T2" }),
            { ...menuiserie(1.2, 1.5, { troncon: "T2" }), type: "paroi" },
            menuiserie(1.5, 2.0, { troncon: "T2" }),
          ],
        },
      },
    } as unknown as StudyContent;
    expect(baiesDuNiveau(content).map((baie) => baie.length)).toEqual([2, 1]);
    expect(baieDeLElement(content, content.enveloppe.releve_brut.elements[1]).map((ref) => ref.troncon)).toEqual(["T1", "T2"]);
    const cotes = cotesDesMenuiseries(content, []);
    expect(cotes.map((cote) => cote.texte)).toEqual(["120 cm"]);
    expect(menuiseriesDeMemeLargeur(content, modele).map((ref) => ref.troncon)).toEqual(["T1", "T2"]);
  });

  it("retrouve les menuiseries de même largeur à ± 2 cm qui ne portent pas déjà le modèle", () => {
    const content = {
      enveloppe: {
        releve_brut: {
          elements: [
            menuiserie(0, 1.21),
            menuiserie(2, 3.19, { modele: "M1 120×215" }),
            menuiserie(4, 5.25),
            menuiserie(6, 7.2, { exclu: true }),
            { ...menuiserie(8, 9.2), type: "paroi" },
          ],
        },
      },
    } as unknown as StudyContent;
    expect(menuiseriesDeMemeLargeur(content, modele).map((ref) => ref.debut_m)).toEqual([0]);
  });

  it("la fiche de la baie annonce l'écart entre le plan et le modèle", () => {
    const html = renderToStaticMarkup(
      <BaieDeLaMenuiserie
        baie={{
          composant: "M1", modele: "M1 120×215", largeur_cm: 240, largeur_retenue_cm: 120, largeur_modele_cm: 120, ecart_modele_cm: 120,
          surface_m2: 2.58, mur_rideau: false, morceau_a_verifier: false, morceaux: [], sheet_id: 1, niveau: "R+1",
          hauteur_m: 2.15, source: "modele", vue_id: 3, vue: "FACADE EST",
        }}
      />,
    );
    expect(html).toContain("M1 120×215");
    expect(html).toContain("2,58 m²");
    expect(html).toContain("baie double");
  });

  it("le panneau de mesure propose le nom et prévient qu'un modèle existant est remplacé", () => {
    const menuiseries = { composants: [], modeles: [modele] } as unknown as MenuiseriesDuProjet;
    const html = renderToStaticMarkup(
      <ModeleDeMenuiserie largeurM={1.2} hauteurM={2.15} menuiseries={menuiseries} onEnregistrer={() => undefined} onAnnuler={() => undefined} />,
    );
    expect(html).toContain('value="M 120×215"');
    expect(html).toContain("Enregistrer le modèle et le poser");
  });

  it("la fiche d'une menuiserie choisit son modèle dans la bibliothèque (D226)", () => {
    const html = renderToStaticMarkup(
      <ChoixDuModele element={menuiserie(0, 1.2, { modele: "M1 120×215" })} modeles={[modele]} busy={false} onChoisir={() => undefined} />,
    );
    expect(html).toContain("Modèle mesuré");
    expect(html).toContain("M1 120×215 · 120×215");
    expect(html).toMatch(/<option value="M1 120×215" selected="">/);
  });

  it("la bibliothèque liste les modèles avec leurs dimensions et leurs poses", () => {
    const html = renderToStaticMarkup(
      <BibliothequeModeles token="t" projectId={1} modeles={[modele]} onPoser={() => undefined} onRetirer={() => undefined} />,
    );
    expect(html).toContain("120 × 215 cm");
    expect(html).toContain("2 posées");
  });
});
