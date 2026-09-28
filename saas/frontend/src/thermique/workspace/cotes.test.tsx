import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { StudyRoom, StudySide } from "../api";
import { controleCote, coteAt, empreinteCote, milieuCote, rangVise } from "./cotes";
import { StudyMetrics } from "./StudyMetrics";
import { StudyRoomPanel } from "./StudyPanel";

const cote = (reste: Partial<StudySide> = {}): StudySide => ({
  adjacence: "exterieur",
  voisin: "",
  longueur_m: 10,
  epaisseur_cm: 30,
  orientation: "Sud",
  deperditif: true,
  trace_pdf: [
    [0, 0],
    [100, 0],
  ],
  ...reste,
});

// Un local carré de 100 pt : un côté par bord, posés sur le contour comme sur le R+1.
const bureau = (cotes: StudySide[] = [
  cote(),
  cote({ adjacence: "local_chauffe", voisin: "Couloir", deperditif: false, longueur_m: 8, trace_pdf: [[100, 0], [100, 100]] }),
  cote({ longueur_m: 12, trace_pdf: [[100, 100], [0, 100]] }),
  cote({ adjacence: "local_chauffe", voisin: "Salle", deperditif: false, longueur_m: 9, trace_pdf: [[0, 100], [0, 0]] }),
]): StudyRoom =>
  ({
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
    fiche: { piece: "Bureau", local: "chauffe", surface_m2: 20, perimetre_m: 40, cotes },
    synthese: {},
    demandes: [],
  }) as unknown as StudyRoom;

const identite = (point: [number, number]): [number, number] => point;

describe("désigner un côté sur le plan (D149)", () => {
  it("attrape le côté le plus proche, de l'intérieur du local", () => {
    expect(coteAt(bureau(), [50, 4], 8)).toBe(0);
    expect(coteAt(bureau(), [96, 50], 8)).toBe(1);
    expect(coteAt(bureau(), [4, 50], 8)).toBe(3);
    // Dans un angle, le plus proche l'emporte.
    expect(coteAt(bureau(), [3, 95], 8)).toBe(3);
  });

  it("n'attrape rien au-delà du trait : c'est là qu'est le mur, qui doit rester attrapable", () => {
    expect(coteAt(bureau(), [50, -4], 8)).toBeNull();
  });

  it("n'attrape rien au milieu du local : un clic loin des côtés rouvre simplement la fiche", () => {
    expect(coteAt(bureau(), [50, 50], 8)).toBeNull();
  });
});

describe("le côté désigné survit, ou tombe, au recalcul (D145)", () => {
  it("reste désigné tant que c'est le même côté", () => {
    const room = bureau();
    const visee = { localId: "L0", rang: 2, empreinte: empreinteCote(room.fiche.cotes[2]), clic: 1 };
    expect(rangVise(room, visee)).toBe(2);
  });

  it("tombe si le côté de ce rang a changé, plutôt que de surligner un voisin", () => {
    const visee = { localId: "L0", rang: 2, empreinte: empreinteCote(bureau().fiche.cotes[2]), clic: 1 };
    const recalcule = bureau([cote(), cote(), cote({ longueur_m: 7.5 }), cote()]);
    expect(rangVise(recalcule, visee)).toBeNull();
  });

  it("n'appartient qu'à son local", () => {
    const room = bureau();
    const visee = { localId: "L9", rang: 0, empreinte: empreinteCote(room.fiche.cotes[0]), clic: null };
    expect(rangVise(room, visee)).toBeNull();
  });

  it("le plan se centre sur le milieu mesuré le long du tracé (D148)", () => {
    expect(milieuCote(cote({ trace_pdf: [[0, 0], [30, 0], [30, 10]] }))).toEqual([20, 0]);
    expect(milieuCote(cote({ trace_pdf: [[5, 5]] }))).toBeNull();
  });
});

