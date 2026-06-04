import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../providers/AuthProvider";
import {
  applyCvcImportSiteMappings,
  fetchBuildings,
  fetchCvcImportBatches,
  fetchCvcImportSiteMatches,
  fetchSites,
  type Building,
  type CvcImportBatchSummary,
  type CvcImportSiteMatchResult,
  type CvcSiteMappingPayload,
  type Site,
} from "../lib/api";

const SUBTLE_TEXT = "#94a3b8";
const NEUTRAL_BORDER = "rgba(148, 163, 184, 0.25)";

type DraftMapping = {
  site_id: number | null;
  building_id: number | null;
};

function compactLabel(parts: Array<string | null | undefined>): string {
  return parts.filter(Boolean).join(" - ");
}

function selectStyle() {
  return {
    width: "100%",
    minWidth: 0,
    padding: "8px 10px",
    borderRadius: 6,
    border: `1px solid ${NEUTRAL_BORDER}`,
    background: "rgba(15,23,42,0.9)",
    color: "#e2e8f0",
    fontSize: "0.82rem",
  };
}

function suggestedMapping(match: CvcImportSiteMatchResult): DraftMapping {
  return {
    site_id: match.current_site_id ?? match.auto_site_id,
    building_id: match.current_building_id ?? match.auto_building_id,
  };
}

function MappingRow({
  match,
  sites,
  buildings,
  value,
  onChange,
}: {
  match: CvcImportSiteMatchResult;
  sites: Site[];
  buildings: Building[];
  value: DraftMapping;
  onChange: (value: DraftMapping) => void;
}) {
  const filteredBuildings = buildings.filter((building) => !value.site_id || building.site_id === value.site_id);
  const bestSite = match.site_suggestions[0];
  const bestBuilding = match.building_suggestions[0];
  const isAuto = !match.current_site_id && (match.auto_site_id || match.auto_building_id);

  return (
    <tr>
      <td>
        <strong>{match.site_raw}</strong>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.74rem" }}>{match.item_count} ligne(s) inventaire</div>
      </td>
      <td>
        {bestSite ? (
          <>
            <strong>{bestSite.nom_site}</strong>
            <div style={{ color: SUBTLE_TEXT, fontSize: "0.74rem" }}>
              Score {Math.round(bestSite.score * 100)}% {bestSite.adresse ? `- ${bestSite.adresse}` : ""}
            </div>
          </>
        ) : (
          <span style={{ color: SUBTLE_TEXT }}>Aucune suggestion site</span>
        )}
      </td>
      <td>
        {bestBuilding ? (
          <>
            <strong>{bestBuilding.nom_batiment ?? `Batiment #${bestBuilding.building_id}`}</strong>
            <div style={{ color: SUBTLE_TEXT, fontSize: "0.74rem" }}>
              Score {Math.round(bestBuilding.score * 100)}% {bestBuilding.adresse ? `- ${bestBuilding.adresse}` : ""}
            </div>
          </>
        ) : (
          <span style={{ color: SUBTLE_TEXT }}>Aucune suggestion batiment</span>
        )}
      </td>
      <td>
        <select
          value={value.site_id ?? ""}
          onChange={(e) => {
            const site_id = e.target.value ? Number(e.target.value) : null;
            onChange({ site_id, building_id: null });
          }}
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
              site_id: building?.site_id ?? value.site_id,
              building_id: e.target.value ? Number(e.target.value) : null,
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
        {match.current_building_id || match.current_site_id ? (
          <span className="success-text">Deja rattache</span>
        ) : isAuto ? (
          <span style={{ color: "#7dd3fc" }}>Preselection</span>
        ) : (
          <span style={{ color: SUBTLE_TEXT }}>A traiter</span>
        )}
      </td>
    </tr>
  );
}

