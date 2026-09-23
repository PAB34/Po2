import type { PdfPoint, SheetNorth } from "../api";
import type { ToScreen } from "../components/TileSheetViewer";

/**
 * La flèche du nord sur le plan, et celle en cours de tracé.
 *
 * Une seule lecture possible : la flèche part de sa base et **pointe vers le nord**, avec un « N » à sa
 * pointe. C'est le geste du crayon sur un tirage papier.
 */
export function NorthOverlay({
  nord,
  enCours,
  toScreen,
  actif,
}: {
  nord: SheetNorth | null;
  /** Points déjà cliqués pendant le tracé : [base] puis [base, pointe]. */
  enCours: PdfPoint[];
  toScreen: ToScreen;
  actif: boolean;
}) {
  // Les points sont partagés par les outils de mesure et de calage : ils ne deviennent une flèche
  // provisoire que lorsque l'outil Nord est réellement actif (D90).
  const brouillon = actif && enCours.length >= 2 ? { p1: enCours[0], p2: enCours[1] } : null;
  if (actif && enCours.length === 1) {
    const [x, y] = toScreen(enCours[0]);
    return (
      <g className="th-north is-draft is-active">
        <circle className="th-north__base" cx={x} cy={y} r={5} />
        <text className="th-north__base-label" x={x + 10} y={y - 10}>
          base
        </text>
        <title>Base de la flèche posée : cliquez maintenant sa pointe, du côté du nord</title>
      </g>
    );
  }
  const pose = brouillon ?? (nord ? { p1: nord.p1, p2: nord.p2 } : null);
  if (!pose) {
    return null;
  }
  const [x1, y1] = toScreen(pose.p1);
  const [x2, y2] = toScreen(pose.p2);
  const longueur = Math.hypot(x2 - x1, y2 - y1);
  if (longueur < 1) {
    return null;
  }
  const ux = (x2 - x1) / longueur;
  const uy = (y2 - y1) / longueur;
  // Pointe : deux ailerons à 30° de l'axe, dimensionnés à l'écran pour rester lisibles à tout zoom.
  const aile = Math.min(16, Math.max(8, longueur * 0.25));
  const gauche = [x2 - ux * aile - uy * aile * 0.5, y2 - uy * aile + ux * aile * 0.5];
  const droite = [x2 - ux * aile + uy * aile * 0.5, y2 - uy * aile - ux * aile * 0.5];
  return (
    <g className={`th-north${brouillon ? " is-draft" : ""}${actif ? " is-active" : ""}`}>
      <line x1={x1} y1={y1} x2={x2} y2={y2} />
      <polygon points={`${x2},${y2} ${gauche[0]},${gauche[1]} ${droite[0]},${droite[1]}`} />
      <circle className="th-north__base" cx={x1} cy={y1} r={3} />
      <text x={x2 + ux * 16} y={y2 + uy * 16} textAnchor="middle" dominantBaseline="central">
        N
      </text>
      <title>Nord de la planche : la flèche pointe vers le nord</title>
    </g>
  );
}
