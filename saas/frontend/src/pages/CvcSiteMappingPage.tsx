import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../providers/AuthProvider";
import {
  applyCvcImportSiteMappings,
  fetchBuildings,
  fetchCvcImportBatches,
  fetchCvcImportSiteMatches,
  type Building,
  type CvcImportBatchSummary,
  type CvcImportSiteMatchResult,
  type CvcSiteMappingPayload,
} from "../lib/api";

const SUBTLE_TEXT = "#94a3b8";
const NEUTRAL_BORDER = "rgba(148, 163, 184, 0.25)";

type DraftMapping = {
  site_id: number | null;
  building_id: number | null;
  building_ids: number[];
  create_building?: boolean;
  create_building_name?: string | null;
};

function searchText(value: string | null | undefined): string {
  return (value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function suggestedMapping(match: CvcImportSiteMatchResult): DraftMapping {
  const buildingIds =
    match.current_building_ids.length > 0
      ? match.current_building_ids
      : match.auto_building_id
        ? [match.auto_building_id]
        : [];
  const buildingId = buildingIds.length === 1 ? buildingIds[0] : null;
  return {
    site_id: match.current_site_id ?? (buildingId ? match.auto_site_id : null),
    building_id: buildingId,
    building_ids: buildingIds,
    create_building: false,
    create_building_name: null,
  };
}

function suggestedCreatedBuildingName(sourceName: string): string {
  const parts = sourceName
    .split(/\s+\+\s+/)
    .map((part) => part.trim())
    .filter(Boolean);
  return parts.length > 1 ? parts[parts.length - 1] : sourceName.trim();
}

type SearchableOption = {
  value: string;
  label: string;
  helper?: string | null;
};

function buildingOptions(buildings: Building[], options?: { includeCreate?: boolean }): SearchableOption[] {
  return [
    { value: "", label: "Aucun batiment", helper: "Ne pas rattacher" },
    ...(options?.includeCreate
      ? [{ value: "__create__", label: "Ajouter ce batiment a la liste patrimoniale", helper: "Creation sans site, a qualifier ensuite" }]
      : []),
    ...buildings.map((building) => ({
      value: String(building.id),
      label: building.nom_batiment ?? `Batiment #${building.id}`,
      helper: building.adresse_reconstituee,
    })),
  ];
}

function buildingOnlyOptions(buildings: Building[]): SearchableOption[] {
  return buildings.map((building) => ({
    value: String(building.id),
    label: building.nom_batiment ?? `Batiment #${building.id}`,
    helper: building.adresse_reconstituee,
  }));
}

function SearchableDropdown({
  value,
  options,
  placeholder,
  searchPlaceholder,
  onChange,
}: {
  value: string;
  options: SearchableOption[];
  placeholder: string;
  searchPlaceholder: string;
  onChange: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const selected = options.find((option) => option.value === value);
  const normalizedQuery = searchText(query);
  const visibleOptions = options.filter((option) => {
    if (!normalizedQuery) return true;
    return searchText(`${option.label} ${option.helper ?? ""}`).includes(normalizedQuery);
  });

  return (
    <div className="cvc-combobox">
      <input
        type="search"
        value={open ? query : selected?.label ?? ""}
        onFocus={() => {
          setOpen(true);
          setQuery("");
        }}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onBlur={() => window.setTimeout(() => setOpen(false), 120)}
        placeholder={selected ? searchPlaceholder : placeholder}
      />
      {open && (
        <div className="cvc-combobox-menu">
          {visibleOptions.length === 0 && <span>Aucun resultat</span>}
          {visibleOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                onChange(option.value);
                setQuery("");
                setOpen(false);
              }}
            >
              <strong>{option.label}</strong>
              {option.helper && <small>{option.helper}</small>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function SearchableMultiDropdown({
  values,
  options,
  placeholder,
  searchPlaceholder,
  onChange,
}: {
  values: string[];
  options: SearchableOption[];
  placeholder: string;
  searchPlaceholder: string;
  onChange: (values: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const normalizedQuery = searchText(query);
  const selectedOptions = values
    .map((value) => options.find((option) => option.value === value))
    .filter((option): option is SearchableOption => Boolean(option));
  const visibleOptions = options.filter((option) => {
    if (!normalizedQuery) return true;
    return searchText(`${option.label} ${option.helper ?? ""}`).includes(normalizedQuery);
  });

  const toggle = (selectedValue: string) => {
    onChange(
      values.includes(selectedValue)
        ? values.filter((value) => value !== selectedValue)
        : [...values, selectedValue],
    );
    setQuery("");
    setOpen(true);
  };

  return (
    <div className="cvc-combobox cvc-multi-combobox">
      <div className="cvc-selected-chips">
        {selectedOptions.length === 0 && <span>{placeholder}</span>}
        {selectedOptions.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(values.filter((value) => value !== option.value))}
          >
            {option.label} x
          </button>
        ))}
      </div>
      <input
        type="search"
        value={query}
        onFocus={() => setOpen(true)}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onBlur={() => window.setTimeout(() => setOpen(false), 120)}
        placeholder={searchPlaceholder}
      />
      {open && (
        <div className="cvc-combobox-menu">
          {visibleOptions.length === 0 && <span>Aucun resultat</span>}
          {visibleOptions.map((option) => {
            const selected = values.includes(option.value);
            return (
              <button
                key={option.value}
                type="button"
                className={selected ? "is-selected" : undefined}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => toggle(option.value)}
              >
                <strong>{selected ? "[x] " : ""}{option.label}</strong>
                {option.helper && <small>{option.helper}</small>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function MappingRow({
  match,
  buildings,
  value,
  onChange,
}: {
  match: CvcImportSiteMatchResult;
  buildings: Building[];
  value: DraftMapping;
  onChange: (value: DraftMapping) => void;
}) {
  const singleOptions = buildingOptions(buildings, { includeCreate: true });
  const multiOptions = buildingOnlyOptions(buildings);
  const bestBuilding = match.building_suggestions[0];
  const isAuto = value.building_ids.length === 0 && !match.current_building_id && match.auto_building_id;
  const selectedBuildingCount = value.building_ids.length;

  return (
    <tr>
      <td>
        <strong>{match.site_raw}</strong>
        <div style={{ color: SUBTLE_TEXT, fontSize: "0.74rem" }}>{match.item_count} ligne(s) inventaire</div>
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
        <SearchableMultiDropdown
          values={value.building_ids.map(String)}
          options={multiOptions}
          placeholder="Choisir un ou plusieurs batiments"
          searchPlaceholder="Rechercher et ajouter un batiment"
          onChange={(selectedValues) => {
            const buildingIds = selectedValues.map(Number).filter((id) => Number.isFinite(id));
            const selectedBuildings = buildingIds
              .map((id) => buildings.find((item) => item.id === id))
              .filter((building): building is Building => Boolean(building));
            const selectedSiteIds = Array.from(
              new Set(selectedBuildings.map((building) => building.site_id).filter((siteId): siteId is number => siteId !== null)),
            );
            onChange({
              site_id: selectedSiteIds.length === 1 ? selectedSiteIds[0] : null,
              building_id: buildingIds.length === 1 ? buildingIds[0] : null,
              building_ids: buildingIds,
              create_building: false,
            });
          }}
        />
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8, flexWrap: "wrap" }}>
          <span style={{ color: SUBTLE_TEXT, fontSize: "0.72rem" }}>
            {selectedBuildingCount > 1
              ? `${selectedBuildingCount} batiments retenus pour cette source`
              : "Cas simple : un batiment retenu alimente les equipements"}
          </span>
        </div>
        <SearchableDropdown
          value={value.create_building ? "__create__" : ""}
          options={singleOptions.filter((option) => option.value === "" || option.value === "__create__")}
          placeholder="Option speciale"
          searchPlaceholder="Ajouter si absent du patrimoine"
          onChange={(selectedValue) => {
            if (selectedValue === "__create__") {
              onChange({
                ...value,
                create_building: true,
                create_building_name: value.create_building_name ?? suggestedCreatedBuildingName(match.site_raw),
              });
              return;
            }
            onChange({
              ...value,
              create_building: false,
              create_building_name: null,
            });
          }}
        />
        {value.create_building && (
          <div className="cvc-create-building-inline">
            <label>
              Nom du batiment a creer
              <input
                type="text"
                value={value.create_building_name ?? ""}
                onChange={(e) => onChange({ ...value, create_building_name: e.target.value })}
                placeholder="Restaurant scolaire"
              />
            </label>
            <button
              type="button"
              className="secondary-button"
              onClick={() => onChange({ ...value, create_building: false, create_building_name: null })}
            >
              Annuler
            </button>
          </div>
        )}
      </td>
      <td>
        {value.create_building ? (
          <span style={{ color: "#fbbf24" }}>Ajout + rattachement</span>
        ) : value.building_ids.length > 1 ? (
          <span className="success-text">Multi-batiment</span>
        ) : match.current_building_id ? (
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
  const [activeBatch, setActiveBatch] = useState("");
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
  const buildingsQuery = useQuery<Building[]>({
    queryKey: ["buildings", token],
    queryFn: () => fetchBuildings(token ?? ""),
    enabled: !!token,
    staleTime: 0,
  });

  const matches = useMemo(() => matchesQuery.data?.matches ?? [], [matchesQuery.data]);
  const latestBatch = batchesQuery.data?.[0] ?? null;

  useEffect(() => {
    const batch = batchesQuery.data?.[0]?.import_batch ?? "";
    setActiveBatch((current) => (current === batch ? current : batch));
  }, [batchesQuery.data]);

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
        building_ids: drafts[match.site_raw]?.building_ids ?? [],
        create_building: drafts[match.site_raw]?.create_building ?? false,
        create_building_name: drafts[match.site_raw]?.create_building_name ?? null,
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
    const selected = Object.values(drafts).filter((draft) => draft.site_id || draft.building_ids.length > 0 || draft.create_building).length;
    return { clearlyMatched, selected };
  }, [drafts, matches]);

  if (!token) {
    return (
      <section className="panel stack-lg">
        <h2>Matching b&acirc;timent CVC</h2>
        <p>Connecte-toi pour acceder a cette page.</p>
      </section>
    );
  }

  return (
    <section className="panel stack-lg cvc-workspace-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Gestion technique</p>
          <h2>Matching b&acirc;timent CVC</h2>
          <p>Rapproche les batiments du fichier importe avec les batiments du patrimoine.</p>
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
          <div>
            <h3>Inventaire courant</h3>
            <p style={{ color: SUBTLE_TEXT, fontSize: "0.84rem" }}>
              {latestBatch
                ? `${latestBatch.import_batch} - ${latestBatch.imported} lignes - ${latestBatch.mapped_items} rattachees`
                : "Aucun inventaire CVC terrain enregistre."}
            </p>
          </div>
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
              ["Batiments source", matches.length],
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
          {!matchesQuery.isLoading && matches.length === 0 && <p>Aucun batiment source trouve pour cet import.</p>}
          {matches.length > 0 && (
            <div className="table-wrapper cvc-table-wrapper">
              <table className="data-table cvc-site-mapping-table">
                <thead>
                  <tr>
                    <th>Batiment source</th>
                    <th>Suggestion batiment</th>
                    <th>Batiment retenu</th>
                    <th>Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {matches.map((match) => (
                    <MappingRow
                      key={match.site_raw}
                      match={match}
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
