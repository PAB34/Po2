import { describe, expect, it } from "vitest";

import type { StudyBridge, StudyContent, StudyEnvelopeShape, StudyReleveElement, StudyRoom } from "../api";
import {
  compterElements,
  ecartsAvecLAgent,
  elementAt,
  elementDuPont,
  elementsDuLocal,
  epaisseurCm,
  formesDuLocal,
  longueurM,
  memeElement,
  pontAt,
  pontsDuLocal,
  porteursDuComposant,
  refDeForme,
  trouverElement,
  viserSurLePlan,
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

const etude = (
  elements: StudyReleveElement[],
  objets: StudyEnvelopeShape[] = [],
  liaisons: StudyBridge[] = [],
): StudyContent =>
  ({
    enveloppe: { releve_brut: { elements, catalogue: [], observations: [] }, objets, liaisons },
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


describe("les ponts thermiques sont des éléments du relevé", () => {
  // Sur le vrai R+1, les 77 liaisons correspondent une à une aux 77 éléments de type angle ou about,
  // et ces éléments-là n'ont AUCUNE forme dessinée : ils n'existent sur le plan que comme pastilles.
  const angle = element({
    troncon: "T01",
    debut_m: 0,
    fin_m: 0.25,
    type: "angle_sortant",
    composant: "L1",
    a_verifier: true,
  });
  const pont: StudyBridge = {
    type: "angle_sortant",
    troncon: "T01",
    abscisse_m: 0.125,
    longueur_m: 0.25,
    piece: "Bureau",
    composant: "L1",
    point_pdf: [100, 100],
  };

  it("retrouve l'élément d'un pont par son tronçon et son abscisse", () => {
    const content = etude([angle], [], [pont]);
    expect(elementDuPont(content, pont)).toEqual({ troncon: "T01", debut_m: 0, fin_m: 0.25 });
    expect(elementDuPont(content, { ...pont, abscisse_m: undefined })).toBeNull();
    expect(elementDuPont(content, { ...pont, troncon: "T99" })).toBeNull();
  });

  it("ne confond pas deux angles du même tronçon", () => {
    const autre = element({ troncon: "T01", debut_m: 8, fin_m: 8.3, type: "angle_sortant" });
    const content = etude([angle, autre], [], [pont]);
    expect(elementDuPont(content, pont)?.debut_m).toBe(0);
    expect(elementDuPont(content, { ...pont, abscisse_m: 8.15 })?.debut_m).toBe(8);
  });

  it("attrape la pastille sous le curseur, la plus proche gagnant", () => {
    const voisin: StudyBridge = { ...pont, abscisse_m: 8.15, point_pdf: [108, 100] };
    expect(pontAt([pont, voisin], [102, 100], 8)).toBe(pont);
    expect(pontAt([pont, voisin], [107, 100], 8)).toBe(voisin);
    expect(pontAt([pont, voisin], [300, 300], 8)).toBeNull();
    expect(pontAt([{ ...pont, point_pdf: undefined }], [100, 100], 8)).toBeNull();
  });

  it("fait figurer les ponts du local dans sa liste d'éléments, bien qu'ils n'aient aucune forme", () => {
    const mur = element({ troncon: "T02", debut_m: 0, fin_m: 4 });
    const content = etude(
      [angle, mur],
      [forme({ source_parcours: { troncon: "T02", debut_m: 0, fin_m: 4, piece: "Bureau" } })],
      [pont],
    );
    expect(elementsDuLocal(content, local("Bureau")).map((item) => item.type)).toEqual([
      "angle_sortant",
      "paroi",
    ]);
    expect(pontsDuLocal(content, local("Bureau"))).toHaveLength(1);
    expect(pontsDuLocal(content, local("Couloir"))).toHaveLength(0);
  });
});


describe("viser un élément n'importe où sur le plan", () => {
  // Coordonnées réelles du R+1 : le local 6.1.1 occupe x 1096..1236, et son mur x 1236..1249.
  // Le mur est donc EN DEHORS du contour de son local — c'est le nu intérieur qui fait le contour.
  // Exiger que le local soit déjà ouvert rendait le mur impossible à attraper.
  const mur = forme({
    id: "env-mur",
    points_pdf: [
      [1245, 1679],
      [1249, 1679],
      [1249, 1791],
      [1245, 1791],
    ],
    source_parcours: { troncon: "T01", debut_m: 0.25, fin_m: 4.2, piece: "6.1.1 B.dir + EAPMR" },
  });
  const pont: StudyBridge = {
    type: "angle_sortant",
    troncon: "T01",
    abscisse_m: 0.125,
    longueur_m: 0.25,
    piece: "6.1.1 B.dir + EAPMR",
    point_pdf: [1236, 1794],
  };
  const angle = element({ troncon: "T01", debut_m: 0, fin_m: 0.25, type: "angle_sortant" });
  const paroi = element({ troncon: "T01", debut_m: 0.25, fin_m: 4.2 });
  const locaux = [local("6.1.1 B.dir + EAPMR"), local("Couloir")];
  const content = etude([angle, paroi], [mur], [pont]);

  it("attrape un mur situé hors du contour de son local, et ouvre ce local", () => {
    const vise = viserSurLePlan(content, locaux, [1247, 1700], { element: 9, pont: 12 });
    expect(vise?.ref).toEqual({ troncon: "T01", debut_m: 0.25, fin_m: 4.2 });
    expect(vise?.room?.nom).toBe("6.1.1 B.dir + EAPMR");
  });

  it("donne le pont avant le mur qui le porte", () => {
    const vise = viserSurLePlan(content, locaux, [1237, 1793], { element: 9, pont: 12 });
    expect(vise?.ref).toEqual({ troncon: "T01", debut_m: 0, fin_m: 0.25 });
    expect(vise?.room?.nom).toBe("6.1.1 B.dir + EAPMR");
  });

  it("ne rend rien loin de tout", () => {
    expect(viserSurLePlan(content, locaux, [500, 500], { element: 9, pont: 12 })).toBeNull();
  });

  it("rend quand même l'élément quand son local n'est pas dans la liste", () => {
    const vise = viserSurLePlan(content, [local("Couloir")], [1247, 1700], { element: 9, pont: 12 });
    expect(vise?.ref.troncon).toBe("T01");
    expect(vise?.room).toBeNull();
  });
});
