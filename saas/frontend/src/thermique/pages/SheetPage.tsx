import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { useAuth } from "../../providers/AuthProvider";
import { thermiqueApi, type PdfPoint, type ProjectDetail, type Sheet, type SheetChanges } from "../api";
import { TileSheetViewer, type ViewerSegment, type ViewerTool } from "../components/TileSheetViewer";
import { NATURES, NATURE_LABELS, NATURE_ROLES, STATUS_LABELS } from "../natures";
import { allSheets, projectQueryKey, projectsQueryKey, replaceSheet } from "../projectCache";
import { COMMON_SCALES, PT_TO_MM, distancePt, formatMeters, formatScale, paperPtToRealM, parseDecimal } from "../scale";

const TOOLS: { id: ViewerTool; label: string; help: string }[] = [
  { id: "pan", label: "Déplacer", help: "Glissez pour déplacer le plan, molette pour zoomer." },
  { id: "measure", label: "Mesurer", help: "Cliquez deux points : la longueur réelle s'affiche." },
  {
    id: "calibrate",
    label: "Vérifier l'échelle",
    help: "Cliquez les deux extrémités d'une cote imprimée, puis saisissez sa valeur.",
  },
];

// Les adresses de tuiles signées valent 12 h : on redemande la fiche avant.
const RASTER_STALE_MS = 6 * 3600 * 1000;

function ScaleInput({ sheet, onSave }: { sheet: Sheet; onSave: (denominator: number) => void }) {
  const [value, setValue] = useState(sheet.scale_denominator ? String(sheet.scale_denominator).replace(".", ",") : "");
  const commit = () => {
    const denominator = parseDecimal(value);
    if (denominator && denominator !== sheet.scale_denominator) {
      onSave(denominator);
    }
  };
  return (
    <label className="th-inline">
      1/
      <input
        className="th-input-xs"
        list="th-sheet-scales"
        value={value}
        placeholder="100"
        onChange={(event) => setValue(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.currentTarget.blur();
          }
        }}
      />
      <datalist id="th-sheet-scales">
        {COMMON_SCALES.map((scale) => (
          <option key={scale} value={scale} />
        ))}
      </datalist>
    </label>
  );
}

