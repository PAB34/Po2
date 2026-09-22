import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { useAuth } from "../../providers/AuthProvider";
import { thermiqueApi, type PdfPoint, type Sheet } from "../api";
import { TileSheetViewer, type ViewerTool, type ViewerView } from "../components/TileSheetViewer";
import { STATUS_LABELS } from "../natures";
import { allSheets, projectQueryKey, projectsQueryKey } from "../projectCache";
import { DocumentsPanel } from "./DocumentsPanel";
import { InfoPanel } from "./InfoPanel";
import { groupSheets, referenceSheet, sheetTitle } from "./levels";
import { LibraryPanel } from "./LibraryPanel";
import { SheetPanel, sheetSegments } from "./SheetPanel";

type Panel = "planche" | "documents" | "bibliotheque" | "infos";

const PANELS: { id: Panel; label: string }[] = [
  { id: "planche", label: "Planche" },
  { id: "documents", label: "Documents" },
  { id: "bibliotheque", label: "Bibliothèque" },
  { id: "infos", label: "Infos" },
];

// Les adresses de tuiles signées valent 12 h : on redemande la fiche avant.
const RASTER_STALE_MS = 6 * 3600 * 1000;

// Plan de référence choisi par le thermicien : gardé dans ce navigateur en attendant son enregistrement côté
// serveur avec l'étude du niveau (lot E2).
const referenceKey = (projectId: number) => `thermique.reference.${projectId}`;

function readReference(projectId: number): number | null {
  try {
    const value = window.localStorage.getItem(referenceKey(projectId));
    return value ? Number(value) : null;
  } catch {
    return null;
  }
}

function writeReference(projectId: number, sheetId: number) {
  try {
    window.localStorage.setItem(referenceKey(projectId), String(sheetId));
  } catch {
    // stockage indisponible : le choix vaut pour la session en cours
  }
}

function SheetMenu({ label, sheets, currentId, onPick }: { label: string; sheets: Sheet[]; currentId: number | null; onPick: (id: number) => void }) {
  if (sheets.length === 0) {
    return null;
  }
  const current = sheets.find((sheet) => sheet.id === currentId);
  return (
    <select
      className={current ? "th-ws__menu is-active" : "th-ws__menu"}
      aria-label={label}
      value={current ? current.id : ""}
      onChange={(event) => event.target.value && onPick(Number(event.target.value))}
    >
      <option value="">
        {label} ({sheets.length})
      </option>
      {sheets.map((sheet) => (
        <option key={sheet.id} value={sheet.id}>
          {sheetTitle(sheet)}
        </option>
      ))}
    </select>
  );
}

