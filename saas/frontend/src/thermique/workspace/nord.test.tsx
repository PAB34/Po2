import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { SheetNorth } from "../api";
import { NorthOverlay } from "./NorthOverlay";
import { azimutEcran, lectureDuNord } from "./nord";

const nord: SheetNorth = { p1: [10, 20], p2: [10, 70], longueur_pt: 50 };
const identite = (point: [number, number]): [number, number] => point;

describe("lecture du nord", () => {
  it("tient compte du retournement de l'axe vertical du rendu PDF", () => {
    const azimut = azimutEcran([100, 100], [100, 150], [2, 0, 0, -2, 0, 1000]);
    expect(azimut).toBeCloseTo(0);
    expect(lectureDuNord(azimut!)).toBe("vers le haut de la planche");
  });

  it("lit les huit secteurs dans le sens horaire", () => {
    expect(lectureDuNord(0)).toBe("vers le haut de la planche");
    expect(lectureDuNord(90)).toBe("vers la droite de la planche");
    expect(lectureDuNord(180)).toBe("vers le bas de la planche");
    expect(lectureDuNord(270)).toBe("vers la gauche de la planche");
  });
});

describe("dessin de la flèche", () => {
  it("ne confond pas les points d'une mesure avec un nord provisoire", () => {
    const html = renderToStaticMarkup(
      <svg>
        <NorthOverlay nord={nord} enCours={[[100, 100], [200, 200]]} toScreen={identite} actif={false} />
      </svg>,
    );
    expect(html).toContain('x1="10"');
    expect(html).not.toContain("is-draft");
  });

  it("montre la base dès le premier clic", () => {
    const html = renderToStaticMarkup(
      <svg>
        <NorthOverlay nord={nord} enCours={[[30, 40]]} toScreen={identite} actif />
      </svg>,
    );
    expect(html).toContain("base");
    expect(html).toContain('cx="30"');
    expect(html).not.toContain("<line");
  });
});
