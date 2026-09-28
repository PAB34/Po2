import type { PdfPoint } from "../api";
import type { ToScreen } from "../components/TileSheetViewer";
import {
  levelFactor,
  pickBackdrop,
  pickLevel,
  rasterToPdf,
  tileSrc,
  visibleTiles,
  type RasterManifest,
  type TileRef,
} from "../raster";
import { appliquer, type Similitude } from "./superposition";

type Affine = { a: number; b: number; c: number; d: number; e: number; f: number };

/**
 * Pixels de l'image du voisin → écran du plan actif. Toute la chaîne est affine (rendu pdfium, similitude
 * du calage, cadrage de l'écran) : trois points suffisent à la connaître.
 */
export function versEcran(manifest: RasterManifest, sim: Similitude, toScreen: ToScreen): Affine {
  const f = (px: number, py: number) => toScreen(appliquer(sim, rasterToPdf(manifest.transform, px, py)));
  const [e, ff] = f(0, 0);
  const [x1, y1] = f(1, 0);
  const [x2, y2] = f(0, 1);
  return { a: x1 - e, b: y1 - ff, c: x2 - e, d: y2 - ff, e, f: ff };
}

function inverse(m: Affine, [x, y]: [number, number]): [number, number] {
  const det = m.a * m.d - m.b * m.c;
  const dx = x - m.e;
  const dy = y - m.f;
  return [(m.d * dx - m.c * dy) / det, (m.a * dy - m.b * dx) / det];
}

/** Les tuiles du voisin qui se voient à l'écran : un fond complet, et le niveau fin sur la zone visible. */
export function tuilesVisibles(manifest: RasterManifest, m: Affine, taille: { width: number; height: number }, dpr = 1): TileRef[] {
  const echelle = Math.sqrt(Math.abs(m.a * m.d - m.b * m.c));
  const fond = pickBackdrop(manifest);
  const fin = pickLevel(manifest, echelle * dpr);
  const coins = [
    inverse(m, [0, 0]),
    inverse(m, [taille.width, 0]),
    inverse(m, [0, taille.height]),
    inverse(m, [taille.width, taille.height]),
  ];
  const xs = coins.map(([x]) => x);
  const ys = coins.map(([, y]) => y);
  const zone = { x0: Math.min(...xs), y0: Math.min(...ys), x1: Math.max(...xs), y1: Math.max(...ys) };
  return [...visibleTiles(manifest, fond, null), ...(fin.z > fond.z ? visibleTiles(manifest, fin, zone) : [])];
}

/**
 * Les points déjà cliqués pendant un calage (D173) : croix de couleur sur le calque, croix noire sur le plan,
 * reliées d'un trait — on voit de combien il faut déplacer le voisin.
 */
export function PointsDeCalage({
  calage,
  sim,
  toScreen,
}: {
  calage: { sens: "inferieur" | "superieur"; paires: [PdfPoint, PdfPoint][]; enAttente: PdfPoint | null };
  sim: Similitude | null;
  toScreen: ToScreen;
}) {
  if (!sim) return null;
  const croix = (point: PdfPoint, classe: string, cle: string) => {
    const [x, y] = toScreen(point);
    return (
      <g key={cle} className={classe}>
        <line x1={x - 7} y1={y} x2={x + 7} y2={y} />
        <line x1={x} y1={y - 7} x2={x} y2={y + 7} />
        <circle cx={x} cy={y} r={3} />
      </g>
    );
  };
  return (
    <g className={`th-calage-points th-calage-points--${calage.sens}`}>
      {calage.paires.map(([surVoisin, surPlan], rang) => {
        const [x1, y1] = toScreen(appliquer(sim, surVoisin));
        const [x2, y2] = toScreen(surPlan);
        return (
          <g key={rang}>
            <line className="th-calage-points__lien" x1={x1} y1={y1} x2={x2} y2={y2} />
            {croix(appliquer(sim, surVoisin), "th-calage-points__voisin", `v${rang}`)}
            {croix(surPlan, "th-calage-points__plan", `p${rang}`)}
          </g>
        );
      })}
      {calage.enAttente && croix(appliquer(sim, calage.enAttente), "th-calage-points__voisin", "attente")}
    </g>
  );
}

/**
 * Le niveau du dessous ou du dessus, en transparence sur le plan actif (S3, D168).
 *
 * Le trait du voisin est teinté — bleu pour le dessous, orange pour le dessus — et multiplié avec le plan :
 * le blanc disparaît, seuls restent ses traits, lisibles sous ceux du plan actif.
 */
export function NiveauFantome({
  manifest,
  tileTemplate,
  sim,
  toScreen,
  taille,
  sens,
}: {
  manifest: RasterManifest;
  tileTemplate: string;
  sim: Similitude;
  toScreen: ToScreen;
  taille: { width: number; height: number };
  sens: "inferieur" | "superieur";
}) {
  const m = versEcran(manifest, sim, toScreen);
  const tuiles = tuilesVisibles(manifest, m, taille, typeof window === "undefined" ? 1 : window.devicePixelRatio || 1);
  const filtre = `th-fantome-teinte-${sens}`;
  // Teinte : chaque canal devient (1 − c)·luminance + c — le noir prend la couleur c, le blanc reste blanc.
  const couleur = sens === "inferieur" ? [0.1, 0.35, 0.95] : [0.95, 0.45, 0.05];
  const ligne = (c: number) => `${(1 - c) / 3} ${(1 - c) / 3} ${(1 - c) / 3} 0 ${c}`;
  return (
    <g className={`th-fantome th-fantome--${sens}`} aria-hidden="true">
      <defs>
        <filter id={filtre} colorInterpolationFilters="sRGB">
          <feColorMatrix type="matrix" values={`${ligne(couleur[0])} ${ligne(couleur[1])} ${ligne(couleur[2])} 0 0 0 1 0`} />
        </filter>
      </defs>
      <g transform={`matrix(${m.a} ${m.b} ${m.c} ${m.d} ${m.e} ${m.f})`} filter={`url(#${filtre})`}>
        {tuiles.map((tuile) => {
          const cote = manifest.tile_size / levelFactor(manifest, manifest.levels[tuile.z]);
          return (
            <image
              key={`${tuile.z}/${tuile.x}/${tuile.y}`}
              href={tileSrc(tileTemplate, tuile)}
              x={tuile.x * cote}
              y={tuile.y * cote}
              width={cote}
              height={cote}
              preserveAspectRatio="none"
            />
          );
        })}
      </g>
    </g>
  );
}
