import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import {
  fetchEnergieOverview, fetchSyncStatus, startSync,
  fetchMaxPowerSyncStatus, startMaxPowerSync,
  fetchLoadCurveSyncStatus, startLoadCurveSync,
  fetchDjuSyncStatus, startDjuSync,
  fetchDataRanges,
  PrmListItem, SupplierDistributionItem, SyncStatus, DjuSyncStatus, LoadCurveSyncStatus, DataRanges,
} from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

const SUPPLIER_COLORS = ["#2563eb", "#f97316", "#16a34a", "#a855f7", "#06b6d4", "#eab308", "#ec4899"];

const STATUS_LABEL: Record<string, string> = { idle: "En attente", running: "En cours…", success: "Succès", error: "Erreur" };
const STATUS_CLASS: Record<string, string> = { idle: "badge-gray", running: "badge-blue", success: "badge-green", error: "badge-red" };

function SubSyncRow({
  label,
  status,
  lastDate,
  rowsAdded,
  error,
  log,
  isRunning,
  isPending,
  progress,
  onIncremental,
  onBackfill,
}: {
  label: string;
  status: string | undefined;
  lastDate: string | null | undefined;
  rowsAdded?: number;
  error?: string | null;
  log?: string[];
  isRunning: boolean;
  isPending: boolean;
  progress?: number | null;
  onIncremental: () => void;
  onBackfill?: () => void;
}) {
  return (
    <div className="sync-sub-row">
      <div className="sync-sub-header">
        <span className="sync-sub-label">{label}</span>
        <div className="sync-panel-meta">
          {status && (
            <span className={`badge ${STATUS_CLASS[status] ?? "badge-gray"}`}>
              {STATUS_LABEL[status] ?? status}
            </span>
          )}
          {lastDate && <span className="sync-last-date">Dernière sync : {lastDate}</span>}
        </div>
      </div>
      {isRunning && progress != null && (
        <div className="sync-progress-row">
          <div className="sync-progress-bar"><div className="sync-progress-fill" style={{ width: `${progress}%` }} /></div>
          <span className="sync-progress-label">{progress}%</span>
        </div>
      )}
      {status === "success" && rowsAdded != null && rowsAdded > 0 && (
        <p className="sync-result-ok">{rowsAdded.toLocaleString("fr-FR")} nouvelles lignes intégrées</p>
      )}
      {error && <p className="sync-error">{error}</p>}
      <div className="sync-actions">
        <button type="button" className="btn-primary" disabled={isRunning || isPending} onClick={onIncremental}>
          {isRunning ? "En cours…" : "Sync incrémentale"}
        </button>
        {onBackfill && (
          <button
            type="button"
            className="btn-secondary"
            disabled={isRunning || isPending}
            onClick={() => {
              if (lastDate && !window.confirm(`Des données existent déjà (dernière sync : ${lastDate}).\n\nRelancer le backfill 3 ans va re-télécharger tout l'historique. Continuer ?`)) return;
              onBackfill();
            }}
            title="Backfill complet sur 3 ans"
          >
            Backfill 3 ans
          </button>
        )}
      </div>
      {log && log.length > 0 && (
        <pre className="sync-log">{log.slice(-10).join("\n")}</pre>
      )}
    </div>
  );
}

