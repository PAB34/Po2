import { describe, expect, it } from "vitest";

import type { HauteursDuPlan, Sheet, Study, StudyContent, StudyReleveElement, VueCoupe } from "../api";
import { avancement, etapeCourante, parcours, paroisDuNiveau, pontsDuNiveau, vueDeLEtape } from "./parcours";

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
      "menuiseries",
      "ponts",
    ]);
    expect(etapes.map((item) => item.titre).slice(2)).toEqual(["Locaux et hauteur", "Parois", "Menuiseries", "Ponts thermiques"]);
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

  it("l'étape des menuiseries compte celles sans modèle, murs-rideaux à part (D227)", () => {
    const menuiserie = (debut: number, reste: Partial<StudyReleveElement> = {}) =>
      element({ type: "menuiserie", debut_m: debut, fin_m: debut + 1, composant: "M1", ...reste });
    const etapes = parcours(
      planche(),
      etude([
        menuiserie(0, { modele: "M1 100×215" }),
        menuiserie(3),
        menuiserie(6, { menuiserie_type: "mur-rideau" }),
        element({ troncon: "T09", a_verifier: true }),
      ]),
    );
    const menuiseries = etapes.find((item) => item.id === "menuiseries");
    expect(menuiseries).toMatchObject({ reste: "1 menuiserie sans modèle sur 2", etat: "en_cours" });
    expect(vueDeLEtape("menuiseries")).toMatchObject({ famille: "menuiseries", clic: "elements", cotes: false });
    expect(vueDeLEtape("enveloppe").famille).toBe("parois");
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
    // Option C (D262) : l'étape Parois compte les parois des locaux ; cette étude n'en a aucune.
    expect(enveloppe?.reste).toBe("aucune paroi à composer");
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
      metres: false,
      ponts: false,
      elements: false,
      toutesCotes: false,
    });
  });

  it("propose la première étape inachevée, sans jamais bloquer les suivantes (D109)", () => {
    const etapes = parcours(planche(), etude([element()], ["Bureau", "Couloir"], ["L0"]));
    // Un local sur deux validé : c'est là qu'on entre.
    expect(etapeCourante(etapes)).toBe("locaux");
    expect(etapes.every((item) => item.etat !== "attente" || item.id === "hauteurs")).toBe(true);
  });

  it("un local sans hauteur garde l'étape des locaux ouverte ; tout étant fini, on se pose sur les ponts (D213)", () => {
    // D243 : le mur doit avoir sa composition validée pour que l'étape des parois soit finie.
    const study = etude([element({ confirme: true })], ["Bureau"], ["L0"]);
    const sans = parcours(planche(), study);
    expect(etapeCourante(sans)).toBe("locaux");
    expect(sans[2].reste).toContain("hauteur à mesurer");
    const hauteurs = {
      locaux: Object.fromEntries(study.content.locaux.map((room) => [room.id, { hauteur_m: 2.7 }])),
    } as unknown as HauteursDuPlan;
    expect(etapeCourante(parcours(planche(), study, [], hauteurs))).toBe("ponts");
  });
});

describe("le parcours d'une planche de coupes ou de façades (S5)", () => {
  const vue = (reste: Partial<VueCoupe> = {}): VueCoupe =>
    ({ id: 7, sheet_id: 1, nom: "FACADE EST", nature: "facade", cadre: [0, 0, 1, 1], haut: [0, 1], ...reste }) as VueCoupe;

  it("une élévation à l'échelle est prête sans nord : il se pose sur les plans de niveau", () => {
    const etapes = parcours(planche({ nature: "facade", nord: null }), undefined);
    expect(etapes.map((item) => item.id)).toEqual(["planche", "lecture", "hauteurs"]);
    expect(etapes[0].etat).toBe("fait");
    expect(etapes[0].reste).not.toContain("nord");
    expect(etapes[1]).toMatchObject({ titre: "Vues", reste: "« Ajouter une vue » : deux clics sur la planche" });
    expect(etapeCourante(etapes)).toBe("lecture");
  });

  it("façades lues puis menuiseries mesurées", () => {
    const lue = parcours(planche({ nature: "facade" }), undefined, [vue(), vue({ id: 8, nom: "Détail", nature: "detail" })]);
    expect(lue[1]).toMatchObject({ etat: "fait", reste: "1 vue cadrée" });
    expect(lue[2].reste).toContain("Coupes et élévations");
    const mesuree = parcours(planche({ nature: "facade" }), undefined, [
      vue({ menuiseries: [{ composant: "M4", largeur_cm: null, hauteur_m: 2.15 }] }),
    ]);
    expect(mesuree[2]).toMatchObject({ etat: "fait", reste: "1 menuiserie mesurée" });
  });

  it("une planche de coupes compte ses étages confirmés, et ignore les vues d'autres planches", () => {
    const coupe = vue({ nom: "COUPE A", nature: "coupe", corrections: [{ sol: 1, plafond: 2, hauteur_m: 2.88 }] });
    const etapes = parcours(planche({ nature: "coupe" }), undefined, [coupe, vue({ id: 9, sheet_id: 2, nature: "coupe" })]);
    expect(etapes[1].reste).toBe("1 vue cadrée");
    expect(etapes[2]).toMatchObject({ titre: "Hauteurs des locaux", etat: "fait", reste: "1 étage confirmé" });
  });
});
