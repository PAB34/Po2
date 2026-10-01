import type { HautDeVue } from "../api";

// Le haut d'une vue est un vecteur de la page PDF (y vers le haut) ; le thermicien, lui, voit la planche
// tournée. Tout ce qu'il choisit ou lit du haut passe par la transformation du raster affiché (D207, D208).

const ECRAN: Record<HautDeVue, [number, number]> = { haut: [0, -1], bas: [0, 1], gauche: [-1, 0], droite: [1, 0] };

/** Le côté de la page vers lequel pointe un vecteur de page (y vers le haut). */
export function cotePage(v: [number, number]): HautDeVue {
  const [x, y] = v;
  if (Math.abs(x) > Math.abs(y)) return x > 0 ? "droite" : "gauche";
  return y < 0 ? "bas" : "haut";
}

/** Le côté de l'écran vers lequel pointe un vecteur de page, avec le raster affiché (y de l'écran vers le bas). */
export function coteEcran(haut: [number, number], transform: number[]): HautDeVue {
  const [a, b, c, d] = transform;
  const x = a * haut[0] + c * haut[1];
  const y = b * haut[0] + d * haut[1];
  if (Math.abs(x) > Math.abs(y)) return x > 0 ? "droite" : "gauche";
  return y > 0 ? "bas" : "haut";
}

/** Le côté de la page qui apparaît, à l'écran, du côté choisi par le thermicien. */
export function pageDuCoteEcran(cote: HautDeVue, transform: number[]): HautDeVue {
  const [a, b, c, d] = transform;
  const [sx, sy] = ECRAN[cote];
  const det = a * d - b * c || 1;
  return cotePage([(d * sx - c * sy) / det, (a * sy - b * sx) / det]);
}

const QUART_HORAIRE: Record<HautDeVue, HautDeVue> = { haut: "droite", droite: "bas", bas: "gauche", gauche: "haut" };

/** La rotation d'affichage (degrés horaires, comme le raster) qui met le haut de la vue en haut de l'écran.
 *
 * `transform` est celle du raster affiché à `rotation` ; chaque quart de tour horaire envoie le haut de
 * l'écran à droite.
 */
export function rotationALEndroit(haut: [number, number], transform: number[], rotation: number): number {
  let cote = coteEcran(haut, transform);
  let quarts = 0;
  while (cote !== "haut" && quarts < 4) {
    cote = QUART_HORAIRE[cote];
    quarts += 1;
  }
  return (((rotation + 90 * quarts) % 360) + 360) % 360;
}
