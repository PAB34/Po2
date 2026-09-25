import { describe, expect, it } from "vitest";

import type { Sheet, Study, StudyContent, StudyReleveElement } from "../api";
import { avancement, etapeCourante, parcours, paroisDuNiveau, pontsDuNiveau } from "./parcours";

const element = (reste: Partial<StudyReleveElement> = {}): StudyReleveElement => ({
  troncon: "T01",
  debut_m: 0,
  fin_m: 4.2,
  type: "paroi",
  composant: "P1",
  nu_exterieur_cm: 0,
  nu_interieur_cm: -44,
  a_verifier: false,
  ...reste,
});

const planche = (reste: Partial<Sheet> = {}): Sheet =>
  ({ id: 1, status: "prete", nord: { angle_deg: 0 }, ...reste }) as unknown as Sheet;

const etude = (elements: StudyReleveElement[], locaux: string[] = ["Bureau"], valides: string[] = []): Study =>
  ({
    content: {
      locaux: locaux.map((nom, rang) => ({ id: `L${rang}`, nom })),
      enveloppe: { releve_brut: { elements, catalogue: [], observations: [] }, objets: [], liaisons: [] },
    } as unknown as StudyContent,
    local_states: Object.fromEntries(valides.map((id) => [id, { status: "valide" }])),
  }) as unknown as Study;

describe("séparer les deux lots d'éléments", () => {
  it("met les liaisons d'un côté et ce qui a un tracé de l'autre", () => {
    const content = etude([
      element(),
      element({ troncon: "T02", type: "angle_sortant" }),
      element({ troncon: "T03", type: "menuiserie" }),
      element({ troncon: "T04", type: "about_refend" }),
    ]).content;
    expect(pontsDuNiveau(content).map((item) => item.troncon)).toEqual(["T02", "T04"]);
    expect(paroisDuNiveau(content).map((item) => item.troncon)).toEqual(["T01", "T03"]);
  });
});

describe("ce qu'il reste à juger", () => {
  it("ne compte que ce dont l'agent a douté et que personne n'a tranché", () => {
    expect(
      avancement([
        element({ a_verifier: true }),
        element({ a_verifier: true, confirme: true }),
        element({ a_verifier: true, corrige: true }),
        element({ a_verifier: true, exclu: true }),
        element(),
      ]),
    ).toEqual({ total: 5, restants: 1, ecartes: 1 });
  });

  it("un relevé sans doute est un lot déjà fini : on n'impose pas 150 clics sur les parois", () => {
    expect(avancement([element(), element(), element()]).restants).toBe(0);
  });

  it("en régime exigeant, la confiance de l'agent ne vaut pas validation : chaque pont passe", () => {
    expect(avancement([element(), element(), element()], true).restants).toBe(3);
    expect(avancement([element({ confirme: true }), element({ exclu: true }), element()], true)).toEqual({
      total: 3,
      restants: 1,
      ecartes: 1,
    });
  });
});

describe("le parcours du niveau", () => {
  it("attend l'analyse avant de parler des locaux", () => {
    const etapes = parcours(planche(), undefined);
    expect(etapes.map((item) => item.id)).toEqual([
      "planche",
      "analyse",
      "locaux",
      "enveloppe",
      "ponts",
      "hauteurs",
    ]);
    expect(etapes[1].etat).toBe("en_cours");
    expect(etapes[2].etat).toBe("attente");
    // L'entrée proposée est l'analyse : la planche est prête, le relevé manque.
    expect(etapeCourante(etapes)).toBe("analyse");
  });

  it("réclame le nord tant qu'il n'est pas posé : sans lui, aucune orientation (D84)", () => {
    const etapes = parcours(planche({ nord: null }), undefined);
    expect(etapes[0].etat).toBe("en_cours");
    expect(etapes[0].reste).toContain("nord");
  });

  it("compte les ponts à juger séparément des parois", () => {
    const etapes = parcours(
      planche(),
      etude([
        element({ a_verifier: true }),
        element({ troncon: "T02", type: "angle_sortant", a_verifier: true }),
        element({ troncon: "T03", type: "angle_rentrant", a_verifier: true }),
        element({ troncon: "T04", type: "about_refend", a_verifier: true, confirme: true }),
      ]),
    );
    const enveloppe = etapes.find((item) => item.id === "enveloppe");
    const ponts = etapes.find((item) => item.id === "ponts");
    expect(enveloppe?.reste).toBe("1 élément à vérifier");
    // Deux ponts douteux et un déjà confirmé : c'est bien deux qui restent.
    expect(ponts?.reste).toBe("2 ponts à juger sur 3");
    expect(ponts?.etat).toBe("en_cours");
  });

  it("annonce les écartés une fois le lot fini, pour qu'un geste ne se perde pas", () => {
    const etapes = parcours(
      planche(),
      etude([element({ troncon: "T02", type: "angle_sortant", a_verifier: true, exclu: true })]),
    );
    const ponts = etapes.find((item) => item.id === "ponts");
    expect(ponts?.etat).toBe("fait");
    expect(ponts?.reste).toBe("1 jugés, 1 écarté");
  });

  it("l'étape des ponts n'allume que les ponts, celle des parois allume les tracés et les cotes (Q6)", () => {
    const etapes = parcours(planche(), etude([element()]));
    expect(etapes.find((item) => item.id === "ponts")?.calques).toEqual({
      metres: false,
      ponts: true,
      elements: false,
      toutesCotes: false,
    });
    expect(etapes.find((item) => item.id === "enveloppe")?.calques).toEqual({
      metres: true,
      ponts: false,
      elements: true,
      toutesCotes: false,
    });
  });

  it("propose la première étape inachevée, sans jamais bloquer les suivantes (D109)", () => {
    const etapes = parcours(planche(), etude([element()], ["Bureau", "Couloir"], ["L0"]));
    // Un local sur deux validé : c'est là qu'on entre.
    expect(etapeCourante(etapes)).toBe("locaux");
    expect(etapes.every((item) => item.etat !== "attente" || item.id === "hauteurs")).toBe(true);
  });

  it("tout étant fini, on se pose sur les ponts et non sur les hauteurs, qui n'existent pas encore", () => {
    const etapes = parcours(planche(), etude([element()], ["Bureau"], ["L0"]));
    expect(etapeCourante(etapes)).toBe("ponts");
  });
});
