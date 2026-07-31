import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  fetchGrdfConsoStatus,
  fetchGrdfMonthly,
  fetchGrdfPces,
  fetchGrdfReconcileP1,
  startGrdfBackfill,
  GrdfMonthlySeries,
  GrdfP1ReconcileItem,
} from "../lib/api";
import { useAuth } from "../providers/AuthProvider";

const MONTHS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"];
const MONTHS_LONG = [
  "janv.", "févr.", "mars", "avr.", "mai", "juin",
  "juil.", "août", "sept.", "oct.", "nov.", "déc.",
];
const YEAR_COLORS = ["#2563eb", "#f97316", "#16a34a", "#a855f7", "#06b6d4", "#eab308", "#ec4899", "#64748b"];

function fmtNumber(value: number, digits = 1): string {
  return value.toLocaleString("fr-FR", { maximumFractionDigits: digits });
}

/** Agrège des séries mensuelles (1..N PCE) en données mois × année pour le graphe. */
function aggregateMonthly(series: GrdfMonthlySeries[]): {
  data: Array<Record<string, number | string>>;
  years: number[];
} {
  const byMonth: Record<number, Record<number, number>> = {};
  const years = new Set<number>();
  for (const s of series) {
    for (const p of s.points) {
      years.add(p.annee);
      byMonth[p.mois] = byMonth[p.mois] ?? {};
      byMonth[p.mois][p.annee] = (byMonth[p.mois][p.annee] ?? 0) + p.mwh_pcs;
    }
  }
  const sortedYears = [...years].sort((a, b) => a - b);
  const data = MONTHS.map((label, i) => {
    const mois = i + 1;
    const row: Record<string, number | string> = { month: label };
    for (const y of sortedYears) row[String(y)] = Math.round((byMonth[mois]?.[y] ?? 0) * 10) / 10;
    return row;
  });
  return { data, years: sortedYears };
}

function reconcileBadge(statut: string): { cls: string; label: string } {
  switch (statut) {
    case "ok":
      return { cls: "badge-green", label: "Cohérent" };
    case "ecart":
      return { cls: "badge-orange", label: "Écart" };
    case "blocked":
      return { cls: "badge-gray", label: "Non rapprochable" };
    default:
      return { cls: "badge-gray", label: statut };
  }
}

