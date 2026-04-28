import { useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { BuildingSelectionWorkspace } from "../components/BuildingSelectionWorkspace";
import {
  createBuildingFromNamingSelection,
  createBuildingRequest,
  fetchBuildingNamingDataset,
  fetchBuildingNamingLookup,
  fetchBuildings,
  fetchFreeAddressLookup,
  previewBuildingImportFile,
  type Building,
  type BuildingImportPreview,
  type BuildingImportRow,
  type BuildingNamingLookup,
  type BuildingNamingRow,
  type CreateBuildingPayload,
  type GeoJsonFeature,
  type User,
} from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

type CreationMode = "blank" | "import";
type WorkflowStep = 1 | 2 | 3;

type ImportedRowState = BuildingImportRow & {
  editableName: string;
  editableAddress: string;
  createdBuildingId: number | null;
};

function buildMajicAddressLine(row: BuildingNamingRow) {
  const parts = [row.numero_voirie, row.indice_repetition, row.nature_voie, row.nom_voie].filter(Boolean);
  return parts.length > 0 ? `${parts.join(" ")}, ${row.nom_commune}` : row.address_display;
}

function pickString(value: unknown) {
  const text = String(value ?? "").trim();
  return text || undefined;
}

function pickNumber(value: unknown) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : undefined;
}

function toRecord(value: unknown) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function guessColumn(columns: string[], candidates: string[]) {
  const normalizedCandidates = candidates.map((candidate) => candidate.trim().toLowerCase());
  return (
    columns.find((column) => normalizedCandidates.includes(column.trim().toLowerCase())) ??
    columns.find((column) => normalizedCandidates.some((candidate) => column.trim().toLowerCase().includes(candidate))) ??
    ""
  );
}

function normalizeImportedRows(rows: BuildingImportRow[]): ImportedRowState[] {
  return rows.map((row: BuildingImportRow) => ({
    ...row,
    editableName: row.source_name,
    editableAddress: row.address_display || row.source_address,
    createdBuildingId: null,
  }));
}

type ImportStats = {
  valid: number;
  invalid: number;
  pending: number;
  created: number;
};

