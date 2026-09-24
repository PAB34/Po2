import { describe, expect, it } from "vitest";

import type { StudyContent, StudyEnvelopeShape, StudyReleveElement, StudyRoom } from "../api";
import {
  compterElements,
  ecartsAvecLAgent,
  elementAt,
  elementsDuLocal,
  epaisseurCm,
  formesDuLocal,
  longueurM,
  memeElement,
  porteursDuComposant,
  refDeForme,
  trouverElement,
} from "./elements";

const element = (reste: Partial<StudyReleveElement> = {}): StudyReleveElement => ({
  troncon: "T01",
  debut_m: 0,
  fin_m: 4.2,
  type: "paroi",
  composant: "P1",
  nu_exterieur_cm: 0,
  nu_interieur_cm: -44,
  confiance: 0.9,
  indice: "bande grise 44 cm",
  a_verifier: false,
  ...reste,
});

const forme = (reste: Partial<StudyEnvelopeShape> = {}): StudyEnvelopeShape => ({
  id: "env-001",
  category: "mur_exterieur",
  subtype: "P1 · voile",
  geometry_type: "polygon",
  points_pdf: [
    [0, 0],
    [40, 0],
    [40, 4],
    [0, 4],
  ],
  source_parcours: { troncon: "T01", debut_m: 0, fin_m: 4.2, piece: "Bureau" },
  ...reste,
});

const etude = (elements: StudyReleveElement[], objets: StudyEnvelopeShape[] = []): StudyContent =>
  ({
    enveloppe: { releve_brut: { elements, catalogue: [], observations: [] }, objets },
  }) as unknown as StudyContent;

const local = (nom: string): StudyRoom => ({ nom }) as StudyRoom;

describe("désigner un élément relevé", () => {
  it("remonte du tracé au relevé par la position, la clé que les deux portent", () => {
    const shape = forme();
    expect(refDeForme(shape)).toEqual({ troncon: "T01", debut_m: 0, fin_m: 4.2 });
    expect(refDeForme(forme({ source_parcours: { piece: "Bureau" } }))).toBeNull();
  });

  it("ne confond pas deux éléments du même tronçon", () => {
    const premier = { troncon: "T01", debut_m: 0, fin_m: 4.2 };
    const second = { troncon: "T01", debut_m: 4.2, fin_m: 9 };
    expect(memeElement(premier, { ...premier })).toBe(true);
    expect(memeElement(premier, second)).toBe(false);
    expect(memeElement(premier, null)).toBe(false);
  });

  it("retrouve l'élément visé dans le relevé", () => {
    const content = etude([element(), element({ debut_m: 4.2, fin_m: 9 })]);
    expect(trouverElement(content, { troncon: "T01", debut_m: 4.2, fin_m: 9 })?.fin_m).toBe(9);
    expect(trouverElement(content, { troncon: "T99", debut_m: 0, fin_m: 1 })).toBeNull();
    expect(trouverElement(content, null)).toBeNull();
  });
});

describe("attraper un élément sur le plan", () => {
  // Le test se fait ici et non par pointer-events : la couche doit rester traversante pour que le plan
  // se déplace toujours (D79).
  it("attrape une forme pleine sous le curseur", () => {
    expect(elementAt([forme()], [20, 2], 1)).toEqual({ troncon: "T01", debut_m: 0, fin_m: 4.2 });
    expect(elementAt([forme()], [20, 40], 1)).toBeNull();
  });

  it("attrape un trait à la tolérance près", () => {
    const trait = forme({
      geometry_type: "polyline",
      points_pdf: [
        [0, 0],
        [40, 0],
      ],
      source_parcours: { troncon: "T02", debut_m: 0, fin_m: 4, piece: "Bureau" },
    });
    expect(elementAt([trait], [20, 1.5], 2)).toEqual({ troncon: "T02", debut_m: 0, fin_m: 4 });
    expect(elementAt([trait], [20, 5], 2)).toBeNull();
  });

  it("préfère la plus petite forme : une menuiserie posée sur un mur reste attrapable", () => {
    const mur = forme();
    const menuiserie = forme({
      id: "env-002",
      points_pdf: [
        [18, 0],
        [24, 0],
        [24, 4],
        [18, 4],
      ],
      source_parcours: { troncon: "T01", debut_m: 1.8, fin_m: 2.4, piece: "Bureau" },
    });
    expect(elementAt([mur, menuiserie], [21, 2], 1)).toEqual({ troncon: "T01", debut_m: 1.8, fin_m: 2.4 });
  });
});

describe("ce que porte un local", () => {
  it("ne retient que les éléments dont une forme touche ce local", () => {
    const ici = element();
    const ailleurs = element({ troncon: "T09", debut_m: 0, fin_m: 3 });
    const content = etude(
      [ici, ailleurs],
      [forme(), forme({ id: "env-002", source_parcours: { troncon: "T09", debut_m: 0, fin_m: 3, piece: "Couloir" } })],
    );
    expect(elementsDuLocal(content, local("Bureau")).map((item) => item.troncon)).toEqual(["T01"]);
    expect(elementsDuLocal(content, null)).toEqual([]);
    expect(formesDuLocal(content, local("Couloir")).map((item) => item.id)).toEqual(["env-002"]);
  });

  it("ne compte qu'une fois un élément dessiné en plusieurs couches", () => {
    // Une paroi en couches donne plusieurs formes : 289 formes pour 227 éléments sur le vrai R+1.
    const content = etude(
      [element()],
      [forme(), forme({ id: "env-002" }), forme({ id: "env-003" })],
    );
    expect(elementsDuLocal(content, local("Bureau"))).toHaveLength(1);
  });
});

describe("compteurs et mesures", () => {
  it("compte ce qui reste à regarder, sans les écartés", () => {
    const content = etude([
      element({ a_verifier: true }),
      element({ troncon: "T02", a_verifier: true, exclu: true }),
      element({ troncon: "T03", confirme: true }),
      element({ troncon: "T04", corrige: true }),
    ]);
    expect(compterElements(content)).toEqual({ total: 4, aVerifier: 1, ecartes: 1, traites: 2 });
  });

  it("ne compte pas un porteur écarté avant d'annoncer la portée d'une correction", () => {
    const content = etude([
      element(),
      element({ troncon: "T02" }),
      element({ troncon: "T03", exclu: true }),
      element({ troncon: "T04", composant: "M1" }),
    ]);
    expect(porteursDuComposant(content, "P1")).toBe(2);
    expect(porteursDuComposant(content, null)).toBe(0);
  });

  it("donne l'épaisseur et la longueur telles qu'on les vérifie d'un coup d'œil", () => {
    expect(epaisseurCm(element())).toBe(44);
    expect(longueurM(element())).toBe(4.2);
  });
});

describe("comparer la lecture de l'agent et la correction", () => {
  it("ne montre que ce qui a vraiment changé", () => {
    const corrige = element({
      nu_interieur_cm: -39,
      type: "paroi",
      releve_origine: { nu_interieur_cm: -44, type: "paroi" },
    });
    expect(ecartsAvecLAgent(corrige)).toEqual([{ champ: "nu_interieur_cm", avant: -44, apres: -39 }]);
  });

  it("ne montre rien tant que l'agent n'a pas été corrigé", () => {
    expect(ecartsAvecLAgent(element())).toEqual([]);
  });
});
