import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchPowerRecommendations } from "../lib/api";
import type { PrmPowerRecommendation } from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

const ACTION_LABEL: Record<string, string> = {
  increase: "Hausse",
  decrease: "Baisse",
  maintain: "Maintien",
  insufficient_data: "Donnees insuff.",
};

const ACTION_CLASS: Record<string, string> = {
  increase: "badge-red",
  decrease: "badge-blue",
  maintain: "badge-green",
  insufficient_data: "badge-gray",
};

const CONFIDENCE_LABEL: Record<string, string> = {
  high: "Haute",
  medium: "Moyenne",
  low: "Faible",
  insufficient: "Insuffisante",
};

const CONFIDENCE_CLASS: Record<string, string> = {
  high: "badge-green",
  medium: "badge-orange",
  low: "badge-blue",
  insufficient: "badge-gray",
};

const RISK_LABEL: Record<string, string> = {
  low: "Risque faible",
  medium: "Risque moyen",
  high: "Risque fort",
  unknown: "Risque inconnu",
};

function formatKva(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} kVA`;
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} %`;
}

function actionBadge(item: PrmPowerRecommendation) {
  return (
    <span className={`badge ${ACTION_CLASS[item.action] ?? "badge-gray"}`}>
      {ACTION_LABEL[item.action] ?? item.action}
    </span>
  );
}

function confidenceBadge(item: PrmPowerRecommendation) {
  return (
    <span className={`badge ${CONFIDENCE_CLASS[item.confidence] ?? "badge-gray"}`}>
      {CONFIDENCE_LABEL[item.confidence] ?? item.confidence}
    </span>
  );
}

function ScenarioChips({ item }: { item: PrmPowerRecommendation }) {
  if (item.scenarios.length === 0) return <span className="muted-text">-</span>;
  return (
    <div className="scenario-chip-grid">
      {item.scenarios.map((scenario) => (
        <div key={scenario.key} className={`scenario-chip ${scenario.is_recommended ? "scenario-chip--active" : ""}`}>
          <strong>{scenario.label}</strong>
          <span>{formatKva(scenario.target_power_kva)}</span>
          <small>{RISK_LABEL[scenario.risk] ?? scenario.risk}</small>
        </div>
      ))}
    </div>
  );
}

export function EnergieRecommendationsPage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("all");
  const [confidenceFilter, setConfidenceFilter] = useState("all");

  const recommendationsQuery = useQuery({
    queryKey: ["power-recommendations"],
    queryFn: () => fetchPowerRecommendations(token!),
    enabled: !!token,
  });

  const recommendations = recommendationsQuery.data?.recommendations ?? [];
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return recommendations.filter((item) => {
      if (actionFilter !== "all" && item.action !== actionFilter) return false;
      if (confidenceFilter !== "all" && item.confidence !== confidenceFilter) return false;
      if (!q) return true;
      return (
        item.name.toLowerCase().includes(q) ||
        item.usage_point_id.includes(q) ||
        item.address.toLowerCase().includes(q) ||
        (item.contractor ?? "").toLowerCase().includes(q)
      );
    });
  }, [recommendations, search, actionFilter, confidenceFilter]);

  const kpis = recommendationsQuery.data?.kpis;

  return (
    <div className="page">
      <div className="page-header page-header-row">
        <div>
          <h2>Preconisations abonnement</h2>
          <p className="page-subtitle">Puissance recommandee, confiance et scenarios sans surpromesse budgetaire.</p>
        </div>
        <button type="button" className="secondary-button" onClick={() => navigate("/energie")}>
          Retour energie
        </button>
      </div>

      {recommendationsQuery.isLoading && <p className="loading-text">Chargement des preconisations...</p>}
      {recommendationsQuery.isError && <p className="error-text">{(recommendationsQuery.error as Error).message}</p>}

      {kpis && (
        <div className="kpi-row">
          <div className="kpi-card">
            <span className="kpi-label">PRM analyses</span>
            <span className="kpi-value">{kpis.total}</span>
          </div>
          <div className="kpi-card kpi-card--alert">
            <span className="kpi-label">Hausse conseillee</span>
            <span className="kpi-value">{kpis.increase}</span>
          </div>
          <div className="kpi-card kpi-card--info">
            <span className="kpi-label">Baisse possible</span>
            <span className="kpi-value">{kpis.decrease}</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Confiance haute</span>
            <span className="kpi-value">{kpis.high_confidence}</span>
          </div>
        </div>
      )}

      <section className="recommendation-note">
        <strong>Garde-fou budgetaire</strong>
        <span>
          L'impact annuel en euros reste masque tant que les tables TURPE ne sont pas importees et auditees.
          Les recommandations ci-dessous priorisent les actions techniques.
        </span>
      </section>

      <div className="list-toolbar">
        <input
          type="search"
          placeholder="Rechercher par nom, PRM, adresse..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="search-input"
        />
        <select value={actionFilter} onChange={(event) => setActionFilter(event.target.value)} className="filter-select">
          <option value="all">Toutes actions</option>
          <option value="increase">Hausse</option>
          <option value="decrease">Baisse</option>
          <option value="maintain">Maintien</option>
          <option value="insufficient_data">Donnees insuff.</option>
        </select>
        <select
          value={confidenceFilter}
          onChange={(event) => setConfidenceFilter(event.target.value)}
          className="filter-select"
        >
          <option value="all">Toutes confiances</option>
          <option value="high">Haute</option>
          <option value="medium">Moyenne</option>
          <option value="low">Faible</option>
          <option value="insufficient">Insuffisante</option>
        </select>
        <span className="result-count">{filtered.length} resultat{filtered.length !== 1 ? "s" : ""}</span>
      </div>

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Site</th>
              <th>Puissances</th>
              <th>Recommandation</th>
              <th>Scenarios</th>
              <th>Confiance</th>
              <th>Impact</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => (
              <tr
                key={item.usage_point_id}
                className="clickable-row"
                onClick={() => navigate(`/energie/${item.usage_point_id}`)}
              >
                <td>
                  <div className="invoice-file-cell">
                    <strong>{item.name}</strong>
                    <span>{item.usage_point_id}</span>
                    <span>{item.address || "-"}</span>
                  </div>
                </td>
                <td>
                  <div className="recommendation-power-cell">
                    <span>Souscrit {formatKva(item.subscribed_power_kva)}</span>
                    <span>Pic {formatKva(item.peak_kva)}</span>
                    <small>{formatPercent(item.current_ratio_percent)} du souscrit</small>
                  </div>
                </td>
                <td>
                  <div className="recommendation-main-cell">
                    {actionBadge(item)}
                    <strong>{formatKva(item.recommended_power_kva)}</strong>
                    <small>{item.justification}</small>
                  </div>
                </td>
                <td><ScenarioChips item={item} /></td>
                <td>
                  <div className="recommendation-power-cell">
                    {confidenceBadge(item)}
                    <span>{item.data_quality.max_power_months} mois</span>
                    <small>{item.data_quality.first_max_power_date ?? "-"} - {item.data_quality.last_max_power_date ?? "-"}</small>
                  </div>
                </td>
                <td>
                  <div className="recommendation-power-cell">
                    <span className="badge badge-gray">Non chiffre</span>
                    <small>{item.economic_estimate.reason}</small>
                  </div>
                </td>
              </tr>
            ))}
            {!recommendationsQuery.isLoading && filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="cell-empty">Aucune preconisation</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

