import type { PdfPoint, StudyBridge, StudyElementRef, StudyEnvelopeShape, StudyRoom, StudySide } from "../api";
import type { ToScreen } from "../components/TileSheetViewer";
import { pointInPolygon } from "./edition";
import { memeElement, refDeForme } from "./elements";

/** Ce que l'on montre au-delà du local sélectionné (D83). Le local sélectionné, lui, montre tout. */
export type MetricsShow = {
  metres: boolean;
  ponts: boolean;
  elements: boolean;
  /** Inclure les côtés non déperditifs (par défaut on ne cote que ce qui déperd — D73). */
  toutesCotes: boolean;
};

export const METRICS_DEFAUT: MetricsShow = { metres: false, ponts: false, elements: false, toutesCotes: false };

// En dessous, l'étiquette ne serait plus lisible : on garde le trait et on retire le texte (D82).
const COTE_LISIBLE_PX = 62;
const SURFACE_LISIBLE_PX = 74;
// Décalage de l'étiquette par rapport au côté, vers l'extérieur du local.
const ECART_ETIQUETTE_PX = 13;

const COULEURS_ELEMENT: Record<string, string> = {
  mur_exterieur: "#4a5568",
  isolation: "#d97706",
  doublage: "#7c3aed",
  menuiserie_exterieure: "#2563eb",
  poteau: "#6b7280",
  garde_corps: "#0d9488",
  indetermine: "#dc2626",
};

const COULEURS_PONT: Record<string, string> = {
  angle_sortant: "#dc2626",
  angle_rentrant: "#ea580c",
  about_refend: "#7c3aed",
};

const LIBELLES_PONT: Record<string, string> = {
  angle_sortant: "angle sortant",
  angle_rentrant: "angle rentrant",
  about_refend: "about de refend",
};

/** Sigle lu en vue en plan : une pastille de couleur ne dit pas de quel pont il s'agit. */
const SIGLES_PONT: Record<string, string> = {
  angle_sortant: "AS",
  angle_rentrant: "AR",
  about_refend: "RF",
};

// Deux sigles plus proches que cela se chevaucheraient : on les efface plutôt (même règle que D82).
const SIGLE_LISIBLE_PX = 26;
// En deçà, deux pastilles se confondent à l'œil : on n'en dessine qu'une, qui annonce combien elle
// représente. Le métré n'est pas touché — sur le R+1, les ponts sont bien distincts, jusqu'à 1,4 m
// d'écart ; c'est le tracé de l'enveloppe qui est très découpé (89 tronçons, 67 changements de cap).
const GROUPE_PONT_PX = 15;

const metres = (value: number) => `${value.toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} m`;

/** L'orientation n'est calculée que si le nord du plan est posé ; sinon elle vaut « nord à caler » sur tout
 *  le niveau et n'a rien à faire sur le dessin (D84). */
function orientationLisible(cote: StudySide): string | null {
  const valeur = cote.orientation;
  return valeur && !valeur.toLowerCase().includes("caler") ? valeur : null;
}

function longueurEcran(points: [number, number][]): number {
  let total = 0;
  for (let rang = 1; rang < points.length; rang += 1) {
    total += Math.hypot(points[rang][0] - points[rang - 1][0], points[rang][1] - points[rang - 1][1]);
  }
  return total;
}

/** Milieu de la polyligne, mesuré le long du tracé, et la direction du segment qui le porte. */
function milieu(points: [number, number][]): { x: number; y: number; ux: number; uy: number } | null {
  if (points.length === 0) {
    return null;
  }
  if (points.length === 1) {
    return { x: points[0][0], y: points[0][1], ux: 1, uy: 0 };
  }
  const cible = longueurEcran(points) / 2;
  let parcouru = 0;
  for (let rang = 1; rang < points.length; rang += 1) {
    const [x1, y1] = points[rang - 1];
    const [x2, y2] = points[rang];
    const longueur = Math.hypot(x2 - x1, y2 - y1);
    if (longueur > 0 && parcouru + longueur >= cible) {
      const part = (cible - parcouru) / longueur;
      return { x: x1 + (x2 - x1) * part, y: y1 + (y2 - y1) * part, ux: (x2 - x1) / longueur, uy: (y2 - y1) / longueur };
    }
    parcouru += longueur;
  }
  const [x1, y1] = points[points.length - 2];
  const [x2, y2] = points[points.length - 1];
  const longueur = Math.hypot(x2 - x1, y2 - y1) || 1;
  return { x: x2, y: y2, ux: (x2 - x1) / longueur, uy: (y2 - y1) / longueur };
}