function SyncPanel({ token }: { token: string }) {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState(false);

  const { data: syncStatus, refetch: refetchConso } = useQuery({
    queryKey: ["sync-status"],
    queryFn: () => fetchSyncStatus(token),
    refetchInterval: (query) => (query.state.data as SyncStatus | undefined)?.status === "running" ? 2000 : false,
  });

  const { data: mpStatus, refetch: refetchMp } = useQuery({
    queryKey: ["sync-max-power-status"],
    queryFn: () => fetchMaxPowerSyncStatus(token),
    refetchInterval: (query) => (query.state.data as SyncStatus | undefined)?.status === "running" ? 2000 : false,
  });

  const { data: lcStatus, refetch: refetchLc } = useQuery({
    queryKey: ["sync-lc-status"],
    queryFn: () => fetchLoadCurveSyncStatus(token),
    refetchInterval: (query) => (query.state.data as LoadCurveSyncStatus | undefined)?.status === "running" ? 3000 : false,
  });

  const { data: djuStatus, refetch: refetchDju } = useQuery({
    queryKey: ["sync-dju-status"],
    queryFn: () => fetchDjuSyncStatus(token),
    refetchInterval: (query) => (query.state.data as DjuSyncStatus | undefined)?.status === "running" ? 2000 : false,
  });

  const consoMutation = useMutation({
    mutationFn: (historyDays?: number) => startSync(token, historyDays),
    onSuccess: () => { setTimeout(() => refetchConso(), 500); queryClient.invalidateQueries({ queryKey: ["energie-overview"] }); },
  });

  const mpMutation = useMutation({
    mutationFn: (historyDays?: number) => startMaxPowerSync(token, historyDays),
    onSuccess: () => { setTimeout(() => refetchMp(), 500); },
  });

  const lcMutation = useMutation({
    mutationFn: () => startLoadCurveSync(token),
    onSuccess: () => { setTimeout(() => refetchLc(), 500); },
  });

  const djuMutation = useMutation({
    mutationFn: () => startDjuSync(token),
    onSuccess: () => { setTimeout(() => refetchDju(), 500); },
  });

  const consoProgress = syncStatus && syncStatus.prms_total > 0
    ? Math.round((syncStatus.prms_done / syncStatus.prms_total) * 100) : null;
  const mpProgress = mpStatus && mpStatus.prms_total > 0
    ? Math.round((mpStatus.prms_done / mpStatus.prms_total) * 100) : null;
  const lcProgress = lcStatus && lcStatus.chunks_total > 0
    ? Math.round((lcStatus.chunks_done / lcStatus.chunks_total) * 100) : null;

  const anyRunning = syncStatus?.status === "running" || mpStatus?.status === "running"
    || lcStatus?.status === "running" || djuStatus?.status === "running";

  return (
    <div className="sync-panel">
      <div className="sync-panel-header" onClick={() => setExpanded((v) => !v)}>
        <span className="sync-panel-title">Synchronisation ENEDIS / DJU</span>
        <div className="sync-panel-meta">
          {anyRunning && <span className="badge badge-blue">En cours…</span>}
          <span className="sync-toggle">{expanded ? "▲" : "▼"}</span>
        </div>
      </div>

      {expanded && (
        <div className="sync-panel-body">
          <SubSyncRow
            label="Consommation journalière (kWh)"
            status={syncStatus?.status}
            lastDate={syncStatus?.last_sync_date}
            rowsAdded={syncStatus?.rows_added}
            error={syncStatus?.error}
            log={syncStatus?.log}
            isRunning={syncStatus?.status === "running"}
            isPending={consoMutation.isPending}
            progress={consoProgress}
            onIncremental={() => consoMutation.mutate(undefined)}
            onBackfill={() => consoMutation.mutate(1095)}
          />

          <SubSyncRow
            label="Puissance max journalière (VA)"
            status={mpStatus?.status}
            lastDate={mpStatus?.last_sync_date}
            rowsAdded={mpStatus?.rows_added}
            error={mpStatus?.error}
            log={mpStatus?.log}
            isRunning={mpStatus?.status === "running"}
            isPending={mpMutation.isPending}
            progress={mpProgress}
            onIncremental={() => mpMutation.mutate(undefined)}
            onBackfill={() => mpMutation.mutate(1095)}
          />

          <SubSyncRow
            label="Courbe de charge 30 min (depuis 01/01/2026)"
            status={lcStatus?.status}
            lastDate={lcStatus?.last_sync_date}
            rowsAdded={lcStatus?.rows_added}
            error={lcStatus?.error}
            log={lcStatus?.log}
            isRunning={lcStatus?.status === "running"}
            isPending={lcMutation.isPending}
            progress={lcProgress}
            onIncremental={() => lcMutation.mutate()}
          />

          <SubSyncRow
            label="DJU météo (Open-Meteo — Sète)"
            status={djuStatus?.status}
            lastDate={djuStatus?.last_sync_date}
            rowsAdded={djuStatus?.rows_added}
            error={djuStatus?.error}
            log={djuStatus?.log}
            isRunning={djuStatus?.status === "running"}
            isPending={djuMutation.isPending}
            onIncremental={() => djuMutation.mutate()}
          />
        </div>
      )}
    </div>
  );
}

