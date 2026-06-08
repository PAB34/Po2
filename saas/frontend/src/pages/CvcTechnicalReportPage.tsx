import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../providers/AuthProvider";
import {
  fetchBuildings,
  fetchCvcSourceBuildingMappings,
  fetchCvcTechnicalCoverageReport,
  fetchSites,
  updateCvcSourceBuildingMapping,
  type Building,
  type CvcSourceBuildingMapping,
  type Site,
} from "../lib/api";

const SUBTLE_TEXT = "#94a3b8";
const NEUTRAL_BORDER = "rgba(148, 163, 184, 0.25)";

type DraftMapping = {
  site_id: number | null;
  building_id: number | null;
  status: string;
  notes: string;
};

function compactLabel(parts: Array<string | null | undefined>): string {
  return parts.filter(Boolean).join(" - ");
}

function selectStyle() {
  return {
    width: "100%",
    minWidth: 0,
    padding: "7px 9px",
    borderRadius: 6,
    border: `1px solid ${NEUTRAL_BORDER}`,
    background: "rgba(15,23,42,0.9)",
    color: "#e2e8f0",
    fontSize: "0.8rem",
  };
}

function sourceLabel(sourceType: string): string {
  if (sourceType === "inventory") return "Inventaire CVC";
  if (sourceType === "refrigerant") return "Fluides ESP";
  return sourceType;
}

function draftFromMapping(mapping: CvcSourceBuildingMapping): DraftMapping {
  return {
    site_id: mapping.site_id,
    building_id: mapping.building_id,
    status: mapping.status,
    notes: mapping.notes ?? "",
  };
}

function MappingRow({
  mapping,
  sites,
  buildings,
  value,
  saving,
  onChange,
  onSave,
}: {
  mapping: CvcSourceBuildingMapping;
  sites: Site[];
  buildings: Building[];
  value: DraftMapping;
  saving: boolean;
  onChange: (value: DraftMapping) => void;
  onSave: () => void;
}) {
  const filteredBuildings = buildings.filter((building) => !value.site_id || building.site_id === value.site_id);
  const bestSite = mapping.site_suggestions[0];
  const bestBuilding = mapping.building_suggestions[0];

  return (
    <tr>
      <td>
        <strong>{mapping.source_site_raw}</strong>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
          {sourceLabel(mapping.source_type)} | {mapping.import_batch}
        </div>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
          {mapping.item_count} eq. CVC | {mapping.refrigerant_count} ligne(s) ESP
        </div>
      </td>
      <td>
        {bestBuilding ? (
          <>
            <strong>{bestBuilding.nom_batiment ?? `Batiment #${bestBuilding.building_id}`}</strong>
            <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
              {Math.round(bestBuilding.score * 100)}% {bestBuilding.adresse ? `| ${bestBuilding.adresse}` : ""}
            </div>
          </>
        ) : bestSite ? (
          <>
            <strong>{bestSite.nom_site}</strong>
            <div style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
              {Math.round(bestSite.score * 100)}% {bestSite.adresse ? `| ${bestSite.adresse}` : ""}
            </div>
          </>
        ) : (
          <span style={{ color: SUBTLE_TEXT }}>Aucune suggestion</span>
        )}
      </td>
      <td>
        <select
          value={value.site_id ?? ""}
          onChange={(e) => onChange({ ...value, site_id: e.target.value ? Number(e.target.value) : null, building_id: null })}
          style={selectStyle()}
        >
          <option value="">Aucun site</option>
          {sites.map((site) => (
            <option key={site.id} value={site.id}>
              {compactLabel([site.nom_site, site.adresse])}
            </option>
          ))}
        </select>
      </td>
      <td>
        <select
          value={value.building_id ?? ""}
          onChange={(e) => {
            const building = buildings.find((item) => item.id === Number(e.target.value));
            onChange({
              ...value,
              site_id: building?.site_id ?? value.site_id,
              building_id: e.target.value ? Number(e.target.value) : null,
              status: e.target.value ? "matched" : value.status,
            });
          }}
          style={selectStyle()}
        >
          <option value="">Aucun batiment</option>
          {filteredBuildings.map((building) => (
            <option key={building.id} value={building.id}>
              {compactLabel([building.nom_batiment ?? `Batiment #${building.id}`, building.adresse_reconstituee])}
            </option>
          ))}
        </select>
      </td>
      <td>
        <select
          value={value.status}
          onChange={(e) => onChange({ ...value, status: e.target.value })}
          style={selectStyle()}
        >
          <option value="matched">Rattache</option>
          <option value="to_review">A revoir</option>
          <option value="not_found">Introuvable patrimoine</option>
          <option value="ignored">Ignore</option>
        </select>
      </td>
      <td>
        <input
          type="text"
          value={value.notes}
          onChange={(e) => onChange({ ...value, notes: e.target.value })}
          placeholder="Note"
          style={selectStyle()}
        />
      </td>
      <td>
        <button type="button" className="secondary-button" onClick={onSave} disabled={saving}>
          {saving ? "..." : "OK"}
        </button>
      </td>
    </tr>
  );
}