/** Point d'ancrage de l'étiquette de surface : le centre de gravité, ramené dans le local quand celui-ci
 *  est creux (un plateau en L a son centre de gravité dehors). */
function ancre(points: [number, number][]): { x: number; y: number } {
  let aire = 0;
  let cx = 0;
  let cy = 0;
  for (let rang = 0, avant = points.length - 1; rang < points.length; avant = rang++) {
    const croix = points[avant][0] * points[rang][1] - points[rang][0] * points[avant][1];
    aire += croix;
    cx += (points[avant][0] + points[rang][0]) * croix;
    cy += (points[avant][1] + points[rang][1]) * croix;
  }
  if (aire !== 0) {
    const centre = { x: cx / (3 * aire), y: cy / (3 * aire) };
    if (pointInPolygon(points, centre.x, centre.y)) {
      return centre;
    }
    // Centre hors du local : on prend le milieu de la plus large traversée horizontale à cette hauteur.
    const croisements: number[] = [];
    for (let rang = 0, avant = points.length - 1; rang < points.length; avant = rang++) {
      const [xi, yi] = points[rang];
      const [xj, yj] = points[avant];
      if (yi > centre.y !== yj > centre.y) {
        croisements.push(((xj - xi) * (centre.y - yi)) / (yj - yi) + xi);
      }
    }
    croisements.sort((a, b) => a - b);
    let large = 0;
    let x = centre.x;
    for (let rang = 0; rang + 1 < croisements.length; rang += 2) {
      const portee = croisements[rang + 1] - croisements[rang];
      if (portee > large) {
        large = portee;
        x = (croisements[rang] + croisements[rang + 1]) / 2;
      }
    }
    return { x, y: centre.y };
  }
  return { x: points[0]?.[0] ?? 0, y: points[0]?.[1] ?? 0 };
}

function boite(points: [number, number][]): { largeur: number; hauteur: number } {
  const xs = points.map(([x]) => x);
  const ys = points.map(([, y]) => y);
  return { largeur: Math.max(...xs) - Math.min(...xs), hauteur: Math.max(...ys) - Math.min(...ys) };
}

function Cote({ cote, contour, toScreen }: { cote: StudySide; contour: [number, number][]; toScreen: ToScreen }) {
  const trace = (cote.trace_pdf ?? []).map(toScreen) as [number, number][];
  if (trace.length < 2) {
    return null;
  }
  const point = milieu(trace);
  if (!point) {
    return null;
  }
  const lisible = longueurEcran(trace) >= COTE_LISIBLE_PX;
  const centre = ancre(contour);
  // Perpendiculaire au côté, poussée du côté opposé au centre du local.
  let nx = -point.uy;
  let ny = point.ux;
  if ((point.x + nx - centre.x) ** 2 + (point.y + ny - centre.y) ** 2 < (point.x - centre.x) ** 2 + (point.y - centre.y) ** 2) {
    nx = -nx;
    ny = -ny;
  }
  const orientation = orientationLisible(cote);
  return (
    <g className={`th-metric-cote${cote.deperditif ? " is-deperditif" : ""}`}>
      <polyline points={trace.map(([x, y]) => `${x},${y}`).join(" ")} />
      {lisible && (
        <text x={point.x + nx * ECART_ETIQUETTE_PX} y={point.y + ny * ECART_ETIQUETTE_PX} textAnchor="middle">
          <tspan className="th-metric-cote__valeur">{metres(cote.longueur_m)}</tspan>
          <tspan className="th-metric-cote__detail" x={point.x + nx * ECART_ETIQUETTE_PX} dy="1.15em">
            {[`${cote.epaisseur_cm} cm`, orientation].filter(Boolean).join(" · ")}
          </tspan>
        </text>
      )}
      <title>{`${cote.adjacence} · ${metres(cote.longueur_m)} · ${cote.epaisseur_cm} cm${orientation ? ` · ${orientation}` : ""}`}</title>
    </g>
  );
}

