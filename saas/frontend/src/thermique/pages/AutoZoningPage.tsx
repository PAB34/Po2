import { useEffect, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../../providers/AuthProvider";
import { thermiqueApi, type PdfPoint } from "../api";
import { TileSheetViewer, type ToScreen } from "../components/TileSheetViewer";
import { nearestVertex, pdfTolerance, projectOnSegment } from "../metre";
import { allSheets, projectQueryKey } from "../projectCache";
import { visionApi, VISION_STYLES, type VisionCategory, type VisionObject, type VisionResult } from "../vision";

const RASTER_STALE_MS = 6 * 3600 * 1000;
const POLL_MS = 1500;
const HIT_PX = 12;
const STAGE_LABELS = {
  raster: "Préparation de l'image haute définition",
  vision: "Lecture visuelle IA des composants",
  normalisation: "Assemblage et mise à l'échelle des objets",
} as const;

function shapePoints(item: VisionObject): PdfPoint[] {
  if (item.geometry_type !== "bbox" || item.points.length !== 2) return item.points;
  const [[x1, y1], [x2, y2]] = item.points;
  return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]];
}

function pointInPolygon(point: PdfPoint, polygon: PdfPoint[]): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i];
    const [xj, yj] = polygon[j];
    if ((yi > point[1]) !== (yj > point[1]) && point[0] < ((xj - xi) * (point[1] - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function hitObject(items: VisionObject[], point: PdfPoint, tolerance: number): VisionObject | null {
  return [...items].reverse().find((item) => {
    const points = shapePoints(item);
    if ((item.geometry_type === "polygon" || item.geometry_type === "bbox") && pointInPolygon(point, points)) return true;
    return nearestVertex(points, point, tolerance) !== null || nearestGeometryEdge(points, point, tolerance, item.geometry_type !== "polyline") !== null;
  }) ?? null;
}

function nearestGeometryEdge(points: PdfPoint[], point: PdfPoint, tolerance: number, closed: boolean): { index: number; point: PdfPoint } | null {
  let best: { index: number; point: PdfPoint } | null = null;
  let distance = tolerance;
  const last = closed ? points.length : points.length - 1;
  for (let index = 0; index < last; index += 1) {
    const projection = projectOnSegment(point, points[index], points[(index + 1) % points.length]);
    if (projection.distance <= distance) {
      best = { index, point: projection.point };
      distance = projection.distance;
    }
  }
  return best;
}

export function AutoZoningPage() {
  const { token } = useAuth();
  const projectId = Number(useParams().projectId);
  const queryClient = useQueryClient();
  const enabled = Boolean(token) && Number.isFinite(projectId);
  const [sheetId, setSheetId] = useState<number | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<PdfPoint[] | null>(null);
  const [importFileError, setImportFileError] = useState<string | null>(null);
  const [creating, setCreating] = useState<{ category: VisionCategory; geometry_type: "polyline" | "polygon" } | null>(null);
  const dragRef = useRef<number | null>(null);
  const pixelsPerPtRef = useRef(1);
  const wasRunningRef = useRef(false);

  const project = useQuery({ queryKey: projectQueryKey(projectId), queryFn: () => thermiqueApi.getProject(token!, projectId), enabled });
  const plans = project.data ? allSheets(project.data).filter((item) => item.nature === "plan") : [];
  const currentSheetId = sheetId ?? plans[0]?.id ?? null;
  const sheet = plans.find((item) => item.id === currentSheetId);
  const visionKey = ["thermique", "vision-analysis", currentSheetId ?? 0] as const;

  const raster = useQuery({
    queryKey: ["thermique", "raster", sheet?.id ?? 0, sheet?.rotation_deg ?? 0],
    queryFn: () => thermiqueApi.getRaster(token!, sheet!.id, sheet!.rotation_deg),
    enabled: Boolean(token && sheet),
    staleTime: RASTER_STALE_MS,
  });
  const vision = useQuery({
    queryKey: visionKey,
    queryFn: () => visionApi.state(token!, currentSheetId!),
    enabled: Boolean(token && currentSheetId),
    refetchInterval: (query) => (query.state.data?.running ? POLL_MS : false),
  });

  useEffect(() => {
    if (vision.data?.running) wasRunningRef.current = true;
    else if (wasRunningRef.current) {
      wasRunningRef.current = false;
      void queryClient.invalidateQueries({ queryKey: visionKey });
    }
  }, [queryClient, vision.data?.running, visionKey]);

  const analyze = useMutation({
    mutationFn: () => visionApi.start(token!, currentSheetId!),
    onSuccess: (state) => queryClient.setQueryData(visionKey, state),
  });
  const importAgent = useMutation({
    mutationFn: (payload: unknown) => visionApi.importAgent(token!, currentSheetId!, payload),
    onSuccess: (state) => {
      queryClient.setQueryData(visionKey, state);
      setImportFileError(null);
      resetSelection();
    },
  });
  const update = useMutation({
    mutationFn: ({ objectId, payload }: { objectId: string; payload: { points?: PdfPoint[]; category?: VisionCategory; confirmed?: boolean } }) =>
      visionApi.update(token!, currentSheetId!, objectId, payload),
    onSuccess: (result: VisionResult) => {
      queryClient.setQueryData(visionKey, { stage: null, running: false, error: null, result });
      setDraft(null);
    },
  });
  const create = useMutation({
    mutationFn: ({ points, category, geometry_type }: { points: PdfPoint[]; category: VisionCategory; geometry_type: "polyline" | "polygon" }) =>
      visionApi.create(token!, currentSheetId!, { points, category, geometry_type }),
    onSuccess: (next: VisionResult) => {
      queryClient.setQueryData(visionKey, { stage: null, running: false, error: null, result: next });
      setCreating(null);
      setDraft(null);
    },
  });
  const remove = useMutation({
    mutationFn: (objectId: string) => visionApi.remove(token!, currentSheetId!, objectId),
    onSuccess: (next: VisionResult) => {
      queryClient.setQueryData(visionKey, { stage: null, running: false, error: null, result: next });
      resetSelection();
    },
  });

  const result = vision.data?.result;
  const objects = result?.objects ?? [];
  const selected = objects.find((item) => item.id === selectedId) ?? null;
  const running = Boolean(vision.data?.running || analyze.isPending);
  const categories = Object.entries(VISION_STYLES) as [VisionCategory, (typeof VISION_STYLES)[VisionCategory]][];

  function resetSelection() {
    setSelectedId(null);
    setDraft(null);
    setCreating(null);
    dragRef.current = null;
  }

  function renderOverlay(toScreen: ToScreen): ReactNode {
    const points = (coords: PdfPoint[]) => coords.map((point) => toScreen(point).map((value) => value.toFixed(1)).join(",")).join(" ");
    return (
      <>
        {objects.map((item) => {
          const geometry = shapePoints(item);
          const style = { "--object-color": VISION_STYLES[item.category].color } as CSSProperties;
          const className = `th-vision-object th-vision-object--${item.geometry_type}${item.id === selectedId ? " is-selected" : ""}${item.review_required ? " needs-review" : ""}`;
          return (
            <g key={item.id} className={className} style={style}>
              {item.geometry_type === "polyline" ? <polyline points={points(geometry)} /> : <polygon points={points(geometry)} />}
            </g>
          );
        })}
        {draft && (
          <g className="th-vision-draft">
            {(selected?.geometry_type ?? creating?.geometry_type) === "polyline" ? <polyline points={points(draft)} /> : <polygon points={points(draft)} />}
            {draft.map((point, index) => {
              const [x, y] = toScreen(point);
              return <circle key={index} cx={x} cy={y} r={6} />;
            })}
          </g>
        )}
      </>
    );
  }

  return (
    <div className="th-viewer-layout th-auto-zoning">
      {sheet && raster.data ? (
        <TileSheetViewer
          manifest={raster.data}
          tileTemplate={thermiqueApi.apiUrl(raster.data.tile_url)}
          tool="vision"
          onHover={(_point, scale) => { pixelsPerPtRef.current = scale; }}
          onAddPoint={(point) => {
            if (creating) {
              setDraft((current) => [...(current ?? []), point]);
              return;
            }
            if (draft) {
              const edge = nearestGeometryEdge(draft, point, pdfTolerance(HIT_PX, pixelsPerPtRef.current), selected?.geometry_type !== "polyline");
              if (edge) setDraft([...draft.slice(0, edge.index + 1), edge.point, ...draft.slice(edge.index + 1)]);
              return;
            }
            setSelectedId(hitObject(objects, point, pdfTolerance(HIT_PX, pixelsPerPtRef.current))?.id ?? null);
          }}
          onGrab={(point, scale, event) => {
            if (!draft) return false;
            const index = nearestVertex(draft, point, pdfTolerance(HIT_PX, scale));
            const minimum = (selected?.geometry_type ?? creating?.geometry_type) === "polygon" ? 3 : 2;
            if (event.altKey && index !== null && draft.length > minimum) {
              setDraft(draft.filter((_, current) => current !== index));
              return false;
            }
            dragRef.current = index;
            return index !== null;
          }}
          onGrabMove={(point) => {
            if (dragRef.current === null) return;
            setDraft((current) => current?.map((vertex, index) => (index === dragRef.current ? point : vertex)) ?? null);
          }}
          onGrabEnd={() => { dragRef.current = null; }}
          renderOverlay={renderOverlay}
        />
      ) : (
        <div className="th-viewer th-viewer--empty"><p className="th-viewer__status">{raster.error ? `Plan impossible à afficher : ${raster.error.message}` : "Préparation du plan…"}</p></div>
      )}

      <aside className="th-panel th-auto-zoning__panel">
        <div>
          <p className="po2-eyebrow"><Link to={`/projets/${projectId}`}>← Retour au projet</Link></p>
          <h1 className="th-panel__title">Analyse IA du plan</h1>
          <p className="th-muted">Lecture de l'image uniquement. Aucun vecteur, calque ou tracé PDF n'entre dans la détection.</p>
        </div>

        {plans.length ? (
          <label className="th-field">
            <span>Plan à analyser</span>
            <select value={currentSheetId ?? ""} onChange={(event) => { setSheetId(Number(event.target.value)); resetSelection(); }}>
              {plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.label}</option>)}
            </select>
          </label>
        ) : <p className="th-alert th-alert--warn">Aucune planche n'est classée comme plan.</p>}

        {currentSheetId && (
          <section className="th-auto-zoning__agent-import">
            <strong>Agent Claude Code</strong>
            <span className="th-muted">Lancez l'agent sur le PDF, puis chargez ici son fichier JSON. Les composants deviennent immédiatement éditables.</span>
            <label className="po2-button po2-button--primary th-auto-zoning__run">
              {importAgent.isPending ? "Import en cours…" : result?.method === "claude_code_agent_raster" ? "Remplacer le résultat Claude" : "Importer le résultat Claude"}
              <input
                type="file"
                accept="application/json,.json"
                hidden
                disabled={importAgent.isPending}
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  event.currentTarget.value = "";
                  if (!file) return;
                  setImportFileError(null);
                  void file.text()
                    .then((content) => importAgent.mutate(JSON.parse(content)))
                    .catch(() => setImportFileError("Ce fichier n'est pas un JSON Claude Code valide."));
                }}
              />
            </label>
            <span className="th-muted">Orientation attendue dans la visionneuse : {sheet?.rotation_deg ?? 0}°.</span>
            <button type="button" className="po2-button po2-button--ghost" disabled={running} onClick={() => analyze.mutate()}>
              {running ? "Analyse serveur en cours…" : "Utiliser l'adaptateur serveur (repli)"}
            </button>
          </section>
        )}
        {running && (
          <section className="th-auto-zoning__progress">
            <span className="th-auto-zoning__spinner" aria-hidden="true" />
            <strong>{vision.data?.stage ? STAGE_LABELS[vision.data.stage] : "Démarrage de l'analyse"}</strong>
            <span className="th-muted">Le modèle confronte la vue globale aux six zones de détail.</span>
          </section>
        )}
        {(analyze.error || importAgent.error || importFileError || vision.data?.error || vision.error) && (
          <p className="th-alert th-alert--error">{analyze.error?.message || importAgent.error?.message || importFileError || vision.data?.error || vision.error?.message}</p>
        )}

        {result && (
          <>
            <section className="th-auto-zoning__summary">
              <strong>{objects.length} composants proposés</strong>
              <span className="th-muted">{result.review_count} à confirmer · moteur {result.model}</span>
              <ul className="th-zone-legend">
                {categories.filter(([category]) => result.counts[category]).map(([category, style]) => (
                  <li key={category}>
                    <span className="th-zone-legend__swatch" style={{ background: style.color }} />
                    <span>{style.label}</span>
                    <strong>{result.counts[category]}</strong>
                  </li>
                ))}
              </ul>
            </section>

            <section className="th-auto-zoning__rooms">
              <strong>Objets détectés</strong>
              <div className="th-zone-list">
                {objects.map((item) => (
                  <button key={item.id} type="button" className={item.id === selectedId ? "is-active" : ""} onClick={() => { setSelectedId(item.id); setDraft(null); }}>
                    <span className="th-zone-list__code" style={{ background: VISION_STYLES[item.category].color }}>{item.id.split("-").at(-1)}</span>
                    <span>
                      <strong>{VISION_STYLES[item.category].label}{item.review_required ? " · à confirmer" : ""}</strong>
                      <small>{Math.round(item.confidence * 100)} % · {item.source === "corrige" ? "corrigé" : item.source === "manuel" ? "ajout manuel" : "proposition IA"}</small>
                    </span>
                  </button>
                ))}
              </div>
              {!creating && (
                <button
                  type="button"
                  className="po2-button po2-button--secondary"
                  onClick={() => { setSelectedId(null); setCreating({ category: "cloison", geometry_type: "polyline" }); setDraft([]); }}
                >
                  Ajouter un objet manuellement
                </button>
              )}
            </section>
          </>
        )}

        {selected && (
          <section className="th-auto-zoning__selected">
            <strong>{selected.id} · {VISION_STYLES[selected.category].label}</strong>
            <span className="th-muted">{selected.evidence || "Justification visuelle non renseignée."}</span>
            <label className="th-field">
              <span>Nature</span>
              <select value={selected.category} disabled={update.isPending} onChange={(event) => update.mutate({ objectId: selected.id, payload: { category: event.target.value as VisionCategory } })}>
                {categories.map(([category, style]) => <option key={category} value={category}>{style.label}</option>)}
              </select>
            </label>
            {draft ? (
              <>
                <span className="th-muted">Glissez un point. Cliquez un segment pour ajouter un point ; Alt + clic retire un point.</span>
                <div className="th-inline">
                  <button type="button" className="po2-button po2-button--primary" disabled={update.isPending || draft.length < 2} onClick={() => update.mutate({ objectId: selected.id, payload: { points: draft, confirmed: true } })}>Enregistrer et valider</button>
                  <button type="button" className="po2-button po2-button--ghost" disabled={update.isPending} onClick={() => setDraft(null)}>Annuler</button>
                </div>
              </>
            ) : (
              <div className="th-inline">
                <button type="button" className="po2-button po2-button--secondary" onClick={() => setDraft(shapePoints(selected))}>Ajuster les points</button>
                {!selected.confirmed && <button type="button" className="po2-button po2-button--ghost" disabled={update.isPending} onClick={() => update.mutate({ objectId: selected.id, payload: { confirmed: true } })}>Valider tel quel</button>}
                <button
                  type="button"
                  className="po2-button po2-button--ghost"
                  disabled={remove.isPending}
                  onClick={() => { if (window.confirm(`Supprimer l'objet ${selected.id} ?`)) remove.mutate(selected.id); }}
                >
                  Supprimer
                </button>
              </div>
            )}
            {(update.error || remove.error) && <span className="th-alert th-alert--error">{update.error?.message || remove.error?.message}</span>}
          </section>
        )}

        {creating && draft && (
          <section className="th-auto-zoning__selected">
            <strong>Ajout manuel — dernier recours</strong>
            <span className="th-muted">Cliquez les points sur le plan dans l'ordre, puis enregistrez.</span>
            <label className="th-field">
              <span>Nature</span>
              <select value={creating.category} onChange={(event) => setCreating({ ...creating, category: event.target.value as VisionCategory })}>
                {categories.map(([category, style]) => <option key={category} value={category}>{style.label}</option>)}
              </select>
            </label>
            <label className="th-field">
              <span>Géométrie</span>
              <select value={creating.geometry_type} onChange={(event) => setCreating({ ...creating, geometry_type: event.target.value as "polyline" | "polygon" })}>
                <option value="polyline">Ligne</option>
                <option value="polygon">Surface</option>
              </select>
            </label>
            <div className="th-inline">
              <button
                type="button"
                className="po2-button po2-button--primary"
                disabled={create.isPending || draft.length < (creating.geometry_type === "polygon" ? 3 : 2)}
                onClick={() => create.mutate({ points: draft, ...creating })}
              >
                Enregistrer l'objet
              </button>
              <button type="button" className="po2-button po2-button--ghost" onClick={() => { setCreating(null); setDraft(null); }}>Annuler</button>
            </div>
            {create.error && <span className="th-alert th-alert--error">{create.error.message}</span>}
          </section>
        )}
      </aside>
    </div>
  );
}
