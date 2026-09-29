import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { LocalHauteur, Sheet, VueCoupe } from "../api";
import { cadrageDeLaVue, hauteurEntreClics } from "./FenetreCoupe";
import { HauteurLocal, lireHauteur } from "./StudyPanel";
import { changeLocalHauteurOperation, provenanceHauteur } from "./study";

const lue: LocalHauteur = {
  hauteur_m: 2.88,
  proposee_m: 2.88,
  source: "lue",
  lectures: [{ vue: "COUPE A", hsp_m: 2.88, longueur_m: 3 }],
  alerte: null,
};
const rien = () => undefined;

describe("hauteur sous plafond d'un local (S5, D178 à D180)", () => {
  it("dit d'où vient la hauteur", () => {
    expect(provenanceHauteur(lue)).toBe("lue sur la coupe COUPE A");
    expect(provenanceHauteur({ ...lue, source: "deduite", lectures: [] })).toMatch(/aucune coupe ne traverse/);
    expect(provenanceHauteur({ ...lue, source: "double_hauteur", hauteur_m: null })).toMatch(/double hauteur/);
    expect(provenanceHauteur({ ...lue, source: "saisie", hauteur_m: 2.65 })).toBe(
      "saisie par vous (les coupes proposent 2,88 m)",
    );
  });

  it("pose ou retire la hauteur par le geste « modifier »", () => {
    expect(changeLocalHauteurOperation("piece-001", 2.7)).toEqual({ type: "modifier", id: "piece-001", hauteur_m: 2.7 });
    expect(changeLocalHauteurOperation("piece-001", null)).toEqual({
      type: "modifier",
      id: "piece-001",
      retirer_hauteur: true,
    });
  });

  it("lit une saisie à la virgule et refuse ce qui sort des bornes du serveur", () => {
    expect(lireHauteur("2,65")).toEqual({ valeur: 2.65, erreur: null });
    expect(lireHauteur(" 3.1 ")).toEqual({ valeur: 3.1, erreur: null });
    for (const faux of ["", "abc", "0,5", "40"]) {
      expect(lireHauteur(faux).valeur).toBeNull();
      expect(lireHauteur(faux).erreur).toMatch(/entre 1,50 et 15 m/);
    }
  });

  it("affiche la hauteur lue, sa provenance et le bouton de validation", () => {
    const html = renderToStaticMarkup(<HauteurLocal hauteur={lue} onHauteur={rien} />);
    expect(html).toContain("2,88 m");
    expect(html).toContain("lue sur la coupe COUPE A");
    expect(html).toContain("Valider cette hauteur");
    expect(html).not.toContain("Revenir aux coupes");
  });

  it("une hauteur saisie peut revenir à celle des coupes", () => {
    const html = renderToStaticMarkup(
      <HauteurLocal hauteur={{ ...lue, source: "saisie", hauteur_m: 2.65 }} onHauteur={rien} />,
    );
    expect(html).toContain("2,65 m");
    expect(html).toContain("Revenir aux coupes");
  });

  it("une double hauteur s'annonce sans valeur inventée", () => {
    const html = renderToStaticMarkup(
      <HauteurLocal
        hauteur={{
          ...lue,
          source: "double_hauteur",
          hauteur_m: null,
          proposee_m: null,
          lectures: [],
          alerte: "double hauteur : pas de plafond à cet étage dans la coupe",
        }}
      />,
    );
    expect(html).toContain("inconnue");
    expect(html).toContain("pas de plafond à cet étage");
  });

  it("deux clics dans une coupe tournée donnent la hauteur le long de son haut (D191)", () => {
    // PC10 : le haut de la coupe est le +x de la page ; 1/100 : 2,88 m = 81,6 points.
    const pts = 2.88 / ((0.0254 / 72) * 100);
    expect(hauteurEntreClics([1252, 1300], [1252 + pts, 1310], [1, 0], 100)).toBeCloseTo(2.88, 3);
    expect(hauteurEntreClics([1252 + pts, 1300], [1252, 1300], [1, 0], 100)).toBeCloseTo(-2.88, 3);
  });

  it("la fenêtre se cadre sur la vue", () => {
    const vue = { id: 1, sheet_id: 2, nom: "COUPE A", nature: "coupe", cadre: [882, 978, 1573, 2003], haut: [1, 0] } as VueCoupe;
    const planche = { id: 2, rotation_deg: 0, page_width_pt: 1684, page_height_pt: 2384 } as Sheet;
    const cadrage = cadrageDeLaVue(vue, planche);
    expect(cadrage.point).toEqual([1227.5, 1490.5]);
    expect(cadrage.zoom).toBeCloseTo(Math.min(1684 / 691, 2384 / 1025) * 0.9, 5);
  });

  it("propose d'ouvrir d'abord les coupes qui traversent le local", () => {
    const html = renderToStaticMarkup(
      <HauteurLocal
        hauteur={lue}
        coupes={[{ vue_id: 1, vue: "COUPE A" }, { vue_id: 2, vue: "COUPE C" }]}
        onVoirCoupe={rien}
      />,
    );
    expect(html).toContain("Voir la coupe COUPE A");
    expect(html).not.toContain("Voir la coupe COUPE C");
    const deduite = renderToStaticMarkup(
      <HauteurLocal hauteur={{ ...lue, source: "deduite", lectures: [] }} coupes={[{ vue_id: 2, vue: "COUPE C" }]} onVoirCoupe={rien} />,
    );
    expect(deduite).toContain("Voir la coupe COUPE C");
  });

  it("sans coupes lues, la hauteur déjà saisie dans l'étude s'affiche", () => {
    expect(renderToStaticMarkup(<HauteurLocal saisie={2.7} />)).toContain("2,7 m");
  });
});
