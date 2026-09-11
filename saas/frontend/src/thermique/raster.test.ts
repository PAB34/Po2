import { describe, expect, it } from "vitest";

import { pdfToRaster, pickBackdrop, pickLevel, rasterToPdf, tileSrc, visibleTiles, type RasterManifest } from "./raster";

// Page A1 portrait tournée de 90° : transformation typique renvoyée par pdfium.
const manifest: RasterManifest = {
  sheet_id: 1,
  rotation: 90,
  tile_size: 256,
  width_px: 1024,
  height_px: 768,
  scale: 3,
  transform: [0, 3, 3, 0, 0, 0],
  levels: [
    { z: 0, width: 256, height: 192, cols: 1, rows: 1 },
    { z: 1, width: 512, height: 384, cols: 2, rows: 2 },
    { z: 2, width: 1024, height: 768, cols: 4, rows: 3 },
  ],
  tiles: { "0": ["0_0"], "1": ["0_0", "1_0", "0_1", "1_1"], "2": ["0_0", "1_1", "3_2"] },
  build_seconds: 1,
  tile_url: "/thermique/sheets/1/tiles/90/{z}/{x}/{y}.png?e=1&s=abc",
};

describe("tuiles des planches", () => {
  it("passe du PDF aux pixels et revient", () => {
    expect(pdfToRaster(manifest.transform, [10, 20])).toEqual([60, 30]);
    const [x, y] = rasterToPdf(manifest.transform, 60, 30);
    expect(x).toBeCloseTo(10);
    expect(y).toBeCloseTo(20);
  });

  it("choisit le niveau le plus léger assez fin pour l'écran", () => {
    expect(pickLevel(manifest, 0.2).z).toBe(0);
    expect(pickLevel(manifest, 0.3).z).toBe(1);
    expect(pickLevel(manifest, 0.9).z).toBe(2);
    expect(pickLevel(manifest, 4).z).toBe(2);
    expect(pickBackdrop(manifest, 4).z).toBe(1);
  });

  it("ne demande que les tuiles visibles et non blanches", () => {
    const level = manifest.levels[2];
    expect(visibleTiles(manifest, level, null).map((tile) => `${tile.x}_${tile.y}`)).toEqual(["0_0", "1_1", "3_2"]);
    expect(visibleTiles(manifest, level, { x0: 0, y0: 0, x1: 100, y1: 100 }).map((tile) => `${tile.x}_${tile.y}`)).toEqual([
      "0_0",
      "1_1",
    ]);
    expect(tileSrc(manifest.tile_url, { z: 2, x: 3, y: 1 })).toBe("/thermique/sheets/1/tiles/90/2/3/1.png?e=1&s=abc");
  });
});
