import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent } from "react";

import type { BuildingNamingLookup, FreeAddressLookup, GeoJsonFeature } from "../lib/api";
import { BuildingNamingMap } from "./BuildingNamingMap";

type NamingCandidateEntry = Record<string, unknown>;
type AttributeEntry = [string, string];

type LookupData = BuildingNamingLookup | FreeAddressLookup;

type BuildingSelectionWorkspaceProps = {
  lookupData: LookupData | null;
  emptyTitle: string;
  emptyDescription: string;
  initialValidatedName?: string;
  createPending: boolean;
  error: string | null;
  success: string | null;
  createLabelWithSelection: string;
  createLabelWithoutSelection: string;
  onCreate: (payload: { validatedName?: string; selectedFeature?: GeoJsonFeature | null }) => Promise<void> | void;
};

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
    (candidate): candidate is NamingCandidateEntry => Boolean(candidate) && typeof candidate === "object" && !Array.isArray(candidate),
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

export function BuildingSelectionWorkspace({
  lookupData,
  emptyTitle,
  emptyDescription,
  initialValidatedName = "",
  createPending,
  error,
  success,
  createLabelWithSelection,
  createLabelWithoutSelection,
  onCreate,
}: BuildingSelectionWorkspaceProps) {
  const [validatedName, setValidatedName] = useState(initialValidatedName);
  const [selectedFeatureIds, setSelectedFeatureIds] = useState<string[]>([]);
  const [activeFeatureId, setActiveFeatureId] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    setValidatedName(initialValidatedName);
    setSelectedFeatureIds([]);
    setActiveFeatureId("");
    setLocalError(null);
  }, [initialValidatedName, lookupData?.input_address]);

  const candidateFeatures = useMemo(
    () => (lookupData?.feature_collection.features ?? []) as GeoJsonFeature[],
    [lookupData?.feature_collection.features],
  );
  const activeOrLastSelectedFeatureId = activeFeatureId || selectedFeatureIds[selectedFeatureIds.length - 1] || "";
  const selectedFeature = candidateFeatures.find((feature: GeoJsonFeature) => {
    const properties = feature.properties ?? {};
    const featureId = String(properties.ign_id ?? properties.id ?? "");
    return featureId === activeOrLastSelectedFeatureId;
  }) ?? null;
  const selectedFeatureProperties = (selectedFeature?.properties ?? {}) as Record<string, unknown>;
  const selectedFeatureCandidates = useMemo(() => readResolvedNameCandidates(selectedFeature), [selectedFeature]);
  const aggregatedToponymyCandidates = useMemo(() => collectToponymyCandidatesFromCollection(candidateFeatures), [candidateFeatures]);
  const displayedToponymyCandidates = selectedFeature ? selectedFeatureCandidates : aggregatedToponymyCandidates;
  const selectedFeatureAttributes = useMemo(() => readIgnAttributes(selectedFeature), [selectedFeature]);

  function toggleFeatureSelection(featureId: string) {
    setSelectedFeatureIds((current: string[]) => {
      const exists = current.includes(featureId);
      const next = exists ? current.filter((entry: string) => entry !== featureId) : [...current, featureId];
      setActiveFeatureId((currentActive: string) => {
        if (!exists) {
          return featureId;
        }
        if (currentActive && currentActive !== featureId) {
          return currentActive;
        }
        return next[next.length - 1] ?? "";
      });
      return next;
    });
    setLocalError(null);
  }

  function focusSingleFeature(featureId: string) {
    setActiveFeatureId(featureId);
    setSelectedFeatureIds((current: string[]) => (current.includes(featureId) ? current : [...current, featureId]));
    setLocalError(null);
  }

  async function handleCreate() {
    if (!lookupData) {
      return;
    }
    if (!selectedFeature && !validatedName.trim()) {
      setLocalError("Sélectionne un objet IGN sur la carte ou saisis un nom manuel avant de créer le bâtiment.");
      return;
    }
    setLocalError(null);
    await onCreate({
      validatedName: validatedName.trim() || undefined,
      selectedFeature,
    });
  }

  if (!lookupData) {
    return (
      <div className="empty-state buildings-empty-workspace">
        <strong>{emptyTitle}</strong>
        <span>{emptyDescription}</span>
      </div>
    );
  }

  return (
    <div className="section-block">
      <div className="section-heading">
        <h3>Rapprochement IGN</h3>
        <p>
          Inspecte les candidats IGN pour l’adresse sélectionnée, puis valide le nom de bâtiment à conserver dans la
          base PatrimoineOp.
        </p>
      </div>

      <div className="detail-grid">
        <div className="detail-card">
          <span>Adresse source</span>
          <strong>{lookupData.input_address}</strong>
        </div>
        <div className="detail-card">
          <span>Source de centrage</span>
          <strong>{lookupData.used_source}</strong>
        </div>
        <div className="detail-card">
          <span>Parcelles détectées</span>
          <strong>{lookupData.parcel_labels.join(", ") || "Aucune parcelle retrouvée"}</strong>
        </div>
        <div className="detail-card">
          <span>Adresse de géocodage</span>
          <strong>{String(lookupData.geocoder.display_name ?? lookupData.input_address)}</strong>
        </div>
      </div>

      <BuildingNamingMap
        addressLabel={lookupData.input_address}
        lat={lookupData.lat}
        lon={lookupData.lon}
        usedSource={lookupData.used_source}
        parcelFeatureCollection={lookupData.parcel_feature_collection}
        featureCollection={lookupData.feature_collection}
        selectedFeatureIds={selectedFeatureIds}
        onToggleFeatureId={toggleFeatureSelection}
      />

      <label className="field">
        <span>Bâtiment IGN actif</span>
        <select value={activeOrLastSelectedFeatureId} onChange={(event: ChangeEvent<HTMLSelectElement>) => focusSingleFeature(event.target.value)}>
          <option value="">Aucun objet IGN retenu</option>
          {candidateFeatures.map((feature: GeoJsonFeature) => {
            const properties = feature.properties ?? {};
            const featureId = String(properties.ign_id ?? properties.id ?? "");
            const label = String(properties.resolved_label ?? properties.label ?? properties.name ?? "Objet IGN");
            const source = String(properties.resolved_name_source ?? properties.ign_layer ?? "IGN");
            return (
              <option key={featureId} value={featureId}>
                {selectedFeatureIds.includes(featureId) ? "✓ " : ""}
                {label} — {source}
              </option>
            );
          })}
        </select>
      </label>

      <div className="info-banner">
        <strong>Sélection carte :</strong> {selectedFeatureIds.length} bâtiment(s) IGN sélectionné(s). Clique un bâtiment
        pour l’ajouter, reclique dessus pour le retirer, sans perdre les autres.
      </div>

      {selectedFeatureIds.length > 0 ? (
        <div className="candidate-list">
          {selectedFeatureIds.map((featureId: string) => {
            const feature = candidateFeatures.find((entry: GeoJsonFeature) => {
              const properties = entry.properties ?? {};
              return String(properties.ign_id ?? properties.id ?? "") === featureId;
            }) ?? null;
            if (!feature) {
              return null;
            }
            const properties = feature.properties ?? {};
            const label = String(properties.resolved_label ?? properties.label ?? properties.name ?? "Objet IGN");
            const isActive = featureId === activeOrLastSelectedFeatureId;
            return (
              <article key={featureId} className={`candidate-card ${isActive ? "candidate-card-active" : ""}`}>
                <strong>{label}</strong>
                <span>{String(properties.resolved_name_source ?? properties.ign_layer ?? "IGN")}</span>
                <div className="resource-card-actions candidate-card-actions">
                  <button type="button" className="secondary-button" onClick={() => focusSingleFeature(featureId)}>
                    {isActive ? "Bâtiment actif" : "Afficher les détails"}
                  </button>
                  <button type="button" className="secondary-button" onClick={() => toggleFeatureSelection(featureId)}>
                    Retirer de la sélection
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      ) : null}

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
                    "Nom du bâtiment",
                )
              : "Nom saisi manuellement ou laissé vide pour reprendre la proposition IGN"
          }
          onChange={(event: ChangeEvent<HTMLInputElement>) => setValidatedName(event.target.value)}
        />
      </label>

      <div className="form-actions">
        <button
          type="button"
          className="secondary-button"
          onClick={() => {
            setSelectedFeatureIds([]);
            setActiveFeatureId("");
            setLocalError(null);
          }}
        >
          Aucun objet bâti retenu
        </button>
      </div>

      {selectedFeature ? (
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
      ) : null}

      {displayedToponymyCandidates.length > 0 ? (
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
                  setLocalError(
                    selectedFeature
                      ? null
                      : `Toponymie sélectionnée : ${pickedName}. Clique aussi un bâtiment si tu veux le lier précisément à un objet IGN.`,
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
      ) : null}

      {selectedFeatureAttributes.length > 0 ? (
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
      ) : null}

      {localError || error ? <p className="error-text">{localError ?? error}</p> : null}
      {success ? <p className="success-text">{success}</p> : null}

      <div className="form-actions">
        <button type="button" onClick={() => void handleCreate()} disabled={createPending}>
          {createPending
            ? "Création..."
            : selectedFeature
              ? createLabelWithSelection
              : createLabelWithoutSelection}
        </button>
      </div>
    </div>
  );
}