export function SheetPage() {
  const { token } = useAuth();
  const params = useParams();
  const projectId = Number(params.projectId);
  const sheetId = Number(params.sheetId);
  const queryClient = useQueryClient();
  const queryKey = projectQueryKey(projectId);
  const [tool, setTool] = useState<ViewerTool>("pan");
  const [points, setPoints] = useState<PdfPoint[]>([]);
  const [realLength, setRealLength] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const { data: project, error } = useQuery({
    queryKey,
    queryFn: () => thermiqueApi.getProject(token!, projectId),
    enabled: Boolean(token) && Number.isFinite(projectId),
  });

  const knownSheet = project ? allSheets(project).find((item) => item.id === sheetId) : undefined;
  const rotation = knownSheet?.rotation_deg ?? 0;
  const raster = useQuery({
    queryKey: ["thermique", "raster", sheetId, rotation],
    queryFn: () => thermiqueApi.getRaster(token!, sheetId, rotation),
    enabled: Boolean(token && knownSheet),
    staleTime: RASTER_STALE_MS,
  });

  useEffect(() => {
    setPoints([]);
    setRealLength("");
    setActionError(null);
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

  if (error) {
    return <p className="th-alert th-alert--error th-main">{error.message}</p>;
  }
  if (!project || !token) {
    return <p className="th-muted th-main">Chargement de la planche…</p>;
  }

  const sheets = allSheets(project);
  const index = sheets.findIndex((item) => item.id === sheetId);
  const sheet = sheets[index];
  if (!sheet) {
    return <p className="th-alert th-alert--error th-main">Planche introuvable.</p>;
  }
  const previous = sheets[index - 1];
  const next = sheets[index + 1];

  async function perform(action: () => Promise<Sheet>) {
    setBusy(true);
    setActionError(null);
    try {
      const updated = await action();
      queryClient.setQueryData<ProjectDetail>(queryKey, (current) => (current ? replaceSheet(current, updated) : current));
      void queryClient.invalidateQueries({ queryKey: projectsQueryKey });
    } catch (actionFailure) {
      setActionError(actionFailure instanceof Error ? actionFailure.message : "Action impossible.");
    } finally {
      setBusy(false);
    }
  }

  const save = (changes: SheetChanges) => perform(() => thermiqueApi.updateSheet(token, sheet.id, changes));

  const calibrate = (apply: boolean) => {
    const real = parseDecimal(realLength);
    if (!real || points.length < 2) {
      setActionError("Cliquez deux points puis saisissez la longueur réelle de la cote.");
      return;
    }
    void perform(() =>
      thermiqueApi.calibrateSheet(token, sheet.id, { p1: points[0], p2: points[1], real_length_m: real, apply }),
    );
  };

  const lengthPt = points.length === 2 ? distancePt(points[0], points[1]) : null;
  const measuredM = lengthPt !== null && sheet.scale_denominator ? paperPtToRealM(lengthPt, sheet.scale_denominator) : null;
  const segments: ViewerSegment[] = [];
  if (points.length === 2 && lengthPt !== null) {
    segments.push({
      p1: points[0],
      p2: points[1],
      tone: "measure",
      label: measuredM !== null ? formatMeters(measuredM) : `${Math.round(lengthPt * PT_TO_MM)} mm sur le papier`,
    });
  }
  if (tool === "calibrate" && points.length === 0 && sheet.calibration) {
    segments.push({
      p1: sheet.calibration.p1,
      p2: sheet.calibration.p2,
      tone: "reference",
      label: `cote ${formatMeters(sheet.calibration.real_length_m)}`,
    });
  }
  const calibration = sheet.calibration;
  const paperWidthMm = Math.round(sheet.page_width_pt * PT_TO_MM);
  const paperHeightMm = Math.round(sheet.page_height_pt * PT_TO_MM);

  return (
    <div className="th-viewer-layout">
      {raster.data ? (
        <TileSheetViewer
          manifest={raster.data}
          tileTemplate={thermiqueApi.apiUrl(raster.data.tile_url)}
          tool={tool}
          points={points}
          segments={segments}
          onAddPoint={(point) => setPoints((current) => (current.length >= 2 ? [point] : [...current, point]))}
        />
      ) : (
        <div className="th-viewer th-viewer--empty">
          <p className="th-viewer__status">
            {raster.error
              ? `Affichage impossible : ${raster.error.message}`
              : "Préparation de la planche… (quelques secondes à la première ouverture)"}
          </p>
        </div>
      )}

      <aside className="th-panel">
        <div>
          <p className="po2-eyebrow">
            <Link to={`/projets/${project.id}`}>{project.name}</Link>
          </p>
          <h1 className="th-panel__title">{sheet.label}</h1>
          <p className="th-muted">
            Feuille {paperWidthMm} × {paperHeightMm} mm ·{" "}
            <span className={`th-status th-status--${sheet.status}`}>{STATUS_LABELS[sheet.status]}</span>
          </p>
        </div>

        <section>
          <h2>Type de planche</h2>
          <select
            value={sheet.nature ?? ""}
            disabled={busy}
            onChange={(event) => void save({ nature: (event.target.value || null) as Sheet["nature"] })}
          >
            <option value="">À classer</option>
            {NATURES.map((nature) => (
              <option key={nature} value={nature}>
                {NATURE_LABELS[nature]}
              </option>
            ))}
          </select>
          {sheet.nature === null && sheet.nature_suggested && (
            <button type="button" className="th-chip" onClick={() => void save({ nature: sheet.nature_suggested })}>
              Suggestion : {NATURE_LABELS[sheet.nature_suggested]} (accepter)
            </button>
          )}
          {sheet.nature && <p className="th-muted">Sert au métré pour : {NATURE_ROLES[sheet.nature]}.</p>}
        </section>

        <section>
          <h2>Niveau</h2>
          <input
            key={`${sheet.id}-${sheet.level_label ?? ""}`}
            defaultValue={sheet.level_label ?? ""}
            placeholder="Ex. Niveau 0"
            maxLength={80}
            onBlur={(event) => {
              const value = event.target.value.trim() || null;
              if (value !== sheet.level_label) {
                void save({ level_label: value });
              }
            }}
          />
        </section>

        <section>
          <h2>Orientation de la feuille</h2>
          <div className="th-inline">
            <button type="button" className="po2-button po2-button--ghost" disabled={busy} onClick={() => void save({ rotation_deg: (sheet.rotation_deg + 270) % 360 })}>
              Pivoter à gauche
            </button>
            <button type="button" className="po2-button po2-button--ghost" disabled={busy} onClick={() => void save({ rotation_deg: (sheet.rotation_deg + 90) % 360 })}>
              Pivoter à droite
            </button>
          </div>
          <p className="th-muted">Rotation d'affichage : {sheet.rotation_deg}°. Les mesures ne changent pas.</p>
        </section>

        <section>
          <h2>Échelle</h2>
          <ScaleInput key={`${sheet.id}-${sheet.scale_denominator ?? ""}`} sheet={sheet} onSave={(denominator) => void save({ scale_denominator: denominator })} />
          <p className="th-muted">
            {sheet.scale_denominator
              ? `${formatScale(sheet.scale_denominator)}, ${sheet.scale_source === "cote" ? "déduite d'une cote" : "déclarée"}.`
              : "Saisissez l'échelle du cartouche (ex. 100), puis vérifiez-la avec une cote."}
          </p>
        </section>

        <section>
          <h2>Outils</h2>
          <div className="th-segmented" role="group" aria-label="Outil">
            {TOOLS.map((item) => (
              <button key={item.id} type="button" className={tool === item.id ? "is-active" : undefined} onClick={() => setTool(item.id)}>
                {item.label}
              </button>
            ))}
          </div>
          <p className="th-muted">{TOOLS.find((item) => item.id === tool)?.help} Échap efface les points.</p>

          {tool === "measure" && lengthPt !== null && (
            <p className="th-result">
              {measuredM !== null ? formatMeters(measuredM) : "Définissez l'échelle pour lire une longueur en mètres."}
            </p>
          )}

          {tool === "calibrate" && (
            <div className="th-form">
              <label className="th-field">
                <span>Valeur de la cote (m)</span>
                <input
                  inputMode="decimal"
                  value={realLength}
                  placeholder="Ex. 31,82"
                  onChange={(event) => setRealLength(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      calibrate(false);
                    }
                  }}
                />
              </label>
              <div className="th-inline">
                <button type="button" className="po2-button po2-button--primary" disabled={busy || points.length < 2} onClick={() => calibrate(false)}>
                  Contrôler
                </button>
                <button type="button" className="po2-button po2-button--ghost" disabled={busy || points.length < 2} onClick={() => calibrate(true)}>
                  Appliquer l'échelle de la cote
                </button>
              </div>
              {calibration && (
                <div className={calibration.ecart_pct !== null && Math.abs(calibration.ecart_pct) > 1 ? "th-alert th-alert--warn" : "th-alert th-alert--ok"}>
                  Cote {formatMeters(calibration.real_length_m)}
                  {calibration.measured_m !== null && <> · mesurée {formatMeters(calibration.measured_m)} à {formatScale(sheet.scale_denominator)}</>}
                  {calibration.ecart_pct !== null && <> · écart {calibration.ecart_pct.toLocaleString("fr-FR")} %</>}
                  <br />
                  Échelle déduite de la cote : {formatScale(calibration.denominator_from_cote)}
                  {calibration.ecart_pct !== null && Math.abs(calibration.ecart_pct) > 1 && (
                    <>
                      <br />
                      L'échelle déclarée ne correspond pas à la cote : vérifiez les points cliqués ou appliquez l'échelle de la cote.
                    </>
                  )}
                </div>
              )}
            </div>
          )}
          {actionError && <p className="th-alert th-alert--error">{actionError}</p>}
        </section>

        <nav className="th-pager">
          {previous ? <Link to={`/projets/${project.id}/planches/${previous.id}`}>Planche précédente</Link> : <span />}
          <span className="th-muted">
            {index + 1} / {sheets.length}
          </span>
          {next ? <Link to={`/projets/${project.id}/planches/${next.id}`}>Planche suivante</Link> : <span />}
        </nav>
      </aside>
    </div>
  );
}
