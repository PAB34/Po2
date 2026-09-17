import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../../providers/AuthProvider";
import { request, thermiqueApi, type PdfPoint } from "../api";
import { calquesApi } from "../calques";
import { TileSheetViewer, type ToScreen } from "../components/TileSheetViewer";
import {
  PT_TO_M,
  insertVertex,
  metreApi,
  nearestEdge,
  nearestVertex,
  pointInPolygon,
  polygonArea,
  removeVertex,
  type Metre,
  type MetreZone,
} from "../metre";
import { allSheets, projectQueryKey } from "../projectCache";
import { ProjectTabs } from "./ProjectLibraryPage";

const RASTER_STALE_MS = 6 * 3600 * 1000;
const HANDLE_PX = 8;
const LINES = { nu_exterieur: "Nu extérieur", contour: "Nu intérieur" } as const;
const m2 = (value: number) => `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 }).format(value)} m²`;

type EnvelopeResult = Metre & { proposition_enveloppe?: { batiments: number; nu_exterieur_m2: number; nu_interieur_m2: number } };

const proposeEnvelope = (token: string, levelId: number, fermetureCm: number, remplacer: boolean) =>
  request<EnvelopeResult>(token, `/thermique/niveaux/${levelId}/proposer-enveloppe`, {
    method: "POST",
    body: JSON.stringify({ fermeture_cm: fermetureCm, remplacer }),
  });

