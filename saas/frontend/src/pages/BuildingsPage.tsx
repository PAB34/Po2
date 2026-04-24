import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import {
  createBuildingFromNamingSelection,
  fetchBuildingNamingDataset,
  fetchBuildingNamingLookup,
  fetchBuildings,
  type Building,
  type BuildingNamingRow,
  type GeoJsonFeature,
} from "../lib/api";
import { BuildingNamingMap } from "../components/BuildingNamingMap";
import { useAuth } from "../providers/AuthProvider";

function buildAddressLine(
  building: Pick<Building, "numero_voirie" | "nature_voie" | "nom_voie" | "adresse_reconstituee" | "nom_commune">,
) {
  if (building.adresse_reconstituee) {
    return building.adresse_reconstituee;
  }

  const parts = [building.numero_voirie, building.nature_voie, building.nom_voie].filter(Boolean);
  return parts.length > 0 ? `${parts.join(" ")}, ${building.nom_commune}` : building.nom_commune;
}

function buildMajicAddressLine(row: BuildingNamingRow) {
  const parts = [row.numero_voirie, row.indice_repetition, row.nature_voie, row.nom_voie].filter(Boolean);
  return parts.length > 0 ? `${parts.join(" ")}, ${row.nom_commune}` : row.address_display;
}

type NamingCandidateEntry = Record<string, unknown>;
type AttributeEntry = [string, string];

function dedupeToponymyCandidates(entries: NamingCandidateEntry[]) {
  const seen = new Set<string>();
  const output: NamingCandidateEntry[] = [];
  for (const entry of entries) {
    const key = [
      String(entry.id ?? ""),
      String(entry.name ?? entry.label ?? "").trim().toLowerCase(),
      String(entry.source ?? "").trim().toLowerCase(),
      String(entry.typename ?? "").trim().toLowerCase(),
    ].join("|");
    if (!key || seen.has(key)) {
      continue;
    }
    seen.add(key);
    output.push(entry);
  }
  return output;
}

function sortToponymyCandidates(entries: NamingCandidateEntry[]) {
  return [...entries].sort((left, right) => {
    const leftDistance = Number(left.distance_m);
    const rightDistance = Number(right.distance_m);
    const normalizedLeft = Number.isFinite(leftDistance) ? leftDistance : Number.POSITIVE_INFINITY;
    const normalizedRight = Number.isFinite(rightDistance) ? rightDistance : Number.POSITIVE_INFINITY;
    if (normalizedLeft !== normalizedRight) {
      return normalizedLeft - normalizedRight;
    }
    return String(left.name ?? left.label ?? "").localeCompare(String(right.name ?? right.label ?? ""), "fr");
  });
}

function readResolvedNameCandidates(feature: GeoJsonFeature | null) {
  const properties = (feature?.properties ?? {}) as Record<string, unknown>;
  const rawCandidates = properties.resolved_name_candidates;
  if (!Array.isArray(rawCandidates)) {
    return [] as NamingCandidateEntry[];
  }
  return rawCandidates.filter(
    (candidate): candidate is NamingCandidateEntry => Boolean(candidate) && typeof candidate === "object" && !Array.isArray(candidate)
  );
}

function readIgnAttributes(feature: GeoJsonFeature | null) {
  const properties = (feature?.properties ?? {}) as Record<string, unknown>;
  const rawAttributes = properties.attributes;
  if (!rawAttributes || typeof rawAttributes !== "object" || Array.isArray(rawAttributes)) {
    return [] as AttributeEntry[];
  }
  return Object.entries(rawAttributes as Record<string, unknown>)
    .map(([key, value]) => [key, value == null ? "" : String(value)] as AttributeEntry)
    .sort(([left], [right]) => left.localeCompare(right, "fr"));
}