function plan(coteVisee: number | null) {
  return renderToStaticMarkup(
    <svg>
      <StudyMetrics
        rooms={[bureau()]}
        selected={bureau()}
        shapes={[]}
        bridges={[]}
        show={{ metres: false, ponts: false, elements: false, toutesCotes: false }}
        toScreen={identite}
        coteVisee={coteVisee}
      />
    </svg>,
  );
}

describe("le côté désigné sur le plan (D147)", () => {
  it("ressort avec un halo, une seule fois", () => {
    const html = plan(2);
    expect(html.match(/th-metric-cote__halo/g)).toHaveLength(1);
    expect(html.match(/class="th-metric-cote[^"]*is-selected/g)).toHaveLength(1);
    // Les quatre côtés restent dessinés : le désigné n'est pas dédoublé.
    expect(html.match(/class="th-metric-cote(?=[ "])/g)).toHaveLength(4);
  });

  it("est dessiné après tous les autres côtés, sinon ils le recouvrent", () => {
    // L'ordre des groupes de côtés dans le SVG est l'ordre de dessin : le dernier est au-dessus.
    const groupes = plan(0).match(/class="th-metric-cote(?=[ "])[^"]*"/g) ?? [];
    expect(groupes).toHaveLength(4);
    expect(groupes[groupes.length - 1]).toContain("is-selected");
  });

  it("sans côté désigné, aucun halo", () => {
    expect(plan(null)).not.toContain("th-metric-cote__halo");
  });
});

describe("contrôle d'un côté par ses parois (G1)", () => {
  const paroi = (lineaire_m: number) => ({ composant: "P1", lineaire_m });

  it("un côté déperditif sans paroi rattachée est signalé : sa composition est inconnue", () => {
    expect(controleCote(cote({ enveloppe: [] })).etat).toBe("sans_paroi");
  });

  it("un écart de 20 cm ou plus est signalé, avec son sens", () => {
    expect(controleCote(cote({ longueur_m: 10, enveloppe: [paroi(8.06), paroi(1.5)] }))).toEqual({
      etat: "ecart",
      paroisM: 9.56,
      ecartM: -0.44,
    });
  });

  it("en deçà, les arrondis du relevé ne font pas d'alerte", () => {
    expect(controleCote(cote({ longueur_m: 10, enveloppe: [paroi(9.9)] })).etat).toBe("ok");
  });

  it("un côté qui ne déperd pas n'est pas contrôlé", () => {
    expect(controleCote(cote({ deperditif: false, enveloppe: [] })).etat).toBe("hors_champ");
  });

  it("la fiche le dit, côté par côté et en tête de liste", () => {
    const html = renderToStaticMarkup(
      <StudyRoomPanel room={bureau([cote({ enveloppe: [] }), cote({ longueur_m: 10, enveloppe: [paroi(8)] })])} />,
    );
    expect(html).toContain("Aucune paroi rattachée");
    expect(html).toContain("pour un côté de");
    expect(html).toContain("1 côté déperditif sans paroi rattachée · 1 dont les parois s&#x27;écartent");
  });
});

describe("la liste « Côtés et adjacences » (D146)", () => {
  const fiche = (coteVisee: number | null, room = bureau()) =>
    renderToStaticMarkup(<StudyRoomPanel room={room} coteVisee={coteVisee} onCote={() => undefined} />);

  it("chaque côté est un bouton, et le côté désigné est enfoncé", () => {
    const html = fiche(1);
    expect(html.match(/class="th-study-side__viser"/g)).toHaveLength(4);
    expect(html.match(/aria-pressed="true"/g)).toHaveLength(1);
    expect(html).toContain('class="is-selected"');
  });

  it("un côté sans tracé ne peut pas être montré, et le dit", () => {
    const html = fiche(null, bureau([cote({ trace_pdf: [] })]));
    expect(html).toContain("disabled");
    expect(html).toContain("n&#x27;a pas de tracé");
  });

  it("sans geste proposé (contour en cours d'édition), la liste reste inerte", () => {
    const html = renderToStaticMarkup(<StudyRoomPanel room={bureau()} />);
    expect(html).not.toContain("th-study-side__viser");
  });
});
