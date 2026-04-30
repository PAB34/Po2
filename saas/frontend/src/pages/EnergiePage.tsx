import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { fetchEnergieOverview, fetchSyncStatus, startSync, PrmListItem, SupplierDistributionItem, SyncStatus } from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

const SUPPLIER_COLORS = ["#2563eb", "#f97316", "#16a34a", "#a855f7", "#06b6d4", "#eab308", "#ec4899"];

function SyncPanel({ token }: { token: string }) {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState(false);

  const { data: syncStatus, refetch } = useQuery({
    queryKey: ["sync-status"],
    queryFn: () => fetchSyncStatus(token),
    refetchInterval: (query) => {
      const s = query.state.data as SyncStatus | undefined;
      return s?.status === "running" ? 2000 : false;
    },
  });

  const startMutation = useMutation({
    mutationFn: (historyDays?: number) => startSync(token, historyDays),
    onSuccess: () => {
      setTimeout(() => refetch(), 500);
    },
  });

  const isRunning = syncStatus?.status === "running";
  const progress = syncStatus && syncStatus.prms_total > 0
    ? Math.round((syncStatus.prms_done / syncStatus.prms_total) * 100)
    : null;

  const statusLabel: Record<string, string> = {
    idle: "En attente",
    running: "En cours…",
    success: "Succès",
    error: "Erreur",
  };

  const statusClass: Record<string, string> = {
    idle: "badge-gray",
    running: "badge-blue",
    success: "badge-green",
    error: "badge-red",
  };

  return (
    <div className="sync-panel">
      <div className="sync-panel-header" onClick={() => setExpanded((v) => !v)}>
        <span className="sync-panel-title">Synchronisation ENEDIS</span>
        <div className="sync-panel-meta">
          {syncStatus && (
            <span className={`badge ${statusClass[syncStatus.status] ?? "badge-gray"}`}>
              {statusLabel[syncStatus.status] ?? syncStatus.status}
            </span>
          )}
          {syncStatus?.last_sync_date && (
            <span className="sync-last-date">Dernière sync : {syncStatus.last_sync_date}</span>
          )}
          <span className="sync-toggle">{expanded ? "▲" : "▼"}</span>
        </div>
      </div>

      {expanded && (
        <div className="sync-panel-body">
          {isRunning && progress !== null && (
            <div className="sync-progress-row">
              <div className="sync-progress-bar">
                <div className="sync-progress-fill" style={{ width: `${progress}%` }} />
              </div>
              <span className="sync-progress-label">
                {syncStatus!.prms_done}/{syncStatus!.prms_total} PRMs ({progress}%)
                {syncStatus!.date_from && ` — ${syncStatus!.date_from} → ${syncStatus!.date_to}`}
              </span>
            </div>
          )}

          {syncStatus?.status === "success" && syncStatus.rows_added > 0 && (
            <p className="sync-result-ok">
              {syncStatus.rows_added.toLocaleString("fr-FR")} nouvelles lignes intégrées
              ({syncStatus.date_from} → {syncStatus.date_to})
            </p>
          )}

          {syncStatus?.error && (
            <p className="sync-error">{syncStatus.error}</p>
          )}

          <div className="sync-actions">
            <button
              type="button"
              className="btn-primary"
              disabled={isRunning || startMutation.isPending}
              onClick={() => startMutation.mutate(undefined)}
            >
              {isRunning ? "Synchronisation en cours…" : "Lancer la sync (incrémentale)"}
            </button>
            <button
              type="button"
              className="btn-secondary"
              disabled={isRunning || startMutation.isPending}
              onClick={() => startMutation.mutate(1095)}
              title="Backfill complet sur 3 ans"
            >
              Backfill 3 ans
            </button>
          </div>

          {syncStatus?.log && syncStatus.log.length > 0 && (
            <pre className="sync-log">
              {syncStatus.log.slice(-20).join("\n")}
            </pre>
          )}
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
      <div className="page-header">
        <h2>Énergie</h2>
        <p className="page-subtitle">Électricité ENEDIS — Points de livraison (PRMs)</p>
      </div>

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
