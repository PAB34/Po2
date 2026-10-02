import type { PdfPoint } from "../api";
import type { ToScreen } from "../components/TileSheetViewer";
import type { Extremite } from "./murs";

/** Le mur en cours de tracé (D250) : du premier point au curseur, avec sa longueur. */
export function TraceDuMur({
  premier,
  survol,
  longueur_m,
  toScreen,
}: {
  premier: PdfPoint;
  survol: PdfPoint | null;
  longueur_m: number | null;
  toScreen: ToScreen;
}) {
  const [ax, ay] = toScreen(premier);
  const [bx, by] = toScreen(survol ?? premier);
  return (
    <g className="th-poignees">
      <line className="th-poignees__ligne" x1={ax} y1={ay} x2={bx} y2={by} />
      {longueur_m != null && longueur_m > 0 && (
        <text className="th-poignees__longueur" x={(ax + bx) / 2} y={(ay + by) / 2 - 10} textAnchor="middle">
          {longueur_m.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m
        </text>
      )}
      <circle className="th-poignees__rond is-active" cx={ax} cy={ay} r={6} />
    </g>
  );
}

/**
 * Les deux poignées de la ligne de métré du mur désigné (D249). Pendant le glisser, la ligne suit le curseur
 * et affiche sa longueur ; un rond plein signale l'aimant accroché à l'extrémité d'un autre mur.
 */
export function PoigneesDuMur({
  extremites,
  glisse,
  toScreen,
}: {
  extremites: Record<Extremite, PdfPoint>;
  glisse: { extremite: Extremite; point: PdfPoint; longueur_m: number | null; aimante: boolean } | null;
  toScreen: ToScreen;
}) {
  const bouts: Record<Extremite, PdfPoint> = glisse ? { ...extremites, [glisse.extremite]: glisse.point } : extremites;
  const [ax, ay] = toScreen(bouts.debut);
  const [bx, by] = toScreen(bouts.fin);
  return (
    <g className="th-poignees">
      {glisse && (
        <>
          <line className="th-poignees__ligne" x1={ax} y1={ay} x2={bx} y2={by} />
          {glisse.longueur_m != null && (
            <text className="th-poignees__longueur" x={(ax + bx) / 2} y={(ay + by) / 2 - 10} textAnchor="middle">
              {glisse.longueur_m.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m
            </text>
          )}
        </>
      )}
      {(["debut", "fin"] as const).map((extremite) => {
        const [x, y] = toScreen(bouts[extremite]);
        const active = glisse?.extremite === extremite;
        return (
          <circle
            key={extremite}
            className={`th-poignees__rond${active ? " is-active" : ""}${active && glisse?.aimante ? " is-aimante" : ""}`}
            cx={x}
            cy={y}
            r={7}
          >
            <title>{extremite === "debut" ? "Début du mur : glissez pour le déplacer" : "Fin du mur : glissez pour la déplacer"}</title>
          </circle>
        );
      })}
    </g>
  );
}