export function CvcSiteMappingPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeBatch, setActiveBatch] = useState(searchParams.get("batch") ?? "");
  const [drafts, setDrafts] = useState<Record<string, DraftMapping>>({});
  const [error, setError] = useState<string | null>(null);

  const batchesQuery = useQuery<CvcImportBatchSummary[]>({
    queryKey: ["cvc-import-batches", token],
    queryFn: () => fetchCvcImportBatches(token ?? ""),
    enabled: !!token,
  });
  const matchesQuery = useQuery({
    queryKey: ["cvc-import-site-matches", token, activeBatch],
    queryFn: () => fetchCvcImportSiteMatches(token ?? "", activeBatch),
    enabled: !!token && !!activeBatch,
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

  const matches = useMemo(() => matchesQuery.data?.matches ?? [], [matchesQuery.data]);

  useEffect(() => {
    const next: Record<string, DraftMapping> = {};
    for (const match of matches) {
      next[match.site_raw] = suggestedMapping(match);
    }
    setDrafts(next);
  }, [matches]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!token || !activeBatch) throw new Error("Choisis un import.");
      const mappings: CvcSiteMappingPayload[] = matches.map((match) => ({
        site_raw: match.site_raw,
        site_id: drafts[match.site_raw]?.site_id ?? null,
        building_id: drafts[match.site_raw]?.building_id ?? null,
      }));
      return applyCvcImportSiteMappings(token, activeBatch, mappings);
    },
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["cvc-import-site-matches"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-import-items"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-import-batches"] });
      queryClient.invalidateQueries({ queryKey: ["cvc-terrain"] });
    },
    onError: (e: unknown) => setError(e instanceof Error ? e.message : "Erreur pendant l'application du mapping."),
  });

  const stats = useMemo(() => {
    const clearlyMatched = matches.filter((match) => match.auto_site_id || match.auto_building_id).length;
    const selected = Object.values(drafts).filter((draft) => draft.site_id || draft.building_id).length;
    return { clearlyMatched, selected };
  }, [drafts, matches]);

  if (!token) {
    return (
      <section className="panel stack-lg">
        <h2>Matching sites CVC</h2>
        <p>Connecte-toi pour acceder a cette page.</p>
      </section>
    );
  }

  return (
    <section className="panel stack-lg cvc-workspace-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Gestion technique</p>
          <h2>Matching sites CVC</h2>
          <p>Rapproche les sites du fichier importe avec les sites et batiments du patrimoine.</p>
        </div>
        <div className="buildings-header-actions">
          <Link className="secondary-link" to="/buildings/cvc-import">Retour inventaire</Link>
        </div>
      </div>

      {error && (
        <div style={{ padding: "10px 14px", background: "rgba(220,38,38,0.15)", border: "1px solid rgba(220,38,38,0.4)", borderRadius: 8, color: "#fca5a5" }}>
          {error}
        </div>
      )}

      <div className="section-block">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <select
            value={activeBatch}
            onChange={(e) => {
              setActiveBatch(e.target.value);
              setSearchParams(e.target.value ? { batch: e.target.value } : {});
            }}
            style={{ ...selectStyle(), maxWidth: 460 }}
          >
            <option value="">Choisir un import</option>
            {(batchesQuery.data ?? []).map((batch) => (
              <option key={batch.import_batch} value={batch.import_batch}>
                {batch.import_batch} - {batch.imported} lignes - {batch.mapped_items} rattachees
              </option>
            ))}
          </select>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button type="button" className="secondary-button" onClick={() => matchesQuery.refetch()} disabled={!activeBatch || matchesQuery.isFetching}>
              Rafraichir
            </button>
            <button type="button" className="primary-button" onClick={() => saveMutation.mutate()} disabled={!activeBatch || saveMutation.isPending}>
              {saveMutation.isPending ? "Application..." : "Appliquer le matching"}
            </button>
          </div>
        </div>
      </div>

      {activeBatch && (
        <div className="section-block">
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {[
              ["Sites source", matches.length],
              ["Matchs evidents", stats.clearlyMatched],
              ["Selections", stats.selected],
            ].map(([label, value]) => (
              <div key={label} style={{ padding: "10px 14px", border: `1px solid ${NEUTRAL_BORDER}`, borderRadius: 8, background: "rgba(15,23,42,0.35)" }}>
                <div style={{ color: "#e2e8f0", fontWeight: 700 }}>{value}</div>
                <div style={{ color: SUBTLE_TEXT, fontSize: "0.74rem" }}>{label}</div>
              </div>
            ))}
          </div>

          {matchesQuery.isLoading && <p>Chargement des correspondances...</p>}
          {!matchesQuery.isLoading && matches.length === 0 && <p>Aucun site source trouve pour cet import.</p>}
          {matches.length > 0 && (
            <div className="table-wrapper cvc-table-wrapper">
              <table className="data-table cvc-site-mapping-table">
                <thead>
                  <tr>
                    <th>Site source</th>
                    <th>Suggestion site</th>
                    <th>Suggestion batiment</th>
                    <th>Site retenu</th>
                    <th>Batiment retenu</th>
                    <th>Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {matches.map((match) => (
                    <MappingRow
                      key={match.site_raw}
                      match={match}
                      sites={sitesQuery.data ?? []}
                      buildings={buildingsQuery.data ?? []}
                      value={drafts[match.site_raw] ?? suggestedMapping(match)}
                      onChange={(value) => setDrafts((current) => ({ ...current, [match.site_raw]: value }))}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
