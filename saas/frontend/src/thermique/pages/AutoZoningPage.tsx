import { useEffect, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../../providers/AuthProvider";
import { thermiqueApi, type PdfPoint } from "../api";
import { calquesApi, type AutoDetection } from "../calques";
import { TileSheetViewer, type ToScreen } from "../components/TileSheetViewer";
import { nearestEdge, nearestVertex, pdfTolerance } from "../metre";
import { insideRoom, piecesApi, type Room, type SheetRooms } from "../pieces";
import { allSheets, projectQueryKey } from "../projectCache";
import { ZONE_STYLES, zoneKind, zoneSummary } from "../zoning";

const RASTER_STALE_MS = 6 * 3600 * 1000;
const POLL_MS = 1200;
const HIT_PX = 12;
const numberFormat = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });
const area = (value: number) => `${numberFormat.format(value)} m²`;

const STEP_LABELS: Record<NonNullable<AutoDetection["etape"]>, string> = {
  objets: "Lecture des murs, portes et menuiseries",
  pieces: "Construction de toutes les pièces",
  noms: "Lecture des noms sur le plan",
  enveloppe: "Vérification de l'enveloppe",
  menuiseries: "Classement final des ouvertures",
};

const roomPoints = (room: Room): PdfPoint[] => {
  const points: PdfPoint[] = [];
  for (let index = 0; index + 1 < room.contour.length; index += 2) points.push([room.contour[index], room.contour[index + 1]]);
  return points;
};

