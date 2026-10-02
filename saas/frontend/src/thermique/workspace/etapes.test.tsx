import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { StudyBridge, StudyEnvelopeShape, StudyRoom } from "../api";
import { vueDeLEtape } from "./parcours";
import { StudyMetrics } from "./StudyMetrics";
import { StudyOverlay } from "./StudyPanel";

const identite = (point: [number, number]): [number, number] => point;

const bureau = {
  id: "L0",
  nom: "Bureau",
  nature: "chauffe",
  contour_pdf: [
    [0, 0],
    [100, 0],
    [100, 100],
    [0, 100],
  ],
  surface_m2: 20,
  fiche: {
    cotes: [{ adjacence: "exterieur", longueur_m: 10, epaisseur_cm: 30, deperditif: true, trace_pdf: [[0, 0], [100, 0]] }],
  },
} as unknown as StudyRoom;

const mur = {
  id: "o1",
  category: "mur_exterieur",
  subtype: "mur",
  geometry_type: "polygon",
  points_pdf: [[0, -10], [100, -10], [100, 0], [0, 0]],
  source_parcours: { troncon: "T01", debut_m: 0, fin_m: 3, piece: "Bureau" },
} as unknown as StudyEnvelopeShape;

const pont = { type: "angle_sortant", troncon: "T01", abscisse_m: 3, longueur_m: 0, piece: "Bureau", point_pdf: [100, 0] } as StudyBridge;

// Ce que dessine le plan, local ouvert, à une étape donnée.
const plan = (etape: Parameters<typeof vueDeLEtape>[0]) =>
  renderToStaticMarkup(
    <svg>
      <StudyMetrics
        rooms={[bureau]}
        selected={bureau}
        shapes={[mur]}
        bridges={[pont]}
        show={{ metres: false, ponts: false, elements: false, toutesCotes: false }}
        toScreen={identite}
        familles={vueDeLEtape(etape)}
      />
    </svg>,
  );

describe("chaque étape ne montre que ses objets (D155)", () => {
  it("locaux : les cotes et la surface, ni murs ni ponts", () => {
    const html = plan("locaux");
    expect(html).toContain("th-metric-cote");
    expect(html).not.toContain("th-metric-element");
    expect(html).not.toContain("th-metric-pont");
  });

  it("parois : ni le relevé de l'IA ni les ponts, les parois des locaux se dessinent à part (option C, D262)", () => {
    const html = plan("enveloppe");
    expect(html).not.toContain("th-metric-element");
    expect(html).not.toContain("th-metric-pont");
  });

  it("ponts : les ponts seuls, même dans le local ouvert", () => {
    const html = plan("ponts");
    expect(html).toContain("th-metric-pont");
    expect(html).not.toContain("th-metric-cote");
    expect(html).not.toContain("th-metric-element");
  });

  it("hors des trois étapes de travail, rien ne change : le local ouvert montre tout", () => {
    const html = plan("planche");
    expect(html).toContain("th-metric-cote");
    expect(html).toContain("th-metric-element");
    expect(html).toContain("th-metric-pont");
  });

  it("les gestes suivent : fiche du local aux locaux, parois seules à leur étape, ponts seuls aux ponts", () => {
    expect(vueDeLEtape("locaux")).toMatchObject({ clic: "locaux", ficheLocal: true, listeElements: "aucune" });
    expect(vueDeLEtape("enveloppe")).toMatchObject({ clic: "locaux", ficheLocal: false, listeElements: "aucune" });
    expect(vueDeLEtape("ponts")).toMatchObject({ clic: "ponts", ficheLocal: false, listeElements: "aucune" });
  });
});

describe("le zonage s'estompe aux étapes des parois et des ponts (D156)", () => {
  const zonage = (discret: boolean) =>
    renderToStaticMarkup(
      <svg>
        <StudyOverlay rooms={[bureau]} selectedId="L0" toScreen={identite} onSelect={() => undefined} discret={discret} />
      </svg>,
    );

  it("le local ouvert perd son trait épais et ses limites colorées, qui masquaient les pastilles", () => {
    expect(zonage(true)).toContain("is-discret");
    expect(zonage(true)).not.toContain("th-study-side");
    expect(zonage(false)).toContain("th-study-side");
  });
});
