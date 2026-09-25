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

export type EditMode = "contour" | "couper" | "ajouter";

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
  /** Lasso en cours (Alt + glisser), pour entourer et supprimer plusieurs sommets d'un coup. */
  lasso?: Lasso | null;
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

/** Tracé du lasso : la suite des points parcourus, refermée d'elle-même au relâchement. */
export type Lasso = PdfPoint[];

/** Le point est-il dans le polygone ? Lancer de rayon : vaut pour n'importe quelle forme, même creuse. */
export function pointInPolygon(polygone: readonly (readonly [number, number])[], x: number, y: number): boolean {
  let dedans = false;
  for (let rang = 0, avant = polygone.length - 1; rang < polygone.length; avant = rang++) {
    const [xi, yi] = polygone[rang];
    const [xj, yj] = polygone[avant];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) {
      dedans = !dedans;
    }
  }
  return dedans;
}

export function verticesInLasso(contour: PdfPoint[], lasso: Lasso): number[] {
  if (lasso.length < 3) {
    return [];
  }
  return contour.reduce<number[]>((rangs, [x, y], rang) => {
    if (pointInPolygon(lasso, x, y)) {
      rangs.push(rang);
    }
    return rangs;
  }, []);
}

/**
 * Supprime d'un coup tous les sommets entourés par le lasso.
 *
 * Aplanir une dentelle de vingt points au droit d'alcôves demandait vingt gestes : le contour passe
 * alors tout droit du sommet qui précède à celui qui suit. Le lasso se referme tout seul entre son
 * dernier point et son premier. Le local garde toujours au moins un triangle, donc on ne retire
 * jamais au-delà.
 */
export function removeVerticesInLasso(
  contour: PdfPoint[],
  lasso: Lasso,
): { contour: PdfPoint[]; removed: number; refus?: "vide" | "trop" } {
  const vises = new Set(verticesInLasso(contour, lasso));
  if (vises.size === 0) {
    return { contour, removed: 0, refus: "vide" };
  }
  const restant = contour.filter((_vertex, rang) => !vises.has(rang));
  if (restant.length < 3) {
    // Au zoom d'ensemble, un petit geste couvre tout le local : on refuse, et on le dit clairement.
    return { contour, removed: 0, refus: "trop" };
  }
  return { contour: restant, removed: contour.length - restant.length };
}

// Au-delà, deux segments ne sont plus dans le prolongement l'un de l'autre : le côté s'arrête là.
const ALIGNEMENT_MAX_DEG = 8;

function capMoyen(a: PdfPoint, b: PdfPoint): number {
  return (Math.atan2(b[1] - a[1], b[0] - a[0]) * 180) / Math.PI;
}

function ecartAngulaire(alpha: number, beta: number): number {
  // En JavaScript, `%` garde le signe : le double modulo évite qu'un passage de -179° à +179°
  // produise un faux écart négatif.
  const brut = Math.abs(((((alpha - beta + 180) % 360) + 360) % 360) - 180);
  // Un segment parcouru à l'envers reste aligné.
  return Math.min(brut, 180 - brut);
}

export function draftForNewRoom(first: PdfPoint): StudyDraft {
  return {
    roomId: "",
    mode: "ajouter",
    contour: [[first[0], first[1]]],
    cut: [],
    nature: "chauffe",
    nom: "Nouveau local",
    noms: ["", ""],
  };
}

/**
 * Redresse le côté visuel qui porte le segment `index` : la suite des segments qui restent dans son
 * prolongement, dont on retire tous les sommets intermédiaires.
 *
 * Ce que l'œil appelle « un côté » est souvent une suite de petits segments presque alignés, laissés
 * par la lecture du plan. Les retirer un à un est le travail que ce geste supprime.
 */
export function straightenSide(contour: PdfPoint[], index: number): { contour: PdfPoint[]; removed: number } {
  const total = contour.length;
  if (total <= 3) {
    return { contour, removed: 0 };
  }
  const cap = capMoyen(contour[index], contour[(index + 1) % total]);
  const aligne = (rang: number) =>
    ecartAngulaire(capMoyen(contour[rang % total], contour[(rang + 1) % total]), cap) <= ALIGNEMENT_MAX_DEG;

  let debut = index;
  let fin = index;
  while (fin - debut < total - 2 && aligne(fin + 1)) {
    fin += 1;
  }
  while (fin - debut < total - 2 && aligne(debut - 1 + total)) {
    debut -= 1;
  }
  // Les sommets strictement entre le premier et le dernier du côté disparaissent.
  const aRetirer = new Set<number>();
  for (let rang = debut + 1; rang <= fin; rang += 1) {
    aRetirer.add(((rang % total) + total) % total);
  }
  if (aRetirer.size === 0 || total - aRetirer.size < 3) {
    return { contour, removed: 0 };
  }
  return {
    contour: contour.filter((_vertex, rang) => !aRetirer.has(rang)),
    removed: aRetirer.size,
  };
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
