import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { StudyContent, StudyParoiLocal, StudyRoom } from "../api";
import { appliquerEnLocal } from "./elementsLocal";
import { FicheParoi, ParoisDesLocaux } from "./ParoisDesLocaux";
import { avancementParois, coupureProche, gesteComposition, paroiVisee, paroisSemblables, surfacesParoi, trouverParoi } from "./paroisLocaux";

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

describe("couper une paroi par des points (D264 à D266)", () => {
  const compose = paroi(0, { trace: [[0, 0], [400, 0]], trace_pdf: [[0, 0], [40, 0]], longueur_m: 40, composition: { id: "c1", ...P1 } });
  const content = etude([local("L1", "Hall", [compose, paroi(1, { trace: [[400, 0], [400, 300]], trace_pdf: [[40, 0], [40, 30]] })])]);

  it("la paroi se coupe aussitôt en deux morceaux de même composition, renumérotés", () => {
    const apres = appliquerEnLocal(content, { type: "cote_couper", local: "L1", point_pdf: [10, 0.4] });
    const parois = apres.locaux[0].fiche.parois!;
    expect(parois.map((p) => [p.rang, p.longueur_m])).toEqual([[0, 10], [1, 30], [2, 4]]);
    expect(parois[0].trace).toEqual([[0, 0], [100, 0]]);
    expect(parois[1].composition?.id).toBe("c1");
    expect(apres.coupures_parois).toHaveLength(1);
    expect(coupureProche(apres, [10.5, 0], 1)).toEqual({ local: "L1", point_pdf: [10, 0.4] });
    const plan = renderToStaticMarkup(
      <svg>
        <ParoisDesLocaux content={apres} choisie={null} toScreen={(p) => [p[0] * 4, p[1] * 4]} />
      </svg>,
    );
    expect(plan).toContain("th-coupure-paroi");
  });

  it("retirer la coupure l'enlève tout de suite ; la paroi se réunit au recalcul", () => {
    const coupe = appliquerEnLocal(content, { type: "cote_couper", local: "L1", point_pdf: [10, 0] });
    const recolle = appliquerEnLocal(coupe, { type: "cote_recoller", local: "L1", point_pdf: [10.2, 0] });
    expect(recolle.coupures_parois).toEqual([]);
  });
});

describe("menuiseries posées sur les parois et surfaces (D267 à D270)", () => {
  const pose = (debut: number, fin: number, modele: string | null) => ({
    ref: { troncon: "T01", debut_m: debut, fin_m: fin },
    composant: "M1",
    modele,
    menuiserie_type: "fenetre",
    largeur_m: fin - debut,
    debut_m: debut,
    fin_m: fin,
    trace: [[debut * 10, 0], [fin * 10, 0]] as [number, number][],
    trace_pdf: [[debut, 0], [fin, 0]] as [number, number][],
  });
  const F1 = { nom: "F1", largeur_cm: 120, hauteur_m: 2.15, vue_id: 1, vue: "Façade nord", capture: true, horodatage: null, poses: 1 };
  const mur = paroi(0, { trace: [[0, 0], [400, 0]], trace_pdf: [[0, 0], [40, 0]], longueur_m: 10, menuiseries: [pose(2, 3.2, "F1"), pose(6, 7, null)] });

  it("surface opaque = brute − baies ; ce qui manque est dit au lieu d'être deviné", () => {
    expect(surfacesParoi(mur, 2.5, [F1])).toEqual({
      brute_m2: 25,
      baies_m2: 2.58,
      opaque_m2: null,
      manques: ["1 menuiserie sans modèle (hauteur inconnue)"],
    });
    const complet = { ...mur, menuiseries: [pose(2, 3.2, "F1")] };
    expect(surfacesParoi(complet, 2.5, [F1])).toEqual({ brute_m2: 25, baies_m2: 2.58, opaque_m2: 22.42, manques: [] });
    expect(surfacesParoi(complet, null, [F1]).manques).toEqual(["hauteur du local à mesurer"]);
  });

  it("couper la paroi partage ses menuiseries entre les deux morceaux, à leur position", () => {
    const content = etude([local("L1", "Bureau", [mur])]);
    const apres = appliquerEnLocal(content, { type: "cote_couper", local: "L1", point_pdf: [20, 0] });
    const [gauche, droite] = apres.locaux[0].fiche.parois!;
    expect(gauche.menuiseries!.map((m) => [m.debut_m, m.fin_m])).toEqual([[2, 3.2]]);
    expect(droite.menuiseries!.map((m) => [m.debut_m, m.fin_m])).toEqual([[1, 2]]);
  });

  it("la fiche de la paroi liste ses menuiseries et ses surfaces, et le plan les dessine en bleu", () => {
    const content = etude([local("L1", "Bureau", [mur])]);
    const fiche = renderToStaticMarkup(
      <FicheParoi content={content} room={content.locaux[0]} paroi={mur} busy={false} hauteurLocal={2.5} modeles={[F1]}
        onValider={() => undefined} onRetour={() => undefined} />,
    );
    expect(fiche).toContain("modèle F1");
    expect(fiche).toContain("sans modèle");
    expect(fiche).toContain("25,00 m²");
    expect(fiche).toContain("À compléter");
    const plan = renderToStaticMarkup(
      <svg>
        <ParoisDesLocaux content={content} choisie={null} toScreen={(p) => [p[0] * 4, p[1] * 4]} />
      </svg>,
    );
    expect(plan.match(/th-paroi-local__baie/g)).toHaveLength(2);
  });
});

describe("le travail déjà fait est repris", () => {
  it("une composition validée sur le mur du relevé compte comme validée et le dit", () => {
    const reprise = paroi(0, { composition: { id: "releve", reprise: true, ...P1 } });
    const content = etude([local("L1", "Bureau", [reprise])]);
    expect(avancementParois(content)).toEqual({ total: 1, restants: 0 });
    const fiche = renderToStaticMarkup(
      <FicheParoi content={content} room={content.locaux[0]} paroi={reprise} busy={false} onValider={() => undefined} onRetour={() => undefined} />,
    );
    expect(fiche).toContain("reprise du mur que vous aviez déjà validé");
  });
});
