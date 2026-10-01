import type { PdfPoint } from "../api";
import type { ViewerSegment } from "../components/TileSheetViewer";

// Ce qui se mesure dans une coupe ou une façade se voit pendant qu'on mesure (D211) : le rectangle de la
// menuiserie et ses deux cotes, la hauteur entre le sol et le plafond, le long du haut de la vue.

const M_PAR_PT = 0.0254 / 72;
export const HAUTEUR_MIN_M = 1.5;
export const HAUTEUR_MAX_M = 15;
const HAUTEUR_COURANTE: [number, number] = [2, 6];
const MENUISERIE_MIN_M = 0.2;

const metres = (v: number) => `${v.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m`;

function axes(haut: [number, number]): { h: [number, number]; d: [number, number] } {
  const norme = Math.hypot(haut[0], haut[1]) || 1;
  const h: [number, number] = [haut[0] / norme, haut[1] / norme];
  return { h, d: [h[1], -h[0]] };
}

const projeter = (v: [number, number], axe: [number, number]) => v[0] * axe[0] + v[1] * axe[1];

/** Le rectangle d'une menuiserie entre deux coins, ses côtés suivant les axes de la vue, cotés en mètres. */
export function rectangleDeMenuiserie(a: PdfPoint, b: PdfPoint, haut: [number, number], echelle: number): ViewerSegment[] {
  const { h, d } = axes(haut);
  const v: [number, number] = [b[0] - a[0], b[1] - a[1]];
  const largeur = projeter(v, d);
  const hauteur = projeter(v, h);
  const c1: PdfPoint = [a[0] + largeur * d[0], a[1] + largeur * d[1]];
  const c2: PdfPoint = [a[0] + hauteur * h[0], a[1] + hauteur * h[1]];
  const m = M_PAR_PT * echelle;
  return [
    { p1: a, p2: c1, label: metres(Math.abs(largeur) * m), tone: "measure" },
    { p1: c1, p2: b, label: metres(Math.abs(hauteur) * m), tone: "measure" },
    { p1: b, p2: c2, tone: "measure" },
    { p1: c2, p2: a, tone: "measure" },
  ];
}

/** La hauteur entre le sol cliqué et le point visé, comptée le long du haut de la vue. */
export function segmentDeHauteur(sol: PdfPoint, vise: PdfPoint, haut: [number, number], echelle: number): ViewerSegment {
  const { h } = axes(haut);
  const montee = projeter([vise[0] - sol[0], vise[1] - sol[1]], h);
  return {
    p1: sol,
    p2: [sol[0] + montee * h[0], sol[1] + montee * h[1]],
    label: metres(montee * M_PAR_PT * echelle),
    tone: "measure",
  };
}

export type AvisHauteur = { bloquant: boolean; texte: string } | null;

/** Une hauteur d'étage impossible bloque ; une hauteur inhabituelle se signale. */
export function avisSurLaHauteur(hauteur: number): AvisHauteur {
  if (hauteur < HAUTEUR_MIN_M || hauteur > HAUTEUR_MAX_M) {
    return {
      bloquant: true,
      texte:
        `Les deux clics donnent ${metres(hauteur)} : ce n'est pas une hauteur d'étage. Cliquez le sol fini puis le ` +
        "plafond fini d'une même pièce ; si le dessin est couché, redressez-le d'abord (« Dessin de travers ? »).",
    };
  }
  if (hauteur < HAUTEUR_COURANTE[0] || hauteur > HAUTEUR_COURANTE[1]) {
    return { bloquant: false, texte: `${metres(hauteur)} : hauteur inhabituelle, vérifiez les deux clics.` };
  }
  return null;
}

/** Une menuiserie trop fine dans un sens trahit deux coins mal cliqués ou une vue de travers. */
export function avisSurLaMenuiserie(largeur: number, hauteur: number): string | null {
  if (largeur >= MENUISERIE_MIN_M && hauteur >= MENUISERIE_MIN_M) return null;
  return "Mesure suspecte : cliquez deux coins opposés de la baie (en diagonale) ; si le dessin est couché, redressez-le d'abord.";
}
