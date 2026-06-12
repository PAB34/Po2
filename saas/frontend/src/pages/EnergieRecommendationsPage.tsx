import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchPowerRecommendations } from "../lib/api";
import type { PrmPowerRecommendation } from "../lib/api";
import { useAuth } from "../providers/AuthProvider";
import { PowerCalibrationChart } from "../components/PowerCalibrationChart";

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

const SORT_LABELS: Record<string, string> = {
  priority: "Priorite",
  annual_desc: "Conso annuelle decroissante",
  annual_asc: "Conso annuelle croissante",
};

type ImpactSummary = {
  pricedCount: number;
  unavailableCount: number;
  annualNetImpact: number;
  annualSavings: number;
  annualExtraCost: number;
  increaseKva: number;
  decreaseKva: number;
  increaseCount: number;
  decreaseCount: number;
};

type SupplierImpactSummary = ImpactSummary & {
  supplier: string;
  totalCount: number;
};

function formatKva(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} kVA`;
}

function formatKwh(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  if (value >= 1000) {
    return `${(value / 1000).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} MWh`;
  }
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 0 })} kWh`;
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} %`;
}

function formatCurrency(value: number | null | undefined) {
  if (value === null || value === undefined) return "-";
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(value);
}

function netImpactBadgeClass(value: number) {
  return value <= 0 ? "badge-green" : "badge-orange";
}

function netImpactLabel(value: number) {
  if (value < 0) return `Gain net ${formatCurrency(Math.abs(value))} / an`;
  if (value > 0) return `Cout net ${formatCurrency(value)} / an`;
  return `Impact neutre ${formatCurrency(0)} / an`;
}

function netImpactCardTitle(value: number) {
  if (value < 0) return "Gain net estime";
  if (value > 0) return "Cout net estime";
  return "Impact net estime";
}

function netImpactCardAmount(value: number) {
  return formatCurrency(Math.abs(value));
}

function buildImpactSummary(recommendations: PrmPowerRecommendation[]): ImpactSummary {
  return recommendations.reduce<ImpactSummary>((summary, item) => {
    applyRecommendationToImpact(summary, item);
    return summary;
  }, emptyImpactSummary());
}

function applyRecommendationToImpact(summary: ImpactSummary, item: PrmPowerRecommendation) {
  const estimate = item.economic_estimate;
  if (estimate.available && estimate.annual_amount_eur !== null) {
    summary.pricedCount += 1;
    summary.annualNetImpact += estimate.annual_amount_eur;
    if (estimate.annual_amount_eur < 0) {
      summary.annualSavings += Math.abs(estimate.annual_amount_eur);
    } else if (estimate.annual_amount_eur > 0) {
      summary.annualExtraCost += estimate.annual_amount_eur;
    }
  } else {
    summary.unavailableCount += 1;
  }

  if (item.subscribed_power_kva !== null && item.recommended_power_kva !== null) {
    const delta = item.recommended_power_kva - item.subscribed_power_kva;
    if (delta > 0) {
      summary.increaseKva += delta;
      summary.increaseCount += 1;
    } else if (delta < 0) {
      summary.decreaseKva += Math.abs(delta);
      summary.decreaseCount += 1;
    }
  }
}

function emptyImpactSummary(): ImpactSummary {
  return {
    pricedCount: 0,
    unavailableCount: 0,
    annualNetImpact: 0,
    annualSavings: 0,
    annualExtraCost: 0,
    increaseKva: 0,
    decreaseKva: 0,
    increaseCount: 0,
    decreaseCount: 0,
  };
}

function buildSupplierImpactSummaries(recommendations: PrmPowerRecommendation[]): SupplierImpactSummary[] {
  const bySupplier = new Map<string, SupplierImpactSummary>();
  for (const item of recommendations) {
    const supplier = item.contractor || "Fournisseur inconnu";
    const summary = bySupplier.get(supplier) ?? {
      ...emptyImpactSummary(),
      supplier,
      totalCount: 0,
    };
    summary.totalCount += 1;
    applyRecommendationToImpact(summary, item);
    bySupplier.set(supplier, summary);
  }
  return Array.from(bySupplier.values()).sort(
    (a, b) => Math.abs(b.annualNetImpact) - Math.abs(a.annualNetImpact) || b.totalCount - a.totalCount,
  );
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

function realCostsCell(item: PrmPowerRecommendation) {
  const rc = item.real_costs;
  if (!rc || !rc.available) {
    return (
      <div className="recommendation-power-cell">
        <span className="badge badge-gray">Pas de facture</span>
        <small>Reimporter les factures pour le reel</small>
      </div>
    );
  }
  const hasPenalty = rc.penalties_eur > 0;
  return (
    <div className="recommendation-power-cell">
      <span className={`badge ${hasPenalty ? "badge-red" : "badge-green"}`}>
        {hasPenalty ? `${formatCurrency(rc.penalties_eur)} penalites` : "0 penalite"}
      </span>
      {rc.fixed_routing_eur !== null && <span>Part fixe {formatCurrency(rc.fixed_routing_eur)}</span>}
      <small>
        {rc.invoices_count} facture{rc.invoices_count !== 1 ? "s" : ""}
        {rc.max_reached_power_kva !== null ? ` | pic facture ${formatKva(rc.max_reached_power_kva)}` : ""}
      </small>
    </div>
  );
}

export function EnergieRecommendationsPage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("all");
  const [confidenceFilter, setConfidenceFilter] = useState("all");
  const [supplierFilter, setSupplierFilter] = useState("all");
  const [sortMode, setSortMode] = useState("priority");

  const recommendationsQuery = useQuery({
    queryKey: ["power-recommendations"],
    queryFn: () => fetchPowerRecommendations(token!),
    enabled: !!token,
  });

  const recommendations = recommendationsQuery.data?.recommendations ?? [];
  const impactSummary = useMemo(() => buildImpactSummary(recommendations), [recommendations]);
  const realCostsSummary = useMemo(() => {
    let penaltiesTotal = 0;
    let prmWithPenalties = 0;
    let prmWithData = 0;
    for (const item of recommendations) {
      const rc = item.real_costs;
      if (!rc?.available) continue;
      prmWithData += 1;
      if (rc.penalties_eur > 0) {
        penaltiesTotal += rc.penalties_eur;
        prmWithPenalties += 1;
      }
    }
    return { penaltiesTotal, prmWithPenalties, prmWithData };
  }, [recommendations]);
  const supplierImpactSummaries = useMemo(() => buildSupplierImpactSummaries(recommendations), [recommendations]);
  const suppliers = useMemo(() => {
    return Array.from(new Set(recommendations.map((item) => item.contractor).filter(Boolean) as string[])).sort((a, b) =>
      a.localeCompare(b, "fr"),
    );
  }, [recommendations]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const rows = recommendations.filter((item) => {
      if (actionFilter !== "all" && item.action !== actionFilter) return false;
      if (confidenceFilter !== "all" && item.confidence !== confidenceFilter) return false;
      if (supplierFilter !== "all" && item.contractor !== supplierFilter) return false;
      if (!q) return true;
      return (
        item.name.toLowerCase().includes(q) ||
        item.usage_point_id.includes(q) ||
        item.address.toLowerCase().includes(q) ||
        (item.contractor ?? "").toLowerCase().includes(q)
      );
    });
    return rows.sort((a, b) => {
      if (sortMode === "annual_desc") {
        return (b.annual_consumption_kwh ?? -1) - (a.annual_consumption_kwh ?? -1);
      }
      if (sortMode === "annual_asc") {
        return (a.annual_consumption_kwh ?? Number.MAX_SAFE_INTEGER) - (b.annual_consumption_kwh ?? Number.MAX_SAFE_INTEGER);
      }
      return b.priority_score - a.priority_score;
    });
  }, [recommendations, search, actionFilter, confidenceFilter, supplierFilter, sortMode]);

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

      {!recommendationsQuery.isLoading && recommendations.length > 0 && (
        <PowerCalibrationChart
          recommendations={filtered}
          onSelect={(prmId) => navigate(`/energie/${prmId}`)}
        />
      )}

      {!recommendationsQuery.isLoading && recommendations.length > 0 && (
        <section className="impact-balance-panel">
          <div className="impact-balance-header">
            <div>
              <h3>Bilan des impacts</h3>
              <p>
                Synthese annuelle des changements de puissance proposes. Le solde correspond aux
                surcouts moins les economies ; un gain net signifie que les economies depassent les
                hausses.
              </p>
            </div>
            <span className={`badge ${netImpactBadgeClass(impactSummary.annualNetImpact)}`}>
              {netImpactLabel(impactSummary.annualNetImpact)}
            </span>
          </div>
          <div className="impact-balance-grid">
            <div className="impact-balance-card impact-balance-card--net">
              <span>{netImpactCardTitle(impactSummary.annualNetImpact)}</span>
              <strong>{netImpactCardAmount(impactSummary.annualNetImpact)}</strong>
              <small>
                Surcouts - economies | {impactSummary.pricedCount} PRM chiffre
                {impactSummary.pricedCount !== 1 ? "s" : ""}
              </small>
            </div>
            <div className="impact-balance-card impact-balance-card--saving">
              <span>Economies potentielles</span>
              <strong>{formatCurrency(impactSummary.annualSavings)}</strong>
              <small>
                {impactSummary.decreaseCount} baisse{impactSummary.decreaseCount !== 1 ? "s" : ""} | -
                {formatKva(impactSummary.decreaseKva)}
              </small>
            </div>
            <div className="impact-balance-card impact-balance-card--cost">
              <span>Surcouts a prevoir</span>
              <strong>{formatCurrency(impactSummary.annualExtraCost)}</strong>
              <small>
                {impactSummary.increaseCount} hausse{impactSummary.increaseCount !== 1 ? "s" : ""} | +
                {formatKva(impactSummary.increaseKva)}
              </small>
            </div>
            <div className="impact-balance-card">
              <span>Non chiffres</span>
              <strong>{impactSummary.unavailableCount}</strong>
              <small>Tarif, donnees ou formule non exploitables pour l'estimation.</small>
            </div>
            <div className="impact-balance-card impact-balance-card--real">
              <span>Penalites reelles payees (12 mois)</span>
              <strong>{formatCurrency(realCostsSummary.penaltiesTotal)}</strong>
              <small>
                {realCostsSummary.prmWithData > 0
                  ? `${realCostsSummary.prmWithPenalties} PRM en depassement, issu des factures importees`
                  : "Aucune facture exploitable : reimporter les factures ENGIE"}
              </small>
            </div>
          </div>
          <p className="impact-balance-footnote">
            Les economies/surcouts ci-dessus sont theoriques (part fixe TURPE). Les penalites reelles et le
            cout d'acheminement par site proviennent des factures importees, sur 12 mois glissants.
          </p>
          {supplierImpactSummaries.length > 0 && (
            <div className="impact-supplier-table-wrapper">
              <div className="impact-supplier-heading">
                <strong>Analyse par fournisseur</strong>
                <span>
                  Classement par solde annuel absolu. Gain net = economies superieures aux surcouts.
                </span>
              </div>
              <table className="data-table impact-supplier-table">
                <thead>
                  <tr>
                    <th>Fournisseur</th>
                    <th>PRM</th>
                    <th>Solde annuel</th>
                    <th>Economies</th>
                    <th>Surcouts</th>
                    <th>Variation kVA</th>
                    <th>Non chiffres</th>
                  </tr>
                </thead>
                <tbody>
                  {supplierImpactSummaries.map((supplier) => (
                    <tr key={supplier.supplier}>
                      <td>
                        <strong>{supplier.supplier}</strong>
                      </td>
                      <td>{supplier.totalCount}</td>
                      <td>
                        <span className={`badge ${netImpactBadgeClass(supplier.annualNetImpact)}`}>
                          {netImpactLabel(supplier.annualNetImpact)}
                        </span>
                      </td>
                      <td>{formatCurrency(supplier.annualSavings)}</td>
                      <td>{formatCurrency(supplier.annualExtraCost)}</td>
                      <td>
                        <div className="recommendation-power-cell">
                          <span>+{formatKva(supplier.increaseKva)} / -{formatKva(supplier.decreaseKva)}</span>
                          <small>
                            {supplier.increaseCount} hausse{supplier.increaseCount !== 1 ? "s" : ""},{" "}
                            {supplier.decreaseCount} baisse
                            {supplier.decreaseCount !== 1 ? "s" : ""}
                          </small>
                        </div>
                      </td>
                      <td>{supplier.unavailableCount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

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
          L'impact annuel affiche uniquement la part fixe TURPE lorsque le bareme et la formule
          d'acheminement sont exploitables.
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
        <select
          value={supplierFilter}
          onChange={(event) => setSupplierFilter(event.target.value)}
          className="filter-select"
        >
          <option value="all">Tous fournisseurs</option>
          {suppliers.map((supplier) => (
            <option key={supplier} value={supplier}>{supplier}</option>
          ))}
        </select>
        <select value={sortMode} onChange={(event) => setSortMode(event.target.value)} className="filter-select">
          {Object.entries(SORT_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        <span className="result-count">{filtered.length} resultat{filtered.length !== 1 ? "s" : ""}</span>
      </div>

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Site</th>
              <th>Conso annuelle</th>
              <th>Puissances</th>
              <th>Recommandation</th>
              <th>Scenarios</th>
              <th>Confiance</th>
              <th>Impact theorique</th>
              <th>Reel (12 mois)</th>
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
                    <span>{item.contractor ?? "-"}</span>
                    <span>{item.address || "-"}</span>
                  </div>
                </td>
                <td>
                  <div className="recommendation-power-cell">
                    <strong>{formatKwh(item.annual_consumption_kwh)}</strong>
                    <small>
                      {item.annual_consumption_days > 0
                        ? `${item.annual_consumption_days} jours | ${item.annual_consumption_start ?? "-"} - ${item.annual_consumption_end ?? "-"}`
                        : "Donnees absentes"}
                    </small>
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
                    {item.economic_estimate.available ? (
                      <span
                        className={`badge ${
                          (item.economic_estimate.annual_amount_eur ?? 0) <= 0 ? "badge-green" : "badge-orange"
                        }`}
                      >
                        {formatCurrency(item.economic_estimate.annual_amount_eur)} / an
                      </span>
                    ) : (
                      <span className="badge badge-gray">Non chiffre</span>
                    )}
                    <small>{item.economic_estimate.reason}</small>
                  </div>
                </td>
                <td>{realCostsCell(item)}</td>
              </tr>
            ))}
            {!recommendationsQuery.isLoading && filtered.length === 0 && (
              <tr>
                <td colSpan={8} className="cell-empty">Aucune preconisation</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
