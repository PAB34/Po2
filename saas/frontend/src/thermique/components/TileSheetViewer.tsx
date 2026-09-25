import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent, ReactNode } from "react";

import type { PdfPoint } from "../api";
import {
  levelFactor,
  pdfToRaster,
  pickBackdrop,
  pickLevel,
  rasterToPdf,
  tileSrc,
  visibleTiles,
  type RasterManifest,
  type TileRef,
} from "../raster";

export type ViewerTool = "pan" | "measure" | "calibrate" | "edition" | "nord";
export type ViewerSegment = { p1: PdfPoint; p2: PdfPoint; label?: string; tone: "measure" | "reference" };
// Touches enfoncées au clic ou au survol : Maj et Alt modifient l'aimantation du métré.
export type PickEvent = { shiftKey: boolean; altKey: boolean };
export type ToScreen = (point: PdfPoint) => [number, number];

type View = { zoom: number; panX: number; panY: number };
export type ViewerView = View;
type Drag = { pointerId: number; x: number; y: number; panX: number; panY: number; moved: boolean; grab: boolean };

type Props = {
  manifest: RasterManifest;
  tileTemplate: string;
  // « pan » : glisser déplace le plan ; tout autre outil : un clic pose un point.
  tool: string;
  points?: PdfPoint[];
  segments?: ViewerSegment[];
  onAddPoint: (point: PdfPoint, event: PickEvent) => void;
  // Clic simple en mode « pan » : le plan n'a pas bougé, le geste désigne donc ce point. Sert à choisir
  // un local ou un élément d'enveloppe sans empêcher le glisser de déplacer le plan. `pixelsPerPt` donne
  // la tolérance à l'écran, pour viser un trait fin au même confort quel que soit le zoom.
  onPick?: (point: PdfPoint, pixelsPerPt: number, event: PickEvent) => void;
  // Survol : point sous le curseur et pixels écran par point PDF (tolérance d'aimantation).
  onHover?: (point: PdfPoint | null, pixelsPerPt: number, event: PickEvent) => void;
  // Clic enfoncé sur un objet : si la fonction renvoie true, le glisser déplace l'objet et non le plan.
  onGrab?: (point: PdfPoint, pixelsPerPt: number, event: PickEvent) => boolean;
  onGrabMove?: (point: PdfPoint, event: PickEvent) => void;
  onGrabEnd?: () => void;
  // Clic droit : point sous le curseur (le menu du navigateur est alors supprimé).
  onContextPick?: (point: PdfPoint, pixelsPerPt: number, ecran: { x: number; y: number }) => void;
  renderOverlay?: (toScreen: ToScreen) => ReactNode;
  // Réglages propres à la planche, rendus dans la barre d'outils (cases d'affichage des métrés…).
  renderTools?: ReactNode;
  // Cadrage à reprendre à l'ouverture de la planche (au lieu de l'ajuster), et suivi du cadrage courant.
  initialView?: ViewerView | null;
  onViewChange?: (view: ViewerView) => void;
  // Point à amener au centre, demandé de l'extérieur : l'étape « ponts thermiques » y amène le pont en
  // cours (F2, Q4). Le recentrage n'a lieu qu'au changement de `cle`, sinon le plan se rappellerait à
  // l'ordre à chaque dessin et deviendrait impossible à déplacer à la main. `zoom` est un multiple du
  // cadrage ajusté, et ne fait jamais reculer un zoom déjà plus serré.
  focus?: { point: PdfPoint; cle: string; zoom?: number } | null;
};

const MAX_ZOOM = 8; // pixels écran par pixel du niveau le plus fin
const DRAG_THRESHOLD_PX = 4;
const NO_POINTS: PdfPoint[] = [];
const NO_SEGMENTS: ViewerSegment[] = [];

function zoomAround(view: View, cx: number, cy: number, factor: number, minZoom: number): View {
  const zoom = Math.min(MAX_ZOOM, Math.max(minZoom, view.zoom * factor));
  const ratio = zoom / view.zoom;
  return { zoom, panX: cx - (cx - view.panX) * ratio, panY: cy - (cy - view.panY) * ratio };
}

const modifiers = (event: { shiftKey: boolean; altKey: boolean }): PickEvent => ({ shiftKey: event.shiftKey, altKey: event.altKey });