export function CvcTechnicalReportPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [sourceFilter, setSourceFilter] = useState("");
  const [drafts, setDrafts] = useState<Record<number, DraftMapping>>({});
  const [error, setError] = useState<string | null>(null);

  const reportQuery = useQuery({
    queryKey: ["cvc-technical-report", token],
    queryFn: () => fetchCvcTechnicalCoverageReport(token ?? ""),
    enabled: !!token,
  });
  const mappingsQuery = useQuery({
    queryKey: ["cvc-source-building-mappings", token, sourceFilter],
    queryFn: () => fetchCvcSourceBuildingMappings(token ?? "", { sourceType: sourceFilter || undefined }),
    enabled: !!token,
  });
  const sitesQuery = useQuery<Site[]>({
    queryKey: ["sites", token],
    queryFn: () => fetchSites(token ?? ""),
    enabled: !!token,
    staleTime: 0,
  });
  const buildingsQuery = useQuery<Building[]>({
    queryKey: ["buildings", token],
    queryFn: () => fetchBuildings(token ?? ""),
    enabled: !!token,
    staleTime: 0,
  });

  const mappings = mappingsQuery.data ?? [];
  const report = reportQuery.data;
  const visibleDrafts = useMemo(() => {
    const next = { ...drafts };
    for (const mapping of mappings) {
      if (!next[mapping.id]) {
        next[mapping.id] = {
          site_id: mapping.site_id,
          building_id: mapping.building_id,
          status: mapping.status,
          notes: mapping.notes ?? "",
        };
      }
    }
    return next;
  }, [drafts, mappings]);

  const updateMutation = useMutation({
    mutationFn: ({ mapping, value }: { mapping: CvcSourceBuildingMapping; value: DraftMapping }) => {
      if (!token) throw new Error("Session expiree.");
      return updateCvcSourceBuildingMapping(token, mapping.id, {
        site_id: value.site_id,
        building_id: value.building_id,
        status: value.status,
        notes: value.notes || null,
      });
    },
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["cvc-source-building-mappings"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-technical-report"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-import-items"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-refrigerant-items"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-refrigerant-batches"] });
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Erreur pendant la sauvegarde."),
  });

  if (!token) {
    return (
      <section className="panel stack-lg">
        <h2>Rapport technique CVC</h2>
        <p>Connecte-toi pour acceder a cette page.</p>
      </section>
    );
  }

  return (
    <section className="panel stack-lg cvc-workspace-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Gestion technique</p>
          <h2>Rapport technique CVC</h2>
          <p>Controle les liaisons entre batiments source, inventaire CVC, fluides ESP et patrimoine.</p>
        </div>
        <div className="buildings-header-actions">
          <Link className="secondary-link" to="/buildings/technique">Retour a la gestion technique</Link>
        </div>
      </div>

      {error && (
        <div style={{ padding: "10px 14px", background: "rgba(220,38,38,0.15)", border: "1px solid rgba(220,38,38,0.4)", borderRadius: 8, color: "#fca5a5" }}>
          {error}
        </div>
      )}

      <div className="section-block">
        <div className="cvc-preview-grid cvc-technical-kpis">
          {[
            ["Batiments patrimoine", report?.patrimoine_buildings ?? 0],
            ["Equipements CVC", report?.cvc_inventory_items ?? 0],
            ["Lignes ESP", report?.cvc_refrigerant_items ?? 0],
            ["CVC sans batiment", report?.inventory_without_building ?? 0],
            ["ESP sans batiment", report?.refrigerants_without_building ?? 0],
            ["ESP sans equipement CVC", report?.refrigerants_without_inventory_item ?? 0],
            ["Mappings a revoir", report?.source_mappings_to_review ?? 0],
            ["Sources introuvables", report?.source_mappings_not_found ?? 0],
          ].map(([label, value]) => (
            <div key={label}>
              <strong>{value}</strong>
              <span>{label}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="section-block">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", flexWrap: "wrap", marginBottom: 12 }}>
          <div>
            <h3>Batiments source a qualifier</h3>
            <p style={{ color: SUBTLE_TEXT, fontSize: "0.86rem" }}>
              Le meme principe s'applique a l'inventaire CVC et aux fluides ESP.
            </p>
          </div>
          <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)} style={{ ...selectStyle(), maxWidth: 260 }}>
            <option value="">Toutes les sources</option>
            <option value="inventory">Inventaire CVC</option>
            <option value="refrigerant">Fluides ESP</option>
          </select>
        </div>

        {mappingsQuery.isLoading && <p>Chargement des mappings...</p>}
        {!mappingsQuery.isLoading && mappings.length === 0 && <p>Aucun batiment source trouve.</p>}
        {mappings.length > 0 && (
          <div className="table-wrapper cvc-table-wrapper">
            <table className="data-table cvc-source-mapping-table">
              <thead>
                <tr>
                  <th>Batiment source</th>
                  <th>Suggestion</th>
                  <th>Site retenu</th>
                  <th>Batiment retenu</th>
                  <th>Statut</th>
                  <th>Note</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {mappings.map((mapping) => (
                  <MappingRow
                    key={mapping.id}
                    mapping={mapping}
                    sites={sitesQuery.data ?? []}
                    buildings={buildingsQuery.data ?? []}
                    value={visibleDrafts[mapping.id] ?? draftFromMapping(mapping)}
                    saving={updateMutation.isPending && updateMutation.variables?.mapping.id === mapping.id}
                    onChange={(value) => setDrafts((current) => ({ ...current, [mapping.id]: value }))}
                    onSave={() => updateMutation.mutate({ mapping, value: visibleDrafts[mapping.id] ?? draftFromMapping(mapping) })}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
