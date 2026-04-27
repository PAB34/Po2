import { useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  analyzeBuildingImportFile,
  executeBuildingImportFile,
  previewBuildingImportFile,
  type BuildingImportAnalysis,
  type BuildingImportBuildingPreviewRow,
  type BuildingImportConfig,
  type BuildingImportLocalPreviewRow,
  type BuildingImportPreview,
  type BuildingImportResult,
} from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

const mappingSections = [
  {
    title: "Pilotage des lignes",
    fields: [
      { key: "row_type_column", label: "Colonne de typologie" },
    ],
  },
  {
    title: "Bâtiment",
    fields: [
      { key: "building_name", label: "Nom du bâtiment" },
      { key: "building_alias", label: "Alias / nom court bâtiment" },
      { key: "building_external_id", label: "Identifiant externe bâtiment" },
      { key: "address", label: "Adresse principale" },
      { key: "address_extra", label: "Complément d'adresse" },
      { key: "city_name", label: "Commune" },
      { key: "parcel_reference", label: "Référence parcellaire" },
      { key: "parcel_section", label: "Section cadastrale" },
      { key: "parcel_number", label: "Numéro de plan" },
      { key: "street_number", label: "Numéro de voirie" },
      { key: "street_repeat", label: "Indice de répétition" },
      { key: "street_type", label: "Nature de voie" },
      { key: "street_name", label: "Nom de voie" },
      { key: "parent_name", label: "Nom du parent / bâtiment" },
    ],
  },
  {
    title: "Local",
    fields: [
      { key: "local_name", label: "Nom du local" },
      { key: "local_external_id", label: "Identifiant externe local" },
      { key: "local_type", label: "Type de local" },
      { key: "local_level", label: "Niveau" },
      { key: "local_usage", label: "Usage" },
      { key: "local_occupancy_status", label: "Statut d'occupation" },
      { key: "local_comment", label: "Commentaire" },
      { key: "local_surface_m2", label: "Surface (m²)" },
    ],
  },
] as const;

function joinValues(values: string[]) {
  return values.join(", ");
}

function parseCommaSeparatedList(value: string): string[] {
  return value
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean);
}

function buildEmptyConfig(headerRowIndex = 0): BuildingImportConfig {
  return {
    sheet_name: null,
    header_row_index: headerRowIndex,
    row_type_column: null,
    building_row_types: [],
    local_row_types: [],
    mapping: {},
    skip_existing_buildings: true,
    create_missing_buildings_for_locals: true,
  };
}

