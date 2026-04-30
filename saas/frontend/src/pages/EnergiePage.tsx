import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchEnergieOverview, PrmListItem } from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

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

          {data.supplier_distribution.length > 0 && (
            <div className="supplier-bar-row">
              {data.supplier_distribution.map((s) => (
                <div key={s.supplier} className="supplier-bar-item">
                  <span className="supplier-name">{s.supplier}</span>
                  <span className="supplier-stats">
                    {s.prm_count} PRM — {s.total_kva.toLocaleString("fr-FR")} kVA
                  </span>
                </div>
              ))}
            </div>
          )}

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
