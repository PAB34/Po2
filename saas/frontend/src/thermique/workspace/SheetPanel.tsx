import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../../providers/AuthProvider";
import { thermiqueApi, type PdfPoint, type ProjectDetail, type Sheet, type SheetChanges, type Study } from "../api";
import type { ViewerSegment, ViewerTool } from "../components/TileSheetViewer";
import { NATURES, NATURE_LABELS, NATURE_ROLES, STATUS_LABELS } from "../natures";
import { projectQueryKey, projectsQueryKey, replaceSheet } from "../projectCache";
import { azimutEcran, degres, lectureDuNord } from "./nord";
import { studyQueryKey } from "./study";
import {
  COMMON_SCALES,
  PT_TO_MM,
  QUICK_SCALES,
  distancePt,
  formatMeters,
  formatScale,
  paperPtToRealM,
  parseDecimal,
} from "../scale";

export const TOOLS: { id: ViewerTool; label: string; help: string }[] = [
  { id: "pan", label: "Déplacer", help: "Glissez pour déplacer le plan, molette pour zoomer." },
  { id: "measure", label: "Mesurer", help: "Cliquez deux points : la longueur réelle s'affiche." },
  {
    id: "calibrate",
    label: "Vérifier l'échelle",
    help: "Cliquez les deux extrémités d'une cote imprimée, puis saisissez sa valeur.",
  },
  {
    id: "nord",
    label: "Nord",
    help: "Cliquez d'abord la base de la flèche, puis sa pointe, du côté du nord.",
  },
];

