import type { PdfPoint } from "../api";

/** Secteurs de lecture, identiques à ceux du serveur : on dit le nord en français, pas en degrés. */
const SECTEURS = [
  "vers le haut de la planche",
  "vers le haut à droite",
  "vers la droite de la planche",
  "vers le bas à droite",
  "vers le bas de la planche",
  "vers le bas à gauche",
  "vers la gauche de la planche",
  "vers le haut à gauche",
];

/**
 * Angle du nord depuis le haut de l'écran, dans le sens horaire.
 *
 * La flèche est stockée en points PDF ; l'image affichée en découle par la matrice du rendu
 * (`px = a·x + c·y + e`, `py = b·x + d·y + f`). Seule la partie linéaire compte : une direction ne se
 * translate pas. Même formule que `thermique_nord.azimut_dans_l_image` côté serveur.
 */
export function azimutEcran(p1: PdfPoint, p2: PdfPoint, transform: number[]): number | null {
  const [a, b, c, d] = transform;
  const dx = p2[0] - p1[0];
  const dy = p2[1] - p1[1];
  const px = a * dx + c * dy;
  const py = b * dx + d * dy;
  if (Math.hypot(px, py) < 1e-9) {
    return null;
  }
  return ((Math.atan2(px, -py) * 180) / Math.PI + 360) % 360;
}

export function lectureDuNord(azimut: number): string {
  return SECTEURS[Math.round(azimut / 45) % 8];
}

export function degres(azimut: number): string {
  return `${Math.round(azimut)}°`;
}