export function AutoZoningPage() {
  const { token } = useAuth();
  const projectId = Number(useParams().projectId);
  const queryClient = useQueryClient();
  const enabled = Boolean(token) && Number.isFinite(projectId);
  const [sheetId, setSheetId] = useState<number | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [draft, setDraft] = useState<PdfPoint[] | null>(null);
  const dragRef = useRef<number | null>(null);
  const pixelsPerPtRef = useRef(1);
  const wasRunningRef = useRef(false);

  const project = useQuery({
    queryKey: projectQueryKey(projectId),
    queryFn: () => thermiqueApi.getProject(token!, projectId),
    enabled,
  });
  const plans = project.data
    ? allSheets(project.data).filter((sheet) => sheet.nature === "plan" && sheet.scale_denominator !== null)
    : [];
  const currentSheetId = sheetId ?? plans[0]?.id ?? null;
  const sheet = plans.find((item) => item.id === currentSheetId);
  const roomsKey = ["thermique", "zonage-auto", currentSheetId ?? 0] as const;
  const autoKey = ["thermique", "detection-auto", currentSheetId ?? 0] as const;

  const raster = useQuery({
    queryKey: ["thermique", "raster", sheet?.id ?? 0, sheet?.rotation_deg ?? 0],
    queryFn: () => thermiqueApi.getRaster(token!, sheet!.id, sheet!.rotation_deg),
    enabled: Boolean(token && sheet),
    staleTime: RASTER_STALE_MS,
  });
  const rooms = useQuery({
    queryKey: roomsKey,
    queryFn: () => piecesApi.list(token!, currentSheetId!),
    enabled: Boolean(token && currentSheetId),
    refetchInterval: (query) => (query.state.data?.lecture_noms === "en_cours" ? 2500 : false),
  });
  const auto = useQuery({
    queryKey: autoKey,
    queryFn: () => calquesApi.autoState(token!, currentSheetId!),
    enabled: Boolean(token && currentSheetId),
    refetchInterval: (query) => (query.state.data?.en_cours ? POLL_MS : false),
  });

  useEffect(() => {
    if (auto.data?.en_cours) {
      wasRunningRef.current = true;
    } else if (wasRunningRef.current) {
      wasRunningRef.current = false;
      void queryClient.invalidateQueries({ queryKey: roomsKey });
    }
  }, [auto.data?.en_cours, queryClient, roomsKey]);

  const detect = useMutation({
    mutationFn: () => calquesApi.autoDetect(token!, currentSheetId!),
    onSuccess: (state) => queryClient.setQueryData(autoKey, state),
  });
  const update = useMutation({
    mutationFn: ({ roomId, contour }: { roomId: number; contour: PdfPoint[] }) =>
      piecesApi.update(token!, roomId, { contour: contour.flat() }),
    onSuccess: (next: SheetRooms) => {
      queryClient.setQueryData(roomsKey, next);
      setDraft(null);
    },
  });

  const roomList = rooms.data?.pieces ?? [];
  const selected = roomList.find((room) => room.id === selectedId) ?? null;
  const summary = zoneSummary(roomList);
  const running = Boolean(auto.data?.en_cours || detect.isPending);

  function resetSelection() {
    setSelectedId(null);
    setDraft(null);
    dragRef.current = null;
  }

  function renderOverlay(toScreen: ToScreen): ReactNode {
    const polygon = (coords: number[]) => {
      const points: string[] = [];
      for (let index = 0; index + 1 < coords.length; index += 2) {
        points.push(toScreen([coords[index], coords[index + 1]]).map((value) => value.toFixed(1)).join(","));
      }
      return points.join(" ");
    };
    return (
      <>
        {roomList.map((room, index) => {
          const style = ZONE_STYLES[zoneKind(room)];
          const [cx, cy] = toScreen(room.centre);
          return (
            <g
              key={room.id}
              className={`th-room th-auto-zone${room.id === selectedId ? " is-selected" : ""}`}
              style={{ "--room": style.color } as CSSProperties}
            >
              <polygon points={polygon(room.contour)} />
              <text x={cx} y={cy} textAnchor="middle">{room.repere || `Z-${String(index + 1).padStart(2, "0")}`}</text>
              <text x={cx} y={cy + 14} textAnchor="middle" className="th-room__area">{area(room.surface_m2)}</text>
            </g>
          );
        })}
        {draft && (
          <g className="th-room-draft">
            <polygon points={polygon(draft.flat())} />
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
          tool="zones"
          onHover={(_point, scale) => { pixelsPerPtRef.current = scale; }}
          onAddPoint={(point, event) => {
            if (draft) {
              const tolerance = pdfTolerance(HIT_PX, pixelsPerPtRef.current);
              const vertex = nearestVertex(draft, point, tolerance);
              if (vertex !== null) {
                if (event.altKey && draft.length > 3) setDraft(draft.filter((_, index) => index !== vertex));
                return;
              }
              const edge = nearestEdge(draft, point, tolerance);
              if (edge) setDraft([...draft.slice(0, edge.index + 1), edge.point, ...draft.slice(edge.index + 1)]);
              return;
            }
            const hit = [...roomList].reverse().find((room) => insideRoom(point, room.contour));
            setSelectedId(hit?.id ?? null);
          }}
          onGrab={(point, scale) => {
            if (!draft) return false;
            dragRef.current = nearestVertex(draft, point, pdfTolerance(HIT_PX, scale));
            return dragRef.current !== null;
          }}
          onGrabMove={(point) => {
            if (dragRef.current === null) return;
            setDraft((current) => current?.map((vertex, index) => (index === dragRef.current ? point : vertex)) ?? null);
          }}
          onGrabEnd={() => { dragRef.current = null; }}
          renderOverlay={renderOverlay}
        />
      ) : (
        <div className="th-viewer th-viewer--empty">
          <p className="th-viewer__status">
            {raster.error ? `Plan impossible à afficher : ${raster.error.message}` : "Préparation du plan…"}
          </p>
        </div>
      )}

      <aside className="th-panel th-auto-zoning__panel">
        <div>
          <p className="po2-eyebrow"><Link to={`/projets/${projectId}`}>← Retour au projet</Link></p>
          <h1 className="th-panel__title">Analyse automatique du plan</h1>
          <p className="th-muted">Toutes les pièces sont proposées en une passe. Vous corrigez uniquement le résultat.</p>
        </div>

        {plans.length > 0 ? (
          <label className="th-field">
            <span>Plan à analyser</span>
            <select value={currentSheetId ?? ""} onChange={(event) => { setSheetId(Number(event.target.value)); resetSelection(); }}>
              {plans.map((plan) => <option key={plan.id} value={plan.id}>{plan.label}</option>)}
            </select>
          </label>
        ) : (
          <p className="th-alert th-alert--warn">Aucun plan à l'échelle n'est prêt. Classez d'abord une planche comme plan et définissez son échelle.</p>
        )}

        {currentSheetId && (
          <button type="button" className="po2-button po2-button--primary th-auto-zoning__run" disabled={running} onClick={() => detect.mutate()}>
            {running ? "Analyse en cours…" : roomList.length ? "Relancer l'analyse du plan" : "Analyser le plan"}
          </button>
        )}
        {running && (
          <section className="th-auto-zoning__progress">
            <span className="th-auto-zoning__spinner" aria-hidden="true" />
            <strong>{auto.data?.etape ? STEP_LABELS[auto.data.etape] : "Démarrage de l'analyse"}</strong>
            <span className="th-muted">Le zonage complet apparaîtra automatiquement.</span>
          </section>
        )}
        {(detect.error || auto.data?.erreur || rooms.error) && (
          <p className="th-alert th-alert--error">{detect.error?.message || auto.data?.erreur || rooms.error?.message}</p>
        )}

        {roomList.length > 0 && (
          <>
            <section className="th-auto-zoning__summary">
              <strong>{roomList.length} zones proposées · {area(roomList.reduce((total, room) => total + room.surface_m2, 0))}</strong>
              <span className="th-muted">Cliquez une zone sur le plan ou dans la liste pour la contrôler.</span>
              <ul className="th-zone-legend">
                {summary.map(({ kind, count, area: total }) => (
                  <li key={kind}>
                    <span className="th-zone-legend__swatch" style={{ background: ZONE_STYLES[kind].color }} />
                    <span>{ZONE_STYLES[kind].label}</span>
                    <strong>{count} · {area(total)}</strong>
                  </li>
                ))}
              </ul>
            </section>

            <section className="th-auto-zoning__rooms">
              <strong>Zones détectées</strong>
              <div className="th-zone-list">
                {roomList.map((room, index) => (
                  <button key={room.id} type="button" className={room.id === selectedId ? "is-active" : ""} onClick={() => { setSelectedId(room.id); setDraft(null); }}>
                    <span className="th-zone-list__code" style={{ background: ZONE_STYLES[zoneKind(room)].color }}>
                      {room.repere || `Z-${String(index + 1).padStart(2, "0")}`}
                    </span>
                    <span><strong>{room.nom || "Nom à confirmer"}</strong><small>{area(room.surface_m2)} · {room.source === "auto" ? "proposition" : "corrigée"}</small></span>
                  </button>
                ))}
              </div>
            </section>
          </>
        )}

        {selected && (
          <section className="th-auto-zoning__selected">
            <strong>{selected.nom || "Zone sélectionnée"} · {area(selected.surface_m2)}</strong>
            {draft ? (
              <>
                <span className="th-muted">Glissez un sommet. Cliquez un côté pour en ajouter un ; Alt + clic sur un sommet pour le retirer.</span>
                <div className="th-inline">
                  <button type="button" className="po2-button po2-button--primary" disabled={update.isPending || draft.length < 3} onClick={() => update.mutate({ roomId: selected.id, contour: draft })}>Enregistrer</button>
                  <button type="button" className="po2-button po2-button--ghost" disabled={update.isPending} onClick={() => setDraft(null)}>Annuler</button>
                </div>
              </>
            ) : (
              <button type="button" className="po2-button po2-button--secondary" onClick={() => setDraft(roomPoints(selected))}>Ajuster le contour</button>
            )}
            {update.error && <span className="th-alert th-alert--error">{update.error.message}</span>}
          </section>
        )}
      </aside>
    </div>
  );
}
