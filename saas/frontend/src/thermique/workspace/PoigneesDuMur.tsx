import type { PdfPoint } from "../api";
import type { ToScreen } from "../components/TileSheetViewer";
import type { Extremite } from "./murs";

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
