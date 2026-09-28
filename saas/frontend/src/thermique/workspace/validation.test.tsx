import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { StudyContent, StudyReleveElement, StudyRoom } from "../api";
import { paroisATrancher } from "./elements";
import { StudyRoomPanel, type StudyRoomValidation } from "./StudyPanel";

const element = (reste: Partial<StudyReleveElement>): StudyReleveElement => ({
  troncon: "T01",
  debut_m: 0,
  fin_m: 3,
  type: "paroi",
  composant: null,
  nu_exterieur_cm: 0,
  nu_interieur_cm: -30,
  confiance: 0.5,
  indice: "",
  a_verifier: true,
  ...reste,
});

const room = {
  id: "L1",
  nom: "Bureau",
  nature: "chauffe",
  contour_pdf: [],
  fiche: { piece: "Bureau", local: "chauffe", surface_m2: 12, perimetre_m: 14, cotes: [], deperditif_m: 4 },
  synthese: {},
  demandes: [],
} as unknown as StudyRoom;

const etude = (elements: StudyReleveElement[]): StudyContent =>
  ({
    locaux: [room],
    enveloppe: {
      releve_brut: { elements, catalogue: [], observations: [] },
      objets: [
        { id: "o1", source_parcours: { troncon: "T01", debut_m: 0, fin_m: 3, piece: "Bureau" } },
        { id: "o2", source_parcours: { troncon: "T02", debut_m: 0, fin_m: 4, piece: "Salle" } },
      ],
      liaisons: [{ type: "angle_sortant", troncon: "T01", abscisse_m: 3, piece: "Bureau", point_pdf: [0, 0] }],
    },
  }) as unknown as StudyContent;

describe("ce qui empêche de valider un local (Q7)", () => {
  const angle = element({ type: "angle_sortant", debut_m: 3, fin_m: 3 });
  const murVoisin = element({ troncon: "T02", fin_m: 4 });

  it("un mur douteux du local bloque ; son angle douteux et le mur du voisin, non", () => {
    expect(paroisATrancher(etude([element({}), angle, murVoisin]), room)).toHaveLength(1);
  });

  it("confirmé, corrigé ou écarté, il ne bloque plus", () => {
    for (const drapeau of ["confirme", "corrige", "exclu"] as const) {
      expect(paroisATrancher(etude([element({ [drapeau]: true }), angle]), room)).toHaveLength(0);
    }
  });

  it("un mur que l'agent n'a pas mis en doute est tenu pour acquis (D114)", () => {
    expect(paroisATrancher(etude([element({ a_verifier: false })]), room)).toHaveLength(0);
  });
});

describe("le bouton « Valider ce local »", () => {
  const fiche = (validation: Partial<StudyRoomValidation>, status: "a_verifier" | "valide" = "a_verifier") =>
    renderToStaticMarkup(
      <StudyRoomPanel
        room={room}
        state={{ status, motif: null }}
        validation={{ restants: 0, bloque: null, busy: false, message: null, onValider: () => undefined, ...validation }}
      />,
    );

  it("est proposé quand plus rien ne bloque", () => {
    const html = fiche({});
    expect(html).toContain("Valider ce local");
    expect(html).not.toMatch(/<button[^>]*disabled[^>]*>Valider ce local/);
  });

  it("dit combien de murs restent, et que les ponts ne comptent pas", () => {
    const html = fiche({ restants: 3 });
    expect(html).toMatch(/<button[^>]*disabled[^>]*>Valider ce local/);
    expect(html).toContain("Encore 3 murs ou menuiseries à vérifier");
    expect(html).toContain("Les ponts thermiques ne bloquent pas");
  });

  it("un travail en attente passe avant, et se dit", () => {
    expect(fiche({ bloque: "Enregistrez d'abord les corrections d'éléments en attente." })).toContain(
      "Enregistrez d&#x27;abord les corrections",
    );
  });

  it("un local déjà validé n'a plus de bouton", () => {
    expect(fiche({}, "valide")).not.toContain("Valider ce local");
  });
});