function deriveImportCommune(user: User | null, row: ImportedRowState) {
  if (user?.city_id != null) {
    return undefined;
  }
  const segments = (pickString(row.editableAddress) ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return segments.length > 0 ? segments[segments.length - 1] : undefined;
}

function buildImportedBuildingPayload(row: ImportedRowState, user: User | null): CreateBuildingPayload {
  return {
    nom_batiment: pickString(row.editableName) ?? `Import ligne ${row.row_number}`,
    nom_commune: deriveImportCommune(user, row),
    adresse_reconstituee: pickString(row.editableAddress),
    latitude: row.lat ?? undefined,
    longitude: row.lon ?? undefined,
    source_creation: "IMPORT",
    statut_geocodage: row.validation_status === "valid" ? "A_VERIFIER" : "NON_FAIT",
  };
}

export function BuildingCreateEditPage() {
  const queryClient = useQueryClient();
  const { token, user } = useAuth();
  const [activeStep, setActiveStep] = useState<WorkflowStep>(1);
  const [mode, setMode] = useState<CreationMode>("import");
  const [listValidationAcknowledged, setListValidationAcknowledged] = useState(false);

  const [selectedUniqueKey, setSelectedUniqueKey] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [blankError, setBlankError] = useState<string | null>(null);
  const [blankSuccess, setBlankSuccess] = useState<string | null>(null);

  const [importFile, setImportFile] = useState<File | null>(null);
  const [importPreview, setImportPreview] = useState<BuildingImportPreview | null>(null);
  const [importNameColumn, setImportNameColumn] = useState("");
  const [importAddressColumn, setImportAddressColumn] = useState("");
  const [importRows, setImportRows] = useState<ImportedRowState[]>([]);
  const [importSearch, setImportSearch] = useState("");
  const [selectedImportRowNumber, setSelectedImportRowNumber] = useState<number | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState<string | null>(null);
  const [validatingRowNumber, setValidatingRowNumber] = useState<number | null>(null);
  const [portfolioValidationPending, setPortfolioValidationPending] = useState(false);

  const buildingsQuery = useQuery({
    queryKey: ["buildings", token],
    queryFn: () => fetchBuildings(token as string),
    enabled: Boolean(token),
  });

  const namingDatasetQuery = useQuery({
    queryKey: ["buildings", "naming-dataset", token],
    queryFn: () => fetchBuildingNamingDataset(token as string),
    enabled: Boolean(token),
  });

  const namingLookupQuery = useQuery({
    queryKey: ["buildings", "naming-lookup", selectedUniqueKey, token],
    queryFn: () => fetchBuildingNamingLookup(token as string, selectedUniqueKey as string),
    enabled: Boolean(token) && Boolean(selectedUniqueKey) && mode === "blank",
  });

  const selectedImportRow = useMemo(
    () => importRows.find((row: ImportedRowState) => row.row_number === selectedImportRowNumber) ?? null,
    [importRows, selectedImportRowNumber],
  );

  const createBlankBuildingMutation = useMutation({
    mutationFn: (payload: { unique_key: string; validated_name?: string; selected_feature?: GeoJsonFeature | null }) =>
      createBuildingFromNamingSelection(token as string, payload),
    onSuccess: async (building: Building) => {
      setBlankSuccess(`Bâtiment « ${building.nom_batiment || `#${building.id}`} » créé avec succès.`);
      setBlankError(null);
      await queryClient.invalidateQueries({ queryKey: ["buildings"] });
    },
    onError: (mutationError: unknown) => {
      setBlankSuccess(null);
      setBlankError(mutationError instanceof Error ? mutationError.message : "Création du bâtiment impossible depuis la sélection IGN.");
    },
  });

  const filteredRows = useMemo(() => {
    const rows = namingDatasetQuery.data?.rows ?? [];
    const query = search.trim().toLowerCase();
    if (!query) {
      return rows;
    }
    return rows.filter((row: BuildingNamingRow) => {
      return [row.address_display, row.nom_commune, row.numero_voirie, row.nom_voie, row.first_reference_norm]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query));
    });
  }, [namingDatasetQuery.data?.rows, search]);

  const existingBuildingByUniqueKey = useMemo(() => {
    const index = new Map<string, Building>();
    for (const building of buildingsQuery.data ?? []) {
      if (building.dgfip_unique_key) {
        index.set(building.dgfip_unique_key, building);
      }
    }
    return index;
  }, [buildingsQuery.data]);

  const filteredImportRows = useMemo(() => {
    const query = importSearch.trim().toLowerCase();
    if (!query) {
      return importRows;
    }
    return importRows.filter((row: ImportedRowState) => {
      return [row.editableName, row.editableAddress, row.validation_status, row.validation_message]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query));
    });
  }, [importRows, importSearch]);

  const importStats = useMemo(() => {
    return importRows.reduce(
      (accumulator: ImportStats, row: ImportedRowState) => {
        if (row.createdBuildingId) {
          accumulator.created += 1;
        } else if (row.validation_status === "valid") {
          accumulator.valid += 1;
        } else if (row.validation_status === "invalid") {
          accumulator.invalid += 1;
        } else {
          accumulator.pending += 1;
        }
        return accumulator;
      },
      { valid: 0, invalid: 0, pending: 0, created: 0 } as ImportStats,
    );
  }, [importRows]);

  async function handleBlankCreate(payload: { validatedName?: string; selectedFeature?: GeoJsonFeature | null }) {
    if (!selectedUniqueKey) {
      setBlankError("Sélectionne une adresse source DGFIP avant de créer un bâtiment.");
      return;
    }
    if (!token) {
      setBlankError("Authentification requise.");
      return;
    }
    setBlankError(null);
    setBlankSuccess(null);
    await createBlankBuildingMutation.mutateAsync({
      unique_key: selectedUniqueKey,
      validated_name: payload.validatedName,
      selected_feature: payload.selectedFeature,
    });
  }

  async function handlePreviewImportFile() {
    if (!token) {
      setImportError("Authentification requise.");
      return;
    }
    if (!importFile) {
      setImportError("Choisis un fichier patrimoine avant de lancer l’analyse.");
      return;
    }
    try {
      const preview = await previewBuildingImportFile(token, importFile);
      setImportPreview(preview);
      setImportRows([]);
      setSelectedImportRowNumber(null);
      setImportError(null);
      setImportSuccess(null);
      setImportNameColumn((current: string) => current || guessColumn(preview.columns, ["nom bâtiment", "nom batiment", "désignation", "designation", "nom", "libellé"]));
      setImportAddressColumn((current: string) => current || guessColumn(preview.columns, ["adresse", "adresse complète", "adresse complete"]));
    } catch (error) {
      setImportError(error instanceof Error ? error.message : "Analyse du fichier impossible.");
      setImportSuccess(null);
    }
  }

  async function handleLoadImportRows() {
    if (!token) {
      setImportError("Authentification requise.");
      return;
    }
    if (!importFile) {
      setImportError("Choisis un fichier patrimoine avant de charger les lignes.");
      return;
    }
    if (!importNameColumn || !importAddressColumn) {
      setImportError("Sélectionne les colonnes 'Nom bâtiment' et 'Adresse'.");
      return;
    }
    try {
      const preview = await previewBuildingImportFile(token, importFile, importNameColumn, importAddressColumn);
      setImportPreview(preview);
      setImportRows(normalizeImportedRows(preview.rows));
      setSelectedImportRowNumber(preview.rows.length > 0 ? preview.rows[0].row_number : null);
      setImportError(null);
      setImportSuccess(`${preview.rows.length} ligne(s) chargée(s). Les adresses incompatibles sont à corriger.`);
    } catch (error) {
      setImportError(error instanceof Error ? error.message : "Chargement des lignes importées impossible.");
      setImportSuccess(null);
    }
  }

  function handleImportFileChange(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] ?? null;
    setImportFile(nextFile);
    setImportPreview(null);
    setImportRows([]);
    setSelectedImportRowNumber(null);
    setImportNameColumn("");
    setImportAddressColumn("");
    setImportError(null);
    setImportSuccess(null);
  }

  function updateImportRow(rowNumber: number, updater: (row: ImportedRowState) => ImportedRowState) {
    setImportRows((current: ImportedRowState[]) =>
      current.map((row: ImportedRowState) => (row.row_number === rowNumber ? updater(row) : row)),
    );
  }

  async function handleValidateSelectedImportRow() {
    if (!token) {
      setImportError("Authentification requise.");
      return;
    }
    if (!selectedImportRow) {
      setImportError("Sélectionne une ligne importée à vérifier.");
      return;
    }
    const address = selectedImportRow.editableAddress.trim();
    if (!address) {
      updateImportRow(selectedImportRow.row_number, (row: ImportedRowState) => ({
        ...row,
        validation_status: "invalid",
        validation_message: "Adresse absente ou vide.",
        lat: null,
        lon: null,
      }));
      setImportError("Renseigne une adresse avant de lancer la vérification.");
      setImportSuccess(null);
      return;
    }
    setValidatingRowNumber(selectedImportRow.row_number);
    try {
      const lookup = await fetchFreeAddressLookup(token, address);
      const featureCount = lookup.feature_collection.features.length;
      const normalizedMessage = String(lookup.geocoder.display_name ?? lookup.input_address);
      updateImportRow(selectedImportRow.row_number, (row: ImportedRowState) => ({
        ...row,
        editableAddress: lookup.input_address,
        address_display: lookup.input_address,
        validation_status: featureCount > 0 ? "valid" : "invalid",
        validation_message:
          featureCount > 0
            ? `Adresse géolocalisée : ${normalizedMessage}. ${featureCount} bâtiment(s) IGN détecté(s).`
            : `Adresse géolocalisée : ${normalizedMessage}. Aucun bâtiment IGN n’a été détecté à proximité.`,
        lat: lookup.lat,
        lon: lookup.lon,
      }));
      if (featureCount > 0) {
        setImportError(null);
        setImportSuccess(`Adresse validée pour la ligne ${selectedImportRow.row_number}.`);
      } else {
        setImportError(`La ligne ${selectedImportRow.row_number} reste à corriger avant intégration.`);
        setImportSuccess(null);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Vérification de l’adresse impossible.";
      updateImportRow(selectedImportRow.row_number, (row: ImportedRowState) => ({
        ...row,
        validation_status: "invalid",
        validation_message: message,
        lat: null,
        lon: null,
      }));
      setImportError(message);
      setImportSuccess(null);
    } finally {
      setValidatingRowNumber(null);
    }
  }

  async function handleValidatePortfolioList() {
    if (mode !== "import") {
      setListValidationAcknowledged(true);
      return;
    }
    if (!token) {
      setImportError("Authentification requise.");
      return;
    }
    const rowsToCreate = importRows.filter((row: ImportedRowState) => row.validation_status === "valid" && !row.createdBuildingId);
    const alreadyCreatedCount = importRows.filter((row: ImportedRowState) => row.createdBuildingId).length;
    if (rowsToCreate.length === 0) {
      if (alreadyCreatedCount > 0 || buildingsCount > 0) {
        setListValidationAcknowledged(true);
        return;
      }
      setImportError("Aucune ligne valide à intégrer. Corrige au moins une adresse avant de valider la liste.");
      setImportSuccess(null);
      return;
    }

    setPortfolioValidationPending(true);
    setImportError(null);
    setImportSuccess(null);

    let createdCount = 0;
    const failures: string[] = [];
    for (const row of rowsToCreate) {
      try {
        const building = await createBuildingRequest(token, buildImportedBuildingPayload(row, user));
        createdCount += 1;
        setImportRows((current: ImportedRowState[]) =>
          current.map((entry: ImportedRowState) =>
            entry.row_number === row.row_number ? { ...entry, createdBuildingId: building.id } : entry,
          ),
        );
      } catch (error) {
        failures.push(`Ligne ${row.row_number} : ${error instanceof Error ? error.message : "création impossible"}`);
      }
    }

    await queryClient.invalidateQueries({ queryKey: ["buildings"] });

    const invalidCount = importRows.filter((row: ImportedRowState) => row.validation_status === "invalid").length;
    if (createdCount > 0 || alreadyCreatedCount > 0 || buildingsCount > 0) {
      setListValidationAcknowledged(true);
    }
    if (createdCount > 0) {
      setImportSuccess(
        `${createdCount} bâtiment(s) créé(s) automatiquement. ${invalidCount > 0 ? `${invalidCount} ligne(s) en anomalie n’ont pas été intégrées.` : "Toutes les lignes compatibles ont été intégrées."}`,
      );
    } else if (invalidCount > 0) {
      setImportSuccess(`${invalidCount} ligne(s) en anomalie restent à corriger avant toute intégration supplémentaire.`);
    }
    setImportError(failures.length > 0 ? failures.slice(0, 3).join(" ") : null);
    setPortfolioValidationPending(false);
  }

  const buildingsCount = buildingsQuery.data?.length ?? 0;
  const currentModeLabel = mode === "import" ? "Import d’un fichier patrimoine" : "Liste vierge DGFIP / MAJIC";
  const canAdvanceToValidation = mode === "import" ? importRows.length > 0 || buildingsCount > 0 : Boolean(selectedUniqueKey) || buildingsCount > 0;
  const canValidatePortfolioList = mode === "import" ? importStats.valid > 0 || importStats.created > 0 || buildingsCount > 0 : buildingsCount > 0;
  const readyToOpenBuildingsList =
    mode === "import"
      ? listValidationAcknowledged && (importStats.created > 0 || buildingsCount > 0)
      : canValidatePortfolioList && listValidationAcknowledged;

  if (!token) {
    return (
      <section className="panel stack-lg">
        <div>
          <h2>Constituer la liste patrimoniale</h2>
          <p>Connecte-toi pour choisir un mode de constitution, préparer la liste puis la valider.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="panel stack-lg buildings-workspace-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Bâtiments</p>
          <h2>Constituer la liste patrimoniale</h2>
          <p>
            Passe par un parcours guidé : choisis un mode de constitution, prépare ta liste patrimoniale, puis valide-la
            avant d’ouvrir l’espace de consultation et de modification.
          </p>
        </div>
        <div className="buildings-header-actions">
          <Link className="secondary-link" to="/buildings">
            Retour aux entrées bâtiments
          </Link>
          <div className="header-badge">
            <strong>{buildingsQuery.data?.length ?? 0}</strong>
            <span>bâtiment(s)</span>
          </div>
        </div>
      </div>

      <div className="buildings-stepper">
        <button type="button" className={activeStep === 1 ? "step-chip step-chip-active" : "step-chip"} onClick={() => setActiveStep(1)}>
          <strong>Étape 1</strong>
          <span>Choix du mode</span>
        </button>
        <button type="button" className={activeStep === 2 ? "step-chip step-chip-active" : "step-chip"} onClick={() => setActiveStep(2)}>
          <strong>Étape 2</strong>
          <span>Préparer la liste</span>
        </button>
        <button
          type="button"
          className={activeStep === 3 ? "step-chip step-chip-active" : "step-chip"}
          onClick={() => {
            if (canAdvanceToValidation) {
              setActiveStep(3);
            }
          }}
          disabled={!canAdvanceToValidation}
        >
          <strong>Étape 3</strong>
          <span>Valider la liste</span>
        </button>
      </div>

      {activeStep === 1 ? (
        <div className="stack-lg">
          <div className="workflow-step-hero">
            <div className="section-heading">
              <h3>Étape 1 · Choisir le mode de constitution</h3>
              <p>
                Commence par indiquer si tu veux importer un fichier patrimoine ou partir d’une liste vierge pour construire progressivement la liste patrimoniale.
              </p>
            </div>
          </div>

          <div className="buildings-choice-grid">
            <article className={`resource-card buildings-entry-card ${mode === "import" ? "resource-card-active" : ""}`}>
              <div className="section-heading">
                <h3>Importer un fichier</h3>
                <p>
                  Recommandé si tu disposes déjà d’un listing patrimoine. Tu pourras mapper les colonnes, corriger les adresses puis rattacher les bâtiments à l’IGN.
                </p>
              </div>
              <div className="resource-card-actions">
                <button
                  type="button"
                  onClick={() => {
                    setMode("import");
                    setActiveStep(2);
                    setListValidationAcknowledged(false);
                  }}
                >
                  Choisir l’import
                </button>
              </div>
            </article>

            <article className={`resource-card buildings-entry-card ${mode === "blank" ? "resource-card-active" : ""}`}>
              <div className="section-heading">
                <h3>Partir d’une liste vierge</h3>
                <p>
                  Utilise la base DGFIP / MAJIC déjà préparée, sélectionne une adresse source puis crée les bâtiments retenus à partir des rapprochements IGN.
                </p>
              </div>
              <div className="resource-card-actions">
                <button
                  type="button"
                  onClick={() => {
                    setMode("blank");
                    setActiveStep(2);
                    setListValidationAcknowledged(false);
                  }}
                >
                  Choisir la liste vierge
                </button>
              </div>
            </article>
          </div>
        </div>
      ) : null}

      {activeStep === 2 ? (
        <div className="stack-lg">
          <div className="panel-header">
            <div>
              <h3>Étape 2 · Préparer la liste patrimoniale</h3>
              <p>
                Mode actuel : <strong>{currentModeLabel}</strong>. Prépare les éléments à intégrer, crée les bâtiments retenus, puis passe à l’étape de validation lorsque tu es prêt.
              </p>
            </div>
            <div className="buildings-header-actions">
              <button type="button" className="secondary-button" onClick={() => setActiveStep(1)}>
                Changer de mode
              </button>
              <button type="button" onClick={() => setActiveStep(3)} disabled={!canAdvanceToValidation}>
                Passer à la validation
              </button>
            </div>
          </div>

          {mode === "blank" ? (
            <div className="buildings-workspace">
              <aside className="buildings-sidebar">
                <div className="section-block">
                  <div className="section-heading">
                    <h3>Source DGFIP / MAJIC</h3>
                    <p>
                      Le fichier source actuellement exploité est <strong>{namingDatasetQuery.data?.filename ?? "non configuré"}</strong>. Les bâtiments sont regroupés par adresse unique avant rapprochement avec l’IGN.
                    </p>
                  </div>
                  {namingDatasetQuery.data ? (
                    <div className="info-banner">
                      <strong>Commune filtrée :</strong> {namingDatasetQuery.data.filtered_city_name ?? "toutes les communes"}. <strong>Filtre MAJIC :</strong> {namingDatasetQuery.data.group_person_column} = {namingDatasetQuery.data.group_person_filter}. <strong>Cache :</strong> {namingDatasetQuery.data.cache_status}. <strong>Préparation :</strong> {namingDatasetQuery.data.build_duration_ms} ms. <strong>Réponse :</strong> {namingDatasetQuery.data.served_duration_ms} ms.
                    </div>
                  ) : null}
                  <div className="detail-grid">
                    <div className="detail-card">
                      <span>Lignes source</span>
                      <strong>{namingDatasetQuery.data?.total_rows ?? 0}</strong>
                    </div>
                    <div className="detail-card">
                      <span>Adresses uniques</span>
                      <strong>{namingDatasetQuery.data?.unique_addresses ?? 0}</strong>
                    </div>
                    <div className="detail-card">
                      <span>Colonnes détectées</span>
                      <strong>{namingDatasetQuery.data?.columns.length ?? 0}</strong>
                    </div>
                  </div>
                </div>

                <div className="section-block buildings-addresses-section">
                  <div className="section-heading">
                    <h3>Adresses DGFIP à traiter</h3>
                    <p>Choisis une adresse unique pour charger ses parcelles et ses candidats de bâtiments IGN.</p>
                  </div>
                  <label className="field">
                    <span>Recherche d’une adresse ou d’une référence cadastrale</span>
                    <input type="text" value={search} onChange={(event: ChangeEvent<HTMLInputElement>) => setSearch(event.target.value)} />
                  </label>
                  {namingDatasetQuery.isLoading ? <p>Chargement des données DGFIP...</p> : null}
                  {namingDatasetQuery.error instanceof Error ? <p className="error-text">{namingDatasetQuery.error.message}</p> : null}
                  <div className="resource-list buildings-address-list">
                    {filteredRows.map((row: BuildingNamingRow) => {
                      const existingBuilding = existingBuildingByUniqueKey.get(row.unique_key);
                      const isActive = selectedUniqueKey === row.unique_key;
                      return (
                        <article key={row.unique_key} className={`resource-card ${isActive ? "resource-card-active" : ""}`}>
                          <div className="resource-card-header">
                            <div>
                              <h3>{buildMajicAddressLine(row)}</h3>
                              <p>{row.address_display}</p>
                            </div>
                            <span className="resource-badge">{existingBuilding ? "Déjà créé" : `${row.duplicate_count} ligne(s)`}</span>
                          </div>
                          <dl className="resource-metadata">
                            <div>
                              <dt>Commune</dt>
                              <dd>{row.nom_commune}</dd>
                            </div>
                            <div>
                              <dt>Références</dt>
                              <dd>{row.references.join(", ") || "Aucune"}</dd>
                            </div>
                            <div>
                              <dt>Indices MAJIC</dt>
                              <dd>{row.majic_building_values.join(", ") || "Aucun bâtiment MAJIC"}</dd>
                            </div>
                          </dl>
                          <div className="resource-card-actions">
                            {existingBuilding ? (
                              <Link className="secondary-link" to={`/buildings/${existingBuilding.id}`}>
                                Ouvrir le bâtiment existant
                              </Link>
                            ) : null}
                            <button
                              type="button"
                              className="secondary-button"
                              onClick={() => {
                                setSelectedUniqueKey(row.unique_key);
                                setBlankError(null);
                                setBlankSuccess(null);
                                setListValidationAcknowledged(false);
                              }}
                            >
                              {isActive ? "Sélection active" : "Analyser cette adresse"}
                            </button>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                </div>
              </aside>

              <div className="buildings-main-content">
                {namingLookupQuery.isLoading ? <p>Chargement des candidats IGN...</p> : null}
                {namingLookupQuery.error instanceof Error ? <p className="error-text">{namingLookupQuery.error.message}</p> : null}
                <BuildingSelectionWorkspace
                  lookupData={(namingLookupQuery.data ?? null) as BuildingNamingLookup | null}
                  emptyTitle="Aucune adresse sélectionnée."
                  emptyDescription="Choisis une adresse dans la colonne de gauche pour afficher la carte, sélectionner un ou plusieurs bâtiments et valider les informations."
                  createPending={createBlankBuildingMutation.isPending}
                  error={blankError}
                  success={blankSuccess}
                  createLabelWithSelection="Créer le bâtiment depuis cette sélection"
                  createLabelWithoutSelection="Créer le bâtiment avec le nom saisi"
                  onCreate={handleBlankCreate}
                />
              </div>
            </div>
          ) : (
            <div className="buildings-workspace">
              <aside className="buildings-sidebar">
                <div className="section-block">
                  <div className="section-heading">
                    <h3>Import d’un listing patrimoine</h3>
                    <p>
                      Uploade un fichier CSV, XLS, XLSX ou XLSM, choisis les colonnes <strong>Nom bâtiment</strong> et <strong>Adresse</strong>, puis vérifie la compatibilité IGN de chaque adresse.
                    </p>
                  </div>
                  <label className="field">
                    <span>Fichier patrimoine</span>
                    <input type="file" accept=".csv,.xls,.xlsx,.xlsm" onChange={handleImportFileChange} />
                  </label>
                  <div className="form-actions">
                    <button type="button" className="secondary-button" onClick={() => void handlePreviewImportFile()} disabled={!importFile}>
                      Analyser le fichier
                    </button>
                  </div>
                  {importPreview ? (
                    <div className="section-block">
                      <div className="detail-grid">
                        <div className="detail-card">
                          <span>Fichier</span>
                          <strong>{importPreview.filename}</strong>
                        </div>
                        <div className="detail-card">
                          <span>Colonnes détectées</span>
                          <strong>{importPreview.columns.length}</strong>
                        </div>
                        <div className="detail-card">
                          <span>Lignes source</span>
                          <strong>{importPreview.total_rows}</strong>
                        </div>
                      </div>
                      <div className="import-sample-table">
                        <div className="import-sample-row import-sample-row-head">
                          {importPreview.columns.slice(0, 4).map((column: string) => (
                            <strong key={column}>{column}</strong>
                          ))}
                        </div>
                        {importPreview.sample_rows.map((row: Record<string, string>, index: number) => (
                          <div key={`sample-${index}`} className="import-sample-row">
                            {importPreview.columns.slice(0, 4).map((column: string) => (
                              <span key={`${index}-${column}`}>{row[column] || "-"}</span>
                            ))}
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                  {importPreview ? (
                    <>
                      <label className="field">
                        <span>Colonne Nom bâtiment</span>
                        <select value={importNameColumn} onChange={(event: ChangeEvent<HTMLSelectElement>) => setImportNameColumn(event.target.value)}>
                          <option value="">Sélectionne une colonne</option>
                          {importPreview.columns.map((column: string) => (
                            <option key={`name-${column}`} value={column}>
                              {column}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="field">
                        <span>Colonne Adresse</span>
                        <select value={importAddressColumn} onChange={(event: ChangeEvent<HTMLSelectElement>) => setImportAddressColumn(event.target.value)}>
                          <option value="">Sélectionne une colonne</option>
                          {importPreview.columns.map((column: string) => (
                            <option key={`address-${column}`} value={column}>
                              {column}
                            </option>
                          ))}
                        </select>
                      </label>
                      <div className="form-actions">
                        <button type="button" onClick={() => void handleLoadImportRows()}>
                          Charger les lignes importées
                        </button>
                      </div>
                    </>
                  ) : null}
                  {importError ? <p className="error-text">{importError}</p> : null}
                  {importSuccess ? <p className="success-text">{importSuccess}</p> : null}
                </div>

                {importRows.length > 0 ? (
                  <div className="section-block buildings-addresses-section">
                    <div className="section-heading">
                      <h3>Lignes patrimoine à traiter</h3>
                      <p>Les lignes en rouge doivent être corrigées manuellement avant l’analyse IGN.</p>
                    </div>
                    <div className="detail-grid">
                      <div className="detail-card">
                        <span>Valides</span>
                        <strong>{importStats.valid}</strong>
                      </div>
                      <div className="detail-card">
                        <span>À corriger</span>
                        <strong>{importStats.invalid}</strong>
                      </div>
                      <div className="detail-card">
                        <span>Créées</span>
                        <strong>{importStats.created}</strong>
                      </div>
                    </div>
                    <label className="field">
                      <span>Recherche dans les lignes importées</span>
                      <input type="text" value={importSearch} onChange={(event: ChangeEvent<HTMLInputElement>) => setImportSearch(event.target.value)} />
                    </label>
                    {selectedImportRow ? (
                      <div className="resource-card import-edit-card">
                        <div className="resource-card-header">
                          <div>
                            <h3>Ligne {selectedImportRow.row_number}</h3>
                            <p>Corrige l’adresse puis relance la vérification si nécessaire.</p>
                          </div>
                          <span className={`resource-badge ${selectedImportRow.validation_status === "invalid" ? "resource-badge-danger" : "resource-badge-success"}`}>
                            {selectedImportRow.validation_status === "valid" ? "Adresse compatible" : "À corriger"}
                          </span>
                        </div>
                        <label className="field">
                          <span>Nom bâtiment</span>
                          <input
                            type="text"
                            value={selectedImportRow.editableName}
                            onChange={(event: ChangeEvent<HTMLInputElement>) => {
                              const value = event.target.value;
                              updateImportRow(selectedImportRow.row_number, (row: ImportedRowState) => ({
                                ...row,
                                editableName: value,
                              }));
                            }}
                          />
                        </label>
                        <label className="field">
                          <span>Adresse</span>
                          <input
                            type="text"
                            value={selectedImportRow.editableAddress}
                            onChange={(event: ChangeEvent<HTMLInputElement>) => {
                              const value = event.target.value;
                              updateImportRow(selectedImportRow.row_number, (row: ImportedRowState) => ({
                                ...row,
                                editableAddress: value,
                                address_display: value,
                                validation_status: value.trim() ? "pending" : "invalid",
                                validation_message: value.trim()
                                  ? "Adresse modifiée. Vérifie-la avant de lancer l’analyse IGN."
                                  : "Adresse absente ou vide.",
                                lat: null,
                                lon: null,
                              }));
                            }}
                          />
                        </label>
                        <div className="form-actions">
                          <button type="button" className="secondary-button" onClick={() => void handleValidateSelectedImportRow()} disabled={validatingRowNumber === selectedImportRow.row_number}>
                            {validatingRowNumber === selectedImportRow.row_number ? "Vérification..." : "Vérifier cette adresse"}
                          </button>
                          {selectedImportRow.createdBuildingId ? (
                            <Link className="secondary-link" to={`/buildings/${selectedImportRow.createdBuildingId}`}>
                              Ouvrir le bâtiment créé
                            </Link>
                          ) : null}
                        </div>
                        {selectedImportRow.validation_message ? <p>{selectedImportRow.validation_message}</p> : null}
                      </div>
                    ) : null}
                    <div className="resource-list buildings-address-list">
                      {filteredImportRows.map((row: ImportedRowState) => {
                        const isActive = selectedImportRowNumber === row.row_number;
                        const stateClass = row.createdBuildingId
                          ? "resource-card-success"
                          : row.validation_status === "valid"
                            ? "resource-card-valid"
                            : row.validation_status === "invalid"
                              ? "resource-card-invalid"
                              : "resource-card-pending";
                        const badgeLabel = row.createdBuildingId
                          ? "Créé"
                          : row.validation_status === "valid"
                            ? "Adresse OK"
                            : row.validation_status === "invalid"
                              ? "Adresse KO"
                              : "À vérifier";
                        return (
                          <article key={row.row_number} className={`resource-card ${stateClass} ${isActive ? "resource-card-active" : ""}`}>
                            <div className="resource-card-header">
                              <div>
                                <h3>{row.editableName || `Ligne ${row.row_number}`}</h3>
                                <p>{row.editableAddress || row.source_address || "Adresse manquante"}</p>
                              </div>
                              <span className="resource-badge">{badgeLabel}</span>
                            </div>
                            <dl className="resource-metadata">
                              <div>
                                <dt>Ligne source</dt>
                                <dd>{row.row_number}</dd>
                              </div>
                              <div>
                                <dt>Latitude</dt>
                                <dd>{row.lat ?? "-"}</dd>
                              </div>
                              <div>
                                <dt>Longitude</dt>
                                <dd>{row.lon ?? "-"}</dd>
                              </div>
                            </dl>
                            {row.validation_message ? <p>{row.validation_message}</p> : null}
                            <div className="resource-card-actions">
                              {row.createdBuildingId ? (
                                <Link className="secondary-link" to={`/buildings/${row.createdBuildingId}`}>
                                  Ouvrir le bâtiment créé
                                </Link>
                              ) : null}
                              <button
                                type="button"
                                className="secondary-button"
                                onClick={() => {
                                  setSelectedImportRowNumber(row.row_number);
                                  setImportError(null);
                                  setImportSuccess(null);
                                  setListValidationAcknowledged(false);
                                }}
                              >
                                {isActive ? "Ligne active" : row.validation_status === "valid" ? "Analyser cette ligne" : "Corriger cette ligne"}
                              </button>
                            </div>
                          </article>
                        );
                      })}
                    </div>
                  </div>
                ) : null}
              </aside>

              <div className="buildings-main-content">
                <div className="section-block">
                  <div className="section-heading">
                    <h3>Contrôle des adresses importées</h3>
                    <p>
                      Dans ce mode, l’import sert uniquement à vérifier le géocodage et la compatibilité IGN des adresses. Les lignes valides seront créées automatiquement à l’étape 3. L’<strong>Attachement GEO</strong> détaillé se fera ensuite depuis chaque fiche bâtiment.
                    </p>
                  </div>

                  <div className="detail-grid buildings-summary-grid">
                    <div className="detail-card">
                      <span>Adresses prêtes</span>
                      <strong>{importStats.valid}</strong>
                    </div>
                    <div className="detail-card">
                      <span>Anomalies à corriger</span>
                      <strong>{importStats.invalid}</strong>
                    </div>
                    <div className="detail-card">
                      <span>Déjà intégrées</span>
                      <strong>{importStats.created}</strong>
                    </div>
                  </div>

                  {selectedImportRow ? (
                    <div className={`resource-card ${selectedImportRow.validation_status === "invalid" ? "resource-card-invalid" : selectedImportRow.validation_status === "valid" ? "resource-card-valid" : "resource-card-pending"}`}>
                      <div className="resource-card-header">
                        <div>
                          <h3>{selectedImportRow.editableName || `Ligne ${selectedImportRow.row_number}`}</h3>
                          <p>{selectedImportRow.editableAddress || "Adresse manquante"}</p>
                        </div>
                        <span className="resource-badge">
                          {selectedImportRow.createdBuildingId
                            ? "Créée"
                            : selectedImportRow.validation_status === "valid"
                              ? "Prête pour validation"
                              : selectedImportRow.validation_status === "invalid"
                                ? "À corriger"
                                : "En attente"}
                        </span>
                      </div>
                      <dl className="resource-metadata">
                        <div>
                          <dt>Latitude</dt>
                          <dd>{selectedImportRow.lat ?? "-"}</dd>
                        </div>
                        <div>
                          <dt>Longitude</dt>
                          <dd>{selectedImportRow.lon ?? "-"}</dd>
                        </div>
                        <div>
                          <dt>Étape suivante</dt>
                          <dd>
                            {selectedImportRow.validation_status === "valid"
                              ? "Cette ligne sera intégrée automatiquement à l’étape 3."
                              : "Corrige l’adresse puis relance la vérification pour l’intégrer."}
                          </dd>
                        </div>
                      </dl>
                      {selectedImportRow.validation_message ? <p>{selectedImportRow.validation_message}</p> : null}
                    </div>
                  ) : (
                    <div className="empty-state buildings-empty-workspace">
                      <strong>Aucune ligne importée sélectionnée.</strong>
                      <span>Choisis une ligne dans la colonne de gauche pour contrôler son géocodage et corriger son adresse si nécessaire.</span>
                    </div>
                  )}

                  <div className="info-banner">
                    <strong>Validation finale :</strong> à l’étape 3, seules les lignes vertes seront créées dans la liste des bâtiments. Les lignes rouges resteront exclues tant qu’elles ne sont pas corrigées.
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : null}

      {activeStep === 3 ? (
        <div className="stack-lg">
          <div className="panel-header">
            <div>
              <h3>Étape 3 · Valider la liste patrimoniale</h3>
              <p>
                {mode === "import"
                  ? "Confirme la liste pour créer automatiquement les lignes compatibles, ignorer les anomalies restantes et basculer ensuite dans l’espace Liste des bâtiments."
                  : "Vérifie que les bâtiments à conserver ont bien été créés, puis confirme la validation pour basculer dans l’espace Liste des bâtiments."}
              </p>
            </div>
            <div className="buildings-header-actions">
              <button type="button" className="secondary-button" onClick={() => setActiveStep(2)}>
                Revenir à la préparation
              </button>
              <button type="button" onClick={() => void handleValidatePortfolioList()} disabled={!canValidatePortfolioList || portfolioValidationPending}>
                {portfolioValidationPending ? "Validation en cours..." : "Valider la liste patrimoniale"}
              </button>
            </div>
          </div>

          <div className="detail-grid buildings-summary-grid">
            <div className="detail-card">
              <span>Mode retenu</span>
              <strong>{currentModeLabel}</strong>
            </div>
            <div className="detail-card">
              <span>Bâtiments actuellement créés</span>
              <strong>{buildingsCount}</strong>
            </div>
            <div className="detail-card">
              <span>État du parcours</span>
              <strong>{canAdvanceToValidation ? "Prêt pour validation" : "Préparation à compléter"}</strong>
            </div>
          </div>

          {mode === "import" ? (
            <div className="detail-grid buildings-summary-grid">
              <div className="detail-card">
                <span>Lignes chargées</span>
                <strong>{importRows.length}</strong>
              </div>
              <div className="detail-card">
                <span>Adresses valides</span>
                <strong>{importStats.valid}</strong>
              </div>
              <div className="detail-card">
                <span>Bâtiments créés depuis l’import</span>
                <strong>{importStats.created}</strong>
              </div>
            </div>
          ) : (
            <div className="info-banner">
              <strong>Mode liste vierge :</strong> sélectionne une adresse DGFIP / MAJIC, rapproche-la avec l’IGN puis crée les bâtiments retenus. La validation finale devient disponible dès qu’au moins un bâtiment est présent dans la liste.
            </div>
          )}

          {!canValidatePortfolioList ? (
            <div className="empty-state">
              <strong>La liste n’est pas encore prête à être validée.</strong>
              <span>
                {mode === "import"
                  ? "Aucune ligne importée n’est encore compatible avec l’IGN. Corrige au moins une adresse rouge pour pouvoir l’intégrer automatiquement à la validation finale."
                  : "Valider une adresse ou visualiser un candidat IGN ne suffit pas encore : crée au moins un bâtiment à l’étape 2 pour ouvrir ensuite l’espace “Liste des bâtiments”."}
              </span>
            </div>
          ) : null}

          {readyToOpenBuildingsList ? (
            <div className="info-banner">
              <strong>Liste patrimoniale validée.</strong> Tu peux maintenant ouvrir la liste des bâtiments pour consulter la carte, la liste filtrable et modifier les fiches existantes.
              <div className="form-actions">
                <Link className="secondary-link" to="/buildings/list">
                  Ouvrir la liste des bâtiments
                </Link>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
