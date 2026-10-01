import type { Baie, MenuiseriesDuProjet, PdfPoint, StudyReleveElement } from "../api";

const M_PAR_PT = 0.0254 / 72;
const PROPOSITION_CM = 5; // D194

export const menuiseriesQueryKey = (projectId: number) => ["thermique", "menuiseries", projectId] as const;

/** La baie (D199) qui contient ce morceau du relevé, sur ce niveau. */
export function baieDeElement(
  menuiseries: MenuiseriesDuProjet | undefined,
  sheetId: number | null,
  element: Pick<StudyReleveElement, "troncon" | "debut_m" | "fin_m">,
): Baie | null {
  for (const fiche of menuiseries?.composants ?? []) {
    for (const baie of fiche.baies) {
      if (baie.sheet_id !== sheetId) continue;
      if (
        baie.morceaux.some(
          (m) => m.troncon === element.troncon && Math.abs(m.debut_m - element.debut_m) < 0.002 && Math.abs(m.fin_m - element.fin_m) < 0.002,
        )
      ) {
        return baie;
      }
    }
  }
  return null;
}

/** D'où vient la hauteur d'une baie, en clair. */
export function provenanceBaie(baie: Baie): string {
  switch (baie.source) {
    case "modele":
      return `modèle « ${baie.modele} » mesuré sur ${baie.vue}`;
    case "baie":
      return `mesurée pour cette baie sur ${baie.vue}`;
    case "composant":
      return `mesurée sur ${baie.vue}, pour toutes les ${baie.composant}`;
    case "hauteur_du_local":
      return "mur-rideau : hauteur sous plafond du local qu'il borde";
    default:
      return "à lire sur une élévation";
  }
}

/** Largeur et hauteur (m) entre deux coins opposés cliqués sur une élévation, selon son haut (D193). */
export function mesureDeDeuxCoins(
  a: PdfPoint,
  b: PdfPoint,
  haut: [number, number],
  echelle: number,
): { largeur_m: number; hauteur_m: number } {
  const norme = Math.hypot(haut[0], haut[1]) || 1;
  const hx = haut[0] / norme;
  const hy = haut[1] / norme;
  const dx = hy;
  const dy = -hx;
  const m = M_PAR_PT * echelle;
  return {
    largeur_m: Math.abs((b[0] - a[0]) * dx + (b[1] - a[1]) * dy) * m,
    hauteur_m: Math.abs((b[0] - a[0]) * hx + (b[1] - a[1]) * hy) * m,
  };
}

/** Les composants qui ont une baie à ± 5 cm de la largeur mesurée, la plus proche d'abord (D194). */
export function proposerComposants(
  menuiseries: MenuiseriesDuProjet | undefined,
  largeurCm: number,
): { composant: string; baie: Baie; ecart_cm: number }[] {
  const proches: { composant: string; baie: Baie; ecart_cm: number }[] = [];
  for (const fiche of menuiseries?.composants ?? []) {
    let meilleure: Baie | null = null;
    for (const baie of fiche.baies) {
      if (!meilleure || Math.abs(baie.largeur_cm - largeurCm) < Math.abs(meilleure.largeur_cm - largeurCm)) meilleure = baie;
    }
    if (meilleure && Math.abs(meilleure.largeur_cm - largeurCm) <= PROPOSITION_CM) {
      proches.push({ composant: fiche.composant, baie: meilleure, ecart_cm: Math.round(Math.abs(meilleure.largeur_cm - largeurCm) * 10) / 10 });
    }
  }
  return proches.sort((a, b) => a.ecart_cm - b.ecart_cm);
}
