import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../../providers/AuthProvider";
import { thermiqueApi, type PdfPoint } from "../api";
import { componentsApi } from "../components";
import { TileSheetViewer, type PickEvent, type ToScreen } from "../components/TileSheetViewer";
import {
  insertVertex,
  metreApi,
  nearestEdge,
  nearestVertex,
  northOnSheet,
  parseSignedNumber,
  pointInPolygon,
  removeVertex,
  repereOf,
  transferPoint,
  type DonneSur,
  type LevelPayload,
  type Metre,
  type MetreLevel,
  type ZoneEdge,
  type ZonePayload,
  type ZoneType,
} from "../metre";
import { allSheets, projectQueryKey } from "../projectCache";
import { formatMeters } from "../scale";
import { SnapIndex, orthogonal, snapPoint, type SnapResult } from "../snap";
import { ProjectTabs } from "./ProjectLibraryPage";

type MetreTool = "pan" | "contour" | "lnc" | "patio" | "edit" | "calage" | "nord";
type Selection = { zoneId: number; edge: number | null };
type VertexDrag = { zoneId: number; index: number; points: PdfPoint[]; moved: boolean };

const TOOLS: { id: MetreTool; label: string; help: string }[] = [
  { id: "pan", label: "Déplacer", help: "Glissez pour déplacer le plan, molette pour zoomer." },
  {
    id: "contour",
    label: "Contour",
    help: "Cliquez les sommets au nu intérieur des murs qui entourent les locaux chauffés. Cliquez le premier sommet ou appuyez sur Entrée pour fermer. Retour arrière retire le dernier sommet, Maj force un côté horizontal ou vertical, Alt coupe l'aimantation.",
  },
  { id: "lnc", label: "Local non chauffé", help: "Tracez le local (garage, cave, cage d'escalier…) comme un contour. Dans le contour, sa surface est déduite." },
  { id: "patio", label: "Patio", help: "Tracez une cour ou un patio à l'intérieur du contour : ses côtés donnent sur l'extérieur." },
  {
    id: "edit",
    label: "Modifier",
    help: "Cliquez un côté pour le qualifier, glissez un sommet pour le déplacer. Maj + clic sur un côté ajoute un sommet, Alt + clic sur un sommet le retire.",
  },
  { id: "calage", label: "Caler", help: "Cliquez deux repères communs à tous les niveaux (deux croisements d'axes, deux angles de cage d'escalier…), toujours dans le même ordre : A puis B." },
  { id: "nord", label: "Nord", help: "Cliquez le pied puis la pointe de la flèche du nord dessinée sur le plan." },
];

const DRAW_TOOLS: MetreTool[] = ["contour", "lnc", "patio"];
const EDGE_COLORS: Record<DonneSur, string> = { exterieur: "#d0342c", lnc: "#2f6fb0", sol: "#8a5a2b", mitoyen: "#7a7f87" };
// Une couleur par épaisseur, dans l'ordre des linéaires décroissants (légende et plan partagent l'ordre).
const WALL_PALETTE = ["#d0342c", "#2f6fb0", "#e07b00", "#2e9d4f", "#8a3fc4", "#00939c", "#a0522d", "#c2185b", "#5f6b73", "#b59a00"];
const SNAP_PX = 12;
const INSULATION_LABELS: Record<string, string> = {
  interieur: "isolant intérieur",
  exterieur: "isolant extérieur",
  reparti: "isolant réparti",
};
const MAX_DRAWN_TRAITS = 12000;
const RASTER_STALE_MS = 6 * 3600 * 1000;

const areaFormat = new Intl.NumberFormat("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const formatArea = (value: number | null | undefined) => (value == null ? "—" : `${areaFormat.format(value)} m²`);
const formatLength = (value: number | null | undefined) => (value == null ? "—" : formatMeters(value));
const decimalText = (value: number | null) => (value === null ? "" : String(value).replace(".", ","));
const distance = (a: PdfPoint, b: PdfPoint) => Math.hypot(b[0] - a[0], b[1] - a[1]);

function NumberField({ label, value, onSave }: { label: string; value: number | null; onSave: (value: number | null) => void }) {
  return (
    <label className="th-field">
      <span>{label}</span>
      <input
        key={decimalText(value)}
        inputMode="decimal"
        defaultValue={decimalText(value)}
        onBlur={(event) => {
          const raw = event.target.value.trim();
          const next = parseSignedNumber(raw);
          if (raw !== "" && next === null) {
            event.target.value = decimalText(value);
            return;
          }
          if (next !== value) {
            onSave(next);
          }
        }}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.currentTarget.blur();
          }
        }}
      />
    </label>
  );
}

function TextField({ label, value, maxLength, onSave }: { label: string; value: string; maxLength: number; onSave: (value: string) => void }) {
  return (
    <label className="th-field">
      <span>{label}</span>
      <input
        key={value}
        defaultValue={value}
        maxLength={maxLength}
        onBlur={(event) => {
          const next = event.target.value.trim();
          if (next && next !== value) {
            onSave(next);
          } else {
            event.target.value = value;
          }
        }}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.currentTarget.blur();
          }
        }}
      />
    </label>
  );
}

function Alerts({ messages }: { messages: string[] }) {
  return (
    <>
      {messages.map((message) => (
        <p key={message} className="th-alert th-alert--warn">
          {message}
        </p>
      ))}
    </>
  );
}

