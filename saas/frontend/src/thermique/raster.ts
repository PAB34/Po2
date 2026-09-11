import type { PdfPoint } from "./api";

export type RasterLevel = { z: number; width: number; height: number; cols: number; rows: number };

export type RasterManifest = {
  sheet_id: number;
  rotation: number;
  tile_size: number;
  width_px: number;
  height_px: number;
  scale: number;
  // PDF (pt) → pixels du niveau le plus fin : px = a·x + c·y + e ; py = b·x + d·y + f
  transform: number[];
  levels: RasterLevel[];
  tiles: Record<string, string[]>;
  build_seconds: number;
  tile_url: string;
};

export type Rect = { x0: number; y0: number; x1: number; y1: number };
export type TileRef = { z: number; x: number; y: number };

export function pdfToRaster(transform: number[], point: PdfPoint): [number, number] {
  const [a, b, c, d, e, f] = transform;
  return [a * point[0] + c * point[1] + e, b * point[0] + d * point[1] + f];
}

export function rasterToPdf(transform: number[], px: number, py: number): PdfPoint {
  const [a, b, c, d, e, f] = transform;
  const det = a * d - b * c;
  return [(d * (px - e) - c * (py - f)) / det, (a * (py - f) - b * (px - e)) / det];
}

// Part de la résolution maximale portée par un niveau.
export function levelFactor(manifest: RasterManifest, level: RasterLevel): number {
  return level.width / manifest.width_px;
}

// Niveau le moins lourd assez fin pour l'écran (pixels écran par pixel du niveau max).
export function pickLevel(manifest: RasterManifest, deviceScale: number): RasterLevel {
  const found = manifest.levels.find((level) => levelFactor(manifest, level) >= deviceScale);
  return found ?? manifest.levels[manifest.levels.length - 1];
}

// Fond basse définition toujours affiché, en peu de tuiles.
export function pickBackdrop(manifest: RasterManifest, maxTiles = 16): RasterLevel {
  let backdrop = manifest.levels[0];
  for (const level of manifest.levels) {
    if (level.cols * level.rows <= maxTiles) {
      backdrop = level;
    }
  }
  return backdrop;
}

export function visibleTiles(manifest: RasterManifest, level: RasterLevel, rect: Rect | null): TileRef[] {
  const stored = new Set(manifest.tiles[String(level.z)] ?? []);
  const span = manifest.tile_size / levelFactor(manifest, level);
  const x0 = rect ? Math.max(0, Math.floor(rect.x0 / span) - 1) : 0;
  const y0 = rect ? Math.max(0, Math.floor(rect.y0 / span) - 1) : 0;
  const x1 = rect ? Math.min(level.cols - 1, Math.floor(rect.x1 / span) + 1) : level.cols - 1;
  const y1 = rect ? Math.min(level.rows - 1, Math.floor(rect.y1 / span) + 1) : level.rows - 1;
  const result: TileRef[] = [];
  for (let y = y0; y <= y1; y += 1) {
    for (let x = x0; x <= x1; x += 1) {
      if (stored.has(`${x}_${y}`)) {
        result.push({ z: level.z, x, y });
      }
    }
  }
  return result;
}

export function tileSrc(template: string, tile: TileRef): string {
  return template.replace("{z}", String(tile.z)).replace("{x}", String(tile.x)).replace("{y}", String(tile.y));
}
