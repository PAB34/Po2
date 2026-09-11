import { useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "../../providers/AuthProvider";
import { thermiqueApi, type ProjectDetail, type Sheet, type SheetChanges, type ThermiqueDocument, type UploadResult } from "../api";
import { NATURES, NATURE_LABELS, NATURE_ROLES, STATUS_LABELS } from "../natures";
import { allSheets, formatSize, projectQueryKey, projectsQueryKey, replaceSheet } from "../projectCache";
import { COMMON_SCALES, formatScale, parseDecimal } from "../scale";
import { ProjectTabs } from "./ProjectLibraryPage";

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
        <strong>Déposez ici vos plans, coupes et façades</strong> ou{" "}
        <button type="button" className="th-link" disabled={disabled} onClick={() => inputRef.current?.click()}>
          choisissez des fichiers
        </button>
      </p>
      <p className="th-muted">PDF (une planche par page). Les fichiers DXF et DWG arrivent à l'étape 2.</p>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.dxf,.dwg,application/pdf"
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

function LevelInput({ sheet, onSave }: { sheet: Sheet; onSave: (value: string | null) => void }) {
  const [value, setValue] = useState(sheet.level_label ?? "");
  const commit = () => {
    const next = value.trim() || null;
    if (next !== sheet.level_label) {
      onSave(next);
    }
  };
  return (
    <input
      className="th-input-sm"
      value={value}
      placeholder="Ex. Niveau 0"
      maxLength={80}
      onChange={(event) => setValue(event.target.value)}
      onBlur={commit}
      onKeyDown={(event) => {
        if (event.key === "Enter") {
          event.currentTarget.blur();
        }
      }}
    />
  );
}

export function ProjectPage() {
  const { token } = useAuth();
  const projectId = Number(useParams().projectId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const queryKey = projectQueryKey(projectId);
  const [report, setReport] = useState<UploadResult | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [bulkScale, setBulkScale] = useState("100");

  const { data: project, isLoading, error } = useQuery({
    queryKey,
    queryFn: () => thermiqueApi.getProject(token!, projectId),
    enabled: Boolean(token) && Number.isFinite(projectId),
  });

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

  if (isLoading) {
    return <p className="th-muted">Chargement du projet…</p>;
  }
  if (error || !project) {
    return <p className="th-alert th-alert--error">{error?.message ?? "Projet introuvable."}</p>;
  }

  const sheets = allSheets(project);
  const pendingSuggestions = sheets.filter((sheet) => sheet.nature === null && sheet.nature_suggested !== null);
  const withoutScale = sheets.filter((sheet) => sheet.scale_denominator === null);
  const readyCount = sheets.filter((sheet) => sheet.status === "prete").length;

  const upload = (files: File[]) =>
    run(`Import de ${files.length} fichier${files.length > 1 ? "s" : ""}…`, async () => {
      const result = await thermiqueApi.uploadDocuments(token!, projectId, files);
      queryClient.setQueryData(queryKey, result.project);
      setReport(result);
    });

  const acceptSuggestions = () =>
    run("Classement des planches…", async () => {
      for (const sheet of pendingSuggestions) {
        await patchSheet(sheet, { nature: sheet.nature_suggested });
      }
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
      <div className="th-page-head">
        <div>
          <p className="po2-eyebrow">
            <Link to="/">Projets</Link>
          </p>
          <h1>{project.name}</h1>
          {project.description && <p className="th-muted">{project.description}</p>}
        </div>
        <button type="button" className="po2-button po2-button--danger" onClick={removeProject} disabled={Boolean(busy)}>
          Supprimer le projet
        </button>
      </div>
      <ProjectTabs projectId={project.id} />

      <section className="po2-card th-section">
        <div className="po2-card__body">
          <UploadZone disabled={Boolean(busy)} onFiles={(files) => void upload(files)} />
          {busy && <p className="th-alert">{busy}</p>}
          {actionError && <p className="th-alert th-alert--error">{actionError}</p>}
          {report && (report.imported.length > 0 || report.errors.length > 0) && (
            <div className="th-report">
              {report.imported.length > 0 && (
                <p className="th-alert th-alert--ok">
                  {report.imported.length} fichier{report.imported.length > 1 ? "s importés" : " importé"} : {report.imported.join(", ")}
                </p>
              )}
              {report.errors.map((item) => (
                <p key={item.filename} className="th-alert th-alert--error">
                  {item.filename} : {item.message}
                </p>
              ))}
            </div>
          )}
        </div>
      </section>

      {sheets.length > 0 && (
        <section className="po2-card th-section">
          <div className="po2-card__header">
            <div>
              <h2>Planches</h2>
              <p className="th-muted">
                {sheets.length} planche{sheets.length > 1 ? "s" : ""} · {readyCount} prête{readyCount > 1 ? "s" : ""} pour le métré
              </p>
            </div>
            <div className="th-actions">
              {pendingSuggestions.length > 0 && (
                <button type="button" className="po2-button po2-button--secondary" onClick={() => void acceptSuggestions()} disabled={Boolean(busy)}>
                  Accepter les {pendingSuggestions.length} types suggérés
                </button>
              )}
              {withoutScale.length > 0 && (
                <span className="th-inline">
                  <label className="th-inline">
                    Échelle 1/
                    <input
                      className="th-input-xs"
                      list="th-scales"
                      value={bulkScale}
                      onChange={(event) => setBulkScale(event.target.value)}
                    />
                  </label>
                  <button type="button" className="po2-button po2-button--ghost" onClick={applyBulkScale} disabled={Boolean(busy)}>
                    Appliquer aux {withoutScale.length} planches sans échelle
                  </button>
                </span>
              )}
              <datalist id="th-scales">
                {COMMON_SCALES.map((scale) => (
                  <option key={scale} value={scale} />
                ))}
              </datalist>
            </div>
          </div>
          <div className="th-table-wrap">
            <table className="th-table">
              <thead>
                <tr>
                  <th>Planche</th>
                  <th>Type</th>
                  <th>Niveau</th>
                  <th>Échelle</th>
                  <th>État</th>
                  <th aria-label="Ouvrir" />
                </tr>
              </thead>
              <tbody>
                {sheets.map((sheet) => (
                  <tr key={sheet.id}>
                    <td>
                      <strong>{sheet.label}</strong>
                    </td>
                    <td>
                      <select
                        value={sheet.nature ?? ""}
                        onChange={(event) =>
                          void run("Enregistrement…", () =>
                            patchSheet(sheet, { nature: (event.target.value || null) as Sheet["nature"] }),
                          )
                        }
                      >
                        <option value="">À classer</option>
                        {NATURES.map((nature) => (
                          <option key={nature} value={nature}>
                            {NATURE_LABELS[nature]}
                          </option>
                        ))}
                      </select>
                      {sheet.nature === null && sheet.nature_suggested && (
                        <button
                          type="button"
                          className="th-chip"
                          onClick={() => void run("Enregistrement…", () => patchSheet(sheet, { nature: sheet.nature_suggested }))}
                        >
                          Suggestion : {NATURE_LABELS[sheet.nature_suggested]} (accepter)
                        </button>
                      )}
                    </td>
                    <td>
                      <LevelInput
                        key={`${sheet.id}-${sheet.level_label ?? ""}`}
                        sheet={sheet}
                        onSave={(value) => void run("Enregistrement…", () => patchSheet(sheet, { level_label: value }))}
                      />
                    </td>
                    <td>
                      {formatScale(sheet.scale_denominator)}
                      {sheet.scale_source === "cote" && <small className="th-muted"> (cote)</small>}
                    </td>
                    <td>
                      <span className={`th-status th-status--${sheet.status}`}>{STATUS_LABELS[sheet.status]}</span>
                    </td>
                    <td>
                      <Link className="po2-button po2-button--ghost" to={`/projets/${project.id}/planches/${sheet.id}`}>
                        Ouvrir
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <div className="th-columns">
        <section className="po2-card th-section">
          <div className="po2-card__header">
            <h2>À quoi sert chaque type de planche</h2>
          </div>
          <div className="po2-card__body">
            <ul className="th-guide">
              {NATURES.map((nature) => (
                <li key={nature}>
                  <strong>{NATURE_LABELS[nature]}</strong>
                  <span className="th-muted">{NATURE_ROLES[nature]}</span>
                  <span className="th-count">{sheets.filter((sheet) => sheet.nature === nature).length}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {project.documents.length > 0 && (
          <section className="po2-card th-section">
            <div className="po2-card__header">
              <h2>Fichiers importés</h2>
            </div>
            <div className="po2-card__body">
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
            </div>
          </section>
        )}
      </div>
    </>
  );
}
