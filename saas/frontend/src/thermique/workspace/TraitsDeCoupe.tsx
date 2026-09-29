import type { HauteursDuPlan, PdfPoint } from "../api";
import type { ToScreen } from "../components/TileSheetViewer";
import { distanceAuSegment } from "./elements";

/** Un trait de coupe montrable et cliquable sur le plan (S5, D171) : relevé sur le plan ou déduit (D190). */
export type TraitCliquable = {
  nom: string;
  points: PdfPoint[];
  sens: [number, number];
  deduit: boolean;
  vueId: number;
  /** Trait d'une façade (S5e, D182) : dessiné le long de l'enveloppe, dans sa propre couleur. */
  facade?: boolean;
  /** Une façade se dessine en plusieurs tronçons : seul le premier porte son nom. */
  etiquette?: boolean;
};

/** Les traits du niveau reliés à la vue qu'ils ouvrent ; un trait sans coupe lue n'est pas cliquable. */
export function traitsCliquables(hauteurs: HauteursDuPlan | undefined): TraitCliquable[] {
  if (!hauteurs) return [];
  return hauteurs.traits.flatMap((trait) => {
    const lecture = hauteurs.coupes.find((coupe) => coupe.trait === trait.nom);
    const vueId = trait.vue_id ?? lecture?.vue_id;
    if (!vueId || !trait.points || trait.points.length < 2) return [];
    return [{ nom: trait.nom, points: trait.points, sens: trait.sens, deduit: Boolean(trait.deduit), vueId }];
  });
}

/** Le trait le plus proche du point, dans la tolérance (points PDF). */
export function traitAt(traits: TraitCliquable[], point: PdfPoint, tolerance: number): TraitCliquable | null {
  let meilleur: TraitCliquable | null = null;
  let distance = tolerance;
  for (const trait of traits) {
    for (let i = 1; i < trait.points.length; i += 1) {
      const d = distanceAuSegment(point, trait.points[i - 1], trait.points[i]);
      if (d <= distance) {
        distance = d;
        meilleur = trait;
      }
    }
  }
  return meilleur;
}

/** Les traits en lignes épaisses, avec leur nom et une flèche du côté où l'on regarde. */
export function TraitsDeCoupe({ traits, toScreen }: { traits: TraitCliquable[]; toScreen: ToScreen }) {
  return (
    <g className="th-traits-coupe">
      {traits.map((trait, rang) => {
        const ecran = trait.points.map(toScreen);
        const [ax, ay] = ecran[0];
        const [bx, by] = ecran[ecran.length - 1];
        // Le sens est un vecteur du repère PDF (y vers le haut) ; à l'écran, y descend.
        const fleche = (x: number, y: number) => {
          const norme = Math.hypot(trait.sens[0], trait.sens[1]) || 1;
          const ux = trait.sens[0] / norme;
          const uy = -trait.sens[1] / norme;
          return `M ${x} ${y} L ${x + ux * 18} ${y + uy * 18}`;
        };
        return (
          <g
            key={`${trait.nom}-${trait.vueId}-${rang}`}
            className={`th-trait-coupe${trait.deduit ? " is-deduit" : ""}${trait.facade ? " is-facade" : ""}`}
          >
            <polyline points={ecran.map(([x, y]) => `${x},${y}`).join(" ")} />
            {!trait.facade && <path className="th-trait-coupe__fleche" d={`${fleche(ax, ay)} ${fleche(bx, by)}`} />}
            {(trait.etiquette ?? true) && (
              <text x={(ax + bx) / 2} y={(ay + by) / 2 - 8} textAnchor="middle">
                {trait.nom}
              </text>
            )}
            <title>
              {trait.facade
                ? `${trait.nom} : cliquez pour ouvrir l'élévation`
                : `${trait.nom}${trait.deduit ? " (situé d'après la coupe)" : ""} : cliquez pour ouvrir la coupe`}
            </title>
          </g>
        );
      })}
    </g>
  );
}
