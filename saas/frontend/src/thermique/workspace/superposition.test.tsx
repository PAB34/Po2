import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { PdfPoint, Sheet } from "../api";
import type { RasterManifest } from "../raster";
import { NiveauFantome, versEcran } from "./NiveauFantome";
import {
  appliquer,
  calageAEnregistrer,
  composer,
  correspondance,
  inverser,
  niveauxVoisins,
  similitude,
} from "./superposition";

const planche = (id: number, niveau: string, reste: Partial<Sheet> = {}): Sheet =>
  ({
    id,
    nature: "plan",
    label: niveau,
    level_label: niveau,
    scale_denominator: 100,
    page_width_pt: 1000,
    page_height_pt: 800,
    rotation_deg: 0,
    calage: null,
    ...reste,
  }) as unknown as Sheet;

const proche = (a: PdfPoint, b: PdfPoint) => Math.hypot(a[0] - b[0], a[1] - b[1]) < 1e-9;

describe("similitudes du calage (S2, D173)", () => {
  it("deux paires suffisent ; composer et inverser se défont", () => {
    const sim = similitude([[0, 0], [100, 0]], [[100, 50], [100, 250]])!;
    expect(proche(appliquer(sim, [50, 30]), [40, 150])).toBe(true);
    expect(proche(appliquer(composer(inverser(sim), sim), [12, 34]), [12, 34])).toBe(true);
  });

  it("calées toutes deux, le voisin se pose par la référence ; sinon, pose provisoire annoncée", () => {
    const reference = planche(1, "RDC");
    const r1 = planche(2, "R+1", { calage: { a: 1, b: 0, tx: 10, ty: 5, reference_sheet_id: 1 } as Sheet["calage"] });
    const calee = correspondance(r1, reference, 1);
    expect(calee.calee).toBe(true);
    expect(proche(appliquer(calee.sim, [0, 0]), [10, 5])).toBe(true);
    const provisoire = correspondance(planche(3, "R+2", { scale_denominator: 50 }), reference, 1);
    expect(provisoire.calee).toBe(false);
    expect(provisoire.sim.a).toBe(0.5);
  });

  it("les voisins sont les plans juste en dessous et juste au-dessus", () => {
    const planches = [planche(3, "R+2"), planche(1, "RDC"), planche(2, "R+1")];
    const { inferieur, superieur } = niveauxVoisins(planches, planches[2]);
    expect(inferieur?.id).toBe(1);
    expect(superieur?.id).toBe(3);
  });

  it("on cale la planche qui ne l'est pas sur celle qui l'est", () => {
    const reference = planche(1, "RDC");
    const r1 = planche(2, "R+1");
    const paires: [PdfPoint, PdfPoint][] = [
      [[0, 0], [10, 10]],
      [[100, 0], [110, 10]],
    ];
    // Plan actif = référence : c'est le voisin (R+1) qui se cale.
    expect(calageAEnregistrer(r1, reference, 1, paires)).toMatchObject({ planche: 2, cible: 1 });
    // Plan actif = R+1 non calé, voisin = référence : c'est le plan actif qui se cale.
    expect(calageAEnregistrer(reference, r1, 1, paires)).toMatchObject({ planche: 2, cible: 1 });
    // Ni l'une ni l'autre calée : refus expliqué.
    expect(calageAEnregistrer(planche(3, "R+2"), r1, 1, paires)).toHaveProperty("refus");
    expect(calageAEnregistrer(r1, reference, null, paires)).toHaveProperty("refus");
  });
});

describe("le calque fantôme (S3, D168)", () => {
  const manifest = {
    sheet_id: 2,
    rotation: 0,
    tile_size: 256,
    width_px: 512,
    height_px: 512,
    scale: 1,
    transform: [1, 0, 0, 1, 0, 0],
    levels: [{ z: 0, width: 512, height: 512, cols: 2, rows: 2 }],
    tiles: { "0": ["0_0", "1_0", "0_1", "1_1"] },
    build_seconds: 0,
    tile_url: "/t/{z}/{x}/{y}.png",
  } as RasterManifest;

  it("passe des pixels du voisin à l'écran par une seule matrice", () => {
    const m = versEcran(manifest, { a: 1, b: 0, tx: 10, ty: 20 }, (p) => [p[0] * 2, p[1] * 2]);
    expect(m).toEqual({ a: 2, b: 0, c: 0, d: 2, e: 20, f: 40 });
  });

  it("dessine les tuiles du voisin, teintées selon le sens", () => {
    const html = renderToStaticMarkup(
      <svg>
        <NiveauFantome
          manifest={manifest}
          tileTemplate="/t/{z}/{x}/{y}.png"
          sim={{ a: 1, b: 0, tx: 0, ty: 0 }}
          toScreen={(p) => p}
          taille={{ width: 512, height: 512 }}
          sens="inferieur"
        />
      </svg>,
    );
    expect(html.match(/<image /g)).toHaveLength(4);
    expect(html).toContain("th-fantome--inferieur");
    expect(html).toContain("th-fantome-teinte-inferieur");
  });
});