/** Le pont visé, reconnu sans le relevé : son abscisse tombe dans les bornes de l'élément désigné. */
function pontVise(bridge: StudyBridge, ref: StudyElementRef | null): boolean {
  if (!ref || bridge.troncon !== ref.troncon || bridge.abscisse_m == null) {
    return false;
  }
  return Math.abs((ref.debut_m + ref.fin_m) / 2 - bridge.abscisse_m) < 1e-6;
}

export function StudyMetrics({
  rooms,
  selected,
  shapes,
  bridges,
  show,
  toScreen,
  selectedElement = null,
}: {
  rooms: StudyRoom[];
  selected: StudyRoom | null;
  shapes: StudyEnvelopeShape[];
  bridges: StudyBridge[];
  show: MetricsShow;
  toScreen: ToScreen;
  /** Élément désigné par le thermicien : il ressort du lot (F4). */
  selectedElement?: StudyElementRef | null;
}) {
  // Le local sélectionné montre tout ; les cases étendent chaque famille au reste du niveau (D83).
  const cotesDe = show.metres ? rooms : selected ? [selected] : [];
  const nomsVises = new Set((show.ponts || show.elements ? rooms : selected ? [selected] : []).map((room) => room.nom));
  const nomSelection = selected?.nom ?? null;
  const visible = (piece: string | null | undefined, etendu: boolean) =>
    piece != null && (piece === nomSelection || (etendu && nomsVises.has(piece)));

  // Les ponts affichés, avec leur position à l'écran : c'est elle qui décide si le sigle tient.
  // Sur le R+1, 77 ponts n'occupent que 48 emplacements distincts — beaucoup se marchent dessus.
  const pontsAffiches = bridges
    .filter(
      (bridge) =>
        // Une liaison que le relevé n'a rattachée à aucun local doit rester visible : l'invisible ne
        // se corrige pas. Elle se dessine en gris avec les ponts du niveau.
        bridge.point_pdf && (visible(bridge.piece, show.ponts) || (show.ponts && bridge.piece == null)),
    )
    .map((bridge) => {
      const [x, y] = toScreen(bridge.point_pdf as PdfPoint);
      return { bridge, x, y, sigleLisible: false };
    });
  // Regroupement visuel : une pastille par amas, qui dit combien de ponts elle porte. Le premier de
  // l'amas la représente ; le clic, lui, vise toujours le pont réellement le plus proche.
  const amas: { bridge: StudyBridge; x: number; y: number; sigleLisible: boolean; nombre: number }[] = [];
  for (const pont of pontsAffiches) {
    const proche = amas.find(
      (groupe) => Math.hypot(groupe.x - pont.x, groupe.y - pont.y) < GROUPE_PONT_PX,
    );
    if (proche && !pontVise(pont.bridge, selectedElement)) {
      proche.nombre += 1;
    } else {
      amas.push({ ...pont, nombre: 1 });
    }
  }
  amas.forEach((pont, rang) => {
    pont.sigleLisible = amas.every(
      (autre, autreRang) => autreRang === rang || Math.hypot(autre.x - pont.x, autre.y - pont.y) >= SIGLE_LISIBLE_PX,
    );
  });

  return (
    <g className="th-metrics">
      {shapes
        .filter((shape) => (shape.points_pdf?.length ?? 0) >= 2 && visible(shape.source_parcours?.piece, show.elements))
        // La forme visée passe en dernier : dessinée avant les autres couches du mur, elle disparaissait
        // dessous. C'est ce qui faisait dire « on ne voit pas l'élément clairement sur le plan ».
        .sort((a, b) => Number(memeElement(refDeForme(a), selectedElement)) - Number(memeElement(refDeForme(b), selectedElement)))
        .map((shape) => {
          const points = (shape.points_pdf ?? []).map(toScreen).map(([x, y]) => `${x},${y}`).join(" ");
          const couleur = COULEURS_ELEMENT[shape.category] ?? COULEURS_ELEMENT.indetermine;
          const vise = memeElement(refDeForme(shape), selectedElement);
          const classes = ["th-metric-element", vise ? "is-selected" : "", shape.review_required ? "is-doute" : ""]
            .filter(Boolean)
            .join(" ");
          const commun = { points, stroke: couleur, className: classes };
          return (
            <g key={shape.id}>
              {vise &&
                (shape.geometry_type === "polygon" ? (
                  <polygon points={points} className="th-metric-element__halo" />
                ) : (
                  <polyline points={points} className="th-metric-element__halo" fill="none" />
                ))}
              {shape.geometry_type === "polygon" ? (
                <polygon {...commun} fill={couleur} fillOpacity={vise ? 0.45 : 0.14} />
              ) : (
                <polyline {...commun} fill="none" />
              )}
              <title>{`${shape.subtype}${shape.review_required ? " · à vérifier" : ""}`}</title>
            </g>
          );
        })}

      {cotesDe.map((room) => {
        const contour = room.contour_pdf.map(toScreen) as [number, number][];
        const taille = boite(contour);
        const centre = ancre(contour);
        // D83 : le local ouvert montre tout, sans réglage. La case « Côtés intérieurs » ne gouverne que
        // le reste du niveau. Sans cette exception, un local dont plus aucun côté ne déperd — ce qui
        // arrive dès qu'un recadrage le décolle de la façade — n'affichait plus une seule cote, sans
        // rien dire au thermicien.
        const tout = show.toutesCotes || room.id === selected?.id;
        return (
          <g key={`metres-${room.id}`}>
            {room.fiche.cotes
              .filter((cote) => (tout || cote.deperditif) && (cote.trace_pdf?.length ?? 0) >= 2)
              .map((cote, rang) => (
                <Cote key={`${room.id}-cote-${rang}`} cote={cote} contour={contour} toScreen={toScreen} />
              ))}
            {Math.min(taille.largeur, taille.hauteur) >= SURFACE_LISIBLE_PX && (
              <text className="th-metric-surface" x={centre.x} y={centre.y} textAnchor="middle">
                {room.surface_m2?.toLocaleString("fr-FR")} m²
              </text>
            )}
          </g>
        );
      })}

      {amas.map(({ bridge, x, y, sigleLisible, nombre }, rang) => {
          const libelle = LIBELLES_PONT[bridge.type] ?? bridge.type;
          const orpheline = bridge.piece == null;
          return (
            <g
              key={`pont-${bridge.troncon}-${rang}`}
              className={`th-metric-pont${orpheline ? " is-orpheline" : ""}${
                pontVise(bridge, selectedElement) ? " is-selected" : ""
              }`}
            >
              {/* Un pont visé n'avait aucun état visible : on ne savait pas ce qu'on venait de cliquer. */}
              {pontVise(bridge, selectedElement) && (
                <circle cx={x} cy={y} r={11} className="th-metric-pont__halo" />
              )}
              <circle cx={x} cy={y} r={5} fill={orpheline ? "#9ca3af" : COULEURS_PONT[bridge.type] ?? COULEURS_PONT.about_refend} />
              {/* Pas de longueur ici : `longueur_m` est l'emprise relevée de l'angle sur le tronçon,
                  pas un linéaire de pont thermique. L'afficher induirait en erreur. */}
              {/* Le sigle dit de quel pont il s'agit : une pastille de couleur ne se lit pas en plan.
                  Il s'efface quand deux ponts sont trop proches pour que les deux sigles tiennent. */}
              {(sigleLisible || pontVise(bridge, selectedElement)) &&
                (() => {
                  const texte = `${SIGLES_PONT[bridge.type] ?? "?"}${nombre > 1 ? ` ×${nombre}` : ""}`;
                  // Le fond est dimensionné sur le texte : une police de 11 px fait ~6,6 px par
                  // caractère en gras, plus 3 px de marge de chaque côté.
                  const largeur = texte.length * 6.6 + 6;
                  return (
                    <>
                      <rect
                        className="th-metric-pont__etiquette"
                        x={x + 7}
                        y={y - 16}
                        width={largeur}
                        height={14}
                        rx={3}
                      />
                      <text className="th-metric-pont__sigle" x={x + 10} y={y - 9}>
                        {texte}
                      </text>
                    </>
                  );
                })()}
              <title>
                {`${libelle}${bridge.composant ? ` · ${bridge.composant}` : ""} · ${bridge.troncon}${
                  bridge.abscisse_m != null ? ` à ${bridge.abscisse_m.toLocaleString("fr-FR")} m` : ""
                }${orpheline ? " · rattachée à aucun local" : ""}${
                  nombre > 1 ? ` · ${nombre} ponts à cet endroit, cliquez pour les distinguer` : ""
                }`}
              </title>
            </g>
          );
        })}
    </g>
  );
}
