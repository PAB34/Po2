import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../providers/AuthProvider";
import {
  applyMeterMappings,
  fetchBuildings,
  fetchMeterMatches,
  type Building,
  type MeterMatchResult,
} from "../lib/api";

const FLUID_LABEL: Record<string, string> = {
  ELECTRICITE: "Électricité",
  GAZ: "Gaz",
  EAU: "Eau",
};

const FLUID_METER_TERM: Record<string, string> = {
  ELECTRICITE: "PRM",
  GAZ: "PCE",
  EAU: "Compteur",
};

function matchKey(match: { fluid: string; meter_identifier: string }): string {
  return `${match.fluid}|${match.meter_identifier}`;
}

function buildingLabel(building: Building): string {
  const name = building.nom_batiment ?? `Bâtiment #${building.id}`;
  return building.nom_commune ? `${name} — ${building.nom_commune}` : name;
}

export default function MeterMatchingPage() {
  const { token } = useAuth();
  const qc = useQueryClient();

  const [fluidFilter, setFluidFilter] = useState<"all" | "ELECTRICITE" | "GAZ">("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "linked" | "unlinked">("all");
  const [search, setSearch] = useState("");
  const [drafts, setDrafts] = useState<Record<string, number | null>>({});
  const [flash, setFlash] = useState<string | null>(null);

  const matchesQuery = useQuery({
    queryKey: ["meter-matches"],
    queryFn: () => fetchMeterMatches(token ?? ""),
    enabled: !!token,
  });
  const buildingsQuery = useQuery({
    queryKey: ["buildings"],
    queryFn: () => fetchBuildings(token ?? ""),
    enabled: !!token,
  });

  const matches = useMemo(() => matchesQuery.data ?? [], [matchesQuery.data]);
  const buildings = useMemo(() => buildingsQuery.data ?? [], [buildingsQuery.data]);

  const buildingOptions = useMemo(
    () =>
      [...buildings]
        .sort((a, b) => buildingLabel(a).localeCompare(buildingLabel(b), "fr"))
        .map((b) => ({ id: b.id, label: buildingLabel(b) })),
    [buildings],
  );
  const buildingNameById = useMemo(() => {
    const map = new Map<number, string>();
    for (const b of buildings) map.set(b.id, buildingLabel(b));
    return map;
  }, [buildings]);

  // Initialise les brouillons (current ?? suggestion) sans ecraser les choix en cours.
  useEffect(() => {
    if (matches.length === 0) return;
    setDrafts((prev) => {
      const next = { ...prev };
      for (const m of matches) {
        const key = matchKey(m);
        if (!(key in next)) {
          next[key] = m.current_building_id ?? m.auto_building_id ?? null;
        }
      }
      return next;
    });
  }, [matches]);

  const applyMut = useMutation({
    mutationFn: (payload: { fluid: string; meter_identifier: string; building_id: number | null }[]) =>
      applyMeterMappings(token ?? "", payload),
    onSuccess: (res) => {
      setFlash(`Rattachements appliqués : ${res.applied} compteur(s)${res.updated ? `, ${res.updated} déplacé(s)` : ""}.`);
      qc.invalidateQueries({ queryKey: ["meter-matches"] });
      qc.invalidateQueries({ queryKey: ["buildings"] });
    },
    onError: (e) => setFlash(`Erreur : ${(e as Error).message}`),
  });

  const normalizedSearch = search.trim().toLowerCase();
  const filtered = useMemo(
    () =>
      matches.filter((m) => {
        if (fluidFilter !== "all" && m.fluid !== fluidFilter) return false;
        const linked = m.current_building_id != null;
        if (statusFilter === "linked" && !linked) return false;
        if (statusFilter === "unlinked" && linked) return false;
        if (normalizedSearch) {
          const hay = `${m.meter_identifier} ${m.label ?? ""} ${m.address ?? ""}`.toLowerCase();
          if (!hay.includes(normalizedSearch)) return false;
        }
        return true;
      }),
    [matches, fluidFilter, statusFilter, normalizedSearch],
  );

  const stats = useMemo(() => {
    const total = matches.length;
    const linked = matches.filter((m) => m.current_building_id != null).length;
    const suggested = matches.filter((m) => m.current_building_id == null && m.auto_building_id != null).length;
    return { total, linked, unlinked: total - linked, suggested };
  }, [matches]);

  // Lignes dont le brouillon differe du lien actuel et pointe vers un batiment.
  const pendingChanges = useMemo(
    () =>
      filtered.filter((m) => {
        const draft = drafts[matchKey(m)];
        return draft != null && draft !== m.current_building_id;
      }),
    [filtered, drafts],
  );

  function applyChanges(rows: MeterMatchResult[]) {
    const payload = rows
      .map((m) => ({ fluid: m.fluid, meter_identifier: m.meter_identifier, building_id: drafts[matchKey(m)] ?? null }))
      .filter((p) => p.building_id != null);
    if (payload.length === 0) return;
    applyMut.mutate(payload);
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Rapprochement des compteurs</h2>
          <p className="page-subtitle">
            Rattache chaque compteur d'énergie (PRM électricité, PCE gaz) au bâtiment du patrimoine. Le
            rapprochement alimente la fiche bâtiment et relie consommations et factures au bon site.
          </p>
        </div>
      </div>

      <div className="kpi-row">
        <div className="kpi-card">
          <span className="kpi-label">Compteurs connus</span>
          <span className="kpi-value">{stats.total}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Rattachés</span>
          <span className="kpi-value">{stats.linked}</span>
        </div>
        <div className="kpi-card kpi-card--alert">
          <span className="kpi-label">Non rattachés</span>
          <span className="kpi-value">{stats.unlinked}</span>
        </div>
        <div className="kpi-card kpi-card--info">
          <span className="kpi-label">Suggestions auto</span>
          <span className="kpi-value">{stats.suggested}</span>
        </div>
      </div>

      <div className="invoice-control-toolbar">
        <label className="invoice-control-search">
          <span className="field-label">Recherche</span>
          <input
            type="search"
            className="form-input"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Identifiant, site, adresse..."
          />
        </label>
        <label>
          <span className="field-label">Fluide</span>
          <select className="form-input" value={fluidFilter} onChange={(e) => setFluidFilter(e.target.value as typeof fluidFilter)}>
            <option value="all">Tous</option>
            <option value="ELECTRICITE">Électricité (PRM)</option>
            <option value="GAZ">Gaz (PCE)</option>
          </select>
        </label>
        <label>
          <span className="field-label">Statut</span>
          <select className="form-input" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}>
            <option value="all">Tous</option>
            <option value="unlinked">Non rattachés</option>
            <option value="linked">Rattachés</option>
          </select>
        </label>
        <button
          type="button"
          className="btn-primary btn-compact"
          disabled={applyMut.isPending || pendingChanges.length === 0}
          onClick={() => applyChanges(pendingChanges)}
        >
          {applyMut.isPending ? "Application..." : `Appliquer (${pendingChanges.length})`}
        </button>
      </div>

      {flash && <p className="sync-result-ok">{flash}</p>}
      {matchesQuery.isLoading && <p className="loading-text">Chargement des compteurs...</p>}
      {matchesQuery.isError && <p className="error-text">{(matchesQuery.error as Error).message}</p>}

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Fluide</th>
              <th>Identifiant</th>
              <th>Site / adresse</th>
              <th>Rattachement actuel</th>
              <th>Bâtiment</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((m) => {
              const key = matchKey(m);
              const draft = drafts[key] ?? null;
              const changed = draft != null && draft !== m.current_building_id;
              const topScore = m.suggestions[0]?.score;
              return (
                <tr key={key}>
                  <td>
                    <span className="badge badge-gray">{FLUID_LABEL[m.fluid] ?? m.fluid}</span>
                    <div className="text-muted" style={{ fontSize: "0.75rem" }}>{FLUID_METER_TERM[m.fluid] ?? ""}</div>
                  </td>
                  <td><strong>{m.meter_identifier}</strong></td>
                  <td>
                    <div>{m.label ?? "-"}</div>
                    {m.address && <div className="text-muted" style={{ fontSize: "0.78rem" }}>{m.address}</div>}
                  </td>
                  <td>
                    {m.current_building_id != null ? (
                      <span className="badge badge-green">{m.current_building_name ?? buildingNameById.get(m.current_building_id) ?? `#${m.current_building_id}`}</span>
                    ) : m.auto_building_id != null ? (
                      <span className="badge badge-orange">
                        Suggéré : {buildingNameById.get(m.auto_building_id) ?? `#${m.auto_building_id}`}
                        {topScore != null ? ` (${Math.round(topScore * 100)}%)` : ""}
                      </span>
                    ) : (
                      <span className="badge badge-gray">Non rattaché</span>
                    )}
                  </td>
                  <td>
                    <select
                      className="form-input"
                      value={draft ?? ""}
                      onChange={(e) =>
                        setDrafts((prev) => ({ ...prev, [key]: e.target.value ? Number(e.target.value) : null }))
                      }
                      style={changed ? { borderColor: "rgba(59,130,246,0.7)" } : undefined}
                    >
                      <option value="">— Aucun —</option>
                      {buildingOptions.map((o) => (
                        <option key={o.id} value={o.id}>{o.label}</option>
                      ))}
                    </select>
                  </td>
                </tr>
              );
            })}
            {!matchesQuery.isLoading && filtered.length === 0 && (
              <tr>
                <td colSpan={5} className="cell-empty">Aucun compteur ne correspond aux filtres.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="invoice-step-hint" style={{ marginTop: 16 }}>
        Les compteurs proviennent des données ENEDIS (PRM) et GRDF (PCE). Le rattachement manuel fin reste
        possible depuis chaque <Link to="/buildings/list">fiche bâtiment</Link>.
      </p>
    </div>
  );
}