// Traits affichés sur le plan : la mesure en cours, ou la cote de référence de l'échelle.
export function sheetSegments(sheet: Sheet, tool: ViewerTool, points: PdfPoint[]): ViewerSegment[] {
  const segments: ViewerSegment[] = [];
  if (tool === "nord") {
    // La flèche du nord a son propre dessin : une longueur en mètres n'aurait aucun sens ici.
    return segments;
  }
  if (points.length === 2) {
    const lengthPt = distancePt(points[0], points[1]);
    const measured = sheet.scale_denominator ? paperPtToRealM(lengthPt, sheet.scale_denominator) : null;
    segments.push({
      p1: points[0],
      p2: points[1],
      tone: "measure",
      label: measured !== null ? formatMeters(measured) : `${Math.round(lengthPt * PT_TO_MM)} mm papier (échelle non définie)`,
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
  return segments;
}

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
        aria-label="Dénominateur de l'échelle"
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

type Props = {
  projectId: number;
  sheet: Sheet;
  isReference: boolean;
  onMakeReference: () => void;
  tool: ViewerTool;
  onTool: (tool: ViewerTool) => void;
  points: PdfPoint[];
  study: Study | null | undefined;
  onStudyImported: (study: Study) => void;
  /** Matrice du rendu de la planche : sert à lire le nord dans le repère affiché. */
  transform: number[] | null;
};

// Panneau « Planche » : réglages de la planche affichée (type, niveau, orientation, échelle) et outils de mesure.
export function SheetPanel({
  projectId,
  sheet,
  isReference,
  onMakeReference,
  tool,
  onTool,
  points,
  study,
  onStudyImported,
  transform,
}: Props) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [realLength, setRealLength] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [nordPartout, setNordPartout] = useState(true);

  async function importStudy(file: File) {
    const replace = study !== null && study !== undefined;
    if (replace && !window.confirm("Une étude existe déjà sur cette planche. La remplacer en conservant sa version précédente ?")) {
      return;
    }
    setBusy(true);
    setActionError(null);
    try {
      onStudyImported(await thermiqueApi.importStudy(token!, sheet.id, file, replace));
    } catch (actionFailure) {
      setActionError(actionFailure instanceof Error ? actionFailure.message : "Import de l'étude impossible.");
    } finally {
      setBusy(false);
    }
  }

  async function perform(action: () => Promise<Sheet>) {
    setBusy(true);
    setActionError(null);
    try {
      const updated = await action();
      queryClient.setQueryData<ProjectDetail>(projectQueryKey(projectId), (current) =>
        current ? replaceSheet(current, updated) : current,
      );
      void queryClient.invalidateQueries({ queryKey: projectsQueryKey });
    } catch (actionFailure) {
      setActionError(actionFailure instanceof Error ? actionFailure.message : "Action impossible.");
    } finally {
      setBusy(false);
    }
  }

  const save = (changes: SheetChanges) => perform(() => thermiqueApi.updateSheet(token!, sheet.id, changes));

  const calibrate = (apply: boolean) => {
    const real = parseDecimal(realLength);
    if (!real || points.length < 2) {
      setActionError("Cliquez deux points puis saisissez la longueur réelle de la cote.");
      return;
    }
    void perform(() => thermiqueApi.calibrateSheet(token!, sheet.id, { p1: points[0], p2: points[1], real_length_m: real, apply }));
  };

  const poserNord = async () => {
    if (points.length < 2) {
      setActionError("Cliquez la base de la flèche, puis sa pointe du côté du nord.");
      return;
    }
    setBusy(true);
    setActionError(null);
    try {
      // La réponse porte toutes les planches touchées : le nord vaut le plus souvent pour le projet.
      const planches = await thermiqueApi.setNorth(token!, sheet.id, {
        p1: points[0],
        p2: points[1],
        tout_le_projet: nordPartout,
      });
      queryClient.setQueryData<ProjectDetail>(projectQueryKey(projectId), (current) =>
        planches.reduce((projet, planche) => (projet ? replaceSheet(projet, planche) : projet), current),
      );
      // Les orientations de l'étude ont été recalculées côté serveur : on la redemande.
      void queryClient.invalidateQueries({ queryKey: studyQueryKey(sheet.id) });
      onTool("pan");
    } catch (actionFailure) {
      setActionError(actionFailure instanceof Error ? actionFailure.message : "Impossible de poser le nord.");
    } finally {
      setBusy(false);
    }
  };

  const azimutNord = sheet.nord && transform ? azimutEcran(sheet.nord.p1, sheet.nord.p2, transform) : null;
  const azimutTrace = points.length >= 2 && transform ? azimutEcran(points[0], points[1], transform) : null;

  const hasScale = sheet.scale_denominator !== null;
  const lengthPt = points.length === 2 ? distancePt(points[0], points[1]) : null;
  const paperMm = lengthPt !== null ? Math.round(lengthPt * PT_TO_MM) : null;
  const measuredM = lengthPt !== null && sheet.scale_denominator ? paperPtToRealM(lengthPt, sheet.scale_denominator) : null;
  const calibration = sheet.calibration;
  const scaleConfirmed = calibration?.standard_scale != null && calibration.standard_scale === sheet.scale_denominator;
  const scaleOff = calibration?.ecart_pct != null && Math.abs(calibration.ecart_pct) > 1;
  const roundableTo =
    calibration?.standard_scale != null && hasScale && calibration.standard_scale !== sheet.scale_denominator
      ? calibration.standard_scale
      : null;

  return (
    <>
      <div>
        <h2 className="th-panel__title">{sheet.label}</h2>
        <p className="th-muted">
          Feuille {Math.round(sheet.page_width_pt * PT_TO_MM)} × {Math.round(sheet.page_height_pt * PT_TO_MM)} mm ·{" "}
          <span className={`th-status th-status--${sheet.status}`}>{STATUS_LABELS[sheet.status]}</span>
        </p>
        {sheet.nature === "plan" &&
          (isReference ? (
            <p className="th-muted">Plan de référence du projet : il s'ouvre en premier.</p>
          ) : (
            <button type="button" className="th-chip" onClick={onMakeReference}>
              En faire le plan de référence
            </button>
          ))}
      </div>

      {sheet.nature === "plan" && (
        <section className="th-study-import">
          <h2>Étude du niveau</h2>
          {study ? (
            <p className="th-alert th-alert--ok">Étude importée · version {study.version_number} · {study.content.locaux.length} locaux</p>
          ) : (
            <p className="th-muted">Déposez le fichier unique <code>etude-&lt;niveau&gt;.json</code> produit sur le poste.</p>
          )}
          <label className="po2-button po2-button--primary">
            {study ? "Remplacer l'étude" : "Importer l'étude"}
            <input
              type="file"
              accept=".json,application/json"
              hidden
              disabled={busy || sheet.status !== "prete"}
              onChange={(event) => {
                const file = event.target.files?.[0];
                event.currentTarget.value = "";
                if (file) void importStudy(file);
              }}
            />
          </label>
          {sheet.status !== "prete" && <p className="th-muted">Classez la planche et définissez son échelle avant l'import.</p>}
        </section>
      )}

      <section>
        <h2>Outils</h2>
        <div className="th-segmented" role="group" aria-label="Outil">
          {TOOLS.map((item) => (
            <button key={item.id} type="button" className={tool === item.id ? "is-active" : undefined} onClick={() => onTool(item.id)}>
              {item.label}
            </button>
          ))}
        </div>
        <p className="th-muted">{TOOLS.find((item) => item.id === tool)?.help} Échap efface les points.</p>
        {tool === "measure" &&
          lengthPt !== null &&
          (measuredM !== null ? (
            <p className="th-result">{formatMeters(measuredM)}</p>
          ) : (
            <p className="th-alert th-alert--warn">
              {paperMm} mm mesurés <strong>sur le papier</strong> : l'échelle n'est pas définie.
            </p>
          ))}
        {tool === "nord" && (
          <div className="th-form th-north-form">
            <ol className="th-steps">
              <li>Repérez la flèche du nord imprimée sur le plan, ou son orientation connue.</li>
              <li>
                Cliquez <strong>la base</strong> de la flèche, puis <strong>sa pointe, du côté du nord</strong>.
              </li>
            </ol>
            {azimutTrace !== null ? (
              <p className="th-alert th-alert--ok">
                Flèche tracée : le nord pointe <strong>{lectureDuNord(azimutTrace)}</strong> ({degres(azimutTrace)}).
                <br />
                Vérifiez le « N » sur le plan avant de valider.
              </p>
            ) : (
              <p className="th-muted">
                {points.length === 1 ? "Cliquez maintenant la pointe, du côté du nord." : "Aucun point posé."}
              </p>
            )}
            <label className="th-inline">
              <input type="checkbox" checked={nordPartout} onChange={(event) => setNordPartout(event.target.checked)} />
              Appliquer à tous les plans du projet
            </label>
            <p className="th-muted">
              Un bâtiment n'a qu'un nord. Décochez si ce plan est dessiné dans un autre sens que les autres.
            </p>
            <button
              type="button"
              className="po2-button po2-button--primary"
              disabled={busy || points.length < 2}
              onClick={() => void poserNord()}
            >
              {busy ? "Recalcul des orientations…" : "Valider le nord"}
            </button>
            <p className="th-muted">Les orientations des parois sont recalculées dans la foulée (quelques secondes).</p>
          </div>
        )}
        {tool === "calibrate" && (
          <div className="th-form">
            {!hasScale && <p className="th-muted">Sans échelle déclarée, la cote fixera l'échelle de la planche.</p>}
            <label className="th-field">
              <span>Valeur de la cote (m)</span>
              <input
                inputMode="decimal"
                value={realLength}
                placeholder="Ex. 3,04"
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
              <div className={scaleOff ? "th-alert th-alert--warn" : "th-alert th-alert--ok"}>
                Cote {formatMeters(calibration.real_length_m)}
                {calibration.measured_m !== null && <> · mesurée {formatMeters(calibration.measured_m)} à {formatScale(sheet.scale_denominator)}</>}
                {calibration.ecart_pct !== null && <> · écart {calibration.ecart_pct.toLocaleString("fr-FR")} %</>}
                <br />
                {scaleConfirmed ? (
                  <strong>Échelle {formatScale(sheet.scale_denominator)} confirmée par la cote.</strong>
                ) : (
                  <>
                    Échelle déduite de la cote : {formatScale(calibration.denominator_from_cote)}
                    {calibration.standard_scale !== null && <>, soit {formatScale(calibration.standard_scale)} (échelle usuelle)</>}.
                  </>
                )}
                {scaleOff && (
                  <>
                    <br />
                    L'échelle déclarée ne correspond pas à la cote : vérifiez les points ou appliquez l'échelle de la cote.
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </section>

      <section>
        <h2>Type de planche</h2>
        <select value={sheet.nature ?? ""} disabled={busy} onChange={(event) => void save({ nature: (event.target.value || null) as Sheet["nature"] })}>
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
        {sheet.nature && <p className="th-muted">Sert pour : {NATURE_ROLES[sheet.nature]}.</p>}
      </section>

      <section>
        <h2>Niveau</h2>
        <input
          key={`${sheet.id}-${sheet.level_label ?? ""}`}
          defaultValue={sheet.level_label ?? ""}
          placeholder="Ex. RDC, R+1, Toiture"
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
        <h2>Échelle</h2>
        {!hasScale && (
          <div className="th-alert th-alert--warn">
            <strong>Échelle non définie</strong> : choisissez celle du cartouche.
            <div className="th-inline" style={{ marginTop: "0.45rem" }}>
              {QUICK_SCALES.map((scale) => (
                <button key={scale} type="button" className="po2-button po2-button--ghost" disabled={busy} onClick={() => void save({ scale_denominator: scale })}>
                  1/{scale}
                </button>
              ))}
            </div>
          </div>
        )}
        <ScaleInput key={`${sheet.id}-${sheet.scale_denominator ?? ""}`} sheet={sheet} onSave={(denominator) => void save({ scale_denominator: denominator })} />
        <p className="th-muted">
          {hasScale
            ? `${formatScale(sheet.scale_denominator)}, ${sheet.scale_source === "cote" ? "déduite d'une cote" : "déclarée"}.`
            : "Ou saisissez une autre échelle, puis vérifiez-la avec une cote."}
        </p>
        {roundableTo !== null && (
          <button type="button" className="th-chip" disabled={busy} onClick={() => void save({ scale_denominator: roundableTo })}>
            Ramener à {formatScale(roundableTo)}, l'échelle usuelle confirmée par la cote
          </button>
        )}
      </section>

      <section>
        <h2>Nord</h2>
        {azimutNord !== null ? (
          <>
            <p className="th-result">
              Nord <strong>{lectureDuNord(azimutNord)}</strong> ({degres(azimutNord)})
            </p>
            <p className="th-muted">
              Les orientations des parois en découlent. La flèche est dessinée sur le plan : vérifiez que son
              « N » tombe bien du côté du nord.
            </p>
          </>
        ) : (
          <div className="th-alert th-alert--warn">
            <strong>Nord non défini</strong> : les orientations des parois restent « à caler », alors qu'elles
            entrent dans le calcul des déperditions.
          </div>
        )}
        <button type="button" className="po2-button po2-button--ghost" onClick={() => onTool("nord")}>
          {azimutNord !== null ? "Redéfinir le nord" : "Définir le nord"}
        </button>
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
      {actionError && <p className="th-alert th-alert--error">{actionError}</p>}
    </>
  );
}
