// Aimantation du tracé sur les traits du plan : sommets déjà tracés, extrémités et croisements
// des traits épais (faces de murs), puis n'importe quel point de ces traits.
import type { PdfPoint } from "./api";
import { projectOnSegment } from "./metre";

export type SnapKind = "sommet" | "extremite" | "intersection" | "trait" | "orthogonal" | "libre";
export type SnapResult = { point: PdfPoint; kind: SnapKind };

const MAX_CANDIDATES = 80;

// Grille de cases : ne teste que les traits proches du curseur.
export class SnapIndex {
  private readonly cells = new Map<string, number[]>();

  constructor(
    readonly segments: number[][],
    private readonly cell = 24,
  ) {
    segments.forEach((segment, index) => {
      const [x1, y1, x2, y2] = segment;
      const keys = new Set<string>();
      const steps = Math.max(1, Math.ceil(Math.hypot(x2 - x1, y2 - y1) / (cell / 2)));
      for (let step = 0; step <= steps; step += 1) {
        const t = step / steps;
        keys.add(this.key(x1 + t * (x2 - x1), y1 + t * (y2 - y1)));
      }
      keys.forEach((key) => {
        const bucket = this.cells.get(key);
        if (bucket) {
          bucket.push(index);
        } else {
          this.cells.set(key, [index]);
        }
      });
    });
  }

  private key(x: number, y: number): string {
    return `${Math.floor(x / this.cell)}:${Math.floor(y / this.cell)}`;
  }

  near([x, y]: PdfPoint, radius: number): number[] {
    const found = new Set<number>();
    const reach = radius + this.cell;
    for (let cx = Math.floor((x - reach) / this.cell); cx <= Math.floor((x + reach) / this.cell); cx += 1) {
      for (let cy = Math.floor((y - reach) / this.cell); cy <= Math.floor((y + reach) / this.cell); cy += 1) {
        this.cells.get(`${cx}:${cy}`)?.forEach((index) => found.add(index));
      }
    }
    return [...found];
  }
}

function intersection(s: number[], t: number[]): PdfPoint | null {
  const [x1, y1, x2, y2] = s;
  const [x3, y3, x4, y4] = t;
  const denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4);
  if (Math.abs(denominator) < 1e-9) {
    return null;
  }
  const u = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denominator;
  const v = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denominator;
  // Légère marge : deux faces qui se touchent presque forment encore un angle.
  if (u < -0.02 || u > 1.02 || v < -0.02 || v > 1.02) {
    return null;
  }
  return [x1 + u * (x2 - x1), y1 + u * (y2 - y1)];
}

export function snapPoint(p: PdfPoint, tolerance: number, index: SnapIndex | null, vertices: PdfPoint[]): SnapResult {
  const distance = (q: PdfPoint) => Math.hypot(q[0] - p[0], q[1] - p[1]);
  let best: SnapResult | null = null;
  let bestDistance = tolerance;
  const consider = (point: PdfPoint, kind: SnapKind) => {
    const d = distance(point);
    if (d <= bestDistance) {
      best = { point, kind };
      bestDistance = d;
    }
  };

  vertices.forEach((vertex) => consider(vertex, "sommet"));
  if (best || !index) {
    return best ?? { point: p, kind: "libre" };
  }
  const candidates = index.near(p, tolerance).slice(0, MAX_CANDIDATES);
  candidates.forEach((id) => {
    const [x1, y1, x2, y2] = index.segments[id];
    consider([x1, y1], "extremite");
    consider([x2, y2], "extremite");
  });
  if (best) {
    return best;
  }
  for (let i = 0; i < candidates.length; i += 1) {
    for (let j = i + 1; j < candidates.length; j += 1) {
      const point = intersection(index.segments[candidates[i]], index.segments[candidates[j]]);
      if (point) {
        consider(point, "intersection");
      }
    }
  }
  if (best) {
    return best;
  }
  candidates.forEach((id) => {
    const [x1, y1, x2, y2] = index.segments[id];
    consider(projectOnSegment(p, [x1, y1], [x2, y2]).point, "trait");
  });
  return best ?? { point: p, kind: "libre" };
}

// Maj enfoncée : côté horizontal ou vertical par rapport au sommet précédent.
export function orthogonal(previous: PdfPoint, p: PdfPoint): PdfPoint {
  return Math.abs(p[0] - previous[0]) >= Math.abs(p[1] - previous[1]) ? [p[0], previous[1]] : [previous[0], p[1]];
}
