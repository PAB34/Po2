import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { StudyContent, StudyParoiLocal, StudyRoom } from "../api";
import { appliquerEnLocal } from "./elementsLocal";
import { FicheParoi, ParoisDesLocaux } from "./ParoisDesLocaux";
import { avancementParois, gesteComposition, paroiVisee, paroisSemblables, trouverParoi } from "./paroisLocaux";

const P1 = { composant: "P1", couches: [{ nature: "mur", epaisseur_cm: 20 }, { nature: "isolant", epaisseur_cm: 12 }], epaisseur_cm: 32 };

const paroi = (rang: number, reste: Partial<StudyParoiLocal> = {}): StudyParoiLocal => ({
  rang,
  adjacence: "exterieur",
  deperditif: true,
  longueur_m: 4,
  epaisseur_cm: 32,
  orientation: "N",
  trace: [[0, 0], [40, 0]],
  trace_pdf: [[0, 0], [40, 0]],
  proposition: P1,
  composition: null,
  ...reste,
});

const local = (id: string, nom: string, parois: StudyParoiLocal[]): StudyRoom =>
  ({ id, nom, fiche: { parois } }) as unknown as StudyRoom;

const etude = (locaux: StudyRoom[]): StudyContent => ({ locaux, enveloppe: { releve_brut: { elements: [] } } }) as unknown as StudyContent;

describe("les parois des locaux portent la composition (option C, D260 à D262)", () => {
  const bureau = local("L1", "Bureau", [
    paroi(0),
    paroi(1, { trace: [[40, 0], [40, 30]], trace_pdf: [[40, 0], [40, 30]], composition: { id: "c1", ...P1 } }),
    paroi(2, { adjacence: "local", deperditif: false, trace: [[40, 30], [0, 30]], trace_pdf: [[40, 30], [0, 30]] }),
  ]);
  const salle = local("L2", "Salle", [paroi(0, { trace: [[100, 0], [140, 0]], trace_pdf: [[100, 0], [140, 0]] })]);
  const content = etude([bureau, salle]);

  it("compte seulement les parois déperditives sans composition validée", () => {
    expect(avancementParois(content)).toEqual({ total: 3, restants: 2 });
  });

  it("un clic près d'une paroi déperditive l'ouvre ; une cloison entre locaux chauffés ne s'attrape pas", () => {
    expect(paroiVisee(content, [20, 1], 2)).toEqual({ local: "L1", rang: 0 });
    expect(paroiVisee(content, [20, 30], 2)).toBeNull();
    expect(trouverParoi(content, { local: "L2", rang: 0 })?.room.nom).toBe("Salle");
  });

  it("« appliquer aussi » vise les parois à composer qui ont la même proposition", () => {
    const semblables = paroisSemblables(content, bureau, bureau.fiche.parois![0]);
    expect(semblables.map(({ room, paroi: p }) => `${room.id}:${p.rang}`)).toEqual(["L2:0"]);
  });

  it("la composition validée se voit aussitôt, avant le recalcul du serveur", () => {
    const geste = gesteComposition(bureau, bureau.fiche.parois![0], [{ nature: "mur", epaisseur_cm: 25 }], "P1");
    expect(geste).toEqual({ type: "paroi_composer", local: "L1", trace: [[0, 0], [40, 0]], composant: "P1", couches: [{ nature: "mur", epaisseur_cm: 25 }] });
    const apres = appliquerEnLocal(content, geste);
    expect(trouverParoi(apres, { local: "L1", rang: 0 })?.paroi.composition?.epaisseur_cm).toBe(25);
    expect(avancementParois(apres).restants).toBe(1);
  });

  it("le plan colore chaque paroi selon son état, et la fiche dit ce qu'il y a derrière", () => {
    const plan = renderToStaticMarkup(
      <svg>
        <ParoisDesLocaux content={content} choisie={{ local: "L1", rang: 0 }} toScreen={(p) => [p[0] * 4, p[1] * 4]} />
      </svg>,
    );
    expect(plan).toContain("is-proposee is-choisie");
    expect(plan).toContain("is-validee");
    expect(plan).toContain("P1 · 32 cm");
    const fiche = renderToStaticMarkup(
      <FicheParoi content={content} room={bureau} paroi={bureau.fiche.parois![0]} busy={false} onValider={() => undefined} onRetour={() => undefined} />,
    );
    expect(fiche).toContain("l&#x27;extérieur");
    expect(fiche).toContain("Proposition tirée du relevé");
    expect(fiche).toContain("Appliquer aussi aux 1 autres murs P1");
    expect(fiche).not.toContain("Supprimer ce mur");
  });
});

describe("une paroi vitrée se traite aux menuiseries", () => {
  it("elle ne compte pas parmi les parois à composer et se signale comme vitrée", () => {
    const vitree = paroi(0, { proposition: null, vitree: true });
    const content = etude([local("L1", "Hall", [vitree, paroi(1, { proposition: null })])]);
    expect(avancementParois(content)).toEqual({ total: 1, restants: 1 });
    const plan = renderToStaticMarkup(
      <svg>
        <ParoisDesLocaux content={content} choisie={null} toScreen={(p) => [p[0] * 4, p[1] * 4]} />
      </svg>,
    );
    expect(plan).toContain("is-vitree");
    expect(plan).toContain("is-vide");
  });
});
