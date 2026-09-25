import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { StudyBridge, StudyContent, StudyElementRef, StudyReleveElement, StudyRoom } from "../api";
import { PontsPanel } from "./PontsPanel";
import { StudyMetrics } from "./StudyMetrics";
import { refDeElement } from "./elements";

const pont = (reste: Partial<StudyReleveElement> = {}): StudyReleveElement => ({
  troncon: "T01",
  debut_m: 12.5,
  fin_m: 12.5,
  type: "angle_sortant",
  composant: null,
  nu_exterieur_cm: 0,
  nu_interieur_cm: -50,
  confiance: 0.9,
  indice: "retour d'angle du voile",
  a_verifier: false,
  ...reste,
});

const liaison = (reste: Partial<StudyBridge> = {}): StudyBridge => ({
  type: "angle_sortant",
  troncon: "T01",
  abscisse_m: 12.5,
  longueur_m: 0,
  piece: "Bureau",
  point_pdf: [120, 80],
  exclu: false,
  ...reste,
});

const etude = (elements: StudyReleveElement[], liaisons: StudyBridge[]): StudyContent =>
  ({
    locaux: [{ id: "L0", nom: "Bureau" }],
    enveloppe: { releve_brut: { elements, catalogue: [], observations: [] }, objets: [], liaisons },
  }) as unknown as StudyContent;

const rien = () => undefined;
const identite = (point: [number, number]): [number, number] => point;

function panneau(elements: StudyReleveElement[], liaisons: StudyBridge[], selected: StudyElementRef | null) {
  return renderToStaticMarkup(
    <PontsPanel
      content={etude(elements, liaisons)}
      selected={selected}
      onSelect={rien}
      busy={false}
      message={null}
      onOperation={rien}
    />,
  );
}

describe("étape « ponts thermiques »", () => {
  it("annonce où l'on en est dans la passe, et ce qui reste", () => {
    const elements = [pont(), pont({ troncon: "T02", type: "angle_rentrant" }), pont({ troncon: "T03" })];
    const html = panneau(elements, [liaison()], refDeElement(elements[1]));
    expect(html).toContain("Pont 2 sur 3");
    expect(html).toContain("3 encore à juger");
    expect(html).toContain("Angle rentrant");
  });

  it("dit dans quel local se trouve le pont, et le reconnaît sans local", () => {
    const element = pont();
    expect(panneau([element], [liaison()], refDeElement(element))).toContain("Dans « Bureau »");
    expect(panneau([element], [liaison({ piece: null })], refDeElement(element))).toContain(
      "Rattaché à aucun local",
    );
  });

  it("montre ce que l'agent a lu : c'est ce qui permet de juger", () => {
    const element = pont();
    const html = panneau([element], [liaison()], refDeElement(element));
    expect(html).toContain("retour d&#x27;angle du voile");
    expect(html).toContain("confiance 90");
  });

  it("propose deux gestes explicites, jamais un « suivant » qui vaudrait acceptation (Q2)", () => {
    const element = pont();
    const html = panneau([element], [liaison()], refDeElement(element));
    expect(html).toContain("Garder");
    expect(html).toContain("Écarter…");
    expect(html).toContain("Passer sans juger");
  });

  it("un pont déjà écarté propose de revenir dans le calcul, avec sa raison", () => {
    const element = pont({ exclu: true, motif_exclusion: "angle du tracé" });
    const html = panneau([element], [liaison({ exclu: true })], refDeElement(element));
    expect(html).toContain("angle du tracé");
    expect(html).toContain("Remettre dans le calcul");
    expect(html).not.toContain("Garder");
  });

  it("un niveau sans liaison le dit, au lieu d'un écran vide", () => {
    expect(panneau([], [], null)).toContain("Aucune liaison relevée");
  });
});

function plan(liaisons: StudyBridge[], grouperPonts: boolean) {
  const room = {
    id: "L0",
    nom: "Bureau",
    contour_pdf: [
      [0, 0],
      [100, 0],
      [100, 100],
      [0, 100],
    ],
    surface_m2: 20,
    fiche: { cotes: [] },
  } as unknown as StudyRoom;
  return renderToStaticMarkup(
    <svg>
      <StudyMetrics
        rooms={[room]}
        selected={null}
        shapes={[]}
        bridges={liaisons}
        show={{ metres: false, ponts: true, elements: false, toutesCotes: false }}
        toScreen={identite}
        grouperPonts={grouperPonts}
      />
    </svg>,
  );
}

/** Nombre de pastilles réellement dessinées : chaque pont dessiné ouvre un groupe `th-metric-pont`. */
const pastilles = (html: string) => (html.match(/class="th-metric-pont(?=[ "])/g) ?? []).length;

describe("les ponts dessinés sur le plan", () => {
  it("regroupe les pastilles confondues à l'œil, et l'annonce", () => {
    const serres = [liaison(), liaison({ abscisse_m: 12.6, point_pdf: [124, 82] })];
    const html = plan(serres, true);
    expect(html).toContain("AS ×2");
    expect(pastilles(html)).toBe(1);
  });

  it("les déplie à l'étape ponts : c'est là qu'il faut les distinguer un à un (Q4)", () => {
    const serres = [liaison(), liaison({ abscisse_m: 12.6, point_pdf: [124, 82] })];
    const html = plan(serres, false);
    expect(html).not.toContain("×2");
    expect(pastilles(html)).toBe(2);
  });

  it("une liaison écartée reste dessinée, marquée, et n'est jamais absorbée dans un groupe (Q5)", () => {
    const html = plan([liaison(), liaison({ abscisse_m: 12.6, point_pdf: [124, 82], exclu: true })], true);
    expect(html).toContain("is-ecartee");
    expect(html).toContain("écarté");
    expect(html).not.toContain("×2");
  });
});