export function BuildingImportPage() {
  const queryClient = useQueryClient();
  const { token } = useAuth();

  const [file, setFile] = useState<File | null>(null);
  const [selectedSheet, setSelectedSheet] = useState<string>("");
  const [headerRowIndex, setHeaderRowIndex] = useState(0);
  const [analysis, setAnalysis] = useState<BuildingImportAnalysis | null>(null);
  const [config, setConfig] = useState<BuildingImportConfig>(() => buildEmptyConfig(0));
  const [preview, setPreview] = useState<BuildingImportPreview | null>(null);
  const [result, setResult] = useState<BuildingImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const allColumns = analysis?.columns ?? [];
  const analysisOutdated = Boolean(analysis) && (selectedSheet !== analysis?.selected_sheet || headerRowIndex !== analysis?.header_row_index);
  const sampleHeaders = useMemo(() => {
    if (analysis?.sample_rows?.length) {
      return Object.keys(analysis.sample_rows[0] ?? {});
    }
    return allColumns;
  }, [analysis?.sample_rows, allColumns]);

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      if (!token) {
        throw new Error("Authentification requise.");
      }
      if (!file) {
        throw new Error("Sélectionne un fichier à analyser.");
      }
      return analyzeBuildingImportFile(token, file, {
        sheet_name: selectedSheet || undefined,
        header_row_index: headerRowIndex,
      });
    },
    onSuccess: (payload: BuildingImportAnalysis) => {
      setAnalysis(payload);
      setSelectedSheet(payload.selected_sheet);
      setHeaderRowIndex(payload.header_row_index);
      setConfig({
        ...payload.suggested_config,
        sheet_name: payload.selected_sheet,
        header_row_index: payload.header_row_index,
      });
      setPreview(null);
      setResult(null);
      setError(null);
      setSuccess("Analyse du fichier terminée. Vérifie le mapping avant de lancer l'import.");
    },
    onError: (mutationError: unknown) => {
      setError(mutationError instanceof Error ? mutationError.message : "Analyse du fichier impossible.");
      setSuccess(null);
    },
  });

  const previewMutation = useMutation({
    mutationFn: async () => {
      if (!token) {
        throw new Error("Authentification requise.");
      }
      if (!file) {
        throw new Error("Sélectionne un fichier avant de lancer la prévisualisation.");
      }
      return previewBuildingImportFile(token, file, config);
    },
    onSuccess: (payload: BuildingImportPreview) => {
      setPreview(payload);
      setResult(null);
      setError(null);
      setSuccess("Prévisualisation prête. Tu peux contrôler les objets qui seront créés.");
    },
    onError: (mutationError: unknown) => {
      setError(mutationError instanceof Error ? mutationError.message : "Prévisualisation impossible.");
      setSuccess(null);
    },
  });

  const executeMutation = useMutation({
    mutationFn: async () => {
      if (!token) {
        throw new Error("Authentification requise.");
      }
      if (!file) {
        throw new Error("Sélectionne un fichier avant de lancer l'import.");
      }
      return executeBuildingImportFile(token, file, config);
    },
    onSuccess: async (payload: BuildingImportResult) => {
      setResult(payload);
      setError(null);
      setSuccess(`Import terminé : ${payload.created_buildings} bâtiment(s) et ${payload.created_locals} local(aux) créés.`);
      await queryClient.invalidateQueries({ queryKey: ["buildings"] });
    },
    onError: (mutationError: unknown) => {
      setError(mutationError instanceof Error ? mutationError.message : "Import impossible.");
      setSuccess(null);
    },
  });

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] ?? null;
    setFile(nextFile);
    setAnalysis(null);
    setPreview(null);
    setResult(null);
    setError(null);
    setSuccess(null);
    setSelectedSheet("");
    setHeaderRowIndex(0);
    setConfig(buildEmptyConfig(0));
  }

  function updateMapping(fieldKey: string, value: string) {
    setConfig((current: BuildingImportConfig) => ({
      ...current,
      mapping: {
        ...current.mapping,
        [fieldKey]: value || null,
      },
    }));
  }

  function updateConfigField(fieldKey: "row_type_column" | "sheet_name", value: string) {
    setConfig((current: BuildingImportConfig) => ({
      ...current,
      [fieldKey]: value || null,
    }));
  }

  if (!token) {
    return (
      <section className="panel stack-lg">
        <div className="section-heading">
          <p className="eyebrow">Import patrimonial</p>
          <h2>Import d'inventaire externe</h2>
          <p>Connecte-toi pour analyser un fichier, mapper ses colonnes puis créer les bâtiments et locaux correspondants.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="panel stack-lg buildings-workspace-panel">
      <div className="panel-header">
        <div className="section-heading">
          <p className="eyebrow">Import patrimonial</p>
          <h2>Importer une base patrimoniale externe</h2>
          <p>
            Téléverse un fichier utilisateur, analyse ses feuilles et colonnes, mappe-le vers le format canonique Po2,
            puis crée automatiquement les bâtiments et locaux.
          </p>
        </div>
        <div className="header-badge">
          <strong>{preview?.building_rows_detected ?? analysis?.total_rows ?? 0}</strong>
          <span>lignes vues</span>
        </div>
      </div>

      {error ? <p className="error-text">{error}</p> : null}
      {success ? <p className="success-text">{success}</p> : null}

      <div className="import-layout">
        <aside className="import-sidebar">
          <div className="section-block">
            <div className="section-heading">
              <h3>1. Fichier source</h3>
              <p>Sélectionne le fichier puis lance une analyse pour récupérer les feuilles, les entêtes et un aperçu.</p>
            </div>
            <label className="field">
              <span>Fichier</span>
              <input type="file" accept=".csv,.xls,.xlsx,.xlsm" onChange={handleFileChange} />
            </label>
            <label className="field">
              <span>Feuille à lire</span>
              <select value={selectedSheet} onChange={(event) => setSelectedSheet(event.target.value)}>
                <option value="">Sélection automatique</option>
                {analysis?.available_sheets.map((sheetName: string) => (
                  <option key={sheetName} value={sheetName}>
                    {sheetName}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Ligne d'entête</span>
              <input
                type="number"
                min={0}
                value={headerRowIndex}
                onChange={(event) => setHeaderRowIndex(Number(event.target.value) || 0)}
              />
            </label>
            <div className="form-actions">
              <button type="button" onClick={() => analyzeMutation.mutate()} disabled={!file || analyzeMutation.isPending}>
                {analyzeMutation.isPending ? "Analyse..." : "Analyser le fichier"}
              </button>
            </div>
          </div>

          {analysis ? (
            <div className="section-block">
              <div className="section-heading">
                <h3>2. Paramètres d'import</h3>
                <p>Affinage du mapping et des règles de création avant prévisualisation.</p>
              </div>
              <label className="field">
                <span>Colonne de typologie</span>
                <select
                  value={config.row_type_column ?? ""}
                  onChange={(event) => updateConfigField("row_type_column", event.target.value)}
                >
                  <option value="">Aucune</option>
                  {allColumns.map((column: string) => (
                    <option key={column} value={column}>
                      {column}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Valeurs considérées comme bâtiments</span>
                <input
                  value={joinValues(config.building_row_types)}
                  onChange={(event: ChangeEvent<HTMLInputElement>) =>
                    setConfig((current: BuildingImportConfig) => ({
                      ...current,
                      building_row_types: parseCommaSeparatedList(event.target.value),
                    }))
                  }
                />
              </label>
              <label className="field">
                <span>Valeurs considérées comme locaux</span>
                <input
                  value={joinValues(config.local_row_types)}
                  onChange={(event: ChangeEvent<HTMLInputElement>) =>
                    setConfig((current: BuildingImportConfig) => ({
                      ...current,
                      local_row_types: parseCommaSeparatedList(event.target.value),
                    }))
                  }
                />
              </label>
              <label className="toggle-field">
                <input
                  type="checkbox"
                  checked={config.skip_existing_buildings}
                  onChange={(event: ChangeEvent<HTMLInputElement>) =>
                    setConfig((current: BuildingImportConfig) => ({
                      ...current,
                      skip_existing_buildings: event.target.checked,
                    }))
                  }
                />
                <span>Réutiliser les bâtiments déjà présents si un doublon est détecté</span>
              </label>
              <label className="toggle-field">
                <input
                  type="checkbox"
                  checked={config.create_missing_buildings_for_locals}
                  onChange={(event: ChangeEvent<HTMLInputElement>) =>
                    setConfig((current: BuildingImportConfig) => ({
                      ...current,
                      create_missing_buildings_for_locals: event.target.checked,
                    }))
                  }
                />
                <span>Créer un bâtiment synthétique lorsqu'une ligne local n'a pas de ligne bâtiment dédiée</span>
              </label>
            </div>
          ) : null}
        </aside>

        <div className="import-main-content">
          {analysis ? (
            <>
              <div className="section-block">
                <div className="section-heading">
                  <h3>3. Mapping des colonnes</h3>
                  <p>Chaque champ canonique peut être relié à une colonne du fichier utilisateur.</p>
                </div>
                <div className="info-banner">
                  <strong>{analysis.filename}</strong> · {analysis.total_rows} lignes détectées · feuille active : {analysis.selected_sheet}
                </div>
                {analysis.detected_row_type_values.length > 0 ? (
                  <div className="info-banner">
                    <strong>Valeurs de typologie détectées :</strong> {analysis.detected_row_type_values.join(", ")}
                  </div>
                ) : null}
                {mappingSections.map((section) => (
                  <div key={section.title} className="section-block">
                    <div className="section-heading">
                      <h3>{section.title}</h3>
                    </div>
                    <div className="import-mapping-grid">
                      {section.fields.map((field) => {
                        if (field.key === "row_type_column") {
                          return null;
                        }
                        return (
                          <label key={field.key} className="field">
                            <span>{field.label}</span>
                            <select
                              value={config.mapping[field.key] ?? ""}
                              onChange={(event) => updateMapping(field.key, event.target.value)}
                            >
                              <option value="">Aucune colonne</option>
                              {allColumns.map((column: string) => (
                                <option key={column} value={column}>
                                  {column}
                                </option>
                              ))}
                            </select>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                ))}
                <div className="form-actions">
                  <button type="button" onClick={() => previewMutation.mutate()} disabled={previewMutation.isPending || !file || analysisOutdated}>
                    {previewMutation.isPending ? "Prévisualisation..." : "Prévisualiser l'import"}
                  </button>
                </div>
              </div>

              {analysisOutdated ? (
                <div className="warning-card">
                  Tu as modifié la feuille ou la ligne d'entête depuis la dernière analyse. Relance d'abord l'analyse pour aligner la prévisualisation et l'import.
                </div>
              ) : null}

              <div className="section-block">
                <div className="section-heading">
                  <h3>Aperçu brut du fichier</h3>
                  <p>Extrait des premières lignes après lecture de l'entête sélectionnée.</p>
                </div>
                <div className="table-shell">
                  <table className="data-table">
                    <thead>
                      <tr>
                        {sampleHeaders.map((header: string) => (
                          <th key={header}>{header}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {analysis.sample_rows.map((row: Record<string, string>, index: number) => (
                        <tr key={`sample-${index}`}>
                          {sampleHeaders.map((header: string) => (
                            <td key={`${index}-${header}`}>{row[header] || ""}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <div className="empty-state buildings-empty-workspace">
              <strong>Aucun fichier analysé.</strong>
              <span>Commence par choisir un fichier puis clique sur « Analyser le fichier ».</span>
            </div>
          )}

          {preview ? (
            <div className="section-block">
              <div className="section-heading">
                <h3>4. Prévisualisation d'import</h3>
                <p>Contrôle les créations et rattachements avant écriture en base.</p>
              </div>
              <dl className="status-grid">
                <div>
                  <dt>Bâtiments détectés</dt>
                  <dd>{preview.building_rows_detected}</dd>
                </div>
                <div>
                  <dt>Locaux détectés</dt>
                  <dd>{preview.local_rows_detected}</dd>
                </div>
                <div>
                  <dt>Lignes lues</dt>
                  <dd>{preview.total_rows}</dd>
                </div>
              </dl>

              {preview.warnings.length > 0 ? (
                <div className="warning-list">
                  {preview.warnings.map((warning: string, index: number) => (
                    <div key={`warning-${index}`} className="warning-card">
                      {warning}
                    </div>
                  ))}
                </div>
              ) : null}

              <div className="section-block">
                <div className="section-heading">
                  <h3>Bâtiments prévus</h3>
                </div>
                <div className="table-shell">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Ligne</th>
                        <th>Action</th>
                        <th>Nom</th>
                        <th>Adresse</th>
                        <th>Parcelle</th>
                        <th>ID externe</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.building_preview.map((row: BuildingImportBuildingPreviewRow) => (
                        <tr key={`${row.identifier}-${row.source_row_number}`}>
                          <td>{row.source_row_number}</td>
                          <td>{row.action}</td>
                          <td>{row.nom_batiment || ""}</td>
                          <td>{row.adresse_reconstituee || ""}</td>
                          <td>{row.dgfip_reference_norm || ""}</td>
                          <td>{row.source_external_id || ""}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="section-block">
                <div className="section-heading">
                  <h3>Locaux prévus</h3>
                </div>
                <div className="table-shell">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Ligne</th>
                        <th>Parent</th>
                        <th>Nom local</th>
                        <th>Type</th>
                        <th>Niveau</th>
                        <th>ID externe</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.local_preview.map((row: BuildingImportLocalPreviewRow) => (
                        <tr key={`${row.parent_identifier}-${row.source_row_number}`}>
                          <td>{row.source_row_number}</td>
                          <td>{row.parent_identifier}</td>
                          <td>{row.nom_local || ""}</td>
                          <td>{row.type_local || ""}</td>
                          <td>{row.niveau || ""}</td>
                          <td>{row.source_external_id || ""}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="form-actions">
                <button type="button" onClick={() => executeMutation.mutate()} disabled={executeMutation.isPending || !file || analysisOutdated}>
                  {executeMutation.isPending ? "Import..." : "Lancer l'import"}
                </button>
              </div>
            </div>
          ) : null}

          {result ? (
            <div className="section-block">
              <div className="section-heading">
                <h3>5. Résultat d'import</h3>
                <p>Résumé de ce qui a été créé ou réutilisé.</p>
              </div>
              <dl className="status-grid">
                <div>
                  <dt>Bâtiments créés</dt>
                  <dd>{result.created_buildings}</dd>
                </div>
                <div>
                  <dt>Bâtiments réutilisés</dt>
                  <dd>{result.skipped_existing_buildings}</dd>
                </div>
                <div>
                  <dt>Locaux créés</dt>
                  <dd>{result.created_locals}</dd>
                </div>
              </dl>
              <dl className="status-grid">
                <div>
                  <dt>Locaux ignorés / existants</dt>
                  <dd>{result.skipped_existing_locals}</dd>
                </div>
                <div>
                  <dt>Fichier</dt>
                  <dd>{result.filename}</dd>
                </div>
                <div>
                  <dt>Feuille</dt>
                  <dd>{result.selected_sheet}</dd>
                </div>
              </dl>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