function SupplierPieChart({ data }: { data: SupplierDistributionItem[] }) {
  if (data.length === 0) return null;
  const pieData = data.map((s) => ({ name: s.supplier, value: s.total_kva, count: s.prm_count }));
  return (
    <div className="supplier-pie-wrapper">
      <h3 className="supplier-pie-title">Répartition par fournisseur (kVA souscrit)</h3>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={pieData}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={80}
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
            labelLine={false}
          >
            {pieData.map((_, i) => (
              <Cell key={i} fill={SUPPLIER_COLORS[i % SUPPLIER_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number, name: string, props) => [
              `${value.toLocaleString("fr-FR")} kVA — ${(props.payload as { count: number }).count} PRM`,
              name,
            ]}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

function connectionBadge(state: string | null): string {
  if (!state) return "";
  if (state.toLowerCase().includes("non alimenté")) return "badge-red";
  if (state.toLowerCase().includes("alimenté")) return "badge-green";
  return "badge-gray";
}

function communicantBadge(level: string | null): string {
  if (!level) return "";
  if (level.toLowerCase().includes("communicant")) return "badge-blue";
  return "badge-gray";
}

type CalibStatus = "sous_dimensionne" | "proche_seuil" | "bien_calibre" | "sur_souscrit";

const CALIB_LABEL: Record<CalibStatus, string> = {
  sous_dimensionne: "Sous-dim.",
  proche_seuil: "Proche seuil",
  bien_calibre: "Bien calibré",
  sur_souscrit: "Sur-souscrit",
};

const CALIB_CLASS: Record<CalibStatus, string> = {
  sous_dimensionne: "badge-red",
  proche_seuil: "badge-orange",
  bien_calibre: "badge-green",
  sur_souscrit: "badge-blue",
};

function calibBadge(status: string | null, ratio: number | null) {
  if (!status) return null;
  const s = status as CalibStatus;
  return (
    <span className={`badge ${CALIB_CLASS[s] ?? "badge-gray"}`} title={ratio != null ? `${ratio}%` : undefined}>
      {CALIB_LABEL[s] ?? status}
    </span>
  );
}

function DataCoverageBar({ token }: { token: string }) {
  const { data } = useQuery<DataRanges>({
    queryKey: ["energie-data-ranges"],
    queryFn: () => fetchDataRanges(token),
    staleTime: 60_000,
  });

  const sources: { key: keyof Omit<DataRanges, "contracts">; label: string }[] = [
    { key: "consumption", label: "Conso. journalière" },
    { key: "max_power", label: "Puissance max" },
    { key: "load_curve", label: "Courbe de charge" },
    { key: "dju", label: "DJU météo" },
  ];

  if (!data) return null;

  return (
    <div className="data-coverage-bar">
      <span className="data-coverage-title">Couverture des données</span>
      <div className="data-coverage-sources">
        {sources.map(({ key, label }) => {
          const src = data[key];
          const hasData = src.first_date != null;
          return (
            <div key={key} className={`data-coverage-chip ${hasData ? "chip-ok" : "chip-empty"}`}>
              <span className="chip-label">{label}</span>
              {hasData ? (
                <span className="chip-dates">{src.first_date} → {src.last_date}</span>
              ) : (
                <span className="chip-dates">Aucune donnée</span>
              )}
              {src.row_count > 0 && (
                <span className="chip-count">{src.row_count.toLocaleString("fr-FR")} lignes</span>
              )}
            </div>
          );
        })}
        <div className="data-coverage-chip chip-ok">
          <span className="chip-label">Contrats</span>
          <span className="chip-dates">{data.contracts.count.toLocaleString("fr-FR")} PRMs</span>
        </div>
      </div>
    </div>
  );
}

export function EnergiePage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [calibFilter, setCalibFilter] = useState<string>("all");

  const { data, isLoading, error } = useQuery({
    queryKey: ["energie-overview"],
    queryFn: () => fetchEnergieOverview(token!),
    enabled: !!token,
  });

  const filtered: PrmListItem[] = (data?.prms ?? []).filter((prm) => {
    if (calibFilter !== "all" && prm.calibration_status !== calibFilter) return false;
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      prm.name.toLowerCase().includes(q) ||
      prm.usage_point_id.includes(q) ||
      prm.address.toLowerCase().includes(q) ||
      (prm.contractor ?? "").toLowerCase().includes(q)
    );
  });

  return (
    <div className="page">
      <div className="page-header page-header-row">
        <div>
          <h2>Énergie</h2>
          <p className="page-subtitle">Électricité ENEDIS — Points de livraison (PRMs)</p>
        </div>
        <button type="button" className="secondary-button" onClick={() => navigate("/energie/factures")}>
          Factures
        </button>
      </div>

      <DataCoverageBar token={token!} />
      <SyncPanel token={token!} />

      {isLoading && <p>Chargement…</p>}
      {error && <p className="error-text">{(error as Error).message}</p>}

      {data && (
        <>
          <div className="kpi-row">
            <div className="kpi-card">
              <span className="kpi-label">PRMs actifs</span>
              <span className="kpi-value">{data.kpis.total_prms}</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Puissance souscrite totale</span>
              <span className="kpi-value">{data.kpis.total_subscribed_kva.toLocaleString("fr-FR")} kVA</span>
            </div>
            {data.kpis.sous_dimensionnes > 0 && (
              <div className="kpi-card kpi-card--alert">
                <span className="kpi-label">Sous-dimensionnés</span>
                <span className="kpi-value">{data.kpis.sous_dimensionnes}</span>
              </div>
            )}
            {data.kpis.proche_seuil > 0 && (
              <div className="kpi-card kpi-card--warn">
                <span className="kpi-label">Proches du seuil</span>
                <span className="kpi-value">{data.kpis.proche_seuil}</span>
              </div>
            )}
            {data.kpis.sur_souscrits > 0 && (
              <div className="kpi-card kpi-card--info">
                <span className="kpi-label">Sur-souscrits</span>
                <span className="kpi-value">{data.kpis.sur_souscrits}</span>
              </div>
            )}
          </div>

          <SupplierPieChart data={data.supplier_distribution} />

          <div className="list-toolbar">
            <input
              type="search"
              placeholder="Rechercher par nom, PRM, adresse…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="search-input"
            />
            <select
              value={calibFilter}
              onChange={(e) => setCalibFilter(e.target.value)}
              className="filter-select"
            >
              <option value="all">Tous calibrages</option>
              <option value="sous_dimensionne">Sous-dimensionnés</option>
              <option value="proche_seuil">Proches du seuil</option>
              <option value="bien_calibre">Bien calibrés</option>
              <option value="sur_souscrit">Sur-souscrits</option>
            </select>
            <span className="result-count">{filtered.length} résultat{filtered.length !== 1 ? "s" : ""}</span>
          </div>

          <div className="table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Nom</th>
                  <th>PRM</th>
                  <th>Adresse</th>
                  <th>Fournisseur</th>
                  <th>Souscrit</th>
                  <th>Pic 3 ans</th>
                  <th>Calibrage</th>
                  <th>État</th>
                  <th>Communicant</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((prm) => (
                  <tr
                    key={prm.usage_point_id}
                    className="clickable-row"
                    onClick={() => navigate(`/energie/${prm.usage_point_id}`)}
                  >
                    <td className="cell-bold">{prm.name}</td>
                    <td className="cell-mono">{prm.usage_point_id}</td>
                    <td>{prm.address}</td>
                    <td>{prm.contractor}</td>
                    <td className="cell-number">{prm.subscribed_power_kva != null ? `${prm.subscribed_power_kva} kVA` : "—"}</td>
                    <td className="cell-number">{prm.peak_kva_3y != null ? `${prm.peak_kva_3y} kVA` : "—"}</td>
                    <td>{calibBadge(prm.calibration_status, prm.calibration_ratio)}</td>
                    <td>
                      {prm.connection_state && (
                        <span className={`badge ${connectionBadge(prm.connection_state)}`}>
                          {prm.connection_state}
                        </span>
                      )}
                    </td>
                    <td>
                      {prm.services_level && (
                        <span className={`badge ${communicantBadge(prm.services_level)}`}>
                          {prm.services_level.includes("Communicant") ? "Communicant" : prm.services_level}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={9} className="cell-empty">Aucun résultat</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
