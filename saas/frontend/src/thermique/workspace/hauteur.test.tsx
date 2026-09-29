import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { LocalHauteur } from "../api";
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

  it("sans coupes lues, la hauteur déjà saisie dans l'étude s'affiche", () => {
    expect(renderToStaticMarkup(<HauteurLocal saisie={2.7} />)).toContain("2,7 m");
  });
});