// Métré d'un projet : un plan par niveau, le contour au nu intérieur, les locaux non chauffés,
// et les niveaux voisins en calque (docs/thermique/metre-plans-decisions.md).
export function MetrePage() {
  const { token } = useAuth();
  const projectId = Number(useParams().projectId);
  const queryClient = useQueryClient();
  const enabled = Boolean(token) && Number.isFinite(projectId);
  const metreKey = useMemo(() => ["thermique", "metre", projectId] as const, [projectId]);

  const [levelId, setLevelId] = useState<number | null>(null);
  const [tool, setTool] = useState<MetreTool>("pan");
  const [draft, setDraft] = useState<PdfPoint[]>([]);
  const [hover, setHover] = useState<SnapResult | null>(null);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [drag, setDrag] = useState<VertexDrag | null>(null);
  const [layers, setLayers] = useState({ below: true, above: false, traits: false, snap: true, murs: false });
  const [wallFilter, setWallFilter] = useState<number | null>(null);
  const [seuil, setSeuil] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [sectionSheetId, setSectionSheetId] = useState<number | null>(null);
  const [sectionChoice, setSectionChoice] = useState({ dessin: 0, inverse: false, premier: 0 });
  const pixelsPerPt = useRef(1);

  const projectQuery = useQuery({
    queryKey: projectQueryKey(projectId),
    queryFn: () => thermiqueApi.getProject(token!, projectId),
    enabled,
  });
  const metreQuery = useQuery({ queryKey: metreKey, queryFn: () => metreApi.get(token!, projectId), enabled });
  const componentsQuery = useQuery({
    queryKey: ["thermique", "metre-composants", projectId],
    queryFn: () => componentsApi.listProject(token!, projectId),
    enabled,
  });

  const metre = metreQuery.data;
  const levels = useMemo(() => [...(metre?.niveaux ?? [])].sort((a, b) => a.ordre - b.ordre || a.id - b.id), [metre]);
  const level = levels.find((item) => item.id === levelId) ?? levels.find((item) => item.planche_id !== null) ?? levels[0] ?? null;
  const levelIndex = level ? levels.indexOf(level) : -1;
  const below = levelIndex > 0 ? levels[levelIndex - 1] : null;
  const above = levelIndex >= 0 && levelIndex < levels.length - 1 ? levels[levelIndex + 1] : null;
  const sheets = projectQuery.data ? allSheets(projectQuery.data) : [];
  const sheet = level?.planche_id ? sheets.find((item) => item.id === level.planche_id) : undefined;
  const rotation = sheet?.rotation_deg ?? 0;

  const raster = useQuery({
    queryKey: ["thermique", "raster", sheet?.id ?? 0, rotation],
    queryFn: () => thermiqueApi.getRaster(token!, sheet!.id, rotation),
    enabled: Boolean(token && sheet),
    staleTime: RASTER_STALE_MS,
  });
  const traits = useQuery({
    queryKey: ["thermique", "traits", sheet?.id ?? 0, seuil],
    queryFn: () => metreApi.traits(token!, sheet!.id, seuil),
    enabled: Boolean(token && sheet),
    staleTime: Infinity,
  });
  const snapIndex = useMemo(() => (traits.data ? new SnapIndex(traits.data.segments) : null), [traits.data]);
  const section = useQuery({
    queryKey: ["thermique", "coupe", sectionSheetId ?? 0],
    queryFn: () => metreApi.section(token!, sectionSheetId!),
    enabled: Boolean(token && sectionSheetId),
    staleTime: Infinity,
  });

  const detectedWalls = useQuery({
    queryKey: ["thermique", "murs", sheet?.id ?? 0, level?.echelle ?? 0],
    queryFn: () => metreApi.walls(token!, sheet!.id),
    enabled: Boolean(token && sheet && layers.murs),
    staleTime: Infinity,
  });
  const wallColors = useMemo(
    () =>
      new Map((detectedWalls.data?.types ?? []).map((type, index) => [Math.round(type.epaisseur_m * 100), WALL_PALETTE[index % WALL_PALETTE.length]])),
    [detectedWalls.data],
  );

  const currentLevelId = level?.id ?? null;
  const currentSheetId = sheet?.id ?? null;
  useEffect(() => {
    setDraft([]);
    setSelection(null);
    setDrag(null);
    setHover(null);
  }, [currentLevelId]);
  useEffect(() => {
    setDraft([]);
    setHover(null);
  }, [tool]);
  useEffect(() => {
    setSeuil(null);
    setWallFilter(null);
  }, [currentSheetId]);

  const keyHandler = useRef<(event: KeyboardEvent) => void>(() => undefined);
  useEffect(() => {
    const listener = (event: KeyboardEvent) => keyHandler.current(event);
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, []);

  async function perform(action: () => Promise<Metre>): Promise<Metre | null> {
    setBusy(true);
    setActionError(null);
    setNotice(null);
    try {
      const data = await action();
      queryClient.setQueryData(metreKey, data);
      return data;
    } catch (failure) {
      setActionError(failure instanceof Error ? failure.message : "Action impossible.");
      void queryClient.invalidateQueries({ queryKey: metreKey });
      return null;
    } finally {
      setBusy(false);
    }
  }

  const saveLevel = (target: MetreLevel, changes: LevelPayload) => perform(() => metreApi.updateLevel(token!, target.id, changes));
  const saveZone = (zoneId: number, payload: ZonePayload) => perform(() => metreApi.updateZone(token!, zoneId, payload));

  // Le tracé sélectionné passe en premier : c'est lui qu'on vise quand deux bords se superposent.
  const zonesInOrder = level
    ? [...level.zones].sort((a, b) => Number(b.id === selection?.zoneId) - Number(a.id === selection?.zoneId))
    : [];

  function vertices(exclude?: { zoneId: number; index: number }): PdfPoint[] {
    const result: PdfPoint[] = [];
    level?.zones.forEach((zone) =>
      zone.points.forEach((point, index) => {
        if (!(exclude && exclude.zoneId === zone.id && exclude.index === index)) {
          result.push(point);
        }
      }),
    );
    if (draft.length) {
      result.push(draft[0]);
    }
    return result;
  }

  function snap(point: PdfPoint, event: PickEvent, previous: PdfPoint | null, exclude?: { zoneId: number; index: number }): SnapResult {
    if (event.shiftKey && previous) {
      return { point: orthogonal(previous, point), kind: "orthogonal" };
    }
    if (!layers.snap || event.altKey) {
      return { point, kind: "libre" };
    }
    return snapPoint(point, SNAP_PX / pixelsPerPt.current, snapIndex, vertices(exclude));
  }

  async function finishPolygon() {
    if (!level || draft.length < 3 || !DRAW_TOOLS.includes(tool)) {
      return;
    }
    const known = new Set(level.zones.map((zone) => zone.id));
    const data = await perform(() => metreApi.createZone(token!, level.id, { type: tool as ZoneType, points: draft }));
    if (!data) {
      return;
    }
    setDraft([]);
    const created = data.niveaux.find((item) => item.id === level.id)?.zones.find((zone) => !known.has(zone.id));
    if (created) {
      setSelection({ zoneId: created.id, edge: null });
      setTool("edit");
    }
  }

  keyHandler.current = (event) => {
    const target = event.target as HTMLElement | null;
    if (target && ["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName)) {
      return;
    }
    if (event.key === "Escape") {
      setDraft([]);
      setSelection(null);
      setDrag(null);
    } else if (event.key === "Backspace" && draft.length) {
      event.preventDefault();
      setDraft((current) => current.slice(0, -1));
    } else if (event.key === "Enter" && draft.length >= 3) {
      void finishPolygon();
    }
  };

  function handlePick(point: PdfPoint, event: PickEvent) {
    if (!level || !token) {
      return;
    }
    const tolerance = SNAP_PX / pixelsPerPt.current;
    if (DRAW_TOOLS.includes(tool)) {
      const snapped = snap(point, event, draft[draft.length - 1] ?? null);
      if (draft.length >= 3 && distance(snapped.point, draft[0]) <= tolerance) {
        void finishPolygon();
        return;
      }
      setDraft([...draft, snapped.point]);
      return;
    }
    if (tool === "calage" || tool === "nord") {
      const next = [...draft, snap(point, event, draft[0] ?? null).point];
      if (next.length < 2) {
        setDraft(next);
        return;
      }
      setDraft([]);
      setTool("pan");
      if (tool === "calage") {
        void saveLevel(level, { calage: { a: next[0], b: next[1] } });
      } else {
        void perform(() => metreApi.setNorth(token, projectId, { niveau_id: level.id, p1: next[0], p2: next[1] }));
      }
      return;
    }
    if (tool !== "edit") {
      return;
    }
    if (event.altKey) {
      for (const zone of zonesInOrder) {
        const vertex = nearestVertex(zone.points, point, tolerance);
        if (vertex === null) {
          continue;
        }
        if (zone.points.length <= 3) {
          setActionError("Un tracé garde au moins trois sommets.");
          return;
        }
        const next = removeVertex(zone.points, zone.cotes, vertex);
        setSelection({ zoneId: zone.id, edge: null });
        void saveZone(zone.id, zone.type === "lnc" ? { points: next.points } : next);
        return;
      }
    }
    for (const zone of zonesInOrder) {
      const edge = nearestEdge(zone.points, point, tolerance);
      if (!edge) {
        continue;
      }
      if (event.shiftKey) {
        const next = insertVertex(zone.points, zone.cotes, edge.index, edge.point);
        void saveZone(zone.id, zone.type === "lnc" ? { points: next.points } : next);
      }
      setSelection({ zoneId: zone.id, edge: zone.type === "lnc" ? null : edge.index });
      return;
    }
    const inside = zonesInOrder.find((zone) => pointInPolygon(point, zone.points));
    setSelection(inside ? { zoneId: inside.id, edge: null } : null);
  }

  function handleHover(point: PdfPoint | null, scale: number, event: PickEvent) {
    pixelsPerPt.current = scale;
    if (tool === "pan" || tool === "edit") {
      if (hover && !drag) {
        setHover(null);
      }
      return;
    }
    setHover(point ? snap(point, event, draft[draft.length - 1] ?? null) : null);
  }

  function handleGrab(point: PdfPoint, scale: number, event: PickEvent): boolean {
    pixelsPerPt.current = scale;
    if (tool !== "edit" || !level || event.altKey || event.shiftKey) {
      return false;
    }
    for (const zone of zonesInOrder) {
      const vertex = nearestVertex(zone.points, point, SNAP_PX / scale);
      if (vertex !== null) {
        setDrag({ zoneId: zone.id, index: vertex, points: zone.points, moved: false });
        setSelection((current) => (current?.zoneId === zone.id ? current : { zoneId: zone.id, edge: null }));
        return true;
      }
    }
    return false;
  }

  function handleGrabMove(point: PdfPoint, event: PickEvent) {
    if (!drag) {
      return;
    }
    const snapped = snap(point, event, null, { zoneId: drag.zoneId, index: drag.index });
    setHover(snapped);
    setDrag({ ...drag, points: drag.points.map((item, index) => (index === drag.index ? snapped.point : item)), moved: true });
  }

  function handleGrabEnd() {
    const current = drag;
    setDrag(null);
    setHover(null);
    if (!current?.moved) {
      return;
    }
    // Affichage immédiat du sommet déplacé, en attendant la réponse du serveur.
    queryClient.setQueryData<Metre>(metreKey, (data) =>
      data
        ? {
            ...data,
            niveaux: data.niveaux.map((item) => ({
              ...item,
              zones: item.zones.map((zone) => (zone.id === current.zoneId ? { ...zone, points: current.points } : zone)),
            })),
          }
        : data,
    );
    void saveZone(current.zoneId, { points: current.points });
  }

  async function moveLevel(direction: 1 | -1) {
    const neighbour = level ? levels[levelIndex + direction] : undefined;
    if (!level || !neighbour) {
      return;
    }
    const mine = level.ordre;
    const target = mine === neighbour.ordre ? neighbour.ordre + direction : neighbour.ordre;
    if (await saveLevel(neighbour, { ordre: mine })) {
      await saveLevel(level, { ordre: target });
    }
  }

  async function detectWalls(zoneId: number) {
    const data = await perform(() => metreApi.detectWalls(token!, zoneId));
    if (data?.detection_murs) {
      const found = data.detection_murs;
      setNotice(
        `Murs lus sur ${found.cotes_lues} côté(s) sur ${found.cotes}, ${found.types} type(s) proposé(s). Rattachez chaque type à un composant ; les parties vitrées restent non lues.`,
      );
    }
  }

  async function acceptWallType(zoneId: number, thickness: number, componentId: number | null) {
    const data = await perform(() => metreApi.acceptWallType(token!, zoneId, { epaisseur_m: thickness, composant_id: componentId }));
    if (data) {
      void componentsQuery.refetch();
      setNotice(
        componentId
          ? "Type de mur rattaché au composant."
          : "Composant créé dans la bibliothèque du projet (composition à compléter) et rattaché aux côtés de ce type.",
      );
    }
  }

  async function createWallComponent(thickness: number, lengthM: number) {
    if (!token) {
      return;
    }
    setBusy(true);
    setActionError(null);
    try {
      await componentsApi.createInProject(token, projectId, {
        categorie: "murs",
        nom: `Mur ${thickness} cm`,
        notes: `Type détecté sur le plan : épaisseur ${thickness} cm sur ${lengthM.toFixed(1).replace(".", ",")} m. Composition à compléter.`,
      });
      await componentsQuery.refetch();
      setNotice(`Composant « Mur ${thickness} cm » créé dans la bibliothèque du projet (composition à compléter).`);
    } catch (failure) {
      setActionError(failure instanceof Error ? failure.message : "Création du composant impossible.");
    } finally {
      setBusy(false);
    }
  }

  async function detectContour() {
    if (!level || !token) {
      return;
    }
    const handDrawn = level.zones.some((zone) => zone.type === "contour" && zone.source !== "automatique");
    if (handDrawn && !window.confirm("Ce niveau a déjà un contour tracé ou corrigé à la main. Le remplacer par la détection ?")) {
      return;
    }
    setSelection(null);
    const data = await perform(() => metreApi.detectContour(token, level.id, handDrawn));
    const created = data?.niveaux.find((item) => item.id === level.id)?.zones.find((zone) => zone.source === "automatique");
    if (data?.detection && created) {
      setSelection({ zoneId: created.id, edge: null });
      setTool("edit");
      setNotice(
        `Contour détecté : ${formatArea(data.detection.aire_m2)}, ${data.detection.sommets} sommets${
          data.detection.zones_exterieures_ecartees ? `, ${data.detection.zones_exterieures_ecartees} zone(s) hachurée(s) laissée(s) dehors` : ""
        }. Vérifiez-le sur le plan et corrigez avec « Modifier ».`,
      );
    }
  }

  function removeLevel() {
    if (!level || !window.confirm(`Supprimer le niveau « ${level.nom} » et tous ses tracés ?`)) {
      return;
    }
    setLevelId(null);
    void perform(() => metreApi.deleteLevel(token!, level.id));
  }

  function renderOverlay(toScreen: ToScreen): ReactNode {
    if (!level) {
      return null;
    }
    const polygonPoints = (points: PdfPoint[]) => points.map((point) => toScreen(point).map((value) => value.toFixed(1)).join(",")).join(" ");
    const current = repereOf(level);
    const ghosts = [
      { key: "dessous", other: below, shown: layers.below },
      { key: "dessus", other: above, shown: layers.above },
    ];
    return (
      <>
        {layers.traits && traits.data && traits.data.segments.length <= MAX_DRAWN_TRAITS && (
          <g className="th-snaplines">
            {traits.data.segments.map((segment, index) => {
              const [x1, y1] = toScreen([segment[0], segment[1]]);
              const [x2, y2] = toScreen([segment[2], segment[3]]);
              return <line key={index} x1={x1} y1={y1} x2={x2} y2={y2} />;
            })}
          </g>
        )}

        {layers.murs && detectedWalls.data && (
          <g className="th-walls">
            {detectedWalls.data.murs.map((wall, index) => {
              const thickness = Math.round(wall.epaisseur_m * 100);
              const color = wallColors.get(thickness) ?? "#5f6b73";
              return (
                <polygon
                  key={index}
                  className={wallFilter !== null && wallFilter !== thickness ? "is-dimmed" : undefined}
                  points={polygonPoints(wall.points)}
                  fill={color}
                  stroke={color}
                />
              );
            })}
          </g>
        )}

        {current &&
          ghosts.map(({ key, other, shown }) => {
            const otherRepere = other ? repereOf(other) : null;
            if (!shown || !other || !otherRepere) {
              return null;
            }
            return (
              <g key={key} className={`th-ghost th-ghost--${key}`}>
                {other.zones
                  .filter((zone) => zone.type !== "lnc")
                  .map((zone) => (
                    <polygon key={zone.id} points={polygonPoints(zone.points.map((point) => transferPoint(otherRepere, current, point)))} />
                  ))}
              </g>
            );
          })}

        {level.zones.map((zone) => {
          const points = drag?.zoneId === zone.id ? drag.points : zone.points;
          const selected = selection?.zoneId === zone.id;
          const screen = points.map(toScreen);
          const labelX = screen.reduce((sum, [x]) => sum + x, 0) / screen.length;
          const labelY = screen.reduce((sum, [, y]) => sum + y, 0) / screen.length;
          return (
            <g key={zone.id} className={`th-zone th-zone--${zone.type}${selected ? " is-selected" : ""}`}>
              <polygon points={polygonPoints(points)} />
              {zone.type !== "lnc" &&
                screen.map(([x1, y1], index) => {
                  const [x2, y2] = screen[(index + 1) % screen.length];
                  const edgeSelected = selected && selection?.edge === index;
                  return (
                    <line
                      key={index}
                      className={edgeSelected ? "th-edge is-selected" : "th-edge"}
                      stroke={EDGE_COLORS[zone.cotes[index]?.donne_sur ?? "exterieur"]}
                      x1={x1}
                      y1={y1}
                      x2={x2}
                      y2={y2}
                    />
                  );
                })}
              {selected && screen.map(([x, y], index) => <circle key={`s${index}`} className="th-vertex" cx={x} cy={y} r={4.5} />)}
              <text x={labelX} y={labelY} textAnchor="middle">
                {zone.nom}
              </text>
            </g>
          );
        })}

        {level.calage &&
          (["a", "b"] as const).map((key) => {
            const [x, y] = toScreen(level.calage![key]);
            return (
              <g key={key} className="th-calage">
                <circle cx={x} cy={y} r={6} />
                <text x={x + 9} y={y - 9}>
                  {key.toUpperCase()}
                </text>
              </g>
            );
          })}

        {current &&
          level.calage &&
          metre?.nord_deg != null &&
          (() => {
            const [dx, dy] = northOnSheet(current, metre.nord_deg);
            const origin = level.calage.a;
            const [x0, y0] = toScreen(origin);
            const [x1, y1] = toScreen([origin[0] + dx, origin[1] + dy]);
            const length = Math.hypot(x1 - x0, y1 - y0) || 1;
            const [ux, uy] = [(x1 - x0) / length, (y1 - y0) / length];
            return (
              <g className="th-north">
                <line x1={x0} y1={y0} x2={x0 + ux * 70} y2={y0 + uy * 70} />
                <text x={x0 + ux * 86} y={y0 + uy * 86} textAnchor="middle" dominantBaseline="middle">
                  N
                </text>
              </g>
            );
          })()}

        {draft.length > 0 && (
          <g className="th-draft">
            <polyline points={polygonPoints(hover && tool !== "calage" ? [...draft, hover.point] : draft)} />
            {draft.map((point, index) => {
              const [x, y] = toScreen(point);
              return <circle key={index} cx={x} cy={y} r={index === 0 ? 6 : 4} />;
            })}
          </g>
        )}

        {hover &&
          tool !== "pan" &&
          (() => {
            const [x, y] = toScreen(hover.point);
            return (
              <g className="th-snap">
                {hover.kind === "sommet" ? (
                  <circle cx={x} cy={y} r={8} />
                ) : hover.kind === "trait" ? (
                  <path d={`M${x - 6} ${y - 6} L${x + 6} ${y + 6} M${x + 6} ${y - 6} L${x - 6} ${y + 6}`} />
                ) : hover.kind === "libre" || hover.kind === "orthogonal" ? (
                  <circle cx={x} cy={y} r={3} />
                ) : (
                  <rect x={x - 6} y={y - 6} width={12} height={12} />
                )}
              </g>
            );
          })()}
      </>
    );
  }

  if (metreQuery.error || projectQuery.error) {
    return <p className="th-alert th-alert--error th-main">{(metreQuery.error ?? projectQuery.error)?.message}</p>;
  }
  if (!metre || !projectQuery.data || !token) {
    return <p className="th-muted th-main">Chargement du métré…</p>;
  }

  const listes = metre.listes;
  const zone = level && selection ? level.zones.find((item) => item.id === selection.zoneId) ?? null : null;
  const zoneSummary = zone && level ? level.synthese.zones.find((item) => item.id === zone.id) ?? null : null;
  const walls = (componentsQuery.data ?? []).filter((item) => item.categorie === "murs");
  const planSheets = [...sheets].sort((a, b) => Number(b.nature === "plan") - Number(a.nature === "plan"));
  const helpText = TOOLS.find((item) => item.id === tool)?.help;
  const summary = level?.synthese;
  const referenceLevel = levels.find((item) => item.calage && item.calage_ecart_m === 0);
  const sectionSheets = sheets.filter((item) => (item.nature ?? item.nature_suggested) === "coupe");
  const sectionDrawing = section.data?.dessins[sectionChoice.dessin] ?? null;
  const sectionIntervals = sectionDrawing ? (sectionChoice.inverse ? sectionDrawing.niveaux_descendant : sectionDrawing.niveaux_montant) : [];

  function setEdges(edge: number | "all", changes: Partial<ZoneEdge>) {
    if (!zone) {
      return;
    }
    void saveZone(zone.id, { cotes: zone.cotes.map((cote, index) => (edge === "all" || index === edge ? { ...cote, ...changes } : cote)) });
  }

  return (
    <div className="th-viewer-layout">
      {!level ? (
        <div className="th-viewer th-viewer--empty">
          <p className="th-viewer__status">Créez les niveaux du bâtiment dans le panneau de droite pour commencer le métré.</p>
        </div>
      ) : !sheet ? (
        <div className="th-viewer th-viewer--empty">
          <p className="th-viewer__status">Associez une planche de plan au niveau « {level.nom} ».</p>
        </div>
      ) : raster.data ? (
        <TileSheetViewer
          manifest={raster.data}
          tileTemplate={thermiqueApi.apiUrl(raster.data.tile_url)}
          tool={tool}
          onAddPoint={handlePick}
          onHover={handleHover}
          onGrab={handleGrab}
          onGrabMove={handleGrabMove}
          onGrabEnd={handleGrabEnd}
          renderOverlay={renderOverlay}
        />
      ) : (
        <div className="th-viewer th-viewer--empty">
          <p className="th-viewer__status">
            {raster.error ? `Affichage impossible : ${raster.error.message}` : "Préparation de la planche… (quelques secondes à la première ouverture)"}
          </p>
        </div>
      )}

      <aside className="th-panel">
        <div>
          <p className="po2-eyebrow">
            <Link to="/">Projets</Link> · <Link to={`/projets/${projectId}`}>{projectQuery.data.name}</Link>
          </p>
          <h1 className="th-panel__title">Métré{level ? ` · ${level.nom}` : ""}</h1>
        </div>
        <ProjectTabs projectId={projectId} />
        {busy && <p className="th-muted">Traitement en cours… (la lecture d'un plan prend 10 à 15 s la première fois)</p>}
        {actionError && <p className="th-alert th-alert--error">{actionError}</p>}
        {notice && <p className="th-alert th-alert--ok">{notice}</p>}
        <Alerts messages={metre.alertes} />

        <section>
          <h2>Niveaux</h2>
          {levels.length === 0 && (
            <p className="th-muted">
              Un niveau par plan : le contour de chaque niveau est ensuite calqué sur ceux du dessous et du dessus.
            </p>
          )}
          <ul className="th-levels">
            {[...levels].reverse().map((item) => (
              <li key={item.id}>
                <button type="button" className={item.id === level?.id ? "is-active" : undefined} onClick={() => setLevelId(item.id)}>
                  <strong>{item.nom}</strong>
                  <small>
                    {item.synthese.surface_chauffee_m2 != null ? formatArea(item.synthese.surface_chauffee_m2) : item.zones.length ? "tracé" : "à tracer"}
                    {!item.calage && " · non calé"}
                  </small>
                </button>
              </li>
            ))}
          </ul>
          <div className="th-inline">
            <button type="button" className="po2-button po2-button--secondary" disabled={busy} onClick={() => void perform(() => metreApi.levelsFromSheets(token, projectId))}>
              Créer depuis les planches
            </button>
            <button type="button" className="po2-button po2-button--ghost" disabled={busy} onClick={() => void perform(() => metreApi.createLevel(token, projectId, {}))}>
              + Niveau
            </button>
          </div>
        </section>

        {level && (
          <section>
            <h2>Niveau sélectionné</h2>
            <TextField label="Nom" value={level.nom} maxLength={80} onSave={(nom) => void saveLevel(level, { nom })} />
            <label className="th-field">
              <span>Plan du niveau</span>
              <select
                value={level.planche_id ?? ""}
                disabled={busy}
                onChange={(event) => {
                  const next = event.target.value ? Number(event.target.value) : null;
                  if (level.calage && !window.confirm("Changer de plan efface le calage de ce niveau. Continuer ?")) {
                    return;
                  }
                  void saveLevel(level, { planche_id: next });
                }}
              >
                <option value="">Aucune planche</option>
                {planSheets.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <div className="th-grid3">
              <NumberField label="Altitude (m)" value={level.altitude_m} onSave={(value) => void saveLevel(level, { altitude_m: value })} />
              <NumberField label="Hauteur d'étage (m)" value={level.hauteur_etage_m} onSave={(value) => void saveLevel(level, { hauteur_etage_m: value })} />
              <NumberField label="Plancher (m)" value={level.epaisseur_plancher_m} onSave={(value) => void saveLevel(level, { epaisseur_plancher_m: value })} />
            </div>
            <NumberField
              label="Hauteur sous plafond (m) — prime sur étage − plancher"
              value={level.hauteur_sous_plafond_m}
              onSave={(value) => void saveLevel(level, { hauteur_sous_plafond_m: value })}
            />
            {level.hauteurs_source && (
              <p className="th-muted">Hauteurs {level.hauteurs_source === "coupe" ? "lues sur une coupe" : "saisies à la main"}.</p>
            )}
            <p className="th-muted">
              {level.calage
                ? `Calé : A-B = ${formatLength(level.calage_ab_m)}${
                    referenceLevel && referenceLevel.id !== level.id && level.calage_ecart_m !== null
                      ? ` (écart ${Math.round(level.calage_ecart_m * 100)} cm avec « ${referenceLevel.nom} »)`
                      : ""
                  }.`
                : "Non calé : cliquez l'outil « Caler » pour superposer ce niveau aux autres."}
              {metre.nord_deg !== null ? " Nord défini." : " Nord à poser (outil « Nord »)."}
            </p>
            <div className="th-inline">
              <button type="button" className="po2-button po2-button--ghost" disabled={busy || !above} onClick={() => void moveLevel(1)}>
                Monter
              </button>
              <button type="button" className="po2-button po2-button--ghost" disabled={busy || !below} onClick={() => void moveLevel(-1)}>
                Descendre
              </button>
              <button type="button" className="th-link th-link--danger" disabled={busy} onClick={removeLevel}>
                Supprimer le niveau
              </button>
            </div>
          </section>
        )}

        {level && sheet && (
          <section>
            <h2>Murs du plan</h2>
            <button
              type="button"
              className="po2-button po2-button--secondary"
              onClick={() => {
                setLayers({ ...layers, murs: !layers.murs });
                setWallFilter(null);
              }}
            >
              {layers.murs ? "Masquer les murs détectés" : "Afficher les murs détectés"}
            </button>
            {layers.murs && detectedWalls.isFetching && <p className="th-muted">Lecture des murs sur les traits du plan… (quelques secondes la première fois)</p>}
            {layers.murs && detectedWalls.error && <p className="th-alert th-alert--error">{detectedWalls.error.message}</p>}
            {layers.murs && detectedWalls.data && (
              <>
                <p className="th-muted">
                  {detectedWalls.data.murs.length} murs coupés, {formatLength(detectedWalls.data.lineaire_m)} de linéaire. Cliquez une épaisseur pour
                  isoler ses murs sur le plan.
                </p>
                <ul className="th-wall-types">
                  {detectedWalls.data.types.map((type) => {
                    const thickness = Math.round(type.epaisseur_m * 100);
                    const name = `Mur ${thickness} cm`;
                    const existing = walls.find((item) => item.nom === name);
                    return (
                      <li key={thickness}>
                        <button
                          type="button"
                          className={wallFilter === thickness ? "is-active" : undefined}
                          aria-pressed={wallFilter === thickness}
                          onClick={() => setWallFilter(wallFilter === thickness ? null : thickness)}
                        >
                          <span className="th-wall-swatch" style={{ background: wallColors.get(thickness) }} />
                          <strong>{thickness} cm</strong>
                          <span>
                            {type.nombre} mur{type.nombre > 1 ? "s" : ""} · {formatLength(type.longueur_m)}
                          </span>
                          <small className="th-muted">{existing ? existing.code : ""}</small>
                        </button>
                        {!existing && wallFilter === thickness && (
                          <button
                            type="button"
                            className="th-link"
                            disabled={busy}
                            onClick={() => void createWallComponent(thickness, type.longueur_m)}
                          >
                            Créer le composant « {name} » dans la bibliothèque du projet
                          </button>
                        )}
                      </li>
                    );
                  })}
                </ul>
                {detectedWalls.data.parois_composees.length > 0 && (
                  <p className="th-muted">
                    Parois composées :{" "}
                    {detectedWalls.data.parois_composees
                      .map((paroi) => `${Math.round(paroi.epaisseur_m * 100)} cm (${paroi.couches_m.map((c) => Math.round(c * 100)).join(" + ")})`)
                      .filter((text, index, all) => all.indexOf(text) === index)
                      .join(", ")}
                    .
                  </p>
                )}
                <p className="th-muted">
                  Lecture directe des vecteurs du PDF : un mur est la paire de ses deux faces, son épaisseur est mesurée entre elles. Aucun contour
                  n'est nécessaire.
                </p>
              </>
            )}
          </section>
        )}

        {level && sheet && (
          <section>
            <h2>Détection automatique</h2>
            <button type="button" className="po2-button po2-button--secondary" disabled={busy} onClick={() => void detectContour()}>
              Détecter le contour de ce niveau
            </button>
            <p className="th-muted">
              Propose le contour au nu intérieur des murs extérieurs. Vérifiez-le toujours : terrasses, coursives et bandes plantées peuvent être
              mal interprétées. Les locaux non chauffés restent à tracer.
            </p>
          </section>
        )}

        {level && sheet && (
          <section>
            <h2>Outils</h2>
            <div className="th-segmented th-tools" role="group" aria-label="Outil">
              {TOOLS.map((item) => (
                <button key={item.id} type="button" className={tool === item.id ? "is-active" : undefined} onClick={() => setTool(item.id)}>
                  {item.label}
                </button>
              ))}
            </div>
            <p className="th-muted">{helpText} Échap annule.</p>
            {DRAW_TOOLS.includes(tool) && draft.length >= 3 && (
              <button type="button" className="po2-button po2-button--secondary" disabled={busy} onClick={() => void finishPolygon()}>
                Fermer le tracé ({draft.length} sommets)
              </button>
            )}
            {(tool === "calage" || tool === "nord") && draft.length === 1 && <p className="th-muted">Premier point posé, cliquez le second.</p>}
          </section>
        )}

        {level && zone && (
          <section>
            <h2>{listes.types_zone[zone.type]}</h2>
            <p className={zone.source === "automatique" ? "th-alert th-alert--warn" : "th-muted"}>
              {zone.source === "automatique"
                ? "Détecté automatiquement : à vérifier."
                : zone.source === "corrige"
                  ? "Détecté puis corrigé à la main."
                  : "Tracé à la main."}
            </p>
            <TextField label="Nom" value={zone.nom} maxLength={120} onSave={(nom) => void saveZone(zone.id, { nom })} />
            {zone.type === "lnc" && (
              <label className="th-field">
                <span>Type de local</span>
                <select value={zone.type_lnc ?? "autre"} disabled={busy} onChange={(event) => void saveZone(zone.id, { type_lnc: event.target.value })}>
                  {Object.entries(listes.types_lnc).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <p className="th-muted">
              {formatArea(zoneSummary?.aire_m2)} · périmètre {formatLength(zoneSummary?.perimetre_m)}
              {zone.type !== "contour" && zoneSummary?.incluse_dans_contour != null && (zoneSummary.incluse_dans_contour ? " · déduit du contour" : " · hors contour")}
            </p>
            <Alerts messages={zoneSummary?.alertes ?? []} />

            {zone.type !== "lnc" &&
              (selection?.edge != null && zone.cotes[selection.edge] ? (
                <div className="th-edgebox">
                  <strong>
                    Côté {selection.edge + 1} / {zone.cotes.length} · {formatLength(zoneSummary?.cotes_m?.[selection.edge])}
                  </strong>
                  {zone.cotes[selection.edge].mur && (
                    <p className="th-muted">
                      {zone.cotes[selection.edge].mur!.epaisseur_m != null
                        ? `Mur lu sur le plan : ${Math.round(zone.cotes[selection.edge].mur!.epaisseur_m! * 100)} cm${
                            zone.cotes[selection.edge].mur!.isolant ? `, ${INSULATION_LABELS[zone.cotes[selection.edge].mur!.isolant!]}` : ""
                          } (${Math.round(zone.cotes[selection.edge].mur!.part_lue * 100)} % du côté)`
                        : "Aucun mur lu sur ce côté (vitrage, ouverture ou dessin non reconnu)."}
                    </p>
                  )}
                  <label className="th-field">
                    <span>Donne sur</span>
                    <select
                      value={zone.cotes[selection.edge].donne_sur}
                      disabled={busy}
                      onChange={(event) => setEdges(selection.edge!, { donne_sur: event.target.value as DonneSur })}
                    >
                      {Object.entries(listes.donne_sur).map(([key, label]) => (
                        <option key={key} value={key}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="th-field">
                    <span>Composant mur</span>
                    <select
                      value={zone.cotes[selection.edge].composant_id ?? ""}
                      disabled={busy}
                      onChange={(event) => setEdges(selection.edge!, { composant_id: event.target.value ? Number(event.target.value) : null })}
                    >
                      <option value="">Non rattaché</option>
                      {walls.map((wall) => (
                        <option key={wall.id} value={wall.id}>
                          {wall.code} · {wall.nom}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="th-inline">
                    <button
                      type="button"
                      className="po2-button po2-button--ghost"
                      onClick={() => setSelection({ zoneId: zone.id, edge: (selection.edge! - 1 + zone.cotes.length) % zone.cotes.length })}
                    >
                      Côté précédent
                    </button>
                    <button
                      type="button"
                      className="po2-button po2-button--ghost"
                      onClick={() => setSelection({ zoneId: zone.id, edge: (selection.edge! + 1) % zone.cotes.length })}
                    >
                      Côté suivant
                    </button>
                  </div>
                </div>
              ) : (
                <p className="th-muted">Avec l'outil « Modifier », cliquez un côté sur le plan pour dire sur quoi il donne.</p>
              ))}
            {zone.type !== "lnc" && (
              <div className="th-edgebox">
                <strong>Types de murs</strong>
                <button type="button" className="po2-button po2-button--secondary" disabled={busy} onClick={() => void detectWalls(zone.id)}>
                  {zone.types_murs?.length ? "Relire les murs sur le plan" : "Détecter les types de murs"}
                </button>
                {!zone.types_murs?.length && (
                  <p className="th-muted">Lit l'épaisseur du mur et la position de l'isolant de chaque côté, puis propose un type par épaisseur.</p>
                )}
                {(zone.types_murs ?? []).map((wallType) => (
                  <div key={wallType.epaisseur_m} className="th-walltype">
                    <span>
                      <strong>{Math.round(wallType.epaisseur_m * 100)} cm</strong>
                      {wallType.isolant ? ` · ${INSULATION_LABELS[wallType.isolant]}` : ""} · {formatLength(wallType.longueur_m)} ·{" "}
                      {wallType.cotes.length} côté{wallType.cotes.length > 1 ? "s" : ""}
                    </span>
                    <div className="th-inline">
                      <select
                        value={wallType.composants.length === 1 ? wallType.composants[0] : ""}
                        disabled={busy}
                        onChange={(event) => {
                          if (event.target.value) {
                            void acceptWallType(zone.id, wallType.epaisseur_m, Number(event.target.value));
                          }
                        }}
                      >
                        <option value="">{wallType.composants.length > 1 ? "Plusieurs composants" : "Rattacher à…"}</option>
                        {walls.map((wall) => (
                          <option key={wall.id} value={wall.id}>
                            {wall.code} · {wall.nom}
                          </option>
                        ))}
                      </select>
                      {wallType.composants.length === 0 && (
                        <button type="button" className="th-link" disabled={busy} onClick={() => void acceptWallType(zone.id, wallType.epaisseur_m, null)}>
                          Créer le composant
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
            {zone.type !== "lnc" && (
              <label className="th-field">
                <span>Tous les côtés donnent sur</span>
                <select
                  value=""
                  disabled={busy}
                  onChange={(event) => {
                    if (event.target.value) {
                      setEdges("all", { donne_sur: event.target.value as DonneSur });
                    }
                  }}
                >
                  <option value="">Choisir…</option>
                  {Object.entries(listes.donne_sur).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <button
              type="button"
              className="th-link th-link--danger"
              disabled={busy}
              onClick={() => {
                if (window.confirm(`Supprimer « ${zone.nom} » ?`)) {
                  setSelection(null);
                  void perform(() => metreApi.deleteZone(token, zone.id));
                }
              }}
            >
              Supprimer ce tracé
            </button>
          </section>
        )}

        {levels.length > 0 && (
          <section>
            <h2>Hauteurs depuis une coupe</h2>
            <label className="th-field">
              <span>Coupe</span>
              <select
                value={sectionSheetId ?? ""}
                onChange={(event) => {
                  setSectionSheetId(event.target.value ? Number(event.target.value) : null);
                  setSectionChoice({ dessin: 0, inverse: false, premier: 0 });
                }}
              >
                <option value="">Choisir une coupe…</option>
                {sectionSheets.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            {section.isFetching && <p className="th-muted">Lecture des planchers de la coupe…</p>}
            {section.error && <p className="th-alert th-alert--error">{section.error.message}</p>}
            {section.data && section.data.dessins.length === 0 && (
              <p className="th-alert th-alert--warn">Aucun plancher repéré sur cette coupe : saisissez les hauteurs à la main.</p>
            )}
            {sectionDrawing && (
              <>
                <label className="th-field">
                  <span>Dessin</span>
                  <select
                    value={sectionChoice.dessin}
                    onChange={(event) => setSectionChoice({ dessin: Number(event.target.value), inverse: false, premier: 0 })}
                  >
                    {section.data!.dessins.map((dessin) => (
                      <option key={dessin.index} value={dessin.index}>
                        Dessin {dessin.index + 1} · {dessin.planchers.length} planchers · étages {dessin.hauteurs_etage_m.map(decimalText).join(" / ")} m
                      </option>
                    ))}
                  </select>
                </label>
                <label className="th-check">
                  <input
                    type="checkbox"
                    checked={sectionChoice.inverse}
                    onChange={(event) => setSectionChoice({ ...sectionChoice, inverse: event.target.checked, premier: 0 })}
                  />
                  Lire les planchers dans l'autre sens (si les hauteurs paraissent inversées)
                </label>
                <label className="th-field">
                  <span>Intervalle du niveau le plus bas ({levels[0].nom})</span>
                  <select value={sectionChoice.premier} onChange={(event) => setSectionChoice({ ...sectionChoice, premier: Number(event.target.value) })}>
                    {sectionIntervals.map((interval, index) => (
                      <option key={index} value={index}>
                        Intervalle {index + 1} : étage {formatLength(interval.hauteur_etage_m)}, plancher {formatLength(interval.epaisseur_plancher_m)}
                      </option>
                    ))}
                  </select>
                </label>
                <dl className="th-dl">
                  {levels.map((item, offset) => {
                    const interval = sectionIntervals[sectionChoice.premier + offset];
                    return (
                      <div key={item.id} style={{ display: "contents" }}>
                        <dt>{item.nom}</dt>
                        <dd>
                          {interval
                            ? `étage ${decimalText(interval.hauteur_etage_m)} · plancher ${decimalText(interval.epaisseur_plancher_m)} · HSP ${decimalText(interval.hauteur_sous_plafond_m)} m`
                            : "—"}
                        </dd>
                      </div>
                    );
                  })}
                </dl>
                <p className="th-muted">Hauteur sous plafond brute : de dalle à dalle, sans faux plafond ni revêtements.</p>
                <button
                  type="button"
                  className="po2-button po2-button--secondary"
                  disabled={busy}
                  onClick={() =>
                    void perform(() =>
                      metreApi.applySectionHeights(token, projectId, {
                        planche_id: sectionSheetId!,
                        dessin: sectionChoice.dessin,
                        sens_montant: !sectionChoice.inverse,
                        premier_intervalle: sectionChoice.premier,
                      }),
                    ).then((data) => {
                      if (data) {
                        setNotice("Hauteurs reportées sur les niveaux. Elles restent modifiables niveau par niveau.");
                      }
                    })
                  }
                >
                  Appliquer aux niveaux
                </button>
              </>
            )}
          </section>
        )}

        {level && summary && (
          <section>
            <h2>Synthèse du niveau</h2>
            <dl className="th-dl">
              <dt>Contour (nu intérieur)</dt>
              <dd>{formatArea(summary.surface_contour_m2)}</dd>
              <dt>Locaux non chauffés tracés</dt>
              <dd>{formatArea(summary.surface_lnc_m2)}</dd>
              <dt>Patios tracés</dt>
              <dd>{formatArea(summary.surface_patio_m2)}</dd>
              <dt>Surface intérieure chauffée</dt>
              <dd>{formatArea(summary.surface_chauffee_m2)}</dd>
              <dt>Hauteur intérieure</dt>
              <dd>{formatLength(summary.hauteur_interieure_m)}</dd>
            </dl>
            {summary.lineaires_m && (
              <dl className="th-dl">
                {(Object.keys(listes.donne_sur) as DonneSur[]).map((key) => (
                  <div key={key} style={{ display: "contents" }}>
                    <dt>
                      <span className="th-dot" style={{ background: EDGE_COLORS[key] }} />
                      Parois sur {listes.donne_sur[key].toLowerCase()}
                    </dt>
                    <dd>
                      {formatLength(summary.lineaires_m![key])}
                      {summary.surfaces_murs_m2 && <small className="th-muted"> · {formatArea(summary.surfaces_murs_m2[key])}</small>}
                    </dd>
                  </div>
                ))}
              </dl>
            )}
            <p className="th-muted">
              Surfaces de murs brutes (côtés × hauteur intérieure), baies non déduites. Planchers et ponts thermiques : lot M2.
            </p>
            <Alerts messages={summary.alertes} />
          </section>
        )}

        {level && sheet && (
          <section>
            <h2>Calques et aimantation</h2>
            <label className="th-check">
              <input type="checkbox" checked={layers.below} disabled={!below} onChange={(event) => setLayers({ ...layers, below: event.target.checked })} />
              Niveau du dessous en calque{below ? ` (${below.nom})` : ""}
              {below && (!below.calage || !level.calage) && <small className="th-muted"> · calez les deux niveaux</small>}
            </label>
            <label className="th-check">
              <input type="checkbox" checked={layers.above} disabled={!above} onChange={(event) => setLayers({ ...layers, above: event.target.checked })} />
              Niveau du dessus en calque{above ? ` (${above.nom})` : ""}
              {above && (!above.calage || !level.calage) && <small className="th-muted"> · calez les deux niveaux</small>}
            </label>
            <label className="th-check">
              <input type="checkbox" checked={layers.snap} onChange={(event) => setLayers({ ...layers, snap: event.target.checked })} />
              Aimanter sur les traits du plan
            </label>
            <label className="th-check">
              <input type="checkbox" checked={layers.traits} onChange={(event) => setLayers({ ...layers, traits: event.target.checked })} />
              Afficher les traits d'aimantation
            </label>
            {traits.data && (
              <label className="th-field">
                <span>Épaisseur minimale des traits</span>
                <select value={seuil ?? ""} onChange={(event) => setSeuil(event.target.value === "" ? null : Number(event.target.value))}>
                  <option value="">Automatique ({decimalText(traits.data.seuil_propose)} pt)</option>
                  {traits.data.classes.map((classe) => (
                    <option key={classe.largeur} value={classe.largeur}>
                      {decimalText(classe.largeur)} pt · {classe.nombre} traits
                    </option>
                  ))}
                </select>
              </label>
            )}
            {traits.data && (
              <p className="th-muted">
                {traits.data.segments.length} traits retenus sur {traits.data.nombre_total}
                {traits.data.tronque && " (les plus longs seulement)"}.
              </p>
            )}
            {traits.error && <p className="th-alert th-alert--warn">Traits du plan illisibles : tracé sans aimantation ({traits.error.message}).</p>}
          </section>
        )}
      </aside>
    </div>
  );
}