// Étape « Enveloppe » (docs/thermique/refondation-parcours-decisions.md §15) : par niveau, le nu extérieur et le
// nu intérieur, proposés depuis les calques puis corrigés ; la bande entre les deux sert de portée aux calques.
export function EnveloppePage() {
  const { token } = useAuth();
  const projectId = Number(useParams().projectId);
  const queryClient = useQueryClient();
  const enabled = Boolean(token) && Number.isFinite(projectId);
  const metreKey = ["thermique", "metre", projectId] as const;

  const [levelId, setLevelId] = useState<number | null>(null);
  const [zoneId, setZoneId] = useState<number | null>(null);
  const [fermetureCm, setFermetureCm] = useState(100);
  const [needsConfirm, setNeedsConfirm] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  // sommet en cours de déplacement : points modifiés localement jusqu'au relâchement
  const [dragPoints, setDragPoints] = useState<PdfPoint[] | null>(null);
  const dragRef = useRef<{ index: number; points: PdfPoint[] } | null>(null);
  const pixelsPerPt = useRef(1);

  const projectQuery = useQuery({
    queryKey: projectQueryKey(projectId),
    queryFn: () => thermiqueApi.getProject(token!, projectId),
    enabled,
  });
  const metre = useQuery({ queryKey: metreKey, queryFn: () => metreApi.get(token!, projectId), enabled });
  const levels = useMemo(() => (metre.data?.niveaux ?? []).filter((item) => item.planche_id !== null), [metre.data]);
  const level = levels.find((item) => item.id === levelId) ?? levels[0] ?? null;
  const sheets = projectQuery.data ? allSheets(projectQuery.data) : [];
  const sheet = sheets.find((item) => item.id === level?.planche_id);
  const rotation = sheet?.rotation_deg ?? 0;
  const lines = (level?.zones ?? []).filter((zone) => zone.type === "contour" || zone.type === "nu_exterieur");
  const selected = lines.find((zone) => zone.id === zoneId) ?? null;
  const metresPerPt = PT_TO_M * (level?.echelle ?? 0);

  useEffect(() => {
    setZoneId(null);
    setNeedsConfirm(false);
  }, [level?.id]);

  const raster = useQuery({
    queryKey: ["thermique", "raster", sheet?.id ?? 0, rotation],
    queryFn: () => thermiqueApi.getRaster(token!, sheet!.id, rotation),
    enabled: Boolean(token && sheet),
    staleTime: RASTER_STALE_MS,
  });
  const designated = useQuery({
    queryKey: ["thermique", "calques-designes", projectId, sheet?.id ?? 0],
    queryFn: () => calquesApi.designated(token!, sheet!.id),
    enabled: Boolean(token && sheet),
    staleTime: Infinity,
  });

  function done(next: Metre) {
    queryClient.setQueryData(metreKey, next);
    // la bande a changé : les calques restreints à l'enveloppe sont à recompter
    void queryClient.invalidateQueries({ queryKey: ["thermique", "calques", projectId] });
    void queryClient.invalidateQueries({ queryKey: ["thermique", "calques-designes", projectId] });
  }

  const proposeMutation = useMutation({
    mutationFn: (remplacer: boolean) => proposeEnvelope(token!, level!.id, fermetureCm, remplacer),
    onSuccess: (next) => {
      done(next);
      setNeedsConfirm(false);
      setZoneId(null);
      const found = next.proposition_enveloppe;
      setNotice(
        found
          ? `${found.batiments > 1 ? `${found.batiments} bâtiments : ` : ""}nu extérieur ${m2(found.nu_exterieur_m2)}, nu intérieur ${m2(found.nu_interieur_m2)}. Vérifiez et corrigez les lignes.`
          : null,
      );
    },
    onError: (error) => setNeedsConfirm(error.message.includes("confirmez")),
  });
  const updateMutation = useMutation({
    mutationFn: ({ zone, points, cotes }: { zone: MetreZone; points: PdfPoint[]; cotes: MetreZone["cotes"] }) =>
      metreApi.updateZone(token!, zone.id, zone.type === "contour" ? { points, cotes } : { points }),
    onSuccess: done,
    onSettled: () => setDragPoints(null),
  });
  const deleteMutation = useMutation({
    mutationFn: (zone: MetreZone) => metreApi.deleteZone(token!, zone.id),
    onSuccess: (next) => {
      done(next);
      setZoneId(null);
    },
  });
  const busy = proposeMutation.isPending || updateMutation.isPending || deleteMutation.isPending;
  const actionError = [proposeMutation, updateMutation, deleteMutation].find((mutation) => mutation.error)?.error ?? null;
  const tolerance = () => HANDLE_PX / pixelsPerPt.current;

  function save(zone: MetreZone, points: PdfPoint[], cotes: MetreZone["cotes"]) {
    updateMutation.mutate({ zone, points, cotes });
  }

  function zoneAt(point: PdfPoint): MetreZone | null {
    // un clic près d'une ligne la choisit ; sinon la plus petite ligne qui contient le point
    const near = lines.find((zone) => nearestEdge(zone.points, point, tolerance()) !== null);
    if (near) {
      return near;
    }
    const around = lines.filter((zone) => pointInPolygon(point, zone.points));
    return around.sort((a, b) => polygonArea(a.points) - polygonArea(b.points))[0] ?? null;
  }

  function renderOverlay(toScreen: ToScreen): ReactNode {
    const path = (points: PdfPoint[]) => points.map((point) => toScreen(point).map((v) => v.toFixed(1)).join(",")).join(" ");
    const flat = (coords: number[]) => {
      const out: PdfPoint[] = [];
      for (let k = 0; k + 1 < coords.length; k += 2) {
        out.push([coords[k], coords[k + 1]]);
      }
      return path(out);
    };
    return (
      <>
        {designated.data && (
          <g className="th-sup-reference">
            {Object.values(designated.data.natures).map((group, index) => (
              <g key={index}>
                {group.traits.map((coords, k) => (
                  <polyline key={k} points={flat(coords)} />
                ))}
              </g>
            ))}
          </g>
        )}
        {lines.map((zone) => {
          const points = zone.id === selected?.id && dragPoints ? dragPoints : zone.points;
          return (
            <g key={zone.id} className={`th-env th-env--${zone.type}${zone.id === selected?.id ? " is-selected" : ""}`}>
              <polygon points={path(points)} />
              {zone.id === selected?.id &&
                points.map((point, index) => {
                  const [x, y] = toScreen(point);
                  return <circle key={index} cx={x} cy={y} r={4} />;
                })}
            </g>
          );
        })}
      </>
    );
  }

  const surfaces = (type: MetreZone["type"]) =>
    lines.filter((zone) => zone.type === type).reduce((sum, zone) => sum + polygonArea(zone.points) * metresPerPt * metresPerPt, 0);

  return (
    <div className="th-viewer-layout">
      {sheet && raster.data ? (
        <TileSheetViewer
          manifest={raster.data}
          tileTemplate={thermiqueApi.apiUrl(raster.data.tile_url)}
          tool="enveloppe"
          onHover={(_, scale) => {
            pixelsPerPt.current = scale;
          }}
          onAddPoint={(point, event) => {
            if (event.altKey && selected) {
              const index = nearestVertex(selected.points, point, tolerance());
              if (index !== null && selected.points.length > 3) {
                const next = removeVertex(selected.points, selected.cotes, index);
                save(selected, next.points, next.cotes);
              }
              return;
            }
            setZoneId(zoneAt(point)?.id ?? null);
          }}
          onGrab={(point, scale) => {
            pixelsPerPt.current = scale;
            if (!selected || busy) {
              return false;
            }
            const index = nearestVertex(selected.points, point, HANDLE_PX / scale);
            if (index === null) {
              return false;
            }
            dragRef.current = { index, points: selected.points };
            return true;
          }}
          onGrabMove={(point) => {
            const drag = dragRef.current;
            if (drag) {
              const next = drag.points.map((vertex, i) => (i === drag.index ? point : vertex));
              dragRef.current = { ...drag, points: next };
              setDragPoints(next);
            }
          }}
          onGrabEnd={() => {
            const drag = dragRef.current;
            dragRef.current = null;
            if (drag && selected) {
              save(selected, drag.points, selected.cotes);
            }
          }}
          onContextPick={(point, scale) => {
            if (!selected) {
              return;
            }
            const edge = nearestEdge(selected.points, point, HANDLE_PX / scale);
            if (edge) {
              const next = insertVertex(selected.points, selected.cotes, edge.index, edge.point);
              save(selected, next.points, next.cotes);
            }
          }}
          renderOverlay={renderOverlay}
        />
      ) : (
        <div className="th-viewer th-viewer--empty">
          <p className="th-viewer__status">
            {raster.error
              ? `Affichage impossible : ${raster.error.message}`
              : metre.isLoading
                ? "Lecture des niveaux…"
                : sheet
                  ? "Préparation de la planche…"
                  : "Aucun niveau associé à un plan : validez d'abord la superposition."}
          </p>
        </div>
      )}

      <aside className="th-panel">
        <div>
          <p className="po2-eyebrow">
            <Link to="/">Projets</Link> · <Link to={`/projets/${projectId}`}>{projectQuery.data?.name ?? "Projet"}</Link>
          </p>
          <h1 className="th-panel__title">Enveloppe</h1>
        </div>
        <ProjectTabs projectId={projectId} />
        <p className="th-muted">
          Pour chaque niveau, le <strong>nu extérieur</strong> (bleu) et le <strong>nu intérieur</strong> (orange). La bande entre les deux
          est l'enveloppe : dans l'onglet Calques, une désignation peut s'y limiter. Cliquez une ligne pour la corriger : glisser un
          sommet, <strong>clic droit</strong> sur un côté pour en ajouter un, <strong>Alt + clic</strong> sur un sommet pour le retirer.
        </p>

        {metre.error && <p className="th-alert th-alert--error">{metre.error.message}</p>}
        {actionError && !needsConfirm && <p className="th-alert th-alert--error">{actionError.message}</p>}
        {notice && <p className="th-alert th-alert--ok">{notice}</p>}

        {levels.length > 0 && (
          <label className="th-field">
            <span>Niveau</span>
            <select
              value={level?.id ?? ""}
              onChange={(event) => {
                setLevelId(Number(event.target.value));
                setNotice(null);
                proposeMutation.reset();
              }}
            >
              {levels.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.nom}
                  {item.planche_libelle && item.planche_libelle !== item.nom ? ` (${item.planche_libelle})` : ""}
                </option>
              ))}
            </select>
          </label>
        )}

        {level && (
          <section className="th-edgebox th-calque-panel">
            <strong>Proposition depuis les calques</strong>
            <span className="th-muted">
              Les lignes suivent vos murs, menuiseries et portes désignés. Désignez les vitrages de façade pour une proposition fidèle.
            </span>
            <label className="th-field">
              <span>Refermer les ouvertures de façade jusqu'à (cm)</span>
              <input
                type="number"
                min={0}
                max={300}
                step={10}
                value={fermetureCm}
                onChange={(event) => setFermetureCm(Math.max(0, Math.min(300, Number(event.target.value) || 0)))}
              />
            </label>
            <div className="th-inline">
              <button type="button" className="po2-button po2-button--primary" disabled={busy} onClick={() => proposeMutation.mutate(false)}>
                {lines.length ? "Proposer à nouveau" : "Proposer les deux lignes"}
              </button>
            </div>
            {proposeMutation.isPending && <span className="th-muted">Calcul des lignes… (quelques secondes)</span>}
            {needsConfirm && (
              <div className="th-alert th-alert--warn">
                Des lignes de ce niveau ont été corrigées ou tracées à la main.{" "}
                <button type="button" className="th-link" disabled={busy} onClick={() => proposeMutation.mutate(true)}>
                  Les remplacer par la proposition
                </button>
              </div>
            )}
          </section>
        )}

        {level && (
          <section>
            <h2>Lignes du niveau</h2>
            {lines.length === 0 && <p className="th-muted">Aucune ligne pour l'instant.</p>}
            {lines.length > 0 && (
              <p className="th-muted">
                Nu extérieur {m2(surfaces("nu_exterieur"))} · nu intérieur {m2(surfaces("contour"))}
              </p>
            )}
            <ul className="th-sup-list">
              {lines.map((zone) => (
                <li key={zone.id}>
                  <button
                    type="button"
                    className={`th-sup-item${zone.id === selected?.id ? " is-selected" : ""}`}
                    onClick={() => setZoneId(zone.id)}
                  >
                    <span>
                      <span className={`th-calque-dot th-env-dot--${zone.type}`} /> {zone.nom}
                      <small className="th-muted"> · {zone.points.length} sommets</small>
                    </span>
                    <span className={`th-sup-state${zone.source === "automatique" ? "" : " is-ok"}`}>
                      {zone.source === "automatique" ? "Proposée" : zone.source === "corrige" ? "Corrigée" : "Tracée"}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            {selected && (
              <button type="button" className="th-link th-link--danger" disabled={busy} onClick={() => deleteMutation.mutate(selected)}>
                Supprimer « {selected.nom} » ({LINES[selected.type as keyof typeof LINES]})
              </button>
            )}
            <p className="th-muted">
              Pour tracer une ligne entièrement à la main, utilisez l'onglet <Link to={`/projets/${projectId}/metre`}>Métré</Link>.
            </p>
          </section>
        )}
      </aside>
    </div>
  );
}
