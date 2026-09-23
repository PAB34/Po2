import type { PdfPoint, StudyLimit, StudyRoom } from "../api";

/** Un côté sur l'enveloppe ou le long d'une paroi lue est ancré : on prévient avant de le déplacer. */
export const LIMIT_LABELS: Record<StudyLimit, string> = {
  exterieur: "sur l'enveloppe",
  paroi: "le long d'une paroi lue",
  convention: "limite d'usage",
};

export const LIMIT_COLORS: Record<StudyLimit, string> = {
  exterieur: "#b3261e",
  paroi: "#1f6f43",
  convention: "#8a5cf6",
};

export type EditMode = "contour" | "couper";

export type StudyDraft = {
  roomId: string;
  mode: EditMode;
  /** Contour de travail, en points PDF ; il ne part au serveur qu'au recalcul. */
  contour: PdfPoint[];
  /** Trait de coupe en cours, en points PDF. */
  cut: PdfPoint[];
  nature: StudyRoom["nature"];
  nom: string;
  /** Noms des deux moitiés, en mode « couper ». */
  noms: [string, string];
};

export function draftFromRoom(room: StudyRoom, mode: EditMode = "contour"): StudyDraft {
  return {
    roomId: room.id,
    mode,
    contour: room.contour_pdf.map((point) => [...point] as PdfPoint),
    cut: [],
    nature: room.nature,
    nom: room.nom,
    noms: [room.nom, `${room.nom} (suite)`],
  };
}

const distance = (a: PdfPoint, b: PdfPoint) => Math.hypot(a[0] - b[0], a[1] - b[1]);

export function nearestVertex(contour: PdfPoint[], point: PdfPoint, tolerance: number): number | null {
  let best: number | null = null;
  let bestDistance = tolerance;
  contour.forEach((vertex, index) => {
    const gap = distance(vertex, point);
    if (gap <= bestDistance) {
      best = index;
      bestDistance = gap;
    }
  });
  return best;
}

/** Distance d'un point au segment [a, b], et position relative du projeté (0 à 1). */
function projection(point: PdfPoint, a: PdfPoint, b: PdfPoint): { gap: number; ratio: number } {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const longueur = dx * dx + dy * dy;
  if (longueur === 0) {
    return { gap: distance(point, a), ratio: 0 };
  }
  const brut = ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / longueur;
  const ratio = Math.min(1, Math.max(0, brut));
  const projete: PdfPoint = [a[0] + ratio * dx, a[1] + ratio * dy];
  return { gap: distance(point, projete), ratio };
}

/** Côté le plus proche d'un point : renvoie l'indice de son premier sommet. */
export function nearestSide(contour: PdfPoint[], point: PdfPoint, tolerance: number): number | null {
  let best: number | null = null;
  let bestGap = tolerance;
  contour.forEach((vertex, index) => {
    const { gap } = projection(point, vertex, contour[(index + 1) % contour.length]);
    if (gap <= bestGap) {
      best = index;
      bestGap = gap;
    }
  });
  return best;
}

export function moveVertex(contour: PdfPoint[], index: number, point: PdfPoint): PdfPoint[] {
  return contour.map((vertex, rank) => (rank === index ? ([point[0], point[1]] as PdfPoint) : vertex));
}

export function insertVertex(contour: PdfPoint[], point: PdfPoint, tolerance: number): PdfPoint[] {
  const side = nearestSide(contour, point, tolerance);
  if (side === null) {
    return contour;
  }
  const suite = [...contour];
  suite.splice(side + 1, 0, [point[0], point[1]] as PdfPoint);
  return suite;
}

export function removeVertex(contour: PdfPoint[], index: number): PdfPoint[] {
  // Un local garde au moins un triangle.
  return contour.length <= 3 ? contour : contour.filter((_vertex, rank) => rank !== index);
}

export function contourChanged(room: StudyRoom, contour: PdfPoint[]): boolean {
  if (room.contour_pdf.length !== contour.length) {
    return true;
  }
  return room.contour_pdf.some((point, index) => point[0] !== contour[index][0] || point[1] !== contour[index][1]);
}

/** Côtés d'un local dont la limite n'est pas ancrée : ceux que le thermicien peut bouger sans risque. */
export function freeSides(room: StudyRoom): number {
  return (room.limites ?? []).filter((limite) => limite === "convention").length;
}

export function coverageTone(pct: number): "ok" | "warn" {
  return pct >= 99 ? "ok" : "warn";
}
