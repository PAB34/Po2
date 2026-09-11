import type { PdfPoint } from "./api";

// 1 point PDF = 25,4/72 mm sur le papier. À 1/N, 1 pt vaut 0,3528 × N mm réels.
export const PT_TO_MM = 25.4 / 72;
export const COMMON_SCALES = [20, 50, 100, 200, 500];

export function distancePt(a: PdfPoint, b: PdfPoint): number {
  return Math.hypot(b[0] - a[0], b[1] - a[1]);
}

export function paperPtToRealM(lengthPt: number, denominator: number): number {
  return (lengthPt * PT_TO_MM * denominator) / 1000;
}

export function denominatorFromMeasure(lengthPt: number, realLengthM: number): number {
  return (realLengthM * 1000) / (lengthPt * PT_TO_MM);
}

const metersFormat = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const scaleFormat = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });

export function formatMeters(value: number): string {
  return `${metersFormat.format(value)} m`;
}

export function formatScale(denominator: number | null): string {
  return denominator ? `1/${scaleFormat.format(denominator)}` : "non définie";
}

export function parseDecimal(value: string): number | null {
  const parsed = Number(value.replace(/\s/g, "").replace(",", "."));
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}