function collectToponymyCandidatesFromCollection(features: GeoJsonFeature[]) {
  const flattened: NamingCandidateEntry[] = [];
  for (const feature of features) {
    const properties = (feature.properties ?? {}) as Record<string, unknown>;
    const directCandidates = readResolvedNameCandidates(feature);
    if (directCandidates.length > 0) {
      flattened.push(...directCandidates);
      continue;
    }
    const fallbackName = String(properties.resolved_name ?? properties.name ?? properties.resolved_label ?? properties.label ?? "").trim();
    if (!fallbackName) {
      continue;
    }
    flattened.push({
      name: fallbackName,
      label: String(properties.resolved_label ?? fallbackName),
      source: String(properties.resolved_name_source ?? properties.ign_layer ?? ""),
      id: String(properties.ign_id ?? properties.id ?? ""),
      typename: String(properties.ign_typename ?? ""),
      distance_m: properties.resolved_name_distance_m,
    });
  }
  return sortToponymyCandidates(dedupeToponymyCandidates(flattened));
}

export function BuildingsPage() {
  const queryClient = useQueryClient();
  const { token } = useAuth();
  const [selectedUniqueKey, setSelectedUniqueKey] = useState<string | null>(null);
  const [validatedName, setValidatedName] = useState("");
  const [selectedFeatureId, setSelectedFeatureId] = useState<string>("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

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
    enabled: Boolean(token) && Boolean(selectedUniqueKey),
  });

  const createBuildingMutation = useMutation({
    mutationFn: (payload: { unique_key: string; validated_name?: string; selected_feature?: GeoJsonFeature | null }) =>
      createBuildingFromNamingSelection(token as string, {
        unique_key: payload.unique_key,
        validated_name: payload.validated_name,
        selected_feature: payload.selected_feature,
      }),
    onSuccess: async (building) => {
      setSuccess(`Bâtiment « ${building.nom_batiment || `#${building.id}`} » créé avec succès.`);
      setError(null);
      setValidatedName("");
      setSelectedFeatureId("");
      await queryClient.invalidateQueries({ queryKey: ["buildings"] });
    },
    onError: (mutationError: unknown) => {
      setSuccess(null);
      setError(mutationError instanceof Error ? mutationError.message : "Création du bâtiment impossible depuis la sélection IGN.");
    },
  });

  const filteredRows = useMemo(() => {
    const rows = namingDatasetQuery.data?.rows ?? [];
    const query = search.trim().toLowerCase();
    if (!query) {
      return rows;
    }
    return rows.filter((row) => {
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

  const candidateFeatures = (namingLookupQuery.data?.feature_collection.features ?? []) as GeoJsonFeature[];
  const selectedFeature = candidateFeatures.find((feature) => {
    const properties = feature.properties ?? {};
    const featureId = String(properties.ign_id ?? properties.id ?? "");
    return featureId === selectedFeatureId;
  }) ?? null;
  const selectedFeatureProperties = (selectedFeature?.properties ?? {}) as Record<string, unknown>;
  const selectedFeatureCandidates = useMemo(() => readResolvedNameCandidates(selectedFeature), [selectedFeature]);
  const aggregatedToponymyCandidates = useMemo(() => collectToponymyCandidatesFromCollection(candidateFeatures), [candidateFeatures]);
  const displayedToponymyCandidates = selectedFeature ? selectedFeatureCandidates : aggregatedToponymyCandidates;
  const selectedFeatureAttributes = useMemo(() => readIgnAttributes(selectedFeature), [selectedFeature]);

  async function handleCreateFromSelection() {
    if (!selectedUniqueKey) {
      setError("Sélectionne une adresse source DGFIP avant de créer un bâtiment.");
      return;
    }

    if (!token) {
      setError("Authentification requise.");
      return;
    }

    setError(null);
    setSuccess(null);

    if (!selectedFeature && !validatedName.trim()) {
      setError("Sélectionne un objet IGN sur la carte ou saisis un nom manuel avant de créer le bâtiment.");
      return;
    }

    await createBuildingMutation.mutateAsync({
      unique_key: selectedUniqueKey,
      validated_name: validatedName || undefined,
      selected_feature: selectedFeature,
    });
  }

  if (!token) {
    return (
      <section className="panel stack-lg">
        <div>
          <h2>Bâtiments</h2>
          <p>Connecte-toi pour consulter et créer des bâtiments.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="panel stack-lg">
      <div className="panel-header">
        <div>
          <h2>Bâtiments</h2>
          <p>
            Identifie les adresses uniques issues du fichier DGFIP, rapproche-les des objets IGN, puis valide le nom de
            bâtiment à enregistrer pour la collectivité.
          </p>
        </div>
        <div className="header-badge">
          <strong>{buildingsQuery.data?.length ?? 0}</strong>
          <span>bâtiment(s)</span>
        </div>
      </div>

      <div className="section-block">
        <div className="section-heading">
          <h3>Source DGFIP / MAJIC</h3>
          <p>
            Le fichier source actuellement exploité est <strong>{namingDatasetQuery.data?.filename ?? "non configuré"}</strong>.
            Les bâtiments sont regroupés par adresse unique avant rapprochement avec l’IGN.
          </p>
        </div>
        {namingDatasetQuery.data ? (
          <div className="info-banner">
            <strong>Commune filtrée :</strong> {namingDatasetQuery.data.filtered_city_name ?? "toutes les communes"}.
            {" "}
            <strong>Filtre MAJIC :</strong> {namingDatasetQuery.data.group_person_column} = {namingDatasetQuery.data.group_person_filter}.
            {" "}
            <strong>Cache :</strong> {namingDatasetQuery.data.cache_status}.
            {" "}
            <strong>Préparation :</strong> {namingDatasetQuery.data.build_duration_ms} ms.
            {" "}
            <strong>Réponse :</strong> {namingDatasetQuery.data.served_duration_ms} ms.
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

      <div className="section-block">
        <div className="section-heading">
          <h3>Adresses DGFIP à traiter</h3>
          <p>Choisis une adresse unique pour charger ses parcelles et ses candidats de bâtiments IGN.</p>
        </div>
        <label className="field">
          <span>Recherche d’une adresse ou d’une référence cadastrale</span>
          <input type="text" value={search} onChange={(event) => setSearch(event.target.value)} />
        </label>
        {namingDatasetQuery.isLoading && <p>Chargement des données DGFIP...</p>}
        {namingDatasetQuery.error instanceof Error && <p className="error-text">{namingDatasetQuery.error.message}</p>}
        <div className="resource-list">
          {filteredRows.map((row) => {
            const existingBuilding = existingBuildingByUniqueKey.get(row.unique_key);
            return (
            <article key={row.unique_key} className="resource-card">
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
                    setValidatedName("");
                    setSelectedFeatureId("");
                  }}
                >
                  {selectedUniqueKey === row.unique_key ? "Sélection active" : "Analyser cette adresse"}
                </button>
              </div>
            </article>
            );
          })}
        </div>
      </div>

      {selectedUniqueKey && (
        <div className="section-block">
          <div className="section-heading">
            <h3>Rapprochement IGN</h3>
            <p>
              Inspecte les candidats IGN pour l’adresse sélectionnée, puis valide le nom de bâtiment à conserver dans la
              base PatrimoineOp.
            </p>
          </div>
          {namingLookupQuery.isLoading && <p>Chargement des candidats IGN...</p>}
          {namingLookupQuery.error instanceof Error && <p className="error-text">{namingLookupQuery.error.message}</p>}
          {namingLookupQuery.data && (
            <>
              <div className="detail-grid">
                <div className="detail-card">
                  <span>Adresse source</span>
                  <strong>{namingLookupQuery.data.input_address}</strong>
                </div>
                <div className="detail-card">
                  <span>Source de centrage</span>
                  <strong>{namingLookupQuery.data.used_source}</strong>
                </div>
                <div className="detail-card">
                  <span>Parcelles détectées</span>
                  <strong>{namingLookupQuery.data.parcel_labels.join(", ") || "Aucune parcelle retrouvée"}</strong>
                </div>
                <div className="detail-card">
                  <span>Adresse de géocodage</span>
                  <strong>{String(namingLookupQuery.data.geocoder.display_name ?? namingLookupQuery.data.input_address)}</strong>
                </div>
              </div>

              <BuildingNamingMap
                addressLabel={namingLookupQuery.data.input_address}
                lat={namingLookupQuery.data.lat}
                lon={namingLookupQuery.data.lon}
                usedSource={namingLookupQuery.data.used_source}
                parcelFeatureCollection={namingLookupQuery.data.parcel_feature_collection}
                featureCollection={namingLookupQuery.data.feature_collection}
                selectedFeatureId={selectedFeatureId}
                onSelectFeatureId={setSelectedFeatureId}
              />

              <label className="field">
                <span>Candidat IGN retenu</span>
                <select value={selectedFeatureId} onChange={(event) => setSelectedFeatureId(event.target.value)}>
                  <option value="">Aucun objet IGN retenu</option>
                  {candidateFeatures.map((feature) => {
                    const properties = feature.properties ?? {};
                    const featureId = String(properties.ign_id ?? properties.id ?? "");
                    const label = String(properties.resolved_label ?? properties.label ?? properties.name ?? "Objet IGN");
                    const source = String(properties.resolved_name_source ?? properties.ign_layer ?? "IGN");
                    return (
                      <option key={featureId} value={featureId}>
                        {label} — {source}
                      </option>
                    );
                  })}
                </select>
              </label>

              <label className="field">
                <span>Nom du bâtiment validé</span>
                <input
                  type="text"
                  value={validatedName}
                  placeholder={
                    selectedFeature
                      ? String(
                          selectedFeature.properties.resolved_name ??
                            selectedFeature.properties.name ??
                            selectedFeature.properties.label ??
                            "Nom du bâtiment"
                        )
                      : "Nom saisi manuellement ou laissé vide pour reprendre la proposition IGN"
                  }
                  onChange={(event) => setValidatedName(event.target.value)}
                />
              </label>

              <div className="form-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => {
                    setSelectedFeatureId("");
                    setSuccess(null);
                    setError(null);
                  }}
                >
                  Aucun objet bâti retenu
                </button>
              </div>

              {selectedFeature && (
                <div className="resource-card">
                  <div className="resource-card-header">
                    <div>
                      <h3>{String(selectedFeatureProperties.resolved_label ?? selectedFeatureProperties.label ?? "Objet IGN")}</h3>
                      <p>
                        {String(selectedFeatureProperties.ign_layer ?? "IGN")} • {String(selectedFeatureProperties.ign_typename ?? "")}
                      </p>
                    </div>
                    <span className="resource-badge">
                      {selectedFeatureProperties.resolved_name_distance_m != null
                        ? `${selectedFeatureProperties.resolved_name_distance_m} m`
                        : "distance inconnue"}
                    </span>
                  </div>
                  <dl className="resource-metadata">
                    <div>
                      <dt>Nom brut IGN</dt>
                      <dd>{String(selectedFeatureProperties.name ?? "-")}</dd>
                    </div>
                    <div>
                      <dt>Nom proposé</dt>
                      <dd>{String(selectedFeatureProperties.resolved_name ?? "-")}</dd>
                    </div>
                    <div>
                      <dt>Source de nomination</dt>
                      <dd>{String(selectedFeatureProperties.resolved_name_source ?? "-")}</dd>
                    </div>
                  </dl>
                </div>
              )}

              {displayedToponymyCandidates.length > 0 && (
                <div className="section-block">
                  <div className="section-heading">
                    <h3>Toponymies IGN candidates</h3>
                    <p>
                      {selectedFeature
                        ? "Ces propositions sont les noms voisins détectés autour du bâtiment sélectionné."
                        : "Ces propositions sont agrégées sur les objets IGN chargés. Tu peux en choisir une avant de cliquer un bâtiment précis."}
                    </p>
                  </div>
                  <div className="candidate-list">
                    {displayedToponymyCandidates.map((candidate: NamingCandidateEntry, index: number) => (
                      <article
                        key={`${String(candidate.id ?? "")}-${index}`}
                        className="candidate-card"
                        onClick={() => {
                          const pickedName = String(candidate.name ?? candidate.label ?? "").trim();
                          if (!pickedName) {
                            return;
                          }
                          setValidatedName(pickedName);
                          setSuccess(null);
                          setError(
                            selectedFeature
                              ? null
                              : `Toponymie sélectionnée : ${pickedName}. Clique aussi un bâtiment si tu veux le lier précisément à un objet IGN.`
                          );
                        }}
                      >
                        <strong>{String(candidate.name ?? candidate.label ?? "Toponyme")}</strong>
                        <span>
                          {String(candidate.source ?? "IGN")}
                          {candidate.distance_m != null ? ` • ${String(candidate.distance_m)} m` : ""}
                        </span>
                        <small>{String(candidate.typename ?? "")}</small>
                      </article>
                    ))}
                  </div>
                </div>
              )}

              {selectedFeatureAttributes.length > 0 && (
                <div className="section-block">
                  <div className="section-heading">
                    <h3>Attributs IGN</h3>
                    <p>Vue détaillée des attributs bruts fournis par l’objet IGN sélectionné.</p>
                  </div>
                  <div className="attribute-table">
                    {selectedFeatureAttributes.map(([key, value]: AttributeEntry) => (
                      <div key={key} className="attribute-row">
                        <dt>{key}</dt>
                        <dd>{value || "-"}</dd>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {error && <p className="error-text">{error}</p>}
              {success && <p className="success-text">{success}</p>}

              <div className="form-actions">
                <button type="button" onClick={handleCreateFromSelection} disabled={createBuildingMutation.isPending}>
                  {createBuildingMutation.isPending
                    ? "Création..."
                    : selectedFeature
                      ? "Créer le bâtiment depuis cette sélection"
                      : "Créer le bâtiment avec le nom saisi"}
                </button>
              </div>
            </>
          )}
        </div>
      )}

      <div className="section-block">
        <div className="section-heading">
          <h3>Liste des bâtiments de la collectivité</h3>
          <p>Liste finale des bâtiments enregistrés, enrichis avec les données cadastrales et les éléments IGN validés.</p>
        </div>
        {buildingsQuery.isLoading && <p>Chargement des bâtiments...</p>}
        {buildingsQuery.error instanceof Error && <p className="error-text">{buildingsQuery.error.message}</p>}
        {!buildingsQuery.isLoading && !buildingsQuery.error && (buildingsQuery.data?.length ?? 0) === 0 && (
          <div className="empty-state">
            <strong>Aucun bâtiment pour le moment.</strong>
            <span>Commence par sélectionner une adresse DGFIP et valider son nom de bâtiment.</span>
          </div>
        )}
        <div className="resource-list">
          {buildingsQuery.data?.map((building: Building) => (
            <article key={building.id} className="resource-card">
              <div className="resource-card-header">
                <div>
                  <h3>{building.nom_batiment || `Bâtiment #${building.id}`}</h3>
                  <p>{buildAddressLine(building)}</p>
                </div>
                <span className="resource-badge">{building.statut_geocodage}</span>
              </div>
              <dl className="resource-metadata">
                <div>
                  <dt>Commune</dt>
                  <dd>{building.nom_commune}</dd>
                </div>
                <div>
                  <dt>Référence DGFIP</dt>
                  <dd>{building.dgfip_reference_norm ?? ([building.prefixe, building.section, building.numero_plan].filter(Boolean).join(" ") || "Non renseignée")}</dd>
                </div>
                <div>
                  <dt>Nom IGN proposé</dt>
                  <dd>{building.ign_name_proposed || building.ign_name || "Aucun rapprochement IGN"}</dd>
                </div>
              </dl>
              <div className="resource-card-actions">
                <Link className="secondary-link" to={`/buildings/${building.id}`}>
                  Ouvrir la fiche
                </Link>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
