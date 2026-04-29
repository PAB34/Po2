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

export function EnergiePage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["energie-overview"],
    queryFn: () => fetchEnergieOverview(token!),
    enabled: !!token,
  });

  const filtered: PrmListItem[] = (data?.prms ?? []).filter((prm) => {
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
          </div>

          <div className="list-toolbar">
            <input
              type="search"
              placeholder="Rechercher par nom, PRM, adresse…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="search-input"
            />
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
                  <th>kVA</th>
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
                    <td className="cell-number">{prm.subscribed_power_kva ?? "—"}</td>
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
                    <td colSpan={7} className="cell-empty">Aucun résultat</td>
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