// Espace de travail du thermicien (D47) : un projet, ses plans, sa bibliothèque et ses infos, sans quitter l'écran.
export function WorkspacePage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const projectId = Number(useParams().projectId);
  const [searchParams, setSearchParams] = useSearchParams();
  const [referenceId, setReferenceId] = useState<number | null>(() => readReference(projectId));
  const [tool, setTool] = useState<ViewerTool>("pan");
  const [points, setPoints] = useState<PdfPoint[]>([]);
  const views = useRef(new Map<string, ViewerView>());

  const { data: project, error } = useQuery({
    queryKey: projectQueryKey(projectId),
    queryFn: () => thermiqueApi.getProject(token!, projectId),
    enabled: Boolean(token) && Number.isFinite(projectId),
  });
  const { data: projects } = useQuery({
    queryKey: projectsQueryKey,
    queryFn: () => thermiqueApi.listProjects(token!),
    enabled: Boolean(token),
  });

  useEffect(() => setReferenceId(readReference(projectId)), [projectId]);

  const sheets = project ? allSheets(project) : [];
  const groups = groupSheets(sheets);
  const reference = referenceSheet(sheets, referenceId);
  const requestedId = Number(searchParams.get("planche")) || null;
  const sheet = sheets.find((item) => item.id === requestedId) ?? reference;
  const panel = (PANELS.find((item) => item.id === searchParams.get("panneau"))?.id ?? (sheets.length ? "planche" : "documents")) as Panel;

  const setParams = useCallback(
    (changes: { planche?: number; panneau?: Panel }) => {
      const next = new URLSearchParams(searchParams);
      if (changes.planche !== undefined) {
        next.set("planche", String(changes.planche));
      }
      if (changes.panneau !== undefined) {
        next.set("panneau", changes.panneau);
      }
      setSearchParams(next);
    },
    [searchParams, setSearchParams],
  );

  const sheetId = sheet?.id ?? null;
  useEffect(() => {
    setPoints([]);
  }, [sheetId, tool]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setPoints([]);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const rotation = sheet?.rotation_deg ?? 0;
  const raster = useQuery({
    queryKey: ["thermique", "raster", sheetId, rotation],
    queryFn: () => thermiqueApi.getRaster(token!, sheetId!, rotation),
    enabled: Boolean(token && sheetId),
    staleTime: RASTER_STALE_MS,
  });
  const viewKey = `${sheetId}|${rotation}`;

  if (error) {
    return <p className="th-alert th-alert--error th-main">{error.message}</p>;
  }
  if (!project || !token) {
    return <p className="th-muted th-main">Chargement du projet…</p>;
  }

  const makeReference = (id: number) => {
    writeReference(project.id, id);
    setReferenceId(id);
  };
  const levelTitle = sheet ? sheetTitle(sheet) : "";

  return (
    <div className="th-ws">
      <div className="th-ws__bar">
        <select
          className="th-ws__project"
          aria-label="Projet"
          value={project.id}
          onChange={(event) => navigate(`/projets/${event.target.value}`)}
        >
          {(projects ?? [project]).map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
        <nav className="th-ws__levels" aria-label="Niveaux">
          {groups.levels.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-pressed={item.id === sheetId}
              className={item.id === sheetId ? "is-active" : undefined}
              onClick={() => setParams({ planche: item.id })}
              title={item.label}
            >
              {sheetTitle(item)}
              {item.id === reference?.id && <span className="th-ws__ref" aria-label="plan de référence"> ★</span>}
            </button>
          ))}
          {groups.levels.length === 0 && sheets.length > 0 && <span className="th-muted">Aucune planche classée en plan</span>}
        </nav>
        <SheetMenu label="Coupes" sheets={groups.sections} currentId={sheetId} onPick={(id) => setParams({ planche: id })} />
        <SheetMenu label="Façades" sheets={groups.elevations} currentId={sheetId} onPick={(id) => setParams({ planche: id })} />
        <SheetMenu label="Autres" sheets={groups.others} currentId={sheetId} onPick={(id) => setParams({ planche: id })} />
        <div className="th-ws__tabs" role="tablist" aria-label="Panneau">
          {PANELS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={panel === item.id}
              className={panel === item.id ? "is-active" : undefined}
              onClick={() => setParams({ panneau: item.id })}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div className={`th-ws__body th-ws__body--${panel}`}>
        <aside className="th-ws__side" aria-label="Étude du niveau">
          <section>
            <h2>Étude {levelTitle ? `· ${levelTitle}` : ""}</h2>
            <ol className="th-ws-steps">
              <li className={sheet?.status === "prete" ? "is-done" : "is-todo"}>
                <button type="button" onClick={() => setParams({ panneau: sheet ? "planche" : "documents" })}>
                  Planche classée et à l'échelle
                </button>
                <small>{sheet ? STATUS_LABELS[sheet.status] : "aucune planche"}</small>
              </li>
              <li className="is-later">
                <span>Locaux</span>
                <small>aucune étude importée</small>
              </li>
              <li className="is-later">
                <span>Enveloppe</span>
                <small>aucune étude importée</small>
              </li>
              <li className="is-later">
                <span>Pièce par pièce</span>
                <small>aucune étude importée</small>
              </li>
              <li className="is-later">
                <span>Hauteurs (coupes)</span>
                <small>à venir</small>
              </li>
            </ol>
          </section>
          <section>
            <h2>Locaux</h2>
            <p className="th-muted">Les locaux du niveau, chauffés d'abord, apparaîtront ici une fois l'étude importée.</p>
          </section>
        </aside>

        <div className="th-ws__plan">
          {!sheet ? (
            <div className="th-viewer th-viewer--empty">
              <p className="th-viewer__status">Déposez les plans du projet dans le panneau « Documents » pour commencer.</p>
            </div>
          ) : raster.data ? (
            <TileSheetViewer
              key={viewKey}
              manifest={raster.data}
              tileTemplate={thermiqueApi.apiUrl(raster.data.tile_url)}
              tool={tool}
              points={points}
              segments={sheetSegments(sheet, tool, points)}
              onAddPoint={(point) => setPoints((current) => (current.length >= 2 ? [point] : [...current, point]))}
              initialView={views.current.get(viewKey) ?? null}
              onViewChange={(view) => views.current.set(viewKey, view)}
            />
          ) : (
            <div className="th-viewer th-viewer--empty">
              <p className="th-viewer__status">
                {raster.error ? `Affichage impossible : ${raster.error.message}` : "Préparation de la planche… (quelques secondes à la première ouverture)"}
              </p>
            </div>
          )}
        </div>

        <aside className="th-panel th-ws__panel" aria-label={PANELS.find((item) => item.id === panel)?.label}>
          {panel === "planche" &&
            (sheet ? (
              <SheetPanel
                key={sheet.id}
                projectId={project.id}
                sheet={sheet}
                isReference={sheet.id === reference?.id}
                onMakeReference={() => makeReference(sheet.id)}
                tool={tool}
                onTool={setTool}
                points={points}
              />
            ) : (
              <p className="th-muted">Aucune planche : déposez les plans dans « Documents ».</p>
            ))}
          {panel === "documents" && (
            <DocumentsPanel project={project} currentSheetId={sheetId} onShowSheet={(id) => setParams({ planche: id })} />
          )}
          {panel === "bibliotheque" && <LibraryPanel projectId={project.id} />}
          {panel === "infos" && <InfoPanel key={project.id} project={project} referenceId={reference?.id ?? null} onReference={makeReference} />}
        </aside>
      </div>
    </div>
  );
}