export function EnergieGazPage() {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [selectedPce, setSelectedPce] = useState<string>("");
  const [showTable, setShowTable] = useState(false);

  const pcesQuery = useQuery({
    queryKey: ["grdf-pces"],
    queryFn: () => fetchGrdfPces(token!),
    enabled: !!token,
  });

  const statusQuery = useQuery({
    queryKey: ["grdf-conso-status"],
    queryFn: () => fetchGrdfConsoStatus(token!),
    enabled: !!token,
    refetchInterval: (query) => (query.state.data?.status === "running" ? 4000 : false),
  });

  // Toujours "tous PCE" : alimente les KPI (total, période) et le graphe agrégé.
  const totalsQuery = useQuery({
    queryKey: ["grdf-monthly", "__all__"],
    queryFn: () => fetchGrdfMonthly(token!),
    enabled: !!token,
  });

  // Série filtrée par le sélecteur : alimente le graphe + le tableau détaillé.
  const monthlyQuery = useQuery({
    queryKey: ["grdf-monthly", selectedPce || "__all__"],
    queryFn: () => fetchGrdfMonthly(token!, selectedPce || undefined),
    enabled: !!token,
  });

  const collecteMutation = useMutation({
    mutationFn: () => startGrdfBackfill(token!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["grdf-conso-status"] });
      queryClient.invalidateQueries({ queryKey: ["grdf-monthly"] });
    },
  });

  const pces = pcesQuery.data ?? [];
  const status = statusQuery.data;
  const isRunning = status?.status === "running";

  const kpis = useMemo(() => {
    const active = pces.filter((p) => p.etat_droit_acces === "Active");
    const collectable = active.filter((p) => p.perim_publiees);
    const totals = totalsQuery.data ?? [];
    const totalKwh = totals.reduce((acc, s) => acc + s.total_kwh, 0);
    const allPoints = totals.flatMap((s) => s.points);
    let periode: string | null = null;
    if (allPoints.length > 0) {
      const keyed = allPoints.map((p) => p.annee * 100 + p.mois).sort((a, b) => a - b);
      const min = keyed[0];
      const max = keyed[keyed.length - 1];
      const fmt = (k: number) => `${MONTHS_LONG[(k % 100) - 1]} ${Math.floor(k / 100)}`;
      periode = `${fmt(min)} → ${fmt(max)}`;
    }
    return {
      total: pces.length,
      active: active.length,
      collectable: collectable.length,
      gwh: totalKwh / 1_000_000,
      periode,
    };
  }, [pces, totalsQuery.data]);

  const chart = useMemo(() => aggregateMonthly(monthlyQuery.data ?? []), [monthlyQuery.data]);

  // Rapprochement P1 : année par défaut = la plus récente disponible.
  const availableYears = useMemo(() => {
    const ys = new Set<number>();
    for (const s of totalsQuery.data ?? []) for (const p of s.points) ys.add(p.annee);
    return [...ys].sort((a, b) => b - a);
  }, [totalsQuery.data]);
  const [reconcileYear, setReconcileYear] = useState<number | null>(null);
  const effectiveYear = reconcileYear ?? availableYears[0] ?? new Date().getFullYear();

  const reconcileQuery = useQuery({
    queryKey: ["grdf-reconcile-p1", effectiveYear],
    queryFn: () => fetchGrdfReconcileP1(token!, effectiveYear),
    enabled: !!token && availableYears.length > 0,
  });

  const selectedSeries = monthlyQuery.data ?? [];

  return (
    <div className="page">
      <header className="page-header page-header-row">
        <div>
          <h1>Gaz — GRDF ADICT</h1>
          <p className="page-subtitle">
            Consommations réelles du distributeur GRDF par PCE, suivi temporel et rapprochement avec le P1 gaz DALKIA.
          </p>
        </div>
        <div className="page-header-actions" style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {status && (
            <span className={`badge ${isRunning ? "badge-blue" : "badge-gray"}`}>
              {isRunning
                ? `Collecte… ${status.pce_total > 0 ? `${status.pce_done}/${status.pce_total}` : ""}`
                : "Synchronisé"}
            </span>
          )}
          <button
            className="btn-primary"
            onClick={() => collecteMutation.mutate()}
            disabled={collecteMutation.isPending || isRunning}
          >
            {isRunning ? "Collecte en cours…" : "Collecter les consommations"}
          </button>
        </div>
      </header>

      {collecteMutation.isError && (
        <p className="error-text" style={{ marginBottom: 12 }}>
          La collecte a échoué — vérifier que les identifiants GRDF sont configurés côté serveur.
        </p>
      )}

      {/* KPI */}
      <div className="kpi-row">
        <div className="kpi-card">
          <span className="kpi-label">PCE référencés</span>
          <span className="kpi-value">{kpis.total}</span>
        </div>
        <div className="kpi-card kpi-card--info">
          <span className="kpi-label">Droits actifs</span>
          <span className="kpi-value">{kpis.active}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Collectables</span>
          <span className="kpi-value">{kpis.collectable}</span>
        </div>
        <div className="kpi-card kpi-card--info">
          <span className="kpi-label">Total consommé</span>
          <span className="kpi-value">{fmtNumber(kpis.gwh, 2)} GWh</span>
        </div>
        {kpis.periode && (
          <div className="kpi-card">
            <span className="kpi-label">Période couverte</span>
            <span className="kpi-value" style={{ fontSize: "1rem" }}>{kpis.periode}</span>
          </div>
        )}
      </div>

      {/* Suivi mensuel — graphe année/année */}
      <div className="chart-section">
        <div className="section-title-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <div>
            <h3 style={{ margin: 0 }}>Suivi mensuel des consommations</h3>
            <p className="chart-subtitle" style={{ margin: "4px 0 0" }}>
              Barres : consommation mensuelle (MWh PCS), une couleur par année. {selectedPce ? "PCE sélectionné." : "Tous les PCE agrégés."}
            </p>
          </div>
          <select value={selectedPce} onChange={(e) => setSelectedPce(e.target.value)}>
            <option value="">Tous les PCE</option>
            {pces.map((p) => (
              <option key={p.id_pce} value={p.id_pce}>
                {p.nom_site ? `${p.nom_site} (${p.id_pce})` : p.id_pce}
              </option>
            ))}
          </select>
        </div>

        {monthlyQuery.isLoading ? (
          <p className="muted-text">Chargement…</p>
        ) : chart.years.length === 0 ? (
          <p className="muted-text">Aucun relevé disponible — lancer une collecte.</p>
        ) : (
          <>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={chart.data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} unit=" MWh" width={72} />
                <Tooltip
                  formatter={(value: number, name: string) => [`${fmtNumber(value)} MWh`, `Année ${name}`]}
                  labelFormatter={(l) => `Mois : ${l}`}
                />
                <Legend formatter={(v) => `Année ${v}`} />
                {chart.years.map((year, i) => (
                  <Bar key={year} dataKey={String(year)} fill={YEAR_COLORS[i % YEAR_COLORS.length]} maxBarSize={22} />
                ))}
              </BarChart>
            </ResponsiveContainer>

            <button
              className="btn-compact"
              style={{ marginTop: 8 }}
              onClick={() => setShowTable((v) => !v)}
            >
              {showTable ? "Masquer le détail chiffré" : "Afficher le détail chiffré"}
            </button>

            {showTable && (
              <div style={{ marginTop: 12 }}>
                {selectedSeries.map((series) => (
                  <div key={series.id_pce} style={{ marginBottom: 20 }}>
                    <h4 style={{ marginBottom: 8 }}>
                      {series.nom_site ? `${series.nom_site} — ${series.id_pce}` : series.id_pce}
                      <span className="muted-text" style={{ fontWeight: "normal", marginLeft: 8 }}>
                        {fmtNumber(series.total_kwh / 1000)} MWh cumulé
                      </span>
                    </h4>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Année</th>
                          {MONTHS.map((m) => (
                            <th key={m}>{m}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {[...new Set(series.points.map((p) => p.annee))].sort().map((y) => (
                          <tr key={y}>
                            <td><strong>{y}</strong></td>
                            {MONTHS.map((_, i) => {
                              const point = series.points.find((p) => p.annee === y && p.mois === i + 1);
                              return <td key={i}>{point ? fmtNumber(point.mwh_pcs) : "—"}</td>;
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {/* Rapprochement P1 DALKIA */}
      <div className="chart-section">
        <div className="section-title-row" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <div>
            <h3 style={{ margin: 0 }}>Rapprochement P1 gaz DALKIA</h3>
            <p className="chart-subtitle" style={{ margin: "4px 0 0" }}>
              Consommation GRDF réelle vs quantité P1 facturée par DALKIA, par PCE.
            </p>
          </div>
          {availableYears.length > 0 && (
            <select
              value={effectiveYear}
              onChange={(e) => setReconcileYear(Number(e.target.value))}
            >
              {availableYears.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          )}
        </div>

        {reconcileQuery.isLoading ? (
          <p className="muted-text">Chargement…</p>
        ) : (reconcileQuery.data ?? []).length === 0 ? (
          <p className="muted-text">Aucun rapprochement disponible pour {effectiveYear}.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Site / PCE</th>
                <th style={{ textAlign: "right" }}>GRDF (MWh)</th>
                <th style={{ textAlign: "right" }}>P1 DALKIA (MWh)</th>
                <th style={{ textAlign: "right" }}>Écart</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {(reconcileQuery.data ?? []).map((item: GrdfP1ReconcileItem) => {
                const badge = reconcileBadge(item.statut);
                const ecart = item.ecart_pct;
                return (
                  <tr key={item.id_pce}>
                    <td>
                      <strong>{item.nom_site || item.code_site || "—"}</strong>
                      <span className="muted-text" style={{ marginLeft: 6, fontSize: "0.85em" }}>{item.id_pce}</span>
                    </td>
                    <td style={{ textAlign: "right" }}>{fmtNumber(item.grdf_mwh_pcs)}</td>
                    <td style={{ textAlign: "right" }}>
                      {item.dalkia_p1_qt_mwhpcs != null ? fmtNumber(item.dalkia_p1_qt_mwhpcs) : "—"}
                    </td>
                    <td style={{ textAlign: "right", color: ecart != null && Math.abs(ecart) > 5 ? "#dc2626" : undefined }}>
                      {ecart != null ? `${ecart > 0 ? "+" : ""}${fmtNumber(ecart)} %` : "—"}
                    </td>
                    <td><span className={`badge ${badge.cls}`}>{badge.label}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default EnergieGazPage;
