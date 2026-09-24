import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../../providers/AuthProvider";
import { thermiqueApi, type ProjectDetail, type Sheet, type SheetChanges, type ThermiqueDocument, type UploadResult } from "../api";
import { NATURES, NATURE_LABELS, STATUS_LABELS } from "../natures";
import { allSheets, formatSize, projectQueryKey, projectsQueryKey, replaceSheet } from "../projectCache";
import { COMMON_SCALES, formatScale, parseDecimal } from "../scale";
import { AnalysisQueue } from "./AnalysisQueue";

function UploadZone({ disabled, onFiles }: { disabled: boolean; onFiles: (files: File[]) => void }) {
  const [isOver, setIsOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  return (
    <div
      className={isOver ? "th-drop is-over" : "th-drop"}
      onDragOver={(event) => {
        event.preventDefault();
        setIsOver(true);
      }}
      onDragLeave={() => setIsOver(false)}
      onDrop={(event) => {
        event.preventDefault();
        setIsOver(false);
        const files = Array.from(event.dataTransfer.files);
        if (files.length && !disabled) {
          onFiles(files);
        }
      }}
    >
      <p>
        <strong>Déposez vos plans, coupes et façades</strong> ou{" "}
        <button type="button" className="th-link" disabled={disabled} onClick={() => inputRef.current?.click()}>
          choisissez des fichiers
        </button>
      </p>
      <p className="th-muted">PDF, une planche par page.</p>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,application/pdf"
        hidden
        onChange={(event) => {
          const files = Array.from(event.target.files ?? []);
          event.target.value = "";
          if (files.length) {
            onFiles(files);
          }
        }}
      />
    </div>
  );
}

type Props = {
  project: ProjectDetail;
  currentSheetId: number | null;
  onShowSheet: (sheetId: number) => void;
};

// Panneau « Documents et planches » : dépôt des PDF, classement des planches (type, niveau, échelle), fichiers.
export function DocumentsPanel({ project, currentSheetId, onShowSheet }: Props) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const queryKey = projectQueryKey(project.id);
  const [report, setReport] = useState<UploadResult | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [bulkScale, setBulkScale] = useState("100");

  async function run(label: string, action: () => Promise<void>) {
    setBusy(label);
    setActionError(null);
    try {
      await action();
    } catch (actionFailure) {
      setActionError(actionFailure instanceof Error ? actionFailure.message : "Action impossible.");
    } finally {
      setBusy(null);
      void queryClient.invalidateQueries({ queryKey: projectsQueryKey });
    }
  }

  async function patchSheet(sheet: Sheet, changes: SheetChanges) {
    const updated = await thermiqueApi.updateSheet(token!, sheet.id, changes);
    queryClient.setQueryData<ProjectDetail>(queryKey, (current) => (current ? replaceSheet(current, updated) : current));
  }

  const sheets = allSheets(project);
  const pendingSuggestions = sheets.filter((sheet) => sheet.nature === null && sheet.nature_suggested !== null);
  const withoutScale = sheets.filter((sheet) => sheet.scale_denominator === null);

  const upload = (files: File[]) =>
    run(`Import de ${files.length} fichier${files.length > 1 ? "s" : ""}…`, async () => {
      const result = await thermiqueApi.uploadDocuments(token!, project.id, files);
      queryClient.setQueryData(queryKey, result.project);
      setReport(result);
    });

  const applyBulkScale = () => {
    const denominator = parseDecimal(bulkScale);
    if (!denominator) {
      setActionError("Échelle invalide.");
      return;
    }
    void run("Application de l'échelle…", async () => {
      for (const sheet of withoutScale) {
        await patchSheet(sheet, { scale_denominator: denominator });
      }
    });
  };

  const removeDocument = (document: ThermiqueDocument) => {
    if (!window.confirm(`Supprimer « ${document.original_filename} » et ses ${document.page_count} planche(s) ?`)) {
      return;
    }
    void run("Suppression…", async () => {
      await thermiqueApi.deleteDocument(token!, document.id);
      await queryClient.invalidateQueries({ queryKey });
    });
  };

  const removeProject = () => {
    if (!window.confirm(`Supprimer le projet « ${project.name} » et tous ses fichiers ?`)) {
      return;
    }
    void run("Suppression du projet…", async () => {
      await thermiqueApi.deleteProject(token!, project.id);
      queryClient.removeQueries({ queryKey });
      navigate("/");
    });
  };

  return (
    <>
      <UploadZone disabled={Boolean(busy)} onFiles={(files) => void upload(files)} />
      {busy && <p className="th-alert">{busy}</p>}
      {actionError && <p className="th-alert th-alert--error">{actionError}</p>}
      {report?.imported.length ? (
        <p className="th-alert th-alert--ok">
          {report.imported.length} fichier{report.imported.length > 1 ? "s importés" : " importé"} : {report.imported.join(", ")}
        </p>
      ) : null}
      {report?.errors.map((item) => (
        <p key={item.filename} className="th-alert th-alert--error">
          {item.filename} : {item.message}
        </p>
      ))}

      {sheets.length > 0 && <AnalysisQueue projectId={project.id} />}

      {sheets.length > 0 && (
        <section>
          <h2>Planches ({sheets.length})</h2>
          <div className="th-inline">
            {pendingSuggestions.length > 0 && (
              <button
                type="button"
                className="po2-button po2-button--secondary"
                disabled={Boolean(busy)}
                onClick={() =>
                  void run("Classement des planches…", async () => {
                    for (const sheet of pendingSuggestions) {
                      await patchSheet(sheet, { nature: sheet.nature_suggested });
                    }
                  })
                }
              >
                Accepter les {pendingSuggestions.length} types suggérés
              </button>
            )}
            {withoutScale.length > 0 && (
              <>
                <label className="th-inline">
                  1/
                  <input className="th-input-xs" list="th-ws-scales" value={bulkScale} onChange={(event) => setBulkScale(event.target.value)} />
                </label>
                <button type="button" className="po2-button po2-button--ghost" onClick={applyBulkScale} disabled={Boolean(busy)}>
                  Échelle des {withoutScale.length} planches sans échelle
                </button>
                <datalist id="th-ws-scales">
                  {COMMON_SCALES.map((scale) => (
                    <option key={scale} value={scale} />
                  ))}
                </datalist>
              </>
            )}
          </div>
          <ul className="th-ws-sheets">
            {sheets.map((sheet) => (
              <li key={sheet.id} className={sheet.id === currentSheetId ? "is-current" : undefined}>
                <button type="button" className="th-ws-sheets__name" onClick={() => onShowSheet(sheet.id)} title="Afficher sur le plan">
                  {sheet.label}
                </button>
                <select
                  aria-label={`Type de ${sheet.label}`}
                  value={sheet.nature ?? ""}
                  onChange={(event) =>
                    void run("Enregistrement…", () => patchSheet(sheet, { nature: (event.target.value || null) as Sheet["nature"] }))
                  }
                >
                  <option value="">À classer</option>
                  {NATURES.map((nature) => (
                    <option key={nature} value={nature}>
                      {NATURE_LABELS[nature]}
                    </option>
                  ))}
                </select>
                <input
                  key={`${sheet.id}-${sheet.level_label ?? ""}`}
                  aria-label={`Niveau de ${sheet.label}`}
                  defaultValue={sheet.level_label ?? ""}
                  placeholder="Niveau"
                  maxLength={80}
                  onBlur={(event) => {
                    const value = event.target.value.trim() || null;
                    if (value !== sheet.level_label) {
                      void run("Enregistrement…", () => patchSheet(sheet, { level_label: value }));
                    }
                  }}
                />
                <span className="th-muted">{formatScale(sheet.scale_denominator)}</span>
                <span className={`th-status th-status--${sheet.status}`}>{STATUS_LABELS[sheet.status]}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {project.documents.length > 0 && (
        <section>
          <h2>Fichiers importés</h2>
          <ul className="th-files">
            {project.documents.map((document) => (
              <li key={document.id}>
                <span>
                  <strong>{document.original_filename}</strong>
                  <small className="th-muted">
                    {" "}
                    · {document.page_count} page{document.page_count > 1 ? "s" : ""} · {formatSize(document.size_bytes)}
                  </small>
                </span>
                <button type="button" className="th-link th-link--danger" onClick={() => removeDocument(document)} disabled={Boolean(busy)}>
                  Supprimer
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <h2>Projet</h2>
        <button type="button" className="po2-button po2-button--danger" onClick={removeProject} disabled={Boolean(busy)}>
          Supprimer le projet
        </button>
      </section>
    </>
  );
}