// Visionneuse de planche en tuiles d'images rendues par le serveur (pdfium).
// Le zoom et le déplacement ne redessinent rien : on ne change que les images affichées.
export function TileSheetViewer({
  manifest,
  tileTemplate,
  tool,
  points = NO_POINTS,
  segments = NO_SEGMENTS,
  onAddPoint,
  onPick,
  onHover,
  onGrab,
  onGrabMove,
  onGrabEnd,
  onContextPick,
  renderTools,
  renderOverlay,
  initialView = null,
  onViewChange,
  focus = null,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<Drag | null>(null);
  const fitZoomRef = useRef(1);
  const fittedKeyRef = useRef("");
  const [size, setSize] = useState({ width: 0, height: 0 });
  const [view, setView] = useState<View>({ zoom: 1, panX: 0, panY: 0 });

  useLayoutEffect(() => {
    const element = containerRef.current;
    if (!element) {
      return;
    }
    // mesure immédiate : l'observateur ne se déclenche qu'au prochain dessin de la page
    setSize({ width: element.clientWidth, height: element.clientHeight });
    const observer = new ResizeObserver(([entry]) => {
      setSize({ width: entry.contentRect.width, height: entry.contentRect.height });
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const fit = useCallback((): boolean => {
    if (size.width === 0 || size.height === 0) {
      return false;
    }
    const zoom = Math.min(size.width / manifest.width_px, size.height / manifest.height_px) * 0.96;
    fitZoomRef.current = zoom;
    setView({
      zoom,
      panX: (size.width - manifest.width_px * zoom) / 2,
      panY: (size.height - manifest.height_px * zoom) / 2,
    });
    return true;
  }, [manifest.width_px, manifest.height_px, size.width, size.height]);

  // Ajuste à l'ouverture d'une planche et à chaque rotation. La zone peut mesurer 0 px au
  // premier affichage : on ne marque la planche ajustée qu'une fois l'ajustement fait.
  useEffect(() => {
    const key = `${manifest.sheet_id}|${manifest.rotation}`;
    if (fittedKeyRef.current === key) {
      return;
    }
    if (initialView && fit()) {
      // l'ajustement fixe le zoom minimal ; le cadrage mémorisé est ensuite repris
      setView(initialView);
      fittedKeyRef.current = key;
    } else if (fit()) {
      fittedKeyRef.current = key;
    }
  }, [manifest.sheet_id, manifest.rotation, fit, initialView]);

  // Recentrage demandé de l'extérieur, une fois par `cle`. La planche doit d'abord avoir été ajustée :
  // sans cela, `fitZoomRef` vaut encore 1 et le cadrage calculé serait faux.
  const focusRef = useRef("");
  useEffect(() => {
    if (!focus || focus.cle === focusRef.current || size.width === 0) {
      return;
    }
    if (fittedKeyRef.current !== `${manifest.sheet_id}|${manifest.rotation}`) {
      return;
    }
    focusRef.current = focus.cle;
    const [px, py] = pdfToRaster(manifest.transform, focus.point);
    setView((current) => {
      const zoom = focus.zoom
        ? Math.min(MAX_ZOOM, Math.max(current.zoom, fitZoomRef.current * focus.zoom))
        : current.zoom;
      return { zoom, panX: size.width / 2 - px * zoom, panY: size.height / 2 - py * zoom };
    });
  }, [focus, manifest.sheet_id, manifest.rotation, manifest.transform, size.width, size.height]);

  const onViewChangeRef = useRef(onViewChange);
  onViewChangeRef.current = onViewChange;
  useEffect(() => {
    // rien n'est signalé avant l'ajustement : le cadrage provisoire écraserait celui mémorisé
    if (fittedKeyRef.current === `${manifest.sheet_id}|${manifest.rotation}`) {
      onViewChangeRef.current?.(view);
    }
  }, [view, manifest.sheet_id, manifest.rotation]);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) {
      return;
    }
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      const rect = element.getBoundingClientRect();
      const delta = event.deltaMode === 1 ? event.deltaY * 16 : event.deltaY;
      setView((current) =>
        zoomAround(current, event.clientX - rect.left, event.clientY - rect.top, Math.exp(-delta * 0.0015), fitZoomRef.current * 0.25),
      );
    };
    element.addEventListener("wheel", onWheel, { passive: false });
    return () => element.removeEventListener("wheel", onWheel);
  }, []);

  const [ta, tb, tc, td] = manifest.transform;
  const pixelsPerPt = view.zoom * Math.sqrt(Math.abs(ta * td - tb * tc));

  const toPdf = (clientX: number, clientY: number): PdfPoint | null => {
    const element = containerRef.current;
    if (!element) {
      return null;
    }
    const rect = element.getBoundingClientRect();
    return rasterToPdf(
      manifest.transform,
      (clientX - rect.left - view.panX) / view.zoom,
      (clientY - rect.top - view.panY) / view.zoom,
    );
  };

  const toScreen: ToScreen = (point) => {
    const [px, py] = pdfToRaster(manifest.transform, point);
    return [px * view.zoom + view.panX, py * view.zoom + view.panY];
  };

  const handlePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0 && event.button !== 1) {
      return;
    }
    let grab = false;
    if (event.button === 0 && tool !== "pan" && onGrab) {
      const point = toPdf(event.clientX, event.clientY);
      grab = point !== null && onGrab(point, pixelsPerPt, modifiers(event));
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      pointerId: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      panX: view.panX,
      panY: view.panY,
      moved: event.button === 1,
      grab,
    };
  };

  const handlePointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) {
      onHover?.(toPdf(event.clientX, event.clientY), pixelsPerPt, modifiers(event));
      return;
    }
    if (drag.grab) {
      const point = toPdf(event.clientX, event.clientY);
      if (point) {
        onGrabMove?.(point, modifiers(event));
      }
      return;
    }
    const dx = event.clientX - drag.x;
    const dy = event.clientY - drag.y;
    if (!drag.moved && Math.hypot(dx, dy) > DRAG_THRESHOLD_PX) {
      drag.moved = true;
    }
    if (drag.moved) {
      setView((current) => ({ ...current, panX: drag.panX + dx, panY: drag.panY + dy }));
    }
  };

  const handlePointerUp = (event: ReactPointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    dragRef.current = null;
    if (drag?.grab) {
      onGrabEnd?.();
      return;
    }
    if (!drag || drag.moved || event.button !== 0) {
      return;
    }
    const point = toPdf(event.clientX, event.clientY);
    if (!point) {
      return;
    }
    // Le plan n'a pas bougé : c'est un clic. En mode « pan » il désigne, ailleurs il pose un point.
    if (tool === "pan") {
      onPick?.(point, pixelsPerPt, modifiers(event));
    } else {
      onAddPoint(point, modifiers(event));
    }
  };

  const zoomBy = (factor: number) =>
    setView((current) => zoomAround(current, size.width / 2, size.height / 2, factor, fitZoomRef.current * 0.25));

  // Tuiles à afficher : un fond basse définition complet + le niveau adapté au zoom, zone visible seulement.
  const dpr = window.devicePixelRatio || 1;
  const backdrop = pickBackdrop(manifest);
  const detail = pickLevel(manifest, view.zoom * dpr);
  const visibleRect = {
    x0: -view.panX / view.zoom,
    y0: -view.panY / view.zoom,
    x1: (size.width - view.panX) / view.zoom,
    y1: (size.height - view.panY) / view.zoom,
  };
  const tiles: TileRef[] = [
    ...visibleTiles(manifest, backdrop, null),
    ...(detail.z > backdrop.z ? visibleTiles(manifest, detail, visibleRect) : []),
  ];

  const tileStyle = (tile: TileRef) => {
    const span = manifest.tile_size / levelFactor(manifest, manifest.levels[tile.z]);
    return { left: `${tile.x * span}px`, top: `${tile.y * span}px`, width: `${span}px`, height: `${span}px` };
  };

  return (
    <div
      ref={containerRef}
      className={tool === "pan" ? "th-viewer" : "th-viewer th-viewer--pick"}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerLeave={() => {
        if (!dragRef.current) {
          onHover?.(null, pixelsPerPt, { shiftKey: false, altKey: false });
        }
      }}
      onPointerCancel={() => {
        const drag = dragRef.current;
        dragRef.current = null;
        if (drag?.grab) {
          // Ne jamais laisser une poignée ou un lasso dans un état « en cours » après une interruption
          // du navigateur (perte de capture, changement de fenêtre, geste tactile annulé).
          onGrabEnd?.();
        }
      }}
      onContextMenu={(event) => {
        if (!onContextPick) {
          return;
        }
        event.preventDefault();
        const point = toPdf(event.clientX, event.clientY);
        if (point) {
          onContextPick(point, pixelsPerPt, { x: event.clientX, y: event.clientY });
        }
      }}
    >
      <div
        className="th-viewer__page"
        style={{
          width: `${manifest.width_px}px`,
          height: `${manifest.height_px}px`,
          transform: `translate(${view.panX}px, ${view.panY}px) scale(${view.zoom})`,
        }}
      >
        {tiles.map((tile) => (
          <img
            key={`${tile.z}/${tile.x}/${tile.y}`}
            className="th-viewer__tile"
            src={tileSrc(tileTemplate, tile)}
            style={tileStyle(tile)}
            alt=""
            draggable={false}
          />
        ))}
      </div>

      <svg className="th-viewer__overlay" width={size.width} height={size.height}>
        {renderOverlay?.(toScreen)}
        {segments.map((segment, index) => {
          const [x1, y1] = toScreen(segment.p1);
          const [x2, y2] = toScreen(segment.p2);
          return (
            <g key={index} className={`th-seg th-seg--${segment.tone}`}>
              <line x1={x1} y1={y1} x2={x2} y2={y2} />
              <circle cx={x1} cy={y1} r={4} />
              <circle cx={x2} cy={y2} r={4} />
              {segment.label && (
                <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 10} textAnchor="middle">
                  {segment.label}
                </text>
              )}
            </g>
          );
        })}
        {points.length === 1 &&
          (() => {
            const [x, y] = toScreen(points[0]);
            return <circle className="th-seg th-seg--measure" cx={x} cy={y} r={5} />;
          })()}
      </svg>

      <div className="th-viewer__toolbar" onPointerDown={(event) => event.stopPropagation()}>
        <button type="button" onClick={() => zoomBy(1 / 1.4)} aria-label="Dézoomer">
          −
        </button>
        <span>{Math.round((view.zoom / fitZoomRef.current) * 100)} %</span>
        <button type="button" onClick={() => zoomBy(1.4)} aria-label="Zoomer">
          +
        </button>
        <button type="button" onClick={() => fit()}>
          Ajuster
        </button>
        {renderTools}
      </div>
    </div>
  );
}
