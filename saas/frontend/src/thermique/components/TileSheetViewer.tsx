import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";

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

export type ViewerTool = "pan" | "measure" | "calibrate";
export type ViewerSegment = { p1: PdfPoint; p2: PdfPoint; label?: string; tone: "measure" | "reference" };

type View = { zoom: number; panX: number; panY: number };
type Drag = { pointerId: number; x: number; y: number; panX: number; panY: number; moved: boolean };

type Props = {
  manifest: RasterManifest;
  tileTemplate: string;
  tool: ViewerTool;
  points: PdfPoint[];
  segments: ViewerSegment[];
  onAddPoint: (point: PdfPoint) => void;
};

const MAX_ZOOM = 8; // pixels écran par pixel du niveau le plus fin
const DRAG_THRESHOLD_PX = 4;

function zoomAround(view: View, cx: number, cy: number, factor: number, minZoom: number): View {
  const zoom = Math.min(MAX_ZOOM, Math.max(minZoom, view.zoom * factor));
  const ratio = zoom / view.zoom;
  return { zoom, panX: cx - (cx - view.panX) * ratio, panY: cy - (cy - view.panY) * ratio };
}

// Visionneuse de planche en tuiles d'images rendues par le serveur (pdfium).
// Le zoom et le déplacement ne redessinent rien : on ne change que les images affichées.
export function TileSheetViewer({ manifest, tileTemplate, tool, points, segments, onAddPoint }: Props) {
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
    if (fittedKeyRef.current !== key && fit()) {
      fittedKeyRef.current = key;
    }
  }, [manifest.sheet_id, manifest.rotation, fit]);

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

  const toScreen = (point: PdfPoint): [number, number] => {
    const [px, py] = pdfToRaster(manifest.transform, point);
    return [px * view.zoom + view.panX, py * view.zoom + view.panY];
  };

  const handlePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0 && event.button !== 1) {
      return;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      pointerId: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      panX: view.panX,
      panY: view.panY,
      moved: event.button === 1,
    };
  };

  const handlePointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) {
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
    if (!drag || drag.moved || tool === "pan" || event.button !== 0) {
      return;
    }
    const point = toPdf(event.clientX, event.clientY);
    if (point) {
      onAddPoint(point);
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
      onPointerCancel={() => {
        dragRef.current = null;
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
      </div>
    </div>
  );
}
